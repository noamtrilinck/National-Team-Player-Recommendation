"""
UI/UX Round 2 (2026-08-30) -- football scouting explanations, rewritten around "what is genuinely
interesting about this player" rather than "which Signals have the highest percentile."

Self-contained (see the Round-1-followup deployment fix): reads only dashboard/data/* -- no
production/ import, no absolute path, no sys.path modification anywhere in this module.

Design (see docs/v2_ui_redesign_round2.md for the full record):
  - Signals are tiered by how football-readable they are, from the already-locked (domain,
    info_type) taxonomy (signal_catalog.csv) -- VOLUME/EXECUTION are intuitive counts/rates/
    success %; RESPONSIBILITY (team-share) and SPECIALISATION (ratio-of-ratios) are internal/
    abstract and deprioritized; a small denylist removes the few VOLUME/EXECUTION signals that
    still read as internal ("Backward Passes per90").
  - Every candidate fact is scored for "interestingness" (extremeness, profile relevance, league-
    rank quality) rather than picked by percentile alone.
  - Facts are grouped into redundancy groups (e.g. Tackling/Interceptions/Ball Recoveries all
    compete as "the ball-winning story") so at most one representative per group is shown.
  - Evidence format (raw-stat / league-rank / global-context) is chosen per fact, not fixed --
    league rank is preferred when the player has a genuinely notable position in a real, validated
    comparison population (same league + same locked scoring position + the project's existing
    900-minute qualification floor + a minimum pool size); global percentile is kept as supporting
    evidence (a badge), not the headline sentence.
  - Language intensity (e.g. "one of the league's best" vs "among the better") is gated by how
    extreme the underlying rank/percentile actually is -- never asserted independent of the numbers.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

MIN_LEAGUE_POOL = 8  # same sample-size floor already used project-wide for league-relative stats

# VOLUME/EXECUTION info_types are the football-readable tier (counts, rates, success %); this
# denylist removes the few that are technically VOLUME/EXECUTION but don't read as a natural
# scouting fact on their own.
HEADLINE_DENYLIST = {"Backward Passes per90"}

# Domain -> headline phrasing + redundancy grouping. Only one Signal PER GROUP is ever shown as a
# strength (and separately, at most one per group as a weakness) -- stops "Tackles/90 + Tackle
# Share + Duel Volume" all being shown as three separate facts when they're really one story.
DOMAIN_INFO = {
    "Tackling":                     dict(group="ball_winning", strength="Ball-winning presence",       weakness="Light on defensive duels"),
    "Interceptions / Anticipation": dict(group="ball_winning", strength="Sharp reader of the game",     weakness="Rarely intercepts"),
    "Ball Recoveries":              dict(group="ball_winning", strength="High-volume ball-winner",      weakness="Low recovery numbers"),
    "Physical Contests -- Aerial":  dict(group="duels",        strength="Aerial threat",                weakness="Aerial concern"),
    "Physical Contests -- Ground":  dict(group="duels",        strength="Strong in ground duels",       weakness="Beaten in ground duels"),
    "Ball Progression -- Passing":  dict(group="progression",  strength="Progressive passer",           weakness="Limited progression"),
    "Long-Range Distribution":      dict(group="progression",  strength="Long-range threat",            weakness="Rarely plays long"),
    "Possession Involvement":       dict(group="progression",  strength="Heavily involved in possession", weakness="Peripheral in possession"),
    "Chance Creation":              dict(group="creativity",   strength="Creative influence",           weakness="Limited creativity"),
    "Wide Delivery / Crossing":     dict(group="creativity",   strength="Crossing threat",              weakness="Ineffective from wide areas"),
    "Dribbling / Take-Ons":         dict(group="dribbling",    strength="Ball-carrying threat",         weakness="Limited dribbler"),
    "Shooting":                     dict(group="shooting",     strength="Clinical in front of goal",    weakness="Wasteful in front of goal"),
    "Ball Retention & Security":    dict(group="retention",    strength="Secure in possession",         weakness="Prone to losing the ball"),
}

# UI/UX Round 4 (points 1-4) -- "football meaning" phrase library. NOT a rotating library of
# whole sentences: each entry translates what a DOMAIN literally measures into its football
# implication, split by info_type where the domain has both a VOLUME signal (how OFTEN/how MUCH)
# and an EXECUTION signal (how WELL/how EFFICIENTLY) -- these are genuinely different facts about
# the player, not synonyms of each other. A domain with only one usable info_type gets a single
# "general" phrase. Real variation in the rendered sentence comes from _comparison_clause()
# (which population -- league, global, or both -- actually makes THIS player's number meaningful)
# and _frame() (which real property of the fact -- tier, comparison type, combination -- decides
# what the sentence is trying to communicate), not from synonym-swapping this dict.
FOOTBALL_MEANING = {
    "Tackling": dict(
        volume="steps in to win the ball back through tackles on a regular basis",
        execution="wins the large majority of the tackles he actually commits to"),
    "Interceptions / Anticipation": dict(
        general="reads the game well enough to cut out opposition play before it develops"),
    "Ball Recoveries": dict(
        general="is a reliable source of turnovers, regularly winning the ball back for his team"),
    "Physical Contests -- Aerial": dict(
        volume="regularly competes for the ball in the air",
        execution="wins most of the aerial duels he actually contests"),
    "Physical Contests -- Ground": dict(
        volume="engages often in one-on-one physical duels",
        execution="comes out on top in most of his ground duels"),
    "Ball Progression -- Passing": dict(
        volume="regularly moves the ball into advanced areas with his passing",
        execution="keeps possession secure even when passing under pressure"),
    "Long-Range Distribution": dict(
        volume="offers a long-distribution outlet, switching play or going direct often",
        execution="picks out his long-range passes with real accuracy"),
    "Possession Involvement": dict(
        general="is heavily involved in his team's build-up, touching the ball often"),
    "Chance Creation": dict(
        volume="regularly finds teammates in positions to finish attacks",
        execution="converts a high share of his creative moments into genuine chances"),
    "Wide Delivery / Crossing": dict(
        volume="provides a consistent route to danger from wide areas",
        execution="delivers his crosses with real accuracy rather than just volume"),
    "Dribbling / Take-Ons": dict(
        volume="looks to beat his marker with the ball at his feet often",
        execution="can beat opponents efficiently rather than simply attempting lots of take-ons"),
    "Shooting": dict(
        volume="gets into shooting positions consistently",
        execution="can turn a relatively small number of opportunities into goals"),
    "Ball Retention & Security": dict(
        general="keeps the ball secure in possession"),
}

# UI/UX Round 4 (point 6) -- pairs of redundancy groups whose evidence, when BOTH are genuinely
# selected strengths for the same player, describe one connected football story rather than two
# isolated facts (e.g. carries the ball forward himself AND finishes the move he creates). Only
# fires on real, independently-selected evidence -- never invents a connection that isn't there.
COMBINE_CONNECTORS = {  # each fills "He {connector}" -- verb-first, no leading conjunction
    frozenset({"dribbling", "shooting"}): "also follows it up by finishing the move himself",
    frozenset({"progression", "creativity"}): "also looks to create the next chance once he's carried the ball forward",
    frozenset({"ball_winning", "duels"}): "also backs that up by winning his physical contests",
    frozenset({"creativity", "dribbling"}): "carries the ball into danger himself as well as creating it with his passing",
}

PHRASES = {
    "Passes in Final Third per90": "{v} passes into the final third per 90",
    "Accurate Passes %": "{v}% pass completion",
    "Tackles per90": "{v} tackles per 90",
    "Tackles Won %": "{v}% tackle success",
    "Interceptions per90": "{v} interceptions per 90",
    "Ball Recoveries per90": "{v} ball recoveries per 90",
    "Dribble Attempts per90": "{v} dribble attempts per 90",
    "Dribble Success %": "{v}% dribble success",
    "Long Balls per90": "{v} long balls per 90",
    "Long Balls Won %": "{v}% long-ball success",
    "Aerial Duel Attempts per90": "{v} aerial duels contested per 90",
    "Aerial Duel Success %": "{v}% aerial duel success",
    "Ground Duel Attempts per90": "{v} ground duels contested per 90",
    "Ground Duel Success % (reconstructed)": "{v}% ground-duel success",
    "Passes per90": "{v} passes per 90",
    "Shots Total per90": "{v} shots per 90",
    "Shot Accuracy %": "{v}% shot accuracy",
    "Goal Conversion %": "{v}% goal conversion",
    "xG per Shot": "{v} xG per shot",
    "xGOT per Shot on Target": "{v} xGOT per shot on target",
    "Total Crosses per90": "{v} crosses per 90",
    "Cross Accuracy %": "{v}% cross accuracy",
    "Big Chances Created per90": "{v} big chances created per 90",
    "Key Passes per90": "{v} key passes per 90",
    "Big Chance Creation Conversion %": "{v}% of his big chances created are converted",
    "Key Pass Conversion %": "{v}% of his key passes are converted",
}

POSITION_LABEL = {
    "CB": "centre back", "FB": "full back", "WM": "wide midfielder", "Winger": "winger",
    "DM": "defensive midfielder", "CM": "central midfielder", "AM": "attacking midfielder", "CF": "centre forward",
}


def _fmt(sig, raw):
    if pd.isna(raw):
        return None
    if "%" in sig:
        return f"{raw:.0f}"
    if "per Shot" in sig:
        return f"{raw:.2f}"
    return f"{raw:.1f}"


def _raw_phrase(sig, raw):
    tmpl = PHRASES.get(sig)
    v = _fmt(sig, raw)
    if v is None:
        return None
    if tmpl:
        return tmpl.format(v=v)
    return f"{v} for {sig.lower()}"


def _ordinal(n):
    n = int(round(n))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


@st.cache_data
def load_signal_scores():
    return pd.read_parquet(DATA_DIR / "signal_scores.parquet")


@st.cache_data
def load_relevant_signals():
    return pd.read_csv(DATA_DIR / "relevant_signals.csv")


@st.cache_data
def load_signal_catalog():
    return pd.read_csv(DATA_DIR / "signal_catalog.csv").set_index("signal_name")


@st.cache_data
def load_signal_denominators():
    """UI/UX Round 5 LOCK (2026-08-30) -- season-grain action counts behind the locked catalog's
    fragile EXECUTION Signals (see FRAGILE_SIGNAL_DENOMINATOR), sourced from
    data/signal_denominators.csv (built from the same real match-level data used throughout the
    Top/Bottom reliability research -- see docs/v2_two_layer_reliability_architecture_design.md
    section 11 and docs/v2_150min_and_signal_eligibility_decision.md). Closes the data-
    availability gap that doc flagged: signal_scores.parquet carries each fragile Signal's __raw
    VALUE (the percentage itself) but not the underlying attempt count needed to judge whether
    that percentage is interpretable."""
    return pd.read_csv(DATA_DIR / "signal_denominators.csv").set_index(["player_id", "season_name"])


# UI/UX Round 5 LOCK -- the fragile EXECUTION Signals identified by the reliability audit, and
# which column of signal_denominators.csv holds each one's real attempt count. xG per Shot and
# xGOT per Shot on Target share Shooting's shots_total_n (same denominator family as Shot
# Accuracy %/Goal Conversion %, confirmed in the design doc -- xGOT's true denominator, shots on
# target, is a subset of shots_total and was not separately exported, so shots_total_n is used as
# the (slightly more permissive) proxy, disclosed here rather than silently assumed exact).
FRAGILE_SIGNAL_DENOMINATOR = {
    "Tackles Won %": "tackles_n",
    "Dribble Success %": "dribble_attempts_n",
    "Shot Accuracy %": "shots_total_n",
    "Goal Conversion %": "shots_total_n",
    "xG per Shot": "shots_total_n",
    "xGOT per Shot on Target": "shots_total_n",
    "Cross Accuracy %": "total_crosses_n",
}
MIN_ATTEMPTS_FOR_INTERPRETATION = 5  # empirically validated floor (real match-level bootstrap,
# see the sensitivity experiment) -- below this, mean deviation from the "true" season value is
# 15-34 percentage points, i.e. closer to noise than to a descriptive fact.


@st.cache_data
def load_signal_scores_with_league():
    """Signal scores merged with each player-season's league_label from players.csv (display-only
    join -- league-relative ranks/percentiles computed from this are NEVER fed back into any
    score)."""
    players = pd.read_csv(DATA_DIR / "players.csv", usecols=["player_id", "season_name", "league_label"])
    return load_signal_scores().merge(players, on=["player_id", "season_name"], how="left")


def relevant_signals_for(position, style, emphasis_list):
    """Union of (signal_name, safe_name) pairs that matter for this exact profile -- Position
    Quality's own weighted Signals, the selected Style's core/supporting Signals, and every
    selected Emphasis's core/supporting Signals. Looked up from precomputed data, zero dependency
    on the production engine at runtime."""
    return set(_relevant_signal_tiers(position, style, emphasis_list).keys())


# UI/UX Round 3 -- the 5-tier profile-relevance hierarchy (docs/v2_ui_redesign_round3.md section 2).
# Tier 1 is the most specific/central to the SELECTED profile; tier 5 is generic Position Quality.
# A Signal relevant at more than one tier is ranked at its most specific (lowest-numbered) tier.
TIER_EMPHASIS_CORE = 1
TIER_EMPHASIS_SUPPORTING = 2
TIER_STYLE_CORE = 3
TIER_STYLE_SUPPORTING = 4
TIER_POSITION_QUALITY = 5

TIER_STORY = {
    TIER_EMPHASIS_CORE: "profile_driver",
    TIER_EMPHASIS_SUPPORTING: "combination",
    TIER_STYLE_CORE: "identity",
    TIER_STYLE_SUPPORTING: "supporting_trait",
    TIER_POSITION_QUALITY: "general",
}


def _relevant_signal_tiers(position, style, emphasis_list):
    """(signal_name, safe_name) -> tier (1-5), derived only from relevant_signals.csv's kind/role
    columns -- which are themselves exported directly from meta.STYLE/meta.EMPHASIS's own
    core/supporting dicts (see build_dashboard_data_v2.py). No invented Signal/profile
    relationship: every tier assignment traces back to the same dicts the scoring engine reads."""
    rel = load_relevant_signals()
    tiers = {}

    def _apply(rows, tier):
        for sig, safe in zip(rows.signal_name, rows.safe_name):
            key = (sig, safe)
            if key not in tiers or tier < tiers[key]:
                tiers[key] = tier

    pq = rel[(rel.kind == "position_quality") & (rel.position == position)]
    _apply(pq, TIER_POSITION_QUALITY)

    if style and style != "NoStyle":
        st_rows = rel[(rel.kind == "style") & (rel.position == position) & (rel.key == style)]
        _apply(st_rows[st_rows.role == "core"], TIER_STYLE_CORE)
        _apply(st_rows[st_rows.role == "supporting"], TIER_STYLE_SUPPORTING)
        recv_rows = rel[(rel.kind == "style_receiving") & (rel.position == position) & (rel.key == style)]
        _apply(recv_rows, TIER_STYLE_CORE)

    for e in emphasis_list:
        e_rows = rel[(rel.kind == "emphasis") & (rel.position == position) & (rel.key == e)]
        _apply(e_rows[e_rows.role == "core"], TIER_EMPHASIS_CORE)
        _apply(e_rows[e_rows.role == "supporting"], TIER_EMPHASIS_SUPPORTING)

    return tiers


def _league_rank(raw, league_pool, raw_col):
    """VALIDATED league-relative rank: same league + same locked scoring position (both already
    enforced by how league_pool is built by the caller) + the project's existing 900-minute
    qualification floor (inherited automatically -- every row in signal_scores.parquet already
    meets it) + a minimum comparison-pool-size floor (MIN_LEAGUE_POOL). Higher raw value = better
    rank for every Signal reachable here (VOLUME/EXECUTION tier only, see _tier() -- RESPONSIBILITY/
    SPECIALISATION signals with ambiguous direction are never selected as headline facts, so no
    direction inversion is needed here). Ties share the same (best) rank ("competition ranking")."""
    vals = league_pool[raw_col].dropna()
    n = len(vals)
    if n < MIN_LEAGUE_POOL or pd.isna(raw):
        return None, None
    rank = int((vals > raw).sum() + 1)  # 1-indexed, ties share the better rank
    return rank, n


def _tier(sig, info_type):
    if sig in HEADLINE_DENYLIST:
        return "obscure"
    return "headline" if info_type in ("VOLUME", "EXECUTION") else "obscure"


def _fragile_denominator(sig, player_id, season_name, denom_table):
    """UI/UX Round 5 LOCK -- returns the real attempt count behind a fragile EXECUTION Signal for
    this player, or None if `sig` isn't one of the fragile Signals (i.e. no guard applies)."""
    col = FRAGILE_SIGNAL_DENOMINATOR.get(sig)
    if col is None:
        return None
    try:
        val = denom_table.loc[(player_id, season_name), col]
    except KeyError:
        return 0
    if isinstance(val, pd.Series):  # duplicate index rows -- take the first, shouldn't occur
        val = val.iloc[0]
    return 0 if pd.isna(val) else int(val)


def _collect_facts(position, style, emphasis_list, row, league_pool, catalog):
    """Builds the full candidate-fact list for this player/profile, each carrying everything
    needed to score profile-relevance tier, interestingness, and render in any evidence format.

    UI/UX Round 5 LOCK (points 10-13) -- a fragile EXECUTION Signal (FRAGILE_SIGNAL_DENOMINATOR)
    below MIN_ATTEMPTS_FOR_INTERPRETATION real attempts is EXCLUDED from candidacy entirely here
    -- it can never become a headline strength/weakness, a league-rank claim, or a global-
    percentile claim, exactly mirroring how RESPONSIBILITY/SPECIALISATION Signals are already
    excluded by _tier() (same mechanism, evidence-based rather than architectural this time).
    This governs INTERPRETATION only, never scoring -- signal_scores.parquet and the locked Final
    Score/Style/Emphasis values are never touched by this guard."""
    sig_tiers = _relevant_signal_tiers(position, style, emphasis_list)
    denom_table = load_signal_denominators()
    player_id, season_name = row.get("player_id"), row.get("season_name")
    facts = []
    for (sig, safe), tier in sig_tiers.items():
        if sig not in catalog.index:
            continue
        domain, info_type = catalog.loc[sig, "domain"], catalog.loc[sig, "info_type"]
        if _tier(sig, info_type) != "headline" or domain not in DOMAIN_INFO:
            continue
        denom = _fragile_denominator(sig, player_id, season_name, denom_table)
        if denom is not None and denom < MIN_ATTEMPTS_FOR_INTERPRETATION:
            continue  # fragile Signal, too few real attempts to interpret -- excluded from candidacy
        pctile_col, raw_col = f"{safe}__percentile", f"{safe}__raw"
        if pctile_col not in row.index or pd.isna(row.get(pctile_col)) or pd.isna(row.get(raw_col)):
            continue
        global_pctile = float(row[pctile_col])
        raw = row[raw_col]
        league_rank, league_n = (None, None)
        if league_pool is not None:
            league_rank, league_n = _league_rank(raw, league_pool, raw_col)
        facts.append(dict(
            sig=sig, domain=domain, group=DOMAIN_INFO[domain]["group"], info_type=info_type,
            global_pctile=global_pctile, raw=raw,
            league_rank=league_rank, league_n=league_n,
            is_profile_signal=True, tier=tier, story=TIER_STORY[tier],
        ))
    return facts


def _interestingness(fact, direction):
    """direction: +1 for strength candidates (want high pctile), -1 for weakness candidates (want
    low pctile). Combines extremeness and league-rank quality -- never picks purely by percentile.
    UI/UX Round 4 (point 4): a small, disclosed EXECUTION bonus stops selection drifting toward
    Volume signals purely because raw counts tend to spread out (and so score as more "extreme")
    -- an efficiency/success-rate Signal answering "how WELL" competes on a more even footing with
    a count answering "how OFTEN". This never overrides tier (relevance still decides first)."""
    gp = fact["global_pctile"]
    score = (gp - 50) * direction  # extremeness in the wanted direction
    if fact.get("info_type") == "EXECUTION":
        score += 6
    if fact["league_rank"] is not None:
        n = fact["league_n"]
        frac = fact["league_rank"] / n
        if direction > 0 and frac <= 0.34:
            score += (0.34 - frac) * 60  # a clean top-third league rank is compelling on its own
        elif direction < 0 and frac >= 0.66:
            score += (frac - 0.66) * 60
    return score


def _strength_language(gp, league_rank, league_n):
    return "strong" if (gp >= 90 or (league_rank is not None and league_n and league_rank <= max(1, round(0.1 * league_n)))) else "moderate"


def _weakness_language(gp, league_rank, league_n):
    return "strong" if (gp <= 10 or (league_rank is not None and league_n and league_rank > league_n - max(1, round(0.1 * league_n)))) else "moderate"


# UI/UX Round 4 (points 1-2) -- decide which comparison population actually makes this fact
# meaningful. League rank and global percentile are both real, already-validated evidence; using
# whichever is genuinely more informative (rather than always leaning on league rank) is what lets
# "only #8 in a strong league but 96th percentile globally" read as the interesting fact it is.
def _comparison_informativeness(fact, direction):
    gp = fact["global_pctile"]
    global_info = abs(gp - 50) / 50.0  # 0 (no signal) .. 1 (maximally extreme)
    league_info, league_frac = 0.0, None
    if fact["league_rank"] is not None and fact["league_n"]:
        league_frac = fact["league_rank"] / fact["league_n"]
        league_info = (1 - league_frac) if direction > 0 else league_frac
    return global_info, league_info, league_frac


def _comparison_clause(fact, position, direction, intensity):
    """Returns a clause naming whichever population(s) make this fact meaningful -- league,
    global, or both when they're close enough that either alone would undersell the evidence."""
    pos_label = POSITION_LABEL.get(position, position)
    gp = fact["global_pctile"]
    global_info, league_info, league_frac = _comparison_informativeness(fact, direction)
    has_league = fact["league_rank"] is not None
    both_meaningful = has_league and abs(global_info - league_info) < 0.15 and max(global_info, league_info) >= 0.3

    if direction > 0:
        league_phrase = ("one of the league's best" if intensity == "strong" else "among the better") + f" eligible {pos_label}s in his league"
        global_phrase = (f"inside the top {max(1, 100 - round(gp))}% of the full eligible population"
                          if gp >= 90 else f"in the {_ordinal(round(gp))} percentile of the full eligible population")
    else:
        league_phrase = ("one of the league's weaker" if intensity == "strong" else "below the league average among") + f" eligible {pos_label}s"
        global_phrase = (f"inside the bottom {max(1, round(gp))}% of the full eligible population"
                          if gp <= 10 else f"in only the {_ordinal(round(gp))} percentile of the full eligible population")

    if both_meaningful:
        return f"{league_phrase}, and {global_phrase.replace('inside the', 'inside').replace('in the', 'also in the')}"
    if has_league and league_info >= global_info:
        return league_phrase
    if global_info > 0.15:
        return global_phrase
    return None  # neither population is genuinely informative -- the raw stat stands alone


# UI/UX Round 4 (point 7) -- which real property of the fact decides what the sentence is trying
# to communicate, tied to actual data (tier, which comparison drove it, whether it was combined
# with another signal) rather than a fixed rotation of openers for the same idea.
_SUPPORTING_TRAIT_FRAMES = {
    "ball_winning": "a useful extra layer to his defensive game, even outside the core profile",
    "duels": "an added physical dimension, though not what defines this profile",
    "progression": "another way he can move the team up the pitch, alongside the core profile",
    "creativity": "a further creative outlet, on top of what defines this profile",
    "dribbling": "an extra way he can beat a man, though not the core of this profile",
    "shooting": "an additional attacking route, separate from what defines this profile",
    "retention": "a further layer of security on the ball, alongside the core profile",
}


def _frame(fact, profile_label, style_label, comparison_used_global):
    tier, story = fact["tier"], fact.get("story")
    if story == "profile_driver":
        return f"a core part of what makes him fit {profile_label}" if not comparison_used_global \
            else f"a core part of his {profile_label} profile, and rare enough to stand out across the whole database"
    if story == "combination":
        return f"another real contributor to his {profile_label} profile"
    if story == "identity":
        return f"part of his identity as a {style_label} player"
    if story == "supporting_trait":
        return _SUPPORTING_TRAIT_FRAMES.get(fact["group"], "a useful additional trait, even if it isn't central to the profile")
    return None  # tier 5 / Position Quality -- no profile-specific frame, implication stands alone


def _render_fact(fact, position, direction, profile_label=None, style_label=None):
    """UI/UX Round 4 (points 1-2-7): the football IMPLICATION of the Signal leads the sentence
    (what the player can actually do, causality-guarded to what the domain literally measures);
    the evidence (raw stat + whichever comparison population is genuinely informative) backs it
    up; a tier-driven frame clause -- built from real data, not a fixed rotation -- says what the
    fact is doing in the story. Badges keep carrying the exact numbers regardless of which
    comparison the prose leans on."""
    sig, domain = fact["sig"], fact["domain"]
    headline = DOMAIN_INFO[domain]["strength" if direction > 0 else "weakness"]
    gp, raw = fact["global_pctile"], fact["raw"]
    league_rank, league_n = fact["league_rank"], fact["league_n"]
    raw_evidence = _raw_phrase(sig, raw)
    intensity = _strength_language(gp, league_rank, league_n) if direction > 0 else _weakness_language(gp, league_rank, league_n)

    global_info, league_info, _ = _comparison_informativeness(fact, direction)
    comparison_used_global = global_info > league_info
    comparison = _comparison_clause(fact, position, direction, intensity)

    if direction > 0:
        # Football-meaning implication only for STRENGTHS: FOOTBALL_MEANING phrases are written
        # as positive capability statements ("wins most of his duels"), so reusing them for a
        # WEAKNESS fact would assert the opposite of what the data shows -- exactly the causality
        # risk the brief warns about. Weaknesses stay evidence-only (below), never a capability claim.
        meaning = FOOTBALL_MEANING.get(domain, {})
        info_type = fact.get("info_type")
        implication = (meaning.get("execution") if info_type == "EXECUTION" else meaning.get("volume")) or meaning.get("general")
        if implication:
            implication_sentence = implication[0].upper() + implication[1:] + "."
            evidence_clause = f" {raw_evidence} —" if raw_evidence else ""
            body = f"{implication_sentence}{evidence_clause} {comparison}." if comparison else f"{implication_sentence}{(' ' + raw_evidence + '.') if raw_evidence else ''}"
        else:  # domain with no library entry (should not occur for the 13 locked domains, kept as a safe fallback)
            body = f"{raw_evidence or sig.lower()}" + (f" — {comparison}." if comparison else ".")
    else:
        body = f"{raw_evidence or sig.lower()}" + (f" — {comparison}." if comparison else ".")

    if direction > 0 and profile_label and style_label:
        frame = _frame(fact, profile_label, style_label, comparison_used_global)
        if frame:
            body = f"{body} This is {frame}."

    badges = _badges_for(fact, label=None)
    return dict(headline=headline, body=body, badges=badges)


def _badges_for(fact, label=None):
    """UI/UX Round 5 (point 1) -- builds a fact's rank/percentile badges. `label` is required
    whenever a badge could otherwise be ambiguous about which Signal it belongs to (i.e. whenever
    more than one Signal's evidence appears together, as in a combined bullet) -- every numerical
    badge must have an unambiguous semantic owner. A standalone single-Signal bullet's own
    headline already establishes ownership, so `label` stays None there."""
    gp = fact["global_pctile"]
    league_rank, league_n = fact["league_rank"], fact["league_n"]
    prefix = f"{label}: " if label else ""
    badges = []
    if league_rank is not None:
        badges.append(f"{prefix}#{league_rank} of {league_n} in league")
    badges.append(f"{prefix}{_ordinal(round(gp))} global percentile")
    return badges


def _combine_top_strengths(chosen, position, profile_label, style_label):
    """UI/UX Round 4 (point 6) -- if the two most relevant selected strengths belong to a pair of
    groups with a real, disclosed football connection (COMBINE_CONNECTORS), merge them into one
    combined story bullet instead of two isolated facts. Only ever combines facts that were
    ALREADY independently selected as genuine evidence -- never invents a connection. Returns
    (rendered_list, facts_actually_used) so the caller can track which facts were consumed.

    UI/UX Round 5 (point 1) -- FIX: once two Signals share one combined bullet, every badge from
    BOTH Signals is now explicitly labeled with which Signal it belongs to (previously only the
    second Signal's badge got a label -- or none at all -- so e.g. two league-rank badges under
    one headline were genuinely ambiguous about which Signal each ranked, exactly as reported)."""
    if len(chosen) < 2:
        return None
    a, b = chosen[0], chosen[1]
    key = frozenset({a["group"], b["group"]})
    connector = COMBINE_CONNECTORS.get(key)
    if not connector:
        return None
    label_a, label_b = DOMAIN_INFO[a["domain"]]["strength"], DOMAIN_INFO[b["domain"]]["strength"]
    fact_a = _render_fact(a, position, 1, profile_label, style_label)
    meaning_b = FOOTBALL_MEANING.get(b["domain"], {})
    implication_b = (meaning_b.get("execution") if b.get("info_type") == "EXECUTION" else meaning_b.get("volume")) or meaning_b.get("general") or b["domain"].lower()
    combined_headline = f'{label_a} + {label_b}'
    combined_body = f'{fact_a["body"]} He {connector} — {implication_b}.'
    combined_badges = _badges_for(a, label_a) + _badges_for(b, label_b)
    return dict(headline=combined_headline, body=combined_body, badges=combined_badges), [a, b]


def _profile_label(style, emphasis_list):
    style_label = "Any Style" if style == "NoStyle" else style
    if emphasis_list:
        return f"{style_label} / {' + '.join(emphasis_list)}", style_label
    return f"{style_label} / Generic", style_label


def build_explanation(player_id, season_name, position, style, emphasis_list,
                       n_strengths_max=4, n_weaknesses_max=3):
    """Returns dict(strengths=[{headline,body,badges}...], weaknesses=[...]). UI/UX Round 3:
    selection is now PRIMARILY driven by profile-relevance tier (Emphasis core > Emphasis
    supporting > Style core > Style supporting > Position Quality only -- see
    docs/v2_ui_redesign_round3.md section 2), with interestingness (extremeness + league-rank
    quality) breaking ties within a tier -- i.e. "why did this player score highly specifically in
    the selected Style + Emphasis" rather than "what is this player statistically good at."
    Still capped at one representative per redundancy group, football-readable Signals only
    (VOLUME/EXECUTION tier). Weaknesses are omitted, not manufactured, when nothing genuinely
    stands out, and keep the plain (non-story) rendering used since round 2."""
    df = load_signal_scores_with_league()
    catalog = load_signal_catalog()
    row_df = df[(df.player_id == player_id) & (df.season_name == season_name)]
    if row_df.empty:
        return dict(strengths=[], weaknesses=[])
    row = row_df.iloc[0]
    league_label = row.get("league_label")
    pos_pool = df[df.reference_position_group == position]
    league_pool = pos_pool[pos_pool.league_label == league_label] if pd.notna(league_label) else None

    facts = _collect_facts(position, style, emphasis_list, row, league_pool, catalog)
    profile_label, style_label = _profile_label(style, emphasis_list)

    def select(direction, cap):
        candidates = [f for f in facts if (f["global_pctile"] >= 60 if direction > 0 else f["global_pctile"] <= 40)]
        # Primary sort: profile-relevance tier (lower = more central to the SELECTED profile).
        # Secondary: interestingness, within that tier only -- general interestingness decides
        # between similarly-relevant candidates, it never lets a peripheral Signal (higher tier
        # number) outrank one genuinely tied to the selected Style/Emphasis.
        scored = sorted(((f, _interestingness(f, direction)) for f in candidates),
                         key=lambda t: (t[0]["tier"], -t[1]))
        chosen, used_groups = [], set()
        for f, _score in scored:
            if f["group"] in used_groups:
                continue
            chosen.append(f)
            used_groups.add(f["group"])
            if len(chosen) >= cap:
                break
        return chosen

    chosen_strengths = select(1, n_strengths_max)
    # UI/UX Round 4 (point 6): try combining the two most relevant strengths into one connected
    # football story before rendering the rest individually -- see _combine_top_strengths.
    combined = _combine_top_strengths(chosen_strengths, position, profile_label, style_label)
    if combined:
        combined_bullet, used_facts = combined
        remaining = [f for f in chosen_strengths if f not in used_facts]
        strengths = [combined_bullet] + [_render_fact(f, position, 1, profile_label, style_label) for f in remaining]
    else:
        strengths = [_render_fact(f, position, 1, profile_label, style_label) for f in chosen_strengths]
    weaknesses = [_render_fact(f, position, -1) for f in select(-1, n_weaknesses_max)]
    return dict(strengths=strengths, weaknesses=weaknesses, facts=facts, profile_label=profile_label, style_label=style_label)


def build_why_fits(position, style, emphasis_list, facts, profile_label, style_label,
                    current_final_score, alternatives, meaningful_gap=3.0):
    """UI/UX Round 3 (point 2) -- 'Why He Fits [Emphasis]', distinct from 'Why He Stands Out':
    scoped ONLY to Tier 1 (Emphasis core) and Tier 2 (Emphasis supporting) evidence -- the Signals
    the locked EMPHASIS definition itself ties to this exact role, not the player's general
    strengths. Uses the player's own real, existing same-Style/other-Emphasis combos (never
    averaged/synthetic -- search_engine_v2.emphasis_alternatives) only to decide WHETHER the
    selected Emphasis is a genuine standout worth framing that way; a small/no gap suppresses the
    leader framing rather than forcing a comparison that isn't really there (per the explicit
    instruction not to force comparisons with no meaningful distinction). Returns None when there
    isn't enough genuine Emphasis-specific evidence to tell a distinct story from 'Why He Stands
    Out' -- never manufactured."""
    if style == "NoStyle" or not emphasis_list:
        return None
    candidates = [f for f in facts if f["tier"] <= 2 and f["global_pctile"] >= 55]
    scored = sorted(((f, _interestingness(f, 1)) for f in candidates), key=lambda t: (t[0]["tier"], -t[1]))
    chosen, used_groups = [], set()
    for f, _score in scored:
        if f["group"] in used_groups:
            continue
        chosen.append(f)
        used_groups.add(f["group"])
        if len(chosen) >= 3:
            break
    if len(chosen) < 2:
        return None

    gap = None
    if alternatives:
        best_alt = max(a["final_score"] for a in alternatives)
        gap = current_final_score - best_alt
    is_clear_leader = gap is not None and gap >= meaningful_gap

    intro = None
    if is_clear_leader:
        intro = f"His clearest use of {style_label} football — {gap:.1f} points clear of his next-best Role Emphasis in this Style."

    bullets = [dict(label=DOMAIN_INFO[f["domain"]]["strength"], **_render_fact(f, position, 1)) for f in chosen]
    return dict(title=f"Why he fits {profile_label}", intro=intro, bullets=bullets, is_clear_leader=is_clear_leader)
