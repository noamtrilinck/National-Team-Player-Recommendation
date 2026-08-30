"""
UI/UX Round 3 (2026-08-30) -- profile-relevant chart selection + redundancy control.

Mirrors the explanation engine's 5-tier profile-relevance hierarchy (see
explanation_engine_v2.py and docs/v2_ui_redesign_round3.md section 2) for the "standout metrics"
charts, which draw from a DIFFERENT, older identifier space (CHART_METRICS/PCT_METRICS raw
match-level keys in data/build_dashboard_data.py) than the 54 Signal names the tier hierarchy is
built from. CHART_METRIC_DOMAIN is the disclosed, manual mapping bridging the two -- see
docs/v2_ui_redesign_round3.md section 4 for the full table and the confidence/rationale of each
entry. A chart metric with no defensible locked-domain match (clearances, fouls_drawn) is left
unmapped and always ranks at the lowest tier, regardless of its raw discriminative power -- this is
the direct fix for the round-3 reported bug (a peripheral metric like Fouls Drawn outranking core
profile metrics).
"""
from src.explanation_engine_v2 import DOMAIN_INFO, _relevant_signal_tiers, TIER_POSITION_QUALITY

CHART_METRIC_DOMAIN = {
    "touches": "Possession Involvement",
    "passes": "Possession Involvement",
    "accurate_passes": "Ball Progression -- Passing",
    "passes_in_final_third": "Ball Progression -- Passing",
    "accurate_passes_pct": "Ball Progression -- Passing",
    "key_passes": "Chance Creation",
    "big_chances_created": "Chance Creation",
    "assists": "Chance Creation",
    "total_crosses": "Wide Delivery / Crossing",
    "accurate_crosses": "Wide Delivery / Crossing",
    "shots_total": "Shooting",
    "shots_on_target": "Shooting",
    "goals": "Shooting",
    "dribble_attempts": "Dribbling / Take-Ons",
    "successful_dribbles": "Dribbling / Take-Ons",
    "tackles": "Tackling",
    "tackles_won": "Tackling",
    "tackles_won_pct": "Tackling",
    "interceptions": "Interceptions / Anticipation",
    "ball_recoveries": "Ball Recoveries",
    "aerials_won": "Physical Contests -- Aerial",
    "duels_won": "Physical Contests -- Ground",
    "long_balls": "Long-Range Distribution",
    "long_balls_won": "Long-Range Distribution",
    "long_balls_won_pct": "Long-Range Distribution",
    # "clearances" and "fouls_drawn" intentionally absent -- no defensible locked-domain match,
    # see docs/v2_ui_redesign_round3.md section 4.
}

UNMAPPED_TIER = TIER_POSITION_QUALITY  # unmapped metrics rank alongside generic Position Quality


def metric_relevance(metric, position, style, emphasis_list):
    """Returns (tier, group) for one chart metric under the selected profile. tier 1 = most
    central (an Emphasis-core Signal lives in this metric's mapped domain), tier 5 = generic or
    unmapped. group is the DOMAIN_INFO redundancy group (None for unmapped metrics)."""
    domain = CHART_METRIC_DOMAIN.get(metric)
    if domain is None or domain not in DOMAIN_INFO:
        return UNMAPPED_TIER, None
    sig_tiers = _relevant_signal_tiers(position, style, emphasis_list)
    best_tier = _best_tier_for_domain(domain, sig_tiers)
    return best_tier, DOMAIN_INFO[domain]["group"]


def _best_tier_for_domain(domain, sig_tiers):
    from src.explanation_engine_v2 import load_signal_catalog
    catalog = load_signal_catalog()
    best = UNMAPPED_TIER
    for (sig, safe), tier in sig_tiers.items():
        if sig in catalog.index and catalog.loc[sig, "domain"] == domain:
            best = min(best, tier)
    return best


# UI/UX Round 5 (points 8-15) -- genuine two-dimensional (X/Y) comparisons, built ONLY from
# domain pairs that already exist as separate CHART_METRICS/PCT_METRICS entries mapped to the
# SAME locked Signal domain (never an invented cross-domain relationship). Each pair puts a
# volume/attempt-style metric against a complementary outcome/execution-style metric from that
# same domain -- "who attempts a lot AND succeeds a lot" is a real, defensible football question,
# not a manufactured one. Domains with no second CHART_METRICS/PCT_METRICS entry (Aerial/Ground
# duels only ever export the "won" count, Interceptions/Ball Recoveries/Possession Involvement
# have no second metric at all) simply have no X/Y candidate and are never forced into one.
VOLUME_EXECUTION_PAIRS = {
    "Dribbling / Take-Ons": ("dribble_attempts", "successful_dribbles"),
    "Tackling": ("tackles", "tackles_won_pct"),
    "Long-Range Distribution": ("long_balls", "long_balls_won_pct"),
    "Wide Delivery / Crossing": ("total_crosses", "accurate_crosses"),
    "Ball Progression -- Passing": ("passes_in_final_third", "accurate_passes_pct"),
    "Shooting": ("shots_total", "goals"),
    "Chance Creation": ("key_passes", "big_chances_created"),
}


def select_priority_metrics(all_dm_ordered, position, style, emphasis_list, k=3):
    """Reorders/selects from an already discriminative-power-ordered metric list (from
    charts.differentiating_metrics(), unchanged/reused) by profile-relevance TIER FIRST,
    discriminative power second (stable sort preserves the incoming order within a tier) -- so a
    statistically-differentiating but peripheral metric can never outrank one genuinely tied to
    the selected Style/Emphasis (point 4). Applies a redundancy cap of one metric per DOMAIN_INFO
    group among the first `k` picks (point 6) -- a different, unmapped-domain metric may still
    fill a slot no relevant group can fill, but never crowds out a second slot in the same story.
    Returns (chosen, remainder) -- remainder preserves the original discriminative order for any
    'show more' pagination."""
    scored = [(m, *metric_relevance(m, position, style, emphasis_list)) for m in all_dm_ordered]
    scored.sort(key=lambda t: t[1])  # stable: ties keep original discriminative-power order

    chosen, used_groups, remainder = [], set(), []
    for m, tier, group in scored:
        if len(chosen) < k and (group is None or group not in used_groups):
            chosen.append(m)
            if group is not None:
                used_groups.add(group)
        else:
            remainder.append(m)
    return chosen, remainder


MIN_XY_SPREAD = 15.0  # percentile points -- point 14: both axes must show genuine separation
# among the CURRENT players or the pair is skipped entirely, never forced onto a flat/duplicate
# relationship. Kept in the same units as the existing differentiating_metrics() spread check.
MAX_XY_TIER = 3  # only offer an X/Y pair when its domain is at least Style-core relevant --
# never force a two-dimensional chart onto a profile with no real connection to it.


def _percentile_spread(chart_rows, mstats, metric, filter_key="full_season", value_col="percentile_value"):
    from src.charts import _metric_lookup, JOIN_KEY
    import pandas as pd
    keys_df = pd.DataFrame([{k: r[k] for k in JOIN_KEY} for r in chart_rows])
    lookup = _metric_lookup(mstats, keys_df, metric, filter_key, value_col)
    vals = [v for v in lookup.values() if pd.notna(v)]
    return (max(vals) - min(vals)) if len(vals) >= 2 else 0.0


def xy_candidate_for_profile(position, style, emphasis_list, chart_rows, mstats, exclude_group=None):
    """UI/UX Round 5 (points 9, 14) -- the single most profile-relevant VOLUME_EXECUTION_PAIRS
    domain (Tier<=3: at least Style-core relevant to the SELECTED profile, never an unrelated
    domain) that also shows genuine separation among the current players on BOTH axes. Returns
    None -- never a forced/invented relationship -- when no pair clears both bars."""
    sig_tiers = _relevant_signal_tiers(position, style, emphasis_list)
    candidates = []
    for domain, (mx, my) in VOLUME_EXECUTION_PAIRS.items():
        if domain not in DOMAIN_INFO:
            continue
        group = DOMAIN_INFO[domain]["group"]
        if exclude_group is not None and group == exclude_group:
            continue
        tier = _best_tier_for_domain(domain, sig_tiers)
        if tier <= MAX_XY_TIER:
            candidates.append((tier, domain, mx, my, group))
    candidates.sort(key=lambda t: t[0])
    for tier, domain, mx, my, group in candidates:
        if _percentile_spread(chart_rows, mstats, mx) >= MIN_XY_SPREAD and \
           _percentile_spread(chart_rows, mstats, my) >= MIN_XY_SPREAD:
            return dict(metric_x=mx, metric_y=my, domain=domain, tier=tier, group=group)
    return None


def select_five_charts(all_dm_ordered, position, style, emphasis_list, chart_rows, mstats, k=5):
    """UI/UX Round 5 (points 8-15) -- up to `k` profile-driven comparison charts with distinct
    analytical jobs, extending select_priority_metrics (unchanged: tier-first, redundancy-capped)
    with ONE slot upgraded to a genuine two-dimensional relationship (point 9) when a real,
    locked-domain-derived pair exists for this profile and shows real separation among the current
    players (point 14) -- never forced when no such pair qualifies. Redundancy control (point 13)
    covers the X/Y slot too: it never duplicates the single most central slot's own story, and
    preferentially replaces whichever single-metric slot already tells the same domain-group
    story rather than just appending a 6th chart. Returns (chart_specs, remainder): each spec is
    {'kind':'range','metric':...} or {'kind':'xy','metric_x':...,'metric_y':...,'domain':...}."""
    chosen, remainder = select_priority_metrics(all_dm_ordered, position, style, emphasis_list, k=k)
    specs = [dict(kind="range", metric=m) for m in chosen]
    if not specs:
        return specs, remainder

    exclude_group = metric_relevance(chosen[0], position, style, emphasis_list)[1]
    xy = xy_candidate_for_profile(position, style, emphasis_list, chart_rows, mstats, exclude_group=exclude_group)
    if xy:
        replace_idx = next((i for i, s in enumerate(specs) if i > 0 and
                             metric_relevance(s["metric"], position, style, emphasis_list)[1] == xy["group"]), None)
        if replace_idx is None and len(specs) == k:
            replace_idx = len(specs) - 1  # no same-story slot to swap -- displace the lowest-priority one
        xy_spec = dict(kind="xy", metric_x=xy["metric_x"], metric_y=xy["metric_y"], domain=xy["domain"])
        if replace_idx is not None:
            specs[replace_idx] = xy_spec
        elif len(specs) < k:
            specs.append(xy_spec)
    return specs, remainder


# UI/UX Round 5 -- LOCKED (2026-08-30) Top/Bottom-Opponents chart-metric eligibility allowlist.
# See dashboard/docs/v2_150min_and_signal_eligibility_decision.md section B for the full evidence
# (real denominator distributions + match-level bootstrap stability, per Signal, not by Domain
# name). Only `tackles_won_pct` currently exists as a chart-facing metric among the fragile
# EXECUTION Signals the lock identifies -- Dribble Success %, Shot Accuracy %, Goal Conversion %,
# Cross Accuracy %, xG per Shot, and xGOT per Shot on Target are locked ALL-MATCHES-ONLY too, but
# aren't (yet) exported as standalone CHART_METRICS/PCT_METRICS ratio columns, so this set is
# short by construction, not because those Signals were judged safe -- if a future export adds
# one of them as a chart metric, it inherits ALL-MATCHES-ONLY automatically (see the fallback
# note below). The two "currently unresolved" Signals from the lock (Big Chance Creation
# Conversion %, Key Pass Conversion %) are likewise not currently chart metrics; if added, treat
# them as ALL-MATCHES-ONLY (conservative default) until independently evidenced otherwise.
ALL_MATCHES_ONLY_METRICS = {"tackles_won_pct"}

# Names that, if ever exported as a chart metric, must default to ALL-MATCHES-ONLY per the lock
# even before this set is updated -- a safety net so a future metric addition can't silently
# inherit ELIGIBLE by omission. Matched by substring against the metric key.
_ALL_MATCHES_ONLY_NAME_HINTS = ("dribble_success", "shot_accuracy", "goal_conversion",
                                 "cross_accuracy", "xg_per_shot", "xgot_per_shot",
                                 "big_chance_creation_conversion", "key_pass_conversion")


def metric_top_bottom_eligible(metric):
    """UI/UX Round 5 LOCK -- whether one chart metric may offer Top/Bottom Opponents controls at
    all (independent of the 150-minute player-level floor, which still applies separately to
    every eligible metric). Volume/count metrics (the vast majority of CHART_METRICS) are
    eligible by default -- they're governed by minutes (Layer 1), not action-count, per the
    locked design doc's section 10 finding."""
    if metric in ALL_MATCHES_ONLY_METRICS:
        return False
    key = metric.lower()
    return not any(hint in key for hint in _ALL_MATCHES_ONLY_NAME_HINTS)


def spec_top_bottom_eligible(spec):
    """UI/UX Round 5 LOCK (point 3/19) -- a chart spec (range or X/Y) supports Top/Bottom only
    when EVERY metric it uses is eligible; for an X/Y chart this means BOTH axes, never mixing a
    filtered axis with a season-only one (point 3's explicit requirement)."""
    if spec["kind"] == "xy":
        return metric_top_bottom_eligible(spec["metric_x"]) and metric_top_bottom_eligible(spec["metric_y"])
    return metric_top_bottom_eligible(spec["metric"])


def xy_chart_title(domain):
    """UI/UX Round 5 (point 15) -- a question-oriented title derived from the domain's own
    already-locked, football-readable strength label (DOMAIN_INFO), not a hardcoded per-domain
    marketing-copy library -- the same short label used throughout the explanation engine."""
    strength = DOMAIN_INFO[domain]["strength"]
    return f"Who pairs {strength[0].lower() + strength[1:]} with the efficiency to back it up?"
