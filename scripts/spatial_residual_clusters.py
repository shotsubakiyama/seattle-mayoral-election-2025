"""Dependency-light spatial diagnostic for 2025 mayoral prediction errors.

Prerequisites: model_precinct_surprises.py has generated the local precinct CSV.
Run: python scripts/spatial_residual_clusters.py

Uses NumPy/SciPy/Shapely rather than PySAL/GeoPandas/GDAL for Windows ARM64.
Global and local Moran-style permutation tests, not byte-identical PySAL output.
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
from scipy.sparse import csr_matrix
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


def draw_without_replacement(rng, population_size, group_size, samples):
    """Independent uniform ordered samples without replacement.

    Reject rows containing repeated indices. This keeps local conditional
    permutations exact while avoiding millions of Python-level sample calls.
    """
    if not 0 < group_size <= population_size or samples < 1:
        raise ValueError("Impossible neighbor sampling request")
    draws = rng.integers(population_size, size=(samples, group_size), dtype=np.int32)
    if group_size > 1:
        while True:
            duplicates = np.zeros(samples, dtype=bool)
            for j in range(1, group_size):
                duplicates |= np.any(draws[:, j, None] == draws[:, :j], axis=1)
            if not duplicates.any():
                break
            draws[duplicates] = rng.integers(
                population_size, size=(duplicates.sum(), group_size), dtype=np.int32)
    return draws


def permutation_moran(values, graph, ids, permutations=9999, seed=2026):
    """Global Moran's I and local conditional Monte Carlo tests.

    Row-standardized adjacency. Local permutations fix the focal precinct
    and sample its neighbors without replacement among all other precincts.
    Two-sided centered p-values are FDR-corrected across all local tests.
    """
    if permutations < 99:
        raise ValueError("At least 99 permutations required")
    n = len(ids)
    if n < 30:
        raise ValueError("Too few connected precincts")
    z = np.asarray(values, dtype=float)
    if z.shape != (n,) or not np.isfinite(z).all():
        raise ValueError("Invalid residual vector")
    z = z - z.mean()
    sum_squares = float(z @ z)
    if sum_squares <= 0:
        raise ValueError("All residuals identical")
    denom = sum_squares / (n - 1)
    position = {pid: idx for idx, pid in enumerate(ids)}
    lengths = np.array([len(graph[pid]) for pid in ids], dtype=int)
    if not lengths.all() or lengths.max() >= n:
        raise ValueError("Invalid adjacency graph")
    rows = np.repeat(np.arange(n), lengths)
    cols = np.array([position[j] for pid in ids for j in graph[pid]], dtype=int)
    weights = np.repeat(1.0 / lengths, lengths)
    matrix = csr_matrix((weights, (rows, cols)), shape=(n, n))
    lag = np.asarray(matrix @ z)
    global_i = float(z @ lag / sum_squares)
    local_i = z * lag / denom

    rng = np.random.default_rng(seed)
    global_null = np.empty(permutations)
    for j in range(permutations):
        shuffled = rng.permutation(z)
        global_null[j] = shuffled @ (matrix @ shuffled) / sum_squares
    global_center = float(global_null.mean())
    global_p = float((1 + np.count_nonzero(
        np.abs(global_null - global_center) >= abs(global_i - global_center)
    )) / (permutations + 1))

    local_p = np.empty(n)
    for i, group_size in enumerate(lengths):
        drawn = draw_without_replacement(rng, n - 1, int(group_size), permutations)
        drawn += drawn >= i  # exclude the fixed focal precinct
        simulated = z[i] * z[drawn].mean(axis=1) / denom
        center = float(simulated.mean())
        local_p[i] = (1 + np.count_nonzero(
            np.abs(simulated - center) >= abs(local_i[i] - center)
        )) / (permutations + 1)

    adjusted = fdr_bh(local_p)
    quadrant = np.where(z >= 0, np.where(lag >= 0, 1, 4),
                        np.where(lag >= 0, 2, 3))
    return global_i, global_p, local_i, local_p, adjusted, quadrant


def run_analysis(rows, shapes, permutations=9999):
    lookup = {r["precinct_id"]: r for r in rows}
    missing = lookup.keys() - shapes.keys()
    if missing:
        raise ValueError(f"Missing model polygons: {sorted(missing)[:8]}")
    ids_all = sorted(lookup, key=int)
    links = neighbors(ids_all, shapes)
    isolated = {pid for pid in ids_all if not links[pid]}
    ids = [pid for pid in ids_all if pid not in isolated]
    graph = {pid: [j for j in links[pid] if j not in isolated] for pid in ids}
    y = np.array([lookup[pid]["residual_pp"] for pid in ids], dtype=float)
    global_i, global_p, local_i, local_p, adjusted, quadrant = permutation_moran(
        y, graph, ids, permutations=permutations)
    found = {}
    for pos, pid in enumerate(ids):
        label = TYPES[int(quadrant[pos])] if adjusted[pos] <= .05 else "Not significant after FDR"
        found[pid] = {
            "cluster": label, "neighbors": len(graph[pid]),
            "local_i": float(local_i[pos]), "p_perm": float(local_p[pos]),
            "q_fdr": float(adjusted[pos]),
        }
    for pid in isolated:
        found[pid] = {
            "cluster": "No eligible neighbors", "neighbors": 0,
            "local_i": "", "p_perm": "", "q_fdr": "",
        }
    return found, global_i, global_p, len(ids), len(isolated)

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
    fig.text(.06, .018, "Moran-style local tests | 9,999 permutations | Benjamini-Hochberg FDR q <= 0.05 | 100-ft shared border",
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
        "- NumPy/SciPy Moran-style global and local statistics use 9,999 Monte Carlo permutations. The global test shuffles all residuals; local tests keep the focal precinct fixed and draw neighbors without replacement. Two-sided centered p-values are corrected with Benjamini-Hochberg FDR. This implementation is independent of PySAL and does not reproduce its exact pseudo-p convention.",
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
