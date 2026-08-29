"""
UI/UX Round 1 (2026-08-30) -- profile-comparison visualization.

Shows, for a set of recommended players from the SAME locked V2 scoring group, how each one's
Final Score varies across the four Styles (using each player's own best-Emphasis combination per
Style -- a real, existing, locked combination, never an average or synthetic score). Answers
"where does each player perform best across profiles?" Suppressed entirely when the selected
players span more than one scoring group (see recommendations.py) -- comparing Final Scores across
different positions' populations that way would be misleading.
"""
import plotly.graph_objects as go

from src.charts import PLAYER_COLORS, _display_label

STYLE_ORDER = ["NoStyle", "Control", "Progression", "Direct"]
STYLE_LABEL = {"NoStyle": "Generic", "Control": "Control", "Progression": "Progression", "Direct": "Direct"}


def profile_comparison_figure(chart_rows, f50_scores, position, style_display):
    """chart_rows: list of player row Series (players.csv rows, must include player_id/season_id/
    team_id/player_name/season_club). f50_scores: the full f50_scores.csv DataFrame."""
    pos_scores = f50_scores[f50_scores.position == position]

    fig = go.Figure()
    for i, row in enumerate(chart_rows):
        color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        player_combos = pos_scores[(pos_scores.player_id == row["player_id"]) &
                                    (pos_scores.season_id == row["season_id"]) &
                                    (pos_scores.team_id == row["team_id"])]
        if player_combos.empty:
            continue
        xs, ys, texts = [], [], []
        for style in STYLE_ORDER:
            sub = player_combos[player_combos["style"] == style]
            if sub.empty:
                continue
            best = sub.loc[sub.final_score.idxmax()]
            xs.append(style_display(style))
            ys.append(best.final_score)
            texts.append(f"#{int(best['rank'])} of {int(best.population)}")
        fig.add_trace(go.Bar(
            x=xs, y=ys, name=_display_label(row), marker_color=color,
            text=texts, textposition="outside",
            hovertemplate="%{x}: %{y:.1f}<br>%{text}<extra>" + _display_label(row) + "</extra>",
        ))

    fig.update_layout(
        barmode="group", height=360, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(title="Final Score", range=[0, 105], gridcolor="#E7EAE1"),
        font=dict(family="IBM Plex Sans, sans-serif", size=12),
    )
    return fig
