"""
Dashboard data export -- V2/F50 migration (2026-08-29).

Replaces the old V1 export (build_dashboard_data.py: Philosophy/Defensive/OwnDominance/Context
Ability scores) with one built on the locked V2/F50 production output
(production/player_evaluation_v2/results/). The old script and its output files are NOT deleted
here -- see the migration report for what was archived.

Produces:
  - players.csv        identity/demographic fields, ONE row per qualifying player-season, keyed
                        by (player_id, season_id, team_id) for compatibility with the existing
                        match-level chart infrastructure (src/charts.py, match_level_stats.*),
                        which is completely independent of the scoring architecture and is REUSED
                        UNCHANGED. Adds `position_v2` (the locked 8-group V2 scoring position --
                        CB/FB/WM/Winger/DM/CM/AM/CF) alongside the existing 11-way
                        `primary_detailed_position`/`position_group_broad` (kept for identification/
                        display/eligibility per the owner's Part 1 decision -- NOT used for V2
                        scoring, which uses position_v2 exclusively).
  - f50_scores.csv      long format: (player_id, season_id, team_id, position, style, emphasis,
                        combo_id, professional_score, opponent_multiplier, final_score, rank,
                        population). This is the core data behind the new Position -> Style ->
                        Emphasis recommendation UI -- one row per valid combination per player.
  - f50_registry.csv     the 192-combination registry (with the Defensive Mind rename already
                        applied), trimmed to what the UI's cascading selector needs.

Every number here is read directly from the already-validated, already-locked V2/F50 production
output -- nothing is recomputed or recalibrated in this script.
"""
import sys, ast, sqlite3
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(r"C:\Users\נועם\Desktop\Football Data\Projects\National Team Selection")
V2 = ROOT / "production" / "player_evaluation_v2"
sys.path.insert(0, str(V2))
sys.path.insert(0, str(ROOT / "production"))
import config as cfg  # noqa: E402
from league_labels import build_league_label  # noqa: E402 -- project-wide canonical helper, reused unchanged

OUT_DIR = Path(__file__).resolve().parent

GROUP8_TO_BROAD = {
    "CB": "Defence", "FB": "Defence",
    "DM": "Midfield", "CM": "Midfield", "AM": "Midfield", "WM": "Midfield",
    "Winger": "Attack", "CF": "Attack",
}

JOIN_KEY = ["player_id", "season_id", "team_id"]


def main():
    stints = pd.read_parquet(cfg.RESULTS_DIR / "00_all_qualifying_stints.parquet")
    stints["last_match_date"] = pd.to_datetime(stints.last_match_date, errors="coerce")

    # league_label must be built the same way the rest of this project builds it ("{Country} {Tier}
    # - {League}", production/league_labels.py) -- V2's own qualifying_stints only carries the raw
    # league_name + league_country_id, not the pre-built label, so it's constructed fresh here using
    # the exact same canonical helper every other production script uses (never a bespoke format).
    con = sqlite3.connect(str(cfg.DB))
    countries = pd.read_sql("SELECT country_id, name AS country_name FROM countries", con)
    con.close()
    stints = stints.merge(
        countries.rename(columns={"country_id": "league_country_id", "country_name": "league_country_name"}),
        on="league_country_id", how="left")
    stints["league_label"] = stints.apply(
        lambda r: build_league_label(r["league_country_name"], r["league_division_level"], r["league_name"]), axis=1)

    has_chrono = stints.last_match_date.notna()
    # Same "latest stint by chronology" convention already used by stage 30/34's own club/league
    # enrichment -- extended here to also carry season_id/team_id, so this export's join keys are
    # compatible with the pre-existing match-level chart data (which is keyed by season_id/team_id,
    # not season_name).
    latest = stints[has_chrono].sort_values("last_match_date", ascending=False).drop_duplicates(
        subset=["player_id", "season_name"], keep="first")
    latest_map = latest.set_index(["player_id", "season_name"])[
        ["season_id", "team_id", "club_name", "league_label", "player_name", "nationality",
         "date_of_birth", "primary_detailed_position"]
    ]

    pop = pd.read_parquet(cfg.RESULTS_DIR / "pop_with_level.parquet")
    print(f"pop_with_level.parquet: {len(pop)} rows")

    # Apply the same owner-approved manual position override (config.MANUAL_POSITION_OVERRIDES)
    # used by scoring, to the RAW display position too -- otherwise this one player's side-specific
    # search/display position (sourced from the raw provider chronology, not the corrected group)
    # would show "Centre Back" while their scoring group is Winger, a confusing mismatch for a
    # UI/UX round that specifically exposes side-specific search. Only 1 override currently exists.
    OVERRIDE_RAW_POSITION = {37743072: "Right Wing"}  # matches config.MANUAL_POSITION_OVERRIDES's "Right Winger"

    rows = []
    n_no_chrono = 0
    for _, r in pop.iterrows():
        key = (r.player_id, r.season_name)
        if key not in latest_map.index:
            n_no_chrono += 1
            continue
        e = latest_map.loc[key]
        rows.append(dict(
            player_id=int(r.player_id), season_id=int(e.season_id), team_id=int(e.team_id),
            season_name=r.season_name, player_name=e.player_name, nationality=e.nationality,
            season_club=e.club_name, league_label=e.league_label,
            primary_detailed_position=OVERRIDE_RAW_POSITION.get(int(r.player_id), e.primary_detailed_position),
            date_of_birth=e.date_of_birth, minutes_played=int(r.minutes_played),
            position_v2=r.reference_position_group,
            position_group_broad=GROUP8_TO_BROAD.get(r.reference_position_group, "Midfield"),
        ))
    players = pd.DataFrame(rows).drop_duplicates(subset=JOIN_KEY)
    print(f"players.csv: {len(players)} rows ({n_no_chrono} pop rows had no resolvable chronology, dropped)")
    players.to_csv(OUT_DIR / "players.csv", index=False)

    # ---------------- f50_scores.csv ----------------
    full = pd.read_parquet(cfg.RESULTS_DIR / "F50_full_population_scores.parquet")
    pop_key = pop[["player_id", "season_name"]].drop_duplicates()
    pop_key = pop_key.merge(
        pd.DataFrame(rows)[["player_id", "season_name", "season_id", "team_id"]],
        on=["player_id", "season_name"], how="inner")
    full2 = full.merge(pop_key, on=["player_id", "season_name"], how="inner")
    print(f"F50_full_population_scores.parquet: {len(full)} rows -> {len(full2)} after joining season_id/team_id "
          f"({len(full) - len(full2)} dropped, no resolvable chronology)")

    f50 = full2[["player_id", "season_id", "team_id", "combo_id", "position", "style", "emphasis",
                 "professional_score", "opponent_multiplier", "final_score", "rank", "population"]]
    f50.to_csv(OUT_DIR / "f50_scores.csv", index=False)
    print(f"f50_scores.csv: {len(f50)} rows")

    # ---------------- f50_registry.csv ----------------
    reg = pd.read_csv(V2 / "reference" / "registry_192.csv")
    reg.to_csv(OUT_DIR / "f50_registry.csv", index=False)
    print(f"f50_registry.csv: {len(reg)} rows (192 expected)")

    # ---------------- signal_scores.parquet + relevant_signals.csv ----------------
    # DEPLOYMENT FIX (2026-08-30): explanation_engine_v2.py previously imported signal_meta/
    # decomposed_engine directly from production/player_evaluation_v2/engine at RUNTIME, and read
    # PRODUCTION_signal_scores.parquet via an absolute production/ path -- both outside the
    # dashboard's own deployed repository, which broke on Streamlit Cloud (ModuleNotFoundError).
    # Both are now precomputed here (build time, dev environment only -- this script is never
    # imported by the deployed app) and exported as plain DATA into dashboard/data/, so the
    # deployed app has zero runtime dependency on production/ code or paths.
    build_signal_explanation_data(players)

    print("\nposition_v2 distribution:")
    print(players.position_v2.value_counts().to_string())
    print("\nAny row in players.csv missing from f50_scores.csv (should be 0 -- every player-season "
          "should have at least its own position's Generic combo):")
    have_scores = set(f50[JOIN_KEY].drop_duplicates().itertuples(index=False, name=None))
    have_players = set(players[JOIN_KEY].drop_duplicates().itertuples(index=False, name=None))
    print(len(have_players - have_scores))


def build_signal_explanation_data(players):
    """Exports two self-contained DATA files for the deployed explanation_engine_v2.py:
      - signal_scores.parquet: trimmed PRODUCTION_signal_scores (player_id, season_name,
        reference_position_group, + every Signal's __raw/__percentile column -- __Z/__shrunk/
        __SignalScore dropped, not needed for explanations).
      - relevant_signals.csv: (kind, position, key, signal_name, safe_name) rows -- kind is
        'position_quality' | 'style' | 'style_receiving' | 'emphasis'; key is the style name or
        emphasis name; signal_name is the original ("Tackles per90"), safe_name is the parquet
        column prefix. Lets the deployed app compute "which Signals matter for this profile"
        via a plain data lookup, with zero dependency on signal_meta.py/decomposed_engine.py at
        runtime.
    Reads signal_meta/decomposed_engine here ONLY (build time, dev environment) -- this script is
    never imported by the deployed app itself.
    """
    sys.path.insert(0, str(V2 / "engine"))
    import signal_meta as meta
    import decomposed_engine as de

    src = pd.read_parquet(cfg.RESULTS_DIR / "PRODUCTION_signal_scores.parquet")
    keep_cols = ["player_id", "season_name", "reference_position_group"]
    for sig in meta.ALL_SIGNALS:
        safe = meta.safe_name(sig)
        for suffix in ("__raw", "__percentile"):
            col = f"{safe}{suffix}"
            if col in src.columns:
                keep_cols.append(col)
    trimmed = src[keep_cols]
    trimmed.to_parquet(OUT_DIR / "signal_scores.parquet", index=False)
    print(f"\nsignal_scores.parquet: {len(trimmed)} rows, {len(trimmed.columns)} columns "
          f"(trimmed from {len(src.columns)})")

    # UI/UX Round 3 (2026-08-30): `role` (core/supporting) is now exported alongside `kind`,
    # read directly from the SAME locked meta.STYLE["core"/"supporting"] and
    # meta.EMPHASIS[...]["core"/"supporting"] dicts scoring itself uses -- not an invented
    # split. This lets the deployed app rank a profile's relevant Signals by how directly the
    # LOCKED architecture ties them to the selected Style/Emphasis (core=defining, supporting=
    # contributing) instead of treating every relevant Signal as equally central.
    rows = []
    for posn in meta.POSITIONS:
        for sig, w in de.position_quality_weights(posn).items():
            if w > 0:
                rows.append(dict(kind="position_quality", role="core", position=posn, key=None,
                                  signal_name=sig, safe_name=meta.safe_name(sig)))
        for style, st_def in meta.STYLE.items():
            for sig in st_def["core"]:
                rows.append(dict(kind="style", role="core", position=posn, key=style,
                                  signal_name=sig, safe_name=meta.safe_name(sig)))
            for sig in st_def.get("supporting", []):
                rows.append(dict(kind="style", role="supporting", position=posn, key=style,
                                  signal_name=sig, safe_name=meta.safe_name(sig)))
            if style == "Direct" and posn in meta.DIRECT_RECEIVING_POSITIONS:
                for sig in st_def.get("core_receiving", []):
                    rows.append(dict(kind="style_receiving", role="core", position=posn, key=style,
                                      signal_name=sig, safe_name=meta.safe_name(sig)))
    for (posn, emph), def_ in meta.EMPHASIS.items():
        for sig in def_["core"]:
            rows.append(dict(kind="emphasis", role="core", position=posn, key=emph,
                              signal_name=sig, safe_name=meta.safe_name(sig)))
        for sig in def_.get("supporting", []):
            rows.append(dict(kind="emphasis", role="supporting", position=posn, key=emph,
                              signal_name=sig, safe_name=meta.safe_name(sig)))

    rel = pd.DataFrame(rows).drop_duplicates()
    rel.to_csv(OUT_DIR / "relevant_signals.csv", index=False)
    print(f"relevant_signals.csv: {len(rel)} rows ({rel.kind.value_counts().to_dict()})")

    # UI/UX Round 2 (2026-08-30): signal_catalog.csv -- (signal_name, safe_name, domain,
    # info_type) for every Signal, exported so the deployed explanation engine can tier Signals
    # by how football-readable they are (VOLUME/EXECUTION = intuitive counts/rates/success %;
    # RESPONSIBILITY = team-share, SPECIALISATION = ratio-of-ratios -- both internal/abstract;
    # BEHAVIOUR is mixed, judged individually in the deployed engine's own small allowlist) and
    # group them by domain for redundancy control -- again a plain data lookup, zero runtime
    # dependency on signal_meta.py.
    cat_rows = [dict(signal_name=sig, safe_name=meta.safe_name(sig), domain=dom, info_type=itype)
                for sig, (dom, itype) in meta.SIGNAL_META.items()]
    cat = pd.DataFrame(cat_rows)
    cat.to_csv(OUT_DIR / "signal_catalog.csv", index=False)
    print(f"signal_catalog.csv: {len(cat)} rows")


if __name__ == "__main__":
    main()
