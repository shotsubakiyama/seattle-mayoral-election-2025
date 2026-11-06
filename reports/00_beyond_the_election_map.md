# Seattle 2025: A familiar map, unfamiliar neighbors
*What statistical learning and spatial analysis reveal beyond the precinct winner map*

**SEATTLE ELECTION RESEARCH · NOVEMBER 2026 · RESEARCH DRAFT**

**The setup.** Katie Wilson defeated Bruce Harrell by **2,011 votes** (138,931 to 136,920). We know where each candidate won. The more useful questions are whether November was predictable, which apparently similar places diverged, and whether those surprises cluster.

| **1,006** precincts modeled | **3.01 pp** average prediction error | **17.4 pp** West Seattle twin gap | **0** locally significant clusters after correction |
|:---:|:---:|:---:|:---:|

## 1 / November was largely written in August

![Model accuracy comparison: three prediction methods](figures/model_comparison_scorecard.svg)

**The finding:** An August-only model predicts the November two-candidate vote with **3.39 percentage points** of average error. Add three basic Census variables and error falls to **3.01 points**, an **11% improvement**. Using the raw August finalist vote share without any adjustment produces **5.32 points** of error.

![Actual versus predicted Harrell two-candidate share, 2025](figures/precinct_surprises_scatter.svg)

**The method — prediction with an honest exam.** We fit a **Ridge regression** (a statistical model that discourages overly extreme coefficients) to August voting and 2020 Census context. In **geographically grouped cross-validation**, entire groups of precincts are held out when testing predictions. The model never gets to learn from the November result of a precinct it is asked to predict.

**What this means:** Seattle's general-election geography was highly predictable from prior voting. Census context added some signal, but it did not overturn the August baseline. Predictive accuracy is not an explanation of *why* anyone voted.

## 2 / The twins that parted ways

![Historical precinct twins across the 2021 general, August 2025 primary, and November 2025 general elections](figures/twin_case_studies.svg)

**The finding:** Highland Park and Junction–Genesee Hill in West Seattle looked nearly identical in Harrell's **2021 vote share** (61.1% vs. 61.9%) and were only **4.8 points apart** among Harrell/Wilson primary votes in August. By November, Harrell received **46.6% vs. 63.9%**—a **17.4-point split**.

Other historical twins separated sharply too: West Seattle Junction–Genesee Hill vs. Queen Anne (**20.2 points**) and South Beacon Hill–New Holly vs. Ravenna–Bryant (**19.2 points**).

**The method — nearest-neighbor matching.** Think of comparing two companies with similar starting financials before comparing their outcomes. We first find precincts similar on **2021 voting, August voting, and basic Census characteristics**; only *after* forming the pairs do we rank their November differences. Across **846** precincts with validated historical boundaries, **1,775 candidate pairs** passed these pre-November matching rules.

**The question, not the answer:** West Seattle's November turnout rates also differed—**62.4% vs. 76.6%**—but aggregate results cannot tell whether the gap came from turnout composition, changing candidate preferences, or unmeasured neighborhood differences. These are **selected extremes**, not evidence of causation.

## 3 / A political divide across a shared border

![Close-up of the 2025 precinct vote share contrast in Queen Anne](figures/fault_line_1709_1724_v2.svg)

**The finding:** Two adjoining Queen Anne precincts, **1709 and 1724**, gave Harrell **23.8% and 81.4%** of the finalist vote. They share roughly **1,283 feet of border**. This is visually powerful, although a Seattle resident may recognize familiar differences between parts of the hill.

**The method — spatial networks.** Each precinct is a *node*; two nodes are connected if their shapes share at least **100 feet** of boundary. We compared **2,582 qualifying adjacent pairs**, then ranked their vote-share gaps. This goes beyond simply coloring an election map: it measures exactly *where* neighboring outcomes diverge.

**Reality check — do surprises cluster?** A separate **Moran-style spatial autocorrelation test** found weak citywide similarity in the prediction errors (**I = 0.100, permutation p = 0.0001**). But **none of the 1,006 local precinct tests survived multiple-testing correction**. We therefore do not label any neighborhood a statistically established surprise cluster.

---

### Bottom line

**Three methods, three different jobs:** prediction establishes what was expected; matching finds unusually different outcomes among comparable places; spatial networks show precisely where adjoining precincts split.

The strongest lead is **the historical twins, especially within West Seattle**. The next worthwhile test is whether the contrast persists after adding **housing tenure and income**—variables we have *not yet measured*. More maps alone are unlikely to answer that question.

<small>All percentages are Harrell shares of the votes for the two named finalists, unless specified. The 2021 race had a different opponent (Lorena González). Matching is descriptive, not an estimate of voter switching or campaign effects. Charts use King County official results, 2025 voting-district geometry and geographically allocated 2020 Census data.</small>

**[How the methods work: plain-English guide + technical appendix](../docs/methodology/techniques_explained.md)** · [Data and boundary methodology](../docs/methodology/precinct_matching.md) · [Source code](../scripts/) · [King County 2025 results](https://data.kingcounty.gov/d/rkie-6y8x)

*Editorial draft for review. Figures other than the new model scorecard are generated on the local checkout and require a final publication commit.*
