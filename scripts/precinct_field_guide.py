"""Create the geographic evidence for Seattle, Precinct by Precinct.

2025: certified King County precinct result CSV and official EPSG:2926 polygons.
2021 comparison: only previously verified identical-boundary precincts in the panel.

The three important safeguards:
* Size in square miles includes water in the official precinct polygon.
* Harrell's 2021 opponent was Lorena González, not Katie Wilson.
* A large gap is a descriptively unusual boundary, not a causal discovery.

Outputs compact PNG/SVG figures, aggregate JSON, and an accessible ranked CSV.
Run after scripts/diagnose_precinct_matching.py and model_precinct_surprises.py.
"""
import csv
import json
import math
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as PlotPolygon
import numpy as np

from diagnose_precinct_matching import suffix
from eight_experiments_opening import (
    RAW, CONTESTS, parse_official_csv, validate_contests
)
from spatial_precinct_overlap import ROOT, fetch_shapes
from eight_experiments_maps import polygon_parts
from political_fault_lines import find_fault_lines

FIG = ROOT / "reports/figures"
OUT = ROOT / "data/processed"
PANEL = OUT / "seattle_mayor_precinct_panel_2021_2025.csv"
CROSSWALK = OUT / "precinct_to_cra_crosswalk.csv"
SUMMARY = OUT / "precinct_field_guide_summary.json"

INK = "#213b4b"
BLUE = "#315c84"
RUST = "#b96042"
NEUTRAL = "#eeeae1"
MISSING = "#dce3e6"
CAMP = LinearSegmentedColormap.from_list(
    "seattle_mayor", [BLUE, "#9ab8cd", NEUTRAL, "#dfb198", RUST], N=256
)
SWING = LinearSegmentedColormap.from_list(
    "vote_share_change", [BLUE, "#abc9d8", NEUTRAL, "#ddad96", RUST], N=256
)
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "DejaVu Sans"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_ballots_counted(path=RAW):
    """Election-administration metric, not two-finalist vote counts."""
    times = {}
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8-sig", newline="", errors="replace") as stream:
        for original in csv.DictReader(stream):
            r = {k.lower().replace(" ", ""): (v or "").strip()
                 for k, v in original.items() if k}
            if r.get("race") != "City of Seattle Mayor" or r.get("countergroup","Total") != "Total":
                continue
            if r.get("countertype") != "Times Counted":
                continue
            pid = suffix(r.get("precinct",""))
            if pid is None:
                continue
            if pid in times:
                raise ValueError(f"Duplicate ballot count for precinct {pid}")
            times[pid] = int(r["sumofcount"].replace(",",""))
    return times


def read_precinct_names(path=RAW):
    """Use full, official identifiers such as SEA 46-2373, not numeric-only IDs."""
    names={}
    with path.open(encoding="utf-8-sig",newline="",errors="replace") as source:
        for record in csv.DictReader(source):
            if (record.get("Race")!="City of Seattle Mayor" or
                    record.get("CounterGroup","Total")!="Total" or
                    record.get("CounterType")!="Registered Voters"):
                continue
            name=record["Precinct"].strip()
            pid=suffix(name)
            if pid is None:
                continue
            if pid in names and names[pid]!=name:
                raise ValueError(f"Conflicting precinct name for {pid}")
            names[pid]=name
    return names


def summarize_precincts(votes, registered, polygons, ballots, names=None):
    race, wilson, harrell, *_ = CONTESTS[0]
    rows = []
    for pid, choices in votes[race].items():
        w, h = choices.get(wilson, 0), choices.get(harrell, 0)
        if pid not in polygons:
            raise ValueError(f"Missing official 2025 boundary for {pid}")
        if w+h <= 0:
            continue
        reg = registered.get(pid)
        if reg is None or reg <= 0:
            raise ValueError(f"Missing registered-voter record for {pid}")
        rows.append(dict(
            precinct_id=pid,
            precinct_name=(names or {}).get(pid,f"SEA precinct {pid}"),
            wilson_votes=w,
            harrell_votes=h,
            finalist_votes=w+h,
            harrell_pct=100*h/(w+h),
            registered=reg,
            counted=ballots.get(pid),
            # 2025 polygons are EPSG:2926, US survey feet. Includes water.
            area_sqmi=float(polygons[pid].area)/(5280**2),
        ))
    rows.sort(key=lambda r:int(r["precinct_id"]))
    if len(rows)<950:
        raise ValueError(f"Only {len(rows)} eligible 2025 precincts")
    if len(rows)>1200:
        raise ValueError("Unexpected Seattle precinct count")
    if sum(r["harrell_votes"] for r in rows)!=136920 or sum(r["wilson_votes"] for r in rows)!=138931:
        raise ValueError("Precinct summary did not reconcile to certified candidate totals")
    if ballots and len(ballots)<len(rows)*.95:
        raise ValueError(f"Ballot count coverage {len(ballots)} insufficient")
    return rows


def model_2021_panel(panel,valid_2025):
    valid={r["precinct_id"] for r in valid_2025}
    clean={}
    for row in panel:
        pid=row["precinct_id"]
        if row["stable_boundary"]!="True" or pid not in valid:
            continue
        n25=int(row["two_candidate_votes_2025"])
        n21=int(row["two_candidate_votes_2021"])
        if n25<100 or n21<100:
            continue
        if pid in clean:
            raise ValueError(f"Duplicate historic precinct {pid}")
        clean[pid]=dict(
            precinct_id=pid,area_name=row["cra_name"],
            harrell_2021=float(row["harrell_share_2021"])*100,
            harrell_2025=float(row["harrell_share_2025"])*100,
            change_pp=100*(float(row["harrell_share_2025"]) - float(row["harrell_share_2021"])),
            votes_2025=n25,
        )
    if len(clean)<750:
        raise ValueError("Insufficient stable, comparable historical precincts")
    return clean


def ordered_quantiles(values):
    if not values:
        raise ValueError("Empty statistic")
    return {str(p):round(float(np.quantile(values,p)),3)
            for p in (0,.25,.5,.75,1)}


def neighborhood_stats(panel,minimum_votes=100,minimum_precincts=8):
    grouped={}
    for r in panel:
        if r["stable_boundary"]!="True":
            continue
        v=int(r["two_candidate_votes_2025"])
        if v<minimum_votes:
            continue
        grouped.setdefault(r["cra_name"],[]).append(
            (float(r["harrell_share_2025"])*100,v,r["precinct_id"])
        )
    output=[]
    for name,measurements in grouped.items():
        if len(measurements)<minimum_precincts:
            continue
        pct=np.array([x[0] for x in measurements])
        weights=np.array([x[1] for x in measurements])
        mean=float(np.average(pct,weights=weights))
        sd=float(np.sqrt(np.average((pct-mean)**2,weights=weights)))
        typical=float(np.average(np.abs(pct-mean),weights=weights))
        output.append(dict(
            name=name,precincts=len(measurements),
            mean_harrell_pct=round(mean,1),
            weighted_sd_pp=round(sd,1),
            typical_gap_pp=round(typical,1),
            finalist_votes=int(np.sum(weights)),
            min_harrell_pct=round(float(min(pct)),1),
            max_harrell_pct=round(float(max(pct)),1),
        ))
    return sorted(output,key=lambda x:-x["typical_gap_pp"])


def build_summary(rows,historical,neighborhoods,lines,ballots,official_precinct_total=None):
    reg=np.array([x["registered"] for x in rows],dtype=int)
    physical=np.array([x["area_sqmi"] for x in rows],dtype=float)
    top_reg=sorted(rows,key=lambda r:-r["registered"])[:5]
    top_area=sorted(rows,key=lambda r:-r["area_sqmi"])[:5]
    with_ballots=[r for r in rows if r["counted"] is not None]
    big_votes=sorted(with_ballots,key=lambda r:-r["counted"])[:5]
    shifts=[r["change_pp"] for r in historical.values()]
    historic_majority_flips=sum(
        (r["harrell_2021"]-50)*(r["harrell_2025"]-50)<0
        for r in historical.values()
    )
    thresh=float(np.quantile([r["difference_pp"] for r in lines],.99))
    high=[r for r in lines if r["difference_pp"]>=thresh-1e-7]
    return dict(
        precinct_count=len(rows),
        official_precinct_total=official_precinct_total or len(rows),
        official_geometry_count=len(set(rows and [r["precinct_id"] for r in rows])),
        historical_comparable_count=len(historical),
        precinct_population_2025={
            "registered_quantiles":ordered_quantiles(reg.tolist()),
            "geographic_sqmi_quantiles":ordered_quantiles(physical.tolist()),
            "ballot_counted_coverage":len(with_ballots),
            "top_registered":top_reg,
            "top_geographic_area":top_area,
            "top_ballots_cast":big_votes,
            "registered_over_900":int(np.count_nonzero(reg>900)),
        },
        history={
            "comparable_precincts_min100_both":len(historical),
            "harrell_majority_crossovers":historic_majority_flips,
            "median_change_pp":round(float(np.median(shifts)),2),
            "median_absolute_change_pp":round(float(np.median(np.abs(shifts))),2),
        },
        neighborhoods=neighborhoods,
        boundary={
            "eligible_borders":len(lines),
            "median_gap_pp":round(float(np.median([r["difference_pp"] for r in lines])),2),
            "p99_gap_pp":round(thresh,2),
            "count_above_p99":len(high),
            "top_10":lines[:10],
        }
    )


def add_precinct_patch(polygons,by_id,colors,color_by_value=None,
                       simplification_feet=35):
    patches=[]
    face=[]
    for pid,polygon in polygons.items():
        value=by_id.get(pid)
        color=(colors if value is None or color_by_value is None
               else color_by_value(value))
        for p in polygon_parts(polygon.simplify(simplification_feet,preserve_topology=True)):
            xy=np.asarray(p.exterior.coords)
            if len(xy)<4:continue
            patches.append(PlotPolygon(xy,closed=True))
            face.append(color)
    return patches,face


def plot_2025_map(polygons,rows,path):
    data={r["precinct_id"]:r["harrell_pct"] for r in rows}
    norm=TwoSlopeNorm(vmin=0,vcenter=50,vmax=100)
    patches,face=add_precinct_patch(
        polygons,data, MISSING,
        color_by_value=lambda value:CAMP(norm(value))
    )
    fig,ax=plt.subplots(figsize=(10.3,11.6))
    ax.add_collection(PatchCollection(patches,facecolors=face,
                                     edgecolors="white",linewidths=.10))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    cb=fig.colorbar(plt.cm.ScalarMappable(cmap=CAMP,norm=norm),ax=ax,
        orientation="horizontal",fraction=.045,pad=.015,shrink=.74)
    cb.set_ticks([0,25,50,75,100])
    cb.set_ticklabels(["0%","25%","50%","75%","100%"])
    cb.set_label("Share of votes cast for Harrell among Harrell + Wilson ballots",fontsize=10)
    fig.suptitle("2025 Seattle mayoral vote by precinct",x=.05,y=.98,
                 ha="left",fontsize=19,weight="bold",color=INK)
    fig.text(.08,.085,"DEEP BLUE = STRONGER WILSON     ·     LIGHT = CLOSE     ·     RUST = STRONGER HARRELL",
            fontsize=9,color=INK)
    fig.text(.08,.06,"King County certified November 2025 precinct results. "
             "Colors reflect candidate share, not party affiliation.",fontsize=9,color="#667c88")
    fig.subplots_adjust(left=.02,right=.98,top=.93,bottom=.14)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,dpi=165,bbox_inches="tight",format="png")
    plt.close(fig)


def plot_anatomy(rows,path):
    registrations=np.array([r["registered"] for r in rows])
    areas=np.array([r["area_sqmi"] for r in rows])
    fig,ax=plt.subplots(1,2,figsize=(12.3,4.6))
    ax[0].hist(registrations,bins=np.arange(0,1251,50),
               color=BLUE,edgecolor="white",linewidth=.5)
    ax[0].axvline(np.median(registrations),color=RUST,lw=2.2,
                  label=f"Median: {np.median(registrations):,.0f}")
    ax[0].axvline(900,color="#465969",lw=1.5,ls="--",label="900 active-voter legal threshold")
    ax[0].set_xlabel("Registered voters per 2025 precinct")
    ax[0].set_ylabel("Number of precincts")
    ax[0].legend(frameon=False,fontsize=9)
    # Linear, in physical square miles. A final bin keeps unusual water/park
    # precincts visible without compressing 95% of city precincts.
    max_regular=.4
    edges=np.arange(0,max_regular+.0201,.02)
    display=np.minimum(areas,max_regular+.01)
    edges=np.append(edges,[max_regular+.05])
    ax[1].hist(display,bins=edges,color="#b78264",edgecolor="white",linewidth=.5)
    ax[1].set_xlim(0,max_regular+.052)
    ax[1].set_xticks([0,.1,.2,.3,.4,.425],["0","0.1","0.2","0.3","0.4","0.4+"])
    ax[1].axvline(np.median(areas),color=BLUE,lw=2,
                  label=f"Median: {np.median(areas):.3f} sq mi")
    ax[1].set_xlabel("Area of official precinct polygon (square miles, linear scale)")
    ax[1].set_ylabel("Number of precincts")
    ax[1].legend(frameon=False,fontsize=9)
    for a in ax:
        a.spines[["top","right"]].set_visible(False)
        a.grid(axis="y",alpha=.16)
        a.set_axisbelow(True)
    fig.suptitle("Precincts vary in voters—and especially in geographic size",
                 x=.07,y=.98,ha="left",fontsize=17,weight="bold")
    fig.text(.07,.03,"Polygon area includes water; it is not necessarily dry land. "
             "Registered-voter counts are from the election returns, not necessarily the boundary-adoption date.",
             fontsize=9,color="#5d7482")
    fig.subplots_adjust(left=.09,right=.97,top=.81,bottom=.20,wspace=.32)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)


def plot_neighborhoods(neighborhoods,path):
    # Highlight contrasting cases without ranking tiny or unverified CRA samples.
    selected=neighborhoods[:10]
    special=next((x for x in neighborhoods if x["name"]=="Capitol Hill"),None)
    if special and all(x["name"]!=special["name"] for x in selected):
        selected.append(special)
    fig,ax=plt.subplots(figsize=(11.1,7.2))
    y=np.arange(len(selected))
    vals=[r["typical_gap_pp"] for r in selected]
    colors=[BLUE if r["name"]=="Capitol Hill" else RUST if r["name"]=="Queen Anne"
            else "#789bab" for r in selected]
    ax.barh(y,vals,color=colors,height=.65)
    ax.set_yticks(y,[f"{r['name']} · {r['precincts']} precincts · {r['finalist_votes']:,} votes" for r in selected],fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0,max(vals)*1.25)
    ax.set_xlabel("Typical precinct difference from its area average (percentage points)")
    ax.set_title("Which neighborhood areas vary most from precinct to precinct?",
                 loc="left",fontweight="bold",fontsize=16,pad=19)
    for i,v in enumerate(vals):
        ax.text(v+.25,i,f"{v:.1f}",va="center",fontsize=10)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=9)
    ax.grid(axis="x",alpha=.17);ax.set_axisbelow(True)
    fig.text(.02,.035,
             "Same-boundary precincts; area must have at least eight precincts and 100 finalist votes per precinct.\\n"
             "The typical gap describes the vote-weighted average distance from the area's mean.",
             fontsize=9,color="#557080")
    fig.subplots_adjust(left=.48,right=.97,top=.87,bottom=.15)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)


def plot_historical_change(polygons,historical,path):
    vals={k:v["change_pp"] for k,v in historical.items()}
    norm=TwoSlopeNorm(vmin=-30,vcenter=0,vmax=30)
    patches,colors=add_precinct_patch(polygons,vals,MISSING,
            color_by_value=lambda v:SWING(norm(np.clip(v,-30,30))))
    fig,ax=plt.subplots(figsize=(10.3,11.6))
    ax.add_collection(PatchCollection(patches,facecolors=colors,
                                     edgecolors="white",linewidths=.09))
    ax.autoscale_view();ax.set_aspect("equal");ax.axis("off")
    cb=fig.colorbar(plt.cm.ScalarMappable(cmap=SWING,norm=norm),
                    ax=ax,orientation="horizontal",fraction=.045,pad=.015,shrink=.74)
    cb.set_ticks([-30,-15,0,15,30])
    cb.set_ticklabels(["−30","−15","0","+15","+30"])
    cb.set_label("Change in Harrell's two-finalist share (percentage points)",fontsize=10)
    fig.suptitle("How did Harrell's support change from 2021 to 2025?",
                 x=.05,y=.98,ha="left",fontsize=18,weight="bold")
    fig.text(.07,.085,"BLUE = LOWER 2025 SHARE    ·    RUST = HIGHER 2025 SHARE    ·    GRAY = NOT COMPARABLE",
             fontsize=9,color=INK)
    fig.text(.07,.06,"Only precincts verified to have stable boundaries and at least 100 finalist votes "
             "in both elections.\n"
             "Different opponents (Lorena González in 2021, Katie Wilson in 2025); not individual voter switching.",
             fontsize=9,color="#5a7180")
    fig.subplots_adjust(left=.02,right=.98,top=.93,bottom=.14)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="png",dpi=165,bbox_inches="tight")
    plt.close(fig)


def plot_boundaries(lines,area_names,path):
    top=lines[:11]
    fig,ax=plt.subplots(figsize=(11.2,7.2))
    y=np.arange(len(top))
    x=[r["difference_pp"] for r in top]
    labels=[]
    for r in top:
        a,b=r["precinct_a"],r["precinct_b"]
        name_a,name_b=area_names.get(a),area_names.get(b)
        area=name_a if name_a and name_a==name_b else (name_a or name_b or "Seattle")
        labels.append(f"{area} · {a} / {b}")
    ax.barh(y,x,height=.65,color=[RUST if {"1709","1724"}=={r["precinct_a"],r["precinct_b"]}
                else "#5b8aa1" for r in top])
    ax.set_yticks(y,labels,fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0,max(x)*1.25)
    for i,v in enumerate(x):
        ax.text(v+.6,i,f"{v:.1f} pp",va="center",fontsize=10)
    ax.set_xlabel("Absolute difference in Harrell vote share across a shared boundary")
    ax.set_title("The sharpest voting differences across a precinct border",
                 loc="left",fontsize=16,fontweight="bold",pad=20)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=7)
    ax.grid(axis="x",alpha=.17);ax.set_axisbelow(True)
    fig.text(.025,.025,"Eligible pairs share at least 100 ft of boundary; both have at least "
             "100 Harrell + Wilson votes. Ranked by absolute 2025 vote-share difference.\n"
             "Some location labels use a single known community area; numeric precinct IDs are definitive.",
             fontsize=9,color="#567080")
    fig.subplots_adjust(left=.36,right=.96,top=.86,bottom=.15)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)


def main():
    if not RAW.is_file():
        raise FileNotFoundError("Run diagnose_precinct_matching.py first")
    v,registered=parse_official_csv(RAW)
    validate_contests(v)
    polys=fetch_shapes(2025)
    counted=read_ballots_counted()
    rows=summarize_precincts(v,registered,polys,counted,read_precinct_names())
    panel=read_csv(PANEL)
    stable=model_2021_panel(panel,rows)
    neighborhoods=neighborhood_stats(panel)
    raw_votes={}
    race,wilson,harrell,*_=CONTESTS[0]
    for pid,options in v[race].items():
        raw_votes[pid]={"Katie Wilson":options.get("Katie Wilson",0),
                        "Bruce Harrell":options.get("Bruce Harrell",0)}
    lines=find_fault_lines(polys,raw_votes,min_votes=100,min_border_feet=100)
    if len(lines)<2000:
        raise ValueError("Too few spatial adjacency comparisons")
    names={r["precinct_id"]:r["cra_name"] for r in panel}
    summary=build_summary(rows,stable,neighborhoods,lines,counted,len(v[race]))
    summary["official_winner"]={"Wilson":138931,"Harrell":136920}
    summary["historical_2021_opponent"]="Lorena González"
    summary["source_dates"]="2021 and 2025 certified general elections"
    OUT.mkdir(parents=True,exist_ok=True)
    SUMMARY.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    with (OUT/"precinct_field_guide_boundaries.csv").open("w",newline="",encoding="utf-8") as file:
        writer=csv.DictWriter(file,fieldnames=list(lines[0]))
        writer.writeheader()
        writer.writerows(lines)
    FIG.mkdir(parents=True,exist_ok=True)
    plot_2025_map(polys,rows,FIG/"precinct_2025_mayoral_gradient.png")
    plot_anatomy(rows,FIG/"precinct_size_distributions.svg")
    plot_neighborhoods(neighborhoods,FIG/"precinct_neighborhood_variation.svg")
    plot_historical_change(polys,stable,FIG/"precinct_2021_to_2025_harrell_change.png")
    plot_boundaries(lines,names,FIG/"precinct_sharp_boundaries.svg")
    print("Summary precincts:",summary["precinct_count"])
    print("Registered median:",summary["precinct_population_2025"]["registered_quantiles"]["0.5"])
    print("Boundary comparisons:",summary["boundary"]["eligible_borders"])
    print("Historical precincts:",summary["historical_comparable_count"])
    print("Graphics: five new figures generated")


if __name__=="__main__":
    main()
