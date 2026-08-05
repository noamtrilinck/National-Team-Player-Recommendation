"""
Comparison charts -- Sprint 3a (fixed Chart 1: attacking philosophy comparison) + Sprint 3b
(the AI-selected real-metric charts: range/dot, scatter, bubble -- built on real per-90/raw/
percentile match-level stats, never Ability/Philosophy/Defensive scores).
"""
import pandas as pd
import plotly.graph_objects as go

PHIL_COLOR = {"Control": "#33587F", "Progression": "#1B7A50", "Direct": "#A8650E"}
PHIL_COLS = {"Control": "phil_control", "Progression": "phil_progression", "Direct": "phil_direct"}

# Muted "player identity" palette -- deliberately distinct from the philosophy colours above,
# so a dot's colour is never confused with a philosophy's colour. Same reasoning as the design
# spec's separate p1..p5 palette.
PLAYER_COLORS = ["#A6633D", "#4C7A78", "#7A5A72", "#94812F", "#5C7A4A", "#8C4569", "#3E6B8F", "#B0762E"]

JOIN_KEY = ["player_id", "season_id", "team_id"]
REF_MARKER_COLOR = "#8A9088"


def _display_label(row):
    """player_name alone isn't a safe chart identity -- 95 confirmed pairs of genuinely different
    players (different player_id) share the same displayed name in this database (e.g. three
    different "A. Keita"s from three different countries). Used as a bare category/legend label,
    that collision would visually merge two different people onto the same row or legend entry.
    Appending the club disambiguates using the same convention already used in the player-picker
    dropdowns (f"{name} — {club}")."""
    return f'{row["player_name"]} ({row["season_club"]})' if pd.notna(row.get("season_club")) else row["player_name"]


def philosophy_comparison_figure(selected_rows, reference_df, reference_label):
    """selected_rows: list of player rows (dict-like, from players.csv) to compare.
    reference_df: players.csv rows defining the reference population (position-scoped).
    reference_label: human-readable description of that reference population, for the caption."""
    philosophies = ["Control", "Progression", "Direct"]
    fig = go.Figure()

    avg = {p: reference_df[PHIL_COLS[p]].mean() for p in philosophies}
    mx = {p: reference_df[PHIL_COLS[p]].max() for p in philosophies}

    # Reference: position average (line marker) and position max (diamond), one legend entry each.
    fig.add_trace(go.Scatter(
        x=[avg[p] for p in philosophies], y=philosophies, mode="markers",
        marker=dict(symbol="line-ns", size=22, line=dict(width=3, color="#8A9088")),
        name="Position average", hovertemplate="Position average: %{x:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[mx[p] for p in philosophies], y=philosophies, mode="markers",
        marker=dict(symbol="diamond-open", size=11, line=dict(width=2, color="#8A9088")),
        name="Position max", hovertemplate="Position max: %{x:.1f}<extra></extra>",
    ))

    for i, row in enumerate(selected_rows):
        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        xs = [row[PHIL_COLS[p]] for p in philosophies]
        fig.add_trace(go.Scatter(
            x=xs, y=philosophies, mode="markers", marker=dict(size=15, color=color, line=dict(width=1.5, color="white")),
            name=_display_label(row),
            customdata=[[row["player_name"], row["season_club"], row["league_label"], row["primary_detailed_position"]]] * 3,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>"
                "%{customdata[3]}<br>%{y}: %{x:.1f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        xaxis=dict(range=[0, 100], title="Score (0-100)", gridcolor="#E7EAE1"),
        yaxis=dict(title=None, categoryorder="array", categoryarray=list(reversed(philosophies))),
        height=320, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Plex Sans, sans-serif", size=12),
    )
    return fig


# ==================== Sprint 3b: AI-selected real-metric charts ====================

def _metric_lookup(mstats, keys_df, metric, filter_key, value_col):
    """{(player_id, season_id, team_id): value} for one metric/filter/display-mode combination,
    scoped to exactly the player-seasons in keys_df."""
    sub = mstats[(mstats["metric"] == metric) & (mstats["filter_key"] == filter_key)]
    sub = sub.merge(keys_df[JOIN_KEY], on=JOIN_KEY, how="inner")
    return {tuple(k): v for k, v in zip(sub[JOIN_KEY].itertuples(index=False, name=None), sub[value_col])}


def differentiating_metrics(chart_df, mstats, filter_key, k=4, min_players=2):
    """Ranks the curated metric pool by how much they actually separate the players CURRENTLY
    IN VIEW (never the whole database) -- the group's percentile spread on that metric, under the
    given match filter. Percentile (not raw/per-90) is the ranking basis because it's already
    position-normalised and on a fixed 0-100 scale, so a spread of "40" means the same thing for
    Touches as for Aerial Duels Won -- raw/per-90 values can't be compared like that across
    metrics with different units. A metric needs at least `min_players` players with real values
    under this filter to be considered, so a filter with heavy missingness (e.g. Away, for a
    home-only player) doesn't surface a metric only one player actually has data for."""
    keys_df = chart_df[JOIN_KEY]
    sub = mstats[mstats["filter_key"] == filter_key].merge(keys_df, on=JOIN_KEY, how="inner")
    if sub.empty:
        return []
    pivot = sub.pivot_table(index=JOIN_KEY, columns="metric", values="percentile_value")
    threshold = min(min_players, len(keys_df))
    counts = pivot.count()
    spread = (pivot.max() - pivot.min())[counts >= threshold].dropna().sort_values(ascending=False)
    return spread.index.tolist()[:k]


def _reference_stats(mstats, reference_df, metric, filter_key, value_col):
    ref_lookup = _metric_lookup(mstats, reference_df, metric, filter_key, value_col)
    values = [v for v in ref_lookup.values() if pd.notna(v)]
    if not values:
        return float("nan"), float("nan")
    return sum(values) / len(values), max(values)


def _player_points(chart_rows, mstats, metric, filter_key, value_col):
    """Returns (row, value, color) for each selected player that actually has a value for this
    metric/filter combination -- players without one (e.g. no Away minutes) are silently dropped
    from THIS chart rather than plotted as zero, which would misrepresent them as having played
    and performed poorly."""
    keys_df = pd.DataFrame([{k: r[k] for k in JOIN_KEY} for r in chart_rows])
    lookup = _metric_lookup(mstats, keys_df, metric, filter_key, value_col)
    points = []
    for i, row in enumerate(chart_rows):
        key = tuple(row[k] for k in JOIN_KEY)
        val = lookup.get(key)
        if val is None or pd.isna(val):
            continue
        points.append((row, val, PLAYER_COLORS[i % len(PLAYER_COLORS)]))
    return points


def metric_range_figure(metric, metric_label, chart_rows, reference_df, mstats, filter_key, value_col, mode_label):
    """Chart type 1: a horizontal dot/range plot -- one metric, every selected player as a dot,
    plus the position average (line marker) and position max (open diamond), same visual language
    as Chart 1 so the whole comparison-chart section reads as one family."""
    avg, mx = _reference_stats(mstats, reference_df, metric, filter_key, value_col)
    points = sorted(_player_points(chart_rows, mstats, metric, filter_key, value_col), key=lambda p: p[1], reverse=True)
    if not points:
        return None

    fig = go.Figure()
    names = [_display_label(p[0]) for p in points]
    fig.add_trace(go.Scatter(
        x=[avg] * len(names), y=names, mode="markers",
        marker=dict(symbol="line-ns", size=22, line=dict(width=3, color=REF_MARKER_COLOR)),
        name="Position average", hovertemplate=f"Position average: %{{x:.1f}}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[mx] * len(names), y=names, mode="markers",
        marker=dict(symbol="diamond-open", size=11, line=dict(width=2, color=REF_MARKER_COLOR)),
        name="Position max", hovertemplate=f"Position max: %{{x:.1f}}<extra></extra>",
    ))
    for row, val, color in points:
        fig.add_trace(go.Scatter(
            x=[val], y=[_display_label(row)], mode="markers",
            marker=dict(size=15, color=color, line=dict(width=1.5, color="white")),
            name=_display_label(row),
            customdata=[[row["player_name"], row["season_club"], row["league_label"], row["primary_detailed_position"], val]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]}<br>"
                f"{metric_label} ({mode_label}): " + "%{customdata[4]:.1f}<extra></extra>"
            ),
        ))
    fig.update_layout(
        xaxis=dict(title=f"{metric_label} ({mode_label})", gridcolor="#E7EAE1"),
        yaxis=dict(title=None),
        height=max(220, 60 + 34 * len(names)), margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Plex Sans, sans-serif", size=12), showlegend=True,
    )
    return fig


def scatter_metric_figure(metric_x, metric_y, label_x, label_y, chart_rows, reference_df, mstats, filter_key, value_col, mode_label):
    """Chart type 2: two differentiating metrics plotted against each other, with the position
    average marked as dashed crosshair lines (not dots, since two dimensions can't share Chart 1's
    single-axis marker language)."""
    avg_x, _ = _reference_stats(mstats, reference_df, metric_x, filter_key, value_col)
    avg_y, _ = _reference_stats(mstats, reference_df, metric_y, filter_key, value_col)
    xs = _metric_lookup(mstats, pd.DataFrame([{k: r[k] for k in JOIN_KEY} for r in chart_rows]), metric_x, filter_key, value_col)
    ys = _metric_lookup(mstats, pd.DataFrame([{k: r[k] for k in JOIN_KEY} for r in chart_rows]), metric_y, filter_key, value_col)
    has_point = any(
        (k := tuple(row[c] for c in JOIN_KEY)) and pd.notna(xs.get(k)) and pd.notna(ys.get(k))
        for row in chart_rows
    )
    if not has_point:
        return None

    fig = go.Figure()
    if pd.notna(avg_x):
        fig.add_vline(x=avg_x, line=dict(color=REF_MARKER_COLOR, width=1.5, dash="dash"))
    if pd.notna(avg_y):
        fig.add_hline(y=avg_y, line=dict(color=REF_MARKER_COLOR, width=1.5, dash="dash"))

    for i, row in enumerate(chart_rows):
        key = tuple(row[k] for k in JOIN_KEY)
        x, y = xs.get(key), ys.get(key)
        if x is None or y is None or pd.isna(x) or pd.isna(y):
            continue
        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers", marker=dict(size=15, color=color, line=dict(width=1.5, color="white")),
            name=_display_label(row),
            customdata=[[row["player_name"], row["season_club"], row["league_label"], row["primary_detailed_position"], x, y]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]}<br>"
                f"{label_x}: " + "%{customdata[4]:.1f}<br>" + f"{label_y}: " + "%{customdata[5]:.1f}<extra></extra>"
            ),
        ))
    fig.update_layout(
        xaxis=dict(title=f"{label_x} ({mode_label})", gridcolor="#E7EAE1"),
        yaxis=dict(title=f"{label_y} ({mode_label})", gridcolor="#E7EAE1"),
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Plex Sans, sans-serif", size=12),
    )
    return fig


def bubble_metric_figure(metric_x, metric_y, metric_size, label_x, label_y, label_size,
                          chart_rows, reference_df, mstats, filter_key, value_col, mode_label):
    """Chart type 3: three differentiating metrics at once -- x, y, and bubble size."""
    avg_x, _ = _reference_stats(mstats, reference_df, metric_x, filter_key, value_col)
    avg_y, _ = _reference_stats(mstats, reference_df, metric_y, filter_key, value_col)
    keys_df = pd.DataFrame([{k: r[k] for k in JOIN_KEY} for r in chart_rows])
    xs = _metric_lookup(mstats, keys_df, metric_x, filter_key, value_col)
    ys = _metric_lookup(mstats, keys_df, metric_y, filter_key, value_col)
    zs = _metric_lookup(mstats, keys_df, metric_size, filter_key, value_col)
    has_point = any(
        (k := tuple(row[c] for c in JOIN_KEY)) and pd.notna(xs.get(k)) and pd.notna(ys.get(k)) and pd.notna(zs.get(k))
        for row in chart_rows
    )
    if not has_point:
        return None

    valid_sizes = [v for v in zs.values() if pd.notna(v) and v >= 0]
    zmax = max(valid_sizes) if valid_sizes else 1.0

    fig = go.Figure()
    if pd.notna(avg_x):
        fig.add_vline(x=avg_x, line=dict(color=REF_MARKER_COLOR, width=1.5, dash="dash"))
    if pd.notna(avg_y):
        fig.add_hline(y=avg_y, line=dict(color=REF_MARKER_COLOR, width=1.5, dash="dash"))

    for i, row in enumerate(chart_rows):
        key = tuple(row[k] for k in JOIN_KEY)
        x, y, z = xs.get(key), ys.get(key), zs.get(key)
        if x is None or y is None or z is None or pd.isna(x) or pd.isna(y) or pd.isna(z):
            continue
        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        size_px = 14 + 26 * (max(z, 0) / zmax if zmax else 0)
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers",
            marker=dict(size=size_px, color=color, line=dict(width=1.5, color="white"), opacity=0.85),
            name=_display_label(row),
            customdata=[[row["player_name"], row["season_club"], row["league_label"], row["primary_detailed_position"], x, y, z]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]}<br>"
                f"{label_x}: " + "%{customdata[4]:.1f}<br>" + f"{label_y}: " + "%{customdata[5]:.1f}<br>"
                f"{label_size} (bubble size): " + "%{customdata[6]:.1f}<extra></extra>"
            ),
        ))
    fig.update_layout(
        xaxis=dict(title=f"{label_x} ({mode_label})", gridcolor="#E7EAE1"),
        yaxis=dict(title=f"{label_y} ({mode_label})", gridcolor="#E7EAE1"),
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Plex Sans, sans-serif", size=12),
    )
    return fig
