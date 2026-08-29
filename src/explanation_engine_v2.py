"""
UI/UX Round 1 (2026-08-30) -- football scouting explanations from real Signal data.

Explicitly NOT a model-engineering explanation ("Signal X contributed Y% to the Final Score") --
see docs/v2_ui_redesign_round1.md. Builds a short strengths/weaknesses summary from the player's
actual underlying Signal values, using three kinds of evidence (global percentile, league-relative
percentile, raw stat), choosing whichever tells the story best rather than repeating all three for
every fact. League-relative percentile is DISPLAY ONLY -- never fed back into any score.

Data source: production/player_evaluation_v2/results/PRODUCTION_signal_scores.parquet, which
already carries `{signal}__percentile` (position-relative, i.e. the "global percentile" this
module reports) and `{signal}__raw` for all 54 Signals -- these are read as-is, never recomputed.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

V2_ENGINE = Path(r"C:\Users\נועם\Desktop\Football Data\Projects\National Team Selection\production\player_evaluation_v2\engine")
V2_RESULTS = Path(r"C:\Users\נועם\Desktop\Football Data\Projects\National Team Selection\production\player_evaluation_v2\results")
if str(V2_ENGINE) not in sys.path:
    sys.path.insert(0, str(V2_ENGINE))
import signal_meta as meta  # noqa: E402
import decomposed_engine as de  # noqa: E402

# ---------------- football-readable phrase templates ----------------
# {v} = raw value already formatted by the caller. Only signals actually reachable by some
# position's Position-Quality/Style/Emphasis weighting need an entry; a generic fallback covers
# the rest so nothing ever renders blank.
PHRASES = {
    "Passes in Final Third per90": "plays {v} passes in the final third per 90",
    "Accurate Passes %": "completes {v}% of his passes",
    "Final Third Pass Share": "is responsible for {v}% of his team's final-third passes while on the pitch",
    "Backward Passes per90": "plays {v} backward passes per 90",
    "Backward Pass Rate": "plays backward {v}% of the time when passing",
    "Backward Pass Share": "accounts for {v}% of his team's backward passes",
    "Tackles per90": "makes {v} tackles per 90",
    "Tackles Won %": "wins {v}% of his tackles",
    "Tackle Share": "makes {v}% of his team's tackles while on the pitch",
    "Interceptions per90": "makes {v} interceptions per 90",
    "Interception Share": "accounts for {v}% of his team's interceptions",
    "Ball Recoveries per90": "makes {v} ball recoveries per 90",
    "Ball Recovery Share": "accounts for {v}% of his team's ball recoveries",
    "Dribble Attempts per90": "attempts {v} dribbles per 90",
    "Dribble Rate": "attempts a dribble on {v}% of his touches",
    "Dribble Success %": "completes {v}% of his dribbles",
    "Dribble Attempt Share": "accounts for {v}% of his team's dribble attempts",
    "Long Balls per90": "plays {v} long balls per 90",
    "Long Ball Rate": "plays long {v}% of the time when passing",
    "Long Balls Won %": "sees {v}% of his long balls reach a teammate",
    "Long Ball Share": "accounts for {v}% of his team's long balls",
    "Aerial Duel Attempts per90": "contests {v} aerial duels per 90",
    "Aerial Duel Success %": "wins {v}% of his aerial duels",
    "Aerial Duel Share": "accounts for {v}% of his team's aerial duels",
    "Ground Duel Attempts per90": "contests {v} ground duels per 90",
    "Ground Duel Success % (reconstructed)": "wins {v}% of his ground duels",
    "Ground Duel Attempt Share": "accounts for {v}% of his team's ground duels",
    "Passes per90": "plays {v} passes per 90",
    "Pass Share": "accounts for {v}% of his team's passes while on the pitch",
    "Shots Total per90": "takes {v} shots per 90",
    "Shot Rate": "shoots on {v}% of his touches in range",
    "Shot Accuracy %": "puts {v}% of his shots on target",
    "Goal Conversion %": "converts {v}% of his shots into goals",
    "xG per Shot": "averages {v} xG per shot",
    "xGOT per Shot on Target": "averages {v} xGOT per shot on target",
    "Shot Share": "accounts for {v}% of his team's shots",
    "Total Crosses per90": "delivers {v} crosses per 90",
    "Cross Rate": "crosses on {v}% of his touches in wide areas",
    "Cross Accuracy %": "completes {v}% of his crosses",
    "Cross Share": "accounts for {v}% of his team's crosses",
    "Final Third Pass Rate": "plays into the final third {v}% of the time when passing",
    "Progressive Passing Preference": "favours progressive passing {v}% of the time",
    "Big Chances Created per90": "creates {v} big chances per 90",
    "Key Passes per90": "plays {v} key passes per 90",
    "Big Chance Creation Conversion %": "sees {v}% of his big chances created converted",
    "Key Pass Conversion %": "sees {v}% of his key passes converted",
    "Big Chance Created Share": "accounts for {v}% of his team's big chances created",
    "Key Pass Share": "accounts for {v}% of his team's key passes",
}


def _ordinal(n):
    n = int(round(n))
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _fmt(sig, raw):
    if pd.isna(raw):
        return None
    if "%" in sig or "Rate" in sig or "Share" in sig or "Preference" in sig:
        return f"{raw:.0f}"
    if "per Shot" in sig:
        return f"{raw:.2f}"
    return f"{raw:.1f}"


def phrase_for(sig, raw):
    tmpl = PHRASES.get(sig)
    v = _fmt(sig, raw)
    if v is None:
        return None
    if tmpl:
        return tmpl.format(v=v)
    return f"registers {v} for {sig.lower()}"


@st.cache_data
def load_signal_scores():
    return pd.read_parquet(V2_RESULTS / "PRODUCTION_signal_scores.parquet")


@st.cache_data
def load_signal_scores_with_league():
    """Signal scores merged with each player-season's league_label from players.csv (display-only
    join -- league-relative percentiles computed from this are NEVER fed back into any score)."""
    from pathlib import Path
    players = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "players.csv",
                           usecols=["player_id", "season_name", "league_label"])
    df = load_signal_scores().merge(players, on=["player_id", "season_name"], how="left")
    return df


def relevant_signals_for(position, style, emphasis_list):
    """Union of Signals that actually matter for this exact profile: Position Quality's own
    weighted Signals for this position, plus the selected Style's core/supporting Signals, plus
    every selected Emphasis's core/supporting Signals. This is what makes the explanation specific
    to the profile being viewed, not a generic dump of all 54 Signals."""
    sigs = set(s for s, w in de.position_quality_weights(position).items() if w > 0)
    if style and style != "NoStyle":
        st_def = meta.STYLE[style]
        sigs |= set(st_def["core"]) | set(st_def.get("supporting", []))
        if style == "Direct" and position in meta.DIRECT_RECEIVING_POSITIONS:
            sigs |= set(st_def.get("core_receiving", []))
    for e in emphasis_list:
        key = (position, e)
        if key in meta.EMPHASIS:
            sigs |= set(meta.EMPHASIS[key]["core"]) | set(meta.EMPHASIS[key].get("supporting", []))
    return sigs


def build_explanation(player_id, season_name, position, style, emphasis_list,
                       n_strengths=3, n_weaknesses=2):
    """Returns dict(strengths=[str,...], weaknesses=[str,...]) -- football-readable sentences,
    each choosing global percentile / league-relative percentile / raw value, whichever tells the
    story best. Never repeats the same fact three ways. Weaknesses are omitted (not manufactured)
    when nothing is genuinely weak; likewise not every high percentile is described -- only the
    most informative facts are selected."""
    df = load_signal_scores_with_league()
    row = df[(df.player_id == player_id) & (df.season_name == season_name)]
    if row.empty:
        return dict(strengths=[], weaknesses=[])
    row = row.iloc[0]
    league_label = row.get("league_label")
    pos_pool = df[df.reference_position_group == position]
    league_pool = pos_pool[pos_pool.league_label == league_label] if pd.notna(league_label) else None

    sigs = sorted(relevant_signals_for(position, style, emphasis_list))
    facts = []
    for sig in sigs:
        safe = meta.safe_name(sig)
        pctile_col, raw_col = f"{safe}__percentile", f"{safe}__raw"
        if pctile_col not in df.columns or pd.isna(row.get(pctile_col)) or pd.isna(row.get(raw_col)):
            continue
        global_pctile = float(row[pctile_col])
        raw = row[raw_col]
        league_pctile = None
        if league_pool is not None and len(league_pool) >= 8 and raw_col in league_pool.columns:
            league_vals = league_pool[raw_col].dropna()
            if len(league_vals) >= 8:
                league_pctile = float((league_vals <= raw).mean() * 100)
        facts.append(dict(sig=sig, global_pctile=global_pctile, league_pctile=league_pctile, raw=raw))

    facts.sort(key=lambda f: -f["global_pctile"])
    strengths_pool = [f for f in facts if f["global_pctile"] >= 75]
    weaknesses_pool = sorted([f for f in facts if f["global_pctile"] <= 30], key=lambda f: f["global_pctile"])

    def render(f):
        p = phrase_for(f["sig"], f["raw"])
        if p is None:
            return None
        gp = f["global_pctile"]
        lp = f["league_pctile"]
        # Vary the evidence: when the league-relative view tells a materially different story
        # (a real gap, not noise), surface both perspectives; otherwise the global percentile
        # alone plus the raw stat already tells the story without redundant repetition.
        if lp is not None and abs(lp - gp) >= 15:
            return (f"Ranks in the {_ordinal(gp)} percentile among comparable players overall "
                     f"(but the {_ordinal(lp)} percentile among players in his own league) — {p}.")
        return f"Ranks in the {_ordinal(gp)} percentile among comparable players — {p}."

    strengths = [render(f) for f in strengths_pool[:n_strengths]]
    weaknesses = [render(f) for f in weaknesses_pool[:n_weaknesses]]
    return dict(strengths=[s for s in strengths if s], weaknesses=[w for w in weaknesses if w])
