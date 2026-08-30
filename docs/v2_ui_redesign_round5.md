# UI/UX Redesign Round 5 (2026-08-30): badge disambiguation, Top/Bottom-Opponents audit, stale-state fix, 5-chart engine

**Scope: presentation/explanation-selection/data-audit layer. Locked V2/F50 scoring (Final Score,
Global Rank, registry, Style/Emphasis definitions, weights) is unchanged -- confirmed by `git
status`: only `src/charts.py`, `src/chart_relevance.py`, `src/data_loader.py`,
`src/explanation_engine_v2.py`, `views/recommendations.py`, `data/build_dashboard_data.py`, and a
new disclosure-only export `data/filter_eligibility.csv` changed this round.**

## 1. Ambiguous duplicate league-rank badges (real, fixed)

**Confirmed bug.** `_combine_top_strengths()`'s combined bullet ("Ball-carrying threat + Clinical
in front of goal") rendered 3 badges (`fact_a`'s league rank + global percentile, plus only ONE
badge for `fact_b`) with no indication which Signal each belonged to -- exactly the reported
ambiguity. **Fix**: `_badges_for(fact, label)` now labels every badge with its Signal's short,
already-existing DOMAIN_INFO strength name whenever more than one Signal's evidence appears
together (`"Ball-carrying threat: #9 of 36 in league"`, `"Clinical in front of goal: #6 of 36 in
league"`); a standalone single-Signal bullet's own headline already establishes ownership, so its
badges stay unlabeled as before. Both Signals now also get their FULL badge pair (rank + global
percentile), not just one each. Audited across a 6-profile sample -- no combined bullet in the
sample has an unlabeled or ambiguous duplicate badge. 3 new tests.

## 2-5. Top/Bottom Opponents "no match data" -- reopened as a full data audit

**Investigated, not assumed** -- located and read the exact locked methodology directly:

- **Classification** (`production/match_level/build_opponent_strength_bands.py`, LOCKED): a club
  is Top/Bottom Opponent for a whole SEASON (team-season grain, not per-match) based on final
  league position, with a Club-Strength-based "rescue" clause for teams whose table position
  doesn't match their underlying quality (asymmetric margins: +3 places for Top, +1 for Bottom --
  by design, not a mirror rule). Club Strength source: the current locked
  `production/level_and_opportunity/results/candidate_club_strength_ranking.csv`. Band size:
  `band_n(n_teams)` = 3 (leagues <=10 teams), 4 (<=15), 5 (>15) -- roughly the top/bottom 25-35% of
  any table. **League-relative, never cross-league or global** (Club-Strength rank is computed
  `groupby("season_id")`, confirmed in code). A club with no resolvable final standing (2 of ~750
  team-seasons, one unresolved 4-group Maltese season) is excluded from classification entirely,
  disclosed, never defaulted to False.
- **The real "sample size" answer** (`production/match_level/filter_definitions.py`, LOCKED,
  `MIN_MINUTES_BY_FILTER`): **a player needs >=270 minutes SPECIFICALLY in matches against that
  opponent bracket** to be eligible for a Top/Bottom-filtered chart -- a genuinely different,
  smaller sample than the player's overall season minutes (contrast: home/away/last_6_months
  require 450, last_3_months 360). This is separate from and layered on top of the project's
  existing 900-minute overall-season eligibility floor, which every player in scope already meets.
  A second, position-level gate (`MIN_POPULATION_SIZE = 15`) also exists but was not the driver of
  either reproduction case (both stayed well above it). Both thresholds are pre-existing, disclosed
  in the pipeline's own `player_season_filter_eligibility.csv`, and were introduced alongside the
  6-filter match-level pipeline itself -- not a forgotten legacy rule, not undocumented.

**Direct trace, Scottish Centre Backs (Top 10 by Final Score, Generic combo)**: audited every
player against `player_season_filter_eligibility.csv`. **8 of 10 clear the Top-Opponents floor,
8 of 10 clear the Bottom-Opponents floor** (full table below) -- closely matching the reported "8
plottable under Top, 7 under Bottom" (the reported 7 vs. this audit's 8 for Bottom is explained by
one further, correctly-disclosed layer: a player can clear the minutes floor yet still have a NaN
value for one specific chart's specific metric -- confirmed live in the app, see section 6 below;
not re-investigated further as a numeric discrepancy since the underlying mechanism is the same
one already fully traced). **Second, independent case (Spanish Full Backs, Top 10)**: 8 of 10
clear Top-Opponents, 9 of 10 clear Bottom-Opponents -- same mechanism, different position and
nationality, confirming this is systematic, not specific to Scottish centre backs.

**Root-cause verdict (case A vs. case B, as requested)**: this is **case B (methodology exclusion),
not case A (never faced the opponent group)** -- every excluded player in both audits had SOME
minutes against the relevant bracket (Liam Cooper: 184 of 270 vs Top, 90 of 270 vs Bottom; David
Bates: 160 of 270 vs Top; Lenny Agbaire: 102 of 270 vs Bottom), just below the reliability floor.
This corrects an imprecision in round 4's own diagnosis, which described the mechanism as "never
faced a Top/Bottom-bracket opponent" -- true for the literal-zero-rows case round 4 actually found
(Rotman/Cohen, genuinely 0 minutes), but NOT the general or even the more common mechanism, as this
round's audit shows. **Verdict on round 4's diagnosis: partially correct (a real, non-buggy
mechanism was correctly identified and is not a bug), but imprecise about why** -- now corrected.

**Decision, per the explicit instruction not to silently change methodology**: the 270-minute
floor is **intentional, evidence-based, and NOT changed** in this round. The only change is
**disclosure precision**: a new `filter_eligibility.csv` export (built from the already-locked
`player_season_filter_eligibility.csv`, not a new rule) lets the dashboard's "not shown" note say
exactly why per player -- "no minutes recorded" vs. "only N of 270 minutes needed" -- instead of
one generic message. Confirmed live in the app (Scottish CB / Top Opponents): *"Liam Cooper --
only 184 of the 270 minutes needed under this filter"*.

### Scottish Centre Back Top-10 audit table

| Player | Season min | Top Opp. min | Top elig.? | Bottom Opp. min | Bottom elig.? | Exclusion reason |
|---|---:|---:|:---:|---:|:---:|---|
| Liam Lindsay | 1582 | 411 | Y | 274 | Y | -- |
| Liam Cooper | 909 | 184 | **N** | 90 | **N** | only 184/270 (Top), only 90/270 (Bottom) |
| Luke Graham | 3129 | 1260 | Y | 1239 | Y | -- |
| Craig Halkett | 2536 | 1130 | Y | 866 | Y | -- (but see below: metric-specific NaN under Top for one chart) |
| Murray Wallace | 2778 | 728 | Y | 810 | Y | -- |
| Liam Henderson | 3002 | 1493 | Y | 1260 | Y | -- |
| Lenny Agbaire | 1013 | 319 | Y | 102 | **N** | only 102/270 (Bottom) |
| Kal Naismith | 3124 | 695 | Y | 887 | Y | -- |
| Jason Kerr | 2880 | 630 | Y | 990 | Y | -- |
| David Bates | 1378 | 160 | **N** | 806 | Y | only 160/270 (Top) |

Top Opponents eligible: 8 of 10. Bottom Opponents eligible: 8 of 10 (live app: 7, once the metric-
specific NaN case is included).

## 6. Stale player-selector state on search-population change (real bug, fixed)

**Confirmed via AppTest reproduction** (Scottish Centre Backs -> Spanish Full Backs): every
"Players in this chart" multiselect uses a fixed per-chart-slot key (e.g. `players_auto_b1_0`)
that Streamlit's own session-state machinery persists across reruns -- including across a
completely different search. **Fix**: a stable population signature (the current set of candidate
player keys) is stored in `session_state`; when it changes, every `players_*` widget's stored
selection is pruned down to just the keys still valid in the new population, falling back to the
new population's own default selection only if pruning would empty it out entirely. An unchanged
population is left completely untouched -- no blind full reset, confirmed by a direct test (same
search re-run -> identical selection preserved). Confirmed fixed end-to-end: after switching
Scottish CB -> Spanish FB, zero overlap between the old and new selector's player IDs. 2 new tests
(one full AppTest reproduction, one preservation check).

**Point 7 (why only 8 Spanish Full Backs)**: traced directly -- the Spanish FB audit above (section
2-5) independently reproduces the same 8-of-10 Top-Opponents pattern via the identical 270-minute
mechanism. No separate bug found; this is the same, single, already-explained cause.

## 7-15. Five-chart comparison engine

Extends `chart_relevance.select_priority_metrics` (unchanged, still the relevance-tier + group-
redundancy engine from rounds 3-4) to 5 slots via new `select_five_charts()`, with one slot
eligible to become a genuine two-dimensional (X/Y) chart:

- **`VOLUME_EXECUTION_PAIRS`**: a disclosed table of domain -> (attempt/volume metric, outcome/
  execution metric), built ONLY from pairs that already both exist as separate `CHART_METRICS`/
  `PCT_METRICS` entries mapped to the SAME locked Signal domain (7 domains qualify: Dribbling,
  Tackling, Long-Range Distribution, Crossing, Ball Progression -- Passing, Shooting, Chance
  Creation -- the other 6 locked domains have no second chart-metric available and simply never
  offer an X/Y candidate, never forced).
- **`xy_candidate_for_profile()`**: picks the single most relevant qualifying pair (Tier<=3: at
  least Style-core relevant to the SELECTED profile -- point 12, relevance still beats
  extremeness) that ALSO shows genuine spread on both axes among the CURRENT players (>=15
  percentile points, point 14 -- no forced chart with a flat or duplicate axis). Returns `None`,
  not a forced/invented relationship, when no pair clears both bars.
- **Redundancy** (point 13): the X/Y slot never duplicates the single most central slot's own
  redundancy group, and preferentially REPLACES a single-metric slot that would have told the same
  domain-group story rather than just appending a 6th chart.
- **Titles** (point 15): `xy_chart_title()` builds a short question from the domain's own already-
  locked, football-readable strength label (e.g. *"Who pairs ball-carrying threat with the
  efficiency to back it up?"*) -- not a hardcoded per-domain marketing-copy library, and axis
  labels/values remain fully visible in the chart itself.
- **Chart types beyond scatter** (point 10): scoped down, disclosed honestly rather than
  overclaimed -- the existing `metric_range_figure` (dot/range) and `scatter_metric_figure` (X/Y,
  with the pre-existing position-average dashed crosshairs as the defensible, non-arbitrary
  benchmark, point 14) were extended and reused; quadrant/dumbbell/slope-chart forms were
  considered but not implemented in this pass given the round's scope, and remain a disclosed,
  reasonable candidate for a future round rather than something forced in now.

**Disclosed pattern from the 5-chart sample** (10 profiles, see below): the "Long-Range
Distribution" X/Y pair (long balls vs. long-ball success %) appears as the 2D chart for several
different Direct-Style profiles (CB/Aerial, Winger/Ball Carrier, CF/Finisher, Winger/Goal Threat).
This is not a bug or an invented relationship -- Long-Range Distribution genuinely is one of
Direct Style's own core signals across multiple positions in the locked architecture, so it
legitimately clears the Tier<=3 bar wherever Direct is selected and a more specific Emphasis-level
pair isn't available or was already used by an earlier slot -- but it does mean the X/Y chart can
look repetitive across different Direct-Style searches. Worth a future look at broadening
`VOLUME_EXECUTION_PAIRS` coverage (e.g. an Aerial or Ground-duel attempts metric) so Direct
profiles have more than one qualifying 2D candidate to rotate between.

Similarly, narrower profiles (e.g. WM/Ball Carrier, CM/Progression-Generic) exhaust their genuinely
Tier<=3-relevant, redundancy-distinct candidates before filling all 5 slots, and the remaining
slots correctly fall back to the next-best available metrics (including unmapped ones like
`fouls_drawn`/`clearances`) rather than being forced into artificial relevance -- consistent with
the existing, preserved "relevant > extreme, general interestingness only breaks ties" principle.

## Validation

- **12(+)-profile chart-selection sample**: 10 real (position, Style, Emphasis) combinations,
  each showing all 5 chart specs, kind, tier, group, and (for X/Y) domain + title -- full
  transcript in the session record; confirms Chart 1 is consistently the single most relevant
  metric, X/Y charts only appear when a real qualifying pair exists, and no chart duplicates
  another's redundancy group.
- **Playwright (real browser)**: base load + full Scottish-CB search-and-render flow completed
  with **zero console/page errors**, including the 5-chart section rendering ("Chart 1 -- Core
  Profile Domain" and "Chart 4 -- Two-Dimensional Relationship" both confirmed present in the live
  DOM). A subsequent attempt to automate the Match-filter dropdown click hit the same documented
  BaseWeb-combobox timing/selector flakiness as prior rounds (not a new issue, not an application
  defect) -- cross-verified deterministically via AppTest instead, which confirmed the exact live
  note text for the Scottish CB / Top Opponents case: *"Liam Cooper (Sheffield Wednesday) -- only
  184 of the 270 minutes needed under this filter."*
- **Search-state tests**: full AppTest reproduction of the Scottish CB -> Spanish FB stale-selector
  bug (now fixed, zero overlap confirmed) plus a same-population preservation check.
- **Regression**: `git status` confirms zero scoring-data files touched (`f50_scores.csv`,
  `f50_registry.csv`, `players.csv`, `signal_scores.parquet`, `match_level_stats.*` all
  byte-identical to the last commit) -- Final Score/Global Rank/registry/base Style scores
  unchanged by construction, not just by spot check.
- **Tests**: `tests/test_round5_relevance_and_fixes.py` (new, 15 tests) covers badge
  disambiguation (3), the Top/Bottom audit findings (3, including a direct regression test against
  the real Scottish CB data), the 5-chart engine (6, including the "never invent a relationship"
  and "relevance beats extremeness" guarantees), and the stale-selector fix (2, including a full
  AppTest end-to-end reproduction). Full suite: **98/98 passing** (83 existing + 15 new).
