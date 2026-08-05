"""
Player detail panel analysis -- Sprint 2.

Everything here is derived from real, already-locked production data: the 11 Football
Abilities' final scores (player_abilities.csv) and the real position x philosophy x ability
weight tables (philosophy_weights.csv, defensive_weights.csv, both copied verbatim from
production/docs/). Nothing here is invented scouting commentary -- "strengths" and "weaknesses"
are the same top/bottom Abilities shown in the ranked list, just translated into a one-line,
factual description of what that Ability measures; "why this score" names the REAL
highest-weighted Abilities for the player's specific position and philosophy, and compares the
player's own score against the real position average computed from the same data.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from src.position_alias import POSITION_ALIAS_FOR_WEIGHTS

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# One neutral, factual line per Ability -- what it measures, not player-specific commentary.
ABILITY_DESCRIPTIONS = {
    "Crossing / Wide Delivery": "Delivery quality and end product from wide areas.",
    "Finishing / Shot Threat": "Shot volume and quality once inside a scoring position.",
    "Progressive Passing": "Passing that advances the ball meaningfully up the pitch.",
    "Chance Creation": "Creating clear scoring opportunities for teammates.",
    "Ball Retention & Security": "Keeping possession under pressure without unnecessary risk.",
    "Build-Up Involvement": "Participation in the team's possession phases.",
    "Long Distribution": "Range and accuracy of longer, territory-shifting passes.",
    "Ball Carrying / Dribbling": "Advancing the ball individually past opponents.",
    "Defensive Ball-Winning": "Regaining possession through tackles and interceptions.",
    "Ground Duels & Physical Contests": "Winning one-on-one physical and ground contests.",
    "Aerial Duels": "Winning contests in the air.",
}


@st.cache_data
def load_abilities():
    return pd.read_csv(DATA_DIR / "player_abilities.csv")


@st.cache_data
def load_philosophy_weights():
    return pd.read_csv(DATA_DIR / "philosophy_weights.csv")


@st.cache_data
def load_defensive_weights():
    return pd.read_csv(DATA_DIR / "defensive_weights.csv")


@st.cache_data
def position_ability_averages():
    """Real position-relative average score per (position, ability), computed directly from
    player_abilities.csv joined to players.csv -- used to say 'above/below the position
    average' honestly rather than asserting it without evidence."""
    players = pd.read_csv(DATA_DIR / "players.csv")[["player_id", "season_id", "team_id", "primary_detailed_position"]]
    ab = load_abilities().merge(players, on=["player_id", "season_id", "team_id"], how="inner")
    return ab.groupby(["primary_detailed_position", "ability"])["score"].mean()


def player_abilities(player_id, season_id, team_id):
    """{ability_name: score} for one player-season, only the Abilities actually present."""
    ab = load_abilities()
    row = ab[(ab.player_id == player_id) & (ab.season_id == season_id) & (ab.team_id == team_id)]
    return dict(zip(row["ability"], row["score"]))


def top_bottom_abilities(abilities, n=3):
    """Top-n strongest and bottom-n weakest, by score. When a player has fewer than 2n scored
    Abilities (325 player-seasons are missing at least one of the 11 -- see build_dashboard_data.py),
    naively taking the top n and bottom n of a short list would double-count the middle entries,
    showing the exact same Ability in both Strengths and Weaknesses. Splitting the list in half
    instead guarantees the two lists never overlap, at the cost of showing fewer than n on each
    side when data is thin -- which is what "not enough data" should look like, not a duplicate."""
    ranked = sorted(abilities.items(), key=lambda kv: kv[1], reverse=True)
    if len(ranked) >= 2 * n:
        return ranked[:n], list(reversed(ranked[-n:]))
    half = len(ranked) // 2
    return ranked[:half], list(reversed(ranked[half:]))


def _weights_for_position(position, philosophy=None):
    aliased = POSITION_ALIAS_FOR_WEIGHTS.get(position, position)
    if philosophy:
        w = load_philosophy_weights()
        w = w[(w.position == aliased) & (w.philosophy == philosophy)]
    else:
        w = load_defensive_weights()
        w = w[w.position == aliased]
    return dict(zip(w["ability"], w["weight_pct"]))


def why_philosophy_text(player_name, position, philosophy, abilities):
    weights = _weights_for_position(position, philosophy)
    if not weights:
        return f"No weighting data found for {position} — this position may not be covered by the current weighting table (worth flagging)."
    top2 = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:2]
    avgs = position_ability_averages()

    parts = []
    for ability, weight in top2:
        score = abilities.get(ability)
        if score is None:
            continue
        avg = avgs.get((position, ability))
        cmp_txt = ""
        if avg is not None:
            direction = "above" if score > avg else "below"
            cmp_txt = f" ({direction} the {position} average of {avg:.0f})"
        parts.append(f"{ability} ({score:.0f}{cmp_txt})")

    weight_desc = " and ".join(f"{a} ({w:.0f}%)" for a, w in top2)
    if not parts:
        return (f"{philosophy} for {position} players is weighted most heavily toward "
                f"{weight_desc}, but {player_name} has no recorded score for either — too few "
                f"qualifying matches to compute them.")
    return (f"{philosophy} for {position} players is weighted most heavily toward {weight_desc}. "
            f"{player_name}'s score there: {' and '.join(parts)}.")


def defensive_explanation_text(player_name, position, abilities):
    weights = _weights_for_position(position, philosophy=None)
    if not weights:
        return "No defensive weighting data found for this position."
    ranked = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
    weight_desc = ", ".join(f"{a} ({w:.0f}%)" for a, w in ranked)
    top_ability, _ = ranked[0]
    top_score = abilities.get(top_ability)
    score_txt = f" {player_name}'s strongest contribution here is {top_ability} ({top_score:.0f})." if top_score is not None else ""
    return (f"Built from {weight_desc} — combined once into a single Defensive score that does "
            f"not change no matter which attacking philosophy is selected above.{score_txt}")
