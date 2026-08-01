# National Team Player Recommendation — Dashboard

Streamlit application implementing the approved design specification: a style-fit player
recommendation engine (Control / Progression / Direct attacking philosophies, plus one fixed
Defensive score) for national team scouting across 32 European leagues outside the top five.
Built in reviewable sprints — see `docs/roadmap.md`.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. `app.py` is a thin router (`st.navigation`) between the two
pages in `views/`: `recommendations.py` (search, results, comparison charts, custom chart
builder) and `methodology.py` (the 7-stage plain-language walkthrough).

## Project structure

```
app.py                    Entry point / page router
views/
  recommendations.py      Search, results, comparison charts, custom chart builder
  methodology.py          The 7-stage methodology walkthrough
src/
  styles.py                Design tokens + all CSS (fonts embedded as base64)
  nav.py                    Shared masthead + top navigation
  data_loader.py            Cached data loading
  cards.py                   Result row / detail panel HTML rendering
  analysis.py                Strengths/weaknesses, "why this score" explanations
  charts.py                   Plotly figure builders (philosophy + real-metric charts)
data/
  build_dashboard_data.py    Exports players.csv / player_abilities.csv / weights from
                              production/ outputs -- never recomputes a score
  optimize_match_level_storage.py   Reshapes match_level_stats.csv into a compact
                                     wide-format Parquet (see below)
  *.csv, *.parquet            The exported data itself
```

## Regenerating the data export

Everything in `data/*.csv` and `data/*.parquet` is exported from `production/` outputs (the
locked analytical engine) — nothing is recomputed inside the dashboard. Re-run after the
underlying master dataset or score files change:

```
python data/build_dashboard_data.py
python data/optimize_match_level_storage.py
```

The first script writes `players.csv`, `player_abilities.csv`, `philosophy_weights.csv`,
`defensive_weights.csv`, and `match_level_stats.csv`. The second reshapes
`match_level_stats.csv` (long format, ~75MB) into `match_level_stats.parquet` (wide format,
~5MB) — a pure storage optimization with a built-in round-trip check; the app reads the Parquet
file, not the CSV. Both scripts use absolute paths into the parent research repository and are
not meant to run in a deployed environment — only the exported data files under `data/` are
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
