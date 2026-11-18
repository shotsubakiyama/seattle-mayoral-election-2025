# Seattle, Through the Numbers
### Eight Computational Experiments on the 2025 Election

**Independent research by Sho Tsubakiyama · November 2026**

Seattle's 2025 mayoral election was decided by just **2,011 votes**. This project asks what the precinct returns can tell us beyond the headline result: where the city divided, how participation affected the arithmetic, what looked predictable, what only looked surprising, and what happens when an algorithm redraws Seattle without being told its neighborhood names.

![Seattle 2025 mayoral vote share by precinct with community-reporting-area outlines and neighborhood labels](reports/figures/seattle_2025_mayor_precinct_map.svg)

If you are coming to the project without much Seattle context, start with the map above. The labels are geographic anchors; the thin outlines are community-reporting areas, not a claim that Seattle has one official set of neighborhood boundaries.

### **[Read the full illustrated research report](reports/seattle_through_the_numbers.md)**

Three findings frame the rest of the project:

- **The citywide result was close, but Seattle was not geographically uniform.** Precinct-level differences were much larger than the 50–50 citywide finish suggests.
- **The mayoral map is not the whole political map.** Harrell-winning precincts still backed several other citywide winners by clear margins.
- **The most useful computational results are often the ones that limit the claim.** Simulations make extreme-looking precinct pairs less surprising, aggregate returns cannot identify individual split-ticket voters, and the electoral-region map changes under alternative specifications.

The eight experiments cover cross-race coalitions, participation reweighting, prediction uncertainty, matched-precinct simulations, campaign finance, ecological inference, graph-based community detection, and boundary stability.

The analysis is reproducible in Python. GitHub Actions rebuild the official-data pipeline, rerun the regression suite, regenerate the figures, and assemble both the Markdown report and a publication-ready `index.html`.

[Source code](scripts/) · [Plain-English methods guide](docs/methodology/techniques_explained.md) · [Earlier precinct modeling work](reports/00_beyond_the_election_map.md)

*Independent, nonpartisan, exploratory analysis. Precinct-level patterns describe places, not individual voters, and do not establish why a neighborhood voted as it did.*
