# Beyond the Election Map
### Exploring the political geography of Seattle's 2025 mayoral election

This is a Python-based, nonpartisan research project combining King County election data, Census crosswalks, geographic analysis, predictive modeling, and original data visualization.

**Start here:** [Beyond the Election Map — research article (draft)](reports/00_beyond_the_election_map.md)

The central question: **What can we learn beyond simply mapping which candidate won?** The project investigates historical precinct twins, unusual local voting contrasts, and what August 2025 already predicted about November.

## Main outputs

- **Precinct Twins:** compare similar pre-election precinct profiles that diverged in November.
- **Political Fault Lines:** measure differences across precincts sharing a physical boundary.
- **Electoral surprises:** cross-validated models of November shares using August results and basic 2020 Census characteristics.
- **Spatial checks:** test whether prediction errors cluster geographically without overstating local significance.

These are exploratory, descriptive comparisons, **not causal explanations or individual-voter analyses**. Detailed boundary matching and other data-quality work live in [methodology notes](docs/methodology/precinct_matching.md).

## Reproduce on Windows / VS Code

Use Python 3.12+ in a terminal opened at the project root.

~~~powershell
python -m pip install -r requirements-spatial-stats.txt
python scripts/diagnose_precinct_matching.py
python scripts/spatial_precinct_overlap.py
python scripts/political_fault_lines.py
python scripts/render_fault_line_cases.py
python scripts/model_precinct_surprises.py
python scripts/spatial_residual_clusters.py
python scripts/precinct_twins.py
python scripts/precinct_twins_history.py
python scripts/twin_case_studies.py
python -m unittest discover -s tests
~~~

The scripts download certified precinct results and archived King County GIS geometry; large source files are cached under the Git-ignored `data/raw/` directory. Many report figures and CSVs are regenerated locally rather than maintained by hand.

**Publishing note:** Generated files under `reports/` are not automatically pushed to GitHub. After reviewing them, commit the selected figures and Markdown reports along with the code so that the online research article displays its images.

## Research boundaries

- Stable 2021–2025 precincts can be compared directly; changed boundaries require spatial harmonization and explicit uncertainty.
- August 2025 primary and November 2025 general are different electorates; 2021 had a different opponent.
- Available Census quantities include density, voting-age fraction, and housing occupancy. **They do not establish homeownership or income.**
- The most visually extreme differences are examples selected after observing results, not independent tests of political causes.

## Repository organization

`scripts/` contains analyses, `tests/` contains reproducibility checks, `data/processed/` holds derived geographic tables, `docs/methodology/` documents matching, and `reports/` holds the editorial draft and figures.

**Project status:** research draft under review, not a finished peer-reviewed study.
