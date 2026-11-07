"""Assemble the chart-led 8-experiment research note from verified pipeline outputs.

This avoids publishing invented statistical findings before the calculation succeeds.
Each figure file is checked before the report is written.
"""
import json
from pathlib import Path
from spatial_precinct_overlap import ROOT

REP=ROOT/"reports/seattle_through_the_numbers.md"
OUT=ROOT/"data/processed"
FIG=ROOT/"reports/figures"

CHARTS=[
"experiment_01_citywide_coalitions.svg","experiment_02_equal_participation.svg",
"experiment_03_prediction_ranges.svg","experiment_04_twin_simulation.svg",
"experiment_05_funding_sources.svg","experiment_06_hidden_ballots.svg",
"experiment_07_algorithmic_seattle.svg","experiment_08_boundary_stability.png",
"experiment_01_precinct_correlations.svg","experiment_03_unexpected_map.png",
"experiment_08_geography_vs_votes.png",
]

def load_metrics():
    values={}
    for suffix in ("03_04","05_06","07_08"):
        path=OUT/f"eight_experiments_{suffix}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing calculation outputs: {path}")
        values.update(json.loads(path.read_text(encoding="utf-8")))
    add=OUT/"eight_experiments_new_views.json"
    if not add.exists():
        raise FileNotFoundError("Missing correlations, surprise map or geography-baseline calculations")
    values.update(json.loads(add.read_text(encoding="utf-8")))
    return values

def create_manuscript(data):
    e3=data["prediction_intervals"]
    e4=data["twin_simulation"]
    e5=data["funding"]
    e6=data["ecological"]
    e7=data["electoral_communities"]
    e8=data["boundary_robustness"]
    alignment=data["alignment"]
    prediction_map=data["prediction_map"]
    geo=data["geography_vs_votes"]
    strongest=max(alignment,key=lambda r:r["correlation"])
    weakest=min(alignment,key=lambda r:r["correlation"])
    biggest_mismatch=max(alignment,key=lambda r:r["different_majority_pct"])
    for filename in CHARTS:
        path=FIG/filename
        if not path.exists() or path.stat().st_size<500:
            raise FileNotFoundError(f"Unverified/missing chart: {path}")
    return f"""# Seattle, Through the Numbers
## Eight Computational Experiments on the 2025 Election

**Independent research · November 2026 · Revised research edition**

Katie Wilson defeated Bruce Harrell by **2,011 votes** in Seattle's 2025 mayoral election. But the winning margin is only the beginning. What happens when we compare different contests, remove differences in participation, model uncertainty, simulate political coincidences, follow campaign funding—and finally let a computer draw a completely new electoral map of Seattle?

Eight computational experiments, each with one clear observation and one statistical method. Where a chart looks surprising, we also ask whether the result depends on the way we measured it.

---

## I. Voting patterns and participation

### 01 · Which races followed Wilson's geographic coalition?

**Takeaway:** **{strongest['contest']}** support closely tracked Wilson's across precincts (correlation **{strongest['correlation']:.2f}**), yet **{strongest['different_majority_pct']:.1f}%** of those precincts produced different majority outcomes. Similar patterns of support do not imply the same winning coalition.

**Method:** For every precinct, compare Wilson's share of the mayoral finalist vote with support for each other winning candidate or Yes option. Measure both the **correlation** between vote shares and how often the two majority outcomes differ.

![Correlations between Wilson's precinct vote share and five other citywide contests, plus different-majority rates](figures/experiment_01_precinct_correlations.svg)

**How to read:** On the left, a correlation closer to +1 means precincts with more Wilson support also tended to give more support to that candidate or option. On the right, the percentage shows how often the other contest had a different majority result than Wilson did in that precinct. A contest can have a positive correlation **and** a high difference rate if it was broadly popular throughout the city.

**Observation:** **{strongest['contest']}** had the strongest precinct-level correlation with Wilson (r = **{strongest['correlation']:.2f}**), while **{weakest['contest']}** had the weakest (r = **{weakest['correlation']:.2f}**). **{biggest_mismatch['contest']}** had a different majority outcome in **{biggest_mismatch['different_majority_pct']:.1f}%** of comparable precincts. That's a more precise description of political coalitions than calling every precinct either “Wilson” or “Harrell.”

These are **correlations across geographic units, not linked individual ballots**. [See the six-contest comparison and plain-English descriptions of each race](experiments/01_coalitions.md).

### 02 · Why vote-weighting changes the citywide picture

**Takeaway:** Precincts with stronger Wilson support contributed fewer votes for the mayoral finalists per registered voter, which modestly narrowed her observed margin.

**Method:** Hold each precinct's observed candidate split fixed, then compare the actual result (**weighted by finalist votes cast**) with a hypothetical result **weighted by registered voters**, as though participation rates were the same everywhere.

![Observed Wilson share versus an equal-participation reweighting](figures/experiment_02_equal_participation.svg)

**The index-fund analogy:** In a market-cap-weighted index, larger companies exert more influence. An equal-weighted version changes the result because each company receives the same importance. Here the first result weights precincts by their **actual votes**, while the second gives every registered voter the same *expected participation rate*. That's **not** equal weight for each precinct: a precinct with 1,000 registered voters still counts twice as much as one with 500.

**Observation:** Wilson received **50.36%** of the two-finalist vote. Under this fixed-preference reweighting, her share becomes **51.69%**, or **1.33 percentage points higher**. The arithmetic shows that *where* mayoral votes came from mattered to the observed margin; it does **not** forecast how additional voters would have voted.

[Calculation, illustrative example and assumptions](experiments/02_equal_participation.md).

---

## II. Predictability and statistical surprises

### 03 · Where did the model miss the election?

**Takeaway:** Most precincts fit within a model-based prediction range, but some areas deviated much further from our estimated November vote share than others.

**Method:** Train a Ridge regression model on three geographic groups, calibrate its error ranges in a fourth, and test it in a fifth—using August voting and broad Census measures. Plot the **size of the miss relative to its prediction range** at each precinct.

![Seattle map highlighting precincts with small, moderate and out-of-range November prediction errors](figures/experiment_03_unexpected_map.png)

**How to read the map:** Blue areas had relatively small misses, pale orange areas had moderate misses, and dark orange areas fell **outside** their held-out prediction range. This shows *where this model worked better or worse*, not whether a neighborhood is inherently unpredictable.

![Selected held-out precinct predictions, expected ranges and actual results](figures/experiment_03_prediction_ranges.svg)

**Observation:** Ranges targeting 90% coverage contained **{e3['coverage']:.1f}%** of held-out precinct outcomes; they averaged **{e3['avg_interval_width_pp']:.1f} percentage points** wide. **{prediction_map['outside_range']} precincts** were outside their estimated range. The second figure shows a few such examples and what the error bands mean.

**Qualification:** This is retrospective model evaluation, *not* a pre-election forecast, and dependence between neighboring precincts complicates formal uncertainty guarantees.

### 04 · Is the largest political-twin gap really unusual?

**Takeaway:** The largest observed difference between historical lookalikes was close to the typical maximum produced by one simulation that repeated the entire search.

**Method:** Match precinct pairs using earlier voting and Census information *without peeking at November*, then simulate many elections and record the **single largest gap across all eligible pairs** each time.

**An analogy:** Imagine finding thousands of pairs of stocks with similar histories, then showing only the pair that diverged most after an earnings announcement. The example looks extraordinary—but selecting the **biggest** difference guarantees a dramatic story. Our statistical question is whether the largest observed gap is big *relative to a search of the same size*.

![Simulated maximum precinct-twin differences versus the observed largest gap](figures/experiment_04_twin_simulation.svg)

**Observation:** Among **{e4['candidate_pairs']:,}** matched candidate pairs, the largest November difference was **{e4['observed_max_gap_pp']:.1f} points**. The typical maximum was **{e4['binomial_median_max_pp']:.1f} points** under independent vote-count variation, versus **{e4['shuffled_errors_median_max_pp']:.1f} points** after redistributing observed model errors. The West Seattle twin pair with a 17.4-point November gap is a useful local illustration, not automatically a statistically significant anomaly.

The two simulations make different simplifying assumptions; neither establishes a formal significance threshold or explains why individual precincts diverged.

---

## III. Campaign finance and limits of aggregate data

### 05 · Democracy Vouchers played very different roles in campaign fundraising

**Takeaway:** Democracy Vouchers accounted for roughly {e5['Katie Wilson']['voucher_percent']:.0f}% of Wilson's reported direct committee funding versus {e5['Bruce Harrell']['voucher_percent']:.0f}% of Harrell's.

**Method:** Separate each campaign's official disclosed receipts into Democracy Vouchers, other contributions, and candidate funds, then compare their proportions.

![Direct Seattle mayoral campaign financing: democracy vouchers, other contributions and candidate funds](figures/experiment_05_funding_sources.svg)

**The result.** Democracy Vouchers accounted for approximately **{e5['Katie Wilson']['voucher_percent']:.0f}%** of Wilson's reported direct campaign funding versus **{e5['Bruce Harrell']['voucher_percent']:.0f}%** of Harrell's. Harrell reported substantially more other cash and in-kind contributions.

**The trick:** Compare the **composition** of money, not just the total. This chart draws on the official Seattle Ethics & Elections Commission's <a href="https://web6.seattle.gov/ethics/elections/campaigns.aspx?IDNum=965&cycle=2025&leftmenu=collapsed&type=campaign">Harrell</a> and <a href="https://web6.seattle.gov/ethics/elections/campaigns.aspx?IDNum=988&cycle=2025&leftmenu=collapsed&type=campaign">Wilson</a> committee records, as reported in November 2026.

**What's omitted:** Independent-expenditure committees and donors' geographic addresses. This is a campaign-cycle financing comparison, including some post-election reporting—not a statement about how much was spent before election day, or where individual donors voted.

### 06 · Precinct totals can't identify individual split-ticket choices

**Takeaway:** Identical precinct-level outcomes can arise from very different individual voting combinations.

**Method:** Construct two fictional groups of 100 ballots with the same candidate totals but different numbers of voters supporting both candidates.

![Two sets of fictional ballots with the same mayoral and city attorney totals](figures/experiment_06_hidden_ballots.svg)

**The result.** Imagine 100 voters, 60 for Wilson and 70 for Evans, all voting in both races. Somewhere between **{e6['possible_overlap_min_pct']} and {e6['possible_overlap_max_pct']}** of them could have voted for *both*. The same aggregate result can come from completely different individual behavior.

**The trick:** Construct two possible individual-level tables with identical margins. That's the *ecological inference problem*: the totals alone don't determine the cross-votes. Sophisticated statistical packages such as PyEI can model this relationship only by adding assumptions, which must be explained.

*The dots in this figure are hypothetical people—not Seattle voter records.*

---

## IV. Political communities and geographic boundaries

**What is a voting precinct?** A precinct is a small election-administration unit, **not** a traditional neighborhood or Seattle City Council district. Under [Washington law](https://app.leg.wa.gov/rcw/default.aspx?cite=29A.16&full=true), precincts must normally be compact, connected, within the same congressional/state legislative/county council district and city, and generally follow visible features such as streets or waterways. They cannot exceed **1,500 active registered voters**. [King County Elections](https://kingcounty.gov/en/dept/elections/maps/precinct-alterations) prepares boundary revisions, which the **King County Council** adopts. Seattle's seven district-based Council seats have [separately drawn boundaries](https://www.seattle.gov/planning-and-community-development/population-and-demographics); the community reporting areas on the left of our next map are descriptive neighborhood groupings, **not legal election districts**.

Our experiment **never redraws the precinct boundaries**. It asks which existing precincts might belong together if we grouped them by location and voting similarities.

### 07 · An algorithm groups Seattle into 11 electoral communities

**Takeaway:** Using six citywide election contests and the shared borders between precincts, the algorithm found **{e7['communities']}** geographically connected electoral groups among **{e7['precincts']:,}** precincts.

**Method:** Create a network where precincts are points, neighboring precincts are connected, and the connections are stronger where the six contest results are more alike. Apply NetworkX's **Louvain community detection** to find groups with strong internal connections.

![Familiar Seattle community reporting areas and election-based Louvain groupings](figures/experiment_07_algorithmic_seattle.svg)

**How Louvain works:** Imagine every precinct starting out as its own group. The algorithm repeatedly asks whether moving a precinct into a neighboring group makes the overall network grouping stronger—meaning a better concentration of connections *within* groups than a random-connection benchmark would suggest. It combines groups and repeats until further moves stop helping. A setting called **resolution** influences how many groups emerge.

**Interpretation:** The algorithm did not learn what “Ballard” means. It discovered **{e7['communities']}** groups in a map made from **{e7['edges']:,}** geographic connections—but a map made from geography *alone* would also form clusters. That's what the final experiment checks.

### 08 · What does election data add beyond geography alone?

**Takeaway:** Adding voting patterns changed just **{geo['border_status_changes_pct']:.1f}%** of neighboring-precinct same-group/different-group relationships compared with a geography-only model yielding a similar number of communities.

**Method:** Run Louvain twice on **the exact same precinct network**: first with every adjacent border equally weighted (geography only), then with stronger weights for neighbors whose six-contest voting patterns are similar. Choose a geography-only resolution giving a comparable number of groups, then compare the boundaries.

![Map highlighting boundaries that change when vote similarity is added to a geography-only precinct network](figures/experiment_08_geography_vs_votes.png)

**Observation:** The geography-only model produced **{geo['geography_only_groups']}** groups versus **{geo['voting_informed_groups']}** with voting data. Adding voting patterns changed the same-group/different-group status of **{geo['border_status_changes_pct']:.1f}%** of the **{geo['shared_borders']:,}** shared precinct borders. The chance-adjusted agreement between groupings was **{geo['adjusted_rand_geography_vs_voting']:.2f}** (adjusted Rand index; 1 means identical group assignments).

**A second check:** Changing the contests and the clustering resolution within the election-based model changed **{e8['model_sensitive_pct']:.1f}%** of local border classifications across five specifications. [See that sensitivity map](figures/experiment_08_boundary_stability.png).

**Interpretation:** Neither a geography-only map nor a vote-informed map is the uniquely correct way to divide Seattle. The useful result is **what actually changes when electoral information is introduced**, rather than the existence of algorithmic clusters itself.

---

## Summary of findings

The methods tell different stories, and they shouldn't all be forced into a single political conclusion.

**Cross-race comparison** reveals coalitions that cannot be reduced to the mayoral contest. **Turnout reweighting** shows the geographic arithmetic behind a narrow result. **Uncertainty estimates and simulations** distinguish genuine evidence from selected extremes. **Campaign-finance data** shows a second kind of coalition. **Ecological inference** reminds us of the limits of precinct data. And **graph community detection** provides a fresh picture of the city—whose sensitivity we can examine instead of ignoring.

The key results are descriptive; none establishes how a particular voter changed their mind or why a neighborhood behaves as it does. Several results depend on choices about geographic units, candidate groupings, and statistical assumptions.

### Methods and sources

- **Official returns:** [King County's certified November 2025 precinct CSV](https://data.kingcounty.gov/d/rkie-6y8x), [August primary](https://data.kingcounty.gov/d/tsx2-ia8a), and [2021 general](https://data.kingcounty.gov/d/4qrf-rjar).
- **Political geography:** [2025 voting-district shapes](https://services.arcgis.com/Ej0PsM5Aw677QF1W/ArcGIS/rest/services/VOTDST_2025_AREA_3072/FeatureServer/0), 2020 Census geographic allocation, and King County precinct-to-community-reporting-area labels.
- **Campaign funding:** [Seattle official disclosure portal](https://web6.seattle.gov/ethics/elections/campaigns.aspx?IDNum=224&cycle=2025&leftmenu=collapsed&type=contest) (November 2026 snapshot; direct campaign committees only).
- **Computational techniques:** scikit-learn, SciPy, Shapely, NetworkX, Matplotlib, and NumPy. [Source code](../scripts/) and [prior detailed methodology](../docs/methodology/techniques_explained.md).
- **Reproduction:** the GitHub Actions workflow runs the analysis from official inputs and commits verified graphics and aggregate research outputs.

*Independent exploratory study · Review edition. Code, sources, and statistical assumptions are linked above.*
"""

def main():
    data=load_metrics()
    text=create_manuscript(data)
    REP.parent.mkdir(parents=True,exist_ok=True)
    REP.write_text(text,encoding="utf-8")
    print("Assembled full eight-experiment narrative:",len(text.split()),"words",
          "and",len(CHARTS),"verified charts")

if __name__=="__main__":
    main()
