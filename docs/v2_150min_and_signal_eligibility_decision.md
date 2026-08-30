# 150-minute floor + Signal Top/Bottom eligibility -- final decision check (2026-08-30)

**Analysis only, nothing implemented.** Short follow-up to the two prior experiments, using
already-collected evidence plus one direct 150-minute recomputation.

## A. 150-minute findings

**Coverage** (recomputed directly, real data):

| Threshold | Top coverage | Bottom coverage |
|---|---:|---:|
| 270 (current) | 89.5% | 87.6% |
| 180 | 95.1% | 94.5% |
| **150** | **96.1%** | **95.7%** |
| 135 | 96.6% | 96.1% |

150 gains +6.6pp (Top) / +8.1pp (Bottom) over 270, and only +1.0pp/+1.2pp over 180 -- sitting
almost exactly on the diminishing-returns knee already identified, essentially matching 135's
coverage (within 0.4-0.5pp) while being a rounder, more explainable number. **No position
collapses**: every position clears 91.7%+ at 150 (weakest: Secondary Striker, n=24, too small a
group to weight heavily; next-weakest a real sample: Centre Forward 94.3%).

**Scottish CB Top 10 at 150**: Top Opponents **10/10** available (full recovery -- David Bates,
the last holdout at 270/180, clears at 150 with his real 160 minutes). Bottom Opponents **8/10**
(Liam Cooper 90min and Lenny Agbaire 102min remain below even 150 -- correctly still excluded,
since they genuinely have very little Bottom-Opponents data).

**Niche searches**: Dutch Wingers Top stays 8/10 at 150 (unchanged from 270/180/135 -- these
particular exclusions are deeper than 150 anyway); Bottom recovers to 9/10 by 180 already.
Brazilian CF Top recovers to 9/10 at 150 (from 8/10 at 270/180).

**Any evidence-based reason not to use 150?** None found. It sits inside the already-mapped
diminishing-returns region (180-135), recovers the Scottish CB Top case completely, doesn't
collapse any position, and the rank-stability curve from the prior experiment (rho ~0.66-0.73 at
135-180) interpolates smoothly here too -- a real but modest, previously-disclosed stability
cost versus 270, not a new risk. **150 is a defensible single hard floor.**

## B. Signal Top/Bottom eligibility

Classified the locked catalog's 13 EXECUTION (percentage/efficiency) Signals plus their VOLUME
counterparts, using the denominator/stability evidence already collected (not by Domain name --
per Signal). 8 of the 13 were directly measured (numerator/denominator distributions + real
bootstrap stability); the other 5 (marked *) share an identical denominator to an already-measured
Signal and are classified by that direct mechanical link, not assumption.

| Signal | Domain | Type | Denominator | Top-Opp typical (P50) | % <10 (Top/Bottom) | Verdict | Reason |
|---|---|---|---|---:|---|---|---|
| Accurate Passes % | Ball Progression -- Passing | EXECUTION | passes | 202 | ~0% | **ELIGIBLE** | Denominator never thin at any grain tested |
| Ground Duel Success % | Physical Contests -- Ground | EXECUTION | total_duels | 61 | ~1% | **ELIGIBLE** | Same |
| Aerial Duel Success % | Physical Contests -- Aerial | EXECUTION | aerials contested | 16 | 27% | **ELIGIBLE** | Moderate, median denominator healthy (16); not in the fragile tier |
| Long Balls Won % | Long-Range Distribution | EXECUTION | long_balls | 21 | 25.6% | **ELIGIBLE** | Same moderate profile as Aerial |
| Tackles Won % | Tackling | EXECUTION | tackles | 10 | 49.6-55.8% | **ALL-MATCHES ONLY** | Direct bootstrap: 1-4 attempts average 17-34pt deviation; half of Top/Bottom samples are under 10 attempts |
| Dribble Success % | Dribbling / Take-Ons | EXECUTION | dribble_attempts | 7 | 60.7-61.8% | **ALL-MATCHES ONLY** | Direct bootstrap: same pattern, worse denominator |
| Shot Accuracy % | Shooting | EXECUTION | shots_total | 6 | 68.5/64.8% | **ALL-MATCHES ONLY** | Worst denominator of any Signal tested |
| Goal Conversion % | Shooting | EXECUTION | shots_total | 6 | 68.5/64.8% | **ALL-MATCHES ONLY** | Same denominator as Shot Accuracy % |
| Cross Accuracy % | Wide Delivery / Crossing | EXECUTION | total_crosses | 8 | 56.4/53.9% | **ALL-MATCHES ONLY** | Consistently thin |
| xG per Shot * | Shooting | EXECUTION | shots_total | 6 | (same as above) | **ALL-MATCHES ONLY** | Identical denominator to Shot Accuracy/Goal Conversion |
| xGOT per Shot on Target * | Shooting | EXECUTION | shots_on_target | <=shots_total | (same family) | **ALL-MATCHES ONLY** | Denominator is a SUBSET of an already-fragile one |
| Big Chance Creation Conversion % * | Chance Creation | EXECUTION | big_chances_created | not directly measured | -- | **REVIEW** | Chance-Creation volume events are themselves low-frequency at full season; plausibly fragile but not independently measured this pass |
| Key Pass Conversion % * | Chance Creation | EXECUTION | key_passes | not directly measured | -- | **REVIEW** | Same reasoning -- genuinely unresolved, flagging rather than guessing |

**Volume counterparts, same domains** (Dribble Attempts per90, Tackles per90, Shots Total per90,
Total Crosses per90, Long Balls per90, Aerial Duel Attempts per90, Ground Duel Attempts per90,
Passes per90, Passes in Final Third per90, Key Passes per90, Big Chances Created per90): **all
ELIGIBLE**. Confirmed directly (prior experiment, section 10): a per-90 rate is governed by
minutes (Layer 1) alone, never collapses to an undefined/meaningless value the way a 0/0 or
1/1 percentage does, and shows smooth, continuous noise growth rather than the sharp fragility
percentage Signals show. **Point 9's hypothesis holds exactly**: Dribble Attempts per90
(ELIGIBLE) and Dribble Success % (ALL-MATCHES ONLY) genuinely diverge, same domain, opposite
verdict -- confirmed by real data, not assumed.

### Proposed production allowlist (comparison-chart-facing metric pool)

**TOP/BOTTOM ELIGIBLE** -- every current `CHART_METRICS` volume/count entry (touches, passes,
accurate_passes [raw count], passes_in_final_third, key_passes, big_chances_created, assists,
shots_total, shots_on_target, goals, dribble_attempts, successful_dribbles, total_crosses,
accurate_crosses, tackles, tackles_won [raw count], interceptions, clearances, aerials_won,
ball_recoveries, long_balls, long_balls_won [raw count], duels_won, fouls_drawn) plus
`accurate_passes_pct`, `long_balls_won_pct`.

**ALL-MATCHES ONLY** -- `tackles_won_pct`. (The only PCT_METRICS entry that fails; the fragile
Signals from the locked catalog -- Dribble/Shot/Goal/Cross efficiency -- are not currently
exported as standalone `CHART_METRICS` percentage columns at all, so this list is short mainly
because most fragile ratios aren't chart-facing yet, not because they were all judged safe. If a
future round adds them as chart metrics -- e.g. exporting a Dribble Success % chart column --
they should inherit the ALL-MATCHES-ONLY verdict from the table above.)

**REVIEW** -- none in the current chart-facing pool (the two genuinely-unresolved Signals, Big
Chance Creation Conversion % and Key Pass Conversion %, are explanation-only, not currently
offered as comparison-chart metrics).

## C. Five-chart system impact

Re-classified all 10 profile samples from the round-5 chart-selection sanity check
(`docs/v2_ui_redesign_round5.md`) against this allowlist:

| Profile | Charts Top/Bottom-eligible | All-Matches-only |
|---|---:|---:|
| CB/Aerial | 5/5 | 0 |
| FB/Attacking | 5/5 | 0 |
| WM/Ball Carrier | 5/5 | 0 |
| Winger/Ball Carrier | 5/5 | 0 |
| Winger/Creator-Provider | 5/5 | 0 |
| DM/Defensive Mind | 5/5 | 0 |
| CM/Progression (Generic) | 5/5 | 0 |
| AM/Creator | 5/5 | 0 |
| **CF/Finisher** | **4/5** | **1 (tackles_won_pct)** |
| Winger/Goal Threat | 5/5 | 0 |

**No profile ever drops to zero Top/Bottom-capable charts; chart diversity is essentially
unharmed.** Only 1 of 50 sampled chart slots (CF/Finisher's `tackles_won_pct`) becomes
All-Matches-only -- because the current chart-metric pool already leans heavily toward raw
counts (which are always eligible) rather than fragile percentages, and the one PCT_METRICS entry
that IS fragile (`tackles_won_pct`) only happened to be selected once in the whole sample.

**X/Y combined eligibility** (point 10 -- both axes must match): re-checked all 7
`VOLUME_EXECUTION_PAIRS` domains -- 6 of 7 pair two raw counts (never fragile, e.g. dribble
attempts vs. successful dribbles, total crosses vs. accurate crosses) and stay ELIGIBLE; only
the Tackling pair (`tackles` vs. `tackles_won_pct`) would need to drop to All-Matches-only as a
combined chart, consistent with the single-metric finding above.

**Domain-level charts** (point 11): the current 5-chart engine has no Domain-aggregate chart
type -- every chart operates on a single raw `CHART_METRICS` value or a real X/Y pair of them, so
this question doesn't currently apply. If a future round adds a Domain-level aggregate chart, it
should inherit the weakest-link rule from the X/Y case (eligible only if every Signal feeding it
is eligible) rather than being assumed valid by default.

## D. Explanation-engine (season-level) reliability -- confirmed scope, unchanged conclusion

The ~5-attempt Layer-2 finding from the prior experiment applies to **season-level (full_season)
percentage/efficiency evidence in `explanation_engine_v2.py`'s headline/rank selection** -- a
SEPARATE mechanism from the chart-eligibility question above (charts operate on the filtered
`CHART_METRICS` pool; explanations always read full-season `signal_scores.parquet`, never a
filtered subset, confirmed in the prior design doc's section 11). Scope, exactly as previously
proposed and unchanged by this task: a candidate fact for a fragile-family EXECUTION Signal
(Tackles Won %, Dribble Success %, Shot Accuracy %, Goal Conversion %, Cross Accuracy %, and by
the same-denominator link xG per Shot/xGOT per Shot on Target) below ~5 underlying attempts
should be excluded from headline/Areas-to-Watch candidacy and from any league-rank/global-
percentile claim -- exactly the "100% Dribble Success -- 1/1" case -- while the raw count itself
may still be shown as plain descriptive text where useful ("2/3 successful dribbles"), never
promoted to a comparative claim. **This does not touch scoring** -- it is a candidate-pool filter
in the explanation engine only, identical in kind to the existing RESPONSIBILITY/SPECIALISATION
exclusion already in production. Not implemented in this task, per the explicit instruction.

## Summary / recommendation

1. **150-minute single hard floor**: supported by the evidence, no red flags found. Recommend
   locking it in place of the current 270-minute floor for Round 5 (replacing the tiered-badge
   idea, per your simplification request).
2. **Per-Signal/chart Top/Bottom eligibility**: recommend locking the allowlist in section B --
   in practice this removes Top/Bottom only from `tackles_won_pct` in the current chart pool
   (and its X/Y pairing), with a standing rule for any future fragile percentage chart metric.
3. **Five-chart system**: effectively unaffected -- diversity preserved, no profile loses
   Top/Bottom entirely.
4. **Explanation engine**: the ~5-attempt guard remains a separate, still-unimplemented,
   scoring-safe design item, unchanged by this task.

Nothing above has been implemented -- ready for your decision on what to lock for Round 5.
