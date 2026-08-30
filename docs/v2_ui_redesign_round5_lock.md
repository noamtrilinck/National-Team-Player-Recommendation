# UI/UX Round 5 -- LOCKED implementation (2026-08-30)

**Implements the decisions approved after `v2_top_bottom_threshold_sensitivity_experiment.md`,
`v2_two_layer_reliability_architecture_design.md`, and
`v2_150min_and_signal_eligibility_decision.md`. Locked scoring (Final Score, Global Rank,
registry, Style/Emphasis/weights) is unchanged -- confirmed by `git status`: only
`data/build_dashboard_data_v2.py`, `data/filter_eligibility.csv`,
`data/signal_denominators.csv` (new), `src/chart_relevance.py`, `src/explanation_engine_v2.py`,
and `views/recommendations.py` changed in the dashboard repo; `f50_scores.csv`, `f50_registry.
csv`, `players.csv`, and `signal_scores.parquet` are all byte-identical to before this round.**

## 1. LOCKED -- 150-minute Top/Bottom floor

`production/match_level/filter_definitions.py`'s `MIN_MINUTES_BY_FILTER["top_opponents"/
"bottom_opponents"]` changed from 270 to **150**, re-ran `build_filtered_eligibility.py`
(Stage 4) to regenerate `player_season_filter_eligibility.csv`, then regenerated the dashboard's
own `data/filter_eligibility.csv` export unchanged in mechanism from round 5. Evidence: +6.6pp
Top / +8.1pp Bottom coverage vs. 270, within ~1pp of 180's diminishing-returns point, no
position-level collapse (every position >=91.7% displayable), Scottish CB Top 10 recovers to
10/10 under Top Opponents (from 8/10). Does not touch any scoring output -- confirmed both by the
pipeline's own scope (analytical filters only, never Ability/Style/Emphasis) and by this round's
own regression (below).

## 2. LOCKED -- per-Signal/chart Top/Bottom eligibility allowlist

New `src/chart_relevance.py` functions `metric_top_bottom_eligible()` / `spec_top_bottom_eligible
()`: `ALL_MATCHES_ONLY_METRICS = {"tackles_won_pct"}` (the only fragile ratio currently exported
as a standalone chart metric) plus a name-hint safety net so any future chart-metric export
matching the other locked fragile Signals (Dribble Success %, Shot Accuracy %, Goal Conversion %,
Cross Accuracy %, xG per Shot, xGOT per Shot on Target, and the two conservatively-treated
unresolved Signals -- Big Chance Creation Conversion %, Key Pass Conversion %) defaults to
All-Matches-only rather than silently inheriting eligibility by omission. Every Volume/count
metric is eligible by default (governed by minutes, not action-count, per the design doc's
section 10 finding).

## 3. LOCKED -- X/Y combined eligibility (weakest link)

`spec_top_bottom_eligible()` requires BOTH axes eligible for an X/Y chart; the Tackling pair
(`tackles` vs `tackles_won_pct`) is the only one of the 7 `VOLUME_EXECUTION_PAIRS` domains that
downgrades to All-Matches-only -- the other 6 (Dribbling, Long-Range, Crossing, Passing,
Shooting, Chance Creation) pair two counts and stay eligible. Never mixes a filtered axis with a
season-only one.

## 4. Domain/composite chart eligibility

No Domain-level aggregate chart type exists in the 5-chart engine -- every chart operates on a
single raw `CHART_METRICS` value or a real X/Y pair of them (confirmed again during this
implementation, unchanged from the prior audit). Nothing to implement; if a future round adds a
Domain-aggregate chart, it must inherit the weakest-link rule from section 3.

## 5. Fixed -- Top/Bottom exclusion messaging

`charts.missing_data_reason()` (built in round 5, unchanged mechanism, now reflecting the new 150
threshold automatically since it reads `min_minutes_required` from the regenerated
`filter_eligibility.csv`) already distinguished "no minutes recorded" (zero exposure) from "only N
of 150 minutes needed" (below threshold, real exposure) -- verified this still holds exactly
after the relock (`test_missing_data_reason_distinguishes_zero_from_insufficient_minutes`, plus
new boundary tests).

## 6-7. Player population stability + stale search-state fix

Both built in round 5 (population-signature-based selection pruning in
`views/recommendations.py`, `ntpr_population_sig`), verified unchanged and intact after this
round's edits (the code block sits untouched between this round's new eligibility logic).
Re-confirmed via a fresh AppTest reproduction: Scottish CB -> Spanish FB leaves zero overlapping
player IDs in the selector; a same-population rerun preserves the existing selection exactly.

## 8. Spanish Full Back count -- resolved, root cause confirmed

Traced the full population chain (search -> ranked -> Top 10 -> comparison -> chart -> match-
filter -> Signal-valid -> plotted) directly against real data: **at 270 minutes, Spanish FB Top
10 was 8/10 eligible under Top Opponents, 9/10 under Bottom** (matches the round-5/6 audit
exactly) -- genuine 270-minute eligibility exclusion, NOT stale state, NOT missing Signal data.
**At the new 150-minute floor, this is now 10/10 under both Top and Bottom** -- confirmed
directly. The original "8 players" observation is fully explained and fully resolved by this
round's relock, no separate bug found.

## 9. Fixed -- ambiguous numerical badges

Already fixed in round 5 (`_badges_for()` labels every badge with its Signal when 2+ Signals
share one combined explanation bullet) -- verified unchanged and covered by 3 existing regression
tests plus this round's own smoke tests.

## 10-13. LOCKED -- explanation-engine 5-attempt denominator guard

New `explanation_engine_v2.py`: `FRAGILE_SIGNAL_DENOMINATOR` maps each locked fragile EXECUTION
Signal to its real attempt-count column in the new `data/signal_denominators.csv` export (built
from the same real match-level data used throughout the reliability research -- `tackles_n`,
`dribble_attempts_n`, `shots_total_n`, `total_crosses_n`, season grain, closing the data-
availability gap the design doc flagged). `MIN_ATTEMPTS_FOR_INTERPRETATION = 5`. `_collect_facts
()` now excludes a fragile-family fact from candidacy entirely when its real denominator is below
5 -- it can never become a headline strength/weakness, a league-rank claim, or a global-percentile
claim. Applied ONLY to the 7 fragile Signals (`Tackles Won %`, `Dribble Success %`, `Shot
Accuracy %`, `Goal Conversion %`, `xG per Shot`, `xGOT per Shot on Target`, `Cross Accuracy %`) --
never universally (point 11); Accurate Passes % and every other robust Signal are untouched
(confirmed: `FRAGILE_SIGNAL_DENOMINATOR` doesn't even contain them, so the guard is structurally a
no-op there). Governs INTERPRETATION only, never scoring -- verified directly
(`test_guard_never_touches_scoring`: `signal_scores.parquet` byte-identical before/after building
an explanation). Real regression case: José Fonte (player_id 1166, 2025/2026) -- real denominators
dribble_attempts_n=3, total_crosses_n=2 (both <5) -- `Dribble Success %` and `Cross Accuracy %`
are confirmed excluded from his candidate facts; `Tackles Won %` (tackles_n=12) remains eligible.

## 14-15. Explanation priority + football interpretation

Unchanged from round 4 -- the tier-first, relevance-then-interestingness sort
(`build_explanation`'s `select()`) and the `FOOTBALL_MEANING` implication library are untouched
by this round; the denominator guard is a candidacy PRE-FILTER ahead of that existing pipeline,
not a replacement for it. Complete effective principle is now: **reliable enough to interpret ->
profile relevance -> interestingness/extremeness**.

## 16-20. Five-chart system

`select_five_charts()` (round 5) is unchanged in its selection logic; this round adds eligibility
awareness at the RENDERING layer only (`views/recommendations.py`): each of the 5 charts
independently checks `spec_top_bottom_eligible()` and only renders the "Match filter" selectbox
(with Top Opponents / Bottom Opponents options) when eligible -- an ineligible chart renders with
a plain caption ("All Matches only -- ...") and no selectbox at all, never a disabled control.
The Custom Chart Builder applies the same rule dynamically to whichever metrics the user has
currently selected, with a session-state guard so a stale "Top Opponents" selection can't survive
a metric change that makes it ineligible (would otherwise raise a Streamlit options-mismatch
error). Verified across a 7-profile sample: no profile ever loses ALL 5 Top/Bottom-capable
charts; only the Tackling-family slot (when selected) downgrades.

## 21. Heatmap -- base Style only (preserved, unchanged)

`charts_v2.profile_comparison_figure()` (round 4 fix) is untouched by this round -- still filters
to the Generic (`emphasis == "(none)"`) combo per Style, still structurally invariant to whichever
Emphasis is selected. Re-verified via the existing Yair Mordechai regression tests.

## Validation summary

- **Automated tests**: 2 new files this round (`tests/test_round5_lock_implementation.py`, 13
  tests) plus 2 corrected assertions in the existing `test_round5_relevance_and_fixes.py` (both
  hardcoded the now-superseded 270-minute number; updated to 150 and to the new, fully-recovered
  Scottish CB Top-Opponents result). Full suite: see the exact count in the deployment report.
- **Playwright**: real-browser pass, see the deployment report for the exact result.
- **Regression**: `git status` confirms zero scoring-data files touched; exact row/diff counts in
  the deployment report.

Full evidence and reasoning for every locked number lives in the three referenced research docs
-- not duplicated here.
