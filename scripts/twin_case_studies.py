"""Compare three meaningful Historical Precinct Twins with readable context.

Run: python scripts/twin_case_studies.py
Uses existing processed CSVs; no new dependencies or downloads.

Produces: reports/07_twin_case_studies.md
          reports/figures/twin_case_studies.svg

This is exploratory, not evidence of individual voter movement or causality.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from spatial_precinct_overlap import ROOT

MODEL = ROOT / "data/processed/precinct_surprises_2025.csv"
PANEL = ROOT / "data/processed/seattle_mayor_precinct_panel_2021_2025.csv"
TWINS = ROOT / "data/processed/precinct_twins_history_2025.csv"
AREAS = ROOT / "data/processed/precinct_to_cra_crosswalk.csv"
REPORT = ROOT / "reports/07_twin_case_studies.md"
FIGURE = ROOT / "reports/figures/twin_case_studies.svg"

# Prioritize a comparison within West Seattle, then two cross-city contrasts.
CASES = [
    ("1246", "1464", "Two parts of West Seattle"),
    ("1449", "1754", "West Seattle and Queen Anne"),
    ("1639", "2252", "South Beacon Hill and Ravenna"),
]


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run precinct_twins_history.py first")
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def prepare_cases(model_rows, panel_rows, twin_rows, areas, selected=CASES):
    model = {r["precinct_id"]: r for r in model_rows}
    historical = {r["precinct_id"]: r for r in panel_rows}
    labels = {r["precinct_id"]: r["cra_name"] for r in areas}
    valid_pairs = {frozenset([r["precinct_a"], r["precinct_b"]]) for r in twin_rows}
    out = []
    for a, b, description in selected:
        if frozenset([a, b]) not in valid_pairs:
            raise ValueError(f"Pair {a}/{b} not found in validated historical twins output")
        if a not in model or b not in model or a not in historical or b not in historical:
            raise ValueError(f"Missing input for pair {a}/{b}")
        ends = []
        for pid in (a, b):
            current = model[pid]
            prior = historical[pid]
            if prior["stable_boundary"] != "True":
                raise ValueError(f"Nonstable 2021 precinct {pid}")
            percentages = [
                100 * float(prior["harrell_share_2021"]),
                100 * float(current["primary_harrell_share"]),
                100 * float(current["actual_harrell_share"]),
            ]
            turnout = [
                100 * float(prior["turnout_2021"]),
                100 * float(prior["turnout_2025"]),
            ]
            if not all(0 <= x <= 100 for x in percentages + turnout):
                raise ValueError(f"Invalid voting percentages for {pid}")
            ends.append({
                "id": pid, "area": labels.get(pid, "Unlabeled"),
                "shares": percentages, "turnout": turnout,
                "general_votes": int(current["general_votes"]),
                "primary_finalist_votes": int(current["primary_finalist_votes"]),
                "votes_2021": int(prior["two_candidate_votes_2021"]),
            })
        gap = [abs(x-y) for x, y in zip(ends[0]["shares"], ends[1]["shares"])]
        if gap[0] > 5.01 or gap[1] > 5.01 or gap[2] < 8:
            raise ValueError(f"Unexpected matching gaps for pair {a}/{b}: {gap}")
        out.append({"a": ends[0], "b": ends[1], "gap": gap, "description": description})
    return out


def draw_cases(cases, destination=FIGURE):
    fig, axes = plt.subplots(len(cases), 1, figsize=(11, 11), sharex=True)
    if len(cases) == 1:
        axes = [axes]
    colors = ("#31759b", "#ce7840")
    for ax, pair in zip(axes, cases):
        left, right = pair["a"], pair["b"]
        for item, color in zip((left, right), colors):
            ax.plot([0, 1, 2], item["shares"], "-o", linewidth=2.5, markersize=7,
                    color=color, label=f"{item['id']} | {item['area']}")
            ax.text(2.07, item["shares"][2], f"{item['shares'][2]:.1f}%",
                    va="center", fontsize=10, weight="bold", color=color)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_ylabel("Harrell share (%)")
        ax.set_xlim(-.1, 2.45)
        ax.grid(axis="y", color="#e4ebef")
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_title(
            f"{pair['description']} | November difference {pair['gap'][2]:.1f} pp",
            loc="left", fontsize=12, weight="bold")
        ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=2)
    axes[-1].set_xticks([0, 1, 2], [
        "2021 general\n(vs. González)",
        "August 2025 primary\n(vs. Wilson only)",
        "November 2025 general\n(vs. Wilson)"
    ])
    fig.suptitle("Historical precinct twins | Similar beginnings, different Novembers",
                 x=.09, y=.99, ha="left", fontsize=16, weight="bold")
    fig.text(.09, .015,
             "Vote shares compare different electorates and, in 2021, a different opponent. Lines describe aggregate precinct shares, not voter switching.",
             fontsize=9, color="#576b7d")
    fig.subplots_adjust(left=.09, right=.96, top=.92, bottom=.11, hspace=.45)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, format="svg", bbox_inches="tight")
    plt.close(fig)


def write_report(cases, destination=REPORT):
    lines = [
        "# Historical precinct twins: Three contrasts worth investigating", "",
        "Three pairs matched closely on Harrell's 2021 two-candidate share,",
        "his August 2025 finalist share, and selected 2020 Census attributes,",
        "but differed substantially in November 2025.", "",
        "![Three selected historical twin comparisons](figures/twin_case_studies.svg)", "",
        "## Case overview", "",
        "| Pair | Neighborhoods | 2021 gap | August gap | November gap |",
        "|---|---|---:|---:|---:|",
    ]
    for case in cases:
        a, b = case["a"], case["b"]
        gaps = case["gap"]
        lines.append(
            f"| {a['id']} / {b['id']} | {a['area']} / {b['area']} | "
            f"{gaps[0]:.1f} pp | {gaps[1]:.1f} pp | **{gaps[2]:.1f} pp** |"
        )
    for case in cases:
        a, b = case["a"], case["b"]
        lines += [
            "", f"## {case['description']} ({a['id']} vs. {b['id']})", "",
            f"Harrell's November share was **{a['shares'][2]:.1f}%** in {a['area']} "
            f"and **{b['shares'][2]:.1f}%** in {b['area']}, a "
            f"**{case['gap'][2]:.1f}-point difference**. His 2021 shares were "
            f"{a['shares'][0]:.1f}% and {b['shares'][0]:.1f}%; "
            f"the August finalist-only share gap was {case['gap'][1]:.1f} points.", "",
            f"**Participation context:** November turnout was {a['turnout'][1]:.1f}% "
            f"versus {b['turnout'][1]:.1f}%; the corresponding 2021 turnout rates were "
            f"{a['turnout'][0]:.1f}% and {b['turnout'][0]:.1f}%. "
            "Turnout differences do not by themselves explain candidate preference.", "",
            f"November votes for the two finalists: {a['general_votes']:,} versus "
            f"{b['general_votes']:,}; August finalist votes: "
            f"{a['primary_finalist_votes']:,} versus {b['primary_finalist_votes']:,}.", "",
        ]
    lines += [
        "## How to interpret these examples", "",
        "- The pairs were selected **because their November outcomes diverged** among",
        "  many eligible matches. They are illustrative, not statistical discoveries.",
        "- The 2021 opponent was Lorena González; August 2025 percentages use only",
        "  votes for Harrell and Wilson, not all candidates on the primary ballot.",
        "- The Census similarity check does **not** include renter share, income,",
        "  educational attainment, or race; matching cannot rule out those differences.",
        "- Changing turnout or composition may matter, but these aggregate percentages",
        "  cannot identify individual-level switching or causal mechanisms.", "",
        "## Next research step", "",
        "Investigate the local geography and housing context of the West Seattle pair",
        "first, then test whether the same contrast recurs among more matched precincts.", "",
        "Reproduce with: python scripts/twin_case_studies.py",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines)+"\n", encoding="utf-8")


def main():
    cases = prepare_cases(load_csv(MODEL), load_csv(PANEL),
                          load_csv(TWINS), load_csv(AREAS))
    draw_cases(cases)
    write_report(cases)
    for case in cases:
        a, b = case["a"], case["b"]
        print(f"{a['id']} ({a['area']}) vs {b['id']} ({b['area']}): "
              f"2021 gap {case['gap'][0]:.1f} pp, "
              f"Aug gap {case['gap'][1]:.1f} pp, "
              f"Nov gap {case['gap'][2]:.1f} pp")
    print(f"Created {REPORT.relative_to(ROOT)}")
    print(f"Created {FIGURE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
