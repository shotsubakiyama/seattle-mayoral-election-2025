# Seattle's 2025 election, under the microscope
### An educational Python and political-geography research project

*A nonpartisan, graph-led project for Seattle readers and technical reviewers. The second-edition article uses a connected story: predict, inspect the misses, match similar precincts, and map sharp boundaries.*

**[Read the story](reports/00_beyond_the_election_map.md)** · **[Plain-English data dictionary](data/README.md)** · **[Technical methods](docs/methodology/techniques_explained.md)**

![Predicting November from the August primary](reports/figures/how_prediction_works.svg)

**Research question:** What can we learn about Seattle's election beyond mapping where Harrell and Wilson won? This project explores three complementary methods:

| Technique | Question | Main tools |
|---|---|---|
| Prediction and geographic cross-validation | How much was November already visible in August? | scikit-learn, Ridge, GroupKFold |
| Historical precinct twins | Which places looked similar before November but diverged? | NearestNeighbors, matched precinct/Census features |
| Political fault lines and spatial statistics | Where do adjoining precincts disagree, and are prediction errors spatially associated? | Shapely, NumPy, SciPy, Moran-style permutations |

**Status:** second-edition draft on a review branch; the first edition is published on main. The new chart build is reproducible through GitHub Actions. Claims are exploratory, not causal.

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
python scripts/build_story_visuals.py
python scripts/spatial_residual_clusters.py
python scripts/precinct_twins.py
python scripts/precinct_twins_history.py
python scripts/twin_case_studies.py
python -m unittest discover -s tests
~~~

Official election CSVs and geographic data are cached under the Git-ignored `data/raw/` directory. The 2020 Census crosswalk is in `data/processed/`. Reports and visualizations are generated under `reports/`.

**For review:** The story-generation script builds new SVGs from the saved precinct model; the branch's GitHub Actions workflow validates and commits them for online preview. Don't merge the draft until the story and charts have been reviewed.

## Interpretation boundaries

The 2021 and 2025 elections had different opponents and electorates. Census demographics describe residents, not voters. This version does **not** measure homeownership or income. The most divergent matched pairs are case studies selected after seeing November results; they do not establish why voting differed.

See the [technical appendix](docs/methodology/techniques_explained.md) for calculations, parameters, and uses elsewhere; the [data dictionary](data/README.md) explains variables and why geographic files are called crosswalks.
