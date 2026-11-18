# Repository instructions for coding agents

## Purpose and audience

This is an independent, nonpartisan research and visual-storytelling project about Seattle's 2025 mayoral election. Write for both curious Seattle residents without technical training and technically sophisticated readers, including prospective employers. The public-facing work should tell a coherent story; methodological detail belongs in linked notes, source code, and appendices.

Before changing anything, read `README.md`, inspect the affected report or page, and identify the current source of truth. Do not assume that the earliest or most familiar report is the latest one.

## Publication surfaces

- `README.md` currently leads with the newer precinct field guide: `reports/seattle_precinct_by_precinct.md`.
- `reports/seattle_through_the_numbers.md` is the earlier eight-experiment essay; it remains a distinct research artifact.
- `index.html` is the static GitHub Pages article. Its contents and publication links may not automatically match the README's preferred report.
- `scripts/render_site.py`, `scripts/render_eight_experiments_report.py`, and the relevant analysis scripts generate parts of the publication. Check generators before editing generated output.
- `.github/workflows/` contains build and deployment workflows. The Pages deployment is configured for manual dispatch; do not imply that a commit necessarily updates the live site.

When changing the landing page, report navigation, or a “read the report” link, verify the destination against the current README and the user's explicit publishing intent. Do not silently redirect readers from the latest field guide to the older eight-experiment essay, or vice versa. If the intended flagship is ambiguous, ask.

## Editorial standards

- Lead with a specific, defensible finding and why it matters. Prefer short paragraphs and direct sentences.
- Avoid generic AI prose, inflated claims, repetitive summaries, and ceremonial transitions. Edit for a natural human research voice.
- Explain methods in one plain-English sentence near each finding; move detailed assumptions and diagnostics to supporting material.
- Distinguish observations, model outputs, counterfactual exercises, and speculation. Clearly label retrospective analyses; do not call them forecasts.
- Avoid ecological fallacies: precinct patterns do not establish individual voter behavior, motivation, or causation.
- Maintain a nonpartisan analytical tone. Treat unusual or politically interesting patterns as hypotheses to investigate, not proof of misconduct or individual intent.
- Do not invent citations, figures, vote totals, geographic labels, or methodological assurances.

## Maps and graphics

- Every chart should communicate one principal point, with legible titles, units, captions, sources, and useful context.
- Prefer interpretable linear scales where practical. If a logarithmic scale is essential, explain it prominently.
- Check visual balance: title and footer centering, labels, map extents, spacing, and legend duplication.
- Prevent overlapping neighborhood labels (for example, Beacon Hill and Columbia City); do not imply that orientation labels or community-reporting-area outlines are official precinct or neighborhood boundaries.
- Make legends consistent with the actual encoding. Avoid redundant legends and misleading color semantics.
- Inspect SVG/PNG output at desktop and mobile sizes, including the rendered page, rather than relying on code review alone. Check alt text and color contrast.

## Analysis and reproducibility

- Prefer the project's documented official election and geographic inputs; preserve provenance and explain joins, crosswalks, denominators, geographic coverage, exclusions, and units.
- Treat `data/processed/` and `reports/figures/` as reproducible outputs where applicable. Update source scripts first; regenerate dependent artifacts when feasible.
- Preserve the distinction between the 1,019 precincts referenced by the newer field guide and the 1,006 precincts used in core spatial analyses; do not assume they describe identical analysis populations.
- For spatial comparisons, confirm that boundaries, years, and geographic units are comparable. State the limits of ecological and cross-year inference.
- Use fixed random seeds when simulations are involved; document sensitivity to assumptions and multiple comparisons.
- Do not commit credentials, private personal information, or large new raw datasets without checking licensing and necessity.

## Change workflow

1. Identify the user's requested outcome, affected source files, generated outputs, and relevant tests.
2. Make the smallest coherent change; avoid unrelated rewriting or broad refactors.
3. Run targeted tests, then `python -m unittest discover -s tests` when dependencies and runtime permit. Install from the appropriate `requirements-*.txt` file rather than assuming a single dependency set.
4. If changing analyses or report generation, run the corresponding scripts or GitHub Actions workflow and verify expected outputs. Do not claim regeneration or test success unless it actually occurred.
5. For website or figure changes, inspect the rendered result and test internal paths, figure links, report links, and mobile layout.
6. Summarize what changed, why, what was verified, and what remains unverified. Clearly distinguish committed source changes from deployed live-site changes.
7. Prefer a pull request for review before merging publication-facing changes. Never silently force-push, delete research outputs, or alter public claims.

## Useful entry points

- Overview and current report links: `README.md`
- Newer field guide: `reports/seattle_precinct_by_precinct.md`
- Earlier eight experiments: `reports/seattle_through_the_numbers.md`
- Plain-English methods: `docs/methodology/techniques_explained.md`
- Field-guide analysis: `scripts/precinct_field_guide.py` and `scripts/precinct_field_guide_extensions.py`
- Tests: `tests/`
- Build and deployment configuration: `.github/workflows/`
