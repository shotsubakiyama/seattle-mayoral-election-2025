"""Experiments 7–8: new electoral regions and their boundary stability.

Uses *all six* citywide 2025 ballots and official 2025 precinct polygons.
Communities are created from a weighted graph whose edges require geographic
adjacency. The model is exploratory and is NOT a geographically invariant truth.

Requires networkx>=3.2, shapely>=2, matplotlib, numpy.
"""
import csv
import json
import math
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon as PlotPolygon
import networkx as nx
from shapely import STRtree

from spatial_precinct_overlap import ROOT,fetch_shapes
from eight_experiments_opening import RAW,CONTESTS,parse_official_csv,validate_contests

FIG=ROOT/"reports/figures"
OUT=ROOT/"data/processed"
CRA=OUT/"precinct_to_cra_crosswalk.csv"


def election_feature_matrix(votes,shapes,min_mayor=100):
    mayor=CONTESTS[0]
    ids=[]
    values=[]
    for pid in sorted(shapes,key=int):
        m=votes[mayor[0]].get(pid,{})
        if m.get(mayor[1],0)+m.get(mayor[2],0)<min_mayor:
            continue
        series=[]
        for race,positive,other,*_ in CONTESTS:
            row=votes[race].get(pid,{})
            a,b=row.get(positive,0),row.get(other,0)
            if a+b<50:
                series=[]
                break
            series.append(a/(a+b))
        if series:
            ids.append(pid)
            values.append(series)
    x=np.asarray(values,dtype=float)
    if len(ids)<950 or x.shape[1]!=6 or np.isnan(x).any():
        raise ValueError("Unexpectedly low/invalid six-contest precinct coverage")
    return ids,x


def precinct_edges(ids,shapes,min_shared_feet=100):
    polys=[shapes[i] for i in ids]
    tree=STRtree(polys)
    edges=[]
    for i,a in enumerate(polys):
        for number in tree.query(a):
            j=int(number)
            if j<=i: continue
            border=a.boundary.intersection(polys[j].boundary).length
            if border>=min_shared_feet:
                edges.append((i,j,float(border)))
    if len(ids)>500 and len(edges)<1800:
        raise ValueError(f"Only {len(edges)} spatial adjacency edges found")
    return edges


def create_similarity_graph(x,edges,features=None,scale=.105):
    if features is None:
        features=range(x.shape[1])
    feature_ids=list(features)
    if not feature_ids:
        raise ValueError("At least one election column needed")
    g=nx.Graph()
    g.add_nodes_from(range(len(x)))
    for i,j,border in edges:
        rms=float(np.sqrt(np.mean((x[i,feature_ids]-x[j,feature_ids])**2)))
        # Neighbor relationships remain present, but vote-similar pairs have stronger ties.
        weight=0.15+math.exp(-rms/scale)
        g.add_edge(i,j,weight=weight,border_feet=border)
    return g


def detect_communities(graph,resolution=.62,seed=2025):
    parts=nx.community.louvain_communities(graph,resolution=resolution,
                                           weight="weight",seed=seed)
    if not parts:
        raise ValueError("No communities found")
    by_node={}
    for i,part in enumerate(sorted(parts,key=lambda s:min(s))):
        for idx in part:
            if idx in by_node:
                raise AssertionError("Overlapping community memberships")
            by_node[idx]=i
    if set(by_node)!=set(graph.nodes):
        raise AssertionError("Unassigned precinct nodes")
    return by_node


def partition_scenarios(x,edges):
    configs=[
        ("All six contests",list(range(6)),.62),
        ("Only mayor",[0],.62),
        ("Other five contests",list(range(1,6)),.62),
        ("Coarser communities",list(range(6)),.40),
        ("Finer communities",list(range(6)),.87),
    ]
    answers={}
    for name,features,res in configs:
        g=create_similarity_graph(x,edges,features=features)
        answers[name]=detect_communities(g,resolution=res)
    return answers


def share_border_sensitivity(edges,scenarios):
    if len(scenarios)<2:
        raise ValueError("Need multiple defensible specs to test stability")
    groups=list(scenarios.values())
    classes=[]
    for a,b,_ in edges:
        same=sum(1 for group in groups if group[a]==group[b])
        if same==len(groups):
            category="Stable internal border"
        elif same==0:
            category="Stable dividing border"
        else:
            category="Model-sensitive border"
        classes.append(category)
    return classes


def polygon_parts(shape):
    if shape.geom_type=="Polygon":
        yield shape
    elif hasattr(shape,"geoms"):
        for piece in shape.geoms:
            yield from polygon_parts(piece)


def render_community_map(ids,shapes,scenario,community_summary,destination):
    fig,axs=plt.subplots(1,2,figsize=(15.3,8))
    cra={}
    with CRA.open(encoding="utf-8-sig",newline="") as f:
        cra={r["precinct_id"]:r["cra_name"] for r in csv.DictReader(f)}
    classes1={name:i for i,name in enumerate(sorted(set(cra.get(pid,"Unassigned") for pid in ids)))}
    colors1=plt.get_cmap("tab20").colors
    colors2=plt.get_cmap("tab20").colors
    for ax,kind in zip(axs,("cra","algorithm")):
        patches=[];colors=[]
        for i,pid in enumerate(ids):
            key=classes1[cra.get(pid,"Unassigned")] if kind=="cra" else scenario[i]
            color=(colors1 if kind=="cra" else colors2)[key % len(colors1)]
            for polygon in polygon_parts(shapes[pid].simplify(45,preserve_topology=True)):
                patches.append(PlotPolygon(np.asarray(polygon.exterior.coords)))
                colors.append(color)
        collection=PatchCollection(patches,facecolor=colors,edgecolor="white",linewidth=.07)
        ax.add_collection(collection)
        ax.autoscale_view()
        ax.set_aspect("equal")
        ax.axis("off")
    axs[0].set_title(f"Familiar community-reporting areas ({len(classes1)})",
                      weight="bold",fontsize=14,pad=18)
    axs[1].set_title(f"Algorithmic electoral communities ({community_summary['communities']})",
                     weight="bold",fontsize=14,pad=18)
    fig.suptitle("An algorithm redraws Seattle—without being told neighborhood names",
                 weight="bold",fontsize=20,x=.06,y=.99,ha="left")
    fig.text(.06,.035,"Colors are group labels, not parties or political ideology. Left: Seattle CRA lookup. Right: Louvain groups\n"
             "using geographic neighbors and similarity across six 2025 citywide election contests.",
             fontsize=10,color="#536c7d")
    fig.subplots_adjust(left=.02,right=.98,top=.89,bottom=.09,wspace=.01)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,format="svg",bbox_inches="tight")
    plt.close(fig)


def segment_lines(shared):
    if shared.geom_type=="LineString":
        if shared.length>0:yield np.asarray(shared.coords)
    elif hasattr(shared,"geoms"):
        for item in shared.geoms:
            yield from segment_lines(item)


def render_stability(ids,shapes,edges,category,summary,destination):
    fig,ax=plt.subplots(figsize=(10.2,10.6))
    patches=[]
    for pid in ids:
        for p in polygon_parts(shapes[pid].simplify(45,preserve_topology=True)):
            patches.append(PlotPolygon(np.asarray(p.exterior.coords)))
    base=PatchCollection(patches,facecolor="#f5f7f9",edgecolor="#d9e1e6",
                         linewidth=.14,zorder=1)
    ax.add_collection(base)
    colors={"Stable internal border":"#d1dae1","Stable dividing border":"#2c5269",
            "Model-sensitive border":"#cd7544"}
    weights={"Stable internal border":.16,"Stable dividing border":.8,
             "Model-sensitive border":1.0}
    line_segments={key:[] for key in colors}
    for (i,j,_),label in zip(edges,category):
        shared=shapes[ids[i]].boundary.intersection(shapes[ids[j]].boundary)
        # A citywide display needs fewer vertices than the analytical border test.
        shared=shared.simplify(45,preserve_topology=True)
        line_segments[label].extend(segment_lines(shared))
    for key,parts in line_segments.items():
        if parts:
            ax.add_collection(LineCollection(parts,colors=colors[key],linewidths=weights[key],
                                             zorder=2))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Which invented political boundaries survive a second look?",
                 fontsize=17,weight="bold",loc="left",pad=18)
    fig.text(.12,.10,"Dark: separated in all 5 specifications. Orange: classification changes. Light: grouped in all 5.",
             fontsize=10,color="#4f6679")
    fig.text(.12,.077,
             f"Of {len(edges):,} adjacent borders, {summary['model_sensitive_pct']:.1f}% "
             "change between tested specifications.",
             fontsize=11,color="#4f6679",weight="bold")
    fig.subplots_adjust(left=.02,right=.98,top=.92,bottom=.12)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,format="svg",bbox_inches="tight")
    plt.close(fig)


def main():
    if not RAW.exists():
        raise FileNotFoundError("First generate official King County results with eight_experiments_opening.py")
    votes,_=parse_official_csv(RAW)
    validate_contests(votes)
    shapes=fetch_shapes(2025)
    ids,x=election_feature_matrix(votes,shapes)
    edges=precinct_edges(ids,shapes)
    scenarios=partition_scenarios(x,edges)
    baseline=scenarios["All six contests"]
    counts=Counter(baseline.values())
    result7={"precincts":len(ids),"edges":len(edges),
             "communities":len(counts),"largest_community_precincts":max(counts.values()),
             "smallest_community_precincts":min(counts.values()),
             "median_community_precincts":round(float(np.median(list(counts.values()))),1)}
    FIG.mkdir(parents=True,exist_ok=True)
    render_community_map(ids,shapes,baseline,result7,
                         FIG/"experiment_07_algorithmic_seattle.svg")
    labels=share_border_sensitivity(edges,scenarios)
    stats=Counter(labels)
    result8={"neighbor_pairs":len(edges),
             "stable_internal_pct":round(100*stats["Stable internal border"]/len(edges),1),
             "stable_dividing_pct":round(100*stats["Stable dividing border"]/len(edges),1),
             "model_sensitive_pct":round(100*stats["Model-sensitive border"]/len(edges),1),
             "models":{label:len(set(clusters.values())) for label,clusters in scenarios.items()}}
    render_stability(ids,shapes,edges,labels,result8,
                     FIG/"experiment_08_boundary_stability.svg")
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"experiment_07_precinct_electoral_communities.csv").open("w",
            newline="",encoding="utf-8") as f:
        writer=csv.writer(f);writer.writerow(["precinct_id","electoral_group"])
        writer.writerows((pid,baseline[i]) for i,pid in enumerate(ids))
    (OUT/"eight_experiments_07_08.json").write_text(
        json.dumps({"electoral_communities":result7,
                    "boundary_robustness":result8},indent=2)+"\n",encoding="utf-8")
    print("Experiment 07",result7)
    print("Experiment 08",result8)


if __name__=="__main__":
    main()
