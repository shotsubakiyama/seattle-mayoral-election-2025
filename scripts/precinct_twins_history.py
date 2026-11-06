"""Stricter historical precinct-twin check (2021 + Aug 2025 + 2020 Census).

Run: python scripts/precinct_twins_history.py

Requires the existing model CSV and 2025 precinct polygons. A 'historical
twin' is similar *before* November 2025, with a stable 2021 boundary.
The selected largest November gaps are exploratory, not causal estimates.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from precinct_twins import CALIPERS, area_names, choose_pairs, load_data
from spatial_precinct_overlap import ROOT, fetch_shapes

PANEL = ROOT / "data/processed/seattle_mayor_precinct_panel_2021_2025.csv"
OUTPUT = ROOT / "data/processed/precinct_twins_history_2025.csv"
FIGURE = ROOT / "reports/figures/precinct_twins_history_2025.svg"
REPORT = ROOT / "reports/06_historical_precinct_twins.md"
HISTORY_CALIPERS = {**CALIPERS, "historical_harrell_share": .05}


def load_historical_panel(path=PANEL, minimum_votes_2021=100):
    """Use only already-validated stable-boundary 2021/2025 precincts."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    found = {}
    for r in rows:
        if r["stable_boundary"] != "True":
            continue
        pid = r["precinct_id"]
        votes = int(r["two_candidate_votes_2021"])
        share = float(r["harrell_share_2021"])
        if not 0 <= share <= 1:
            raise ValueError(f"Invalid 2021 Harrell share for {pid}")
        if pid in found:
            raise ValueError(f"Duplicate stable 2021 precinct {pid}")
        if votes >= minimum_votes_2021:
            found[pid] = {"historical_harrell_share": share, "votes_2021": votes}
    if not found:
        raise ValueError("No eligible 2021 precincts; check the historical panel")
    return found


def assemble_history(rows, historical):
    joined = []
    for row in rows:
        record = historical.get(row["precinct_id"])
        if record is not None:
            joined.append({**row, **record})
    return joined


def enrich_pairs(pairs, by_id):
    enriched = []
    for pair in pairs:
        a, b = by_id[pair["precinct_a"]], by_id[pair["precinct_b"]]
        p = dict(pair)
        p.update({
            "share_2021_a_pct": 100 * a["historical_harrell_share"],
            "share_2021_b_pct": 100 * b["historical_harrell_share"],
            "gap_2021_pp": 100 * abs(a["historical_harrell_share"] - b["historical_harrell_share"]),
            "share_primary_a_pct": 100 * a["primary_harrell_share"],
            "share_primary_b_pct": 100 * b["primary_harrell_share"],
            "votes_2021_a": a["votes_2021"],
            "votes_2021_b": b["votes_2021"],
        })
        if p["gap_2021_pp"] > 5.0001 or p["august_gap_pp"] > 5.0001:
            raise AssertionError("Historical twin violates pre-November calipers")
        enriched.append(p)
    return enriched


def plot_gap_progression(pairs, names):
    if not pairs:
        return
    n = len(pairs)
    fig, ax = plt.subplots(figsize=(11.5, max(5.2, n * .63 + 2.1)))
    offsets = [(-.22, "#9ca9b4", "2021 general"), (0, "#4b88a9", "2025 primary"),
               (.22, "#d17a41", "2025 general")]
    x = np.arange(n)
    for offset, color, legend in offsets:
        vals = [
            p["gap_2021_pp"] if legend == "2021 general" else
            p["august_gap_pp"] if legend == "2025 primary" else
            p["november_gap_pp"] for p in pairs
        ]
        ax.barh(x+offset, vals, height=.20, color=color, label=legend)
        if legend == "2025 general":
            for i, value in enumerate(vals):
                ax.text(value+.55, i+offset, f"{value:.1f} pp", fontsize=9,
                        va="center", color="#394958", weight="bold")
    ax.set_yticks(x)
    ax.set_yticklabels([f"{p['precinct_a']} / {p['precinct_b']}" for p in pairs], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Absolute difference in Harrell two-candidate vote share (percentage points)")
    max_gap = max(p["november_gap_pp"] for p in pairs)
    ax.set_xlim(0, max(30, max_gap+7))
    ax.set_title("Historical Precinct Twins | Did the divide emerge in November?",
                 loc="left", weight="bold", fontsize=15, pad=18)
    ax.grid(axis="x", color="#e8edf0")
    ax.set_axisbelow(True)
    ax.spines[["right", "top", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.legend(loc="lower right", frameon=False, ncol=3, fontsize=9)
    fig.text(.04, .015,
             "Caution: 2021 Harrell vs. Gonzalez; 2025 primary/general Harrell vs. Wilson. Primary shares are among finalists only.",
             fontsize=8.5, color="#536779")
    fig.subplots_adjust(left=.19, right=.96, top=.89, bottom=.14)
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, format="svg")
    plt.close(fig)


def write_report(pairs, counts, eligible_count):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    columns = list(pairs[0]) if pairs else [
        "precinct_a", "precinct_b", "gap_2021_pp", "august_gap_pp", "november_gap_pp"
    ]
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(pairs)
    lines = [
        "# Historical Precinct Twins: Were they already different in 2021?", "",
        "The earlier Precinct Twins exploration matched August 2025 voting and three",
        "basic 2020 Census attributes. Its largest pairs looked surprising, but some",
        "had large vote-share differences in 2021. This is a stricter sensitivity check.", "",
        "Here, a pair must also have a **2021 Harrell two-candidate share within five",
        "percentage points**. Both precinct boundaries must be stable between",
        "2021 and 2025, with at least 100 candidate votes in 2021. Matching also",
        "requires similar August 2025 results and 2020 Census features.", "",
        f"Eligible after stable-history restriction: **{eligible_count:,}** precincts.",
        f"Candidate pairs meeting all matching conditions: **{counts['candidates']:,}**.",
        f"Displayed pairs with no precinct repeated: **{len(pairs)}**.", "",
    ]
    if pairs:
        lines += [
            "![Historical precinct twin gaps across elections](figures/precinct_twins_history_2025.svg)", "",
            "| Precincts | 2021 share gap | Aug 2025 gap | Nov 2025 gap | Votes (A/B) |",
            "|---|---:|---:|---:|---:|",
        ]
        for p in pairs:
            lines.append(
                f"| {p['precinct_a']} / {p['precinct_b']} | {p['gap_2021_pp']:.1f} pp | "
                f"{p['august_gap_pp']:.1f} pp | **{p['november_gap_pp']:.1f} pp** | "
                f"{p['votes_a']:,}/{p['votes_b']:,} |"
            )
    else:
        lines.append("No pairs pass every criterion. Do not loosen thresholds solely to manufacture findings.")
    lines += [
        "", "## Interpretation", "",
        "A large November gap despite similar historical and primary vote shares",
        "is a candidate for investigation, **not** evidence of persuasion or voter",
        "switching. The 2021 election had a different opponent and electorate.",
        "The primary share uses Harrell versus Wilson votes (not all primary candidates).",
        "These pairs are selected after seeing the November gap, so the differences",
        "are extreme by design and should not be treated as hypothesis-test results.", "",
        "The Census crosswalk supplies population density, voting-age fraction,",
        "and housing occupancy; **it does not include income, educational attainment,",
        "or homeowner/renter tenure**. A historical twin is not a demographic twin",
        "in those important respects.", "",
        "## Next question", "",
        "After reviewing the top pairs on a map, check housing tenure or",
        "other independent pre-election characteristics before proposing an explanation.", "",
        "## Reproduce", "",
        "Run: python scripts/precinct_twins_history.py after precinct_twins.py.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")


def main():
    rows = load_data()
    historical = load_historical_panel()
    joined = assemble_history(rows, historical)
    if len(joined) < 500:
        raise ValueError(f"Only {len(joined)} eligible precincts joined to 2021 results")
    polygons = fetch_shapes(2025)
    matches, counts = choose_pairs(joined, polygons, feature_calipers=HISTORY_CALIPERS)
    result = enrich_pairs(matches, {r["precinct_id"]: r for r in joined})
    plot_gap_progression(result, area_names())
    write_report(result, counts, len(joined))
    print(f"Eligible precincts with validated 2021 history: {len(joined):,}")
    print(f"Matching candidates with 2021 + August + Census similarity: {counts['candidates']:,}")
    print(f"Displayed unique pairs: {len(result)}")
    for row in result[:5]:
        print(f"  {row['precinct_a']} vs {row['precinct_b']}: 2021 {row['gap_2021_pp']:.1f} pp, "
              f"August {row['august_gap_pp']:.1f} pp, November {row['november_gap_pp']:.1f} pp")
    print(f"Created {REPORT.relative_to(ROOT)} and {OUTPUT.relative_to(ROOT)}")
    if result:
        print(f"Created {FIGURE.relative_to(ROOT)}")


if __name__=="__main__":
    main()
