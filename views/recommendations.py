"""
Recommendations page -- V2/F50 migration (2026-08-29).

Replaces the old Philosophy/Defensive-score recommendation flow with the locked V2/F50
architecture: a Position -> Style -> Emphasis cascading selection (backed by the 192-combination
registry, so only valid combinations are ever offered) drives a single ranked Final Score list.
There is deliberately no universal "best player" ranking -- the same player can rank very
differently under a different Style/Emphasis, and the UI is built to make that visible rather than
hide it.

The real-metric comparison charts (differentiating metrics, range/scatter/bubble, custom chart
builder) are REUSED UNCHANGED from the old page -- they operate on real per-90 match-level stats,
completely independent of which scoring architecture ranks players.

The old page is preserved at Archive/dashboard_v1/views/recommendations.py (see the migration
report) -- not deleted, since it documents the superseded V1 UI.
"""
import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.data_loader import load_match_level_stats, METRIC_LABELS, MATCH_FILTERS, DISPLAY_MODE_COLUMN
from src.data_loader_v2 import (
    load_players, load_f50_scores, nationality_options,
    POSITION_LABELS, POSITION_ORDER, style_options_for, style_display,
    emphasis_options_for, emphasis_display, combo_id_for,
)
from src.cards_v2 import render_result_row, render_detail_panel
from src.charts import differentiating_metrics, metric_range_figure, scatter_metric_figure, bubble_metric_figure
from src.nav import render_nav
from src.league_coverage import parse_league_labels, prepare_league_coverage_display, render_league_coverage
from src.nationality_flags import get_flag_html

MAX_METRIC_CHART_PLAYERS = 8
MAX_DISPLAYED_ROWS = 150

render_nav("rec")

players = load_players()
f50 = load_f50_scores()

# ---------------- Hero ----------------
st.markdown("""
<span class="ntpr-kicker">Player recommendation engine — not a ranking platform</span>
<div class="ntpr-h1">Not the best player.<br>The right one for <em>how you play.</em></div>
<p class="ntpr-sub">Every eligible player is evaluated against every valid <b>Style</b> and <b>Emphasis</b>
combination for their position (192 valid combinations in total). A recommendation always means
<b>"rated for this exact profile,"</b> never <b>"ranked highest overall."</b> There is no universal player
score, and there never will be one — the same player can and does rank very differently for a different
profile.</p>
<div class="ntpr-notthis">
  <div><div class="lbl">What this isn't</div><div class="no">A universal player ranking</div></div>
  <div><div class="lbl">What this is</div><div class="yes">A profile-fit recommendation, with context</div></div>
</div>
""", unsafe_allow_html=True)

# ---------------- Leagues Covered ----------------
render_league_coverage(prepare_league_coverage_display(parse_league_labels(players["league_label"])))

# ---------------- Database scope ----------------
st.markdown("""
<div class="ntpr-scope">
  <div class="ic">🛈</div>
  <div>
    <b>Database Scope</b>
    <p>This recommendation engine covers a curated set of European leagues outside the top divisions of the
    "big five" (Premier League, La Liga, Serie A, Bundesliga, Ligue 1) — built to help national teams identify
    players in strong secondary European competitions. Note: this <b>does</b> include selected lower divisions
    from some of those same countries (e.g. the Championship, Ligue 2, Serie B) — a search for "England" will
    surface Championship and League One players, not Premier League ones.</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------- Style/Emphasis explainer ----------------
st.markdown("""
<div class="ntpr-explain">
  <div class="ntpr-explain-cell">
    <h4 style="color:var(--control)">Control</h4>
    <p>Retain the ball, recycle possession, wait for the right opening. Values patience and low-risk progression over speed.</p>
  </div>
  <div class="ntpr-explain-cell">
    <h4 style="color:var(--progression)">Progression</h4>
    <p>Advance the ball through the lines with purpose — combination play and line-breaking passes, not just forward for its own sake.</p>
  </div>
  <div class="ntpr-explain-cell">
    <h4 style="color:var(--direct)">Direct</h4>
    <p>Go forward at every opportunity, as fast as possible — carrying and playing vertically the moment a lane opens.</p>
  </div>
</div>
<p style="font-size:12.5px; color:var(--ink-muted); margin: 6px 2px 0;">Emphasis narrows the profile further within a
Style — e.g. a Centre Back's <b>Ball-Playing</b> Emphasis rewards passing/build-up involvement specifically, on top of
whichever Style is selected. Not every position has the same Emphasis options.</p>
""", unsafe_allow_html=True)

# ---------------- Control bar ----------------
U21_CUTOFF = pd.Timestamp("2004-01-01")

with st.container(border=True):
    row1 = st.columns([1.0, 1.0, 1.3, 1.0, 0.9])
    with row1[0]:
        st.markdown('<div class="ntpr-controlbar-label">Position</div>', unsafe_allow_html=True)
        position = st.selectbox("Position", POSITION_ORDER, format_func=lambda p: POSITION_LABELS[p],
                                 label_visibility="collapsed", key="v2_position")
    with row1[1]:
        st.markdown('<div class="ntpr-controlbar-label">Style</div>', unsafe_allow_html=True)
        style_opts = style_options_for(position)
        style = st.selectbox("Style", style_opts, format_func=style_display,
                              label_visibility="collapsed", key="v2_style")
    with row1[2]:
        st.markdown('<div class="ntpr-controlbar-label">Emphasis</div>', unsafe_allow_html=True)
        emph_opts = emphasis_options_for(position, style)
        emphasis = st.selectbox("Emphasis", emph_opts, format_func=emphasis_display,
                                 label_visibility="collapsed", key="v2_emphasis")
    with row1[3]:
        st.markdown('<div class="ntpr-controlbar-label">Nationality</div>', unsafe_allow_html=True)
        nationality = st.selectbox("Nationality", nationality_options(), label_visibility="collapsed", key="v2_nationality")
    with row1[4]:
        st.markdown('<div class="ntpr-controlbar-label">Recommendations</div>', unsafe_allow_html=True)
        count_choice = st.radio("Count", ["3", "5", "10", "All"], index=1, horizontal=True, label_visibility="collapsed")

    row2 = st.columns([1.0, 3.0])
    with row2[0]:
        st.markdown('<div class="ntpr-controlbar-label">Age eligibility</div>', unsafe_allow_html=True)
        age_eligibility = st.radio("Age eligibility", ["Senior National Team", "U-21 National Team"],
                                    horizontal=True, label_visibility="collapsed")

    generate = st.button("Generate Recommendations →", type="primary")

if generate:
    st.session_state["ntpr_query_v2"] = {
        "position": position, "style": style, "emphasis": emphasis,
        "nationality": nationality, "age_eligibility": age_eligibility, "count": count_choice,
    }
    for k in [k for k in st.session_state if k.startswith("players_auto_b") or k == "players_custom"]:
        st.session_state.pop(k, None)
    for k in [k for k in st.session_state if k.startswith("cmp_")]:
        del st.session_state[k]
    st.session_state.pop("ntpr_expanded", None)

query = st.session_state.get("ntpr_query_v2")

if not query:
    st.markdown('<div class="ntpr-empty">Set your search above and click <b>Generate Recommendations</b> to see results.</div>',
                unsafe_allow_html=True)
else:
    combo_id = combo_id_for(query["position"], query["style"], query["emphasis"])
    scores = f50[f50.combo_id == combo_id].copy()
    df = scores.merge(players, on=["player_id", "season_id", "team_id"], how="inner")

    if query["nationality"] != "All Nationalities":
        df = df[df["nationality"] == query["nationality"]]
    if query["age_eligibility"] == "U-21 National Team":
        dob = pd.to_datetime(df["date_of_birth"], errors="coerce")
        df = df[dob > U21_CUTOFF]

    df = df.sort_values("final_score", ascending=False)
    total_matches = len(df)
    if query["count"] != "All":
        df = df.head(int(query["count"]))
    row_cap_applied = len(df) > MAX_DISPLAYED_ROWS
    if row_cap_applied:
        df = df.head(MAX_DISPLAYED_ROWS)

    combo_label = f'{style_display(query["style"])} / {emphasis_display(query["emphasis"])}'
    age_note = " · <b>U-21 eligible only</b>" if query["age_eligibility"] == "U-21 National Team" else ""
    cap_note = (f' &nbsp;·&nbsp; <span style="color:var(--direct)">showing the top {MAX_DISPLAYED_ROWS} of {total_matches} '
                f'— narrow your search to see the rest</span>') if row_cap_applied else ""
    nationality_badge = (f'{get_flag_html(query["nationality"])} {html.escape(query["nationality"])}'
                          if query["nationality"] != "All Nationalities" else html.escape(query["nationality"]))
    st.markdown(f"""
    <div class="ntpr-contextbar">
      <div>Showing <b>{'All' if query['count']=='All' else 'Top ' + query['count']}</b> ·
        <b>{POSITION_LABELS[query['position']]}</b> · <b style="color:var(--progression)">{html.escape(combo_label)}</b> ·
        <b>{nationality_badge}</b>{age_note}
        &nbsp;·&nbsp; {total_matches} eligible player{'s' if total_matches != 1 else ''} matched{cap_note}</div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.markdown('<div class="ntpr-empty">No players match this search. Try a different position, profile, or nationality.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="ntpr-dossier">', unsafe_allow_html=True)
        expanded_key = st.session_state.get("ntpr_expanded")
        row_keys_this_search = []
        for i, (_, row) in enumerate(df.iterrows()):
            row_key = f"{int(row.player_id)}_{int(row.season_id)}_{int(row.team_id)}"
            row_keys_this_search.append(row_key)
            is_open = expanded_key == row_key

            rcol, ccol, bcol = st.columns([0.90, 0.05, 0.05])
            with rcol:
                st.markdown(render_result_row(i + 1, row, row, combo_label), unsafe_allow_html=True)
            with ccol:
                st.checkbox("Compare", key=f"cmp_{row_key}", label_visibility="collapsed", help="Add to comparison charts")
            with bcol:
                st.markdown('<div class="ntpr-toggle">', unsafe_allow_html=True)
                if st.button("▲" if is_open else "▾", key=f"tog_{row_key}"):
                    st.session_state["ntpr_expanded"] = None if is_open else row_key
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            if is_open:
                st.markdown(render_detail_panel(row, row, combo_label), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- Real-metric comparison charts ----------------
        compare_keys = {k for k in row_keys_this_search if st.session_state.get(f"cmp_{k}")}
        if compare_keys:
            chart_df = df[df.apply(lambda r: f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" in compare_keys, axis=1)]
            scope_note = f"{len(chart_df)} selected player{'s' if len(chart_df) != 1 else ''}"
        else:
            chart_df = df
            scope_note = f"all {len(chart_df)} shown recommendation{'s' if len(chart_df) != 1 else ''} (no players selected for comparison)"

        st.markdown('<h2 style="font-family: var(--font-display); font-size:22px; margin-top:40px;">Real-metric comparison</h2>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:13px; color:var(--ink-muted); margin-top:6px;">These charts are picked automatically -- '
                     f'the real football stats that best separate {"the selected players" if compare_keys else "this shown group"} '
                     f'from each other. Comparing {scope_note}. Tick "Compare" on any row above to narrow this.</p>',
                     unsafe_allow_html=True)

        if len(chart_df) < 2:
            st.markdown('<div class="ntpr-empty">Select at least 2 players (tick "Compare" above) to see real-metric comparison charts.</div>',
                        unsafe_allow_html=True)
        else:
            mstats = load_match_level_stats()
            metric_group_df = chart_df.head(MAX_METRIC_CHART_PLAYERS)
            ref_position_group_df = players[players["position_v2"] == query["position"]]
            all_dm = differentiating_metrics(metric_group_df, mstats, "full_season", k=50)

            candidate_names = {
                f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}": f"{r.player_name} — {r.season_club}"
                for _, r in df.iterrows()
            }
            default_sel = [k for k in candidate_names if k in compare_keys] or \
                          [f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" for _, r in metric_group_df.iterrows()]

            if len(all_dm) < 2:
                st.markdown('<div class="ntpr-empty">Not enough overlapping data across these players to identify meaningful '
                            'differentiating metrics under the Full Season filter.</div>', unsafe_allow_html=True)
            else:
                def _metric_chart_controls(chart_key, title):
                    st.markdown(f'<div style="font-family:var(--font-display); font-weight:600; font-size:15px; margin-top:22px;">{title}</div>',
                                unsafe_allow_html=True)
                    c1, c2, c3 = st.columns([1, 1, 2])
                    with c1:
                        filter_label = st.selectbox("Match filter", list(MATCH_FILTERS.keys()), key=f"filt_{chart_key}")
                    with c2:
                        mode_label = st.radio("Display mode", list(DISPLAY_MODE_COLUMN.keys()), index=1, horizontal=True, key=f"mode_{chart_key}")
                    with c3:
                        ms_kwargs = {} if f"players_{chart_key}" in st.session_state else {"default": default_sel}
                        sel = st.multiselect("Players in this chart", options=list(candidate_names.keys()),
                                              format_func=lambda k: candidate_names[k], key=f"players_{chart_key}", **ms_kwargs)
                    rows = [r for _, r in df.iterrows() if f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" in sel]
                    return MATCH_FILTERS[filter_label], DISPLAY_MODE_COLUMN[mode_label], mode_label, rows

                no_data_msg = ('<div class="ntpr-empty">None of the selected players have data for this metric under the chosen '
                               'match filter. Try a different filter or players.</div>')

                def _render(fig, chart_key):
                    if fig:
                        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=chart_key)
                    else:
                        st.markdown(no_data_msg, unsafe_allow_html=True)

                batch = all_dm[:4]
                if batch:
                    fk, vc, ml, rows = _metric_chart_controls("b1_1", f"{METRIC_LABELS.get(batch[0], batch[0])} — by player")
                    if rows:
                        _render(metric_range_figure(batch[0], METRIC_LABELS.get(batch[0], batch[0]), rows, ref_position_group_df, mstats, fk, vc, ml), "chart_b1_1")
                if len(batch) >= 2:
                    fk, vc, ml, rows = _metric_chart_controls("b1_2", f"{METRIC_LABELS.get(batch[1], batch[1])} — by player")
                    if rows:
                        _render(metric_range_figure(batch[1], METRIC_LABELS.get(batch[1], batch[1]), rows, ref_position_group_df, mstats, fk, vc, ml), "chart_b1_2")
                    fk, vc, ml, rows = _metric_chart_controls("b1_scatter", f"{METRIC_LABELS.get(batch[0], batch[0])} vs. {METRIC_LABELS.get(batch[1], batch[1])}")
                    if rows:
                        _render(scatter_metric_figure(batch[0], batch[1], METRIC_LABELS.get(batch[0], batch[0]), METRIC_LABELS.get(batch[1], batch[1]),
                                                       rows, ref_position_group_df, mstats, fk, vc, ml), "chart_b1_scatter")
                if len(batch) >= 3:
                    x, y, sz = batch[-2], batch[-1], batch[0]
                    fk, vc, ml, rows = _metric_chart_controls("b1_bubble", f"{METRIC_LABELS.get(x, x)} vs. {METRIC_LABELS.get(y, y)} (bubble size: {METRIC_LABELS.get(sz, sz)})")
                    if rows:
                        _render(bubble_metric_figure(x, y, sz, METRIC_LABELS.get(x, x), METRIC_LABELS.get(y, y), METRIC_LABELS.get(sz, sz),
                                                      rows, ref_position_group_df, mstats, fk, vc, ml), "chart_b1_bubble")
