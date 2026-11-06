"""Build editorial visuals and one feature-ablation check for the Seattle election report.

Run after model_precinct_surprises.py:
    python scripts/build_story_visuals.py

Uses the existing model, historical precincts, and neighborhood lookup table.
No additional data downloads.
"""
import csv
import math
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "data/processed/precinct_surprises_2025.csv"
HISTORY = ROOT / "data/processed/seattle_mayor_precinct_panel_2021_2025.csv"
AREAS = ROOT / "data/processed/precinct_to_cra_crosswalk.csv"
FIGURES = ROOT / "reports/figures"
FEATURED = ("1246", "1464")
ORANGE, BLUE, INK = "#ba6a36", "#2b739d", "#1e3244"


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run the data/model scripts first.")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def weighted_errors(rows):
    """November-vote-weighted prediction MAE, in percentage points."""
    if not rows:
        raise ValueError("Empty model results")
    weights = np.array([int(r["general_votes"]) for r in rows], float)
    y = np.array([float(r["actual_harrell_share"]) for r in rows])
    preds = [
        np.array([float(r["primary_harrell_share"]) for r in rows]),
        np.array([float(r["expected_primary_only_pct"])/100 for r in rows]),
        np.array([float(r["expected_primary_plus_census_pct"])/100 for r in rows]),
    ]
    if np.any(weights <= 0) or not np.isfinite(y).all() or not all(np.isfinite(p).all() for p in preds):
        raise ValueError("Nonfinite model data")
    return [float(100*np.average(abs(y-p), weights=weights)) for p in preds]


def prediction_explainer():
    """The 55% is deliberately hypothetical; no fake prediction is presented."""
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1050 288" role="img" aria-label="How the August primary helps estimate November results in held-out precincts">',
        '<style>text{font-family:Arial,sans-serif;fill:#22364a}.title{font-size:24px;font-weight:700}.sub{font-size:14px;fill:#52687e}.label{font-size:16px;font-weight:700}.small{font-size:13px;fill:#52687e}.big{font-size:28px;font-weight:700}</style>',
        '<rect width="1050" height="288" fill="white"/>',
        '<text x="28" y="36" class="title">How can an August primary help explain November?</text>',
        '<text x="28" y="61" class="sub">A retrospective test: learn from other precincts, then predict November in withheld areas.</text>',
    ]
    cards = [
        (30, "1 / AUGUST", "55%", "Harrell share in August", "Illustrative precinct"),
        (377, "2 / LEARN", "Pattern", "August + November, elsewhere", "Train on four groups of areas"),
        (724, "3 / TEST", "?", "Estimate November share", "Test the fifth, unseen group"),
    ]
    for x, top, number, meaning, note in cards:
        parts += [
            f'<rect x="{x}" y="89" width="296" height="148" rx="9" fill="#f4f7fa" stroke="#d4dfe8"/>',
            f'<text x="{x+15}" y="115" class="small">{escape(top)}</text>',
            f'<text x="{x+15}" y="156" class="big">{escape(number)}</text>',
            f'<text x="{x+15}" y="183" class="label">{escape(meaning)}</text>',
            f'<text x="{x+15}" y="206" class="small">{escape(note)}</text>',
        ]
    for x in (338, 685):
        parts.append(f'<path d="M{x} 155 h27 m-8 -8 l8 8 -8 8" fill="none" stroke="#7b91a5" stroke-width="2"/>')
    parts += [
        '<text x="30" y="271" class="small">55% is a made-up example. In each round, the test precincts’ November results are hidden until scoring.</text>',
        '</svg>',
    ]
    return "\n".join(parts)+"\n"


def render_error_chart(scores, count, path):
    names = ["Repeat the August vote share", "Learn the August–November relationship", "Add Census neighborhood context"]
    fig, ax = plt.subplots(figsize=(10.4, 4.0))
    order = np.arange(3)
    bars = ax.barh(order, scores, color=["#aab7c3", BLUE, ORANGE], height=.58)
    ax.set_yticks(order, names, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlim(0, max(6.0, math.ceil(max(scores)+1)))
    ax.set_xlabel("Average absolute miss (percentage points) — lower is better")
    ax.set_title("How much did each prediction miss by?", loc="left", fontsize=16, weight="bold", pad=20)
    ax.grid(axis="x", color="#e6ebf0")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=10)
    for bar, score in zip(bars, scores):
        ax.text(score+.12, bar.get_y()+bar.get_height()/2,
                f"{score:.2f} points", fontsize=11, va="center", weight="bold", color=INK)
    fig.text(.035, .02,
        f"{count:,} precincts. Predict 60%, see 57% = a 3-point miss. The learned models are tested on geographically held-out precincts.",
        fontsize=9, color="#637688")
    fig.subplots_adjust(left=.39, right=.93, top=.79, bottom=.24)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)


def choose_outliers(rows, areas, per_side=4):
    eligible = []
    for row in rows:
        pid = row["precinct_id"]
        residual = float(row["residual_pp"])
        votes = int(row["general_votes"])
        if pid in areas and votes >= 150 and math.isfinite(residual):
            eligible.append((pid, areas[pid], residual, votes))
    high = sorted((x for x in eligible if x[2] > 0), key=lambda x: -x[2])[:per_side]
    low = sorted((x for x in eligible if x[2] < 0), key=lambda x: x[2])[:per_side]
    if len(high) < per_side or len(low) < per_side:
        raise ValueError("Insufficient labeled precinct outliers")
    return high + low


def render_outlier_chart(outliers, path):
    labels = [f"{area} · {pid}" for pid, area, _, _ in outliers]
    difference = np.array([r[2] for r in outliers])
    fig, ax = plt.subplots(figsize=(10.8, 6.1))
    ax.barh(np.arange(len(outliers)), difference,
            color=[ORANGE if v >= 0 else BLUE for v in difference], height=.58)
    ax.set_yticks(np.arange(len(outliers)), labels, fontsize=10)
    ax.invert_yaxis()
    bound = max(15, math.ceil(np.abs(difference).max() + 2))
    ax.set_xlim(-bound, bound)
    ax.axvline(0, color=INK, linewidth=1)
    ax.grid(axis="x", color="#e8ecef")
    ax.set_axisbelow(True)
    ax.set_title("Precincts that surprised the model most", loc="left", fontsize=16, weight="bold", pad=34)
    ax.set_xlabel("Actual minus predicted November Harrell share (percentage points)", fontsize=10)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.text(.01, 1.05, "← More Wilson support than expected", color=BLUE, transform=ax.transAxes, fontsize=10)
    ax.text(.99, 1.05, "More Harrell support than expected →", color=ORANGE,
            transform=ax.transAxes, ha="right", fontsize=10)
    for i, val in enumerate(difference):
        ax.text(val+(.35 if val >= 0 else -.35), i, f"{val:+.1f}",
                va="center", ha="left" if val >= 0 else "right", fontsize=10, weight="bold", color=INK)
    fig.text(.035, .026,
             "Selected extreme errors among precincts with available neighborhood labels and 150+ votes; not significance tests.",
             fontsize=9, color="#637688")
    fig.subplots_adjust(left=.34, right=.96, top=.78, bottom=.16)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)


def twin_features(models, history):
    mm = {r["precinct_id"]: r for r in models}
    hh = {r["precinct_id"]: r for r in history}
    pairs = []
    for pid in FEATURED:
        if pid not in mm or pid not in hh or hh[pid]["stable_boundary"] != "True":
            raise ValueError(f"Missing or unverified historical twin {pid}")
        m, h = mm[pid], hh[pid]
        pairs.append({
            "id": pid,
            "prior": 100*float(h["harrell_share_2021"]),
            "august": 100*float(m["primary_harrell_share"]),
            "other": 100*float(m["primary_other_share"]),
            "age": 100*float(m["vap_ratio"]),
            "occupied": 100*float(m["occupancy_ratio"]),
            "density": math.expm1(float(m["log_pop_density"])),
            "november": 100*float(m["actual_harrell_share"]),
            "turnout": 100*float(h["turnout_2025"]),
        })
    if abs(pairs[0]["prior"] - pairs[1]["prior"]) > 5.001 or abs(pairs[0]["august"] - pairs[1]["august"]) > 5.001:
        raise ValueError("Twin comparison no longer meets matching limits")
    return pairs


def twin_profile_svg(pair):
    a, b = pair
    if (a["id"], b["id"]) != FEATURED:
        raise ValueError("Expected precincts 1246 and 1464")
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 646" role="img" aria-label="Matched West Seattle precincts: earlier voting and Census measures versus divergent November results">',
        '<style>text{font-family:Arial,sans-serif;fill:#24384b}.title{font-size:24px;font-weight:700}.sub{font-size:14px;fill:#607386}.head{font-size:15px;font-weight:700}.label{font-size:15px}.detail{font-size:16px;font-weight:600}.big{font-size:30px;font-weight:700}.note{font-size:12px;fill:#5f7386}</style>',
        '<rect width="1040" height="646" fill="white"/>',
        '<text x="28" y="38" class="title">How Python recognized two West Seattle political twins</text>',
        '<text x="28" y="63" class="sub">Matched on history and Census data before looking at November 2025.</text>',
        '<rect x="22" y="91" width="996" height="450" rx="8" fill="#f6f8fa"/>',
        '<text x="34" y="117" class="head">A / WHAT WE MATCHED</text>',
        '<text x="530" y="117" class="head">1246 · Highland Park</text>',
        '<text x="783" y="117" class="head">1464 · Junction–Genesee Hill</text>',
    ]
    measures = [
        ("Harrell share in 2021", "prior", False),
        ("Harrell share in August 2025", "august", False),
        ("August votes for other candidates", "other", False),
        ("Residents of voting age (2020)", "age", False),
        ("Occupied housing units (2020)", "occupied", False),
        ("Population density (2020)", "density", True),
    ]
    for i, (label, key, density) in enumerate(measures):
        y = 151 + i*57
        first = f"{a[key]:,.0f} / sq mi" if density else f"{a[key]:.1f}%"
        second = f"{b[key]:,.0f} / sq mi" if density else f"{b[key]:.1f}%"
        lines += [
            f'<line x1="31" y1="{y+21}" x2="1009" y2="{y+21}" stroke="#e1e7ed"/>',
            f'<text x="34" y="{y}" class="label">{escape(label)}</text>',
            f'<text x="530" y="{y}" class="detail">{first}</text>',
            f'<text x="783" y="{y}" class="detail">{second}</text>',
        ]
    gap = abs(a["november"] - b["november"])
    lines += [
        '<text x="34" y="520" class="note">These are broad similarities, not proof that the residents or voters are identical.</text>',
        '<text x="34" y="574" class="head">B / REVEAL NOVEMBER</text>',
        f'<text x="530" y="580" class="big" fill="{BLUE}">{a["november"]:.1f}%</text>',
        f'<text x="784" y="580" class="big" fill="{ORANGE}">{b["november"]:.1f}%</text>',
        f'<text x="34" y="607" class="head">{gap:.1f}-percentage-point difference in Harrell&#39;s November share</text>',
        f'<text x="34" y="633" class="note">Turnout was {a["turnout"]:.1f}% and {b["turnout"]:.1f}%. Different turnout is a clue, not proof of a cause.</text>',
        '</svg>',
    ]
    return "\n".join(lines)+"\n"


def leave_one_feature_out(rows):
    """One additional method: drop-column feature importance with spatial CV."""
    from model_precinct_surprises import NUMERIC_FEATURES, cross_validate
    _,full_error = cross_validate(rows, NUMERIC_FEATURES)
    result = []
    for key in ("log_pop_density", "vap_ratio", "occupancy_ratio"):
        _,error = cross_validate(rows, [name for name in NUMERIC_FEATURES if name != key])
        result.append((key, 100*(error-full_error)))
    return result, 100*full_error


def render_feature_ablation(items, path):
    names = {"log_pop_density": "Population density", "vap_ratio": "Voting-age share",
             "occupancy_ratio": "Occupied housing share"}
    values = [v for _,v in items]
    fig, ax = plt.subplots(figsize=(9.0,3.8))
    ax.barh(range(len(values)),values, color=[ORANGE if x >= 0 else BLUE for x in values],height=.55)
    ax.set_yticks(range(len(items)), [names[name] for name,_ in items])
    ax.invert_yaxis()
    ax.axvline(0,color=INK,lw=1)
    maxvalue = max(.15, 1.15*max(map(abs,values)))
    ax.set_xlim(-maxvalue*1.4,maxvalue*1.4)
    ax.set_xlabel("Change in held-out prediction error when the feature is removed (percentage points)")
    ax.set_title("Remove an ingredient: does accuracy get worse?",loc="left",fontsize=15,weight="bold")
    ax.spines[["top","right","left"]].set_visible(False)
    ax.grid(axis="x",color="#e5eaee")
    ax.set_axisbelow(True)
    ax.tick_params(axis="y",length=0)
    for i,val in enumerate(values):
        ax.text(val+(.012 if val >= 0 else -.012),i,f"{val:+.3f} pp",
                ha="left" if val >= 0 else "right",va="center",fontsize=10)
    fig.text(.03,.02,"Negative means removing a feature improved predictions. This measures predictive value, not a causal effect.",fontsize=9,color="#637688")
    fig.subplots_adjust(left=.30,right=.95,top=.80,bottom=.25)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)


def main():
    rows = read_csv(MODEL)
    historical = read_csv(HISTORY)
    areas = {r["precinct_id"]:r["cra_name"] for r in read_csv(AREAS)}
    score = weighted_errors(rows)
    outliers = choose_outliers(rows,areas)
    profile = twin_features(rows,historical)
    FIGURES.mkdir(parents=True,exist_ok=True)
    (FIGURES/"how_prediction_works.svg").write_text(prediction_explainer(),encoding="utf-8")
    render_error_chart(score,len(rows),FIGURES/"explained_model_errors.svg")
    render_outlier_chart(outliers,FIGURES/"biggest_model_misses.svg")
    (FIGURES/"west_seattle_twin_profile.svg").write_text(twin_profile_svg(profile),encoding="utf-8")
    ablation,full = leave_one_feature_out(rows)
    render_feature_ablation(ablation,FIGURES/"census_feature_ablation.svg")
    print("Weighted model errors:",*(f"{m:.2f} pp" for m in score))
    print("Featured West Seattle precincts:",[(x["id"],round(x["august"],1),round(x["november"],1)) for x in profile])
    print("Feature ablation:",[(name,round(delta,4)) for name,delta in ablation])
    print("Created five editorial figures under reports/figures/")


if __name__=="__main__":
    main()
