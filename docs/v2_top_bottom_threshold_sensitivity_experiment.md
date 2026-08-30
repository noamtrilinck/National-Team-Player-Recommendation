# Top/Bottom-Opponents minute-threshold sensitivity experiment (2026-08-30)

**Analysis only. Nothing in production was changed.** Locked scoring, the 270-minute threshold
itself, Style/Emphasis definitions, and Project 2 are all untouched. This experiment exists to
inform a conscious decision, not to make one.

## 1. Documenting the current rule (as it actually is, not as remembered)

- **Where**: `production/match_level/filter_definitions.py` -- `MIN_MINUTES_BY_FILTER =
  {"top_opponents": 270, "bottom_opponents": 270, ...}`. Applied in
  `production/match_level/build_filtered_eligibility.py` (Stage 4), which flags
  `meets_minimum_sample = minutes_played >= min_minutes_required` per (player, season, team,
  filter_key) row, and separately `position_population_ok = (eligible count for that position x
  filter) >= 15`. `is_eligible_for_dashboard = meets_minimum_sample & position_population_ok`.
- **Exactly `>= 270`, not `> 270`** -- confirmed directly in code (`>=`).
- **Independent per filter**: Top and Bottom Opponents each get their own 270-minute count,
  computed from that player's OWN matches against that specific opponent bracket -- a player can
  clear one and fail the other (confirmed repeatedly in the Scottish CB case).
- **Applied AFTER raw aggregation, BEFORE the percentile stage**: Stage 2
  (`build_filtered_unified.py`) aggregates a player's stats across whichever matches qualify for a
  filter regardless of the 270-minute floor -- a below-floor player's raw/per-90 numbers DO exist
  in `player_season_unified_by_filter_with_per90.csv`. Stage 5
  (`build_filtered_percentiles.py`) then computes percentiles ONLY over the eligible (>=270)
  population. The dashboard's own export (`build_dashboard_data.build_match_level_stats`) does an
  **inner join** between the per-90 file and the percentile file -- so a below-floor player is
  dropped from **Raw, Per-90, AND Percentile display modes simultaneously**, not just Percentile.
  This wasn't obvious from the UI and is worth stating plainly: today, "not shown under this
  filter" means all three modes, always together.
- **Applies at the (player, filter) grain, not per-Signal**: if a player fails the floor for
  `top_opponents`, EVERY chart metric under that filter disappears for them together -- there is
  currently no per-Signal reliability layer at all (this is exactly the gap point 8 asks about;
  confirmed absent in every stage of the pipeline read for this experiment).
- **Never touches Domain-level or locked scoring**: `build_filtered_eligibility.py`'s own
  docstring states this pipeline stopped producing filtered Ability/Philosophy/Domain scores after
  an earlier product decision -- "filters are an ANALYTICAL tool only." Confirmed: Final Score,
  Global Rank, Style/Emphasis scores are always computed from full-season data, never touched by
  this threshold, at any threshold tested below.
- **Only affects the dashboard's comparison charts** (Standout metrics, Custom Chart Builder) --
  no other production output.
- **When introduced / why 270 specifically**: found the original evidence-based analysis --
  `Archive/production_v1_scoring/docs_v1_lock_summaries/match_level_filtering_pipeline.md` §6
  (dated before this project's V2/F50 rescoring migration; the RULE itself, unlike the rest of
  that era's scoring pipeline, was carried forward unchanged into the still-live
  `filter_definitions.py` -- the document location in `Archive/` reflects when the analysis was
  written, not that the rule is stale). It tested population retention at 3/4/5/8-match floors
  specifically for Top/Bottom Opponents (the thinnest filter by construction -- a team meets only
  3-5 "extreme" clubs per season) and chose **3 matches (270 min) as "the floor that still
  requires a genuine repeat sample"** -- 4 matches would have dropped Bottom-Opponents retention
  to 73.9%, 5 to 58.5%. It also explicitly disclosed, at the time, that even 3 matches leaves
  substantial residual noise for rare-event stats (SE approx. 49-59% of the mean) -- **this
  experiment's Part B findings below are a re-confirmation of a known, disclosed limitation, not a
  new discovery**.

**A vs. B, corrected**: round 4 described the mechanism as "player never faced that opponent
bracket" (true only for the rare literal-zero-minutes case); round 5 corrected this to "some
minutes, below the floor" (case B) for the general/common case. Both are real and both occur; case
B is the dominant one in every population sampled here.

## 2-4. Coverage at 5 candidate thresholds

Recomputed directly from `player_season_unified_by_filter_with_per90.csv`'s real
`minutes_played` per (player, season, team, filter_key) -- no new data needed, no threshold
touched in production.

**Full population (7,678 player-seasons), Top Opponents:**

| Threshold | Eligible | % of population | Gain vs. previous |
|---|---:|---:|---:|
| >=270 (current) | 6,871 | 89.5% | -- |
| >=180 | 7,305 | 95.1% | +434 (+5.7pp) |
| >=135 | 7,417 | 96.6% | +112 (+1.5pp) |
| >=90 | 7,510 | 97.8% | +93 (+1.2pp) |
| >=45 | 7,562 | 98.5% | +52 (+0.7pp) |

**Bottom Opponents:**

| Threshold | Eligible | % of population | Gain vs. previous |
|---|---:|---:|---:|
| >=270 (current) | 6,729 | 87.6% | -- |
| >=180 | 7,259 | 94.5% | +530 (+6.9pp) |
| >=135 | 7,381 | 96.1% | +122 (+1.6pp) |
| >=90 | 7,507 | 97.8% | +126 (+1.7pp) |
| >=45 | 7,560 | 98.5% | +53 (+0.7pp) |

**Clear diminishing returns after 180**: the 270->180 step buys 5.7-6.9 percentage points; every
step after that buys 0.7-1.7pp. This matches §6's original 3-vs-4-match retention analysis almost
exactly (independently re-derived, same conclusion).

**Minutes distribution** (players with any recorded minutes under the filter):

| Bucket | Top Opponents | Bottom Opponents |
|---|---:|---:|
| 0-44 | 38 | 40 |
| 45-89 | 52 | 53 |
| 90-134 | 93 | 126 |
| 135-179 | 112 | 122 |
| 180-269 | 434 | 530 |
| 270+ | 6,871 | 6,729 |

No dramatic "cliff" right at 270 -- the 180-269 bucket (434/530 players) is the single largest
non-270+ bucket, meaning most of the near-miss population sits comfortably below 270 (median
around 220-230), not clustered at 268-269. **The literal 269-vs-270 all-or-nothing case is
individually rare**, though the general hard-cutoff critique (point 10) still holds in principle.

**Position coverage at 270 vs. 90** (selected positions, Top Opponents): Centre Forward is the
weakest position at the current floor (84.8% at 270, recovering to 96.4% at 90) -- consistent
with forwards rotating/getting substituted more; Centre Back is close to the population average
(92.4% -> 98.4%). No position collapses at any tested threshold.

### Scottish Centre Back Top-10 (the reproduction case)

| Player | Season min | Top Opp min | 270 | 180 | 135 | 90 | 45 | Bottom Opp min | 270 | 180 | 135 | 90 | 45 |
|---|---:|---:|:-:|:-:|:-:|:-:|:-:|---:|:-:|:-:|:-:|:-:|:-:|
| Liam Lindsay | 1582 | 411 | Y | Y | Y | Y | Y | 274 | Y | Y | Y | Y | Y |
| Liam Cooper | 909 | 184 | N | Y | Y | Y | Y | 90 | N | N | N | Y | Y |
| Luke Graham | 3129 | 1260 | Y | Y | Y | Y | Y | 1239 | Y | Y | Y | Y | Y |
| Craig Halkett | 2536 | 1130 | Y | Y | Y | Y | Y | 866 | Y | Y | Y | Y | Y |
| Murray Wallace | 2778 | 728 | Y | Y | Y | Y | Y | 810 | Y | Y | Y | Y | Y |
| Liam Henderson | 3002 | 1493 | Y | Y | Y | Y | Y | 1260 | Y | Y | Y | Y | Y |
| Lenny Agbaire | 1013 | 319 | Y | Y | Y | Y | Y | 102 | N | N | N | Y | Y |
| Kal Naismith | 3124 | 695 | Y | Y | Y | Y | Y | 887 | Y | Y | Y | Y | Y |
| Jason Kerr | 2880 | 630 | Y | Y | Y | Y | Y | 990 | Y | Y | Y | Y | Y |
| David Bates | 1378 | 160 | N | N | Y | Y | Y | 806 | Y | Y | Y | Y | Y |

**Confirmed**: 10 -> 8 under Top and 10 -> 8 under Bottom at the current 270-min floor is fully
explained by the minutes rule (this experiment's independent re-derivation matches round 5's
audit exactly). The originally reported "7 under Bottom" is one player different -- traced to a
separate, correctly-disclosed layer (a player who clears the minutes floor but has a NaN value for
that specific chart's specific metric; not re-litigated further here since the mechanism is
already understood). At 180 min: Top recovers to 9/10 (only David Bates still short); Bottom stays
at 8/10 until 90 min, where both remaining exclusions (Cooper, Agbaire) clear.

### Simulated real searches (Top 10 by Final Score, multiple positions/leagues/nationalities)

| Search | Top Opp: 270/180/135/90/45 | Bottom Opp: 270/180/135/90/45 |
|---|---|---|
| Scottish Centre Backs | 8/9/10/10/10 | 8/8/8/10/10 |
| Spanish Full Backs | 8/10/10/10/10 | 9/9/10/10/10 |
| English Central Midfielders | 9/10/10/10/10 | 9/10/10/10/10 |
| Dutch Wingers | 8/8/8/8/10 | 7/9/9/9/10 |
| Brazilian Centre Forwards | 8/8/9/9/10 | 7/9/9/9/9 |
| German Defensive Midfielders | 10/10/10/10/10 | 9/10/10/10/10 |
| All Centre Backs (no nationality filter) | 9/10/10/10/10 | 8/10/10/10/10 |
| All Wingers (no nationality filter) | 10/10/10/10/10 | 10/10/10/10/10 |

Niche/small-nationality searches (Scotland, Netherlands, Brazil) lose 2-3 of 10 players at the
current threshold -- broad/large searches (England, Germany, no-nationality-filter) rarely lose
more than 0-1. This is a real, user-visible pattern: **the current threshold is most noticeable
exactly where users are most likely to search narrowly** (a specific nationality within a
specific position), which is a meaningful part of this dashboard's actual use case.

## 5-7. Stability: real match-level resampling, not synthetic simulation

**Method**: pulled the real `player_match_performance` rows (from the project's own database) for
400 randomly sampled Centre Backs who clear the CURRENT 270-minute Top-Opponents floor (the
"trusted"/ground-truth cohort), restricted to their actual matches against Top-Opponent-band
clubs. For each of the 5 candidate thresholds, ran 10 real bootstrap draws per player: shuffle
their real matches into a random order, accumulate real minutes until the threshold is crossed,
and compute the metric from that ACTUAL subset of real matches -- compared against the metric
computed from their FULL >=270-minute sample (treated as ground truth). This is real resampling
from real match data, not a statistical simulation.

**Scope disclosed**: Centre Backs only (matches the reproduction case), 400 of 1,621 eligible
trusted CBs (subsampled for runtime), 4 signals spanning both requested families -- 2 Volume
(Tackles per90, Dribble Attempts per90) and 2 Execution/% (Tackle Success %, Dribble Success %).
Broader position/signal coverage was not run given this task's scope, but the CB-only result
already independently reconfirms §6's original SE estimates almost exactly, which is a good sign
this generalizes.

**Bias vs. spread** (deviation of the sampled value from the full-sample "truth"):

| Signal | T=270 std dev | T=180 | T=135 | T=90 | T=45 | Bias at any T |
|---|---:|---:|---:|---:|---:|---|
| Tackles per90 | 0.51 | 0.69 | 0.76 | 1.08 | 1.16 | ~0 (unbiased throughout) |
| Tackle Success % (pts) | 22.9 | 30.1 | 32.9 | 39.8 | 40.9 | ~+1pt (negligible) |
| Dribble Attempts per90 | 0.26 | 0.35 | 0.39 | 0.55 | 0.61 | ~0 (unbiased throughout) |
| Dribble Success % (pts) | 26.2 | 29.8 | 30.4 | 35.3 | 34.9 | ~0 to -1pt (negligible) |

**No systematic bias at any threshold** -- lowering the threshold makes signals noisier, not
skewed. But the noise itself is large and grows steadily (roughly doubling from 270 to 45 for the
per-90 Volume signals; percentage signals are noisy at EVERY threshold tested, including the
current one -- see below).

**Rank stability** (mean Spearman correlation between the full-sample "true" ranking and each
threshold's sampled ranking, averaged over draws; ~400 players):

| Signal | rho @270 | @180 | @135 | @90 | @45 |
|---|---:|---:|---:|---:|---:|
| Tackles per90 | 0.770 | 0.656 | 0.636 | 0.502 | 0.457 |
| Tackle Success % | 0.687 | 0.578 | 0.541 | 0.446 | 0.437 |
| Dribble Attempts per90 | 0.772 | 0.662 | 0.643 | 0.498 | 0.494 |
| Dribble Success % | 0.771 | 0.732 | 0.717 | 0.632 | 0.627 |

**Important, somewhat uncomfortable finding**: even at the CURRENT, production 270-minute
threshold, rank correlation with the "true" full-season-vs-Top-Opponents value is only
~0.69-0.77 (mean rank movement 58-64 places out of ~400) -- a 270-minute sample is itself a small
sample of a season, and this comparative UI's rankings were never as stable as a single number on
screen implies. This is not new information (§6 disclosed it at design time) but this experiment
makes it concretely visible. Degradation below 270 is real and continuous (roughly halving rho by
45 minutes), not a cliff -- there is no single "safe" threshold below which everything breaks and
above which everything is fine; it is a smooth trade-off.

## 8. Layer 1 (minutes) vs. Layer 2 (action-sample) reliability -- confirmed as a SEPARATE, currently-unaddressed problem

Directly measured, using the same real-match bootstrap: even among players who clear the CURRENT
270-minute Top-Opponents floor, how many of their real matches-to-date have a thin action
denominator for a percentage Signal?

| Threshold | % of samples with <5 tackle attempts (Tackle Success % denominator) | % of samples with <3 dribble attempts (Dribble Success % denominator) |
|---|---:|---:|
| 270 (current) | 52.7% | 85.1% |
| 180 | 76.9% | 92.5% |
| 135 | 80.7% | 93.7% |
| 90 | 95.7% | 97.9% |
| 45 | 96.9% | 98.3% |

**This confirms point 8's concern directly and quantitatively, at the CURRENT threshold, not just
at lower ones**: over half of 270-minute Top-Opponents samples for Centre Backs still have fewer
than 5 tackle attempts behind their displayed Tackle Success %, and 85% have fewer than 3 dribble
attempts behind Dribble Success %. **The 270-minute rule (Layer 1) does not, by itself, guarantee
a reliable percentage Signal (Layer 2) -- these are genuinely two separate problems, and today
only Layer 1 exists anywhere in the pipeline.** Layer 2 does not currently get worse or better by
changing the minute threshold in either direction -- it is a structurally separate gap that a
minutes-only threshold, at any value, cannot close.

## 9-10. Tiered reliability and the hard-cutoff question

The rank-stability and bias/spread results support a graduated view rather than a single cliff:
- Stability degrades smoothly and continuously across every threshold tested -- there is no
  evidence of a natural "safe/unsafe" break point at exactly 270, or at any other single value.
- The 270-vs-269 literal cliff is individually rare (few players sit at the exact boundary; most
  of the near-miss population is well below 270), but the underlying principle it represents --
  "one more minute suddenly makes a number OK to show" -- is not supported by the stability data
  at ANY of the tested boundaries, including the current one.
- This is evidence FOR exploring a tiered/graduated display concept (visible but flagged at lower
  confidence, per the brief's own conceptual "Strong / Limited / Insufficient" sketch) rather than
  evidence for or against any specific number -- the data doesn't identify a single correct cutoff
  because there isn't one; it identifies a continuous trade-off curve.

## 12. Trade-off summary and recommendation

| Threshold | Top coverage | Bottom coverage | Rank stability (rho, CB signals) | Denominator reliability | UI impact |
|---|---:|---:|---:|---:|---|
| 270 (current) | 89.5% | 87.6% | 0.69-0.77 | Poor even here (53-85% thin) | Noticeable in niche/nationality searches |
| 180 | 95.1% | 94.5% | 0.58-0.73 | Worse | Recovers most niche-search gaps |
| 135 | 96.6% | 96.1% | 0.54-0.72 | Worse still | Marginal further gain |
| 90 | 97.8% | 97.8% | 0.45-0.63 | Poor | Small further gain, real stability cost |
| 45 | 98.5% | 98.5% | 0.44-0.63 | Poor | Diminishing coverage gain, largest stability cost |

**Recommendation: C -- a lower DISPLAY threshold combined with an explicit reliability tier/label,
not a straight swap of the hard 270-minute cutoff for a different one.**

Reasoning, directly from the evidence above:
1. There is no threshold in the tested range where rank stability is genuinely "safe" -- even 270
   only reaches rho~0.7-0.77. Recommending a straight lower hard cutoff (option B) would present
   fabricated confidence at exactly the thresholds where the data shows the least of it.
2. Coverage gains are real and concentrated in the 270->180 step (+5.7 to +6.9pp, recovering most
   of the niche-search pain point identified in section 4) with steadily diminishing returns
   after that -- so a pure coverage argument favors going at least to ~180, not all the way to 45.
3. Keeping the hard 270-minute cutoff unchanged (option A) leaves real, currently-invisible-to-
   users coverage loss on the table (confirmed concretely in the Scottish CB/Spanish FB/Dutch/
   Brazilian cases) without actually buying the stability users might assume a "270-minute
   minimum" implies (option A doesn't solve the Layer-2 problem either, and its own rank stability
   isn't as strong as its single hard number suggests).
4. The Layer-1/Layer-2 distinction (section 8) is real and independent of whatever minute
   threshold is chosen -- a tiered architecture is also the natural place to eventually add a
   Layer-2 (denominator-based) caveat without conflating it with the minutes question, which a
   pure hard-cutoff change (A or B) cannot do at all.

This is a recommendation, not an implementation -- **no production threshold, display logic, or
methodology was changed as part of this task**, per the explicit instruction.
