"""
UI/UX Round 2 (2026-08-30) -- Profile Comparison, redesigned as a heatmap.
UI/UX Round 4 (2026-08-30) -- BUGFIX: each cell must be the player's pure BASE STYLE score (the
Generic/no-Emphasis combo), never an Emphasis-specific Final Score. The round-2 version picked
`sub.final_score.idxmax()` across every combo for that Style -- i.e. the player's BEST EMPHASIS
score for that Style, not the Style score itself (confirmed root cause of the reported "Yair
Mordechai shows ~88 for Direct" issue: that 88 was actually his Direct + Goal Threat combo).
Fixed to filter to the single real, existing Generic (`emphasis == "(none)"`) combo per Style --
same grain the registry itself defines as "the Style with no Emphasis applied" -- never averaged,
never Emphasis-dependent, and provably invariant to whatever Emphasis is selected in the search
controls (see tests/test_round4_heatmap_and_comparison.py).

Replaces the round-1 grouped bar chart (too crowded with 5 players x multiple profiles, a large
player-name legend, rank labels above every bar, and a wasted 0-100 baseline when scores cluster
high). A heatmap answers the actual question -- "how does each player compare across profiles" --
more directly: rows are players (identity always visible, no legend needed), columns are the
Styles genuinely comparable within one scoring group, color intensity makes each player's
strongest/weakest profile jump out immediately, and Global Rank is a small in-cell annotation
rather than a separate label cluttering the chart.
"""
import plotly.graph_objects as go

from src.charts import _display_label

STYLE_ORDER = ["NoStyle", "Control", "Progression", "Direct"]
GENERIC_EMPHASIS = "(none)"  # same encoding as f50_scores.csv's emphasis column project-wide


def profile_comparison_figure(chart_rows, f50_scores, position, style_display):
    """chart_rows: list of player row Series (players.csv rows, must include player_id/season_id/
    team_id/player_name/season_club). f50_scores: the full f50_scores.csv DataFrame. Each cell is
    the player's real, existing BASE STYLE (Generic, no-Emphasis) combo for that Style -- never
    the currently-selected Emphasis, never the player's best-scoring Emphasis, never averaged."""
    pos_scores = f50_scores[(f50_scores.position == position) & (f50_scores.emphasis == GENERIC_EMPHASIS)]

    labels = [_display_label(row) for row in chart_rows]
    columns = [style_display(s) for s in STYLE_ORDER]

    z, text = [], []
    for row in chart_rows:
        player_combos = pos_scores[(pos_scores.player_id == row["player_id"]) &
                                    (pos_scores.season_id == row["season_id"]) &
                                    (pos_scores.team_id == row["team_id"])]
        z_row, text_row = [], []
        for style in STYLE_ORDER:
            sub = player_combos[player_combos["style"] == style]
            if sub.empty:
                z_row.append(None)
                text_row.append("")
                continue
            best = sub.iloc[0]  # exactly one Generic combo per (player, Style) by registry construction
            z_row.append(float(best.final_score))
            text_row.append(f"{best.final_score:.0f}  ·  #{int(best['rank'])}")
        z.append(z_row)
        text.append(text_row)

    flat_z = [v for row in z for v in row if v is not None]
    # Adaptive color range: scores among a compared set often cluster in a narrow high band (the
    # players shown are usually already strong candidates) -- a fixed 0-100 range would make every
    # cell look the same dark green. Scaling to the actual spread (with a little padding) restores
    # real visual contrast between a player's strongest and weakest profile.
    vmin = min(flat_z) - 3 if flat_z else 0
    vmax = max(flat_z) + 1 if flat_z else 100

    fig = go.Figure(data=go.Heatmap(
        z=z, x=columns, y=labels, text=text, texttemplate="%{text}",
        colorscale=[[0, "#F4E3E1"], [0.5, "#E1EFE6"], [1, "#1B7A50"]],
        zmin=vmin, zmax=vmax, showscale=True,
        colorbar=dict(title="Final<br>Score", thickness=12, len=0.6, tickfont=dict(size=10)),
        hovertemplate="%{y}<br>%{x}: %{z:.1f}<extra></extra>",
        xgap=3, ygap=3,
    ))
    fig.update_layout(
        height=max(160, 70 * len(chart_rows) + 60),
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", size=12),
        xaxis=dict(side="top", tickfont=dict(size=12)),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12)),
    )
    return fig
