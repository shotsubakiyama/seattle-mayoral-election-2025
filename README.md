# Seattle Mayoral Election Analysis (2025)

Precinct-level analysis of Seattle's 2025 mayoral election, including comparisons with 2021. The research goal is to uncover patterns that are less obvious than a standard election results map.

## Current repository contents

- `data/processed/seattle_mayor_precinct_panel_2021_2025.csv`: 850 matched precincts with 2021 and 2025 candidate votes, turnout, and swing measures.
- `data/processed/precinct_to_cra_crosswalk.csv`: precinct-to-community reporting area (CRA) assignments.
- `data/processed/block_group_to_2025_precinct_crosswalk.csv` and `census_block_to_2025_precinct_crosswalk.csv`: geographic population-allocation crosswalks.
- `notebooks/01_2025_general_results.ipynb`: initial exploration of 2025 results; requires original source data in `data/raw/`.
- `notebooks/02_2021_2025_comparison.ipynb` and `03_precinct_demographics.ipynb`: currently empty placeholders.

**Current limitations:** This is a work in progress, not yet a reproducible end-to-end pipeline. Raw election downloads are not committed; `data/raw/` is Git-ignored. No dependency manifest or precinct geometry is currently committed. The 850-row matched panel is **not** a complete list of all 2025 precincts; validate coverage before drawing citywide conclusions. Geographic crosswalks are allocations, not direct observations of individuals.

## Open the project in VS Code

1. In VS Code, choose **Source Control → Clone Repository**, then enter `https://github.com/shotsubakiyama/seattle-mayoral-election-2025.git`.
2. Open the cloned folder. Install the Python and Jupyter extensions if you plan to use notebooks.
3. Review the checked-in `data/processed/` CSV files. The first notebook cannot run without the separately downloaded `data/raw/` files.
4. Keep changes in Git branches and review them before merging.

## Editing this repository from ChatGPT

ChatGPT can edit the **GitHub repository** through the connected GitHub app, using a separate branch and pull request. Those edits do **not** immediately change files on your computer. After reviewing/merging a pull request, use **Source Control → Pull** in VS Code (or `git pull`) on your local `main` branch.

For a proposed branch before merging, use **Source Control → Fetch**, then switch to that remote branch in VS Code.

## Next analysis directions

1. **Precinct Twins:** find precincts with similar profiles but unexpectedly different mayoral outcomes.
2. **Political Fault Lines:** identify sharp changes between adjacent precincts.
3. **Local Moran's I / LISA:** detect local spatial clusters and outliers.
4. **Turnout analysis:** evaluate where turnout changes and vote shifts coincide.

These require additional provenance checks, demographic feature construction and/or precinct geometry before making substantive claims.
