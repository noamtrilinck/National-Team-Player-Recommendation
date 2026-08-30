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
    rel = load_relevant_signals()
    sigs = set()
    pq = rel[(rel.kind == "position_quality") & (rel.position == position)]
    sigs |= set(zip(pq.signal_name, pq.safe_name))
    if style and style != "NoStyle":
        st_rows = rel[(rel.kind == "style") & (rel.position == position) & (rel.key == style)]
        sigs |= set(zip(st_rows.signal_name, st_rows.safe_name))
        recv_rows = rel[(rel.kind == "style_receiving") & (rel.position == position) & (rel.key == style)]
        sigs |= set(zip(recv_rows.signal_name, recv_rows.safe_name))
    for e in emphasis_list:
        e_rows = rel[(rel.kind == "emphasis") & (rel.position == position) & (rel.key == e)]
        sigs |= set(zip(e_rows.signal_name, e_rows.safe_name))
    return sigs


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


def _collect_facts(position, style, emphasis_list, row, league_pool, catalog):
    """Builds the full candidate-fact list for this player/profile, each carrying everything
    needed to score interestingness and render in any evidence format."""
    sig_pairs = relevant_signals_for(position, style, emphasis_list)
    facts = []
    for sig, safe in sig_pairs:
        if sig not in catalog.index:
            continue
        domain, info_type = catalog.loc[sig, "domain"], catalog.loc[sig, "info_type"]
        if _tier(sig, info_type) != "headline" or domain not in DOMAIN_INFO:
            continue
        pctile_col, raw_col = f"{safe}__percentile", f"{safe}__raw"
        if pctile_col not in row.index or pd.isna(row.get(pctile_col)) or pd.isna(row.get(raw_col)):
            continue
        global_pctile = float(row[pctile_col])
        raw = row[raw_col]
        league_rank, league_n = (None, None)
        if league_pool is not None:
            league_rank, league_n = _league_rank(raw, league_pool, raw_col)
        facts.append(dict(
            sig=sig, domain=domain, group=DOMAIN_INFO[domain]["group"],
            global_pctile=global_pctile, raw=raw,
            league_rank=league_rank, league_n=league_n,
            is_profile_signal=True,
        ))
    return facts


def _interestingness(fact, direction):
    """direction: +1 for strength candidates (want high pctile), -1 for weakness candidates (want
    low pctile). Combines extremeness and league-rank quality -- never picks purely by percentile."""
    gp = fact["global_pctile"]
    score = (gp - 50) * direction  # extremeness in the wanted direction
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


def _render_fact(fact, position, direction):
    sig, domain = fact["sig"], fact["domain"]
    headline = DOMAIN_INFO[domain]["strength" if direction > 0 else "weakness"]
    gp, raw = fact["global_pctile"], fact["raw"]
    league_rank, league_n = fact["league_rank"], fact["league_n"]
    pos_label = POSITION_LABEL.get(position, position)
    raw_evidence = _raw_phrase(sig, raw)
    intensity = _strength_language(gp, league_rank, league_n) if direction > 0 else _weakness_language(gp, league_rank, league_n)

    badges = []
    if league_rank is not None:
        badges.append(f"#{league_rank} of {league_n} in league")
    badges.append(f"{_ordinal(round(gp))} global percentile")

    # Vary the sentence: a genuinely notable league rank tells the best story; failing that, an
    # extreme global percentile; otherwise the raw stat stands on its own.
    if league_rank is not None and ((direction > 0 and league_rank <= max(3, round(0.2 * league_n)))
                                     or (direction < 0 and league_rank > league_n - max(3, round(0.2 * league_n)))):
        if direction > 0:
            qualifier = "one of the league's best" if intensity == "strong" else "among the better"
        else:
            qualifier = "one of the league's weaker" if intensity == "strong" else "below the league average among"
        body = f"{raw_evidence or sig.lower()} — {qualifier} eligible {pos_label}s in his league."
    elif direction > 0 and gp >= 95:
        body = f"{raw_evidence or sig.lower()} — inside the top {max(1, 100 - round(gp))}% of the full comparable population."
    elif direction < 0 and gp <= 5:
        body = f"{raw_evidence or sig.lower()} — inside the bottom {max(1, round(gp))}% of the full comparable population."
    else:
        body = f"{raw_evidence or sig.lower()}."

    return dict(headline=headline, body=body, badges=badges)


def build_explanation(player_id, season_name, position, style, emphasis_list,
                       n_strengths_max=4, n_weaknesses_max=3):
    """Returns dict(strengths=[{headline,body,badges}...], weaknesses=[...]). Selection is driven
    by interestingness (extremeness + league-rank quality), capped at one representative per
    redundancy group, football-readable Signals only (VOLUME/EXECUTION tier). Weaknesses are
    omitted, not manufactured, when nothing genuinely stands out."""
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

    def select(direction, cap):
        candidates = [f for f in facts if (f["global_pctile"] >= 60 if direction > 0 else f["global_pctile"] <= 40)]
        scored = sorted(((f, _interestingness(f, direction)) for f in candidates), key=lambda t: -t[1])
        chosen, used_groups = [], set()
        for f, _score in scored:
            if f["group"] in used_groups:
                continue
            chosen.append(f)
            used_groups.add(f["group"])
            if len(chosen) >= cap:
                break
        return chosen

    strengths = [_render_fact(f, position, 1) for f in select(1, n_strengths_max)]
    weaknesses = [_render_fact(f, position, -1) for f in select(-1, n_weaknesses_max)]
    return dict(strengths=strengths, weaknesses=weaknesses)
