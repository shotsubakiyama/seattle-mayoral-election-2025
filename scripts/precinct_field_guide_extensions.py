"""Extra maps and grounded supporting tables for Seattle, Precinct by Precinct.

Uses *the same* official 2025 mayoral precinct votes/polygons as the main guide.
Historical boundary counts are queried from archived King County ArcGIS layers.
No assumptions that precinct count rose monotonically.
"""
import csv
import json
import math
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as PlotPolygon
from matplotlib.lines import Line2D
import numpy as np
from scipy.spatial import cKDTree
from spatial_precinct_overlap import ROOT,fetch_shapes
from eight_experiments_opening import RAW,CONTESTS,parse_official_csv,validate_contests
from eight_experiments_maps import polygon_parts
from precinct_field_guide import (
    CAMP,BLUE,RUST,INK,NEUTRAL,FIG,OUT,PANEL,CROSSWALK,
    SUMMARY,read_csv,model_2021_panel,summarize_precincts,read_ballots_counted,
)
OUTFILE=OUT/"precinct_field_guide_extensions.json"
GROUPS=OUT/"experiment_07_precinct_electoral_communities.csv"
HISTORY_YEARS=(2001,2005,2010,2015,2020,2021,2025)
ROOT_URL="https://services.arcgis.com/Ej0PsM5Aw677QF1W/ArcGIS/rest/services"


def historical_counts(years=HISTORY_YEARS):
    """Archived *boundary* counts, not counts of ballots in an election.

    Services are the year-stamped VOTDST layers listed in King County's GIS catalog.
    Each query counts NAME LIKE 'SEA %', the same name criterion as the current maps.
    """
    values=[]
    for year in years:
        dataset=f"VOTDST_{year}_AREA_{3044+year-2000}" if year!=2025 else "VOTDST_2025_AREA_3072"
        service=f"{ROOT_URL}/{dataset}/FeatureServer/0/query"
        params=urllib.parse.urlencode(dict(where="NAME LIKE 'SEA %'",
                  returnCountOnly="true",f="json"))
        req=urllib.request.Request(service+"?"+params,
                headers={"User-Agent":"SeattlePrecinctResearch/1.0 (public archive analysis)"})
        with urllib.request.urlopen(req,timeout=25) as response:
            data=json.loads(response.read().decode("utf-8"))
        n=data.get("count")
        if data.get("error") or not isinstance(n,int) or n<500 or n>1400:
            # Earlier archived layers do not all have the modern NAME field.
            # Search a layer's published schema for a comparable precinct-name
            # field. Never silently substitute a countywide count.
            meta_request=urllib.request.Request(
                f"{ROOT_URL}/{dataset}/FeatureServer/0?f=json",
                headers={"User-Agent":"SeattlePrecinctResearch/1.0"})
            with urllib.request.urlopen(meta_request,timeout=25) as response:
                meta=json.loads(response.read().decode("utf-8"))
            fields=[f["name"] for f in meta.get("fields",[])]
            for field in fields:
                canonical=field.upper().replace("_","")
                if field.upper()=="NAME" or canonical in (
                       "PRECINCTNAME","VOTDSTNAME","PRECINCT","VOTINGPRECINCTNAME"):
                    if field.upper()=="NAME":
                        continue
                    params2=urllib.parse.urlencode(dict(
                        where=f"{field} LIKE 'SEA %'",
                        returnCountOnly="true",f="json"))
                    request2=urllib.request.Request(service+"?"+params2,
                        headers={"User-Agent":"SeattlePrecinctResearch/1.0"})
                    with urllib.request.urlopen(request2,timeout=25) as response:
                        alternative=json.loads(response.read().decode("utf-8"))
                    alt=alternative.get("count")
                    if isinstance(alt,int) and 500<=alt<=1400:
                        n=alt
                        break
            if not isinstance(n,int) or n<500 or n>1400:
                print(f"Skipping {year}: no comparable SEA-prefixed name field in {fields}")
                continue
        values.append(dict(year=year,seattle_precincts=n,url=f"{ROOT_URL}/{dataset}/FeatureServer/0"))
    if len(values)<min(2,len(years)):
        raise ValueError("Too few verified historic Seattle precinct snapshots")
    if 2025 in years and (values[-1]["year"]!=2025 or
                          values[-1]["seattle_precincts"] not in range(1017,1022)):
        raise ValueError("2025 GIS count differs unexpectedly from certified 2025 results")
    return values


def plot_count_history(rows,path):
    x=np.array([r["year"] for r in rows]);y=np.array([r["seattle_precincts"] for r in rows])
    fig,ax=plt.subplots(figsize=(10.4,4.6))
    ax.plot(x,y,marker="o",ms=8,lw=2.8,color=BLUE)
    for year,count in zip(x,y):
        ax.annotate(f"{count:,}",(year,count),xytext=(0,11),
                    textcoords="offset points",ha="center",fontsize=10,color=INK,
                    fontweight="bold")
    lo=max(0,int(y.min()//100*100)-80)
    hi=int(y.max()//100*100)+150
    ax.set_ylim(lo,hi)
    ax.set_xticks(x)
    ax.set_ylabel("Seattle precincts in archived GIS snapshots")
    ax.set_title("How Seattle's precinct count has changed",loc="left",
                 fontsize=16,fontweight="bold",pad=20)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
    fig.text(.045,.015,"Official King County year-specific voting-district GIS layers; "
             "counts are historical map snapshots, not a continuous population measure.\n"
             "Boundaries change with redistricting and administrative balancing. Different years do not imply identical polygons.",
             fontsize=9,color="#597083")
    fig.subplots_adjust(left=.1,right=.97,top=.79,bottom=.21)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)


def enrich_area_location(summary,polygons,area_names):
    """Approximate a missing name from nearby named precincts, not a fake formal assignment."""
    named={pid:name for pid,name in area_names.items() if name and pid in polygons}
    ids=list(named)
    centers=np.array([(polygons[pid].representative_point().x,
                       polygons[pid].representative_point().y) for pid in ids])
    tree=cKDTree(centers)
    for entry in summary["precinct_population_2025"]["top_geographic_area"]:
        pid=entry["precinct_id"]
        if pid in named:
            entry["near_area"]=named[pid]
            entry["area_label_quality"]="assigned community area"
        else:
            pt=polygons[pid].representative_point()
            dist,neighbors=tree.query([pt.x,pt.y],k=min(5,len(ids)))
            if np.isscalar(neighbors):
                neighbors=[int(neighbors)]
            labels=Counter(named[ids[int(i)]] for i in neighbors)
            label=labels.most_common(1)[0][0]
            entry["near_area"]=label
            entry["area_label_quality"]="approximate from nearby labeled precincts"
    return summary


def plot_voter_bubble_comparison(polygons,rows,path):
    """A *symbol-size* cartogram: circle area is proportional to FINALIST votes.

    This deliberately does not shift or distort precinct boundaries. Circles may
    overlap in dense areas; their centers are representative points, not household
    coordinates. Side by side map makes the point without false vote-location precision.
    """
    data={r["precinct_id"]:r for r in rows}
    norm=TwoSlopeNorm(vmin=0,vcenter=50,vmax=100)
    fig,axs=plt.subplots(1,2,figsize=(13.0,8.9))
    patches=[];colors=[]
    for pid,p in polygons.items():
        r=data.get(pid)
        col=CAMP(norm(r["harrell_pct"])) if r else "#e4e8eb"
        for polygon in polygon_parts(p.simplify(60,preserve_topology=True)):
            xy=np.asarray(polygon.exterior.coords)
            if len(xy)>=4:
                patches.append(PlotPolygon(xy))
                colors.append(col)
    axs[0].add_collection(PatchCollection(patches,facecolors=colors,
                                         edgecolors="white",linewidth=.10))
    axs[0].autoscale_view();axs[0].set_aspect("equal");axs[0].axis("off")
    cx=[];cy=[];sizes=[];face=[]
    for pid,r in data.items():
        center=polygons[pid].representative_point()
        cx.append(center.x);cy.append(center.y)
        sizes.append(r["finalist_votes"]*.19)
        face.append(CAMP(norm(r["harrell_pct"])))
    order=np.argsort(sizes)[::-1]
    axs[1].scatter(np.array(cx)[order],np.array(cy)[order],
                   s=np.array(sizes)[order],c=np.array(face)[order],
                   edgecolor="#ffffff",linewidth=.21,alpha=.92)
    axs[1].set_xlim(axs[0].get_xlim());axs[1].set_ylim(axs[0].get_ylim())
    axs[1].set_aspect("equal");axs[1].axis("off")
    axs[0].set_title("Precincts by land and water area",fontsize=12,weight="bold",pad=12)
    axs[1].set_title("Precincts sized by mayoral votes",fontsize=12,weight="bold",pad=12)
    fig.suptitle("The election looks different when each precinct is sized by its votes",
                 x=.035,y=.98,ha="left",weight="bold",fontsize=17)
    bar=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=CAMP),
                     ax=axs,orientation="horizontal",fraction=.034,pad=.035,shrink=.62)
    bar.set_ticks([0,25,50,75,100])
    bar.set_ticklabels(["0%","25%","50%","75%","100%"])
    bar.set_label("Harrell's share of Harrell + Wilson votes",fontsize=10)
    fig.text(.06,.025,"Each circle represents one precinct; circle AREA is proportional to its "
             "Harrell + Wilson vote count. Circles are centered inside precinct polygons\n"
             "and can overlap. This is a schematic symbol map, not a map of actual voter addresses.",
             fontsize=9,color="#5c7482")
    fig.subplots_adjust(left=.02,right=.98,top=.90,bottom=.14,wspace=.035)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="png",dpi=165,bbox_inches="tight")
    plt.close(fig)


def plot_change_distribution(historical,path):
    changes=np.array([r["change_pp"] for r in historical.values()],dtype=float)
    down=int(np.sum(changes<-.01));up=int(np.sum(changes>.01))
    fig,ax=plt.subplots(figsize=(10.2,4.8))
    bins=np.arange(-32,19,2)
    ax.hist(changes,bins=bins,color=BLUE,edgecolor="white",linewidth=.8)
    ax.axvline(0,color=INK,lw=1.6)
    ax.axvline(np.median(changes),color=RUST,lw=2.5,
               label=f"Median shift: {np.median(changes):+.1f} points")
    ax.set_xlabel("2025 minus 2021 Harrell two-finalist share (percentage points)")
    ax.set_ylabel("Comparable precincts")
    ax.set_title("Harrell's vote share declined in most comparable precincts",
                 loc="left",fontsize=17,fontweight="bold",pad=18)
    ax.legend(frameon=False)
    ax.spines[["top","right"]].set_visible(False);ax.grid(axis="y",alpha=.15)
    ax.set_axisbelow(True)
    fig.text(.03,.022,f"{down} precincts lower in 2025; {up} higher. "
             "Different opponents (Lorena González in 2021; Katie Wilson in 2025).\n"
             "Only validated same-boundary precincts with 100+ finalist votes in both years.",
             fontsize=9,color="#587282")
    fig.subplots_adjust(left=.09,right=.97,top=.82,bottom=.22)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight");plt.close(fig)
    return dict(declined=down,increased=up,total=len(changes),
                median_change_pp=round(float(np.median(changes)),2))


def cluster_totals(votes,path):
    """Aggregate actual 2025 mayoral votes by existing 11 Louvain groups.

    A group label is only a locator naming dominant community reporting areas;
    it is NOT the algorithm's discovered name nor a formal district name.
    """
    group_rows=read_csv(GROUPS)
    cross={r["precinct_id"]:r["cra_name"] for r in read_csv(CROSSWALK)}
    race,wilson,harrell,*_=CONTESTS[0]
    acc=defaultdict(lambda:dict(wilson=0,harrell=0,precincts=0,known_places=Counter()))
    for row in group_rows:
        pid=row["precinct_id"];gid=int(row["electoral_group"])
        data=votes[race].get(pid,{})
        a,b=data.get(wilson,0),data.get(harrell,0)
        acc[gid]["wilson"]+=a
        acc[gid]["harrell"]+=b
        acc[gid]["precincts"]+=1
        if pid in cross:
            acc[gid]["known_places"][cross[pid]]+=a+b
    if len(acc)!=11:
        raise ValueError(f"Expected 11 Louvain communities, got {len(acc)}")
    groups=[]
    for gid,rows in sorted(acc.items()):
        n=rows["harrell"]+rows["wilson"]
        if n<1000:
            raise ValueError("Unexpectedly small computed cluster")
        names=[name for name,_ in rows["known_places"].most_common(2)]
        label=" / ".join(names) if names else "Area labels unavailable"
        groups.append(dict(id=gid,label=label,precincts=rows["precincts"],
                           harrell_votes=rows["harrell"],wilson_votes=rows["wilson"],
                           finalist_votes=n,
                           harrell_pct=round(100*rows["harrell"]/n,1),
                           wilson_pct=round(100*rows["wilson"]/n,1)))
    groups.sort(key=lambda x:-x["harrell_pct"])
    fig,ax=plt.subplots(figsize=(12.7,7.5))
    ids=np.arange(len(groups))
    harrell=np.array([r["harrell_pct"] for r in groups])
    ax.barh(ids,harrell,color=RUST,height=.69)
    ax.barh(ids,100-harrell,left=harrell,color=BLUE,height=.69)
    ax.axvline(50,color="#fff",lw=1.5,linestyle="--")
    ax.set_yticks(ids,[f"Group {r['id']+1}: {r['label']}" for r in groups],fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0,100)
    ax.set_xticks([0,25,50,75,100],["0%","25%","50%","75%","100%"])
    ax.set_xlabel("Share of Harrell + Wilson votes")
    ax.set_title("How the 11 computed communities voted",loc="left",
                 fontsize=17,fontweight="bold",pad=20)
    for i,r in enumerate(groups):
        ax.text(r["harrell_pct"]*.5,i,f"{r['harrell_pct']:.0f}% H",va="center",
                ha="center",fontsize=9,color="white" if r["harrell_pct"]>17 else INK)
        ax.text(r["harrell_pct"]+(100-r["harrell_pct"])/2,i,
                f"{r['wilson_pct']:.0f}% W",va="center",ha="center",fontsize=9,color="white")
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=9);ax.grid(axis="x",alpha=.1);ax.set_axisbelow(True)
    fig.text(.03,.028,"Names are informal locator labels from the two leading community reporting areas; "
             "groups are not legal election districts.\n"
             "Vote shares are computed from official 2025 mayoral votes in all grouped precincts.",
             fontsize=9,color="#5e7384")
    fig.subplots_adjust(left=.36,right=.97,top=.88,bottom=.16)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight");plt.close(fig)
    return groups


def main():
    vote,registered=parse_official_csv(RAW)
    validate_contests(vote)
    shapes=fetch_shapes(2025)
    voters=summarize_precincts(vote,registered,shapes,read_ballots_counted())
    historic=model_2021_panel(read_csv(PANEL),voters)
    history=historical_counts()
    area_names={r["precinct_id"]:r["cra_name"] for r in read_csv(CROSSWALK)}
    original=json.loads(SUMMARY.read_text(encoding="utf-8"))
    enrich_area_location(original,shapes,area_names)
    SUMMARY.write_text(json.dumps(original,indent=2)+"\n",encoding="utf-8")
    plot_count_history(history,FIG/"precinct_count_history.svg")
    plot_voter_bubble_comparison(shapes,voters,FIG/"precinct_vote_weighted_map.png")
    change=plot_change_distribution(historic,FIG/"precinct_2021_to_2025_distribution.svg")
    clusters=cluster_totals(vote,FIG/"precinct_cluster_vote_breakdown.svg")
    info=dict(precinct_count_history=history,change_distribution=change,
              groups=clusters)
    OUTFILE.write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    print("Historic count:",[(p["year"],p["seattle_precincts"]) for p in history])
    print("Change:",change)
    print("Groups:",[(g["id"],g["label"],g["harrell_pct"]) for g in clusters])


if __name__=="__main__":
    main()
