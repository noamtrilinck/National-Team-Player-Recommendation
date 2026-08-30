# Two-layer reliability architecture: design + evidence (2026-08-30)

**Design/analysis only. Nothing in production was changed** -- no threshold, no denominator rule,
no UI, no scoring. Builds directly on
`v2_top_bottom_threshold_sensitivity_experiment.md` (previous task).

## 1. Accepted starting point

270 minutes was a legitimate, evidence-based choice at the time (§6 of the archived pipeline
doc). But even at 270 min, Top/Bottom rank correlation with the "true" larger sample only reaches
~0.70-0.77; coverage gains taper sharply after 180 min; there is no threshold in the tested range
that is fully reliable. A binary AVAILABLE/NOT AVAILABLE gate cannot represent this continuum
honestly. This task designs a two-layer, tiered alternative.

## 2-3. Layer 1 -- match-sample (minutes) tiers: three candidates tested

| Architecture | Top: Strong/Limited/Insufficient | Bottom: Strong/Limited/Insufficient | Displayable (Strong+Limited) |
|---|---|---|---|
| **A** Strong>=270 / Limited 180-269 / Insuff<180 | 89.5% / 5.7% / 4.9% | 87.6% / 6.9% / 5.5% | Top 95.2%, Bottom 94.5% |
| **B** Strong>=270 / Limited 135-269 / Insuff<135 | 89.5% / 7.1% / 3.4% | 87.6% / 8.5% / 3.9% | Top 96.6%, Bottom 96.1% |
| **C** Strong>=180 / Limited 90-179 / Insuff<90 | 95.1% / 2.7% / 2.2% | 94.5% / 3.2% / 2.2% | Top 97.8%, Bottom 97.7% |

**Position breakdown** (Architecture A, Top Opponents): every position clears >=87.5%
displayable; Secondary Striker is the thinnest (87.5%, n=24, too small a group to read much into);
Centre Forward next-thinnest at a real sample (92.0%, n=979) -- consistent with forwards rotating
more.

**Scottish CB Top 10 under each architecture** -- the reproduction case:

| Player | Top min | A | B | C | Bottom min | A | B | C |
|---|---:|---|---|---|---:|---|---|---|
| Liam Lindsay | 411 | Strong | Strong | Strong | 274 | Strong | Strong | Strong |
| Liam Cooper | 184 | **Limited** | **Limited** | Strong | 90 | **Insuff.** | **Insuff.** | **Limited** |
| Luke Graham | 1260 | Strong | Strong | Strong | 1239 | Strong | Strong | Strong |
| Craig Halkett | 1130 | Strong | Strong | Strong | 866 | Strong | Strong | Strong |
| Murray Wallace | 728 | Strong | Strong | Strong | 810 | Strong | Strong | Strong |
| Liam Henderson | 1493 | Strong | Strong | Strong | 1260 | Strong | Strong | Strong |
| Lenny Agbaire | 319 | Strong | Strong | Strong | 102 | **Insuff.** | **Insuff.** | **Limited** |
| Kal Naismith | 695 | Strong | Strong | Strong | 990 | Strong | Strong | Strong |
| Jason Kerr | 630 | Strong | Strong | Strong | 160 | -- | -- | -- |
| David Bates | 160 | **Insuff.** | **Limited** | **Limited** | 806 | Strong | Strong | Strong |

**Under every architecture, at least 9 of 10 players remain VISIBLE (Strong or Limited) under
Top; at least 8 of 10 under Bottom** -- a materially better outcome than today's binary cutoff
(8/10 and 8/10 hard-visible, the rest simply gone with no context). Only Architecture C ever
reduces an "Insufficient" case anywhere in this sample, and even then only for the two genuinely
thinnest players (Cooper, Agbaire, both <102 min).

## 4. Layer 2 audit -- every percentage/efficiency Signal that can appear in the app

Numerator/denominator, sourced directly from the real, already-exported
`player_season_unified_by_filter_with_per90.csv` (no new data needed), computed at THREE grains
per point 9's requirement -- full season, Top Opponents, Bottom Opponents:

| Signal | Num / Den | Full-season P10/P50/P90 | Top-Opp P10/P50/P90 | Bottom-Opp P10/P50/P90 | Full-season <5 | Top-Opp <5 | Bottom-Opp <5 |
|---|---|---|---|---|---:|---:|---:|
| Accurate Passes % | accurate_passes/passes | 268/657/1393 | 72/202/464 | 75/217/494 | 0.1% | 0.1% | 0.1% |
| Ground Duel Success % | duels_won/total_duels (proxy) | 96/187/323 | 26/61/119 | 26/59/109 | 0.1% | 0.5% | 0.4% |
| Aerial Duel Success % | aerials_won/(won+lost) | 19/50/125 | 5/16/43 | 5/16/43 | 0.6% | 8.5% | 8.9% |
| Long Balls Won % | long_balls_won/long_balls | 14/66/177 | 4/21/61 | 4/21/62 | 1.7% | 11.5% | 11.7% |
| Tackles Won % | tackles_won/tackles | 11/28/56 | 3/10/22 | 3/9/19 | 1.9% | 18.6% | 22.6% |
| Dribble Success % | successful_dribbles/dribble_attempts | 5/22/62 | 2/7/22 | 2/7/22 | 9.6% | 32.3% | 32.3% |
| Shot Accuracy % / Goal Conversion % | (shots_on_target or goals)/shots_total | 6/20/53 | 2/6/18 | 2/7/20 | 6.5% | 36.7% | 33.2% |
| Cross Accuracy % | accurate_crosses/total_crosses | 3/22/97 | 1/8/32 | 1/8/35 | 17.1% | 35.9% | 33.3% |

**This is a MAJOR structural issue, not a small edge case** -- and it is already present at full
season grain for the weaker families (Dribbling/Shooting/Crossing already have 6.5-17.1% of
observations under 5 opportunities in a WHOLE SEASON), and becomes dominant under Top/Bottom
filters, where Shooting (up to 68.5% at <10, see the previous experiment's finding), Dribbling
(60-62% at <10), and Crossing (54-56% at <10) are frequently built on single-digit samples.
**Passing and Ground Duels are essentially always safe** at every grain tested (denominators in
the hundreds even under a single-opponent-bracket filter) -- confirming point 5's premise directly:
**one universal action threshold cannot be correct across these families.**

## 5-6. Signal-specific rules, empirically grounded (not "sounds reasonable")

Real match-level bootstrap (reused from the sensitivity experiment: 400 trusted Centre Backs,
real matches vs Top Opponents), this time binned by the ACTUAL resulting denominator rather than
by minute threshold -- directly answers "at what denominator does this become useful":

**Tackle Success %** (mean absolute deviation from the "true" full-sample value, by attempt count):
| Attempts | 1-2 | 3-4 | 5-9 | 10-19 |
|---|---:|---:|---:|---:|
| Mean abs deviation | 33.9 pts | 17.4 pts | 11.3 pts | 6.4 pts |

**Dribble Success %:**
| Attempts | 1 | 2 | 3-4 | 5-9 | 10+ |
|---|---:|---:|---:|---:|---:|
| Mean abs deviation | 23.8 pts | 16.8 pts | 14.5 pts | 9.5 pts | 4.7 pts |

Both signals cross below ~10 percentage points of expected deviation somewhere around **5
attempts**, and are still averaging 15-34 points of noise below that -- i.e. a percentage
statement built on 1-4 opportunities is closer to a coin flip than a descriptive fact. This
empirical curve, not intuition, is the basis for the tier boundaries proposed in section 7.
**Proposed family grouping**, directly from sections 4+6's evidence:
- **Robust families (Passing, Ground Duels)**: denominators are large enough at every grain
  tested that a Layer-2 floor essentially never binds -- no meaningful extra rule needed.
- **Moderate families (Aerial Duels, Long Balls)**: denominators shrink meaningfully under
  Top/Bottom filters (8.5-11.7% under 5) but stay reasonable at full season -- a modest floor
  (~5 attempts) is enough.
- **Fragile families (Tackling, Dribbling, Shooting/Conversion, Crossing)**: frequently thin even
  at full season, dominant under Top/Bottom filters (30-70% under 10 attempts) -- these need the
  full 3-tier Layer-2 treatment and are where a denominator floor matters most.

## 7. Displayable / Headline-eligible / Rank-eligible -- three distinct bars, not one

Grounded directly in the stability curve above:

| Concept | Proposed floor (fragile families) | Rationale |
|---|---|---|
| **Displayable** | >=1 attempt (i.e. any real data) | Show the raw count always -- "1/1", "2/6" is honest and informative on its own; suppressing it entirely throws away real, if limited, information (point 17). |
| **Headline-eligible** (can become explanation evidence) | ~5+ attempts | Below this, mean deviation is still 15-24 points -- too noisy to assert as "why this player stands out." |
| **Rank/percentile-eligible** (league rank, global percentile, "#3 in league") | ~5+ attempts, same floor as headline | A rank claim is a comparative claim across the whole population -- needs the same reliability bar as a headline claim, arguably a slightly stricter one, but the evidence doesn't support a materially different number from Headline-eligible given the smooth (not cliff-shaped) curve. |

A player with 4/6 dribbles is **Displayable** ("4/6 successful dribbles") but not
**Headline-eligible** or **Rank-eligible** ("67% -- #3 in league" is NOT shown) -- exactly the
worked example in the brief, and now grounded in a real number (14.5pt mean deviation at 3-4
attempts) rather than asserted.

## 8. Showing counts when counts matter

Proposed compact treatment for the Limited tier: append the raw count only when the family is
fragile and the count is below the Headline/Rank floor -- `"67% Dribble Success · 4/6"` -- and
never for the robust families (Passing, Ground Duels), where the count would just be visual
clutter on an already-reliable number (matches the explicit "do not clutter high-volume
statistics unnecessarily" instruction).

## 9. Filtered-grain requirement -- already respected in this design

Every Layer-2 number in section 4 was computed separately for `top_opponents` and
`bottom_opponents`, never inherited from `full_season` -- confirmed structurally correct: e.g. a
player with 45 season dribble attempts but only 4 under Top Opponents would be evaluated at the
**4-attempt** Layer-2 tier for a Top-Opponents chart, never the 45-attempt one. This is a design
requirement to carry into implementation, not something requiring further testing here.

## 10. Raw/Per-90 Volume signals -- Layer 1 is the primary, sufficient mechanism

Reusing the sensitivity experiment's own bootstrap results (same 400 CBs): Tackles-per90 and
Dribble-Attempts-per90 standard deviation grows smoothly with LOWER MINUTES (0.51 at 270min ->
1.16 at 45min for tackles; 0.26 -> 0.61 for dribbles) -- i.e. Volume/per-90 signals are already
governed by Layer 1 (minutes), and degrade continuously with it, with no evidence of a SEPARATE
denominator effect distinct from minutes for these signals (unlike percentages, a per-90 rate
isn't bounded 0-100 and doesn't collapse to a coin-flip at a tiny numerator the way a % does -- 2
key passes in 92 minutes is a noisy estimate of the season rate, but it is not a MEANINGLESS
number the way "100% dribble success" from 1/1 is). **Conclusion: Layer 1 alone is adequate
protection for Volume/per-90 signals; Layer 2 is specifically a percentage/efficiency-signal
concern**, confirming the brief's own instinct not to assume identical treatment.

## 11-12. Connecting to explanation and chart selection (design, not implemented)

**Explanation engine** (`explanation_engine_v2.py`): the brief's proposed principle --
**Reliable enough to interpret -> Relevant -> Interesting/Extreme** -- maps onto the existing
`_collect_facts()` / `select()` pipeline as ONE ADDITIONAL GATE inserted before the existing
tier+interestingness sort: a fact whose Signal is a fragile-family percentage below the
Headline-eligible floor would be excluded from the strength/weakness candidate pool entirely
(never scored, never selected), exactly mirroring how `_tier()` already excludes
RESPONSIBILITY/SPECIALISATION signals today -- same mechanism, new gate. A 100th-percentile
"1/1" fact would never reach candidacy. This requires the explanation engine to have access to
each fact's underlying denominator, which today's full-season `signal_scores.parquet` does not
carry (only the derived percentile) -- **a real data-availability gap for a future implementation
to plan for**, flagged here rather than solved.

**Chart selection / X/Y charts**: recommend, for a Limited-tier point in any chart -- **remain
plotted, marked visually distinct (e.g. reduced opacity or a hollow marker), denominator shown in
hover, and excluded from any rank/percentile-based framing (dashed average lines stay
population-wide, unaffected) but INCLUDED in raw value comparison** -- "remain plotted but marked"
rather than "suppress" for Limited, reserving actual removal from the chart for the Insufficient
tier only. This preserves visual information (point 17) while being honest that the point carries
less weight than a Strong one, and specifically protects X/Y Volume-vs-Efficiency charts (section
12's named concern) from making a 1/1 look visually equivalent to a 40/61.

## 13. Scoring impact

None. Every number in this document was computed from already-exported analytical data (chart
metrics, match-level filter tables); nothing here touches `signal_scores.parquet`, `f50_scores.
csv`, `f50_registry.csv`, or any Style/Emphasis/weight definition. No scoring-methodology issue
was uncovered by this analysis (confirmed: the underlying concern is entirely about how filtered/
low-sample DESCRIPTIVE evidence is interpreted and displayed, not about how players are scored).

## 14. Proposed wording for each reliability state

- **Strong**: no extra wording -- current display stands.
- **Limited (Layer 1)**: e.g. *"Limited sample · 184 of 270 min vs Top Opponents"* -- names the
  actual minutes played, not just "insufficient," directly fixing the misleading "no match data
  available" wording for a player who clearly did play.
- **Limited (Layer 2, fragile-family %)**: e.g. *"67% Dribble Success · 4/6 -- based on a small
  number of attempts"*.
- **Insufficient (Layer 1)**: e.g. *"Not shown for Top Opponents · only 90 of the 270 minutes
  needed"* (this wording already shipped in round 5's fix and stays accurate under a tiered
  model, since it already states the real minutes rather than claiming "no data").
- **Insufficient (Layer 2)**: e.g. *"Dribble Success % not shown -- only 1 attempt recorded"*.

## 15. Real edge cases (all pulled from the actual production data, not constructed)

| Case | Real example | Layer 1 | Layer 2 |
|---|---|---|---|
| 0 Top/Bottom minutes | (confirmed to exist in round-4/5 audits: Rotman/top, Cohen/bottom) | Insufficient | N/A |
| Just below 270 | Steven Nzonzi, 267 min vs Top | Limited (A/B) | -- |
| Just above 270 | James Husband, 270 min vs Top | Strong | -- |
| Large minutes, tiny denominator | José Fonte, 397 min vs Top, 1/1 dribbles (100%) | Strong | Insufficient (1 attempt) -- the exact "misleadingly perfect %" case, 983 real players share this shape (>=270 min, <=2 dribble attempts) |
| Modest minutes, strong denominator | Celil Yüksel, 147 min vs Top, 10 tackles | Limited (A/B) / Strong (C) | Strong (10 attempts) -- proves Layer 1 and Layer 2 genuinely diverge, as the brief expected |
| 100% from 1/1 or 2/2 | José Fonte, Calum Chambers, Brendan Galloway, Jack Stephens (all 1/1 dribbles vs Top) | Strong | Insufficient |
| Weak % from tiny denominator | (any 0/1 or 0/2 case in the same pool) | varies | Insufficient |
| Top reliable, Bottom unreliable | Yonatan Cohen: 870 min vs Top (Strong), 68 min vs Bottom (Insufficient/A,B; Limited/C) | Diverges by filter | -- |

## 16. Scale of the Layer-2 problem

Directly from section 4's table: for the fragile families under a Top-Opponents filter, roughly
**33-69% of currently-computed observations sit below a 10-attempt denominator**, and 8.5-36.7%
below even 5 -- meaning a large share of today's Top/Bottom Dribble/Shooting/Crossing/Tackling
percentages, league ranks, and global percentiles are currently displayed with no reliability
signal at all, despite resting on single-digit samples. This is a structural issue affecting a
substantial minority-to-majority of filtered comparison-chart points for these specific Signal
families, not a rare edge case -- while Passing and Ground Duels are essentially unaffected at
any grain tested.

## 17. Show + qualify, not hide

The evidence supports **show + qualify** over **hide** wherever there is SOME real data: even a
1/1 dribble is a genuine fact (the raw count itself is never misleading), it is the PERCENTAGE
framing and any RANK claim built on it that becomes misleading. Recommend hiding only at the
Insufficient tier (Layer 1: essentially zero real minutes; Layer 2: 0-1 opportunities, where even
the raw count communicates almost nothing) -- everything above that should remain visible with
appropriate qualification, preserving directional information rather than discarding it.

## 18. Final architecture options

**Option 1 -- Conservative tiered (Layer 1: Architecture A / Layer 2: floor=5)**
- Layer 1: Strong>=270, Limited 180-269, Insufficient<180 (closest to today's number, smallest
  behavioural change).
- Layer 2: Displayable>=1, Headline+Rank-eligible>=5, applied only to the 4 fragile families
  (Tackling, Dribbling, Shooting/Conversion, Crossing); Aerial/Long-Range get the same floor at a
  lower urgency; Passing/Ground-Duels exempt.
- Coverage: Top 95.2% / Bottom 94.5% displayable (up from today's hard 89.5%/87.6%).
- Complexity: Moderate -- one new Layer-2 gate, reuses existing badge/note infrastructure from
  round 5.

**Option 2 -- Coverage-forward tiered (Layer 1: Architecture C / Layer 2: floor=5)**
- Layer 1: Strong>=180, Limited 90-179, Insufficient<90 -- takes the diminishing-returns point
  from the sensitivity experiment at face value and moves the whole scale down.
- Layer 2: same floor=5 fragile-family gate as Option 1.
- Coverage: Top 97.8% / Bottom 97.7% displayable -- best of the three.
- Trade-off: "Strong" now means what "Limited" meant under 270 -- a real redefinition of what the
  UI calls confident, not just a coverage change; rank stability at 180 min (rho ~0.66-0.73,
  section 6 of the prior doc) is meaningfully weaker than at 270 (~0.70-0.77) for the top tier.
- Complexity: Moderate, same as Option 1, but a bigger philosophical shift from today's number.

**Option 3 -- Full three-tier + eligibility split (Layer 1: Architecture B / Layer 2: full
Displayable/Headline/Rank split)**
- Layer 1: Strong>=270, Limited 135-269, Insufficient<135 -- keeps 270 as the confident anchor
  (least disruptive to existing user expectations) while recovering more of the Limited band than
  Option 1 (96.6%/96.1% displayable).
- Layer 2: the full three-way split from section 7 (Displayable/Headline-eligible/Rank-eligible
  as genuinely separate bars, not collapsed into one Layer-2 floor) -- most faithful to the
  brief's own section 7 distinction, but the most implementation work (three checks per fragile
  Signal instead of one).
- Complexity: Highest of the three -- most correct, most moving parts.

## 19. Recommendation

**Option 1 (Conservative tiered: Layer 1 Architecture A + Layer 2 floor=5, fragile families
only)**, with a note that Option 3's fuller Displayable/Headline/Rank split is the right longer-
term target once the explanation-engine data gap (section 11) is closed.

Reasoning against the four stated priorities:
1. **Football usefulness**: recovers 5.7-6.9pp of currently-hidden players (the Scottish CB /
   niche-search pain point) while keeping the Strong tier anchored at the number users already
   associate with confidence.
2. **Statistical honesty**: directly closes the biggest, most measurable gap found in this
   analysis (Layer 2 for fragile families, 30-70% thin at <10 attempts) rather than the smaller
   Layer 1 gap alone; Option 2's move to a 180-minute "Strong" would improve coverage further but
   at a real, measured stability cost (rho ~0.66-0.73 vs ~0.70-0.77) the brief did not ask to
   accept without discussion.
3. **Player coverage**: second-best of the three options, a real and meaningful improvement over
   today.
4. **UI simplicity**: a single Layer-2 floor (Option 1) is simpler to build and explain than
   Option 3's three separate eligibility checks, while still fixing the specific misleading cases
   this whole investigation started from (e.g. José Fonte's "100% Dribble Success").

This is a recommendation for review -- **no threshold, denominator rule, or UI text was changed
in production as part of this task**, per the explicit instruction.
