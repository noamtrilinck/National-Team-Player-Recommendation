"""
Dashboard data export -- Sprint 1 + Sprint 2 scope.

Produces, all sourced exclusively from already-locked production/ outputs (never recomputed
here):
  - players.csv            (Sprint 1) identity, position, club/league, age, minutes, the 3
                            Philosophy scores, Final Defensive Score.
  - player_abilities.csv   (Sprint 2) the 11 Football Abilities' final (context-adjusted)
                            scores per player, long format -- feeds the detail panel's
                            Strongest/Weakest Abilities lists.
  - philosophy_weights.csv (Sprint 2) position x philosophy x ability weight_pct, copied from
                            the locked ability_weighting_v1.csv -- feeds the "why this
                            Philosophy score" explanation with the REAL weights, not a guess.
  - defensive_weights.csv  (Sprint 2) position x ability weight_pct for the single blended
                            Defensive score, copied from position_defensive_weights.csv.
  - match_level_stats.csv  (Sprint 3b) long format (player_id, season_id, team_id, filter_key,
                            metric, raw_value, per90_value, percentile_value) for a curated pool
                            of real underlying football stats (never Ability/Philosophy/Defensive
                            scores) across all 7 match filters -- feeds the 4 AI-selected
                            real-metric comparison charts.

Each sprint extends this export only as far as that sprint's own UI actually needs, mirroring
how the data pipeline itself was built in validated stages rather than all at once.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.position_alias import POSITION_ALIAS_FOR_WEIGHTS

ROOT = Path(r"C:\Users\נועם\Desktop\Football Data\Projects\National Team Selection")
MASTER = ROOT / "production" / "master_dataset" / "results_master" / "master_player_dataset.csv"
ABIL = ROOT / "production" / "abilities"
CC_RESULTS = ROOT / "production" / "competitive_context" / "results"
DOCS = ROOT / "production" / "docs"
MATCH_LEVEL = ROOT / "production" / "match_level" / "results"
OUT_DIR = Path(__file__).resolve().parent
OUT = OUT_DIR / "players.csv"

# Curated pool of real, underlying football metrics for Sprint 3b's comparison charts --
# per-90 rate + percentile + raw count for each, across all 7 filter_keys. Deliberately a
# subset of the ~107 columns available (not every metric the pipeline computes), spanning
# passing/creativity/shooting/dribbling/crossing/defending/duels so the "which metric best
# explains the group's differences" search has real breadth without an unmanageable column
# count. Extending this list costs nothing later if a metric turns out to be missing.
CHART_METRICS = {
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
}
PCT_METRICS = {
    "accurate_passes_pct": "Accurate Pass %", "long_balls_won_pct": "Long Ball Won %",
    "tackles_won_pct": "Tackle Won %",
}

JOIN_KEY = ["player_id", "season_id", "team_id"]

# The 11 Football Abilities: real names as used throughout production/ (NOT the placeholder
# names used in the earlier design-mockup examples -- those were illustrative only).
ATTACKING_ABILITIES = ["Crossing / Wide Delivery", "Finishing / Shot Threat", "Progressive Passing",
                        "Chance Creation", "Ball Retention & Security", "Build-Up Involvement",
                        "Long Distribution", "Ball Carrying / Dribbling"]
DEFENSIVE_ABILITIES = ["Defensive Ball-Winning", "Ground Duels & Physical Contests", "Aerial Duels"]
ABILITY_FOLDER = {
    "Crossing / Wide Delivery": "results_crossing_ability", "Finishing / Shot Threat": "results_finishing_ability",
    "Progressive Passing": "results_progressive_passing_ability", "Chance Creation": "results_chance_creation_ability",
    "Ball Retention & Security": "results_ball_retention_ability", "Build-Up Involvement": "results_build_up_involvement_ability",
    "Long Distribution": "results_long_distribution_ability", "Ball Carrying / Dribbling": "results_ball_carrying_dribbling_ability",
    "Defensive Ball-Winning": "results_defensive_ball_winning_ability",
    "Ground Duels & Physical Contests": "results_ground_duels_ability", "Aerial Duels": "results_aerial_duels_ability",
}


def afn(a):
    return a.replace(" / ", "_").replace(" & ", "_").replace(" ", "_")


def main():
    master = pd.read_csv(MASTER)
    master = master.dropna(subset=JOIN_KEY + ["primary_detailed_position"])
    print(f"master_player_dataset.csv: {len(master)} rows")

    phil = pd.read_csv(CC_RESULTS / "philosophy_scores_context_adjusted.csv")
    phil = phil.rename(columns={
        "Control Attacking Score": "phil_control",
        "Progression Attacking Score": "phil_progression",
        "Direct Attacking Score": "phil_direct",
    })[JOIN_KEY + ["phil_control", "phil_progression", "phil_direct"]]

    defense = pd.read_csv(CC_RESULTS / "final_defensive_score.csv")
    defense = defense.rename(columns={"FinalDefensiveScore": "final_defensive_score"})[
        JOIN_KEY + ["final_defensive_score"]
    ]

    df = master.merge(phil, on=JOIN_KEY, how="inner").merge(defense, on=JOIN_KEY, how="inner")
    print(f"After merging Philosophy + Defensive scores: {len(df)} rows "
          f"({len(master) - len(df)} master rows dropped for missing a score)")

    # position_group_broad drives the Broad Position filter (All/Defence/Midfield/Attack);
    # primary_detailed_position drives the Specific Position filter, dynamically scoped to
    # whichever broad group is selected.
    #
    # date_of_birth (not the static, season-start-relative `age` column) is exported so the
    # dashboard can compute each player's real CURRENT age at render time -- see
    # src/cards.py's _current_age(). The master dataset's own `age` is deliberately computed
    # as of each season's start date (see build_master_player_dataset.py's compute_age
    # docstring) -- correct for that analytical table, but not what a user checking the
    # dashboard today wants to see. date_of_birth has the exact same missingness as `age`
    # (age is itself derived from it), so nothing is lost by exporting the one and not the other.
    keep_cols = JOIN_KEY + [
        "player_name", "nationality", "season_club", "league_label",
        "primary_detailed_position", "position_group_broad", "date_of_birth", "minutes_played",
        "phil_control", "phil_progression", "phil_direct", "final_defensive_score",
    ]
    df = df[keep_cols].round({
        "phil_control": 1, "phil_progression": 1, "phil_direct": 1, "final_defensive_score": 1,
    })

    df.to_csv(OUT, index=False)
    print(f"\nWrote {OUT}: {len(df)} rows, {len(df.columns)} columns")
    print(f"Distinct nationalities: {df.nationality.nunique()}")
    print(f"Distinct specific positions: {df.primary_detailed_position.nunique()}")
    print("Rows per broad position group:")
    print(df.position_group_broad.value_counts().to_string())
    print(f"\nAny null Philosophy/Defensive scores after merge (should be 0): "
          f"{df[['phil_control','phil_progression','phil_direct','final_defensive_score']].isna().sum().sum()}")

    scope = df[JOIN_KEY].drop_duplicates()
    build_player_abilities(scope)
    build_weights()
    build_match_level_stats(scope)


def build_player_abilities(scope):
    """player_abilities.csv: long format (player_id, season_id, team_id, ability, score) --
    the FINAL (context-adjusted) score for all 11 Abilities, scoped to exactly the players.csv
    population (same population the detail panel will ever be opened for)."""
    frames = []
    for ability in ATTACKING_ABILITIES + DEFENSIVE_ABILITIES:
        folder = ABILITY_FOLDER[ability]
        adj = pd.read_csv(CC_RESULTS / f"{afn(ability)}_context_adjusted.csv")
        adj = adj[JOIN_KEY + ["score_context_adjusted"]].rename(columns={"score_context_adjusted": "score"})
        adj = adj.merge(scope, on=JOIN_KEY, how="inner")
        adj["ability"] = ability
        frames.append(adj)
        print(f"  {ability}: {len(adj)} scores in scope")

    out = pd.concat(frames, ignore_index=True)
    out["score"] = out["score"].round(1)
    out_path = OUT_DIR / "player_abilities.csv"
    out.to_csv(out_path, index=False)
    n_player_seasons = out[JOIN_KEY].drop_duplicates().shape[0]
    print(f"\nWrote {out_path}: {len(out)} rows ({n_player_seasons} player-seasons x up to {out.ability.nunique()} abilities)")

    # Coverage check: how many players.csv rows have all 11 Ability scores present?
    counts = out.groupby(JOIN_KEY).size()
    n_complete = (counts == 11).sum()
    print(f"Player-seasons with all 11 Ability scores present: {n_complete} of {len(scope)}")
    if n_complete < len(scope):
        n_missing_some = len(scope) - n_complete
        print(f"  {n_missing_some} player-seasons are missing at least one Ability score "
              f"(the detail panel will show fewer than 3 strongest/weakest entries for these -- "
              f"disclosed, not padded with fabricated values)")


def build_weights():
    """philosophy_weights.csv / defensive_weights.csv: copied verbatim from the locked weighting
    tables (kept in THEIR OWN position spelling, including the pooled-only rows like Full-Back/
    Winger/Wide Midfielder that have no master-side equivalent). The app-side lookup applies
    POSITION_ALIAS_FOR_WEIGHTS to primary_detailed_position before querying these tables --
    validated below so a silent NaN-weight bug is caught here, not at detail-panel render time."""
    phil_w = pd.read_csv(DOCS / "ability_weighting_v1.csv")
    phil_w.to_csv(OUT_DIR / "philosophy_weights.csv", index=False)
    print(f"\nWrote philosophy_weights.csv: {len(phil_w)} rows, positions: {sorted(phil_w.position.unique())}")

    def_w = pd.read_csv(DOCS / "position_defensive_weights.csv")
    def_w.to_csv(OUT_DIR / "defensive_weights.csv", index=False)
    print(f"Wrote defensive_weights.csv: {len(def_w)} rows, positions: {sorted(def_w.position.unique())}")

    # Validate the alias mapping actually resolves every position appearing in players.csv --
    # catch a silent NaN-weight bug now, not at detail-panel render time.
    players = pd.read_csv(OUT)
    aliased = players["primary_detailed_position"].replace(POSITION_ALIAS_FOR_WEIGHTS)
    unresolved_phil = sorted(set(aliased) - set(phil_w["position"]))
    unresolved_def = sorted(set(aliased) - set(def_w["position"]))
    print(f"\nPositions in players.csv with NO match in philosophy_weights.csv after aliasing "
          f"(should be empty): {unresolved_phil}")
    print(f"Positions in players.csv with NO match in defensive_weights.csv after aliasing "
          f"(should be empty): {unresolved_def}")


def build_match_level_stats(scope):
    """match_level_stats.csv (Sprint 3b): long format (player_id, season_id, team_id, filter_key,
    metric, raw_value, per90_value, percentile_value) for the curated CHART_METRICS/PCT_METRICS
    pool, across all 7 filter_keys -- feeds the 4 AI-selected real-metric comparison charts.
    Deliberately never touches Ability/Philosophy/Defensive scores; these are real underlying
    football stats only, sourced from the already-locked match-level filtering pipeline."""
    # usecols narrows the read to exactly what's needed -- avoids pandas' mixed-dtype warning on
    # columns like "source" that this export never touches, and cuts load time on a 50k-row file.
    per90_cols = set(JOIN_KEY + ["filter_key"])
    for m in CHART_METRICS:
        per90_cols |= {m, f"{m}_per90"}
    per90_cols |= set(PCT_METRICS)
    per90 = pd.read_csv(MATCH_LEVEL / "player_season_unified_by_filter_with_per90.csv",
                         usecols=lambda c: c in per90_cols)
    pct_cols = set(JOIN_KEY + ["filter_key"]) | {f"{m}_percentile" for m in PCT_METRICS}
    pct_cols |= {f"{m}_per90_percentile" for m in CHART_METRICS}
    pct = pd.read_csv(MATCH_LEVEL / "player_season_filtered_percentiles.csv", usecols=lambda c: c in pct_cols)

    key = ["player_id", "season_id", "team_id", "filter_key"]
    per90 = per90.merge(scope, on=JOIN_KEY, how="inner")
    pct = pct.merge(scope, on=JOIN_KEY, how="inner")
    merged = per90.merge(pct, on=key, how="inner", suffixes=("", "_pctfile"))
    print(f"\nmatch-level per90 rows in scope: {len(per90)}, percentile rows in scope: {len(pct)}, "
          f"merged: {len(merged)}")

    frames = []
    for metric in CHART_METRICS:
        raw_col, per90_col, pctile_col = metric, f"{metric}_per90", f"{metric}_per90_percentile"
        if raw_col not in merged.columns or per90_col not in merged.columns or pctile_col not in merged.columns:
            print(f"  SKIPPED (column missing): {metric}")
            continue
        sub = merged[key + [raw_col, per90_col, pctile_col]].rename(
            columns={raw_col: "raw_value", per90_col: "per90_value", pctile_col: "percentile_value"})
        sub["metric"] = metric
        frames.append(sub)

    for metric in PCT_METRICS:
        raw_col, pctile_col = metric, f"{metric}_percentile"
        if raw_col not in merged.columns or pctile_col not in merged.columns:
            print(f"  SKIPPED (column missing): {metric}")
            continue
        # Percentage metrics (e.g. Accurate Pass %) don't have a meaningful "per 90" transform --
        # they're already minutes-independent rates, so per90_value mirrors raw_value rather than
        # being left null (keeps the Raw/Per90/Percentile display-mode toggle from erroring on
        # these metrics; Raw and Per 90 will simply read identically for this subset).
        sub = merged[key + [raw_col, pctile_col]].rename(
            columns={raw_col: "raw_value", pctile_col: "percentile_value"})
        sub["per90_value"] = sub["raw_value"]
        sub["metric"] = metric
        frames.append(sub[key + ["raw_value", "per90_value", "percentile_value", "metric"]])

    out = pd.concat(frames, ignore_index=True)
    for c in ("raw_value", "per90_value", "percentile_value"):
        out[c] = out[c].round(2)
    out_path = OUT_DIR / "match_level_stats.csv"
    out.to_csv(out_path, index=False)
    print(f"\nWrote {out_path}: {len(out)} rows, {out.metric.nunique()} metrics x "
          f"{out.filter_key.nunique()} filter_keys x {out[JOIN_KEY].drop_duplicates().shape[0]} player-seasons")
    print("Rows per filter_key:")
    print(out.filter_key.value_counts().to_string())
    print(f"\nNull raw/per90/percentile values (should be low -- real per-filter data-availability gaps, "
          f"e.g. a player with 0 minutes Away): "
          f"{out[['raw_value','per90_value','percentile_value']].isna().sum().to_dict()}")

    full_season = out[out.filter_key == "full_season"]
    coverage = full_season[JOIN_KEY].drop_duplicates().shape[0]
    print(f"\nfull_season filter_key coverage: {coverage} of {len(scope)} players.csv player-seasons")


if __name__ == "__main__":
    main()
