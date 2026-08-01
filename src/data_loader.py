"""Data loading for the dashboard. Single cached read of the Sprint 1 export."""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_PATH = DATA_DIR / "players.csv"
MATCH_LEVEL_PATH = DATA_DIR / "match_level_stats.parquet"
MATCH_LEVEL_KEY = ["player_id", "season_id", "team_id", "filter_key"]
MATCH_LEVEL_VALUE_SUFFIXES = {"raw": "raw_value", "per90": "per90_value", "pct": "percentile_value"}

PHILOSOPHY_COLUMNS = {
    "Control": "phil_control",
    "Progression": "phil_progression",
    "Direct": "phil_direct",
}

# Real underlying football metrics available to the Sprint 3b comparison charts, with their
# display names -- mirrors dashboard/data/build_dashboard_data.py's CHART_METRICS/PCT_METRICS
# (the source of truth for which metrics were actually exported).
METRIC_LABELS = {
    "touches": "Touches", "passes": "Passes", "accurate_passes": "Accurate Passes",
    "passes_in_final_third": "Passes into Final Third", "key_passes": "Key Passes",
    "big_chances_created": "Big Chances Created", "assists": "Assists",
    "shots_total": "Shots", "shots_on_target": "Shots on Target", "goals": "Goals",
    "dribble_attempts": "Dribble Attempts", "successful_dribbles": "Successful Dribbles",
    "total_crosses": "Crosses", "accurate_crosses": "Accurate Crosses",
    "tackles": "Tackles", "tackles_won": "Tackles Won", "interceptions": "Interceptions",
    "clearances": "Clearances", "aerials_won": "Aerial Duels Won",
    "ball_recoveries": "Ball Recoveries", "long_balls": "Long Balls",
    "long_balls_won": "Long Balls Won", "duels_won": "Duels Won", "fouls_drawn": "Fouls Drawn",
    "accurate_passes_pct": "Accurate Pass %", "long_balls_won_pct": "Long Ball Won %",
    "tackles_won_pct": "Tackle Won %",
}

MATCH_FILTERS = {
    "Full Season": "full_season", "Home": "home", "Away": "away",
    "Last 3 Months": "last_3_months", "Last 6 Months": "last_6_months",
    "Top Opponents": "top_opponents", "Bottom Opponents": "bottom_opponents",
}

DISPLAY_MODE_COLUMN = {"Raw": "raw_value", "Per 90": "per90_value", "Percentile": "percentile_value"}


@st.cache_data
def load_players():
    df = pd.read_csv(DATA_PATH)
    return df


@st.cache_data
def load_match_level_stats():
    """Reads the wide-format Parquet (Sprint 6 storage optimization -- see
    dashboard/data/optimize_match_level_storage.py) and melts it back into the same long-format
    shape (player_id, season_id, team_id, filter_key, metric, raw_value, per90_value,
    percentile_value) the rest of the app was built against, so charts.py needed zero changes."""
    wide = pd.read_parquet(MATCH_LEVEL_PATH)
    frames = []
    for suffix, value_col in MATCH_LEVEL_VALUE_SUFFIXES.items():
        cols = [c for c in wide.columns if c.endswith(f"__{suffix}")]
        sub = wide[MATCH_LEVEL_KEY + cols].melt(id_vars=MATCH_LEVEL_KEY, var_name="metric", value_name=value_col)
        sub["metric"] = sub["metric"].str.removesuffix(f"__{suffix}")
        frames.append(sub.set_index(MATCH_LEVEL_KEY + ["metric"]))
    return pd.concat(frames, axis=1).reset_index()


@st.cache_data
def nationality_options():
    df = load_players()
    return ["All Nationalities"] + sorted(df["nationality"].dropna().unique().tolist())


@st.cache_data
def specific_positions_for(broad_group):
    df = load_players()
    if broad_group != "All":
        df = df[df["position_group_broad"] == broad_group]
    return sorted(df["primary_detailed_position"].dropna().unique().tolist())
