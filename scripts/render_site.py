"""Render the public, reader-first GitHub Pages article from verified outputs."""
from pathlib import Path
from render_eight_experiments_report import load_metrics

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "index.html"

def main():
    data = load_metrics()
    e3 = data["prediction_intervals"]
    e4 = data["twin_simulation"]
    e5 = data["funding"]
    e6 = data["ecological"]
    e7 = data["electoral_communities"]
    e8 = data["boundary_robustness"]

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Seattle, Through the Numbers — 2025 Mayoral Election</title>
<meta name="description" content="Eight computational experiments on Seattle's 2025 election, from precinct geography and turnout to campaign finance and algorithmic political regions.">
<style>
:root {{
  --ink:#16303f; --muted:#5d6f79; --paper:#f7f5f1; --card:#ffffff;
  --blue:#367d9e; --orange:#c77945; --line:#d9dedf; --soft:#ece8e0;
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{
  margin:0; color:var(--ink); background:var(--paper);
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height:1.62;
}}
a {{ color:#1d647f; }}
.wrap {{ width:min(1120px, calc(100% - 36px)); margin:0 auto; }}
header {{ padding:72px 0 24px; }}
.eyebrow {{ text-transform:uppercase; letter-spacing:.11em; font-size:.78rem; font-weight:750; color:var(--muted); }}
h1 {{ font-family: Georgia, "Times New Roman", serif; font-size:clamp(3rem, 7vw, 6.4rem); line-height:.96; letter-spacing:-.045em; margin:.12em 0 .18em; font-weight:600; }}
.dek {{ font-family: Georgia, "Times New Roman", serif; font-size:clamp(1.3rem,2.2vw,2rem); color:#314b59; max-width:820px; margin:0; }}
.intro {{ max-width:790px; font-size:1.08rem; margin-top:28px; }}
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:1px; background:var(--line); border:1px solid var(--line); margin:38px 0; }}
.stat {{ background:var(--card); padding:20px; }}
.stat b {{ display:block; font-family:Georgia,serif; font-size:2rem; font-weight:600; line-height:1; }}
.stat span {{ display:block; color:var(--muted); margin-top:7px; font-size:.88rem; }}
.hero-figure, .figure {{ background:var(--card); border:1px solid var(--line); padding:18px; margin:30px 0 16px; }}
.hero-figure img, .figure img {{ display:block; width:100%; height:auto; }}
.caption {{ color:var(--muted); font-size:.88rem; margin:9px 2px 0; }}
.reading-guide {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin:42px 0 12px; }}
.note {{ border-top:3px solid var(--ink); padding:14px 2px; }}
.note b {{ display:block; margin-bottom:5px; }}
nav {{ position:sticky; top:0; z-index:5; background:rgba(247,245,241,.95); border-top:1px solid var(--line); border-bottom:1px solid var(--line); backdrop-filter:blur(8px); }}
nav .wrap {{ display:flex; gap:22px; overflow:auto; padding:11px 0; white-space:nowrap; font-size:.88rem; }}
nav a {{ text-decoration:none; color:var(--muted); font-weight:650; }}
section {{ padding:70px 0 14px; }}
.section-kicker {{ font-size:.8rem; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); font-weight:750; }}
h2 {{ font-family:Georgia,serif; font-size:clamp(2.15rem,4vw,3.7rem); letter-spacing:-.025em; line-height:1.04; margin:.12em 0 .25em; font-weight:600; }}
.experiment {{ display:grid; grid-template-columns:minmax(0,1.05fr) minmax(330px,.95fr); gap:40px; align-items:start; padding:42px 0 56px; border-bottom:1px solid var(--line); }}
.experiment:nth-child(even) .copy {{ order:2; }}
.experiment:nth-child(even) .figure {{ order:1; }}
.num {{ font-size:.78rem; letter-spacing:.12em; color:var(--muted); font-weight:800; }}
h3 {{ font-family:Georgia,serif; font-size:clamp(1.65rem,2.6vw,2.45rem); line-height:1.12; margin:.25em 0 .45em; font-weight:600; }}
.copy p {{ margin:0 0 1em; }}
.method {{ color:#405965; }}
.takeaways {{ background:#173342; color:#f8f6f0; margin-top:70px; padding:58px 0; }}
.takeaways h2 {{ color:white; }}
.takeaways ul {{ max-width:850px; font-size:1.08rem; }}
footer {{ padding:56px 0 80px; color:var(--muted); font-size:.92rem; }}
.links {{ display:flex; gap:14px; flex-wrap:wrap; margin-top:20px; }}
.button {{ display:inline-block; border:1px solid #9ba7ac; border-radius:999px; padding:8px 14px; text-decoration:none; color:var(--ink); background:white; }}
@media (max-width:820px) {{
  header {{ padding-top:46px; }}
  .stats {{ grid-template-columns:repeat(2,1fr); }}
  .reading-guide {{ grid-template-columns:1fr; gap:8px; }}
  .experiment, .experiment:nth-child(even) {{ grid-template-columns:1fr; gap:12px; }}
  .experiment:nth-child(even) .copy, .experiment:nth-child(even) .figure {{ order:initial; }}
  section {{ padding-top:50px; }}
}}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <div class="eyebrow">Seattle election research · November 2026 · Sho Tsubakiyama</div>
    <h1>Seattle,<br>Through the Numbers</h1>
    <p class="dek">Eight computational experiments on the 2025 election.</p>
    <p class="intro">Katie Wilson defeated Bruce Harrell by just <strong>2,011 votes</strong>. The close finish is the obvious story. This project asks what the precinct returns can tell us beyond it: where the city divided, where participation mattered, what looked predictable, what only looked surprising, and what happens when an algorithm redraws Seattle without being told its neighborhood names.</p>
    <div class="stats">
      <div class="stat"><b>2,011</b><span>votes in the citywide margin</span></div>
      <div class="stat"><b>1,006</b><span>precincts in the core spatial analyses</span></div>
      <div class="stat"><b>8</b><span>experiments, each centered on one figure</span></div>
      <div class="stat"><b>{e7['communities']}</b><span>algorithmic electoral regions in the baseline map</span></div>
    </div>
    <div class="hero-figure">
      <img src="reports/figures/seattle_2025_mayor_precinct_map.svg" alt="Seattle 2025 mayoral vote share by precinct with community reporting area outlines and neighborhood labels">
      <p class="caption">Wilson share of the vote between the two mayoral finalists. Thin outlines show community-reporting areas; labels are geographic anchors, not election units or official neighborhood boundaries.</p>
    </div>
    <div class="reading-guide">
      <div class="note"><b>The city was close, but not uniform.</b> A 50–50 citywide result can hide large differences from one precinct to the next.</div>
      <div class="note"><b>The mayoral map is not the whole political map.</b> Harrell-winning precincts still backed several other citywide winners by clear margins.</div>
      <div class="note"><b>Precincts describe places, not people.</b> Aggregate returns cannot identify individual split-ticket voters or explain why a neighborhood changed.</div>
    </div>
  </div>
</header>

<nav><div class="wrap">
  <a href="#election">The election</a>
  <a href="#statistics">Statistics</a>
  <a href="#money">Money & inference</a>
  <a href="#redrawn">Seattle redrawn</a>
  <a href="#methods">Methods</a>
</div></nav>

<main>
<section id="election"><div class="wrap">
  <div class="section-kicker">I · The election we actually held</div>
  <h2>A close race contained several different coalitions.</h2>

  <article class="experiment">
    <div class="copy">
      <div class="num">01</div>
      <h3>Harrell precincts were not a separate political city.</h3>
      <p>Even where Harrell won the mayoral vote, Erika Evans received <strong>57%</strong> of the city-attorney vote between the finalists, Alexis Mercedes Rinck received <strong>76.9%</strong> for Council Position 8, and both city propositions won majorities.</p>
      <p class="method"><strong>How it works.</strong> Group precincts by their mayoral winner, then compare support in the same precinct groups across six citywide contests. This says something about places, not whether the same individuals split their tickets.</p>
    </div>
    <div class="figure"><img src="reports/figures/experiment_01_citywide_coalitions.svg" alt="Support for Seattle citywide winners in Harrell and Wilson mayoral precincts"></div>
  </article>

  <article class="experiment">
    <div class="copy">
      <div class="num">02</div>
      <h3>Equal precinct participation would raise Wilson's share by 1.33 points.</h3>
      <p>Wilson won <strong>50.36%</strong> of the finalist vote. Holding each precinct's candidate preference fixed but giving precincts equal finalist participation per registered voter raises her calculated share to <strong>51.69%</strong>, a <strong>1.33-point</strong> difference.</p>
      <p class="method"><strong>How it works.</strong> This is a standardization exercise, not a forecast of how nonvoters would have voted. It isolates the arithmetic of where participation was concentrated.</p>
    </div>
    <div class="figure"><img src="reports/figures/experiment_02_equal_participation.svg" alt="Actual Wilson vote share compared with equal precinct participation"></div>
  </article>
</div></section>

<section id="statistics"><div class="wrap">
  <div class="section-kicker">II · What statistics can reveal</div>
  <h2>The dramatic-looking result is not always the unusual one.</h2>

  <article class="experiment">
    <div class="copy">
      <div class="num">03</div>
      <h3>Prediction is more useful when it shows how wrong it can be.</h3>
      <p>The geographic holdout experiment targeted 90% coverage and contained <strong>{e3['coverage']:.1f}%</strong> of held-out precinct results. The typical interval was still <strong>{e3['avg_interval_width_pp']:.1f} points wide</strong>.</p>
      <p class="method"><strong>How it works.</strong> A Ridge model learns from August voting and broad Census variables, while entire geographic groups are held out for calibration and testing. This is a retrospective model check, not a pre-election forecast.</p>
    </div>
    <div class="figure"><img src="reports/figures/experiment_03_prediction_ranges.svg" alt="Predicted Harrell vote shares with uncertainty intervals and actual results"></div>
  </article>

  <article class="experiment">
    <div class="copy">
      <div class="num">04</div>
      <h3>Once you search thousands of twins, a spectacular split becomes less spectacular.</h3>
      <p>There were <strong>{e4['candidate_pairs']:,}</strong> geographically separated precinct pairs that passed the pre-November similarity test. The largest real November gap was <strong>{e4['observed_max_gap_pp']:.1f} points</strong>. In the simulations, the largest gap was often around <strong>{e4['binomial_median_max_pp']:.1f}–{e4['shuffled_errors_median_max_pp']:.1f} points</strong>.</p>
      <p class="method"><strong>Why that matters.</strong> The eye naturally fixates on the most extreme pair after the fact. Repeating the same search in simulated data shows that an eye-catching maximum can arise simply because we looked at many plausible pairs.</p>
    </div>
    <div class="figure"><img src="reports/figures/experiment_04_twin_simulation.svg" alt="Simulated maximum differences among matched precinct pairs"></div>
  </article>
</div></section>

<section id="money"><div class="wrap">
  <div class="section-kicker">III · Money and what aggregate returns hide</div>
  <h2>Some political differences are visible. Others are not identifiable from precinct totals.</h2>

  <article class="experiment">
    <div class="copy">
      <div class="num">05</div>
      <h3>Wilson and Harrell financed their campaigns in very different ways.</h3>
      <p>Democracy Vouchers represented about <strong>{e5['Katie Wilson']['voucher_percent']:.0f}%</strong> of Wilson's reported direct campaign funding, compared with <strong>{e5['Bruce Harrell']['voucher_percent']:.0f}%</strong> for Harrell. Harrell reported much more other cash and in-kind support.</p>
      <p class="method"><strong>Scope.</strong> These are direct campaign committee records. Independent expenditures and donor geography are intentionally outside this comparison.</p>
    </div>
    <div class="figure"><img src="reports/figures/experiment_05_funding_sources.svg" alt="Direct campaign funding composition for Katie Wilson and Bruce Harrell"></div>
  </article>

  <article class="experiment">
    <div class="copy">
      <div class="num">06</div>
      <h3>Precinct totals cannot tell us who split their ticket.</h3>
      <p>If 60 of 100 voters chose Wilson and 70 chose Evans, anywhere from <strong>{e6['possible_overlap_min_pct']} to {e6['possible_overlap_max_pct']}</strong> could have chosen both. Identical aggregate totals can come from very different individual voting patterns.</p>
      <p class="method"><strong>The limitation.</strong> This is the ecological inference problem. Precinct-level data can reveal geographic relationships, but it cannot reconstruct individual ballots without additional assumptions or data.</p>
    </div>
    <div class="figure"><img src="reports/figures/experiment_06_hidden_ballots.svg" alt="Two hypothetical individual voting patterns with the same aggregate totals"></div>
  </article>
</div></section>

<section id="redrawn"><div class="wrap">
  <div class="section-kicker">IV · Seattle, redrawn</div>
  <h2>What if the election itself were allowed to draw the neighborhoods?</h2>

  <article class="experiment">
    <div class="copy">
      <div class="num">07</div>
      <h3>The baseline specification finds {e7['communities']} electoral regions without knowing neighborhood names.</h3>
      <p>The model groups <strong>{e7['precincts']:,}</strong> precincts connected by <strong>{e7['edges']:,}</strong> substantial shared borders. Similarity comes from six 2025 citywide contests, not from labels such as Ballard, Queen Anne, Capitol Hill, or Ravenna.</p>
      <p class="method"><strong>How to read the map.</strong> The left side shows community-reporting areas. The right side shows the algorithmic clusters. Neighborhood labels appear on both only as geographic anchors; the colors are group IDs, not ideology.</p>
    </div>
    <div class="figure"><img src="reports/figures/experiment_07_algorithmic_seattle.svg" alt="Seattle community reporting areas compared with algorithmically generated electoral communities"></div>
  </article>

  <article class="experiment">
    <div class="copy">
      <div class="num">08</div>
      <h3>The most interesting boundaries are the ones that survive changes in the model.</h3>
      <p>Across five reasonable specifications, <strong>{e8['model_sensitive_pct']:.1f}%</strong> of shared precinct borders changed whether their two precincts belonged to the same community. Only <strong>{e8['stable_dividing_pct']:.1f}%</strong> were dividing borders every time.</p>
      <p class="method"><strong>The point.</strong> A polished cluster map can look more definitive than it is. Stability analysis exposes which boundaries are robust and which mostly reflect modeling choices.</p>
    </div>
    <div class="figure"><img src="reports/figures/experiment_08_boundary_stability.png" alt="Seattle precinct borders classified by stability across clustering specifications"></div>
  </article>
</div></section>

<section class="takeaways"><div class="wrap">
  <div class="section-kicker">What I would take away</div>
  <h2>The methods disagree in useful ways.</h2>
  <ul>
    <li><strong>Seattle's mayoral divide is real, but it is not a complete description of the city's politics.</strong> The coalition supporting other citywide winners crossed the mayoral boundary.</li>
    <li><strong>Participation geography mattered to the closeness of the result, but the data do not tell us why.</strong> Reweighting can show the arithmetic without pretending to recover nonvoters' preferences.</li>
    <li><strong>The computational tools are strongest when they reveal uncertainty and limits.</strong> Simulations make selected extremes less seductive; ecological inference blocks overclaiming; stability tests keep the cluster map honest.</li>
  </ul>
</div></section>
</main>

<footer id="methods"><div class="wrap">
  <div class="eyebrow">Methods & sources</div>
  <p>Official election returns come from King County. Precinct geometry uses 2025 voting-district shapes; demographic context uses geographically allocated 2020 Census data; campaign finance uses Seattle Ethics & Elections Commission records. The analysis is independent, nonpartisan, and exploratory.</p>
  <p>Precinct-level comparisons describe places, not individual voters, and do not establish why a neighborhood voted as it did.</p>
  <div class="links">
    <a class="button" href="https://github.com/shotsubakiyama/seattle-mayoral-election-2025">Source & reproducibility</a>
    <a class="button" href="https://github.com/shotsubakiyama/seattle-mayoral-election-2025/blob/main/reports/seattle_through_the_numbers.md">Full research report</a>
    <a class="button" href="https://github.com/shotsubakiyama/seattle-mayoral-election-2025/blob/main/docs/methodology/techniques_explained.md">Methods guide</a>
  </div>
</div></footer>
</body>
</html>
"""
    DEST.write_text(html, encoding="utf-8")
    print("Rendered public article:", DEST)

if __name__ == "__main__":
    main()
