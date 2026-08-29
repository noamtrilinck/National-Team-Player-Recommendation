# National Team Player Recommendation — Dashboard

Streamlit application on the **V2/F50 methodology** (migrated 2026-08-30 from `Agent's Player to
Club Model`, owner-locked — see `../docs/v2_methodology_CANONICAL.md`): every eligible player is
rated against every valid **Position → Style → Emphasis** combination (192 total), with a
Professional Score adjusted for the strength of opposition actually faced (F50 Opponent Context).
There is deliberately no single universal player rating. The previous V1 methodology (11 Football
Abilities → Philosophy/Defensive scores → Context Ability blend) is retired and archived at
`../Archive/production_v1_scoring/` and `../Archive/dashboard_v1/` — not deleted, kept as history.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. `app.py` is a thin router (`st.navigation`) between the two
pages in `views/`: `recommendations.py` (Position/Style/Emphasis search, results, comparison
charts, custom chart builder) and `methodology.py` (the V2/F50 pipeline walkthrough).

## Project structure

```
app.py                    Entry point / page router
views/
  recommendations.py      Position -> Style -> Emphasis search, results, comparison charts
  methodology.py          The V2/F50 methodology walkthrough
src/
  styles.py                Design tokens + all CSS (fonts embedded as base64)
  nav.py                    Shared masthead + top navigation
  data_loader.py            Cached loading of match-level stats + real-metric chart labels (reused unchanged from V1)
  data_loader_v2.py         Cached loading of players.csv / f50_scores.csv / f50_registry.csv (V2)
  cards_v2.py                Result row / detail panel HTML rendering (Final/Professional Score, Opponent Multiplier)
  charts.py                   Plotly figure builders (real-metric comparison charts)
data/
  build_dashboard_data_v2.py  Exports players.csv / f50_scores.csv / f50_registry.csv from
                               production/player_evaluation_v2 outputs -- never recomputes a score
  optimize_match_level_storage.py   Reshapes match_level_stats.csv into a compact
                                     wide-format Parquet (see below)
  *.csv, *.parquet            The exported data itself
```

## Regenerating the data export

Everything in `data/*.csv` and `data/*.parquet` is exported from `production/` outputs (the
locked analytical engine) — nothing is recomputed inside the dashboard. Re-run after the
underlying V2/F50 production output changes:

```
python data/build_dashboard_data_v2.py
python data/optimize_match_level_storage.py
```

The first script writes `players.csv`, `f50_scores.csv`, and `f50_registry.csv`. The second
reshapes `match_level_stats.csv` (long format) into `match_level_stats.parquet` (wide format) — a
pure storage optimization with a built-in round-trip check, unchanged from V1; the app reads the
Parquet file, not the CSV. Both scripts use absolute paths into the parent research repository and
are not meant to run in a deployed environment — only the exported data files under `data/` are
needed there.

## Deploying to Streamlit Community Cloud

1. Push this `dashboard/` directory as the root of its own GitHub repository (see
   `docs/roadmap.md` — it's intentionally kept separate from the research/data-engineering
   project's own history).
2. On [share.streamlit.io](https://share.streamlit.io), create a new app pointing at that repo,
   branch `main`, main file path `app.py`.
3. `requirements.txt` and `runtime.txt` (Python version) are picked up automatically.
   `.streamlit/config.toml` sets the theme to match the design tokens; no secrets are needed —
   there's no external API or database call at runtime, everything reads from the committed
   data files.
4. First boot will be slower while `player_abilities.csv` and the Parquet file are parsed into
   `st.cache_data`; subsequent interactions are served from cache.

## Status

Sprints 1-5 complete. Sprint 6 (final polish, responsiveness, deployment prep, git extraction)
in progress — see `docs/roadmap.md` for the full plan.
