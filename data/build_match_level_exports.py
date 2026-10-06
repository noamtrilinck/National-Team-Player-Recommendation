"""
Dashboard match-level exports -- the LAST step of the match-level graph/filter chain
(production/match_level/run_match_level_pipeline.py runs it; see docs/PROJECT1_RUNBOOK.md §4b).

Produces, scoped to exactly the current dashboard population (dashboard/data/players.csv, the
canonical one-row-per-scored-player key written by build_dashboard_data_v2.py):
  - match_level_stats.csv      long format (player_id, season_id, team_id, filter_key, metric,
                               raw_value, per90_value, percentile_value) for the curated chart
                               metric pool across every match filter -- local regeneration source
                               only (git-ignored, 100+ MB).
  - match_level_stats.parquet  the same data pivoted wide (optimize_match_level_storage.py) --
                               what the app actually loads (src/data_loader.load_match_level_stats).
  - filter_eligibility.csv     the locked, disclosed per-(player, filter) minimum-minutes gate, so
                               the dashboard's "not shown" note can say WHY a player is missing
                               under a filter.

Moved here unchanged (2026-10-06) from the retired V1 builder build_dashboard_data.py, whose main()
read the archived V1 master dataset and could no longer be run -- which is why these two files
silently stayed on the 2026-09-09 (13,935-player) population through the V3 rebuilds. Nothing is
recomputed here: every value is copied from production/match_level/results/, which already
combines every contributing real stint of a multi-club player into the canonical key
(multiclub_canon.py).
"""
import os
import sys
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).resolve().parent
# Same convention as build_dashboard_data_v2.py: the project checkout this dashboard lives in.
ROOT = Path(os.environ.get("NTS_PROJECT_ROOT", OUT_DIR.parents[1]))
MATCH_LEVEL = ROOT / "production" / "match_level" / "results"
PLAYERS = OUT_DIR / "players.csv"

# Curated pool of real, underlying football metrics for the comparison charts -- per-90 rate +
# percentile + raw count for each, across every filter_key. Deliberately a subset of the ~107
# columns available, spanning passing/creativity/shooting/dribbling/crossing/defending/duels.
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


def load_scope():
    scope = pd.read_csv(PLAYERS, usecols=JOIN_KEY).dropna(subset=["team_id"]).drop_duplicates()
    return scope.astype({"team_id": int})


def build_match_level_stats(scope):
    """match_level_stats.csv: long format for the curated CHART_METRICS/PCT_METRICS pool, across
    every filter_key. Real underlying football stats only (never a score)."""
    per90_cols = set(JOIN_KEY + ["filter_key"])
    for m in CHART_METRICS:
        per90_cols |= {m, f"{m}_per90"}
    per90_cols |= set(PCT_METRICS)
    per90 = pd.read_csv(MATCH_LEVEL / "player_season_unified_by_filter_with_per90.csv",
                         usecols=lambda c: c in per90_cols)
    pct_cols = set(JOIN_KEY + ["filter_key"]) | {f"{m}_percentile" for m in PCT_METRICS}
    pct_cols |= {f"{m}_per90_percentile" for m in CHART_METRICS}
    pct = pd.read_csv(MATCH_LEVEL / "player_season_filtered_percentiles.csv", usecols=lambda c: c in pct_cols)

    key = JOIN_KEY + ["filter_key"]
    per90 = per90.merge(scope, on=JOIN_KEY, how="inner")
    pct = pct.merge(scope, on=JOIN_KEY, how="inner")
    merged = per90.merge(pct, on=key, how="inner", suffixes=("", "_pctfile"))
    print(f"match-level per90 rows in scope: {len(per90)}, percentile rows in scope: {len(pct)}, merged: {len(merged)}")

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
        # Percentage metrics are already minutes-independent rates: per90_value mirrors raw_value
        # so the Raw/Per 90/Percentile toggle never errors on them.
        sub = merged[key + [raw_col, pctile_col]].rename(
            columns={raw_col: "raw_value", pctile_col: "percentile_value"})
        sub["per90_value"] = sub["raw_value"]
        sub["metric"] = metric
        frames.append(sub[key + ["raw_value", "per90_value", "percentile_value", "metric"]])

    out = pd.concat(frames, ignore_index=True)
    for c in ("raw_value", "per90_value", "percentile_value"):
        out[c] = out[c].round(2)
    out.to_csv(OUT_DIR / "match_level_stats.csv", index=False)
    full_season = out[out.filter_key == "full_season"][JOIN_KEY].drop_duplicates()
    print(f"Wrote match_level_stats.csv: {len(out)} rows, {out.metric.nunique()} metrics x "
          f"{out.filter_key.nunique()} filter_keys; full_season coverage {len(full_season)} of {len(scope)}")
    print(out.drop_duplicates(key).filter_key.value_counts().to_string())


def build_filter_eligibility(scope):
    """filter_eligibility.csv: the locked per-(player, filter) minimum-minutes gate
    (filter_definitions.MIN_MINUTES_BY_FILTER) exactly as build_filtered_eligibility.py wrote it.
    Not a new threshold -- it only lets the dashboard explain a missing chart point."""
    elig = pd.read_csv(MATCH_LEVEL / "player_season_filter_eligibility.csv",
                        usecols=JOIN_KEY + ["filter_key", "minutes_played", "min_minutes_required",
                                            "meets_minimum_sample"])
    elig = elig.merge(scope, on=JOIN_KEY, how="inner")
    elig.to_csv(OUT_DIR / "filter_eligibility.csv", index=False)
    print(f"Wrote filter_eligibility.csv: {len(elig)} rows ({elig[JOIN_KEY].drop_duplicates().shape[0]} "
          f"players x {elig.filter_key.nunique()} filters)")


def main():
    scope = load_scope()
    print(f"Dashboard scope (players.csv): {len(scope)} canonical player keys")
    build_match_level_stats(scope)
    build_filter_eligibility(scope)
    sys.path.insert(0, str(OUT_DIR))
    import optimize_match_level_storage
    optimize_match_level_storage.main()


if __name__ == "__main__":
    main()
