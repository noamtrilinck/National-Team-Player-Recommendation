"""
Recommendations page -- Sprint 1 + Sprint 2 + Sprint 3a + Sprint 3b + Sprint 4.

Sprint 1: application shell, search controls, recommendation generation, player result cards.
Sprint 2: expandable player detail panel (click a row's Details button).
Sprint 3a: player selection for comparison + the fixed Chart 1 (attacking philosophy
comparison). Sprint 3b: the AI-selected real-metric charts (range/scatter/bubble), each with
its own independent match filter, display mode, and player selection -- extended post-launch
with "Add Automatic Charts" (renders further batches of 4, ranked from the same one-time
differentiating-metrics call, so later batches never repeat a metric already shown). Sprint 4:
the Custom Chart Builder (manual chart type/metric/filter/display-mode/player picks), reusing
the same chart-rendering functions. Sprint 5 moved this out of app.py into its own routed page.
Post-launch: added the Age eligibility filter (Senior/U-21), removed the Last 3/6 Months match
filters, and switched every chart's default display mode from Raw to Per 90 -- see
dashboard/docs/roadmap.md.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.data_loader import (
    load_players, nationality_options, specific_positions_for, load_match_level_stats,
    METRIC_LABELS, MATCH_FILTERS, DISPLAY_MODE_COLUMN,
)
from src.cards import render_result_row, render_detail_panel
from src.charts import (
    philosophy_comparison_figure, differentiating_metrics, metric_range_figure,
    scatter_metric_figure, bubble_metric_figure,
)
from src.nav import render_nav

MAX_METRIC_CHART_PLAYERS = 8  # PLAYER_COLORS has 8 distinct colours; beyond this a chart reads as clutter, not comparison.
MAX_DISPLAYED_ROWS = 150  # Each row renders 2 real Streamlit widgets (checkbox + toggle) on top of
# the HTML -- a broad "All" search can match thousands of players (the full database is 7,568),
# and rendering that many widgets in one run is slow enough to make the page unresponsive rather
# than just slow. Capping the RENDERED rows (never the underlying match count, which is always
# reported honestly) keeps the page usable; the empty-state/context-bar copy makes the cap explicit
# rather than silently truncating.

render_nav("rec")

# ---------------- Hero ----------------
st.markdown("""
<span class="ntpr-kicker">Player recommendation engine — not a ranking platform</span>
<div class="ntpr-h1">Not the best player.<br>The right one for <em>how you play.</em></div>
<p class="ntpr-sub">Every eligible player is evaluated against three attacking philosophies — Control, Progression, Direct —
plus one fixed defensive standard. A recommendation always means <b>"fits the style you selected,"</b> never
<b>"ranked highest overall."</b> There is no combined score, and there never will be one.</p>
<div class="ntpr-notthis">
  <div><div class="lbl">What this isn't</div><div class="no">A universal player ranking</div></div>
  <div><div class="lbl">What this is</div><div class="yes">A style-fit recommendation, with evidence</div></div>
</div>
""", unsafe_allow_html=True)

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

# ---------------- Philosophy explainer ----------------
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
""", unsafe_allow_html=True)

# ---------------- Control bar ----------------
players = load_players()

U21_CUTOFF = pd.Timestamp("2004-01-01")  # UEFA U-21 Euro eligibility: born strictly after this date.

with st.container(border=True):
    row1 = st.columns([1.1, 1.1, 1.3, 1.1, 0.9])
    with row1[0]:
        st.markdown('<div class="ntpr-controlbar-label">Nationality</div>', unsafe_allow_html=True)
        nationality = st.selectbox("Nationality", nationality_options(), label_visibility="collapsed")
    with row1[1]:
        st.markdown('<div class="ntpr-controlbar-label">Broad position</div>', unsafe_allow_html=True)
        broad_position = st.radio("Broad position", ["All", "Defence", "Midfield", "Attack"],
                                   horizontal=True, label_visibility="collapsed")
    with row1[2]:
        st.markdown('<div class="ntpr-controlbar-label">Specific position (optional)</div>', unsafe_allow_html=True)
        specific_positions = st.multiselect("Specific position", specific_positions_for(broad_position),
                                             label_visibility="collapsed")
    with row1[3]:
        st.markdown('<div class="ntpr-controlbar-label">Age eligibility</div>', unsafe_allow_html=True)
        age_eligibility = st.radio("Age eligibility", ["Senior National Team", "U-21 National Team"],
                                    horizontal=True, label_visibility="collapsed")
    with row1[4]:
        st.markdown('<div class="ntpr-controlbar-label">Recommendations</div>', unsafe_allow_html=True)
        count_choice = st.radio("Count", ["3", "5", "10", "All"], index=1, horizontal=True, label_visibility="collapsed")

    st.markdown('<div class="ntpr-controlbar-label" style="margin-top:14px;">Attacking philosophy</div>', unsafe_allow_html=True)
    philosophy = st.radio("Attacking philosophy", ["Control", "Progression", "Direct"], index=1,
                           horizontal=True, label_visibility="collapsed")

    generate = st.button("Generate Recommendations →", type="primary")

# ---------------- Recommendation generation ----------------
if generate:
    st.session_state["ntpr_query"] = {
        "nationality": nationality, "broad_position": broad_position,
        "specific_positions": specific_positions, "age_eligibility": age_eligibility,
        "count": count_choice, "philosophy": philosophy,
    }
    # A new search produces a new results population -- any per-chart player selection from the
    # PREVIOUS search's results would reference row keys that no longer exist among the new
    # options, which Streamlit silently collapses to an empty selection rather than erroring.
    # Clearing these here (before the widgets are recreated below) lets them reseed fresh against
    # the new results, rather than leaving the metric charts stuck on "no players selected."
    # "auto_b" covers every auto-chart batch (however many the user has added via "Add Automatic
    # Charts"), not just the first -- a static key list can't, since the batch count is dynamic.
    for k in [k for k in st.session_state if k.startswith("players_auto_b") or k == "players_custom"]:
        st.session_state.pop(k, None)
    st.session_state["n_auto_batches"] = 1
    # Same class of bug for "Compare" checkboxes and the expanded detail panel: row_key is built
    # from player_id/season_id/team_id, which is STABLE identity -- if the same player-season
    # reappears in a new, unrelated search (e.g. they rank highly under more than one philosophy),
    # their checkbox/panel state from the previous search would silently carry over without the
    # user having touched anything in the current search. Clear both on every new search.
    for k in [k for k in st.session_state if k.startswith("cmp_")]:
        del st.session_state[k]
    st.session_state.pop("ntpr_expanded", None)

query = st.session_state.get("ntpr_query")

if not query:
    st.markdown('<div class="ntpr-empty">Set your search above and click <b>Generate Recommendations</b> to see results.</div>',
                unsafe_allow_html=True)
else:
    df = players.copy()
    if query["nationality"] != "All Nationalities":
        df = df[df["nationality"] == query["nationality"]]
    if query["broad_position"] != "All":
        df = df[df["position_group_broad"] == query["broad_position"]]
    if query["specific_positions"]:
        df = df[df["primary_detailed_position"].isin(query["specific_positions"])]
    if query["age_eligibility"] == "U-21 National Team":
        # Eligible for the next UEFA U-21 Euro: born strictly after 1 Jan 2004. A player with no
        # recorded date of birth can't be confirmed eligible, so they're excluded here (they still
        # show up fine under Senior) rather than assumed eligible.
        dob = pd.to_datetime(df["date_of_birth"], errors="coerce")
        df = df[dob > U21_CUTOFF]

    phil_col = {"Control": "phil_control", "Progression": "phil_progression", "Direct": "phil_direct"}[query["philosophy"]]
    df = df.sort_values(phil_col, ascending=False)

    total_matches = len(df)
    if query["count"] != "All":
        df = df.head(int(query["count"]))
    row_cap_applied = len(df) > MAX_DISPLAYED_ROWS
    if row_cap_applied:
        df = df.head(MAX_DISPLAYED_ROWS)

    pos_label = query["broad_position"] if not query["specific_positions"] else ", ".join(query["specific_positions"])
    age_note = " · <b>U-21 eligible only</b>" if query["age_eligibility"] == "U-21 National Team" else ""
    cap_note = (f' &nbsp;·&nbsp; <span style="color:var(--direct)">showing the top {MAX_DISPLAYED_ROWS} of {total_matches} '
                f'— narrow your search (nationality or position) to see the rest</span>') if row_cap_applied else ""
    st.markdown(f"""
    <div class="ntpr-contextbar">
      <div>Showing <b>{'All' if query['count']=='All' else 'Top ' + query['count']}</b> ·
        <b>{query['nationality']}</b> · <b>{pos_label}</b>{age_note} · ranked by <b style="color:{'var(--control)' if query['philosophy']=='Control' else 'var(--progression)' if query['philosophy']=='Progression' else 'var(--direct)'}">{query['philosophy']}</b>
        &nbsp;·&nbsp; {total_matches} eligible player{'s' if total_matches != 1 else ''} matched{cap_note}</div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.markdown('<div class="ntpr-empty">No players match this search. Try a broader position or a different nationality.</div>',
                    unsafe_allow_html=True)
    else:
        # Each row is real HTML (matches the design spec exactly) plus real Streamlit controls
        # for the compare checkbox and the expand/collapse trigger -- markdown-only HTML can't
        # fire a Python rerun on click, so the row is split into columns rather than one single
        # HTML block, unlike Sprint 1.
        st.markdown('<div class="ntpr-dossier">', unsafe_allow_html=True)
        expanded_key = st.session_state.get("ntpr_expanded")
        row_keys_this_search = []
        for i, (_, row) in enumerate(df.iterrows()):
            row_key = f"{int(row.player_id)}_{int(row.season_id)}_{int(row.team_id)}"
            row_keys_this_search.append(row_key)
            is_open = expanded_key == row_key

            rcol, ccol, bcol = st.columns([0.90, 0.05, 0.05])
            with rcol:
                st.markdown(render_result_row(i + 1, row, query["philosophy"]), unsafe_allow_html=True)
            with ccol:
                st.checkbox("Compare", key=f"cmp_{row_key}", label_visibility="collapsed",
                             help="Add to comparison charts")
            with bcol:
                st.markdown('<div class="ntpr-toggle">', unsafe_allow_html=True)
                if st.button("▲" if is_open else "▾", key=f"tog_{row_key}"):
                    st.session_state["ntpr_expanded"] = None if is_open else row_key
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            if is_open:
                st.markdown(render_detail_panel(row, query["philosophy"]), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- Comparison charts (Sprint 3a: Chart 1 only) ----------------
        compare_keys = {k for k in row_keys_this_search if st.session_state.get(f"cmp_{k}")}
        if compare_keys:
            chart_df = df[df.apply(lambda r: f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" in compare_keys, axis=1)]
            scope_note = f"{len(chart_df)} selected player{'s' if len(chart_df) != 1 else ''}"
        else:
            chart_df = df
            scope_note = f"all {len(chart_df)} shown recommendation{'s' if len(chart_df) != 1 else ''} (no players selected for comparison)"

        st.markdown('<h2 style="font-family: var(--font-display); font-size:22px; margin-top:40px;">Comparison charts</h2>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:13px; color:var(--ink-muted); margin-top:6px;">Comparing {scope_note}. '
                     f'Tick "Compare" on any row above to narrow this to specific players.</p>', unsafe_allow_html=True)

        if len(chart_df) < 1:
            st.markdown('<div class="ntpr-empty">No players selected. Select one or more players above, or clear the selection to compare all shown recommendations.</div>',
                        unsafe_allow_html=True)
        else:
            ref_position_group = chart_df["position_group_broad"].mode().iloc[0]
            reference_df = players[players["position_group_broad"] == ref_position_group]
            fig = philosophy_comparison_figure(
                [row for _, row in chart_df.iterrows()], reference_df,
                reference_label=ref_position_group,
            )
            st.markdown(f'<div style="font-family:var(--font-display); font-weight:600; font-size:15px; margin-top:14px;">'
                        f'Attacking Philosophy Comparison</div>'
                        f'<div style="font-family:var(--font-mono); font-size:10.5px; color:var(--ink-faint); text-transform:uppercase; margin-bottom:8px;">'
                        f'Control · Progression · Direct — vs. {ref_position_group} league-wide average &amp; max</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            st.markdown('<p style="font-size:11.5px; color:var(--ink-faint);">Fixed chart — always scores, never affected by a match filter.</p>',
                        unsafe_allow_html=True)

            # ---------------- Comparison charts (Sprint 3b: AI-selected real metrics) ----------------
            mstats = load_match_level_stats()
            metric_group_df = chart_df.head(MAX_METRIC_CHART_PLAYERS)
            # k=50 comfortably covers the entire curated metric pool (27 metrics) -- this ranks
            # ALL of them once, up front, so "Add Automatic Charts" can hand out further batches
            # of 4 with zero risk of repeating a metric already shown (each metric appears in this
            # ranking exactly once; batches are disjoint slices of it, not independent re-picks).
            all_dm = differentiating_metrics(metric_group_df, mstats, "full_season", k=50)
            st.session_state.setdefault("n_auto_batches", 1)

            st.markdown('<h2 style="font-family: var(--font-display); font-size:22px; margin-top:36px;">Real-metric comparison</h2>',
                        unsafe_allow_html=True)
            st.markdown(f'<p style="font-size:13px; color:var(--ink-muted); margin-top:6px;">These charts are picked automatically -- '
                        f'the real football stats that best separate {"the selected players" if compare_keys else "this shown group"} '
                        f'from each other, not just whichever numbers are largest. Each chart has its own match filter, display mode '
                        f'(Per 90 / Raw / Percentile), and player selection'
                        f'{" (capped at " + str(MAX_METRIC_CHART_PLAYERS) + " players for readability)" if len(chart_df) > MAX_METRIC_CHART_PLAYERS else ""}.</p>',
                        unsafe_allow_html=True)

            ref_position_group_mstats = players[players["position_group_broad"] == ref_position_group]
            candidate_names = {
                f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}": f"{r.player_name} — {r.season_club}"
                for _, r in df.iterrows()
            }
            default_sel = [k for k in candidate_names if k in compare_keys] or \
                          [f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" for _, r in metric_group_df.iterrows()]

            if len(all_dm) < 2:
                st.markdown('<div class="ntpr-empty">Not enough overlapping data across these players to identify meaningful '
                            'differentiating metrics under the Full Season filter. Try selecting more players to compare.</div>',
                            unsafe_allow_html=True)
            else:
                def _metric_chart_controls(chart_key, title):
                    # A pending "Select all" click sets the widget's session_state value BEFORE
                    # the multiselect below is instantiated -- Streamlit forbids writing to a
                    # widget's key in the same run it was created, so the reset has to land here,
                    # one run ahead, rather than right after the button click.
                    if st.session_state.pop(f"_selectall_{chart_key}", False):
                        st.session_state[f"players_{chart_key}"] = list(candidate_names.keys())

                    st.markdown(f'<div style="font-family:var(--font-display); font-weight:600; font-size:15px; margin-top:22px;">{title}</div>',
                                unsafe_allow_html=True)
                    c1, c2, c3 = st.columns([1, 1, 2])
                    with c1:
                        filter_label = st.selectbox("Match filter", list(MATCH_FILTERS.keys()), key=f"filt_{chart_key}")
                    with c2:
                        # index=1 -> "Per 90" is the default display mode (was "Raw").
                        mode_label = st.radio("Display mode", list(DISPLAY_MODE_COLUMN.keys()), index=1,
                                               horizontal=True, key=f"mode_{chart_key}")
                    with c3:
                        # `default` only applies on this widget's first-ever render; once its key
                        # is already in session_state (any later rerun), passing default alongside
                        # it triggers a harmless-but-noisy Streamlit warning -- so it's omitted then.
                        ms_kwargs = {} if f"players_{chart_key}" in st.session_state else {"default": default_sel}
                        sel = st.multiselect("Players in this chart", options=list(candidate_names.keys()),
                                              format_func=lambda k: candidate_names[k], key=f"players_{chart_key}", **ms_kwargs)
                    if not sel:
                        st.markdown('<div class="ntpr-empty">No players selected for this chart. Tick players above, or use "Select all" below.</div>',
                                    unsafe_allow_html=True)
                        if st.button("Select all", key=f"selectall_{chart_key}"):
                            st.session_state[f"_selectall_{chart_key}"] = True
                            st.rerun()
                    rows = [r for _, r in df.iterrows() if f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" in sel]
                    return MATCH_FILTERS[filter_label], DISPLAY_MODE_COLUMN[mode_label], mode_label, rows

                no_data_msg = ('<div class="ntpr-empty">None of the selected players have data for this metric under the chosen '
                               'match filter (e.g. no minutes played in that filter window). Try a different filter or players.</div>')

                def _render(fig, chart_key):
                    if fig:
                        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=chart_key)
                    else:
                        st.markdown(no_data_msg, unsafe_allow_html=True)

                def _render_batch(prefix, b):
                    """Renders up to 4 charts (2 range + 1 scatter + 1 bubble) from a batch of up
                    to 4 differentiating metrics -- the same shape as the original fixed 4-chart
                    set, just parameterised so "Add Automatic Charts" can produce more of them.
                    Degrades gracefully with fewer than 4 metrics (a final partial batch): scatter
                    needs 2, bubble needs 3 (reusing the batch's own metrics for its axes, exactly
                    like the original 4-metric case did)."""
                    if not b:
                        return
                    fk, vc, ml, rows = _metric_chart_controls(f"{prefix}_1", f"{METRIC_LABELS.get(b[0], b[0])} — by player")
                    if rows:
                        fig = metric_range_figure(b[0], METRIC_LABELS.get(b[0], b[0]), rows, ref_position_group_mstats, mstats, fk, vc, ml)
                        _render(fig, f"chart_{prefix}_1")

                    if len(b) >= 2:
                        fk, vc, ml, rows = _metric_chart_controls(f"{prefix}_2", f"{METRIC_LABELS.get(b[1], b[1])} — by player")
                        if rows:
                            fig = metric_range_figure(b[1], METRIC_LABELS.get(b[1], b[1]), rows, ref_position_group_mstats, mstats, fk, vc, ml)
                            _render(fig, f"chart_{prefix}_2")

                        fk, vc, ml, rows = _metric_chart_controls(f"{prefix}_scatter", f"{METRIC_LABELS.get(b[0], b[0])} vs. {METRIC_LABELS.get(b[1], b[1])}")
                        if rows:
                            fig = scatter_metric_figure(b[0], b[1], METRIC_LABELS.get(b[0], b[0]), METRIC_LABELS.get(b[1], b[1]),
                                                         rows, ref_position_group_mstats, mstats, fk, vc, ml)
                            _render(fig, f"chart_{prefix}_scatter")

                    if len(b) >= 3:
                        x, y, sz = b[-2], b[-1], b[0]
                        fk, vc, ml, rows = _metric_chart_controls(
                            f"{prefix}_bubble", f"{METRIC_LABELS.get(x, x)} vs. {METRIC_LABELS.get(y, y)} (bubble size: {METRIC_LABELS.get(sz, sz)})")
                        if rows:
                            fig = bubble_metric_figure(x, y, sz, METRIC_LABELS.get(x, x), METRIC_LABELS.get(y, y), METRIC_LABELS.get(sz, sz),
                                                        rows, ref_position_group_mstats, mstats, fk, vc, ml)
                            _render(fig, f"chart_{prefix}_bubble")

                n_batches = st.session_state["n_auto_batches"]
                for batch_num in range(1, n_batches + 1):
                    batch_metrics = all_dm[(batch_num - 1) * 4: batch_num * 4]
                    if not batch_metrics:
                        break
                    if batch_num > 1:
                        st.markdown('<h3 style="font-family: var(--font-display); font-size:17px; margin-top:30px;">More automatic charts</h3>'
                                    '<p style="font-size:12px; color:var(--ink-muted);">Next best differentiating metrics, never repeating one already shown above.</p>',
                                    unsafe_allow_html=True)
                    _render_batch(f"auto_b{batch_num}", batch_metrics)

                more_available = len(all_dm) > n_batches * 4
                bcol1, _ = st.columns([1, 3])
                with bcol1:
                    if more_available:
                        if st.button("+ Add Automatic Charts", key="add_auto_batch"):
                            st.session_state["n_auto_batches"] += 1
                            st.rerun()
                    else:
                        st.markdown('<p style="font-size:11.5px; color:var(--ink-faint); margin-top:10px;">'
                                    'No more differentiating metrics available for this group.</p>', unsafe_allow_html=True)

            # ---------------- Custom Chart Builder (Sprint 4) ----------------
            st.markdown('<h2 style="font-family: var(--font-display); font-size:22px; margin-top:40px;">Build your own chart</h2>',
                        unsafe_allow_html=True)
            st.markdown('<p style="font-size:13px; color:var(--ink-muted); margin-top:6px;">Pick the chart type, metrics, match filter, '
                        'display mode, and players yourself -- independent of the AI-selected charts above and of each other.</p>',
                        unsafe_allow_html=True)

            if st.session_state.pop("_selectall_custom", False):
                st.session_state["players_custom"] = list(candidate_names.keys())

            metric_options = list(METRIC_LABELS.keys())
            cc1, cc2 = st.columns([1, 3])
            with cc1:
                chart_type = st.radio("Chart type", ["Range / Dot", "Scatter", "Bubble"], key="custom_chart_type")
            with cc2:
                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    metric_x = st.selectbox("Metric" if chart_type == "Range / Dot" else "X-axis metric",
                                             metric_options, format_func=lambda k: METRIC_LABELS[k], key="custom_metric_x")
                metric_y, metric_size = None, None
                if chart_type in ("Scatter", "Bubble"):
                    with mc2:
                        metric_y = st.selectbox("Y-axis metric", metric_options, index=1,
                                                 format_func=lambda k: METRIC_LABELS[k], key="custom_metric_y")
                if chart_type == "Bubble":
                    with mc3:
                        metric_size = st.selectbox("Bubble size metric", metric_options, index=2,
                                                    format_func=lambda k: METRIC_LABELS[k], key="custom_metric_size")

            cf1, cf2, cf3 = st.columns([1, 1, 2])
            with cf1:
                custom_filter_label = st.selectbox("Match filter", list(MATCH_FILTERS.keys()), key="filt_custom")
            with cf2:
                custom_mode_label = st.radio("Display mode", list(DISPLAY_MODE_COLUMN.keys()), index=1, horizontal=True, key="mode_custom")
            with cf3:
                custom_ms_kwargs = {} if "players_custom" in st.session_state else {"default": default_sel}
                custom_sel = st.multiselect("Players in this chart", options=list(candidate_names.keys()),
                                             format_func=lambda k: candidate_names[k], key="players_custom", **custom_ms_kwargs)

            if not custom_sel:
                st.markdown('<div class="ntpr-empty">No players selected for this chart. Tick players above, or use "Select all" below.</div>',
                            unsafe_allow_html=True)
                if st.button("Select all", key="selectall_custom"):
                    st.session_state["_selectall_custom"] = True
                    st.rerun()
            else:
                custom_rows = [r for _, r in df.iterrows() if f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" in custom_sel]
                custom_fk, custom_vc = MATCH_FILTERS[custom_filter_label], DISPLAY_MODE_COLUMN[custom_mode_label]
                custom_fig = None
                if chart_type == "Range / Dot":
                    custom_fig = metric_range_figure(metric_x, METRIC_LABELS[metric_x], custom_rows,
                                                       ref_position_group_mstats, mstats, custom_fk, custom_vc, custom_mode_label)
                elif chart_type == "Scatter":
                    custom_fig = scatter_metric_figure(metric_x, metric_y, METRIC_LABELS[metric_x], METRIC_LABELS[metric_y],
                                                         custom_rows, ref_position_group_mstats, mstats, custom_fk, custom_vc, custom_mode_label)
                else:
                    custom_fig = bubble_metric_figure(metric_x, metric_y, metric_size, METRIC_LABELS[metric_x], METRIC_LABELS[metric_y],
                                                        METRIC_LABELS[metric_size], custom_rows, ref_position_group_mstats, mstats,
                                                        custom_fk, custom_vc, custom_mode_label)
                if custom_fig:
                    st.plotly_chart(custom_fig, width="stretch", config={"displayModeBar": False}, key="chart_custom")
                else:
                    st.markdown('<div class="ntpr-empty">None of the selected players have data for this metric under the chosen '
                                'match filter (e.g. no minutes played in that filter window). Try a different filter or players.</div>',
                                unsafe_allow_html=True)

                st.markdown('<p style="font-size:11.5px; color:var(--ink-faint);">Reference lines/markers show the position average and max '
                            'for the broad position group shown, under each chart\'s own filter and display mode.</p>', unsafe_allow_html=True)
