"""
Recommendations page -- UI/UX Redesign Round 1 (2026-08-30).

Search flow reordered to Nationality -> Position(s) -> Style -> Emphasis -> Age Eligibility ->
Count (see search_engine_v2.py for the position-resolution rules). Side-specific search (Right
Back vs Left Back, etc.) is a display/filter distinction only -- the locked V2 8-group scoring
architecture is unchanged; see docs/v2_ui_redesign_round1.md.

Card presentation now leads with Final Score + Global Rank for the selected profile only; internal
components (Professional Score, Opponent Multiplier, Own Club Level) are not shown prominently.
Player explanations are built from real Signal data in football language (explanation_engine_v2.py)
rather than model-engineering contribution breakdowns.
"""
import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.data_loader import load_match_level_stats, METRIC_LABELS, MATCH_FILTERS, DISPLAY_MODE_COLUMN, load_filter_eligibility
from src.data_loader_v2 import (
    load_players, load_f50_scores, load_f50_registry, nationality_options, style_display, emphasis_display,
)
from src import search_engine_v2 as se
from src.cards_v3 import render_result_row, render_detail_panel
from src.charts import differentiating_metrics, metric_range_figure, scatter_metric_figure, bubble_metric_figure, missing_data_players, missing_data_reason, _display_label
from src.chart_relevance import select_priority_metrics, select_five_charts, xy_chart_title
from src.charts_v2 import profile_comparison_figure
from src.explanation_engine_v2 import build_explanation, build_why_fits
from src.nav import render_nav
from src.league_coverage import parse_league_labels, prepare_league_coverage_display, render_league_coverage
from src.nationality_flags import get_flag_html

MAX_METRIC_CHART_PLAYERS = 8
MAX_DISPLAYED_ROWS = 150
U21_CUTOFF = pd.Timestamp("2004-01-01")

render_nav("rec")

players = load_players()
f50 = load_f50_scores()
registry = load_f50_registry()

# ---------------- Hero ----------------
st.markdown("""
<span class="ntpr-kicker">Player recommendation engine — not a ranking platform</span>
<div class="ntpr-h1">Not the best player.<br>The right one for <em>how you play.</em></div>
<p class="ntpr-sub">Every eligible player is rated against every valid Style and Role Emphasis for their
position. A recommendation always means <b>"rated for this exact profile,"</b> never <b>"ranked highest
overall."</b> There is no universal player score — the same player can and does rate very differently for
a different profile.</p>
""", unsafe_allow_html=True)

render_league_coverage(prepare_league_coverage_display(parse_league_labels(players["league_label"])))

st.markdown("""
<div class="ntpr-scope">
  <div class="ic">🛈</div>
  <div>
    <b>Database Scope</b>
    <p>This recommendation engine covers a curated set of European leagues outside the top divisions of the
    "big five" (Premier League, La Liga, Serie A, Bundesliga, Ligue 1) — built to help national teams identify
    players in strong secondary European competitions.</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ================================================================================================
# SEARCH PANEL -- Nationality -> Position(s) -> Style -> Emphasis -> Age -> Count
# ================================================================================================
if "pos_slot_ids" not in st.session_state:
    st.session_state["pos_slot_ids"] = [0]
    st.session_state["pos_slot_next_id"] = 1
    st.session_state["pos_slot_0"] = se.SIDE_POSITION_ORDER[0]

with st.container(border=True):
    st.markdown('<div class="ntpr-controlbar-label" style="font-size:13px;">Nationality</div>', unsafe_allow_html=True)
    nationality = st.selectbox("Nationality", nationality_options(), label_visibility="collapsed", key="v2_nationality")

    st.markdown('<div class="ntpr-controlbar-label" style="margin-top:12px;">Position(s)</div>', unsafe_allow_html=True)
    all_positions_mode = st.checkbox("All Positions (regardless of role)", key="v2_all_positions")

    selected_ui_positions = []
    if not all_positions_mode:
        slot_ids = st.session_state["pos_slot_ids"]
        for i, sid in enumerate(list(slot_ids)):
            already_taken = {st.session_state.get(f"pos_slot_{other}") for other in slot_ids if other != sid}
            opts = [p for p in se.SIDE_POSITION_ORDER if p not in already_taken or p == st.session_state.get(f"pos_slot_{sid}")]
            pc, rc = st.columns([5, 1])
            with pc:
                val = st.selectbox(f"Position {i+1}", opts, key=f"pos_slot_{sid}", label_visibility="collapsed")
                selected_ui_positions.append(val)
            with rc:
                if len(slot_ids) > 1:
                    if st.button("✕", key=f"pos_remove_{sid}", help="Remove this position"):
                        st.session_state["pos_slot_ids"] = [s for s in slot_ids if s != sid]
                        st.rerun()
        if len(selected_ui_positions) < len(se.SIDE_POSITION_ORDER):
            if st.button("+ Add Position", key="pos_add"):
                new_id = st.session_state["pos_slot_next_id"]
                st.session_state["pos_slot_next_id"] += 1
                st.session_state["pos_slot_ids"].append(new_id)
                st.rerun()

    plan = se.plan_search(selected_ui_positions, all_positions_mode)

    row2 = st.columns([1, 1.3, 1, 0.9])
    with row2[0]:
        st.markdown('<div class="ntpr-controlbar-label">Style</div>', unsafe_allow_html=True)
        style = st.selectbox("Style", se.style_options_for_plan(plan, registry), format_func=style_display,
                              label_visibility="collapsed", key="v2_style")
    with row2[1]:
        if plan.mode == "single_full":
            st.markdown('<div class="ntpr-controlbar-label">Role Emphasis</div>', unsafe_allow_html=True)
            emph_opts = se.emphasis_options_for_plan(plan, registry)
            emphasis = st.selectbox("Role Emphasis", emph_opts, format_func=emphasis_display,
                                     label_visibility="collapsed", key="v2_emphasis")
        else:
            emphasis = ()
            st.markdown('<div class="ntpr-controlbar-label">Role Emphasis</div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:12px; color:var(--ink-faint); padding-top:8px;">Not shared across the selected positions</div>', unsafe_allow_html=True)
    with row2[2]:
        st.markdown('<div class="ntpr-controlbar-label">Age eligibility</div>', unsafe_allow_html=True)
        age_eligibility = st.radio("Age eligibility", ["Senior", "U-21"], horizontal=True, label_visibility="collapsed", key="v2_age")
    with row2[3]:
        st.markdown('<div class="ntpr-controlbar-label">Results</div>', unsafe_allow_html=True)
        count_choice = st.radio("Count", ["3", "5", "10", "All"], index=1, horizontal=True, label_visibility="collapsed", key="v2_count")

    generate = st.button("Generate Recommendations →", type="primary")

if generate:
    st.session_state["ntpr_query_v2"] = {
        "positions": selected_ui_positions, "all_positions": all_positions_mode,
        "style": style, "emphasis": emphasis, "nationality": nationality,
        "age_eligibility": age_eligibility, "count": count_choice,
    }
    for k in [k for k in st.session_state if k.startswith("players_auto_b") or k == "players_custom"]:
        st.session_state.pop(k, None)
    for k in [k for k in st.session_state if k.startswith("cmp_")]:
        del st.session_state[k]
    st.session_state.pop("ntpr_expanded", None)

query = st.session_state.get("ntpr_query_v2")

if not query:
    st.markdown('<div class="ntpr-empty">Set your search above and click <b>Generate Recommendations</b> to see results.</div>', unsafe_allow_html=True)
else:
    q_plan = se.plan_search(query["positions"], query["all_positions"])
    combo_map = se.resolve_search(q_plan, query["style"], query.get("emphasis"), registry)  # {group8: combo_id}

    frames = []
    for g8, cid in combo_map.items():
        sub = f50[f50.combo_id == cid]
        frames.append(sub)
    scores = pd.concat(frames, ignore_index=True) if frames else f50.iloc[0:0]
    df = scores.merge(players, on=["player_id", "season_id", "team_id"], how="inner")
    df = se.apply_side_filter(df, q_plan)

    if query["nationality"] != "All Nationalities":
        df = df[df["nationality"] == query["nationality"]]
    if query["age_eligibility"] == "U-21":
        dob = pd.to_datetime(df["date_of_birth"], errors="coerce")
        df = df[dob > U21_CUTOFF]

    df = df.sort_values("final_score", ascending=False)
    total_matches = len(df)
    if query["count"] != "All":
        df = df.head(int(query["count"]))
    row_cap_applied = len(df) > MAX_DISPLAYED_ROWS
    if row_cap_applied:
        df = df.head(MAX_DISPLAYED_ROWS)

    combo_label = f'{style_display(query["style"])}' + (f' / {emphasis_display(query.get("emphasis") or ())}' if q_plan.mode == "single_full" else "")
    age_note = " · <b>U-21 eligible only</b>" if query["age_eligibility"] == "U-21" else ""
    cap_note = (f' &nbsp;·&nbsp; <span style="color:var(--direct)">showing the top {MAX_DISPLAYED_ROWS} of {total_matches} '
                f'— narrow your search to see the rest</span>') if row_cap_applied else ""
    nationality_badge = (f'{get_flag_html(query["nationality"])} {html.escape(query["nationality"])}'
                          if query["nationality"] != "All Nationalities" else html.escape(query["nationality"]))
    st.markdown(f"""
    <div class="ntpr-contextbar">
      <div>Showing <b>{'All' if query['count']=='All' else 'Top ' + query['count']}</b> ·
        <b>{nationality_badge}</b> · <b>{html.escape(q_plan.label)}</b> ·
        <b style="color:var(--progression)">{html.escape(combo_label)}</b>{age_note}
        &nbsp;·&nbsp; {total_matches} eligible player{'s' if total_matches != 1 else ''} matched{cap_note}</div>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.markdown('<div class="ntpr-empty">No players match this search. Try a different position, profile, or nationality.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ntpr-dossier">', unsafe_allow_html=True)
        expanded_key = st.session_state.get("ntpr_expanded")
        row_keys_this_search = []
        for i, (_, row) in enumerate(df.iterrows()):
            row_key = f"{int(row.player_id)}_{int(row.season_id)}_{int(row.team_id)}"
            row_keys_this_search.append(row_key)
            is_open = expanded_key == row_key
            position_label = next((ui for ui, (g8, _) in se.SIDE_POSITIONS.items()
                                    if g8 == row["position_v2"] and row["primary_detailed_position"] in se.SIDE_POSITIONS[ui][1]), row["position_v2"])

            rcol, ccol, bcol = st.columns([0.90, 0.05, 0.05])
            with rcol:
                st.markdown(render_result_row(i + 1, row, row, combo_label, position_label), unsafe_allow_html=True)
            with ccol:
                st.checkbox("Compare", key=f"cmp_{row_key}", label_visibility="collapsed", help="Add to comparison charts")
            with bcol:
                st.markdown('<div class="ntpr-toggle">', unsafe_allow_html=True)
                if st.button("▲" if is_open else "▾", key=f"tog_{row_key}"):
                    st.session_state["ntpr_expanded"] = None if is_open else row_key
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            if is_open:
                row_emphasis_list = list(row.emphasis.split("+")) if row.emphasis != "(none)" else []
                explanation = build_explanation(int(row.player_id), row.season_name, row.position_v2, row.style,
                                                 row_emphasis_list)
                other = se.other_profiles(f50, row, query["style"], registry, exclude_combo=row["combo_id"])
                alternatives = se.emphasis_alternatives(f50, row, row.style, exclude_combo=row["combo_id"])
                why_fits = build_why_fits(row.position_v2, row.style, row_emphasis_list, explanation["facts"],
                                           explanation["profile_label"], explanation["style_label"],
                                           row["final_score"], alternatives)
                st.markdown(render_detail_panel(row, row, combo_label, explanation, other, why_fits), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        same_group = df["position_v2"].nunique() == 1
        compare_keys = {k for k in row_keys_this_search if st.session_state.get(f"cmp_{k}")}
        chart_df = df[df.apply(lambda r: f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" in compare_keys, axis=1)] if compare_keys else df.head(MAX_METRIC_CHART_PLAYERS)
        scope_note = f"{len(chart_df)} selected player{'s' if len(chart_df) != 1 else ''}" if compare_keys else f"the top {len(chart_df)} shown recommendation{'s' if len(chart_df) != 1 else ''} (no players selected for comparison)"

        # ---------------- Profile comparison (same scoring group only) ----------------
        if same_group and len(chart_df) >= 2:
            st.markdown('<h2 style="font-family: var(--font-display); font-size:22px; margin-top:40px;">Profile comparison</h2>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-size:13px; color:var(--ink-muted); margin-top:6px;">Where does each player perform best across '
                        f'different Styles? Comparing {scope_note}, each shown at their base Style score (no Role Emphasis applied).</p>', unsafe_allow_html=True)
            fig = profile_comparison_figure([r for _, r in chart_df.iterrows()], f50, df["position_v2"].iloc[0], style_display)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        elif not same_group and compare_keys:
            st.markdown('<p style="font-size:12px; color:var(--ink-faint); margin-top:24px;">Profile comparison is not shown because the selected '
                        'players are evaluated in different position groups — comparing their Final Scores across Styles would not be meaningful.</p>', unsafe_allow_html=True)

        # ---------------- Standout real-metric charts ----------------
        st.markdown('<h2 style="font-family: var(--font-display); font-size:22px; margin-top:36px;">Standout metrics</h2>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:13px; color:var(--ink-muted); margin-top:6px;">Automatically identified: the real football stats where '
                    f'{"the selected players" if compare_keys else "any player in this recommendation list"} stand out most — not restricted to the '
                    f'top-ranked recommendation. Comparing {scope_note}.</p>', unsafe_allow_html=True)

        if len(chart_df) < 2:
            st.markdown('<div class="ntpr-empty">Select at least 2 players (tick "Compare" above) to see standout-metric charts.</div>', unsafe_allow_html=True)
        else:
            mstats = load_match_level_stats()
            ref_position_group_df = players[players["position_v2"].isin(df["position_v2"].unique())]

            # UI/UX Round 4 (points 9-10): a chart-specific filter (Top/Bottom Opponents, Home/
            # Away, etc.) must never silently remove a player from view -- the original search
            # result stays the comparison population; a player missing real match data for THIS
            # filter/metric combination is now named explicitly rather than just vanishing from
            # the plotted points. Generic across every chart type/position/filter/population (see
            # charts.missing_data_players) -- shared by both the automatic charts and the Custom
            # Chart Builder below.
            # UI/UX Round 5 (points 2-5): reopened as a full data audit rather than accepting the
            # round-4 diagnosis as-is (docs/v2_ui_redesign_round5.md). Confirmed the real, LOCKED
            # mechanism is production/match_level's own per-filter minimum-minutes gate (270
            # minutes specifically against Top/Bottom-Opponent-band matches -- a genuinely
            # different, smaller sample than the player's overall season minutes) -- intentional,
            # evidence-based, NOT changed here. The note now says precisely why per player (no
            # minutes at all vs. some minutes short of the floor) using filter_eligibility.csv.
            filter_eligibility = load_filter_eligibility()

            def _missing_note(rows, metrics, fk, filter_label):
                missing = missing_data_players(rows, mstats, metrics, fk, "percentile_value")
                if not missing:
                    return ""
                lines = "".join(
                    f'<li>{html.escape(_display_label(r))} — {html.escape(missing_data_reason(r, filter_eligibility, fk))}</li>'
                    for r in missing
                )
                return (f'<div style="font-size:11px; color:var(--ink-faint); margin:2px 0 10px;">'
                        f'Not shown for <b>{html.escape(filter_label)}</b>:'
                        f'<ul style="margin:2px 0 0 16px; padding:0;">{lines}</ul></div>')

            all_dm = differentiating_metrics(chart_df.head(MAX_METRIC_CHART_PLAYERS), mstats, "full_season", k=50)
            # UI/UX Round 3 (points 4-6) + Round 5 (points 8-15): reorder the discriminative-
            # power-ordered pool by profile relevance to the SELECTED Style/Emphasis, one
            # representative per football "story" (redundancy group) among the first 5 -- see
            # src/chart_relevance.py. One of the 5 slots is upgraded to a genuine X/Y relationship
            # (e.g. attempts vs successes within one locked domain) when a real, relevant,
            # well-separated pair exists for this profile -- never forced. `all_dm` itself
            # (discriminative order) is preserved unchanged for the Custom Chart Builder below.
            _query_emphasis = list(query.get("emphasis") or ())
            _position_v2 = df["position_v2"].iloc[0]
            _xy_chart_rows = [r for _, r in chart_df.head(MAX_METRIC_CHART_PLAYERS).iterrows()]
            _first5_specs, _rest = select_five_charts(
                all_dm, _position_v2, query["style"], _query_emphasis, _xy_chart_rows, mstats, k=5)

            candidate_names = {
                f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}": f"{r.player_name} — {r.season_club}"
                for _, r in df.iterrows()
            }

            default_sel = [k for k in candidate_names if k in compare_keys] or \
                          [f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" for _, r in chart_df.head(MAX_METRIC_CHART_PLAYERS).iterrows()]

            # UI/UX Round 5 (point 6) -- BUGFIX: every "Players in this chart" multiselect is
            # keyed by a fixed per-chart-slot key (e.g. "players_auto_b1_0") that is REUSED
            # across different searches, so Streamlit's own persisted widget state could keep a
            # PREVIOUS search's players selected/visible even after the population genuinely
            # changed (confirmed reproduction: Scottish Centre Backs -> Spanish Full Backs left
            # Scottish names in the selector). Detected via a stable signature (the current set of
            # candidate keys) stored in session_state -- when it changes, every "players_*"
            # widget's stored selection is pruned down to just the keys still valid in the NEW
            # population, falling back to the new population's own default_sel only if that
            # pruning empties it out entirely (never a blind full reset: an unchanged population
            # leaves existing selections untouched, and a changed one only removes what no longer
            # belongs, re-seeding only when nothing valid would remain to show).
            new_population_sig = frozenset(candidate_names.keys())
            old_population_sig = st.session_state.get("ntpr_population_sig")
            if old_population_sig is not None and old_population_sig != new_population_sig:
                for k in list(st.session_state.keys()):
                    if k.startswith("players_") and isinstance(st.session_state[k], list):
                        pruned = [v for v in st.session_state[k] if v in new_population_sig]
                        if pruned != st.session_state[k]:
                            st.session_state[k] = pruned or list(default_sel)
            st.session_state["ntpr_population_sig"] = new_population_sig

            if len(all_dm) < 2:
                st.markdown('<div class="ntpr-empty">Not enough overlapping data across these players to identify meaningful standout metrics.</div>', unsafe_allow_html=True)
            else:
                def _metric_chart_controls(chart_key, title):
                    if st.session_state.pop(f"_selectall_{chart_key}", False):
                        st.session_state[f"players_{chart_key}"] = list(candidate_names.keys())
                    st.markdown(f'<div style="font-family:var(--font-display); font-weight:600; font-size:15px; margin-top:22px;">{title}</div>', unsafe_allow_html=True)
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
                    return MATCH_FILTERS[filter_label], DISPLAY_MODE_COLUMN[mode_label], mode_label, rows, filter_label

                no_data_msg = '<div class="ntpr-empty">None of the selected players have data for this metric under the chosen match filter.</div>'

                def _render(fig, chart_key, rows=None, metrics=None, fk=None, filter_label=None):
                    if fig:
                        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=chart_key)
                    else:
                        st.markdown(no_data_msg, unsafe_allow_html=True)
                    if rows and metrics and fk and filter_label:
                        note = _missing_note(rows, metrics, fk, filter_label)
                        if note:
                            st.markdown(note, unsafe_allow_html=True)

                # UI/UX Round 3 (point 5) + Round 5 (points 8-15): each chart is its own
                # independent comparison rather than the old "Signal A, Signal B, A+B combined"
                # pattern -- 5 charts = 5 distinct analytical jobs, not the same story decomposed
                # and recombined. The FIRST batch is profile-priority-ordered
                # (chart_relevance.select_five_charts, one metric per relevant football "story",
                # with one slot upgraded to a genuine X/Y relationship where a real, relevant,
                # well-separated pair exists -- point 9); later "+ Show More" batches continue
                # through the remaining discriminative-power-ordered single-metric pool.
                FIRST_BATCH_LABELS = ["Chart 1 — Core Profile Domain", "Chart 2 — Key Behaviour",
                                       "Chart 3 — Complementary Dimension", "Chart 4 — Two-Dimensional Relationship",
                                       "Chart 5 — Complementary Trait"]

                def _render_batch(prefix, specs, labeled=False):
                    if not specs:
                        return
                    for idx, spec in enumerate(specs):
                        if spec["kind"] == "xy":
                            label_x, label_y = METRIC_LABELS.get(spec["metric_x"], spec["metric_x"]), METRIC_LABELS.get(spec["metric_y"], spec["metric_y"])
                            base_title = xy_chart_title(spec["domain"])
                            title = f"{FIRST_BATCH_LABELS[idx]}: {base_title}" if labeled and idx < len(FIRST_BATCH_LABELS) else base_title
                            fk, vc, ml, rows, filter_label = _metric_chart_controls(f"{prefix}_{idx}", title)
                            if rows:
                                fig = scatter_metric_figure(spec["metric_x"], spec["metric_y"], label_x, label_y,
                                                             rows, ref_position_group_df, mstats, fk, vc, ml)
                                _render(fig, f"chart_{prefix}_{idx}", rows=rows, metrics=[spec["metric_x"], spec["metric_y"]], fk=fk, filter_label=filter_label)
                                st.markdown(f'<p style="font-size:11px; color:var(--ink-faint); margin-top:-6px;">'
                                            f'{html.escape(label_x)} (x) vs. {html.escape(label_y)} (y) — dashed lines mark the position average.</p>', unsafe_allow_html=True)
                        else:
                            metric = spec["metric"]
                            title = (f"{FIRST_BATCH_LABELS[idx]}: {METRIC_LABELS.get(metric, metric)}" if labeled and idx < len(FIRST_BATCH_LABELS)
                                      else f"{METRIC_LABELS.get(metric, metric)} — by player")
                            fk, vc, ml, rows, filter_label = _metric_chart_controls(f"{prefix}_{idx}", title)
                            if rows:
                                _render(metric_range_figure(metric, METRIC_LABELS.get(metric, metric), rows, ref_position_group_df, mstats, fk, vc, ml),
                                        f"chart_{prefix}_{idx}", rows=rows, metrics=[metric], fk=fk, filter_label=filter_label)

                st.session_state.setdefault("n_auto_batches", 1)
                n_batches = st.session_state["n_auto_batches"]
                _rest_specs = [dict(kind="range", metric=m) for m in _rest]
                for batch_num in range(1, n_batches + 1):
                    if batch_num == 1:
                        batch_specs = _first5_specs
                    else:
                        start = (batch_num - 2) * 5
                        batch_specs = _rest_specs[start: start + 5]
                    if not batch_specs:
                        break
                    if batch_num > 1:
                        st.markdown('<h3 style="font-family: var(--font-display); font-size:17px; margin-top:30px;">More standout metrics</h3>', unsafe_allow_html=True)
                    _render_batch(f"auto_b{batch_num}", batch_specs, labeled=(batch_num == 1))

                more_available = len(_rest_specs) > (n_batches - 1) * 5
                bcol1, _ = st.columns([1, 3])
                with bcol1:
                    if more_available:
                        if st.button("+ Show 5 More Charts", key="add_auto_batch"):
                            st.session_state["n_auto_batches"] += 1
                            st.rerun()
                    else:
                        st.markdown('<p style="font-size:11.5px; color:var(--ink-faint); margin-top:10px;">No more standout metrics available for this group.</p>', unsafe_allow_html=True)

            # ---------------- Custom Chart Builder ----------------
            st.markdown('<h2 style="font-family: var(--font-display); font-size:22px; margin-top:40px;">Custom Chart</h2>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:13px; color:var(--ink-muted); margin-top:6px;">Pick the chart type, metrics, match filter, '
                        'display mode, and players yourself.</p>', unsafe_allow_html=True)

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
                st.markdown('<div class="ntpr-empty">No players selected for this chart. Tick players above, or use "Select all" below.</div>', unsafe_allow_html=True)
                if st.button("Select all", key="selectall_custom"):
                    st.session_state["_selectall_custom"] = True
                    st.rerun()
            else:
                custom_rows = [r for _, r in df.iterrows() if f"{int(r.player_id)}_{int(r.season_id)}_{int(r.team_id)}" in custom_sel]
                custom_fk, custom_vc = MATCH_FILTERS[custom_filter_label], DISPLAY_MODE_COLUMN[custom_mode_label]
                if chart_type == "Range / Dot":
                    custom_fig = metric_range_figure(metric_x, METRIC_LABELS[metric_x], custom_rows, ref_position_group_df, mstats, custom_fk, custom_vc, custom_mode_label)
                elif chart_type == "Scatter":
                    custom_fig = scatter_metric_figure(metric_x, metric_y, METRIC_LABELS[metric_x], METRIC_LABELS[metric_y],
                                                        custom_rows, ref_position_group_df, mstats, custom_fk, custom_vc, custom_mode_label)
                else:
                    custom_fig = bubble_metric_figure(metric_x, metric_y, metric_size, METRIC_LABELS[metric_x], METRIC_LABELS[metric_y],
                                                       METRIC_LABELS[metric_size], custom_rows, ref_position_group_df, mstats, custom_fk, custom_vc, custom_mode_label)
                if custom_fig:
                    st.plotly_chart(custom_fig, width="stretch", config={"displayModeBar": False}, key="chart_custom")
                else:
                    st.markdown('<div class="ntpr-empty">None of the selected players have data for this metric under the chosen match filter.</div>', unsafe_allow_html=True)
                custom_metrics = [m for m in (metric_x, metric_y, metric_size) if m]
                custom_note = _missing_note(custom_rows, custom_metrics, custom_fk, custom_filter_label)
                if custom_note:
                    st.markdown(custom_note, unsafe_allow_html=True)
