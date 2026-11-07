"""Extra reader-first views for the 2025 Seattle election experiments.

Experiment 1: Does support for Wilson track support in other citywide contests?
Experiment 3: Map model misses relative to geographic prediction intervals.
Experiment 8: What does voting information add beyond a geography-only network?

Uses verified existing precinct returns, polygon cache, and calibrated model.
Every result is descriptive at PRECINCT level, not individual voter behavior.
"""
import json
import csv
import math
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.patches import Patch, Polygon as PlotPolygon
from sklearn.metrics import adjusted_rand_score
from spatial_precinct_overlap import ROOT, fetch_shapes
from eight_experiments_opening import RAW,CONTESTS,parse_official_csv,validate_contests
from eight_experiments_stats import MODEL,read_csv,three_way_intervals
from eight_experiments_maps import (
    election_feature_matrix,precinct_edges,create_similarity_graph,detect_communities,
    polygon_parts,segment_lines
)

FIG=ROOT/"reports/figures"
OUT=ROOT/"data/processed"
BLUE="#357f9f";ORANGE="#c77e49";INK="#253d50";GRAY="#dde6eb"
plt.rcParams["svg.fonttype"]="none"

def cross_race_alignment(x):
    if x.ndim!=2 or x.shape[1]!=6 or not np.isfinite(x).all():
        raise ValueError("Expected complete six-contest support shares")
    y=x[:,0]
    result=[]
    for j in range(1,6):
        other=x[:,j]
        rho=float(np.corrcoef(y,other)[0,1])
        valid=((y!=.5)&(other!=.5))
        mismatch=int(np.count_nonzero((y[valid]>.5)!=(other[valid]>.5)))
        result.append(dict(contest=CONTESTS[j][5],correlation=round(rho,3),
                different_majority_pct=round(100*mismatch/int(valid.sum()),1),
                valid_precincts=int(valid.sum())))
    return result

def plot_alignment(rows,path):
    labels=[r["contest"] for r in rows]
    r=np.array([d["correlation"] for d in rows])
    differences=np.array([d["different_majority_pct"] for d in rows])
    y=np.arange(len(rows))
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12.1,5.6),
        gridspec_kw={"width_ratios":[1.13,1]})
    ax1.hlines(y,0,r,color="#bed3df",linewidth=7)
    ax1.scatter(r,y,s=80,color=BLUE,zorder=3)
    ax1.axvline(0,color="#8497a6",lw=.7)
    ax1.set_xlim(-.15,1.14)
    ax1.set_yticks(y,labels,fontsize=11)
    ax1.invert_yaxis()
    ax1.set_xticks([0,.25,.5,.75,1])
    ax1.set_xlabel("Correlation with Wilson's precinct vote share")
    ax1.set_title("Do neighborhood patterns move together?",loc="left",
                  fontsize=12,fontweight="bold",pad=15)
    for i,v in enumerate(r):
        ax1.text(v+.035,i,f"{v:.2f}",va="center",fontsize=11,fontweight="bold",color=INK)
    ax2.barh(y,differences,color=ORANGE,height=.56)
    ax2.set_yticks(y,[""]*len(rows))
    ax2.set_xlim(0,104)
    ax2.invert_yaxis()
    ax2.set_xticks([0,25,50,75,100])
    ax2.set_xlabel("Precincts where Wilson and this option\nhad different majority outcomes (%)")
    ax2.set_title("Where did those majorities diverge?",loc="left",
                  fontsize=12,fontweight="bold",pad=15)
    for i,v in enumerate(differences):
        ax2.text(v+1,i,f"{v:.1f}%",va="center",fontsize=10,color=INK)
    for ax in (ax1,ax2):
        ax.spines[["top","right","left"]].set_visible(False)
        ax.grid(axis="x",color="#e5ebef",lw=.7)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y",length=0)
    fig.suptitle("Which races tracked the mayor's precinct-level coalition?",
        x=.025,y=.98,ha="left",fontsize=17,fontweight="bold")
    fig.text(.025,.055,
             "Each point is a Seattle precinct with valid votes in all six contests. "
             "Correlation describes places, NOT linked individual ballots.\n"
             "Different-majority means Wilson did not win the same precinct where this candidate or Yes option received >50%.",
             fontsize=9,color="#526d7d")
    fig.subplots_adjust(left=.16,right=.96,top=.76,bottom=.27,wspace=.29)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="svg",bbox_inches="tight")
    plt.close(fig)

def miss_categories(rows,expected,low,high):
    if not (len(rows)==len(expected)==len(low)==len(high)):
        raise ValueError("Length mismatch")
    categories={}
    for i,r in enumerate(rows):
        true=float(r["actual_harrell_share"])
        diff=true-expected[i]
        radius=high[i]-expected[i] if diff>=0 else expected[i]-low[i]
        score=abs(diff)/max(radius,1e-6)
        categories[r["precinct_id"]]=(0 if score<=.5 else 1 if score<=1 else 2)
    return categories

def plot_miss_map(shapes,categories,path):
    palette=["#bad6e2","#edce9d","#c86f4c","#e9eef1"]
    patches=[];values=[]
    for pid,shape in shapes.items():
        idx=categories.get(pid,3)
        for polygon in polygon_parts(shape.simplify(40,preserve_topology=True)):
            patches.append(PlotPolygon(np.asarray(polygon.exterior.coords),closed=True))
            values.append(palette[idx])
    fig,ax=plt.subplots(figsize=(9.6,10.2))
    ax.add_collection(PatchCollection(patches,facecolor=values,
                                     edgecolor="white",linewidth=.08))
    ax.autoscale_view();ax.set_aspect("equal");ax.axis("off")
    counts=Counter(categories.values())
    fig.suptitle("Where did November depart most from our prediction?",
                 x=.03,y=.97,ha="left",fontsize=17,fontweight="bold")
    legend=[
        Patch(facecolor=palette[0],label="Small miss (inside half the range)"),
        Patch(facecolor=palette[1],label="Moderate miss (within the range)"),
        Patch(facecolor=palette[2],label="Outside the 90%-target range"),
        Patch(facecolor=palette[3],label="Not modeled"),
    ]
    fig.legend(handles=legend,loc="lower center",bbox_to_anchor=(.5,.08),
               ncol=2,frameon=False,fontsize=10)
    fig.text(.05,.035,
             f"{counts[2]:,} of {len(categories):,} modeled precincts fell outside their held-out prediction range.\n"
             "A darker color indicates a larger *model miss*, not a less predictable neighborhood in every election.",
             color="#567082",fontsize=10)
    fig.subplots_adjust(left=.005,right=.995,top=.92,bottom=.17)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="png",dpi=180,bbox_inches="tight")
    plt.close(fig)
    return {"small_misses":counts[0],"moderate_misses":counts[1],
            "outside_range":counts[2],"modeled":len(categories)}

def electoral_cohesion(x,membership):
    labels=np.array([membership[i] for i in range(len(x))])
    grand=float(((x-x.mean(axis=0))**2).sum())
    within=0.
    for group in np.unique(labels):
        part=x[labels==group]
        within+=float(((part-part.mean(axis=0))**2).sum())
    return within/grand

def geography_only_comparison(x,edges,vote_groups):
    g=nx.Graph()
    g.add_nodes_from(range(len(x)))
    for i,j,_ in edges:
        g.add_edge(i,j,weight=1.0)
    target=len(set(vote_groups.values()))
    resolutions=[.38,.45,.52,.6,.62,.7,.78,.88,1.,1.1,1.25]
    scenarios=[(r,detect_communities(g,resolution=r,seed=2025)) for r in resolutions]
    resolution,geo=min(scenarios,key=lambda item:(abs(len(set(item[1].values()))-target),
                                                  abs(item[0]-.62)))
    changed=[(geo[a]==geo[b])!=(vote_groups[a]==vote_groups[b]) for a,b,_ in edges]
    divided_both=[geo[a]!=geo[b] and vote_groups[a]!=vote_groups[b] for a,b,_ in edges]
    same_both=[geo[a]==geo[b] and vote_groups[a]==vote_groups[b] for a,b,_ in edges]
    label_geo=[geo[i] for i in range(len(x))]
    label_vote=[vote_groups[i] for i in range(len(x))]
    coh_g=electoral_cohesion(x,geo);coh_v=electoral_cohesion(x,vote_groups)
    summary=dict(
        precincts=len(x),shared_borders=len(edges),
        geography_only_groups=len(set(label_geo)),voting_informed_groups=target,
        geography_only_resolution=resolution,
        border_status_changes_pct=round(100*np.mean(changed),1),
        always_dividing_pct=round(100*np.mean(divided_both),1),
        always_together_pct=round(100*np.mean(same_both),1),
        adjusted_rand_geography_vs_voting=round(float(adjusted_rand_score(label_geo,label_vote)),3),
        geography_only_within_vote_variance_pct=round(coh_g*100,1),
        vote_informed_within_vote_variance_pct=round(coh_v*100,1),
    )
    return geo,summary

def plot_geography_vs_vote(shapes,ids,edges,geography_groups,vote_groups,summary,path):
    # One map: highlight boundaries whose SAME/DIFFERENT status changes after voting features are added.
    colors={"Only with votes":"#c66a3e","Consistent division":"#365b70"}
    lines={k:[] for k in colors}
    patches=[]
    for pid in ids:
        for p in polygon_parts(shapes[pid].simplify(50,preserve_topology=True)):
            patches.append(PlotPolygon(np.asarray(p.exterior.coords),closed=True))
    for i,j,_ in edges:
        baseline=geography_groups[i]==geography_groups[j]
        vote=vote_groups[i]==vote_groups[j]
        if baseline!=vote:
            label="Only with votes"
        elif not baseline and not vote:
            label="Consistent division"
        else:
            continue
        shared=shapes[ids[i]].boundary.intersection(shapes[ids[j]].boundary)
        for seg in segment_lines(shared.simplify(65,preserve_topology=True)):
            lines[label].append(seg)
    fig,ax=plt.subplots(figsize=(10.2,10.3))
    ax.add_collection(PatchCollection(patches,facecolor="#f6f8f9",
                         edgecolor="#dde4e8",linewidth=.16,zorder=1))
    for label in ("Consistent division","Only with votes"):
        if lines[label]:
            ax.add_collection(LineCollection(lines[label],colors=colors[label],
                linewidths=.8 if label=="Consistent division" else 1.35,zorder=3))
    ax.autoscale_view();ax.set_aspect("equal");ax.axis("off")
    fig.suptitle("Which political borders appear when we add votes to the map?",
                 x=.04,y=.965,ha="left",fontweight="bold",fontsize=17)
    fig.legend(handles=[Patch(facecolor=colors[k],label=k) for k in colors],
               loc="lower center",bbox_to_anchor=(.5,.09),ncol=2,
               frameon=False,fontsize=11)
    fig.text(.06,.045,
             f"{summary['border_status_changes_pct']:.1f}% of shared precinct borders changed same-group status between "
             "geography-only and geography+votes clusters.\n"
             "Both models start from identical precinct polygons; political features only alter the strength of connections.",
             fontsize=9,color="#547082")
    fig.subplots_adjust(left=.01,right=.99,top=.91,bottom=.16)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format="png",dpi=170,bbox_inches="tight")
    plt.close(fig)

def main():
    if not RAW.exists():
        raise FileNotFoundError("Run scripts/eight_experiments_opening.py first")
    votes,_=parse_official_csv(RAW)
    validate_contests(votes)
    shapes=fetch_shapes(2025)
    ids,x=election_feature_matrix(votes,shapes)
    alignment=cross_race_alignment(x)
    plot_alignment(alignment,FIG/"experiment_01_precinct_correlations.svg")
    rows=read_csv(MODEL)
    estimates,low,high,summary=three_way_intervals(rows)
    missed=miss_categories(rows,estimates,low,high)
    map_info=plot_miss_map(shapes,missed,FIG/"experiment_03_unexpected_map.png")
    # Recreate published electoral graph using exactly the original parameters.
    edges=precinct_edges(ids,shapes)
    electoral=detect_communities(create_similarity_graph(x,edges),
                                resolution=.62,seed=2025)
    geography,result8=geography_only_comparison(x,edges,electoral)
    plot_geography_vs_vote(shapes,ids,edges,geography,electoral,result8,
                          FIG/"experiment_08_geography_vs_votes.png")
    OUT.mkdir(parents=True,exist_ok=True)
    output={"alignment":alignment,"prediction_map":map_info,
            "geography_vs_votes":result8}
    (OUT/"eight_experiments_new_views.json").write_text(
        json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print("Experiment 01 correlations:",alignment)
    print("Experiment 03 map:",map_info)
    print("Experiment 08 geography baseline:",result8)

if __name__=="__main__":
    main()
