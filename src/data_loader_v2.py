"""
Data loading for the V2/F50 Recommendations page (migration, 2026-08-29). Reads the files
produced by dashboard/data/build_dashboard_data_v2.py -- players.csv (rebuilt, F50-compatible),
f50_scores.csv (long format, one row per player-season x valid combo), f50_registry.csv (the 192
valid combinations). The pre-existing match_level_stats.parquet loader is untouched and imported
from the old data_loader.py -- it is completely independent of the scoring architecture.
"""
import ast
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PLAYERS_PATH = DATA_DIR / "players.csv"
F50_SCORES_PATH = DATA_DIR / "f50_scores.csv"
F50_REGISTRY_PATH = DATA_DIR / "f50_registry.csv"
MULTI_CLUB_PATH = DATA_DIR / "multi_club_lineage.csv"

POSITION_LABELS = {
    "CB": "Centre Back", "FB": "Full Back", "WM": "Wide Midfielder", "Winger": "Winger",
    "DM": "Defensive Midfielder", "CM": "Central Midfielder", "AM": "Attacking Midfielder", "CF": "Centre Forward",
}
POSITION_ORDER = ["CB", "FB", "WM", "Winger", "DM", "CM", "AM", "CF"]


@st.cache_data
def load_players():
    """UI/UX multi-club lineage pass (2026-09-09): merges in `multi_club_lineage.csv` (see
    `production/match_level/build_multi_club_lineage.py` -- traces exactly which club stints
    actually contributed to a player-season's score, from the canonical pre-merge evidence file)
    as DISPLAY-ONLY additions -- `season_club`/`league_label` themselves are left completely
    UNCHANGED (still the single primary club/league every filter, TOP5 check, and league dropdown
    already keys off) so no filtering/scope logic anywhere is affected. Consumers that want the
    multi-club-aware label use the new `season_club_display`/`league_label_display`/
    `is_multi_club`/`cross_league` columns; every other consumer that just reads `season_club`/
    `league_label` behaves exactly as before."""
    df = pd.read_csv(PLAYERS_PATH)
    df["season_club_display"] = df["season_club"]
    df["league_label_display"] = df["league_label"]
    df["is_multi_club"] = False
    df["cross_league"] = False
    if MULTI_CLUB_PATH.exists():
        mc = pd.read_csv(MULTI_CLUB_PATH)
        mc = mc.set_index(["player_id", "season_name"])
        keyed = df.set_index(["player_id", "season_name"])
        matched = keyed.index.isin(mc.index)
        if matched.any():
            df.loc[matched, "season_club_display"] = keyed.index[matched].map(mc["clubs_ordered"]).values
            df.loc[matched, "league_label_display"] = keyed.index[matched].map(mc["leagues_ordered"]).values
            df.loc[matched, "is_multi_club"] = True
            df.loc[matched, "cross_league"] = keyed.index[matched].map(mc["cross_league"]).values
    return df


@st.cache_data
def load_f50_scores():
    return pd.read_csv(F50_SCORES_PATH)


@st.cache_data
def load_f50_registry():
    reg = pd.read_csv(F50_REGISTRY_PATH)
    # Tuples, not lists: Streamlit selectbox options must be hashable for the widget's internal
    # state tracking -- a list-valued option silently breaks default-selection (observed: value
    # comes back None even though the options render). A tuple behaves identically for iteration/
    # join/comparison everywhere else in this module.
    reg["emphasis_list"] = reg["emphasis_set"].apply(
        lambda x: () if pd.isna(x) or x in ("[]", "") else tuple(ast.literal_eval(x)))
    return reg


def style_options_for(position):
    reg = load_f50_registry()
    styles = reg[reg["position"] == position]["style"].unique().tolist()
    # NoStyle first (as "Any Style"), then the 3 named styles in a fixed, familiar order
    order = ["NoStyle", "Control", "Progression", "Direct"]
    return [s for s in order if s in styles]


def style_display(style):
    return "Any Style" if style == "NoStyle" else style


def emphasis_options_for(position, style):
    reg = load_f50_registry()
    sub = reg[(reg["position"] == position) & (reg["style"] == style)]
    # sorted by number of emphases, then alphabetically, so "None" is first and single-emphasis
    # options come before combinations -- easiest-to-scan order for a selectbox
    opts = sorted(sub["emphasis_list"].tolist(), key=lambda lst: (len(lst), lst))
    return opts


def emphasis_display(emphasis_list):
    return "None (Generic)" if not emphasis_list else " + ".join(emphasis_list)


def combo_id_for(position, style, emphasis_list):
    reg = load_f50_registry()
    sub = reg[(reg["position"] == position) & (reg["style"] == style)]
    for _, r in sub.iterrows():
        if r["emphasis_list"] == emphasis_list:
            return r["combo_id"]
    return None


@st.cache_data
def nationality_options():
    df = load_players()
    return ["All Nationalities"] + sorted(df["nationality"].dropna().unique().tolist())


# UI/UX Round 6 (2026-09-08) -- league filter, driven entirely by the canonical `league_label`
# population already in players.csv rather than a hand-maintained list, so a database expansion
# (new leagues added upstream) is reflected automatically the next time the dashboard data is
# rebuilt -- no dashboard code change required to "add" a new league.
@st.cache_data
def league_options():
    df = load_players()
    return sorted(df["league_label"].dropna().unique().tolist())


# The traditional European "Top 5" leagues, identified explicitly by their exact canonical
# `league_label` values (not re-derived from division level, club strength, or any other proxy --
# per the owner spec, Top 5 is a fixed, named list of these five competitions specifically).
TOP5_LEAGUE_LABELS = [
    "England 1 - Premier League",
    "Spain 1 - La Liga",
    "Germany 1 - Bundesliga",
    "Italy 1 - Serie A",
    "France 1 - Ligue 1",
]
