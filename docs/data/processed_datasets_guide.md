# What the processed datasets actually mean

This guide translates data-engineering filenames into plain English. The existing filenames are **preserved** to avoid breaking scripts; descriptive aliases can be introduced in a separate, tested migration.

| Existing file | Plain-English description | What it does *not* mean |
|---|---|---|
| `block_group_to_2025_precinct_crosswalk.csv` | **2020 Census block-group estimates allocated to 2025 voting precincts.** Supplies estimated population, voting-age population, housing units, and occupied housing units. | Not the people who actually voted in 2025; not homeownership or renter share. |
| `census_block_to_2025_precinct_crosswalk.csv` | **2020 Census blocks associated with 2025 precinct geography.** A finer geographic link used in preparation/validation. | Not a voter list and not evidence that precinct boundaries were unchanged since 2021. |
| `precinct_to_cra_crosswalk.csv` | **Precinct-to-Seattle community-reporting-area labels.** Provides recognizable geographic names for charts. | Not a unique official neighborhood boundary or a demographic profile. |
| `seattle_mayor_precinct_panel_2021_2025.csv` | **Side-by-side 2021 and 2025 mayoral precinct results**, with boundary-stability checks and turnout context. | Not a panel following the same individual voters. |
| `precinct_surprises_2025.csv` | **One row per modeled precinct**, including August predictors, Census features, November result, and held-out model estimates. Created locally by the analysis script. | Not an advance forecast issued before November. |
| `precinct_twins_history_2025.csv` | **Selected similar precinct pairs**, using 2021 voting, August 2025 voting and Census characteristics before ranking November gaps. Created locally. | Not proof that paired neighborhoods are identical or that a campaign caused their differences. |

## What's a “crosswalk”?

Imagine drawing a Seattle voting-precinct map on transparent paper, then placing it over a map of Census areas. Their borders often **do not line up**. A geographic *crosswalk* is a table that tells our code how to connect the two systems.

Some measures must be **estimated or allocated** because a Census area can overlap more than one precinct. That's why the report says *Census context*, not *precinct voter demographics*.

## Which source feeds which figure?

- **Prediction comparison:** August 2025 primary precinct votes + November 2025 general precinct votes; expanded model adds allocated 2020 Census attributes.
- **Historical precinct twins:** Those same data plus 2021 mayoral results and boundary-stability checks.
- **Political fault lines:** November 2025 precinct votes + 2025 precinct polygons; no historical matching required.
- **Spatial residual test:** Out-of-fold errors from the prediction model + 2025 geographic adjacency.

## Where to inspect the code

- [Build model inputs](../../scripts/model_precinct_surprises.py)
- [Match historical precincts](../../scripts/precinct_twins_history.py)
- [Draw twin case studies](../../scripts/twin_case_studies.py)
- [Find shared-border contrasts](../../scripts/political_fault_lines.py)

*Technical variable names remain unchanged so existing tests and reproducibility instructions continue to work.*
