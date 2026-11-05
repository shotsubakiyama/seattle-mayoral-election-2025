"""Audit 2021/2025 Seattle precinct IDs; do NOT assume matching IDs imply matching boundaries.

Run: python scripts/diagnose_precinct_matching.py
     python scripts/diagnose_precinct_matching.py --offline
Official source downloads are stored in gitignored data/raw/.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE_IDS = {2021: "4qrf-rjar", 2025: "rkie-6y8x"}
CERTIFIED_2025 = {"Bruce Harrell": 136_920, "Katie Wilson": 138_931}


def ensure_source(year, path, offline):
    if path.exists() and path.stat().st_size:
        return
    if offline:
        raise FileNotFoundError(f"Missing {path}; omit --offline to download")
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset = SOURCE_IDS[year]
    urls = [
        f"https://data.kingcounty.gov/api/v3/views/{dataset}/export.csv?accessType=DOWNLOAD",
        f"https://data.kingcounty.gov/api/views/{dataset}/rows.csv?accessType=DOWNLOAD",
    ]
    failures = []
    for url in urls:
        try:
            request = Request(url, headers={"User-Agent": "Seattle-Mayoral-Election-Research/1.0"})
            with urlopen(request, timeout=90) as response, path.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if path.stat().st_size:
                print(f"Downloaded {year} certified precinct results")
                return
        except (OSError, TimeoutError) as error:
            failures.append(str(error))
            path.unlink(missing_ok=True)
    raise RuntimeError(f"Download failed for {year}: {failures}")


def suffix(precinct):
    name = precinct.strip()
    if not name.startswith("SEA ") or "-" not in name:
        return None
    value = name.rsplit("-", 1)[-1]
    return value if value.isdigit() else None


def read_results(path):
    results = defaultdict(lambda: defaultdict(int))
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {"".join(k.lower().split()) for k in reader.fieldnames or []}
        if not {"precinct", "race", "countertype", "sumofcount"} <= fields:
            raise ValueError(f"Unexpected CSV header in {path}: {reader.fieldnames}")
        for original in reader:
            row = {"".join(k.lower().split()): (v or "").strip() for k, v in original.items() if k}
            if row["race"] != "City of Seattle Mayor" or row.get("countergroup", "Total") != "Total":
                continue
            pid = suffix(row["precinct"])
            if pid is None:
                raise ValueError(f"Unexpected Seattle precinct: {row['precinct']!r}")
            results[pid]
            candidate = row["countertype"]
            if candidate in CERTIFIED_2025:
                results[pid][candidate] += int(row["sumofcount"].replace(",", ""))
    if not results:
        raise ValueError(f"No Seattle mayoral precinct records in {path}")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Do not download missing data")
    args = parser.parse_args()
    raw = ROOT / "data/raw"
    files = {y: raw / f"{y}_final_precinct_results.csv" for y in SOURCE_IDS}
    for year, file in files.items():
        ensure_source(year, file, args.offline)
    data21 = read_results(files[2021])
    data25 = read_results(files[2025])

    with (ROOT / "data/processed/seattle_mayor_precinct_panel_2021_2025.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        panel = list(csv.DictReader(handle))
    stable = {r["precinct_id"] for r in panel}
    if len(panel) != len(stable):
        raise ValueError("Duplicate stable precinct IDs")
    if not stable <= data25.keys():
        raise ValueError("Stable precinct ID missing from official 2025 records")
    totals = {candidate: sum(row.get(candidate, 0) for row in data25.values())
              for candidate in CERTIFIED_2025}
    if totals != CERTIFIED_2025:
        raise ValueError(f"Official 2025 candidate totals failed reconciliation: {totals}")

    destination = ROOT / "data/processed/precinct_2025_match_diagnostic.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    counts = defaultdict(int)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "precinct_id", "match_status", "harrell_votes_2025", "wilson_votes_2025",
            "two_candidate_votes_2025", "has_2021_numeric_id"
        ])
        writer.writeheader()
        for pid in sorted(data25, key=int):
            if pid in stable:
                status = "stable_boundary_verified_in_existing_panel"
            elif pid in data21:
                status = "shared_numeric_id_boundary_not_verified"
            else:
                status = "no_matching_2021_numeric_id"
            counts[status] += 1
            h, w = (data25[pid].get(c, 0) for c in CERTIFIED_2025)
            writer.writerow({
                "precinct_id": pid, "match_status": status,
                "harrell_votes_2025": h, "wilson_votes_2025": w,
                "two_candidate_votes_2025": h + w,
                "has_2021_numeric_id": pid in data21,
            })
    print(f"2021 mayoral precincts: {len(data21):,}")
    print(f"2025 mayoral precincts: {len(data25):,}")
    print(f"2025 certified candidate totals reconciled: {totals}")
    for status, count in sorted(counts.items()):
        print(f"{status}: {count:,}")
    print(f"Wrote {destination.relative_to(ROOT)}")
    print("IMPORTANT: Shared numeric precinct ID is not proof of matching boundaries.")


if __name__ == "__main__":
    main()
