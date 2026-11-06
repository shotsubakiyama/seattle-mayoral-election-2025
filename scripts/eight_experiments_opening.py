"""Experiments 1–2 for Seattle, Through the Numbers.

Uses King County's certified November 2025 precinct CSV (downloaded by
scripts/diagnose_precinct_matching.py), and produces two descriptive graphics.

E1: citywide cross-contest coalition patterns across precinct groups.
E2: counterfactual equal mayoral finalist participation per registered voter.

This cannot identify an individual's split-ticket vote or how an abstaining
voter would have voted. The counterfactual is a mechanical reweighting.

Usage from the repo root:
    python scripts/eight_experiments_opening.py
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from diagnose_precinct_matching import ROOT, ensure_source, suffix

RAW = ROOT / "data/raw/2025_final_precinct_results.csv"
FIG = ROOT / "reports/figures"
OUTPUT = ROOT / "data/processed"
SUPPORT = ROOT / "reports/experiments"

# Short, nonpartisan guide to each of the six citywide ballot decisions.
# See the official King County 2025 general-election voter pamphlet.
CONTEST_DESCRIPTIONS = {
    "Wilson": "Mayor — Wilson vs. incumbent Harrell; city executive",
    "Evans": "City Attorney — Evans vs. incumbent Davison; city legal affairs",
    "Rinck": "City Council Position 8 — Rinck vs. Savage; citywide council seat",
    "Foster": "City Council Position 9 — Foster vs. incumbent Nelson; citywide council seat",
    "Prop. 1 Yes": "Proposition 1 — renew education levy for preschool, K–12 and college/career support",
    "Prop. 2 Yes": "Proposition 2 — change business tax: higher exemption and revised rates",
}

# Exact names and citywide certified two-option vote totals, King County 2025.
CONTESTS = [
    ("City of Seattle Mayor", "Katie Wilson", "Bruce Harrell", 138931, 136920, "Wilson"),
    ("City of Seattle City Attorney", "Erika Evans", "Ann Davison", 178470, 87886, "Evans"),
    ("City of Seattle Council Position No. 8", "Alexis Mercedes Rinck", "Rachael Savage", 207892, 46266, "Rinck"),
    ("City of Seattle Council Position No. 9", "Dionne Foster", "Sara Nelson", 165930, 97710, "Foster"),
    ("City of Seattle Proposition No. 1", "Yes", "No", 217294, 54440, "Prop. 1 Yes"),
    ("City of Seattle Proposition No. 2", "Yes", "No", 190555, 77958, "Prop. 2 Yes"),
]


def parse_official_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing King County official precinct CSV: {path}")
    race_choices = {r[0]: {r[1], r[2]} for r in CONTESTS}
    votes = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    registered = {}
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        rows = csv.DictReader(handle)
        fields = {n.replace(" ", "").lower() for n in (rows.fieldnames or [])}
        if not {"precinct", "race", "countergroup", "countertype", "sumofcount"} <= fields:
            raise ValueError(f"Unexpected King County result columns: {rows.fieldnames}")
        for source in rows:
            row = {k.replace(" ", "").lower(): (v or "").strip()
                   for k, v in source.items() if k}
            race = row["race"]
            if race not in race_choices or row.get("countergroup", "Total") != "Total":
                continue
            pid = suffix(row["precinct"])
            if pid is None:
                continue
            raw_count = row["sumofcount"].replace(",", "")
            number = int(raw_count)
            if number < 0:
                raise ValueError("Negative vote/registered count")
            choice = row["countertype"]
            if choice in race_choices[race]:
                votes[race][pid][choice] += number
            if race == "City of Seattle Mayor" and choice == "Registered Voters":
                if pid in registered:
                    raise ValueError(f"Duplicate registered voter record for {pid}")
                registered[pid] = number
    return votes, registered


def validate_contests(votes):
    for race, a, b, expected_a, expected_b, _ in CONTESTS:
        if race not in votes:
            raise ValueError(f"Missing contest from source: {race}")
        actual_a = sum(p.get(a, 0) for p in votes[race].values())
        actual_b = sum(p.get(b, 0) for p in votes[race].values())
        if (actual_a, actual_b) != (expected_a, expected_b):
            raise ValueError(f"{race} does not match official totals. "
                             f"Expected {(expected_a,expected_b)} got {(actual_a,actual_b)}")


def mayoral_groups(votes):
    race,a,b,*_ = CONTESTS[0]
    result={}
    for pid,choices in votes[race].items():
        aa,bb=choices.get(a,0),choices.get(b,0)
        if aa+bb < 10 or aa == bb:
            continue
        result[pid] = "Wilson-winning precincts" if aa>bb else "Harrell-winning precincts"
    if len(result) < 950:
        raise ValueError(f"Only {len(result)} eligible mayoral precincts")
    return result


def cross_contest_shares(votes,groups):
    output=[]
    for race,a,b,_,_,short in CONTESTS:
        for group in ("Wilson-winning precincts","Harrell-winning precincts"):
            subset=[pid for pid,g in groups.items() if g==group]
            available=[pid for pid in subset if pid in votes[race]]
            if len(available)<len(subset)*.97:
                raise ValueError(f"Insufficient coverage for {race}, {group}")
            yes=sum(votes[race][p].get(a,0) for p in available)
            no=sum(votes[race][p].get(b,0) for p in available)
            if yes+no <=0:
                raise ValueError(f"No votes for {race} / {group}")
            output.append(dict(contest=race,choice=a,label=short,group=group,
                               share=100*yes/(yes+no),votes_yes=yes,votes_other=no,
                               precincts=len(available)))
    return output


def equal_participation(votes,registered):
    race,a,b,*_ = CONTESTS[0]
    kept=[]
    for pid,results in votes[race].items():
        aa,bb=results.get(a,0),results.get(b,0)
        regs=registered.get(pid,0)
        if aa+bb==0:
            continue
        if regs <= 0 or aa+bb > regs:
            raise ValueError(f"Missing/invalid registered-voter denominator for precinct {pid}")
        kept.append((regs,aa,bb))
    if sum(a for _,a,_ in kept) != 138931 or sum(b for _,_,b in kept) != 136920:
        raise ValueError("Equal-participation comparison omitted mayoral votes")
    actual=sum(a for _,a,_ in kept)/sum(a+b for _,a,b in kept)
    weighted=sum(reg*(a/(a+b)) for reg,a,b in kept)/sum(reg for reg,_,_ in kept)
    return dict(actual_wilson=actual*100, equal_wilson=weighted*100,
                actual_margin_pp=(2*actual-1)*100,
                equal_margin_pp=(2*weighted-1)*100,
                precincts=len(kept),registered=sum(r for r,_,_ in kept))


def plot_coalitions(rows,destination):
    labels=[r[5] for r in CONTESTS]
    ys=np.arange(len(labels))
    h=[next(x["share"] for x in rows if x["label"]==name and
            x["group"]=="Harrell-winning precincts") for name in labels]
    w=[next(x["share"] for x in rows if x["label"]==name and
            x["group"]=="Wilson-winning precincts") for name in labels]
    fig,ax=plt.subplots(figsize=(11.3,6.2))
    ax.barh(ys-.19,h,.35,label="Precincts won by Harrell",color="#c77945")
    ax.barh(ys+.19,w,.35,label="Precincts won by Wilson",color="#367d9e")
    ax.set_yticks(ys,labels,fontsize=11)
    ax.invert_yaxis()
    ax.set_xlim(0,105)
    ax.set_xticks([0,25,50,75,100],["0%","25%","50%","75%","100%"])
    ax.set_xlabel("Support for the named candidate or Yes, in two-candidate / Yes–No votes")
    ax.axvline(50,ls="--",lw=1,color="#6a7b87")
    ax.grid(axis="x",alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=13)
    for i,(a,b) in enumerate(zip(h,w)):
        ax.text(a+1,i-.19,f"{a:.1f}%",va="center",fontsize=9,color="#593b28")
        ax.text(b+1,i+.19,f"{b:.1f}%",va="center",fontsize=9,color="#225067")
    # Reserve a dedicated legend band above the axes, away from proposition bars.
    handles, legend_labels = ax.get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper left",
               bbox_to_anchor=(.225,.905), ncol=2, frameon=False,
               fontsize=10, columnspacing=2.4, handlelength=2.2)
    fig.suptitle("Harrell-winning precincts still backed other citywide winners",
                 x=.225, y=.982, ha="left", weight="bold", fontsize=16)
    fig.text(.02,.015,
        "Precincts are grouped by who won the 2025 mayor race. Percentages pool votes across each group.\n"
        "Same-precinct support is NOT evidence that individual people split their tickets.",
        fontsize=9,color="#536775")
    fig.subplots_adjust(left=.23,right=.95,top=.78,bottom=.20)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,format="svg",bbox_inches="tight")
    plt.close(fig)


def plot_counterfactual(x,destination):
    labels=["Actual 2025 result","Equal mayoral participation per registered voter"]
    vals=[x["actual_wilson"],x["equal_wilson"]]
    fig,ax=plt.subplots(figsize=(10,3.7))
    for i,(label,val) in enumerate(zip(labels,vals)):
        ax.barh(i,val,height=.52,color="#397b98" if i==0 else "#c47747")
        ax.text(val+.8,i,f"{val:.2f}%",va="center",fontsize=14,weight="bold")
    ax.set_yticks([0,1],labels,fontsize=11)
    ax.invert_yaxis()
    ax.set_xlim(40,61)
    ax.axvline(50,color="#243b4c",ls="--",lw=1)
    ax.set_xlabel("Katie Wilson's share of mayoral finalist votes")
    ax.set_title("Equal precinct participation: Wilson +{:.2f} percentage points".format(
                 x["equal_wilson"]-x["actual_wilson"]),
                 loc="left",weight="bold",fontsize=15,pad=20)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.grid(axis="x",alpha=.18)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y",length=0,pad=10)
    fig.text(.02,.005,"Equal participation means the same finalist votes per registered voter in every precinct.\n"
             "Precinct candidate preferences are held fixed: this is not a prediction of nonvoters' choices.",
             fontsize=9,color="#526777")
    fig.subplots_adjust(left=.43,right=.94,top=.72,bottom=.30)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,format="svg",bbox_inches="tight")
    plt.close(fig)


def write_outputs(rows,x):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    SUPPORT.mkdir(parents=True,exist_ok=True)
    path=OUTPUT/"experiment_01_cross_contest_support.csv"
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    coalition=[
        "# Experiment 01 — One city, multiple political coalitions","",
        "![2025 support for each citywide winner or choice, grouped by mayoral precinct winner](../figures/experiment_01_citywide_coalitions.svg)","",
        "The chart groups precincts according to their **2025 mayoral winner**, then displays the "
        "**pooled candidate/Yes vote share** in each group for six citywide contests. "
        "This tests whether the mayoral vote resembles support in other races.","",
        "**What were these contests?** Seattle voters elected a mayor, a city attorney and "
        "two citywide council members, while voting on an education property-tax levy "
        "(Proposition 1) and a business-and-occupation tax change (Proposition 2). "
        "Each table row shows **support for the named candidate or Yes**. "
        "The other candidate's support is the remainder of the two-candidate vote.","",
        "**The key observation:** Even in precincts won by Harrell, Evans, Rinck and Foster "
        "each received a majority of the votes for their respective two-candidate contests. "
        "Both propositions also received majority support.","",
        "The 50% reference line means an outright majority between the named candidates "
        "(or among Yes/No votes). This is **not individual-level split-ticket voting**: we have "
        "aggregate precinct votes, no linked ballots.","",
        "| Contest and what was decided (candidate/Yes shown) | Harrell-winning precincts | Wilson-winning precincts |",
        "|---|---:|---:|"
    ]
    for _,a,b,_,_,name in CONTESTS:
        h=next(r for r in rows if r["label"]==name and r["group"]=="Harrell-winning precincts")
        w=next(r for r in rows if r["label"]==name and r["group"]=="Wilson-winning precincts")
        coalition.append(f"| {CONTEST_DESCRIPTIONS[name]} (**{a}**) | {h['share']:.1f}% | {w['share']:.1f}% |")
    coalition += ["","**Method:** group Seattle precincts by mayoral winner; pool ballots separately for each "
                "other citywide contest. Official results from King County, November 2025.",
                "Differential undervoting means denominators differ across races.","",
                "**Ballot descriptions:** [King County — Proposition 1: Families, Education, Preschool, and Promise Levy]"
                "(https://info.kingcounty.gov/kcelections/Vote/contests/ballotmeasures.aspx?cid=101780) "
                "and [Proposition 2: Changes to the Business and Occupation Tax]"
                "(https://info.kingcounty.gov/kcelections/Vote/contests/ballotmeasures.aspx?cid=101794&groupname=City&lang=en-US).",""]
    (SUPPORT/"01_coalitions.md").write_text("\n".join(coalition),encoding="utf-8")
    compare=[
        "# Experiment 02 — The participation gap and Wilson's narrower observed lead","",
        "**The point:** Seattle's geography of mayoral participation mechanically "
        "reduced Wilson's winning vote share compared with a hypothetical city in "
        "which precincts contributed the same number of finalist votes per registered voter. "
        "In other words, precincts that were relatively stronger for Wilson tended to "
        "contribute fewer mayoral finalist votes per registered voter. This is a "
        "relationship between aggregates, not proof of why turnout differed.","",
        "![Observed mayoral result versus a mechanical equal-participation counterfactual](../figures/experiment_02_equal_participation.svg)","",
        f"**Actual:** Wilson received **{x['actual_wilson']:.2f}%** of the two-finalist votes. "
        f"**Equal participation:** she would receive **{x['equal_wilson']:.2f}%** if every "
        "precinct contributed the same number of mayoral finalist votes **per registered voter**, "
        "holding each precinct's observed candidate split unchanged. "
        f"That is a **{x['equal_wilson']-x['actual_wilson']:.2f}-percentage-point increase** "
        "in Wilson's share, which would widen her share advantage over Harrell. "
        "It suggests that where voters participated mattered to the closeness of the result, "
        "under these fixed-preference assumptions.","",
        "This is a **reweighting of precinct vote shares**, not a forecast of what nonvoters "
        "would have chosen, and does not separate persuasion from turnout. "
        "Only valid registered-voter denominators are used, with certified mayor totals "
        "reconciled before comparison.","",
        f"Examined **{x['precincts']:,} precincts**, totaling **{x['registered']:,} registered voters**.","",
        "**When is this used?** Analysts use reweighting and standardization to compare "
        "populations on a common basis—for example, to study how age composition affects "
        "the comparison of health rates between cities. Here the common basis is "
        "registered voters per precinct, not the observed number of mayoral votes.","",
        "**How it works (a simple example):** Suppose two precincts each have 1,000 "
        "registered voters; the first votes 60% Wilson with 600 votes cast for the "
        "finalists, and the second votes 40% Wilson with 300 finalist votes. "
        "The observed pooled Wilson share is 53.3%; equally weighting the two precincts "
        "by their registered-voter totals gives 50%. This is illustrative, not Seattle data.","",
        "**Limitation:** The counterfactual keeps the same observed support in every "
        "precinct, even though different turnout could bring out a different electorate. "
        "Registered voters are not identical to all eligible residents, and turnout "
        "in this calculation is *votes for the two finalists per registered voter*, "
        "not necessarily ballot-return turnout.","",
        "The reweighting is equivalent to taking the registered-voter-weighted average "
        "of Wilson's share in each precinct, rather than the observed-vote-weighted average.",""]
    (SUPPORT/"02_equal_participation.md").write_text("\n".join(compare),encoding="utf-8")
    return path


def main():
    ensure_source(2025,RAW,offline=False)
    votes,registered=parse_official_csv(RAW)
    validate_contests(votes)
    groups=mayoral_groups(votes)
    rows=cross_contest_shares(votes,groups)
    cf=equal_participation(votes,registered)
    plot_coalitions(rows,FIG/"experiment_01_citywide_coalitions.svg")
    plot_counterfactual(cf,FIG/"experiment_02_equal_participation.svg")
    write_outputs(rows,cf)
    print(f"PASS: all {len(CONTESTS)} citywide contests reconcile with certified totals.")
    print(f"PASS: {len(groups)} precincts with decisive mayoral winner.")
    print(f"Actual Wilson two-finalist share {cf['actual_wilson']:.3f}%; "
          f"equal participation {cf['equal_wilson']:.3f}%.")
    for name in ("experiment_01_citywide_coalitions.svg","experiment_02_equal_participation.svg"):
        if not (FIG/name).is_file():
            raise FileNotFoundError(FIG/name)
    print("Created experiments 01 and 02 reports and figures.")


if __name__ == "__main__":
    main()
