"""
Sprint 6 performance pass: reshape the existing match_level_stats.csv into a wide-format Parquet
file, purely as a storage/load-time optimization.

Deliberately reads ONLY the already-exported dashboard/data/match_level_stats.csv -- never
production/match_level/results/ or the master dataset -- so this can run safely while position
recovery is in progress and the data layer is on hold. If the position work later changes the
master dataset and build_dashboard_data.py is rerun, match_level_stats.csv gets regenerated from
scratch and this script should simply be rerun on top of it again.

Long format (1.27M rows: player_id, season_id, team_id, filter_key, metric, raw_value,
per90_value, percentile_value) repeats the 4 key columns once per metric per player-season-filter
-- 27x more rows than necessary. Pivoting to one row per (player_id, season_id, team_id,
filter_key) with one column per (metric, value_type) removes that repetition, and Parquet's
columnar compression removes most of the rest. src/data_loader.load_match_level_stats() melts
this back to the original long shape in memory, so nothing downstream (charts.py, app views)
needs to change.
"""
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).resolve().parent
CSV_PATH = OUT_DIR / "match_level_stats.csv"
PARQUET_PATH = OUT_DIR / "match_level_stats.parquet"

KEY = ["player_id", "season_id", "team_id", "filter_key"]
VALUE_COLS = {"raw_value": "raw", "per90_value": "per90", "percentile_value": "pct"}


def main():
    long_df = pd.read_csv(CSV_PATH)
    print(f"Read {CSV_PATH}: {len(long_df)} rows")

    wide = long_df.pivot(index=KEY, columns="metric", values=list(VALUE_COLS.keys()))
    wide.columns = [f"{metric}__{VALUE_COLS[value_col]}" for value_col, metric in wide.columns]
    wide = wide.reset_index()
    print(f"Pivoted to wide: {len(wide)} rows, {len(wide.columns)} columns")

    wide.to_parquet(PARQUET_PATH, engine="pyarrow", index=False, compression="zstd")
    csv_mb = CSV_PATH.stat().st_size / 1_000_000
    parquet_mb = PARQUET_PATH.stat().st_size / 1_000_000
    print(f"\n{CSV_PATH.name}: {csv_mb:.1f} MB -> {PARQUET_PATH.name}: {parquet_mb:.1f} MB "
          f"({csv_mb / parquet_mb:.1f}x smaller)")

    # Round-trip check: melt the wide parquet back and compare against the original long CSV,
    # row-for-row (after sorting both the same way), before trusting this as the new source.
    check = pd.read_parquet(PARQUET_PATH)
    melted_frames = []
    for value_col, suffix in VALUE_COLS.items():
        cols = [c for c in check.columns if c.endswith(f"__{suffix}")]
        sub = check[KEY + cols].melt(id_vars=KEY, var_name="metric", value_name=value_col)
        sub["metric"] = sub["metric"].str.removesuffix(f"__{suffix}")
        melted_frames.append(sub.set_index(KEY + ["metric"]))
    reconstructed = pd.concat(melted_frames, axis=1).reset_index()

    orig_sorted = long_df.sort_values(KEY + ["metric"]).reset_index(drop=True)
    recon_sorted = reconstructed.sort_values(KEY + ["metric"]).reset_index(drop=True)[orig_sorted.columns]
    mismatches = 0
    for col in ["raw_value", "per90_value", "percentile_value"]:
        both_null = orig_sorted[col].isna() & recon_sorted[col].isna()
        diff = (orig_sorted[col] - recon_sorted[col]).abs() > 1e-6
        mismatches += int((diff & ~both_null).sum())
    print(f"Round-trip mismatches after melting back to long format (should be 0): {mismatches}")
    print(f"Row count match: original {len(orig_sorted)} vs reconstructed {len(recon_sorted)}")


if __name__ == "__main__":
    main()
