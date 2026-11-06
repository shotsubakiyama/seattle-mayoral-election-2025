# Visual research inspirations for the next edition

*Curated November 2026. These are design and analytical references, not claims that their methods have already been implemented in this project.*

The goal is to move from a chart that **displays results** to a small visual puzzle whose method and result become clear to a reader in one sitting. Most examples are election-related. A handful borrow clever ideas from other disciplines.

## Elections and political geography — 18 cases

| # | Example | What is worth borrowing |
|---|---|---|
| 1 | [The Urbanist — Katie Wilson's precinct-by-precinct victory](https://www.theurbanist.org/katie-wilsons-path-to-election-victory-precinct-by-precinct/) | Seattle-specific baseline; don't rediscover widely known apartment-versus-homeowner geography |
| 2 | [NYT — an extremely detailed map of the 2024 election](https://www.nytimes.com/interactive/2025/us/elections/2024-election-map-precinct-results.html) | Seamless overview-to-street map, alongside rigorous data caveats |
| 3 | [NYT — where Democratic votes shifted in 11 cities (project page)](https://jk-lee.com/projects/nyt-2024-11-28-mapping-vote-shift/) | Compare *change* rather than winners; make a citywide pattern legible |
| 4 | [VoteHub — the 2024 election at a precinct level](https://votehub.com/2024-map/) | Toggle between vote share, margins, shifts, and modeled demographic subgroups; label modeled outcomes |
| 5 | [Washington Post — How Trump built his victory, vote by vote](https://www.washingtonpost.com/elections/interactive/2024/2024-election-vote-map/) | One dot/grain stands for one vote; use meaningful units rather than visually oversized geographic polygons |
| 6 | [Washington Post — See how people like you vote](https://www.washingtonpost.com/elections/interactive/2024/voting-patterns-presidential-elections/) | Personalized reveal of long-run demographic trends; teach the variable before showing the comparison |
| 7 | [Washington Post — How counties are shifting in 2024](https://www.washingtonpost.com/elections/interactive/2024/11/05/compare-2020-2024-presidential-results/) | Directional arrows to show election-to-election swing, independent of which candidate leads |
| 8 | [NYT — Do you live in a political bubble?](https://www.nytimes.com/interactive/2021/04/30/opinion/politics/bubble-politics.html) | Turn neighborhood spatial similarity into a relatable question |
| 9 | [Washington Community Alliance — Elections dashboard](https://wacommunityalliance.org/elections/) | Two coordinated maps, precinct controls and transparent interpretation |
| 10 | [Minnesota Star Tribune — split-ticket counties disappearing](https://www.startribune.com/fewer-trump-klobuchar-counties-show-dwindling-split-ticket-voting/601180559) | Plot two races together to reveal which counties break partisan expectations |
| 11 | [ProPublica — literacy and voter turnout](https://www.propublica.org/article/voter-participation-literacy-accessibility) | Build a focused, testable question from a surprising combination of public datasets |
| 12 | [ProPublica — How well are your elections run?](https://projects.propublica.org/voting/) | County-level searchable election-administration metrics and diagnostic comparison |
| 13 | [The Pudding — In pursuit of democracy](https://pudding.cool/2025/11/democracy/) | Classify 140+ years of congressional text; use NLP/LLM classifications to tell a chronological visual story |
| 14 | [Financial Times — the 2024 year of democracy in six charts](https://www.ft.com/content/350ba985-bb07-4aa3-aa5e-38eda7c525dd) | Clear small-multiple graphics with one strong interpretation per chart |
| 15 | [Call the Map — The Drift](https://www.callthemap.com/news/the-drift) | Linked maps and paired timelines showing long-term movement instead of a one-year snapshot |
| 16 | [Washington Post — where voters moved since 2020](https://www.washingtonpost.com/politics/2024/04/11/where-2024-voters-moved-since-2020-how-they-registered/) | Consider demographic/voter mobility as an unmeasured alternative to persuasion |
| 17 | [FiveThirtyEight — Atlas of Redistricting (project data)](https://github.com/fivethirtyeight/redistricting-atlas-data) | Compare simulated alternative maps and define precise metrics, not just actual geography |
| 18 | [Matt Stiles — presidential elections mapping scripts](https://github.com/stiles/presidential-elections) | Reproducible open-source path from official results to proportional symbols and county swing arrows |

## Other fields — 8 cases

| # | Example | Why the technique might transfer |
|---|---|---|
| 19 | [The Pudding — The Real Kevin Bacon](https://pudding.cool/2026/10/kevin-bacon/) | Graph networks and shortest-path/centrality metrics; could illustrate precinct similarity networks |
| 20 | [The Pudding — Are you more likely to die on your birthday?](https://pudding.cool/2025/04/birthday-effect/) | **Best pedagogical model:** introduce one observation, show noise, increase sample size, then teach a statistical test |
| 21 | [The Pudding — The pour-igin of species](https://pudding.cool/2025/04/wine-animals/) | Computer vision extracts a quirky label, then price-vs-quality residuals expose better-than-expected cases |
| 22 | [The Pudding — NYC's Urban Textscape](https://pudding.cool/2025/07/street-view/) | Transform messy real-world images into searchable geographic data |
| 23 | [The Pudding — Happy map](https://pudding.cool/2026/02/happy-map/) | Map many small human observations while keeping their human meaning central |
| 24 | [The Pudding — Comparisons as Predictable as the Sunrise](https://pudding.cool/2026/05/similes/) | Corpus mining + clustering to reveal patterns invisible when reading one document |
| 25 | [ProPublica — Machine Bias](https://www.propublica.org/series/machine-bias) | Audit prediction errors, asymmetries and limits rather than reporting only average model accuracy |
| 26 | [The Pudding — 5,000 historical restaurant menus](https://pudding.cool/2026/06/menu-collection/) | Make a historical data archive exploratory and approachable |

## Five designs I'd actually prototype

1. **The Birthday Effect approach for electoral surprises:** begin with one striking precinct gap, then show the reader how much random variation is expected; demonstrate why we did not label every residual a discovery.
2. **The Kevin Bacon approach for Political Twins:** build a graph of precincts connected by pre-November similarity, show the nearest matches and then reveal which edges stretch the farthest in November. Use scikit-learn and NetworkX.
3. **The NYT city-shift approach:** a Seattle-wide map of actual-versus-expected vote shift, with selectively annotated precinct cases instead of an unlabeled scatter cloud.
4. **The Financial Times approach:** one result per chart, with a large, plain-language takeaway and a one-paragraph explanation of the method directly beneath it.
5. **The Washington Post vote-unit approach:** scale precinct symbols by ballots, not area; a large park or industrial precinct should not visually overpower densely populated voting districts.

## Editorial rule for the next revision

Before coding a new chart, answer in one sentence: **“What new thing will an informed Seattle reader learn?”** After coding, answer: **“Can a nontechnical reader explain the algorithm's main trick without opening an appendix?”**

A more exotic package is not a substitute for a finding; a simple explanation of a surprising, carefully checked result is the strongest technical demonstration.
