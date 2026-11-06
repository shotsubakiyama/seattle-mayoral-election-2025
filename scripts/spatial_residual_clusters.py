"""Spatial diagnostic for cross-validated 2025 mayoral election residuals.

Prerequisites: model_precinct_surprises.py has generated the local precinct CSV.
Run: python scripts/spatial_residual_clusters.py

Exploratory analysis; spatial clusters do not establish causal explanations.
"""
import csv
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as PlotPolygon, Patch
import numpy as np
from esda.moran import Moran, Moran_Local
from libpysal.weights import W
from shapely import STRtree

from spatial_precinct_overlap import ROOT, fetch_shapes

INPUT = ROOT / "data/processed/precinct_surprises_2025.csv"
OUTPUT = ROOT / "data/processed/precinct_residual_clusters_2025.csv"
FIGURE = ROOT / "reports/figures/precinct_residual_clusters.svg"
REPORT = ROOT / "reports/04_spatial_residual_clusters.md"
CRA = ROOT / "data/processed/precinct_to_cra_crosswalk.csv"
TYPES = {1: "Harrell-positive cluster", 2: "Wilson-positive local outlier",
         3: "Wilson-positive cluster", 4: "Harrell-positive local outlier"}
COLORS = {
    TYPES[1]: "#bb7140", TYPES[2]: "#8062aa",
    TYPES[3]: "#337fa5", TYPES[4]: "#d9b44d",
    "Not significant after FDR": "#e8ebee",
    "No eligible model result": "#fafafa",
    "No eligible neighbors": "#b2bac2",
}


def fdr_bh(pvalues):
    """Benjamini-Hochberg adjusted p-values in original input order."""
    p = np.asarray(pvalues, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid permutation p-values")
    order = np.argsort(p)
    result = np.empty(len(p))
    limit = 1.0
    for rank in range(len(p), 0, -1):
        index = order[rank-1]
        limit = min(limit, p[index] * len(p) / rank)
        result[index] = limit
    return result


def load_rows():
    if not INPUT.exists():
        raise FileNotFoundError("First run: python scripts/model_precinct_surprises.py")
    with INPUT.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows or len({r["precinct_id"] for r in rows}) != len(rows):
        raise ValueError("Empty or duplicate model output")
    for row in rows:
        row["residual_pp"] = float(row["residual_pp"])
        row["general_votes"] = int(row["general_votes"])
        if not np.isfinite(row["residual_pp"]):
            raise ValueError("Invalid model residual")
    return rows


def neighbors(ids, shapes, min_border=100):
    """Rook-style adjacent precincts sharing >=100 feet, not a corner touch."""
    polys = [shapes[i] for i in ids]
    index = STRtree(polys)
    links = {i: [] for i in ids}
    for n, poly in enumerate(polys):
        for j in index.query(poly):
            j = int(j)
            if j <= n:
                continue
            if poly.boundary.intersection(polys[j].boundary).length >= min_border:
                links[ids[n]].append(ids[j])
                links[ids[j]].append(ids[n])
    return links


def run_analysis(rows, shapes, permutations=9999):
    lookup = {r["precinct_id"]: r for r in rows}
    missing = lookup.keys() - shapes.keys()
    if missing:
        raise ValueError(f"Missing model polygons: {sorted(missing)[:8]}")
    ids_all = sorted(lookup, key=int)
    links = neighbors(ids_all, shapes)
    isolated = {k for k in ids_all if not links[k]}
    ids = [k for k in ids_all if k not in isolated]
    if len(ids) < 30:
        raise ValueError("Too few connected precincts")
    graph = {i: [j for j in links[i] if j not in isolated] for i in ids}
    w = W(graph, id_order=ids, silence_warnings=True)
    y = np.array([lookup[i]["residual_pp"] for i in ids])
    if np.std(y) == 0:
        raise ValueError("All residuals identical")
    np.random.seed(2026)  # deterministic global permutation test
    global_moran = Moran(y, w, permutations=permutations)
    local = Moran_Local(y, w, permutations=permutations,
                        seed=2026, n_jobs=1, keep_simulations=False)
    adjusted = fdr_bh(local.p_sim)
    found = {}
    for pos, i in enumerate(ids):
        label = TYPES[int(local.q[pos])] if adjusted[pos] <= .05 else "Not significant after FDR"
        found[i] = {
            "cluster": label, "neighbors": len(graph[i]),
            "local_i": float(local.Is[pos]), "p_perm": float(local.p_sim[pos]),
            "q_fdr": float(adjusted[pos]),
        }
    for i in isolated:
        found[i] = {"cluster": "No eligible neighbors", "neighbors": 0,
                    "local_i": "", "p_perm": "", "q_fdr": ""}
    return found, float(global_moran.I), float(global_moran.p_sim), len(ids), len(isolated)


def iter_polygons(g):
    if g.geom_type == "Polygon":
        yield g
    elif hasattr(g, "geoms"):
        for part in g.geoms:
            yield from iter_polygons(part)


def make_map(shapes, labels):
    polygons, colors = [], []
    for pid, shape in shapes.items():
        c = COLORS[labels[pid]["cluster"]] if pid in labels else COLORS["No eligible model result"]
        for poly in iter_polygons(shape):
            polygons.append(PlotPolygon(np.asarray(poly.exterior.coords), closed=True))
            colors.append(c)
    fig, ax = plt.subplots(figsize=(9.5, 10))
    ax.add_collection(PatchCollection(polygons, facecolor=colors,
                                      edgecolor="white", linewidth=.08))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("Are Seattle's electoral surprises geographically clustered?",
                 loc="left", fontsize=16, weight="bold")
    order = [TYPES[1], TYPES[3], TYPES[2], TYPES[4],
             "Not significant after FDR", "No eligible neighbors", "No eligible model result"]
    fig.legend(handles=[Patch(facecolor=COLORS[k], label=k) for k in order],
               loc="lower center", bbox_to_anchor=(.5, .06), frameon=False,
               ncol=2, fontsize=9)
    fig.text(.06, .018, "Local Moran's I | 9,999 permutations | Benjamini-Hochberg FDR q <= 0.05 | 100-ft shared border",
             fontsize=8.5, color="#526273")
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, format="svg", bbox_inches="tight")
    plt.close(fig)


def save_results(rows, found, global_i, global_p, tested, islands):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["precinct_id", "residual_pp", "general_votes",
                    "cluster", "neighbors", "local_i", "p_perm", "q_fdr"])
        writer.writeheader()
        for row in rows:
            i = row["precinct_id"]
            writer.writerow({**{k: row[k] for k in ("precinct_id", "residual_pp", "general_votes")},
                             **found[i]})
    counter = Counter(r["cluster"] for r in found.values())
    with CRA.open(newline="", encoding="utf-8-sig") as f:
        areas = {r["precinct_id"]: r["cra_name"] for r in csv.DictReader(f)}
    interesting = [(i, value) for i, value in found.items() if value["cluster"] in TYPES.values()]
    by_id = {r["precinct_id"]: r for r in rows}
    interesting.sort(key=lambda pair: -abs(by_id[pair[0]]["residual_pp"]))
    lines = [
        "# Where Seattle's electoral surprises form geographic clusters", "",
        "![Local Moran cluster map](figures/precinct_residual_clusters.svg)", "",
        "Exploratory diagnostics only: a cluster of model errors is not a causal explanation.",
        f"Global Moran's I: **{global_i:.3f}**, permutation p-value **{global_p:.4f}**",
        f"({tested:,} connected eligible precincts; {islands} eligible isolates).", "",
        "## Local results (5% FDR-adjusted)", "",
    ]
    for typ in TYPES.values():
        lines.append(f"- {typ}: {counter[typ]} precincts")
    lines += [
        f"- Not significant after adjustment: {counter['Not significant after FDR']} precincts", "",
        "## Strongest local findings", "",
        "| Precinct | Community area (where available) | Residual | Local pattern | FDR q |",
        "|---|---|---:|---|---:|",
    ]
    if interesting:
        for i, value in interesting[:12]:
            lines.append(f"| {i} | {areas.get(i, 'Unlabeled')} | "
                         f"{by_id[i]['residual_pp']:+.1f} pp | {value['cluster']} | {value['q_fdr']:.4f} |")
    else:
        lines.append("| None | — | — | No local tests survived FDR correction | — |")
    lines += [
        "", "## Cautions", "",
        "- Residuals are observed minus held-out predicted two-candidate Harrell shares, not raw election results.",
        "- Rook-style neighbors share at least 100 feet of precinct border; corner-only contacts do not qualify.",
        "- Local Moran's I uses 9,999 conditional permutations. Local p-values are corrected for multiple comparisons using Benjamini-Hochberg FDR.",
        "- Isolated precincts and those excluded by the earlier prediction model are not assigned a local cluster.",
        "- Statistical clustering does not identify a cause. Model misspecification or omitted geography may generate structure.",
        "- Residuals have unequal precision because precincts differ in voter counts; this exploratory run does not account for that in spatial weights.",
        "- Areas of large polygons on the map are not proportional to their voting populations.", "",
        "## Reproduce", "",
        "Run: python scripts/spatial_residual_clusters.py",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return counter


def main():
    rows = load_rows()
    polygons = fetch_shapes(2025)
    labels, value, pvalue, tested, islands = run_analysis(rows, polygons)
    make_map(polygons, labels)
    counts = save_results(rows, labels, value, pvalue, tested, islands)
    print(f"Global Moran I: {value:.3f}, permutation p={pvalue:.4f}")
    print(f"Spatially tested: {tested}; isolated: {islands}")
    for label, count in counts.items():
        print(f"{label}: {count}")
    print("Created reports/04_spatial_residual_clusters.md and reports/figures/precinct_residual_clusters.svg")


if __name__ == "__main__":
    main()
