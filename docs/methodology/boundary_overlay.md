# Boundary-overlay diagnostic

This is methodological infrastructure, not a headline finding.

The numeric precinct-ID diagnostic found 850 previously verified stable IDs, another 155 shared IDs needing geographic validation, and 14 IDs without a 2021 counterpart. Before estimating electoral shifts for those 169 cases, we must examine actual shapes rather than relying on names.

## Run locally (Windows PowerShell)

    python -m pip install -r requirements-spatial.txt
    python scripts/spatial_precinct_overlap.py

Requires that \`python scripts/diagnose_precinct_matching.py\` has already downloaded the certified CSV files. The GIS script downloads King County's archived 2021 and 2025 voting-district polygon layers via ArcGIS REST. It also uses the Windows certificate-store fallback if Python's SSL validation fails. Geometry and a detailed overlap crosswalk remain local under gitignored \`data/raw/precinct_shapes/\` in accordance with King County's data redistribution restrictions.

The script compares polygons in EPSG:2926, reports same-ID intersection-over-union, and measures whether 2021 polygons collectively cover 2025 precincts. The overlap CSV gives the fraction of each **2025 precinct's geographic area** contributed by 2021 precincts. This is not a population-based or vote-based allocation: do not use area fractions directly to infer precinct vote changes.

It should be followed by a population-weighted harmonization where necessary. The existing 850-precinct panel remains our conservative direct-comparison baseline.

Official sources:
- https://www5.kingcounty.gov/sdc/?Layer=votdst_2021_area
- https://www5.kingcounty.gov/sdc/?Layer=votdst_2025_area
