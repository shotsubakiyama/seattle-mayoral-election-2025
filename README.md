# Beyond the Election Map
### Seattle's 2025 mayoral election, explained with Python

**[Read the illustrated research story](reports/00_beyond_the_election_map.md)** · **[See how the algorithms work](docs/methodology/techniques_explained.md)** · **[Understand the datasets](data/README.md)**

![How predictive were August's primary results?](reports/figures/explained_model_errors.svg)

This is a public, **nonpartisan computational research portfolio** aimed at two audiences: Seattle readers interested in their city and technical readers interested in how data science can make familiar information more revealing.

The project's guiding question is not simply *Who voted for whom?* It is:

**Can Python learn Seattle's usual voting patterns, then identify places where those patterns don't hold?**

## The project in three computational moves

| Technique | Plain-English question | Code/packages |
|---|---|---|
| Predictive learning, geographic cross-validation | What could prior voting tell us about November? | scikit-learn (Ridge, GroupKFold), NumPy |
| Historical nearest-neighbor matching | Which precincts looked similar before November but voted differently? | scikit-learn (NearestNeighbors), Census/vote data |
| Spatial graph and adjacency analysis | Where did neighboring precincts differ most sharply? | Shapely, SciPy, Matplotlib |

The [methods appendix](docs/methodology/techniques_explained.md) also explains spatial autocorrelation and a new **leave-one-feature-out** model interpretation test. All conclusions are exploratory, not causal.

## Reproduce in VS Code (Python 3.12+)

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

Original official source files are downloaded and cached under **data/raw/**, which is intentionally not committed. The derived public mapping data, scripts, chosen SVG figures, and notes live in the repository. [Data README](data/README.md) explains terms like “crosswalk” without assuming a data-engineering background.

## How to read the claims

- The August–November model is a **retrospective, geographically held-out prediction test**. It is not a forecast issued before the general election.
- The Census measurements describe **2020 residents and housing**, not individual 2025 voters. Occupied units are not the same as homeowner/renter share.
- The selected precinct twins were chosen because they have large November differences despite similarities on a limited set of earlier measures. They are **research leads**, not evidence of individual vote switching.
- Vote comparisons across 2021 and 2025 have different opponents. Changed historical precinct boundaries require careful handling.

See [precinct boundary methods](docs/methodology/precinct_matching.md) for the technical matching constraints.

This version is developed via a GitHub pull request so the previously published article on main remains available while the revised narrative is reviewed.
