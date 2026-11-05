"""Rebuild the first coverage audit and SVG figure from checked-in CSVs.

Run: python scripts/coverage_audit.py
Uses only the Python standard library. No raw-data download required.
"""
import csv
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data/processed/seattle_mayor_precinct_panel_2021_2025.csv"
CROSSWALK = ROOT / "data/processed/block_group_to_2025_precinct_crosswalk.csv"
OUT = ROOT / "docs/methodology"
CITY_HARRELL = 136_920
CITY_WILSON = 138_931


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def audit():
    rows = read_csv(PANEL)
    ids = [r["precinct_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicated matched precinct IDs")
    if not all(r["stable_boundary"] == "True" for r in rows):
        raise ValueError("A matched precinct lacks a stable-boundary flag")
    for row in rows:
        for year in (2021, 2025):
            a = int(row[f"harrell_votes_{year}"])
            b = int(row[f"opponent_votes_{year}"])
            if a + b != int(row[f"two_candidate_votes_{year}"]):
                raise ValueError(f"Vote totals disagree: {row['precinct_id']} {year}")
    harrell = sum(int(r["harrell_votes_2025"]) for r in rows)
    wilson = sum(int(r["opponent_votes_2025"]) for r in rows)
    if harrell > CITY_HARRELL or wilson > CITY_WILSON:
        raise ValueError("Matched votes exceed certified citywide totals")
    crosswalk_ids = {r["precinct_id"] for r in read_csv(CROSSWALK)}
    if not set(ids) <= crosswalk_ids:
        raise ValueError("Matched precinct missing from Census crosswalk")
    return len(ids), len(crosswalk_ids), harrell, wilson


def make_svg(n, h, w):
    margins = [
        (f"Matched {n:,} stable-boundary precincts", h - w),
        ("All remaining 2025 votes", (CITY_HARRELL - h) - (CITY_WILSON - w)),
        ("Certified Seattle citywide", CITY_HARRELL - CITY_WILSON),
    ]
    largest = max(abs(v) for _, v in margins)
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 830 375" role="img" aria-label="Net vote margins among matched precincts, remaining precincts, and citywide">',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#213447}.title{font-size:22px;font-weight:700}.subtitle{font-size:13px;fill:#536779}.row-label{font-size:15px;font-weight:600}.number{font-size:15px;font-weight:700}.foot{font-size:12px;fill:#657789}</style>',
        '<rect width="830" height="375" fill="#ffffff"/>',
        '<text x="26" y="37" class="title">Why the matched subset tells a different story</text>',
        '<text x="26" y="64" class="subtitle">Net 2025 mayoral votes (Harrell minus Wilson); blue = Harrell advantage, orange = Wilson advantage</text>',
        '<line x1="442" y1="101" x2="442" y2="324" stroke="#9aaaba" stroke-width="2"/>',
    ]
    for i, (label, margin) in enumerate(margins):
        top = 128 + 80 * i
        width = 265 * abs(margin) / largest
        x = 442 if margin >= 0 else 442 - width
        color = "#2474a8" if margin >= 0 else "#cc7135"
        label_x = x + width + 9 if margin >= 0 else x - 9
        anchor = "start" if margin >= 0 else "end"
        lines += [
            f'<text x="26" y="{top-11}" class="row-label">{escape(label)}</text>',
            f'<rect x="{x:.1f}" y="{top}" width="{width:.1f}" height="25" rx="4" fill="{color}"/>',
            f'<text x="{label_x:.1f}" y="{top+18}" text-anchor="{anchor}" class="number">{margin:+,}</text>',
        ]
    lines += [
        '<text x="26" y="356" class="foot">Sources: King County certified totals; matched-precinct panel. Remainder is an arithmetic difference, not spatially harmonized.</text>',
        '</svg>',
    ]
    return "\n".join(lines) + "\n"


def main():
    n, all_ids, h, w = audit()
    other_h, other_w = CITY_HARRELL - h, CITY_WILSON - w
    coverage = 100 * (h + w) / (CITY_HARRELL + CITY_WILSON)
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    (OUT / "figures/matched_coverage_margins.svg").write_text(make_svg(n, h, w), encoding="utf-8")
    print(f"Matched precincts: {n:,} of {all_ids:,} in the 2025 Census crosswalk")
    print(f"Matched two-candidate vote coverage: {coverage:.1f}%")
    print(f"Net Harrell votes within matched subset: {h-w:+,}")
    print(f"Net Harrell votes outside subset: {other_h-other_w:+,}")
    print(f"Net Harrell votes citywide: {CITY_HARRELL-CITY_WILSON:+,}")
    print("Figure written: docs/methodology/figures/matched_coverage_margins.svg")


if __name__ == "__main__":
    main()
