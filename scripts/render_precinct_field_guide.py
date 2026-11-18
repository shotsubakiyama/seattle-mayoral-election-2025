"""Render the editorial second draft from generated facts, not placeholder numbers.

A conventional GitHub Markdown research note: concise prose, visible sources,
descriptive chart titles, expandable boundary case studies, explicit caveats.
"""
import csv
import json
from pathlib import Path
from spatial_precinct_overlap import ROOT

FIG=ROOT/"reports/figures"
SUMMARY=ROOT/"data/processed/precinct_field_guide_summary.json"
EXTRA=ROOT/"data/processed/precinct_field_guide_extensions.json"
REPORT=ROOT/"reports/seattle_precinct_by_precinct.md"
REQUIRED=[
 "precinct_count_history.svg",
 "precinct_size_distributions.svg",
 "precinct_2025_mayoral_gradient.png",
 "precinct_vote_weighted_map.png",
 "precinct_neighborhood_variation.svg",
 "precinct_2021_to_2025_harrell_change.png",
 "precinct_2021_to_2025_distribution.svg",
 "precinct_sharp_boundaries.svg",
 "fault_line_1709_1724_v2.svg",
 "fault_line_1955_1957_v2.svg",
 "fault_line_1803_1808_v2.svg",
 "experiment_07_algorithmic_seattle.svg",
 "precinct_cluster_vote_breakdown.svg",
]


def location_for(row,known):
    pid=row["precinct_id"]
    name=known.get(pid) or row.get("near_area")
    if row.get("area_label_quality","").startswith("approximate") and name:
        return f"near {name} (approx.)"
    return name or "area not assigned"


def text_document(data,more,known):
    p=data["precinct_population_2025"]
    h=data["history"];b=data["boundary"]
    hist=more["precinct_count_history"]
    first,last=hist[0],hist[-1]
    delta=last["seattle_precincts"]-first["seattle_precincts"]
    trend=("increased" if delta>0 else "decreased" if delta<0 else "remained unchanged")
    change=more["change_distribution"]
    groups=more["groups"]
    by_year={r["year"]:r["seattle_precincts"] for r in hist}
    latest=lambda row:row["precinct_name"]
    top_voters=p["top_registered"][0]
    top_area=p["top_geographic_area"][0]
    top_ballots=p["top_ballots_cast"][0]
    med_reg=round(p["registered_quantiles"]["0.5"])
    median_area=p["geographic_sqmi_quantiles"]["0.5"]
    nhood={x["name"]:x for x in data["neighborhoods"]}
    queen=nhood["Queen Anne"];capitol=nhood["Capitol Hill"]
    table=[
        "| By which measure? | Precinct and approximate location | Figure |",
        "|---|---|---:|",
        f"| Most registered voters | {latest(top_voters)} · {location_for(top_voters,known)} | {top_voters['registered']:,} voters |",
        f"| Largest geographic polygon | {latest(top_area)} · {location_for(top_area,known)} | {top_area['area_sqmi']:.2f} sq mi |",
        f"| Most ballots counted | {latest(top_ballots)} · {location_for(top_ballots,known)} | {top_ballots['counted']:,} ballots |",
    ]
    table_text="\n".join(table)
    dominant=sorted(data["neighborhoods"],key=lambda x:-x["mean_harrell_pct"])[:4]
    strongwilson=sorted(data["neighborhoods"],key=lambda x:x["mean_harrell_pct"])[:4]
    electoral_rows=[
        "| Computed group (informal area labels) | Precincts | Finalist votes | Harrell | Wilson |",
        "|---|---:|---:|---:|---:|"
    ]
    for r in groups:
        electoral_rows.append(
            f"| Group {r['id']+1}: {r['label']} | {r['precincts']} | {r['finalist_votes']:,} | "
            f"{r['harrell_pct']:.1f}% | {r['wilson_pct']:.1f}% |")
    electoral_table="\n".join(electoral_rows)

    def named_rank(rows):
        return ", ".join(x["name"] for x in rows[:3])
    lower=more["change_distribution"]["declined"]
    return f"""# Seattle, Precinct by Precinct
*An introduction to the city's voting geography, using the 2025 mayoral election*

Seattle's mayoral election was decided by 2,011 votes in November 2025. Those votes came from more than a thousand precincts. Before looking at who won where, it's worth knowing what a precinct is, where its boundaries come from, and how much one precinct can differ from the next.

## 1. How did Seattle get its precincts?

A precinct is a small election-administration area. It determines which ballot a voter receives and gives election officials a way to organize the results. It is not a neighborhood or a City Council district.

Seattle has used wards and precincts since its early years. The [1891 ward-and-precinct map](https://commons.wikimedia.org/wiki/File:Seattle_ward_and_precinct_map,_1891.jpg) shows a very different city.

<a href="https://commons.wikimedia.org/wiki/File:Seattle_ward_and_precinct_map,_1891.jpg"><img src="https://cdn2.picryl.com/photo/1895/12/31/seattle-ward-and-precinct-map-1891-b21ed9-1024.jpg" alt="Seattle ward and precinct map, 1891, Seattle Municipal Archives" width="340"></a>

*Seattle ward and precinct map, 1891. Seattle Municipal Archives.*

Today King County Elections proposes precinct-boundary revisions, which the County Council adopts. Boundaries must fit other electoral districts, and officials periodically adjust them as the population and registration change. King County's limit is generally 900 active registered voters per precinct at the time of boundary balancing; the state ceiling is 1,500. The election-day registered-voter total can differ from the earlier balancing count. [County precinct alterations](https://kingcounty.gov/en/dept/elections/maps/precinct-alterations) · [Washington law](https://app.leg.wa.gov/rcw/default.aspx?cite=29A.16.040).

### Has the number of precincts increased?

![Seattle precinct counts over time from archived King County GIS boundary snapshots](figures/precinct_count_history.svg)

The archived GIS snapshots show **{first['seattle_precincts']:,} precincts in {first['year']}** and **{last['seattle_precincts']:,} in {last['year']}**—a net change of **{delta:+,}**. Counts have {trend} over that period overall, but the chart is not a measure of Seattle's population growth. Redistricting, administrative changes and precinct splitting or consolidation can move the count in either direction.

Between 2010 and 2020, Seattle's population increased **21.1%** (608,660 to 737,015), while its mapped precinct count grew from **{by_year[2010]:,} to {by_year[2020]:,}**, or **{100*(by_year[2020]/by_year[2010]-1):.1f}%**. Precinct counts don't track population one-for-one. [Seattle's Census comparison](https://www.census.gov/quickfacts/fact/table/seattlecitywashington/POP060220).

These are snapshots of the county's year-specific **voting-district maps**. The underlying boundaries can change, and a snapshot count is not always identical to an election's reporting count. [Archived GIS data](https://kingcounty.gov/en/dept/elections/maps/precinct-and-district-data).

## 2. What does a precinct look like today?

The official results list **{data['official_precinct_total']:,}** Seattle precincts in 2025. Of these, **{data['precinct_count']:,}** had votes for one of the two mayoral finalists and usable registration data. The median precinct had **{med_reg:,} registered voters** and covered **{median_area:.3f} square miles**.

![Distributions of registered voters and precinct size, in square miles on a linear scale](figures/precinct_size_distributions.svg)

Most precincts are quite small geographically, but the large outliers matter. The last size bar groups precincts larger than 0.4 square miles instead of squeezing the rest of the distribution into a logarithmic scale. The mapped boundaries can include water, so polygon area is not necessarily dry land.

{table_text}

The numbers describe different things. A large precinct on a map does not necessarily contain many voters, and a precinct with many registered voters may have relatively few ballots cast.

## 3. How did Seattle's precincts vote in 2025?

![Seattle precinct map, with muted blue for Wilson and rust for Harrell](figures/precinct_2025_mayoral_gradient.png)

Each precinct is colored by Harrell's share of votes for Harrell and Wilson. Blue means Wilson led, rust means Harrell led, and lighter shades indicate closer results. **These are candidate colors, not party colors.**

In our comparable-precinct sample, **{named_rank(dominant)}** were among the neighborhood reporting areas with the highest Harrell shares. **{named_rank(strongwilson)}** were among the areas with the lowest. Those broad descriptions can still conceal substantial variation from one precinct to another.

### What if each precinct occupied space according to its votes?

![Geographic voting map compared with a map of vote-proportional precinct circles](figures/precinct_vote_weighted_map.png)

On the left, a precinct's visual size is its geographic area. On the right, each precinct is a circle whose **area is proportional to votes for Harrell or Wilson**. Circles are placed near their precincts, so they can overlap. This is a schematic vote-weighted map—not the location of individual voters.

Parkland and water occupy plenty of space on the left. On the right, precincts with more mayoral votes become more prominent. Neither map alone tells the whole story.

### How similar are precincts within the same neighborhood?

![Neighborhood areas ranked by the typical precinct voting difference from the area average](figures/precinct_neighborhood_variation.svg)

We grouped precincts using existing community reporting areas. For each area, we calculated its vote-weighted Harrell share, then measured **how far its typical precinct was from that average**. A higher bar means more variation *within* the named area, not stronger support for either candidate.

For example, Queen Anne contributes **{queen['precincts']} precincts** and **{queen['finalist_votes']:,} finalist votes** to the comparison. Its typical precinct differed from the Queen Anne average by **{queen['typical_gap_pp']:.1f} points**. For Capitol Hill, the comparable figure is **{capitol['typical_gap_pp']:.1f} points** across **{capitol['precincts']} precincts** and **{capitol['finalist_votes']:,} votes**. We show precinct counts and votes beside the labels so that these differences have some context.

These are descriptive community reporting areas, not the city's formal neighborhood boundaries. For consistency, this chart uses the subset with verified boundaries across 2021 and 2025, with at least 100 votes in each included 2025 precinct.

## 4. How did the geography change since 2021?

![Map of changes in Harrell vote share in comparable precincts, 2021 to 2025](figures/precinct_2021_to_2025_harrell_change.png)

Harrell received a smaller share of the two-finalist vote in **{lower} of {h['comparable_precincts_min100_both']} comparable precincts**. The typical change, measured by the median across precincts, was **{h['median_change_pp']:+.1f} percentage points**. That decline was far from identical across the city.

![Distribution of percentage-point changes in Harrell's vote share between 2021 and 2025](figures/precinct_2021_to_2025_distribution.svg)

Only **{change["increased"]}** of these precincts showed an increase in Harrell's share; **{h["harrell_majority_crossovers"]}** crossed the 50% threshold between the two elections.

The comparison has an important limit: Harrell faced **Lorena González in 2021** and **Katie Wilson in 2025**. We can compare where his *relative support* was higher or lower; we cannot use these precinct totals to determine whether individual people changed their votes. Gray map areas weren't verified as geographically comparable, or lacked enough votes for this analysis.

## 5. Where were the sharpest precinct boundaries?

Two precincts might share a street and still vote quite differently. To find those contrasts, we used **Shapely**, a Python library that works with geographic shapes. It can identify where two precinct polygons share a line and measure that line's length.

We compared every pair of precincts sharing at least **100 feet of border**, provided each cast **100 or more votes** for Harrell or Wilson. We measured the difference between their Harrell vote shares and ranked the gaps.

![Largest Harrell share differences across neighboring precinct boundaries](figures/precinct_sharp_boundaries.svg)

Among **{b['eligible_borders']:,}** qualifying pairs, the median vote-share difference was **{b['median_gap_pp']:.1f} points**. At the **99th percentile**, the gap reached **{b['p99_gap_pp']:.1f} points**. Here, *sharp boundary* simply means the highest 1% by that measure; it is a descriptive cutoff, not a claim about what caused the difference.

### Three nearby contrasts

These three close-ups show adjacent precincts from the ranked analysis. Expand each for a map with surrounding precincts.

<details open>
<summary><strong>Queen Anne — precincts 1709 / 1724</strong> · 57.6-point gap</summary>

![Close-up map of Queen Anne precincts 1709 and 1724](figures/fault_line_1709_1724_v2.svg)

</details>

<details>
<summary><strong>Precincts 1955 / 1957</strong> · 48.9-point gap</summary>

![Close-up map of precincts 1955 and 1957](figures/fault_line_1955_1957_v2.svg)

</details>

<details>
<summary><strong>Precincts 1803 / 1808</strong> · 47.0-point gap</summary>

![Close-up map of precincts 1803 and 1808](figures/fault_line_1803_1808_v2.svg)

</details>

The maps reveal where the difference appears, not why. We would need more information about the buildings, residents and streets on either side before claiming an explanation. The cases were chosen precisely because their differences were large.

## 6. What do computational groupings tell us about neighborhoods?

For a final comparison, we can ignore familiar neighborhood names and group precincts using **Louvain community detection**. First, connect precincts that share a border. Next, make connections stronger when neighboring precincts gave similar results across six 2025 citywide contests. Louvain then searches for groups with relatively strong connections within them.

![Familiar community reporting areas compared with the algorithm's groups](figures/experiment_07_algorithmic_seattle.svg)

This produced **11 groups**. The most Harrell-leaning group, around **{groups[0]['label']}**, gave him **{groups[0]['harrell_pct']:.1f}%** of the two-finalist vote. The most Wilson-leaning group, around **{groups[-1]['label']}**, gave her **{groups[-1]['wilson_pct']:.1f}%**. The labels below are informal geographic descriptions based on represented community reporting areas—not official district names.

{electoral_table}

![Election vote split across the 11 computed precinct groups](figures/precinct_cluster_vote_breakdown.svg)

The table runs from the most Harrell-supporting computed group to the most Wilson-supporting. It makes the map's color-coded clusters easier to interpret: not just where the groups are, but how many precincts and votes each contains.

Geography alone also produces clusters. In a separate comparison with a geography-only network, adding voting patterns changed the grouping relationship for only about **6.8% of shared precinct borders**. The algorithm gives us another perspective on Seattle's political geography, not a replacement for neighborhood boundaries.

## Sources and notes

- [King County certified 2025 general precinct results](https://data.kingcounty.gov/d/rkie-6y8x), [2021 general precinct results](https://data.kingcounty.gov/d/4qrf-rjar).
- [King County historical and current voting-district GIS data](https://kingcounty.gov/en/dept/elections/maps/precinct-and-district-data) and [election archives](https://kingcounty.gov/en/dept/executive-services/data-information-services/archives/find-it-in-archives/county-government-history/elections-history).
- The 2025 citywide maps cover precincts with valid mayoral candidate votes. The 2021 comparison and within-neighborhood chart use a smaller, previously verified stable-boundary subset. **Do not treat those as the same denominator.**
- Polygon area includes water. The vote-weighted circles are visualization symbols, not actual voter locations. The computed groups are exploratory.
- [Reproduce the figures](../scripts/precinct_field_guide.py) · [Additional figure code](../scripts/precinct_field_guide_extensions.py) · [Aggregate research data](../data/processed/precinct_field_guide_extensions.json).

*Second editorial draft. The earlier [eight-experiment report](seattle_through_the_numbers.md) remains in the research archive.*
"""


def main():
    summary=json.loads(SUMMARY.read_text(encoding="utf-8"))
    extra=json.loads(EXTRA.read_text(encoding="utf-8"))
    for p in REQUIRED:
        path=FIG/p
        if not path.exists() or path.stat().st_size<300:
            raise FileNotFoundError(f"Missing chart: {path}")
    known={}
    panel=ROOT/"data/processed/seattle_mayor_precinct_panel_2021_2025.csv"
    with panel.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            known[r["precinct_id"]]=r["cra_name"]
    s=text_document(summary,extra,known)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(s,encoding="utf-8")
    print("Wrote precinct field guide:",len(s.split()),"words; figures",s.count("!["))


if __name__=="__main__":
    main()
