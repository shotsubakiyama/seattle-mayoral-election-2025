"""Explore precinct twins: similar August results and Census profiles, divergent November votes.

Run from repository root after model_precinct_surprises.py:
    python scripts/precinct_twins.py

Matching uses ONLY primary-election and 2020 Census variables. November votes
are used afterward to rank interesting contrasts. This is exploratory, not causal.
"""
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
MODEL_CSV = ROOT / "data/processed/precinct_surprises_2025.csv"
AREAS_CSV = ROOT / "data/processed/precinct_to_cra_crosswalk.csv"
PAIRS_CSV = ROOT / "data/processed/precinct_twins_2025.csv"
FIGURE = ROOT / "reports/figures/precinct_twins_2025.svg"
REPORT = ROOT / "reports/05_precinct_twins.md"

# Conservative, interpretable per-feature maximum differences.
# occupancy_ratio is NOT the renter/homeowner ratio.
CALIPERS = {
    "primary_harrell_share": .05,
    "primary_other_share": .10,
    "vap_ratio": .10,
    "occupancy_ratio": .12,
    "log_pop_density": math.log(2),
}
FEATURES = list(CALIPERS)


def load_data(path=MODEL_CSV):
    if not path.exists():
        raise FileNotFoundError("First run: python scripts/model_precinct_surprises.py")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    columns = set(FEATURES) | {
        "precinct_id", "general_votes", "actual_harrell_share",
        "expected_primary_only_pct", "expected_primary_plus_census_pct"
    }
    if not rows or not columns.issubset(rows[0]):
        raise ValueError("Precinct surprises CSV is empty or missing model columns")
    output, seen = [], set()
    for row in rows:
        pid = row["precinct_id"]
        if pid in seen:
            raise ValueError(f"Duplicate precinct: {pid}")
        seen.add(pid)
        r = {"precinct_id": pid, "general_votes": int(row["general_votes"])}
        for key in FEATURES + ["actual_harrell_share",
                                "expected_primary_only_pct",
                                "expected_primary_plus_census_pct"]:
            r[key] = float(row[key])
            if not math.isfinite(r[key]):
                raise ValueError(f"Invalid value in precinct {pid}: {key}")
        if r["general_votes"] <= 0 or not 0 <= r["actual_harrell_share"] <= 1:
            raise ValueError(f"Invalid voting data for {pid}")
        output.append(r)
    return output


def baseline_errors(rows):
    """All benchmarks use the same precincts and two-candidate vote weights."""
    weight = np.array([r["general_votes"] for r in rows], dtype=float)
    y = np.array([r["actual_harrell_share"] for r in rows])
    choices = {
        "raw_primary": np.array([r["primary_harrell_share"] for r in rows]),
        "trained_primary": np.array([r["expected_primary_only_pct"] / 100 for r in rows]),
        "trained_census": np.array([r["expected_primary_plus_census_pct"] / 100 for r in rows]),
    }
    return {k: float(100 * np.average(abs(y - pred), weights=weight))
            for k, pred in choices.items()}


def choose_pairs(rows, polygons, limit=10, min_votes=150, min_miles=1.0, feature_calipers=None):
    """Nearest neighbors use pre-November features exclusively.

    Compare November outcomes only after matching. Pair rankings are
    exploratory/extreme selection, not significance tests.
    """
    eligible = sorted(
        [r for r in rows if r["general_votes"] >= min_votes
         and r["precinct_id"] in polygons],
        key=lambda r: int(r["precinct_id"])
    )
    if len(eligible) < 3:
        raise ValueError("Too few precincts with sufficient votes and geometry")
    limits = feature_calipers if feature_calipers is not None else CALIPERS
    keys = list(limits)
    x = np.array([[r[k] for k in keys] for r in eligible], dtype=float)
    scales = np.array([limits[k] for k in keys], dtype=float)
    if (scales <= 0).any() or not np.isfinite(x).all():
        raise ValueError("Matching inputs must be finite with positive calipers")
    nearest = NearestNeighbors(n_neighbors=min(len(eligible), 200))
    nearest.fit(x / scales)
    dist, idx = nearest.kneighbors(x / scales)
    points = [polygons[r["precinct_id"]].representative_point() for r in eligible]
    candidates = {}
    for i, (neighbors, dists) in enumerate(zip(idx, dist)):
        for j, similarity in zip(neighbors, dists):
            j = int(j)
            if i == j or similarity > 1.5:
                continue
            key = (min(i, j), max(i, j))
            if key in candidates:
                continue
            delta = np.abs(x[i] - x[j])
            if np.any(delta > scales + 1e-12):
                continue
            miles = points[i].distance(points[j]) / 5280
            if miles < min_miles:
                continue
            a, b = eligible[key[0]], eligible[key[1]]
            november_gap = abs(a["actual_harrell_share"] - b["actual_harrell_share"]) * 100
            if november_gap < 8:
                continue
            candidates[key] = {
                "precinct_a": a["precinct_id"], "precinct_b": b["precinct_id"],
                "harrell_2025_a_pct": 100 * a["actual_harrell_share"],
                "harrell_2025_b_pct": 100 * b["actual_harrell_share"],
                "votes_a": a["general_votes"], "votes_b": b["general_votes"],
                "november_gap_pp": november_gap,
                "august_gap_pp": delta[0] * 100,
                "other_primary_gap_pp": delta[1] * 100,
                "voting_age_gap_pp": delta[2] * 100,
                "housing_occupancy_gap_pp": delta[3] * 100,
                "density_ratio": math.exp(delta[4]),
                "feature_distance": float(similarity),
                "straight_line_miles": miles,
                "selection_score": november_gap / (1 + .4 * float(similarity)),
            }
    ordered = sorted(candidates.values(), key=lambda p: (
        -p["selection_score"], -p["november_gap_pp"],
        int(p["precinct_a"]), int(p["precinct_b"])
    ))
    chosen, used = [], set()
    for pair in ordered:
        if pair["precinct_a"] in used or pair["precinct_b"] in used:
            continue
        chosen.append(pair)
        used.update((pair["precinct_a"], pair["precinct_b"]))
        if len(chosen) >= limit:
            break
    return chosen, {"eligible": len(eligible), "candidates": len(candidates)}


def area_names():
    with AREAS_CSV.open(encoding="utf-8-sig", newline="") as f:
        return {r["precinct_id"]: r["cra_name"] for r in csv.DictReader(f)}


def render_chart(pairs, areas):
    if not pairs:
        return
    fig, ax = plt.subplots(figsize=(12, max(6, len(pairs) * .75 + 2)))
    for index, pair in enumerate(pairs):
        low, high = sorted((pair["harrell_2025_a_pct"], pair["harrell_2025_b_pct"]))
        ax.plot([low, high], [index, index], lw=3, color="#a1aebb", zorder=1)
        ax.scatter(low, index, s=90, c="#347da8", zorder=2)
        ax.scatter(high, index, s=90, c="#c47a47", zorder=2)
        ax.text(101.5, index, f"{pair['november_gap_pp']:.1f} pp",
                va="center", weight="bold", fontsize=10)
    def label(p):
        a, b = p["precinct_a"], p["precinct_b"]
        return f"{a} ({areas.get(a, 'unlabeled')}) / {b} ({areas.get(b, 'unlabeled')})"
    ax.set_yticks(range(len(pairs)), labels=[label(p) for p in pairs], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("Harrell share of November two-candidate votes (%)")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.grid(axis="x", color="#e5eaee")
    ax.set_axisbelow(True)
    ax.set_title("Precinct Twins | Similar profiles, different votes",
                 loc="left", fontsize=16, weight="bold", pad=22)
    fig.text(.02, .015,
             "August 2025 primary + allocated 2020 Census define similarity; November 2025 results reveal the gap.",
             fontsize=9, color="#536779")
    fig.subplots_adjust(left=.43, right=.95, top=.89, bottom=.12)
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, format="svg")
    plt.close(fig)


def save_report(pairs, errors, counts):
    PAIRS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with PAIRS_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(pairs[0]) if pairs else
                                ["precinct_a", "precinct_b", "november_gap_pp"])
        writer.writeheader()
        writer.writerows(pairs)
    lines = [
        "# Precinct Twins: Similar on paper, different at the ballot box", "",
        "Exploratory case-finding, not evidence of why individuals voted differently.", "",
        "## First: does the predictive model add value?", "",
        "The error below is the vote-weighted mean absolute error, in percentage points,",
        "calculated on the same set of precincts. The fitted estimates are geographically held out.", "",
        "| Method | Weighted prediction error |", "|---|---:|",
        f"| Direct August primary finalist share (no training) | {errors['raw_primary']:.2f} pp |",
        f"| Fitted primary model | {errors['trained_primary']:.2f} pp |",
        f"| Fitted primary + 2020 Census model | {errors['trained_census']:.2f} pp |", "",
        "The direct primary baseline is intentionally uncalibrated for November's electorate.", "",
        "## Precinct Twins", "",
        f"Among {counts['eligible']:,} eligible precincts, {counts['candidates']:,} pairs met our",
        "demographic/primary-similarity and geographical-separation conditions.",
        f"Showing {len(pairs)} top-ranked pairs without reusing the same precinct.", "",
    ]
    if pairs:
        lines += ["![Comparison of November vote shares](figures/precinct_twins_2025.svg)", "",
                  "| Precinct pair | November Harrell share (A/B) | Difference | August finalist share gap | Density ratio |",
                  "|---|---|---:|---:|---:|"]
        for p in pairs:
            lines.append(
                f"| {p['precinct_a']} / {p['precinct_b']} | "
                f"{p['harrell_2025_a_pct']:.1f}% / {p['harrell_2025_b_pct']:.1f}% | "
                f"{p['november_gap_pp']:.1f} pp | {p['august_gap_pp']:.1f} pp | {p['density_ratio']:.2f}× |"
            )
    else:
        lines.append("No pairs passed all criteria. No matches have been fabricated.")
    lines += [
        "", "## Matching design and limitations", "",
        "- Five matching features, none from November: August Harrell share among finalists,",
        "  August share for other named candidates, and allocated 2020 Census voting-age fraction,",
        "  occupied-housing fraction, and population density.",
        "- Maximum matched gaps: 5 pp in August finalist vote share, 10 pp in other candidates,",
        "  10 pp in voting-age fraction, 12 pp in occupied-housing fraction, and roughly 2x density.",
        "- Additional combined-distance filter; >=150 November two-candidate votes each;",
        "  and >=1 straight-line mile between representative points inside precincts.",
        "- November vote-share gaps are ranked **after** matching; the extreme pairs are",
        "  selected examples, not random samples or statistically validated effects.",
        "- **Occupied housing fraction is NOT renter share, homeownership, or income.**",
        "  The Census quantities were geographically allocated, not directly observed for voters.",
        "- The pairs may differ substantially in unmeasured housing tenure, income,",
        "  race, educational attainment, campaign activity, or other local characteristics.",
        "- A precinct ID appears in at most one displayed pair; listed distances are straight-line.",
        "", "## Reproduce", "",
        "Run: python scripts/precinct_twins.py after model_precinct_surprises.py.", "",
        "Next: inspect the strongest pair locations and add targeted housing-tenure data",
        "before presenting any explanation of the divergence.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    from spatial_precinct_overlap import fetch_shapes
    rows = load_data()
    errors = baseline_errors(rows)
    polygons = fetch_shapes(2025)
    pairs, counts = choose_pairs(rows, polygons)
    save_report(pairs, errors, counts)
    render_chart(pairs, area_names())
    print("Direct August primary baseline MAE: " + f"{errors['raw_primary']:.2f} pp")
    print("Fitted primary-only spatial-CV MAE: " + f"{errors['trained_primary']:.2f} pp")
    print("Fitted primary+Census spatial-CV MAE: " + f"{errors['trained_census']:.2f} pp")
    print(f"Eligible precincts: {counts['eligible']:,}; candidate pairs: {counts['candidates']:,}")
    for p in pairs[:5]:
        print(f"  {p['precinct_a']} vs {p['precinct_b']}: November {p['november_gap_pp']:.1f} pp,"
              f" August {p['august_gap_pp']:.1f} pp, density {p['density_ratio']:.2f}x")
    print(f"Created {REPORT.relative_to(ROOT)} and {PAIRS_CSV.relative_to(ROOT)}")
    if pairs:
        print(f"Created {FIGURE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
