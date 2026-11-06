# What the election data files mean

This folder is the **cleaned, machine-readable material** used by the analyses. If you are new to GIS or data engineering, think of the files as stages in turning official election tables and Census geography into one usable Seattle precinct dataset.

## Human-readable guide to existing files

| File in this repo | What it means in plain English | Used for |
|---|---|---|
| block_group_to_2025_precinct_crosswalk.csv | **Estimated Census population and housing assigned to 2025 precincts** | Model inputs: estimated population, voting-age share, housing occupancy and density |
| census_block_to_2025_precinct_crosswalk.csv | **Geographic lookup: 2020 Census blocks mapped to 2025 election precincts** | Allocating or comparing boundaries from different map systems |
| precinct_to_cra_crosswalk.csv | **Election precinct → Seattle community reporting area lookup** | Giving charts approximate area labels such as Highland Park or Queen Anne |
| seattle_mayor_precinct_panel_2021_2025.csv | **Side-by-side 2021 and 2025 mayoral results for historically comparable precincts** | Election-history checks, turnout, matched historical precinct twins |
| precinct_surprises_2025.csv (generated locally) | **Actual November shares, model estimates, and prediction misses** | Prediction accuracy and outlier figures |
| precinct_twins_history_2025.csv (generated locally) | **Pairs of similar precincts that later voted differently** | Historical twins chart and case studies |

The original filenames are currently retained as **stable data interfaces** because Python scripts and tests read them by name. Rather than break reproducibility with an unexplained mass rename, this is the user-facing catalog. When we eventually change filenames, the code and documentation should be migrated together.

## What is a “crosswalk” anyway?

Imagine laying a 2020 Census map on top of a 2025 precinct map. The borders do **not** necessarily line up. A *geographic crosswalk* is a translation table recording which pieces correspond and—where necessary—what fraction of a source area gets assigned to a target area.

For example, one Census block group may overlap several election precincts. A row such as *allocated_population_2020* estimates the number of that block group's residents assigned to one precinct. A fractional value (e.g., 643.75) is normal for an **estimate**; it is not a count of individual voters.

## Column glossary

| Field | Meaning |
|---|---|
| precinct_id | Shared numeric portion of a Seattle election precinct identifier |
| block_group_geoid | Official Census geographic identifier for a block group |
| allocated_population_2020 | Estimated residents allocated to this precinct from a 2020 block group |
| allocated_vap_2020 | Estimated voting-age residents allocated to this precinct |
| allocated_housing_units_2020 | Estimated total housing units allocated to the precinct |
| allocated_occupied_housing_2020 | Estimated occupied units allocated to the precinct |
| population_weight | Share of the source geography's population allocated to the destination geography |
| cra_name | Community reporting area label—not a precise cultural neighborhood boundary |
| dominant_share | Relative geographic dominance of the assigned community reporting area |
| stable_boundary | Flag indicating whether this precinct has verified comparable 2021/2025 shapes |
| harrell_share_2021 | Harrell share of the two named mayoral candidates' votes in 2021 |
| harrell_share_2025 | Harrell share of the two named mayoral candidates' votes in November 2025 |
| residual_pp | Actual November Harrell percentage minus the model's expected percentage, in **percentage points** |

## Limits

**2020 residents are not necessarily 2025 voters.** Census allocation provides approximate geographic context, not the exact demographic composition of ballot-casters. Occupied housing share is **not** renter share or homeownership. CRA labels are broad areas, not a verified street address for a precinct. For direct historical comparisons we prioritize stable-boundary precincts; a repeated numeric precinct ID alone does not prove geography is unchanged.

Reproduction instructions: [repository README](../README.md). Methodology: [historical boundary matching](../docs/methodology/precinct_matching.md).
