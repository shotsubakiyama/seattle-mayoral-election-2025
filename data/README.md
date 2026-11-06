# Data guide: What these files actually mean

This folder stores the reusable tables behind the election analysis. The filenames are machine-oriented because the scripts rely on them; the **plain-English names** below are for readers.

## Start here

| Reader-friendly name | Actual filename | What's in it |
|---|---|---|
| **2021 and 2025 mayoral results lined up by precinct** | seattle_mayor_precinct_panel_2021_2025.csv | One row per precinct, vote totals and shares for both elections, with **stable_boundary** indicating when a direct historical comparison is defensible. |
| **Which Seattle community area is each precinct in?** | precinct_to_cra_crosswalk.csv | Precinct ID, best-fitting Community Reporting Area (CRA), and a dominance measure. Community Reporting Areas are broad labels, not exact neighborhood identities. |
| **2020 Census population estimates allocated to 2025 voting precincts** | block_group_to_2025_precinct_crosswalk.csv | One row per Census block group/precinct intersection, with estimated fractions of population, voting-age population, and housing counts assigned to the precinct. |
| **2020 Census blocks matched to 2025 precinct geography** | census_block_to_2025_precinct_crosswalk.csv | Underlying block-level geographic mapping that supports the aggregation. |
| **November precinct votes versus model estimates** | precinct_surprises_2025.csv *(generated locally)* | Each eligible precinct's observed share, held-out estimated share and prediction error. |
| **Similar precincts by earlier voting history** | precinct_twins_history_2025.csv *(generated locally)* | Selected historical matches and their 2021, August 2025 and November 2025 voting gaps. |

**What is a “crosswalk”?** It's simply a **lookup or translation table**. Voting precincts and Census statistical areas have different names and geographic boundaries. This table shows which pieces correspond, so the datasets can be combined without pretending their borders match exactly.

**What does “allocated” mean?** The Census does not arrive in King County's 2025 voting precinct format. Our mapping assigns *estimated fractions* of 2020 Census totals to each 2025 precinct. These are estimates about **residents and housing**, not a list of 2025 voters.

## Useful column translations

| Column | Plain English |
|---|---|
| precinct_id | Numeric ID identifying one Seattle voting precinct |
| cra_name | Community Reporting Area label used for the precinct |
| harrell_share_2025 | Harrell's November 2025 votes divided by votes for Harrell plus Wilson |
| stable_boundary | Whether direct geographic comparison with 2021 passed the project's validation rule |
| primary_harrell_share | August Harrell votes divided by votes for Harrell plus Wilson only |
| primary_other_share | Portion of August named-candidate votes going to other candidates |
| vap_ratio | Estimated fraction of 2020 residents old enough to vote |
| occupancy_ratio | Portion of 2020 housing units occupied; **not homeowner/renter share** |
| log_pop_density | Population density on a logarithmic scale, used by the model |
| residual_pp | Actual minus predicted November Harrell share, in **percentage points** |

Original filenames stay in place to avoid breaking reproducible scripts. The article uses the friendly labels above instead of asking readers to decode engineering vocabulary.

## File status

Some processed files are versioned on GitHub; model tables can be regenerated on the user's computer or in the publication build from official source files. The [README](../README.md) includes commands. See [boundary methodology](../docs/methodology/precinct_matching.md) for matching details.
