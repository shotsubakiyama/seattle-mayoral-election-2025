"""Render three close-up Seattle electoral fault-line case studies.

Requires cached King County 2025 vote results and precinct polygons from earlier
diagnostics. Run: python scripts/render_fault_line_cases.py
Outputs a Markdown draft and three standalone SVG maps under reports/.
"""
import csv
from html import escape
from pathlib import Path

from shapely.geometry import Polygon, box

from diagnose_precinct_matching import CERTIFIED_2025, read_results
from spatial_precinct_overlap import ROOT, fetch_shapes
from political_fault_lines import find_fault_lines

PAIRS = [("1709", "1724"), ("1955", "1957"), ("1803", "1808")]
FIGURES = ROOT / "reports/figures"
REPORT = ROOT / "reports/02_fault_line_case_studies.md"
VOTES = ROOT / "data/raw/2025_final_precinct_results.csv"
CRA = ROOT / "data/processed/precinct_to_cra_crosswalk.csv"
WILSON, CENTER, HARRELL = (34, 105, 144), (242, 245, 247), (212, 128, 57)


def lerp(a, b, t):
    t = max(0, min(1, t))
    return "#" + "".join(f"{round(x+(y-x)*t):02x}" for x, y in zip(a, b))


def vote_color(share):
    """Blue = Wilson-leading, orange = Harrell-leading, neutral at 50%."""
    if share is None:
        return "#e9eef1"
    if share <= 50:
        return lerp(WILSON, CENTER, share / 50)
    return lerp(CENTER, HARRELL, (share - 50) / 50)


def share_of(votes, pid):
    row = votes.get(pid, {})
    harrell = row.get("Bruce Harrell", 0)
    wilson = row.get("Katie Wilson", 0)
    total = harrell + wilson
    return (100 * harrell / total if total else None, total)


def polygons_of(geometry):
    if geometry.is_empty:
        return
    if isinstance(geometry, Polygon):
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from polygons_of(part)


def path_for(geometry, transform):
    segments = []
    for polygon in polygons_of(geometry):
        for ring in [polygon.exterior, *polygon.interiors]:
            points = [transform(x, y) for x, y in ring.coords]
            if len(points) < 4:
                continue
            segments.append(" ".join(
                [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
                + [f"L{x:.1f},{y:.1f}" for x, y in points[1:]] + ["Z"]
            ))
    return " ".join(segments)


def map_view(poly_a, poly_b):
    xmin, ymin, xmax, ymax = poly_a.union(poly_b).bounds
    pad = max(900, max(xmax-xmin, ymax-ymin) * 0.33)
    return box(xmin-pad, ymin-pad, xmax+pad, ymax+pad)


def map_transform(bounds):
    minx, miny, maxx, maxy = bounds
    width, height, left, top = 710, 422, 51, 154
    spanx, spany = max(maxx-minx, 1), max(maxy-miny, 1)
    scale = min((width-30)/spanx, (height-30)/spany)
    padx, pady = (width-spanx*scale)/2, (height-spany*scale)/2
    def convert(x, y):
        return (left + padx + (x-minx)*scale, top+height-pady-(y-miny)*scale)
    return convert, scale


def labels():
    with CRA.open(encoding="utf-8-sig", newline="") as file:
        return {r["precinct_id"]: r["cra_name"] for r in csv.DictReader(file)}


def area_name(a, b, names):
    x, y = names.get(a), names.get(b)
    if x and x == y:
        return x
    return " / ".join(dict.fromkeys(v for v in (x,y) if v)) or "Seattle"


def draw_case(row, shapes, votes, names):
    a, b = row["precinct_a"], row["precinct_b"]
    if a not in shapes or b not in shapes:
        raise ValueError(f"Missing polygon for {a}/{b}")
    pa, na = share_of(votes, a)
    pb, nb = share_of(votes, b)
    if pa is None or pb is None or min(na,nb) < 100:
        raise ValueError(f"Too few votes in {a}/{b}")
    border = shapes[a].boundary.intersection(shapes[b].boundary).length
    if border < 100 or abs(border-row["shared_border_ft"]) > 1:
        raise ValueError(f"Shared border mismatch for {a}/{b}")
    if abs(abs(pa-pb) - row["difference_pp"]) > 0.03:
        raise ValueError(f"Vote share mismatch for {a}/{b}")
    view = map_view(shapes[a], shapes[b])
    tx, scale = map_transform(view.bounds)
    title = escape(area_name(a,b,names))
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 660" role="img" aria-label="Precincts {a} and {b}; Harrell shares {pa:.1f} and {pb:.1f} percent">',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#203043}.title{font-size:27px;font-weight:700}.sub{font-size:15px;fill:#53667a}.small{font-size:13px;fill:#51657b}.label{font-size:15px;font-weight:700}.big{font-size:36px;font-weight:700}.pct{font-size:28px;font-weight:700}.id{font-size:14px;font-weight:700}</style>',
        '<rect width="1160" height="660" fill="white"/>',
        '<text x="40" y="48" class="title">Across the precinct line</text>',
        f'<text x="40" y="77" class="sub">{title} | 2025 Seattle mayoral election | Precincts {a} and {b}</text>',
        '<text x="40" y="110" class="small">Nearby precinct colors show the Harrell share of votes for Harrell or Wilson.</text>',
        '<rect x="39" y="145" width="737" height="448" rx="10" fill="#f8fafc" stroke="#cbd6df"/>',
        '<defs><clipPath id="mapclip"><rect x="47" y="151" width="720" height="431"/></clipPath></defs>',
        '<g clip-path="url(#mapclip)">',
    ]
    for pid, polygon in shapes.items():
        if not polygon.intersects(view):
            continue
        clipped = polygon.intersection(view)
        path = path_for(clipped, tx)
        share, count = share_of(votes, pid)
        color = vote_color(share) if count >= 20 else "#e9eef1"
        if path:
            lines.append(f'<path d="{path}" fill="{color}" fill-rule="evenodd" stroke="#ffffff" stroke-width="1.3"/>')
    for pid in (a,b):
        path = path_for(shapes[pid].intersection(view), tx)
        lines.append(f'<path d="{path}" fill="none" stroke="#ffffff" stroke-width="6"/>')
        lines.append(f'<path d="{path}" fill="none" stroke="#263b4e" stroke-width="3.3"/>')
        point = shapes[pid].representative_point()
        px, py = tx(point.x, point.y)
        lines.append(f'<rect x="{px-31:.1f}" y="{py-14:.1f}" width="62" height="27" rx="13" fill="white" stroke="#263b4e" stroke-width="1.5"/>')
        lines.append(f'<text x="{px:.1f}" y="{py+5:.1f}" text-anchor="middle" class="id">{pid}</text>')
    lines.append("</g>")
    scale_feet = 1000 if 1000*scale <= 175 else 500
    scale_width = scale_feet*scale
    lines += [
        f'<rect x="54" y="531" width="{max(152,scale_width+25):.1f}" height="47" rx="6" fill="white" opacity="0.93"/>',
        f'<path d="M63 556h{scale_width:.1f}" stroke="#24394c" stroke-width="4"/>',
        f'<path d="M63 551v10 M{63+scale_width:.1f} 551v10" stroke="#24394c" stroke-width="2"/>',
        f'<text x="{63+scale_width/2:.1f}" y="547" text-anchor="middle" class="small">{scale_feet:,} feet</text>',
        '<text x="743" y="178" text-anchor="middle" class="label">N ↑</text>',
        '<text x="815" y="163" class="label">VOTE-SHARE DIFFERENCE</text>',
        f'<text x="815" y="211" class="big">{abs(pa-pb):.1f} pp</text>',
        f'<text x="815" y="242" class="small">{border:,.0f} feet of shared boundary</text>',
    ]
    for pid, share, count, y in ((a,pa,na,282),(b,pb,nb,386)):
        lines += [
            f'<text x="815" y="{y}" class="label">Precinct {pid}</text>',
            f'<text x="815" y="{y+35}" class="pct">{share:.1f}%</text>',
            f'<text x="934" y="{y+35}" class="small">Harrell share</text>',
            f'<rect x="815" y="{y+48}" width="300" height="12" rx="6" fill="#e5ebef"/>',
            f'<rect x="815" y="{y+48}" width="{300*share/100:.1f}" height="12" rx="6" fill="{vote_color(share)}"/>',
            f'<text x="815" y="{y+78}" class="small">{count:,} two-candidate votes</text>',
        ]
    lines.append('<text x="815" y="520" class="small">Harrell share across nearby precincts</text>')
    for i in range(61):
        x = 815 + 300*i/61
        lines.append(f'<rect x="{x:.1f}" y="531" width="{300/61+0.3:.1f}" height="13" fill="{vote_color(i*100/60)}"/>')
    lines += [
        '<text x="815" y="566" class="small">0%</text><text x="965" y="566" text-anchor="middle" class="small">50%</text><text x="1115" y="566" text-anchor="end" class="small">100%</text>',
        '<text x="40" y="624" class="small">Source: King County certified 2025 precinct results and GIS boundaries (EPSG:2926).</text>',
        '<text x="40" y="644" class="small">Descriptive, not causal. No roads, zoning or building-level information is represented.</text>',
        '</svg>',
    ]
    FIGURES.mkdir(parents=True,exist_ok=True)
    output = FIGURES / f"fault_line_{a}_{b}_v2.svg"
    output.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return output


def write_report(rows, votes, names):
    lines = [
        "# Seattle Political Fault Lines: Three neighborhood contrasts", "",
        "How can two precincts sharing a physical border vote so differently in the same mayoral election?",
        "The figures below illustrate **2025 Harrell-versus-Wilson two-candidate vote shares**.",
        "Pairs require at least 100 votes per precinct and at least 100 feet of shared boundary.", "",
        "| Adjacent precincts | Area | Harrell share (A / B) | Votes (A / B) | Gap |",
        "|---|---|---|---|---:|",
    ]
    for row in rows:
        a,b=row["precinct_a"],row["precinct_b"]
        pa,na=share_of(votes,a);pb,nb=share_of(votes,b)
        lines.append(f"| {a} / {b} | {area_name(a,b,names)} | {pa:.1f}% / {pb:.1f}% | {na:,} / {nb:,} | **{abs(pa-pb):.1f} pp** |")
    for row in rows:
        a,b=row["precinct_a"],row["precinct_b"]
        pa,_=share_of(votes,a);pb,_=share_of(votes,b)
        high=a if pa>pb else b
        lines += [
            "",f"## {area_name(a,b,names)}: {a} and {b}","",
            f"![2025 voting geography for precincts {a} and {b}](figures/fault_line_{a}_{b}_v2.svg)","",
            f"These precincts share about {row['shared_border_ft']:,.0f} feet of boundary, but",
            f"Harrell received {pa:.1f}% of the two-candidate vote in {a} and {pb:.1f}% in {b}.",
            f"Precinct **{high}** gave Harrell the higher share. This does not establish why.","",
        ]
    lines += [
        "## Interpretation and limitations", "",
        "The maps show neighboring precinct vote shares on one consistent scale: blue indicates",
        "Wilson-leading areas and orange indicates Harrell-leading areas. Dark outlines identify",
        "the selected precincts. These are descriptive extremes selected from many pairs.",
        "They should not be interpreted as evidence that individual voters changed sides",
        "or as proof of an effect from housing, income or other neighborhood characteristics.", "",
        "The next step is to add street and housing context, inspect the geography, and test",
        "potential explanations before selecting headline findings.", "",
        "## Reproduce", "",
        "Run: python scripts/render_fault_line_cases.py", "",
        "Sources: King County November 2025 certified precinct returns and 2025 voting-district GIS layer.",
    ]
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")


def main():
    if not VOTES.exists():
        raise FileNotFoundError("First run python scripts/diagnose_precinct_matching.py")
    votes=read_results(VOTES)
    totals={k:sum(r.get(k,0) for r in votes.values()) for k in CERTIFIED_2025}
    if totals != CERTIFIED_2025:
        raise ValueError(f"2025 official totals fail reconciliation: {totals}")
    shapes=fetch_shapes(2025)
    if set(votes)-set(shapes):
        raise ValueError("Missing GIS polygons for election precincts")
    ranked=find_fault_lines(shapes,votes)
    lookup={frozenset((r["precinct_a"],r["precinct_b"])):r for r in ranked}
    rows=[]
    for a,b in PAIRS:
        r=lookup.get(frozenset((a,b)))
        if r is None:
            raise ValueError(f"Case study pair {a}/{b} is not in current adjacency ranking")
        if r["precinct_a"] != a:
            r={**r,"precinct_a":a,"precinct_b":b,
               "harrell_share_a_pct":r["harrell_share_b_pct"],
               "harrell_share_b_pct":r["harrell_share_a_pct"],
               "votes_a":r["votes_b"],"votes_b":r["votes_a"]}
        rows.append(r)
    names=labels()
    for row in rows:
        print("Created",draw_case(row,shapes,votes,names).relative_to(ROOT))
    write_report(rows,votes,names)
    print("Created",REPORT.relative_to(ROOT))


if __name__=="__main__":
    main()
