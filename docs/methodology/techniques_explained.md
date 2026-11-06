# Methods behind the maps
*A plain-English guide and reproducibility notes for [Beyond the Election Map](../../reports/00_beyond_the_election_map.md).*

**Why these techniques?** Standard election maps answer *who won where*. These methods ask different questions: *What would we expect? Which places are comparable? Where do boundaries matter? Could a pattern be random?*

## A / Predicting without fooling ourselves

**Plain English.** If I already know a precinct's August voting and the broad characteristics of its residents, how closely can I predict November? We fit a model on some areas, then make it predict areas it has **not seen**. The distance between predicted and actual percentages is our error.

**Where else used:** The same logic appears in medical machine learning: when many observations come from the same patient, researchers hold out *patients*, not individual samples. [scikit-learn's grouped cross-validation guide](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data) explains why related observations should stay together.

**What we implemented:**
- **Outcome:** November 2025 Harrell votes divided by the Harrell + Wilson two-candidate total, by precinct.
- **Baseline #1:** use each precinct's August Harrell share among Harrell + Wilson votes directly, without fitting. Weighted mean absolute error **5.32 percentage points**.
- **Baseline #2:** fit the two August primary features with Ridge regression: Harrell's finalist share and other named candidates' share of all named primary votes. Out-of-fold error **3.39 points**.
- **Expanded model:** also add three 2020 Census-derived features: estimated voting-age share, housing-unit *occupancy* share and log population density. Out-of-fold error **3.01 points**.
- **Test design:** five-fold **GroupKFold** with precincts grouped by approximately 10,000-foot projected-coordinate grid cells; none of a held-out cell's precincts enters that fold's training set. Nearby cells can still be adjacent, so this is *not* a strict geographic-buffer holdout.
- **Model:** scikit-learn [Ridge regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html), standardized using training-fold means and standard deviations. The model penalizes very large coefficients, which can reduce unstable fits from correlated variables. Weights depend on the precinct's November two-candidate votes.
- **Error:** \(\mathrm{MAE}_{w}=\frac{\sum_i v_i\,|\hat{s}_i-s_i|}{\sum_i v_i}\), where \(v_i\) is November two-candidate votes and \(s_i\) is Harrell's vote share. Displayed in percentage points.

**Interpretation:** Prediction accuracy does not identify causes; a basic election-history predictor can be strong because neighborhoods have relatively persistent voting patterns. The 2020 Census describes **residents**, not the actual 2025 electorate.

**Code:** [model_precinct_surprises.py](../../scripts/model_precinct_surprises.py) and [build_model_scorecard.py](../../scripts/build_model_scorecard.py).

## B / Precinct twins: compare like with like (but only partly)

**Plain English.** Imagine two neighborhoods with nearly matching political histories and broad demographic profiles. If their November outcomes diverge, we've found a *research question*: what else differs?

**Where else used:** Nearest-neighbor algorithms also power similarity search and image reconstruction; see [scikit-learn's nearest-neighbors documentation](https://scikit-learn.org/stable/modules/neighbors.html). In observational research, matching on pre-outcome characteristics is a common way to create a more meaningful comparison. Our version is **exploratory**, not a causal matching design.

**What we implemented:**
- Start from the **850** previously validated stable-boundary historical precincts. After eligibility filtering for the model and historical vote counts, **846 precincts** remain for this exercise.
- Use 2021 Harrell two-candidate share, 2025 August Harrell/Wilson share, August share of other named candidates, and the three Census attributes above. **No November result is allowed into the similarity calculation.**
- Restrict pre-November differences using *calipers*: at most **5 percentage points** for 2021 Harrell share and August finalist share, **10 points** for August other-candidate share, **10 points** for voting-age fraction, **12 points** for occupied-housing fraction and approximately **2×** population density. A combined normalized-distance filter is also applied.
- Require precincts at least **one mile** apart by straight-line representative-point distance, at least **100 votes in 2021**, and at least **150 November two-candidate votes** in each precinct.
- Then—and only then—rank November differences. **1,775 candidate pairs** passed the combined checks; the displayed pairs are deliberately selected extremes, with no precinct repeated in the displayed shortlist.

**A subtle point:** The primary's “Harrell share” here means his fraction of votes for **Harrell plus Wilson only**; other primary candidates are represented separately. That allows the finalist comparison but is not the same as his share of the whole August ballot.

**What matching does not control:** The available Census crosswalk is *not* an income, educational-attainment or homeownership dataset. Matching a couple of historical political measures and three Census quantities is **not** proof that a pair is otherwise demographically identical. In 2021 Harrell faced **Lorena González**, so those shares are also not a fixed-candidate comparison across all three stages.

**Code:** [precinct_twins.py](../../scripts/precinct_twins.py), [precinct_twins_history.py](../../scripts/precinct_twins_history.py) and [twin_case_studies.py](../../scripts/twin_case_studies.py).

## C / Political fault lines: turn a precinct map into a network

**Plain English.** Treat every precinct as a point in a network. Draw a connection only when two precinct polygons share a meaningful border. Compare vote shares *across those connections*, not every possible pair in the city.

**Where else used:** This is the same **graph representation** used in transportation and network science—places are nodes, relationships are edges—although here an edge means a shared geographic boundary, not a road or a social tie. Spatial adjacency is a standard starting point for geographic statistics.

**What we implemented:**
- Pull official 2025 election precinct polygons and count votes for Harrell and Wilson.
- Use Shapely to find polygons sharing **at least 100 feet of border**. Touching only at a corner does not qualify.
- Require **at least 100 two-candidate votes per precinct**.
- Rank the **2,582 eligible neighboring pairs** by the absolute difference in Harrell's two-candidate vote share. We used local SVG maps to inspect the actual precinct shapes.

**Interpretation:** A very large gap along a shared border is visually interesting but need not be politically surprising. It might reflect visible differences in housing and urban form. The method locates differences; it does not explain their cause.

**Code:** [political_fault_lines.py](../../scripts/political_fault_lines.py) and [render_fault_line_cases.py](../../scripts/render_fault_line_cases.py).

## D / Spatial autocorrelation: is a pattern stronger than chance?

**Plain English.** Are unusually high (or low) model errors next to one another more often than random reshuffling would produce? This is *spatial autocorrelation*.

**Where else used:** Spatial cluster and outlier analysis is used to study **affluence–poverty boundaries, abnormal spending and elevated diabetes rates**. See [Esri's Local Moran's I methodology and applications](https://pro.arcgis.com/en/pro-app/3.4/tool-reference/spatial-statistics/h-how-cluster-and-outlier-analysis-anselin-local-m.htm).

**What we implemented:**
- Test the *out-of-fold prediction errors*, not raw candidate shares. A positive error means Harrell exceeded model expectation; a negative one means Wilson did.
- Define rook-style adjacency as at least **100 feet of shared border**, with row-standardized neighbors.
- **Global Moran's I:** a citywide summary of how neighboring residuals co-vary. The observed value was **0.100**, with a permutation p-value of **0.0001** from **9,999 permutations**.
- **Local Moran-style tests:** fix each precinct's residual and repeatedly draw alternative neighbor residuals without replacement, computing a two-sided deviation from the permutation-null center. Adjust the roughly 1,000 local tests with **Benjamini–Hochberg false-discovery-rate correction** at 5%.
- **Result:** not a single individual precinct survived the local correction, despite the weak positive *citywide* association.

**Why we didn't use the full PySAL package:** Windows ARM64 installation pulled in GDAL-dependent packages without a working wheel. We implemented the core global and local **Moran-style** permutation computations with NumPy, SciPy and Shapely, and tested them against synthetic spatial patterns. **Our Monte Carlo conventions are not numerically identical to PySAL's**; results are reproducible for this implementation, not presented as a PySAL reference calculation.

**Code:** [spatial_residual_clusters.py](../../scripts/spatial_residual_clusters.py).

## E / Geographic matching, inputs and reproducibility

**Boundary changes are a data-quality problem, not the story.** King County's 2021 and 2025 precinct shapes do not line up everywhere. For valid direct historical comparison, the project uses the **850 stable-boundary matched precincts** rather than pretending a shared precinct ID guarantees unchanged geography. A separate overlay diagnostic found that **1,014 of 1,019** 2025 precincts have at least 99% of their area covered by 2021 polygon geography; that does **not** mean all their votes can be reassigned exactly.

**Primary inputs**
- [King County November 2025 general precinct results](https://data.kingcounty.gov/d/rkie-6y8x).
- [King County August 2025 primary precinct results](https://data.kingcounty.gov/d/tsx2-ia8a).
- [King County precinct geography and historical data](https://kingcounty.gov/en/dept/elections/maps/precinct-and-district-data).
- [County 2021 general precinct results](https://data.kingcounty.gov/d/4qrf-rjar).
- Project's 2020 Census block-group population-allocation crosswalk, stored under [data/processed](../../data/processed/).

**Limits worth remembering:** ecological fallacy (precinct data are not person data); winner-share measurements exclude other votes; changing turnout; model feature omissions; multiple comparisons; extreme pair selection; uncertain geographic allocations.

**Full reproduction:** Start at the [repository README](../../README.md). The charts embedded in the report are generated from official inputs and the existing repository code; their output files must be included in the publication commit.

*This appendix documents what was actually implemented, not a claim that the project established causality.*
