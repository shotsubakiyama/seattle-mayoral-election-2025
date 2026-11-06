"""Compare 2025 Seattle primary and general precinct patterns with 2020 Census.

From the repository root, after precinct downloads / shapefiles are cached:
    python -m pip install -r requirements-analysis.txt
    python scripts/model_precinct_surprises.py

Produces a cross-validated (spatial group held-out) exploratory model,
figures, and an explanatory report. Correlations are NOT causal claims.
"""
import csv
import math
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Polygon as PlotPolygon
from matplotlib.collections import PatchCollection
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from diagnose_precinct_matching import ROOT, CERTIFIED_2025, read_results, windows_curl_download
from spatial_precinct_overlap import fetch_shapes

PRIMARY_CSV = ROOT / "data/raw/2025_primary_final_precinct_results.csv"
CENSUS_CSV = ROOT / "data/processed/block_group_to_2025_precinct_crosswalk.csv"
OUTPUT_CSV = ROOT / "data/processed/precinct_surprises_2025.csv"
FIG_DIR = ROOT / "reports/figures"
REPORT = ROOT / "reports/03_precinct_surprises_exploration.md"
PRIMARY_URL = "https://data.kingcounty.gov/api/v3/views/tsx2-ia8a/export.csv?accessType=DOWNLOAD"
PRIMARY_CERTIFIED = {"Bruce Harrell": 80043, "Katie Wilson": 98562}
ADMIN_TYPES = {"Registered Voters", "Times Counted", "Times Under Voted", "Times Over Voted", "Write-in"}
NUMERIC_FEATURES = ["primary_harrell_share", "primary_other_share", "vap_ratio", "occupancy_ratio", "log_pop_density"]


def validate_primary(path):
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        header = next(csv.reader(handle), [])
    if not {"Precinct", "Race", "CounterType", "SumOfCount"} <= set(header):
        raise ValueError(f"Invalid primary precinct CSV header: {header}")


def download_primary(path=PRIMARY_CSV):
    if path.exists() and path.stat().st_size:
        validate_primary(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    try:
        try:
            req = Request(PRIMARY_URL, headers={"User-Agent": "Seattle-Election-Research/1.0"})
            with urlopen(req, timeout=90) as incoming, partial.open("wb") as dest:
                while buf := incoming.read(1024 * 1024):
                    dest.write(buf)
        except OSError as first_error:
            partial.unlink(missing_ok=True)
            try:
                windows_curl_download(PRIMARY_URL, partial)
            except Exception as second_error:
                raise RuntimeError(
                    "Primary download failed using both Python and Windows curl. "
                    "Check network access; certificate verification has not been bypassed. "
                    f"Errors: {first_error}; {second_error}"
                ) from second_error
        validate_primary(partial)
        partial.replace(path)
        print("Downloaded King County's certified August 2025 primary precinct CSV")
    finally:
        partial.unlink(missing_ok=True)


def read_primary(path):
    """Sum mayoral candidate votes by numeric precinct ID; include other candidates."""
    precincts = defaultdict(lambda: defaultdict(int))
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["Race"].strip() != "City of Seattle Mayor":
                continue
            if row.get("CounterGroup", "Total").strip() != "Total":
                continue
            name = row["Precinct"].strip()
            if not name.startswith("SEA "):
                continue
            pid = name.rsplit("-", 1)[-1]
            if not pid.isdigit():
                raise ValueError(f"Unexpected primary precinct {name!r}")
            typ = row["CounterType"].strip()
            if typ in ADMIN_TYPES:
                continue
            precincts[pid][typ] += int(row["SumOfCount"].replace(",", ""))
    if not precincts:
        raise ValueError("No Seattle mayoral primary candidate results found")
    total = {name: sum(p.get(name, 0) for p in precincts.values()) for name in PRIMARY_CERTIFIED}
    if total != PRIMARY_CERTIFIED:
        raise ValueError(f"Primary finalist totals do not reconcile: {total}; expected {PRIMARY_CERTIFIED}")
    return precincts


def census_by_precinct(path):
    """Accumulate allocated 2020 Census block-group quantities per 2025 precinct."""
    columns = {"pop": "allocated_population_2020", "vap": "allocated_vap_2020",
               "housing": "allocated_housing_units_2020", "occupied": "allocated_occupied_housing_2020"}
    by_id = defaultdict(lambda: defaultdict(float))
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            pid = row["precinct_id"]
            for target, source in columns.items():
                by_id[pid][target] += float(row[source] or 0)
    return by_id


def build_table(general, primary, census, shapes, min_general=100, min_primary=40):
    """Build non-election Census features + primary political baseline, no general leakage."""
    data = []
    reasons = defaultdict(int)
    for pid, votes in general.items():
        if pid not in shapes or pid not in census:
            reasons["missing_geometry_or_census"] += 1
            continue
        h, w = (votes.get(k, 0) for k in PRIMARY_CERTIFIED)
        p = primary.get(pid, {})
        ph, pw = (p.get(k, 0) for k in PRIMARY_CERTIFIED)
        if h + w < min_general or ph + pw < min_primary:
            reasons["few_primary_or_general_votes"] += 1
            continue
        pop, vap, housing, occupied = (census[pid].get(k, 0) for k in ("pop", "vap", "housing", "occupied"))
        if pop < 10 or housing < 3 or occupied < 1 or not shapes[pid].area:
            reasons["insufficient_census_data"] += 1
            continue
        all_primary_named = sum(p.values())
        if all_primary_named < ph + pw:
            raise ValueError(f"Primary candidate votes inconsistent for {pid}")
        density = pop / (shapes[pid].area / 27878400)  # EPSG:2926: US survey feet
        if density <= 0:
            reasons["invalid_density"] += 1
            continue
        x, y = shapes[pid].representative_point().coords[0]
        record = {
            "precinct_id": pid,
            "general_votes": h + w,
            "primary_finalist_votes": ph + pw,
            "primary_harrell_share": ph / (ph + pw),
            "primary_other_share": (all_primary_named - ph - pw) / all_primary_named,
            "vap_ratio": min(1, max(0, vap / pop)),
            "occupancy_ratio": min(1, max(0, occupied / housing)),
            "log_pop_density": math.log1p(density),
            "actual_harrell_share": h / (h + w),
            "spatial_group": f"{int(x // 10000)}_{int(y // 10000)}",
        }
        data.append(record)
    return sorted(data, key=lambda r: int(r["precinct_id"])), dict(reasons)


def weighted_mae(observed, predicted, weights):
    return float(np.average(np.abs(observed - predicted), weights=weights))


def cross_validate(rows, features, folds=5):
    if len(rows) < 50:
        raise ValueError("Too few eligible precincts for cross-validation")
    x = np.array([[r[k] for k in features] for r in rows], dtype=float)
    y = np.array([r["actual_harrell_share"] for r in rows], dtype=float)
    weight = np.array([r["general_votes"] for r in rows], dtype=float)
    groups = np.array([r["spatial_group"] for r in rows])
    if len(set(groups)) < folds:
        raise ValueError("Too few geographic groups for spatial cross-validation")
    oof = np.full(len(rows), np.nan)
    for train, test in GroupKFold(n_splits=folds).split(x, y, groups):
        if set(groups[train]) & set(groups[test]):
            raise AssertionError("Spatial group leaked across a validation fold")
        scaler = StandardScaler().fit(x[train])
        model = Ridge(alpha=12.0)
        normalized_weights = weight[train] / np.mean(weight[train])
        model.fit(scaler.transform(x[train]), y[train], sample_weight=normalized_weights)
        oof[test] = np.clip(model.predict(scaler.transform(x[test])), 0, 1)
    if np.isnan(oof).any():
        raise AssertionError("Out-of-fold predictions missing")
    return oof, weighted_mae(y, oof, weight)


def polygons_of(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from polygons_of(part)


def render_figures(rows, predictions, shapes):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    actual = np.array([r["actual_harrell_share"] for r in rows]) * 100
    expected = np.array(predictions) * 100
    difference = actual - expected

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.scatter(expected, actual, s=14, alpha=.55, color="#476d85")
    ax.plot([0,100], [0,100], color="#333b46", linewidth=1.2, linestyle="--")
    ax.set(xlim=(0,100), ylim=(0,100), xlabel="Expected Harrell share (%), held-out precincts",
           ylabel="Actual Harrell share (%)", title="Which precincts defied expectations?")
    ax.text(.02,.98, "2025 general | primary baseline + 2020 Census context",
            transform=ax.transAxes, va="top", fontsize=10, color="#566675")
    ax.grid(color="#e8edf0", alpha=.7)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "precinct_surprises_scatter.svg")
    plt.close(fig)

    by_id = {r["precinct_id"]: d for r, d in zip(rows, difference)}
    patches, vals = [], []
    for pid, geom in shapes.items():
        for poly in polygons_of(geom):
            # Citywide map; one color per eligible precinct. Missing data stays light gray.
            patches.append(PlotPolygon(np.asarray(poly.exterior.coords), closed=True))
            vals.append(by_id.get(pid, np.nan))
    fig, ax = plt.subplots(figsize=(9, 10))
    cmap = plt.get_cmap("RdBu_r").with_extremes(bad="#e7ecf0")  # red: Harrell above expected
    collection = PatchCollection(patches, cmap=cmap, norm=TwoSlopeNorm(vmin=-20, vcenter=0, vmax=20),
                                 linewidth=.08, edgecolor="white")
    collection.set_array(np.ma.masked_invalid(np.array(vals)))
    ax.add_collection(collection)
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Seattle's electoral surprises | 2025", loc="left", fontsize=17, weight="bold")
    bar=fig.colorbar(collection, ax=ax, shrink=.68, fraction=.035, pad=.015, extend="both")
    bar.set_label("Actual minus expected Harrell share (percentage points)")
    fig.text(.05,.07,"Out-of-sample Ridge model: August primary + 2020 Census demographics. Gray = excluded precincts.",fontsize=9,color="#506070")
    fig.text(.05,.05,"Geographic patterns are descriptive; the model is not causal and estimates are imperfect.",fontsize=9,color="#506070")
    fig.savefig(FIG_DIR / "precinct_surprises_map.svg", bbox_inches="tight")
    plt.close(fig)


def write_results(rows, simple_preds, full_preds, simple_mae, full_mae, excluded):
    sorted_rows=[]
    for record, simple, predicted in zip(rows, simple_preds, full_preds):
        row = {**record, "expected_primary_only_pct":round(100*simple, 2),
               "expected_primary_plus_census_pct":round(100*predicted, 2),
               "actual_harrell_pct":round(100*record["actual_harrell_share"],2),
               "residual_pp":round(100*(record["actual_harrell_share"]-predicted),2)}
        sorted_rows.append(row)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        fieldnames=list(sorted_rows[0])
        writer=csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_rows)

    def format_outliers(candidates):
        return [f"| {r['precinct_id']} | {r['actual_harrell_pct']:.1f}% | "
                f"{r['expected_primary_plus_census_pct']:.1f}% | {r['residual_pp']:+.1f} pp | "
                f"{r['general_votes']:,} |" for r in candidates]
    pos=sorted(sorted_rows,key=lambda r:-r["residual_pp"])[:6]
    neg=sorted(sorted_rows,key=lambda r:r["residual_pp"])[:6]
    lines=[
        "# Where Seattle defied expectations (exploratory)","",
        "![Precinct-level expected vs actual results](figures/precinct_surprises_scatter.svg)","",
        "![Map of local voting surprises](figures/precinct_surprises_map.svg)","",
        f"Using **{len(rows):,}** eligible precincts, a basic primary-only baseline had a",
        f"spatially held-out weighted mean absolute error of **{simple_mae*100:.2f} percentage points**.",
        f"Adding three broad 2020 Census characteristics yielded **{full_mae*100:.2f} points**.",
        "Lower error is better. If the expanded model is worse, that is an important result:",
        "demographics did not improve out-of-sample predictions over the political baseline.","",
        "### Precincts where Harrell performed most above this baseline", "",
        "| Precinct | Actual | Expected | Difference | 2025 votes |","|---|---:|---:|---:|---:|",
        *format_outliers(pos),"",
        "### Precincts where Wilson performed most above this baseline","",
        "| Precinct | Actual Harrell | Expected Harrell | Difference | 2025 votes |","|---|---:|---:|---:|---:|",
        *format_outliers(neg),"",
        "### Method and cautions","",
        "- Expected share comes from **five-fold geographic-block cross-validation**, not a model fitted on the same precinct's outcome.",
        "- Primary predictor: Harrell's share among Harrell+Wilson **primary** votes, not the share among all primary candidates. We also include the share for other named primary candidates.",
        "- Additional variables: **2020** Census voting-age fraction, housing occupancy, and population density, allocated through the existing 2025 precinct crosswalk.",
        "- The extra variables describe **residents, not voters**. Changes in turnout, candidate choice, and neighborhood composition are not directly observed.",
        "- Geographic grouping uses 10,000-foot cells; nearby groups can still influence each other. Prediction errors are not statistical significance tests.",
        f"- Excluded precincts: {excluded}. These are not silently treated as zero votes.",
        "- Do not infer that voters switched candidates between August and November. Precinct-level aggregation cannot establish individual behavior.","",
        "### Reproduce","",
        "Run python scripts/model_precinct_surprises.py after installing requirements-analysis.txt.",
        "Sources: King County August 2025 primary (Socrata tsx2-ia8a), November 2025 general (rkie-6y8x), and 2020 Census block-group crosswalk.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return sorted_rows


def main():
    download_primary()
    primary=read_primary(PRIMARY_CSV)
    general_file=ROOT / "data/raw/2025_final_precinct_results.csv"
    if not general_file.exists():
        raise FileNotFoundError("First run python scripts/diagnose_precinct_matching.py")
    general=read_results(general_file)
    counts={k:sum(r.get(k,0) for r in general.values()) for k in CERTIFIED_2025}
    if counts != CERTIFIED_2025:
        raise ValueError(f"General election counts fail reconciliation: {counts}")
    census=census_by_precinct(CENSUS_CSV)
    shapes=fetch_shapes(2025)
    rows, excluded=build_table(general,primary,census,shapes)
    if len(rows)<750:
        raise ValueError(f"Only {len(rows)} eligible precincts; inspect missing primary/Census joins: {excluded}")
    baseline,mae_basic=cross_validate(rows,["primary_harrell_share","primary_other_share"])
    augmented,mae_full=cross_validate(rows,NUMERIC_FEATURES)
    render_figures(rows,augmented,shapes)
    write_results(rows,baseline,augmented,mae_basic,mae_full,excluded)
    print(f"Primary precincts: {len(primary):,}; general precincts: {len(general):,}")
    print(f"Eligible precincts: {len(rows):,}; exclusions: {excluded}")
    print(f"5-fold geographic-block weighted MAE, primary only: {mae_basic*100:.2f} pp")
    print(f"5-fold geographic-block weighted MAE, plus 2020 Census: {mae_full*100:.2f} pp")
    for r in sorted(rows,key=lambda z: z["precinct_id"])[:1]:
        print("Example precinct included:",r["precinct_id"])
    print("Generated reports/03_precinct_surprises_exploration.md and two SVG figures")
    print("Generated data/processed/precinct_surprises_2025.csv")


if __name__=="__main__":
    main()
