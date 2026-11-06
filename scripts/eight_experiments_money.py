"""Verified Seattle campaign-funding sources and an ecological-inference teaching graphic.

Experiment 5: official Seattle Ethics and Elections Commission 2025 candidate
disclosures (Nov 3 2026 snapshot), excluding independent committees.
Experiment 6: explicitly hypothetical 100-person ballots to demonstrate ambiguity.
No individual contributor records are collected.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/"reports/figures"
OUT=ROOT/"data/processed"
SOURCES={
    "Harrell":"https://web6.seattle.gov/ethics/elections/campaigns.aspx?IDNum=965&cycle=2025&leftmenu=collapsed&type=campaign",
    "Wilson":"https://web6.seattle.gov/ethics/elections/campaigns.aspx?IDNum=988&cycle=2025&leftmenu=collapsed&type=campaign",
}
FINANCE={
    "Katie Wilson":{"vouchers":795925.00,"other_contributions":228976.61,"candidate_funds":0.00},
    "Bruce Harrell":{"vouchers":486975.00,"other_contributions":658624.08,"candidate_funds":43743.13},
}
COLORS=("#2f80a0","#d58b4d","#677b8c")
LABELS=("Democracy Vouchers","Other cash / in-kind","Candidate funds")

def figure_funding(destination=FIG/"experiment_05_funding_sources.svg"):
    vals=np.array([[c["vouchers"],c["other_contributions"],c["candidate_funds"]]
                   for c in FINANCE.values()])
    totals=vals.sum(axis=1)
    if vals.shape!=(2,3) or np.any(vals<0) or not (1.0e6<totals[0]<1.1e6 and 1.1e6<totals[1]<1.3e6):
        raise ValueError("Unexpected official finance snapshot; verify candidate pages")
    fig,ax=plt.subplots(figsize=(11.4,5.3))
    left=np.zeros(2)
    for j in range(3):
        ax.barh(np.arange(2),vals[:,j]/1e6,left=left/1e6,height=.48,
                color=COLORS[j],label=LABELS[j])
        for i in range(2):
            if vals[i,j]>160000:
                ax.text((left[i]+vals[i,j]/2)/1e6,i,f"{vals[i,j]/1e3:.0f}k",
                        va="center",ha="center",color="white",weight="bold",fontsize=12)
        left+=vals[:,j]
    ax.set_yticks(np.arange(2),list(FINANCE),fontsize=12)
    ax.invert_yaxis()
    ax.set_xlim(0,1.53)
    ax.set_xlabel("Campaign funding reported (millions of dollars)",fontsize=11)
    ax.set_title("The same office. Two very different fundraising models.",
                 loc="left",fontsize=17,weight="bold",pad=20)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.grid(axis="x",alpha=.15)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y",length=0,pad=12)
    for i,(v,t) in enumerate(zip(vals,totals)):
        ax.text(t/1e6+.025,i,f"{t/1e6:.2f}m  |  {100*v[0]/t:.0f}% vouchers",
                va="center",fontsize=11,color="#274054",weight="bold")
    fig.legend(loc="upper left",bbox_to_anchor=(.24,.88),ncol=3,frameon=False,
               fontsize=10,handlelength=1.7)
    fig.text(.02,.018,
        "Seattle Ethics & Elections Commission, 2025 cycle disclosures (November 2026 snapshot).\n"
        "Candidate committees only; post-election contributions included. Independent expenditures excluded.",
        fontsize=9,color="#597082")
    fig.subplots_adjust(left=.24,right=.97,top=.71,bottom=.27)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,format="svg",bbox_inches="tight")
    plt.close(fig)
    return {name:{"total":round(float(v.sum()),2),
                  "voucher_percent":round(float(100*v[0]/v.sum()),1)}
            for name,v in zip(FINANCE,vals)}

def ballot_cross_tab(total=100,mayor=60,attorney=70,overlap=30):
    if not 0<=min(mayor,attorney)<=total or not 0<=overlap<=min(mayor,attorney):
        raise ValueError("Invalid margins or intersection")
    cells=(overlap,mayor-overlap,attorney-overlap,total-mayor-attorney+overlap)
    if min(cells)<0 or sum(cells)!=total:
        raise ValueError("Overlap incompatible with fixed marginal totals")
    return cells

def figure_ecological(destination=FIG/"experiment_06_hidden_ballots.svg"):
    left=ballot_cross_tab(overlap=30)
    right=ballot_cross_tab(overlap=60)
    palette=["#2d7797","#d28a53","#a68abd","#e5ebf0"]
    categories=["Wilson + Evans","Wilson, not Evans","Evans, not Wilson","Neither"]
    fig,axs=plt.subplots(1,2,figsize=(11.2,5.3))
    for ax,cells,label in zip(axs,(left,right),("Scenario A: 30% chose both",
                                               "Scenario B: 60% chose both")):
        grid=np.concatenate([np.repeat(i,n) for i,n in enumerate(cells)])
        for k,v in enumerate(grid):
            row,col=divmod(k,10)
            ax.add_patch(Rectangle((col,row),.91,.91,color=palette[int(v)],linewidth=0))
        ax.set(xlim=(0,10),ylim=(10,0),aspect="equal")
        ax.set_title(label,loc="left",fontsize=13,weight="bold")
        ax.axis("off")
        ax.text(.5,-.55,"Both: 60% Wilson / 70% Evans",
                fontsize=10,color="#526878")
    fig.suptitle("Identical precinct totals. Different stories about individual voters.",
                 fontsize=16,weight="bold",x=.07,y=.98,ha="left")
    fig.legend(handles=[Patch(facecolor=color,label=label) for label,color in zip(categories,palette)],
               loc="lower center",bbox_to_anchor=(.5,.14),ncol=4,frameon=False,fontsize=10)
    fig.text(.07,.05,"ILLUSTRATIVE: 100 fictional voters, all voting in both races. "
             "This is not a reconstruction of Seattle ballots.",fontsize=9,color="#526878")
    fig.subplots_adjust(left=.07,right=.95,top=.82,bottom=.21,wspace=.17)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,format="svg",bbox_inches="tight")
    plt.close(fig)
    return {"mayor_wilson_pct":60,"attorney_evans_pct":70,
            "possible_overlap_min_pct":30,"possible_overlap_max_pct":60}

def main():
    m5=figure_funding()
    m6=figure_ecological()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"eight_experiments_05_06.json").write_text(
        json.dumps({"funding":m5,"ecological":m6,"sources":SOURCES},indent=2)+"\n",
        encoding="utf-8")
    print("Experiment 05",m5)
    print("Experiment 06",m6)

if __name__=="__main__":
    main()
