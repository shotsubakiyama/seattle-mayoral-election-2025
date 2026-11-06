"""Compare 2021 and 2025 Seattle precinct polygons; keep source GIS files local.

Requires: pip install shapely>=2.1
Run: python scripts/spatial_precinct_overlap.py
Historical King County polygons are cached under ignored data/raw/.
"""
import csv
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shapely import STRtree, make_valid
from shapely.geometry import LinearRing, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/raw/precinct_shapes"
SERVICES = {
    2021: "VOTDST_2021_AREA_3065",
    2025: "VOTDST_2025_AREA_3072",
}
BASE = "https://services.arcgis.com/Ej0PsM5Aw677QF1W/ArcGIS/rest/services"


def query(year, params):
    url = f"{BASE}/{SERVICES[year]}/FeatureServer/0/query?" + urlencode({**params, "f": "json"})
    try:
        with urlopen(Request(url, headers={"User-Agent": "Seattle-Election-Research/1.0"}), timeout=90) as response:
            data = response.read()
    except OSError as error:
        if os.name != "nt":
            raise RuntimeError(f"Could not connect to {url}: {error}") from error
        curl = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/curl.exe"
        if not curl.is_file():
            raise RuntimeError(f"Missing Windows curl.exe; original error: {error}") from error
        result = subprocess.run([str(curl), "--fail", "--location", "--silent", "--show-error",
                                 "--connect-timeout", "20", "--max-time", "180", url],
                                capture_output=True, timeout=190, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace")) from error
        data = result.stdout
    response = json.loads(data)
    if "error" in response:
        raise ValueError(f"ArcGIS API returned an error: {response['error']}")
    return response


def fetch_shapes(year):
    file = CACHE / f"{year}_seattle_precincts.json"
    if file.exists():
        data = json.loads(file.read_text(encoding="utf-8"))
    else:
        ids = query(year, {"where": "NAME LIKE 'SEA %'", "returnIdsOnly": "true"}).get("objectIds", [])
        if len(ids) < 900:
            raise ValueError(f"Only {len(ids)} Seattle geometry IDs returned for {year}; refusing incomplete fetch")
        features = []
        for i in range(0, len(ids), 100):
            result = query(year, {"objectIds": ",".join(map(str, ids[i:i+100])),
                                  "outFields": "NAME,OBJECTID", "returnGeometry": "true", "outSR": "2926"})
            page = result.get("features", [])
            if len(page) != len(ids[i:i+100]):
                raise ValueError(f"Incomplete polygon batch for {year}: expected {len(ids[i:i+100])}, got {len(page)}")
            features.extend(page)
        data = {"spatialReference": {"wkid": 2926}, "features": features}
        CACHE.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(data), encoding="utf-8")
    if data.get("spatialReference", {}).get("wkid") != 2926:
        raise ValueError(f"Unexpected coordinate system for {year}; expected EPSG:2926")
    result = {}
    for feature in data["features"]:
        name = feature["attributes"]["NAME"]
        if not name.startswith("SEA "):
            continue
        pid = name.rsplit("-", 1)[-1]
        if not pid.isdigit() or pid in result:
            raise ValueError(f"Invalid/duplicate Seattle precinct: {name!r}")
        result[pid] = esri_polygon(feature["geometry"])
    return result


def esri_polygon(geometry):
    # Esri JSON: clockwise rings represent exteriors, counter-clockwise holes.
    outer, holes = [], []
    for ring in geometry.get("rings", []):
        if len(ring) < 4:
            continue
        poly = Polygon(ring)
        if poly.area == 0:
            continue
        (holes if LinearRing(ring).is_ccw else outer).append(poly)
    if not outer:
        raise ValueError("Polygon geometry has no clockwise exterior rings")
    shape = unary_union(outer)
    if holes:
        shape = shape.difference(unary_union(holes))
    shape = make_valid(shape)
    if shape.is_empty or shape.area == 0:
        raise ValueError("Invalid or empty polygon after conversion")
    return shape


def read_election_ids(year):
    file = ROOT / f"data/raw/{year}_final_precinct_results.csv"
    if not file.exists():
        raise FileNotFoundError(f"First run: python scripts/diagnose_precinct_matching.py (missing {file})")
    with file.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        rows = csv.DictReader(handle)
        ids = {row["Precinct"].rsplit("-", 1)[-1] for row in rows
               if row["Race"] == "City of Seattle Mayor" and row["Precinct"].startswith("SEA ")}
    return ids


def main():
    p21, p25 = fetch_shapes(2021), fetch_shapes(2025)
    for year, polygons in ((2021, p21), (2025, p25)):
        missing = read_election_ids(year) - polygons.keys()
        if missing:
            raise ValueError(f"{year} boundaries missing election precincts: {sorted(missing)[:10]}")
    with (ROOT / "data/processed/seattle_mayor_precinct_panel_2021_2025.csv").open(encoding="utf-8", newline="") as f:
        stable_ids = {row["precinct_id"] for row in csv.DictReader(f)}
    old_ids = list(p21)
    old_polygons = [p21[pid] for pid in old_ids]
    tree = STRtree(old_polygons)
    result = []
    covered = 0
    stable_iou_low = []
    same_id_close = 0
    no_shared = 0
    for pid25, shape25 in p25.items():
        pieces = []
        intersection_total = 0.0
        for index in tree.query(shape25):
            pid21 = old_ids[int(index)]
            intersection = shape25.intersection(old_polygons[int(index)]).area
            if intersection <= 0:
                continue
            intersection_total += intersection
            pieces.append((pid21, intersection / shape25.area))
        coverage = intersection_total / shape25.area
        covered += coverage >= 0.99
        if pid25 not in p21:
            no_shared += 1
        else:
            both = shape25.intersection(p21[pid25]).area
            iou = both / (shape25.area + p21[pid25].area - both)
            same_id_close += iou >= 0.995
            if pid25 in stable_ids and iou < 0.995:
                stable_iou_low.append((pid25, round(iou, 6)))
        pieces.sort(key=lambda item: item[1], reverse=True)
        for pid21, fraction in pieces:
            result.append((pid25, pid21, round(fraction, 8)))
    output = CACHE / "overlap_2025_to_2021_by_area.csv"
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["precinct_id_2025", "precinct_id_2021", "fraction_of_2025_area"])
        writer.writerows(result)
    print(f"Precinct geometries: 2021 = {len(p21):,}; 2025 = {len(p25):,}")
    print(f"2025 precincts with >=99% of area covered by 2021 precincts: {covered:,} / {len(p25):,}")
    print(f"Same-ID precincts with >=99.5% geometric overlap (IoU): {same_id_close:,}")
    print(f"2025 precincts with no shared 2021 ID: {no_shared:,}")
    print(f"Previously labeled stable but with <99.5% overlap: {len(stable_iou_low)}")
    if stable_iou_low:
        print(f"Examples to investigate: {stable_iou_low[:8]}")
    print(f"Detailed local crosswalk: {output.relative_to(ROOT)}")
    print("This is AREA overlap only, not a completed population-weighted vote allocation.")


if __name__ == "__main__":
    main()
