"""Rank neighboring 2025 Seattle precincts by differences in Harrell vote share.

Run: python scripts/political_fault_lines.py
Requires raw results and 2025 polygons from the preceding diagnostics.
"""
import csv
from html import escape
from pathlib import Path
from shapely import STRtree

from diagnose_precinct_matching import CERTIFIED_2025, read_results
from spatial_precinct_overlap import ROOT, fetch_shapes

OUT_CSV = ROOT / "data/processed/political_fault_lines_2025.csv"
OUT_SVG = ROOT / "reports/figures/political_fault_lines.svg"
OUT_MD = ROOT / "reports/01_political_fault_lines.md"


def candidate_votes(votes, precinct):
    row = votes.get(precinct, {})
    h = row.get("Bruce Harrell", 0)
    w = row.get("Katie Wilson", 0)
    return h, w


def find_fault_lines(polygons, votes, min_votes=100, min_border_feet=100):
    """Rank only pairs sharing meaningful boundary length, not point-only contact."""
    ids = sorted(polygons, key=int)
    shapes = [polygons[p] for p in ids]
    tree = STRtree(shapes)
    results = []
    for i, a in enumerate(shapes):
        aid = ids[i]
        ha, wa = candidate_votes(votes, aid)
        na = ha + wa
        if na < min_votes:
            continue
        for index in tree.query(a):
            j = int(index)
            if j <= i:
                continue
            bid = ids[j]
            hb, wb = candidate_votes(votes, bid)
            nb = hb + wb
            if nb < min_votes:
                continue
            border = a.boundary.intersection(shapes[j].boundary).length
            if border < min_border_feet:
                continue
            share_a = 100 * ha / na
            share_b = 100 * hb / nb
            results.append({
                "precinct_a": aid, "precinct_b": bid,
                "harrell_share_a_pct": round(share_a, 3),
                "harrell_share_b_pct": round(share_b, 3),
                "difference_pp": round(abs(share_a - share_b), 3),
                "votes_a": na, "votes_b": nb,
                "shared_border_ft": round(border, 1),
            })
    return sorted(results, key=lambda r: (-r["difference_pp"], -r["shared_border_ft"]))


def render_figure(rows):
    top = rows[:10]
    if not top:
        raise ValueError("No qualifying neighboring pairs found")
    height = 185 + 52 * len(top)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 {height}" role="img" aria-label="Largest adjacent precinct vote-share differences">',
        '<style>text{font-family:Arial,sans-serif;fill:#273747}.title{font-size:24px;font-weight:bold}.sub{font-size:14px;fill:#53687d}.pair{font-size:15px;font-weight:600}.axis{font-size:12px;fill:#53687d}.gap{font-size:15px;font-weight:bold}</style>',
        f'<rect width="1100" height="{height}" fill="white"/>',
        '<text x="25" y="38" class="title">Seattle political fault lines</text>',
        '<text x="25" y="63" class="sub">Largest 2025 Harrell vote-share differences between precincts sharing at least 100 feet of border</text>',
        '<circle cx="31" cy="90" r="6" fill="#2677af"/><text x="44" y="95" class="axis">Precinct A</text>',
        '<circle cx="156" cy="90" r="6" fill="#ce783d"/><text x="170" y="95" class="axis">Precinct B</text>',
    ]
    left, width = 383, 555
    for tick in [0,25,50,75,100]:
        x = left + width * tick / 100
        out += [f'<line x1="{x}" y1="112" x2="{x}" y2="{height-59}" stroke="#e1e6ed"/>',
                f'<text x="{x}" y="108" text-anchor="middle" class="axis">{tick}%</text>']
    for pos, row in enumerate(top):
        y = 144 + 52 * pos
        a, b = row["precinct_a"], row["precinct_b"]
        xa = left + width * row["harrell_share_a_pct"] / 100
        xb = left + width * row["harrell_share_b_pct"] / 100
        out += [
            f'<text x="25" y="{y+4}" class="pair">Precincts {escape(a)} and {escape(b)}</text>',
            f'<line x1="{min(xa,xb):.1f}" y1="{y}" x2="{max(xa,xb):.1f}" y2="{y}" stroke="#a1aebc" stroke-width="3"/>',
            f'<circle cx="{xa:.1f}" cy="{y}" r="6" fill="#2677af"/>',
            f'<circle cx="{xb:.1f}" cy="{y}" r="6" fill="#ce783d"/>',
            f'<text x="1080" y="{y+5}" class="gap" text-anchor="end">{row["difference_pp"]:.1f} pp</text>',
        ]
    out.append(f'<text x="25" y="{height-20}" class="axis">At least 100 two-candidate votes per precinct. Descriptive comparison; no causal inference.</text>')
    out.append('</svg>')
    OUT_SVG.parent.mkdir(parents=True, exist_ok=True)
    OUT_SVG.write_text("\n".join(out)+"\n", encoding="utf-8")


def render_report(rows):
    sections = [
        "# Political Fault Lines: Where Seattle neighbors voted differently in 2025",
        "",
        "![Largest adjacent precinct gaps](figures/political_fault_lines.svg)",
        "",
        "## Exploratory results — not yet a final interpretation",
        "",
        "This analysis finds adjacent precinct pairs with sharp differences in their",
        "2025 Harrell-versus-Wilson two-candidate vote shares. It does not assume",
        "that a difference has a particular political or demographic cause.",
        "",
        "| Precinct A | Precinct B | Harrell A | Harrell B | Gap |",
        "|---|---|---:|---:|---:|",
    ]
    for r in rows[:10]:
        sections.append(
            f'| {r["precinct_a"]} | {r["precinct_b"]} | '
            f'{r["harrell_share_a_pct"]:.1f}% | {r["harrell_share_b_pct"]:.1f}% | '
            f'{r["difference_pp"]:.1f} pp |'
        )
    sections += [
        "",
        "## Method",
        "",
        "Adjacent precincts must share 100 feet or more of geographic boundary.",
        "Each precinct must have at least 100 votes for either of the two candidates.",
        "A corner touch is insufficient. Differences are absolute percentage-point gaps.",
        "The analysis covers 2025 and does not require the 2021 boundary crosswalk.",
        "",
        "## Interpretation limitations",
        "",
        "Rankings are descriptive and sensitive to minimum-vote and border thresholds.",
        "Some large gaps may reflect unusual precinct geography; inspect locations",
        "before publishing a narrative. Neighboring precincts are not controlled",
        "experimental units, and voters' individual preferences cannot be inferred.",
        "",
        "Sources: King County 2025 certified precinct results and 2025 voting-district GIS layer.",
        "",
        "Reproduce: python scripts/political_fault_lines.py",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(sections)+"\n", encoding="utf-8")


def main():
    vote_file = ROOT / "data/raw/2025_final_precinct_results.csv"
    if not vote_file.exists():
        raise FileNotFoundError("First run python scripts/diagnose_precinct_matching.py")
    votes = read_results(vote_file)
    totals = {name: sum(p.get(name, 0) for p in votes.values()) for name in CERTIFIED_2025}
    if totals != CERTIFIED_2025:
        raise ValueError(f"Official vote totals do not reconcile: {totals}")
    polygons = fetch_shapes(2025)
    missing = votes.keys() - polygons.keys()
    if missing:
        raise ValueError(f"Missing GIS polygons for 2025 precinct IDs: {sorted(missing)[:10]}")
    rows = find_fault_lines(polygons, votes)
    if not rows:
        raise ValueError("No qualifying pairs; inspect geographic data")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    render_figure(rows)
    render_report(rows)
    print(f"2025 precincts: {len(polygons):,}; qualifying neighboring pairs: {len(rows):,}")
    for r in rows[:5]:
        print(f"  {r['precinct_a']} vs {r['precinct_b']}: {r['difference_pp']:.1f} pp; "
              f"{r['shared_border_ft']:.0f} ft shared border")
    print("Generated reports/01_political_fault_lines.md and reports/figures/political_fault_lines.svg")


if __name__ == "__main__":
    main()
