"""Experiments 3 and 4: geographic prediction ranges and selection-aware twin simulations.

Run after model_precinct_surprises.py and precinct_twins_history.py.
All prediction intervals are empirically evaluated in held-out geographic groups,
NOT claimed to have formal spatially dependent coverage guarantees.
"""
import csv
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import Ridge
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from model_precinct_surprises import NUMERIC_FEATURES
from precinct_twins_history import HISTORY_CALIPERS
from spatial_precinct_overlap import ROOT, fetch_shapes

MODEL=ROOT/"data/processed/precinct_surprises_2025.csv"
PANEL=ROOT/"data/processed/seattle_mayor_precinct_panel_2021_2025.csv"
AREA=ROOT/"data/processed/precinct_to_cra_crosswalk.csv"
OUT=ROOT/"data/processed"
FIG=ROOT/"reports/figures"

def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Run prerequisite analysis before {path}")
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def three_way_intervals(rows):
    """5 test folds, each calibrated on 1 *different* fold, trained on remaining 3."""
    x=np.array([[float(r[k]) for k in NUMERIC_FEATURES] for r in rows])
    y=np.array([float(r["actual_harrell_share"]) for r in rows])
    weights=np.array([int(r["general_votes"]) for r in rows])
    groups=np.array([r["spatial_group"] for r in rows])
    folds=list(GroupKFold(n_splits=5).split(x,y,groups))
    expected=np.full(len(rows),np.nan)
    lower=np.full(len(rows),np.nan)
    upper=np.full(len(rows),np.nan)
    calib_n=[]
    for k,(_,test) in enumerate(folds):
        cal=folds[(k+1)%5][1]
        train=np.setdiff1d(np.arange(len(rows)),np.concatenate([test,cal]),assume_unique=True)
        if len(train)<len(rows)*.3 or (set(groups[test]) & set(groups[cal])):
            raise AssertionError("Leaking geographic groups into training/calibration")
        scaler=StandardScaler().fit(x[train])
        model=Ridge(alpha=12.0)
        model.fit(scaler.transform(x[train]),y[train],
                  sample_weight=weights[train]/weights[train].mean())
        cal_p=np.clip(model.predict(scaler.transform(x[cal])),0,1)
        errors=np.abs(y[cal]-cal_p)
        # Standard finite-sample split-conformal quantile; geographic dependence remains.
        q_idx=min(len(cal)-1,math.ceil((len(cal)+1)*.9)-1)
        radius=np.sort(errors)[q_idx]
        pred=np.clip(model.predict(scaler.transform(x[test])),0,1)
        expected[test]=pred
        lower[test]=np.clip(pred-radius,0,1)
        upper[test]=np.clip(pred+radius,0,1)
        calib_n.append(len(cal))
    if np.isnan(expected).any() or np.isnan(lower).any():
        raise AssertionError("Missing held-out predictions")
    coverage=float(np.mean((y>=lower)&(y<=upper)))
    avg_width=float(100*np.mean(upper-lower))
    weighted_mae=float(100*np.average(abs(expected-y),weights=weights))
    return expected,lower,upper,dict(coverage=round(coverage*100,2),
        avg_interval_width_pp=round(avg_width,2),
        weighted_mae_pp=round(weighted_mae,2),precincts=len(rows),
        calibration_fold_sizes=calib_n)

def plot_intervals(rows,pred,low,high,summary,destination):
    choices=[]
    for i,r in enumerate(rows):
        if int(r["general_votes"])<150: continue
        miss=float(r["actual_harrell_share"])-pred[i]
        choices.append((max(0,abs(miss)-(high[i]-pred[i] if miss>=0 else pred[i]-low[i])),
                        abs(miss),i))
    idx=[t[2] for t in sorted(choices,reverse=True)[:10]]
    fig,ax=plt.subplots(figsize=(11,7.1))
    area={r["precinct_id"]:r["cra_name"] for r in read_csv(AREA)}
    for iy,i in enumerate(idx):
        r=rows[i]
        y=float(r["actual_harrell_share"])*100
        ax.plot([low[i]*100,high[i]*100],[iy,iy],color="#86a9be",lw=5,
                solid_capstyle="round",alpha=.75)
        ax.scatter(pred[i]*100,iy,marker="|",s=220,color="#1c5676",zorder=5)
        out=not low[i] <= float(r["actual_harrell_share"]) <= high[i]
        ax.scatter(y,iy,s=55,color="#c27643" if out else "#26849b",zorder=6)
    ax.set_yticks(range(len(idx)),[
        f"{area.get(rows[i]['precinct_id'],'Seattle')} · {rows[i]['precinct_id']}" for i in idx],
        fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Harrell share of 2025 finalist vote (%)")
    ax.set_title("Which precincts fell outside the model's expected range?",
                 loc="left",weight="bold",fontsize=16,pad=20)
    ax.grid(axis="x",alpha=.18)
    ax.set_axisbelow(True)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=10)
    fig.text(.05,.065,
        "Pale line = 90%-target prediction range; dark tick = estimate; dot = actual result.\n"
        "Orange dots fall beyond their range. Chosen extremes are descriptive, not individually tested discoveries.",
        fontsize=9,color="#566e7c")
    fig.subplots_adjust(left=.33,right=.96,top=.84,bottom=.18)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,format="svg",bbox_inches="tight")
    plt.close(fig)

def pre_november_matches(rows, historical, polygons):
    """Rebuild matching pool without filtering on NOVEMBER GAP (unlike original shortlist)."""
    prev={r["precinct_id"]:r for r in historical
          if r["stable_boundary"]=="True" and int(r["two_candidate_votes_2021"])>=100}
    eligible=[]
    for r in rows:
        pid=r["precinct_id"]
        if pid in prev and pid in polygons and int(r["general_votes"])>=150:
            eligible.append({**r,"historical_harrell_share":prev[pid]["harrell_share_2021"]})
    eligible.sort(key=lambda r:int(r["precinct_id"]))
    if len(eligible)<600:
        raise ValueError("Historical data coverage unexpectedly low")
    keys=list(HISTORY_CALIPERS)
    scales=np.array([HISTORY_CALIPERS[x] for x in keys])
    x=np.array([[float(r[k]) for k in keys] for r in eligible])
    nearest=NearestNeighbors(n_neighbors=min(200,len(eligible))).fit(x/scales)
    dists,ind=nearest.kneighbors(x/scales)
    points=[polygons[r["precinct_id"]].representative_point() for r in eligible]
    edges=set()
    for i,(nn,ds) in enumerate(zip(ind,dists)):
        for j,d in zip(nn,ds):
            j=int(j)
            if i==j or d>1.5: continue
            a,b=min(i,j),max(i,j)
            if (a,b) in edges: continue
            if np.any(np.abs(x[i]-x[j])>scales+1e-12):continue
            if points[i].distance(points[j])<5280:continue
            edges.add((a,b))
    if len(edges)<250:
        raise ValueError("Unexpectedly few historical twin candidate pairs")
    return eligible,np.array(sorted(edges),dtype=int)

def simulate_maxima(pair_rows,links,draws=1200,seed=20251104):
    """Two explicit scenario models: independent binomial; shuffled observed model errors.

    Maxima are computed across *all* candidate pairs on each draw. Both baselines
    make restrictive assumptions (in particular independence / exchangeability).
    Neither simulation yields a universal 'statistically significant twin' claim.
    """
    n=np.array([int(r["general_votes"]) for r in pair_rows],dtype=int)
    p=np.array([float(r["expected_primary_plus_census_pct"])/100 for r in pair_rows])
    obs=np.array([float(r["actual_harrell_share"]) for r in pair_rows])
    residual=obs-p
    if not np.isfinite(p).all() or len(links)<1:
        raise ValueError("Invalid twin simulation")
    a,b=links.T
    actual_max=float(100*np.max(abs(obs[a]-obs[b])))
    rng=np.random.default_rng(seed)
    binomial=np.empty(draws)
    errors=np.empty(draws)
    for k in range(draws):
        simulated=rng.binomial(n,np.clip(p,0,1))/n
        binomial[k]=100*np.max(abs(simulated[a]-simulated[b]))
        # Baseline + randomly reassigned empirical residuals; no geographic dependence.
        shuffled=np.clip(p+rng.permutation(residual),0,1)
        errors[k]=100*np.max(abs(shuffled[a]-shuffled[b]))
    return {"observed_max_gap_pp":round(actual_max,2),
            "candidate_pairs":len(links),"eligible_precincts":len(pair_rows),
            "binomial_median_max_pp":round(float(np.median(binomial)),2),
            "binomial_95pct_max_pp":round(float(np.quantile(binomial,.95)),2),
            "shuffled_errors_median_max_pp":round(float(np.median(errors)),2),
            "shuffled_errors_95pct_max_pp":round(float(np.quantile(errors,.95)),2),
            "binomial_exceedance_percent":round(float(100*np.mean(binomial>=actual_max)),1),
            "shuffled_exceedance_percent":round(float(100*np.mean(errors>=actual_max)),1),
            "draws":draws},binomial,errors

def plot_twin_simulations(result,binom,shuffled,destination):
    fig,ax=plt.subplots(figsize=(10.5,5.0))
    ax.hist(binom,bins=36,alpha=.67,density=True,label="Random vote counts only",
            color="#7ca9c0")
    ax.hist(shuffled,bins=36,alpha=.50,density=True,
            label="Redistributed observed model errors",color="#d29a68")
    ax.axvline(result["observed_max_gap_pp"],color="#af493c",lw=3,
               label=f"Real largest gap: {result['observed_max_gap_pp']:.1f} points")
    ax.set_xlabel("Largest November difference across all preselected matched pairs (percentage points)")
    ax.set_ylabel("Simulated frequency")
    ax.set_title("If we search many precinct twins, how big a gap should we expect?",
                 loc="left",weight="bold",fontsize=15,pad=20)
    ax.legend(loc="upper left",frameon=False,fontsize=10)
    ax.spines[["top","right"]].set_visible(False)
    fig.text(.045,.012,
             f"{result['candidate_pairs']:,} pre-November matched pairs; {result['draws']:,} scenarios per null model.\n"
             "Exploratory sensitivity experiment; scenarios ignore correlated local errors and aren't formal p-values.",
             fontsize=9,color="#5c7180")
    fig.subplots_adjust(left=.10,right=.95,top=.83,bottom=.25)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,format="svg",bbox_inches="tight")
    plt.close(fig)

def main():
    rows=read_csv(MODEL)
    e,lo,hi,m3=three_way_intervals(rows)
    plot_intervals(rows,e,lo,hi,m3,FIG/"experiment_03_prediction_ranges.svg")
    paired,links=pre_november_matches(rows,read_csv(PANEL),fetch_shapes(2025))
    m4,binom,shuffle=simulate_maxima(paired,links)
    plot_twin_simulations(m4,binom,shuffle,FIG/"experiment_04_twin_simulation.svg")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"eight_experiments_03_04.json").write_text(json.dumps(
        {"prediction_intervals":m3,"twin_simulation":m4},indent=2)+"\n",encoding="utf-8")
    print("Experiment 03",m3)
    print("Experiment 04",m4)

if __name__=="__main__":
    main()
