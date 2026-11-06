# Beyond the Election Map
### Seattle's 2025 mayoral election through statistical learning and political geography

*A nonpartisan, graph-first research project.*

**[Read the visual research brief](reports/00_beyond_the_election_map.md)** · **[Learn the methods](docs/methodology/techniques_explained.md)** · [Data and boundary validation](docs/methodology/precinct_matching.md)

![Three predictive baselines from the research note](reports/figures/model_comparison_scorecard.svg)

**Research question:** What can we learn about Seattle's election beyond mapping where Harrell and Wilson won? This project explores three complementary methods:

| Technique | Question | Main tools |
|---|---|---|
| Prediction and geographic cross-validation | How much was November already visible in August? | scikit-learn, Ridge, GroupKFold |
| Historical precinct twins | Which places looked similar before November but diverged? | NearestNeighbors, matched precinct/Census features |
| Political fault lines and spatial statistics | Where do adjoining precincts disagree, and are prediction errors spatially associated? | Shapely, NumPy, SciPy, Moran-style permutations |

**Status:** editorial draft; analytical results have been run on Windows ARM64 and 32 tests passed at the last user verification. Claims are exploratory, not causal. Some figures exist only on the local checkout until the final publication commit.

## Reproduce with VS Code (Windows / Python 3.12+)

Run from the repository root:

~~~powershell
python -m pip install -r requirements-spatial-stats.txt
python scripts/diagnose_precinct_matching.py
python scripts/spatial_precinct_overlap.py
python scripts/political_fault_lines.py
python scripts/render_fault_line_cases.py
python scripts/model_precinct_surprises.py
python scripts/build_model_scorecard.py
python scripts/spatial_residual_clusters.py
python scripts/precinct_twins.py
python scripts/precinct_twins_history.py
python scripts/twin_case_studies.py
python -m unittest discover -s tests
~~~

Official election CSVs and geographic data are cached under the Git-ignored `data/raw/` directory. The 2020 Census crosswalk is in `data/processed/`. Reports and visualizations are generated under `reports/`.

**For publication:** Ensure these locally generated SVGs are committed to the branch alongside the research article: `precinct_surprises_scatter.svg`, `twin_case_studies.svg`, and `fault_line_1709_1724_v2.svg`. The model-comparison SVG is already checked in. Other experimental charts may remain untracked.

## Interpretation boundaries

The 2021 and 2025 elections had different opponents and electorates. Census demographics describe residents, not voters. This version does **not** measure homeownership or income. The most divergent matched pairs are case studies selected after seeing November results; they do not establish why voting differed.

See the [technical appendix](docs/methodology/techniques_explained.md) for calculations, parameters, uses of these methods in other fields, and source links.
