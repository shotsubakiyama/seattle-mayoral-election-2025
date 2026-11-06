"""Build the article's model-comparison scorecard from local model CSV.

Run: python scripts/build_model_scorecard.py

Only uses the standard library. The chart itself is an SVG suitable for GitHub.
"""
import csv
import math
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/precinct_surprises_2025.csv"
OUTPUT = ROOT / "reports/figures/model_comparison_scorecard.svg"


def errors(rows):
    if not rows:
        raise ValueError("No precinct model rows")
    total_weight = 0
    sums = [0.0, 0.0, 0.0]
    for row in rows:
        w = int(row["general_votes"])
        observed = float(row["actual_harrell_share"])
        predicted = (
            float(row["primary_harrell_share"]),
            float(row["expected_primary_only_pct"]) / 100,
            float(row["expected_primary_plus_census_pct"]) / 100,
        )
        if w <= 0 or not (0 <= observed <= 1) or any(not math.isfinite(v) for v in predicted):
            raise ValueError(f"Invalid vote / share in precinct {row['precinct_id']}")
        total_weight += w
        for i, p in enumerate(predicted):
            sums[i] += w * abs(observed - p)
    return [100 * x / total_weight for x in sums]


def svg_document(values, precinct_count):
    if len(values) != 3 or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Expected three nonnegative finite errors")
    labels = (
        "Use August share directly",
        "Calibrate August voting",
        "August + Census context",
    )
    colors = ("#9aa8b7", "#4b829e", "#d0874d")
    x0, scale = 328, 88  # chart spans 0 to 6 percentage points
    max_display = 6.0
    if max(values) > max_display:
        raise ValueError("MAE above chart scale; update the chart axis")
    result = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 370" role="img" aria-label="Comparison of model errors: direct August baseline, fitted August model and fitted August plus Census model">',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#223346}.title{font-size:23px;font-weight:700}.sub{font-size:13px;fill:#617183}.label{font-size:16px;font-weight:600}.value{font-size:20px;font-weight:700}.tick{font-size:12px;fill:#728292}.foot{font-size:12px;fill:#617183}</style>',
        '<rect width="1000" height="370" fill="#ffffff"/>',
        '<text x="32" y="37" class="title">The August primary was a strong starting point</text>',
        f'<text x="32" y="62" class="sub">{precinct_count:,} Seattle precincts | Weighted error in percentage points | Lower is better</text>',
    ]
    for tick in (0, 2, 4, 6):
        x=x0+scale*tick
        result += [
            f'<line x1="{x}" y1="87" x2="{x}" y2="294" stroke="#e3eaf0" stroke-width="1"/>',
            f'<text x="{x}" y="315" class="tick" text-anchor="middle">{tick}</text>',
        ]
    for i, (label, val, color) in enumerate(zip(labels, values, colors)):
        y=111+i*72
        bar=val*scale
        result += [
            f'<text x="32" y="{y+24}" class="label">{escape(label)}</text>',
            f'<rect x="{x0}" y="{y}" width="{bar:.2f}" height="37" rx="3" fill="{color}"/>',
            f'<text x="{x0+bar+12:.2f}" y="{y+26}" class="value">{val:.2f}</text>',
        ]
    result += [
        '<text x="32" y="349" class="foot">Fitted models: held-out geographic-group cross-validation; direct August is an uncalibrated benchmark.</text>',
        '</svg>',
    ]
    return "\n".join(result)+"\n"


def main():
    if not INPUT.exists():
        raise FileNotFoundError("First run python scripts/model_precinct_surprises.py")
    with INPUT.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    errors_pct = errors(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg_document(errors_pct, len(rows)), encoding="utf-8")
    print("Model errors (pp):", *(f"{x:.2f}" for x in errors_pct))
    print("Generated", OUTPUT.relative_to(ROOT))


if __name__=="__main__":
    main()
