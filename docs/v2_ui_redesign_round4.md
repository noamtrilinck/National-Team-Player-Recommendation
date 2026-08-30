# UI/UX Redesign Round 4 (2026-08-30): football-meaning explanations + heatmap fix + comparison-filter fix

**Scope: presentation/explanation-selection layer + 2 real display/data-path bugs. Locked V2/F50
scoring (Final Score, Global Rank, registry, Style/Emphasis definitions, weights) is unchanged --
confirmed by `git status` showing zero scoring/data files touched this round (only `src/charts.py`,
`src/charts_v2.py`, `src/explanation_engine_v2.py`, `views/recommendations.py` changed).**

## Bug 1: comparison heatmap showed Emphasis-specific scores, not base Style scores

**Root cause, traced through the actual data path** (raw scoring output -> Style score ->
Emphasis-specific score -> search result -> comparison dataframe -> heatmap): `charts_v2.
profile_comparison_figure()` scoped each cell to `player_combos[player_combos["style"] == style]`
-- ALL combos for that Style, across every Emphasis -- then picked `.final_score.idxmax()`, i.e.
the player's BEST-SCORING EMPHASIS for that Style, not the Style itself. Verified directly against
`f50_scores.csv` for the reported case (Yair Mordechai, Winger): the heatmap's "Direct" cell showed
87.6 (his `Direct + Goal Threat` combo, rank #65) instead of 78.7 (his real `Direct` / Generic
combo, rank #102) -- an 8.9-point, 37-rank misrepresentation.

**Fix**: `profile_comparison_figure()` now filters to `emphasis == "(none)"` (the Generic combo)
before building each column -- the single real, existing, locked registry row for "this Style with
no Emphasis applied". The function never took an Emphasis argument to begin with, so it is
structurally invariant to whatever Emphasis is selected in the search controls (verified: `Emphasis`
does not appear in its signature). Caption text updated from "each shown at their own single
strongest Role Emphasis per Style" to "each shown at their base Style score (no Role Emphasis
applied)" to match. Regression tests: `tests/test_round4_relevance_and_fixes.py::
test_heatmap_uses_generic_combo_never_best_emphasis`,
`test_heatmap_invariant_to_currently_selected_emphasis`, `test_heatmap_generic_combo_is_unique_per_style`.

## Bug 2: players silently disappearing under Top/Bottom Opponents comparison filters

**Investigated, not assumed.** Reproduced the Israeli Left Winger case directly against
`match_level_stats.parquet`: of 11 Israeli Left Wingers, **Liran Rotman** has zero rows for
`filter_key == "top_opponents"` (and none for `"home"` either) and **Yonatan Cohen** has zero rows
for `filter_key == "bottom_opponents"` -- two players, two different filter_keys, two unrelated
gaps (each genuinely never faced a "Top"/"Bottom"-bracket opponent that season under the project's
existing, already-validated Peer Filter classification -- not a shared defect). Checked and ruled
out, in order: NaN/missing values (confirmed -- this IS the actual mechanism, but only for those 2
specific player/filter combinations, not a population-wide pattern), independent per-chart
filtering (confirmed correct and INTENDED -- a Top-Opponents chart should only plot Top-Opponents
data), Top/Bottom applied before population freezing (ruled out -- the underlying `df`/`chart_df`
population is never filtered by `filter_key`, only the per-chart plotted points are), ties (ruled
out, unrelated), eligibility/position/merge/index mismatch (ruled out -- `_metric_lookup`'s merge
keys and the source population match exactly), Streamlit state/cache (ruled out -- `st.cache_data`
scoping is unaffected by which filter is selected).

**Actual root cause**: `charts._player_points()` (and its scatter/bubble siblings) already,
by design, drop a player from ONE chart's plotted points when real match data for the selected
filter/metric is genuinely missing (documented since round 1 -- correct behaviour, avoids plotting
a false zero). The gap was that this was **silent** -- no on-screen indication of who was dropped
or why, so a real, football-explicable data gap read as an unexplained bug.

**Fix, implemented generically** (not special-cased to Israeli/Left-Wingers/any position): new
`charts.missing_data_players(chart_rows, mstats, metrics, filter_key, value_col)` identifies
exactly which of the chart's intended players lack real data for ALL of the chart's required
metric(s) under the selected filter -- one metric for a range chart, two for scatter, three for
bubble. `views/recommendations.py` now renders an explicit caption under every chart ("Not shown
for **Top Opponents**: Liran Rotman -- no match data available under this filter.") whenever this
happens, for both the automatic Standout-metrics batches and the Custom Chart Builder. The
underlying search-result population (`df`/`chart_df`) is never touched -- verified directly
(`test_original_population_untouched_by_a_missing_data_player`) -- satisfying the explicit
requirement that Top/Bottom only changes which players are HIGHLIGHTED for one chart, never the
source comparison population. Live-app confirmation via AppTest: switching the Standout-metrics
match filter to Bottom Opponents for the real Israeli Left Winger search produced the new
"Not shown for" note; switching back to Full Season cleared it.

## Explanation engine: football meaning, relevance-over-extremeness, global/league storytelling

- **Football implication over stat description** (points 1, 4): new `FOOTBALL_MEANING` dict
  translates each of the 13 locked Signal domains into what it means on the pitch, split by
  info_type where a domain has BOTH a VOLUME signal (how OFTEN/how MUCH) and an EXECUTION signal
  (how WELL/how EFFICIENTLY) -- these are genuinely different facts, not synonyms, and this is
  also the direct fix for the "Volume over-prioritised" concern (point 4): a Signal's own
  info_type decides which implication fires, and `_interestingness()` now gives EXECUTION signals
  a small, disclosed +6 bonus so an efficiency/success-rate fact competes on a more even footing
  against a bigger-looking raw count. **Causality guard, tested**: implication sentences are used
  ONLY for strengths -- reusing a positive capability phrase for a weakness would assert the
  OPPOSITE of what the data shows (caught and fixed during this round's own testing: an early
  version rendered "Reads the game well... [evidence: below league average]" for a genuine
  weakness). Weaknesses stay evidence-only, as before.
- **Global population as a first-class story input** (point 2): `_comparison_informativeness()`
  scores both league-rank and global-percentile extremeness (0-1 each) and `_comparison_clause()`
  leads with whichever is genuinely more informative -- or cites both when they're comparably
  strong -- rather than defaulting to league rank. Tested directly
  (`test_comparison_clause_prefers_global_when_more_informative` /
  `..._prefers_league_when_more_informative`).
- **Relevance beats extremeness** (point 3, already partially established in round 3's tier
  selection, extended here): `select()`'s sort key remains `(tier, -interestingness)` -- profile
  relevance dominates first, interestingness only orders WITHIN a tier. The strength floor stays
  at the 60th global percentile (not a league-rank-extremeness gate), so a genuinely relevant
  60-85th-percentile Tier-1/2 fact is eligible on equal footing with any Tier-5 fact regardless of
  how extreme the latter is (point 5) -- proven directly against real fixtures in
  `test_relevant_moderate_signal_beats_irrelevant_extreme_signal` and reflected in the 12-player
  sample below (e.g. Trincão's 71st-percentile shot volume, Camara's 64th-percentile pass
  completion, Manning's 66th-percentile interceptions all surfaced ahead of more extreme but less
  relevant alternatives).
- **Combining evidence into one story** (point 6): `_combine_top_strengths()` merges the two
  most-relevant selected strengths into a single connected bullet when their redundancy groups
  form a real, disclosed football pairing (`COMBINE_CONNECTORS`: dribbling+shooting,
  progression+creativity, ball_winning+duels, creativity+dribbling) -- e.g. Prestianni: "...He
  carries the ball into danger himself as well as creating it with his passing -- regularly finds
  teammates in positions to finish attacks." Only fires on facts ALREADY independently selected as
  real evidence; never invents a connection outside the disclosed pairs
  (`test_combination_only_fires_on_real_disclosed_group_pairs`).
- **Sentence variety tied to real data, not decoration** (point 7): `_frame()` picks the closing
  clause from the fact's actual tier/story (`profile_driver`/`combination`/`identity`/
  `supporting_trait`), with the dominant `supporting_trait` case further varied by the fact's own
  redundancy group (7 distinct phrasings) rather than one fixed sentence repeating across a
  player's whole profile. A 20-case audit across 12 positions/Styles/Emphases before this fix
  showed one supporting-trait phrase repeating verbatim 15/62 times; after the group-aware
  variants, the same closing clause never repeats identically across unrelated groups within one
  explanation.

## Validation

**12-player football sanity sample** (multiple positions/leagues/Styles/Emphases, high-scoring
and moderate profiles, extreme AND non-extreme selected evidence -- full transcript kept in the
session record): confirms Tier-1/2 evidence consistently leads even at moderate percentiles
(Camara's 64th-pctile pass completion, Trincão's 71st-pctile shot volume), the combination pass
fires on real pairs (Manning, Johnston, Camara, Trincão), weaknesses stay evidence-only, and
global-vs-league framing genuinely varies fact-to-fact based on which population is more
informative for that specific number.

**Playwright (real browser)**: base page load with zero console/page errors, confirmed. Repeated
BaseWeb-combobox automation attempts for the full click-through search flow hit the same
documented timing flakiness as rounds 1-3 (a `role="combobox"`/`role="option"` click occasionally
times out) -- not a new issue, not an application defect. Cross-verified deterministically via
Streamlit's own `AppTest` harness driving the real `recommendations.py` page code end-to-end:
Israeli Left Winger search renders results; the heatmap caption confirms the base-Style-score
framing; switching a Standout-metrics chart's match filter to Bottom Opponents produced the new
explicit "Not shown for Bottom Opponents: Yonatan Cohen -- no match data available under this
filter" note against the real data, and switching back to Full Season cleared it; a Style switch
(Direct -> Control) with the panel already expanded produced genuinely different explanation
content -- no stale state, matching round 3's established no-stale-state guarantee under the
rewritten engine.

**Regression**: `git status` on the dashboard repo shows only `src/charts.py`, `src/charts_v2.py`,
`src/explanation_engine_v2.py`, and `views/recommendations.py` changed this round -- `f50_scores.
csv`, `f50_registry.csv`, `players.csv`, and `signal_scores.parquet` are byte-identical to the last
locked commit, so Final Score / Global Rank / registry are unchanged by construction.

**Tests**: `tests/test_round4_relevance_and_fixes.py` (new, 16 tests) covers the heatmap fix
(3 tests), missing-data handling (4 tests), relevance-over-extremeness (2 tests), the causality
guard (2 tests), global-vs-league comparison selection (2 tests), the Volume/Execution balance
nudge (1 test), the combination pass (1 test), and a broad smoke test across 11 profiles (1 test).
Full suite: **83/83 passing** (67 existing + 16 new), including deployment-isolation static checks
(no `production/` imports introduced this round).
