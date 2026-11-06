"""Build human-readable election story figures using verified processed inputs.

Run from project root:
    python scripts/build_story_visuals.py

New technique: remove one Census variable at a time and re-run geographic
cross-validation ("feature ablation"). This tests predictive usefulness, not causality.
All other figures are explanatory presentations of the existing analysis.
"""
import csv
import math
from pathlib import Path
from xml.etree import ElementTree

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "data/processed/precinct_surprises_2025.csv"
HISTORY = ROOT / "data/processed/seattle_mayor_precinct_panel_2021_2025.csv"
AREAS = ROOT / "data/processed/precinct_to_cra_crosswalk.csv"
FIGURES = ROOT / "reports/figures"
BLUE, ORANGE, INK, MUTED = "#2b739d", "#ba6a36", "#21384a", "#5f7284"
TWIN_IDS = ("1246", "1464")


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run model_precinct_surprises.py first.")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def weighted_mae_comparison(rows):
    if not rows:
        raise ValueError("Model table contains no precincts")
    weights = np.array([int(r["general_votes"]) for r in rows], dtype=float)
    actual = np.array([float(r["actual_harrell_share"]) for r in rows])
    choices = [
        np.array([float(r["primary_harrell_share"]) for r in rows]),
        np.array([float(r["expected_primary_only_pct"]) / 100 for r in rows]),
        np.array([float(r["expected_primary_plus_census_pct"]) / 100 for r in rows]),
    ]
    if (weights <= 0).any() or not np.isfinite(actual).all() or any(not np.isfinite(x).all() for x in choices):
        raise ValueError("Non-finite precinct results")
    return [100 * float(np.average(np.abs(actual-x), weights=weights)) for x in choices]


def prediction_flow_svg():
    """A static hypothetical tutorial, not real observed precinct data."""
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1090 305" role="img" aria-label="Three steps explain how August primary voting predicts November using other precincts as training examples">',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#25384a}.title{font-size:25px;font-weight:700}.sub{font-size:14px;fill:#627487}.tag{font-size:13px;font-weight:700;fill:#65788b}.number{font-size:30px;font-weight:700}.desc{font-size:16px;font-weight:600}.note{font-size:13px;fill:#65788b}</style>',
        '<rect width="1090" height="305" fill="white"/>',
        '<text x="28" y="36" class="title">How can August help estimate November?</text>',
        '<text x="28" y="62" class="sub">Retrospective experiment: learn from other precincts, then estimate November in precincts held out from training.</text>',
    ]
    cards = [
        (28, "1 / PRIMARY RESULTS", "55%", "Harrell share in August", "Hypothetical precinct; finalists only"),
        (392, "2 / LEARNING PATTERNS", "Python", "Compare other precincts", "Learn August-to-November relationships"),
        (756, "3 / HELD-OUT TEST", "?", "Estimate November share", "Reveal the actual result to score error"),
    ]
    for x,tag,num,desc,note in cards:
        lines.extend([
            f'<rect x="{x}" y="90" width="306" height="159" rx="8" fill="#f3f7fa" stroke="#d3dfe8"/>',
            f'<text x="{x+16}" y="117" class="tag">{tag}</text>',
            f'<text x="{x+16}" y="163" class="number">{num}</text>',
            f'<text x="{x+16}" y="194" class="desc">{desc}</text>',
            f'<text x="{x+16}" y="222" class="note">{note}</text>',
        ])
    for x in (345,709):
        lines.append(f'<path d="M{x} 165h36 m-12 -10 l12 10 -12 10" stroke="#899cae" stroke-width="2.5" fill="none"/>')
    lines += [
        '<text x="28" y="283" class="note">55% is illustrative. This model was analyzed AFTER the election; it is not an Election Day forecast.</text>',
        '</svg>',
    ]
    return "\n".join(lines)+"\n"


def render_mae(values, n, path):
    names = ["Repeat the August share", "Learn August–November patterns", "Add Census neighborhood information"]
    fig,ax = plt.subplots(figsize=(11,4.2))
    ys=np.arange(3)
    bars=ax.barh(ys,values,height=.56,color=["#a6b5c4",BLUE,ORANGE])
    ax.set_yticks(ys,names,fontsize=11)
    ax.invert_yaxis()
    ax.set_xlim(0,7.0)
    ax.set_xticks(range(0,8))
    ax.set_xlabel("Average prediction miss, in percentage points (lower is better)")
    ax.grid(axis="x",color="#e5eaf0")
    ax.set_axisbelow(True)
    ax.spines[["right","left","top"]].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=12)
    for bar,value in zip(bars,values):
        ax.text(value+.15,bar.get_y()+bar.get_height()/2,
                f"{value:.2f} points",va="center",weight="bold",fontsize=11,color=INK)
    ax.set_title("Three ways to guess November: which misses least?",loc="left",weight="bold",fontsize=16,pad=18)
    fig.text(.03,.03,
             f"{n:,} precincts. Predicting 60% when the result is 57% means a 3-percentage-point miss.\n"
             "Two learned models use held-out geographic groups; the first method simply repeats the August percentage.",
             fontsize=9,color=MUTED)
    fig.subplots_adjust(left=.39,right=.95,top=.78,bottom=.26)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)


def find_labeled_outliers(rows, area_names, each_side=4):
    available=[]
    for r in rows:
        pid=r["precinct_id"]
        if pid not in area_names or int(r["general_votes"]) < 150:
            continue
        residual=float(r["residual_pp"])
        if math.isfinite(residual):
            available.append((pid,area_names[pid],residual))
    high=sorted((x for x in available if x[2]>0),key=lambda x:-x[2])[:each_side]
    low=sorted((x for x in available if x[2]<0),key=lambda x:x[2])[:each_side]
    if min(len(high),len(low)) < each_side:
        raise ValueError("Insufficient labeled outlier precincts")
    return high+low


def render_outliers(rows, path):
    labels=[f"{area} · {pid}" for pid,area,_ in rows]
    values=np.array([r[2] for r in rows],float)
    fig,ax=plt.subplots(figsize=(11,6.5))
    ys=np.arange(len(rows))
    ax.barh(ys,values,color=[ORANGE if x>0 else BLUE for x in values],height=.6)
    ax.set_yticks(ys,labels,fontsize=10)
    ax.invert_yaxis()
    ax.axvline(0,color=INK,lw=1)
    limit=max(15,math.ceil(np.max(np.abs(values))+2))
    ax.set_xlim(-limit,limit)
    ax.set_xlabel("Actual November Harrell share minus model estimate (percentage points)")
    for i,v in enumerate(values):
        ax.text(v+(0.4 if v>0 else -0.4),i,f"{v:+.1f}",
                va="center",ha="left" if v>0 else "right",fontsize=10,weight="bold",color=INK)
    ax.text(0,1.045,"Blue / Wilson exceeded model expectation         Orange / Harrell exceeded model expectation",
            transform=ax.transAxes,ha="left",fontsize=10,color=MUTED)
    ax.set_title("Where did the prediction miss?",loc="left",weight="bold",fontsize=16,pad=36)
    ax.grid(axis="x",color="#e4eaf0")
    ax.set_axisbelow(True)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=10)
    fig.text(.03,.025,"Selected extremes among labeled areas with ≥150 two-candidate votes; not individually significant clusters.",
             fontsize=9,color=MUTED)
    fig.subplots_adjust(left=.35,right=.97,top=.75,bottom=.17)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)


def twin_rows(model,history):
    by_model={r["precinct_id"]:r for r in model}
    by_hist={r["precinct_id"]:r for r in history}
    result=[]
    for pid in TWIN_IDS:
        if pid not in by_model or pid not in by_hist or by_hist[pid]["stable_boundary"] != "True":
            raise ValueError(f"Missing verified stable-boundary twin {pid}")
        m,h=by_model[pid],by_hist[pid]
        record={
            "precinct_id":pid,
            "year2021":100*float(h["harrell_share_2021"]),
            "august":100*float(m["primary_harrell_share"]),
            "other":100*float(m["primary_other_share"]),
            "voting_age":100*float(m["vap_ratio"]),
            "occupied":100*float(m["occupancy_ratio"]),
            "density":math.expm1(float(m["log_pop_density"])),
            "november":100*float(m["actual_harrell_share"]),
            "turnout":100*float(h["turnout_2025"]),
            "votes":int(m["general_votes"]),
        }
        if not all(math.isfinite(x) for x in record.values() if isinstance(x,float)):
            raise ValueError("Missing or invalid twin input")
        result.append(record)
    if abs(result[0]["year2021"]-result[1]["year2021"])>5 or abs(result[0]["august"]-result[1]["august"])>5:
        raise ValueError("Pair did not satisfy historical twin similarity filters")
    return result


def twin_profile_svg(pair):
    a,b=pair
    if (a["precinct_id"],b["precinct_id"]) != TWIN_IDS:
        raise ValueError("Unexpected highlighted pair")
    def t(x,y,label,cls="normal"):
        # All interpolated values here are controlled numeric outputs or fixed labels.
        from xml.sax.saxutils import escape
        return f'<text x="{x}" y="{y}" class="{cls}">{escape(str(label))}</text>'
    lines=[
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 671" role="img" aria-label="Detailed comparison of Highland Park and Junction Genesee Hill political twins">',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#23394d}.title{font-size:25px;font-weight:700}.sub{font-size:14px;fill:#687b8d}.head{font-size:15px;font-weight:700}.normal{font-size:16px}.num{font-size:17px;font-weight:700}.bigblue{font-size:35px;font-weight:700;fill:#2b739d}.bigorange{font-size:35px;font-weight:700;fill:#ba6a36}.note{font-size:13px;fill:#65778a}</style>',
        '<rect width="1120" height="671" fill="white"/>',
        t(28,38,"Meet two West Seattle political twins","title"),
        t(28,65,"We matched them using only information available before November 2025.","sub"),
        '<rect x="22" y="89" width="1075" height="465" rx="8" fill="#f5f8fa"/>',
        t(32,120,"WHAT LOOKED SIMILAR","head"),
        t(554,120,"1246 · Highland Park","head"),
        t(835,120,"1464 · Junction–Genesee Hill","head"),
    ]
    fields=[
        ("2021 Harrell share","year2021",False),
        ("August 2025 Harrell share","august",False),
        ("Share of August votes for others","other",False),
        ("Residents of voting age (2020)","voting_age",False),
        ("Share of homes occupied (2020)","occupied",False),
        ("Population density (2020)","density",True),
    ]
    for i,(label,key,density) in enumerate(fields):
        y=160+57*i
        one=f"{a[key]:,.0f} people/mi²" if density else f"{a[key]:.1f}%"
        two=f"{b[key]:,.0f} people/mi²" if density else f"{b[key]:.1f}%"
        lines += [
            f'<line x1="31" y1="{y+19}" x2="1087" y2="{y+19}" stroke="#dee8ef"/>',
            t(33,y,label),t(554,y,one,"num"),t(835,y,two,"num"),
        ]
    lines += [
        t(33,531,"2020 Census figures describe residents and dwellings, not who voted.","note"),
        t(33,586,"THEN WE LOOKED AT NOVEMBER","head"),
        t(554,590,f"{a['november']:.1f}%","bigblue"),
        t(835,590,f"{b['november']:.1f}%","bigorange"),
        t(33,625,f"Harrell's vote share differed by {abs(a['november']-b['november']):.1f} percentage points.","head"),
        t(33,650,f"2025 turnout: {a['turnout']:.1f}% in Highland Park; {b['turnout']:.1f}% in Junction–Genesee Hill. A clue, not proof of why.","note"),
        '</svg>',
    ]
    return "\n".join(lines)+"\n"


def census_ablation(rows):
    """A new, pre-specified sensitivity analysis: remove each Census feature."""
    from model_precinct_surprises import cross_validate, NUMERIC_FEATURES
    _,mae=cross_validate(rows,NUMERIC_FEATURES)
    changes=[]
    for key in ("log_pop_density","vap_ratio","occupancy_ratio"):
        predictors=[f for f in NUMERIC_FEATURES if f!=key]
        _,reduced=cross_validate(rows,predictors)
        changes.append((key,100*(reduced-mae)))
    return changes,mae*100


def render_ablation(changes,path):
    labels={"log_pop_density":"Population density",
            "vap_ratio":"Share of residents of voting age",
            "occupancy_ratio":"Occupied-housing share"}
    vals=[score for _,score in changes]
    maxabs=max(.1,max(abs(v) for v in vals)*1.25)
    fig,ax=plt.subplots(figsize=(10.4,4.0))
    ys=np.arange(len(vals))
    ax.barh(ys,vals,color=[ORANGE if v>=0 else BLUE for v in vals],height=.6)
    ax.invert_yaxis()
    ax.set_yticks(ys,[labels[k] for k,v in changes],fontsize=11)
    ax.set_xlim(-maxabs,maxabs)
    ax.axvline(0,color=INK,lw=1)
    ax.grid(axis="x",color="#e3eaee")
    ax.set_axisbelow(True)
    ax.set_xlabel("Change in prediction error after removing the variable (percentage points)")
    for i,v in enumerate(vals):
        ax.text(v+(maxabs*.025 if v>=0 else -maxabs*.025),i,f"{v:+.3f}",
                va="center",ha="left" if v>=0 else "right",weight="bold",fontsize=11,color=INK)
    ax.set_title("Which extra clues helped? Remove them one at a time.",loc="left",fontsize=16,pad=20,weight="bold")
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=10)
    fig.text(.02,.025,"Positive: removing the variable made predictions worse. Negative: removing it helped. Not evidence of a causal effect.",
             fontsize=9,color=MUTED)
    fig.subplots_adjust(left=.33,right=.96,top=.79,bottom=.27)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)


def main():
    model=load_csv(MODEL)
    history=load_csv(HISTORY)
    area={r["precinct_id"]:r["cra_name"] for r in load_csv(AREAS)}
    maes=weighted_mae_comparison(model)
    twins=twin_rows(model,history)
    FIGURES.mkdir(parents=True,exist_ok=True)
    (FIGURES/"how_prediction_works.svg").write_text(prediction_flow_svg(),encoding="utf-8")
    render_mae(maes,len(model),FIGURES/"explained_model_errors.svg")
    render_outliers(find_labeled_outliers(model,area),FIGURES/"biggest_model_misses.svg")
    (FIGURES/"west_seattle_twin_profile.svg").write_text(twin_profile_svg(twins),encoding="utf-8")
    changes,full=census_ablation(model)
    render_ablation(changes,FIGURES/"census_feature_ablation.svg")
    for name in ("how_prediction_works.svg","explained_model_errors.svg","biggest_model_misses.svg",
                 "west_seattle_twin_profile.svg","census_feature_ablation.svg"):
        ElementTree.parse(FIGURES/name)
    print(f"Precincts modeled: {len(model):,}. Average errors: " + ", ".join(f"{x:.2f}" for x in maes))
    print("West Seattle: "+", ".join(f"{r['precinct_id']} August {r['august']:.1f}% November {r['november']:.1f}%" for r in twins))
    print("Feature-removal changes to prediction error:",[(name,round(delta,3)) for name,delta in changes])
    print("Generated five article figures in reports/figures/")


if __name__ == "__main__":
    main()
