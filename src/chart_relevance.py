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
