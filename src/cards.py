"""Result row + detail panel rendering -- custom HTML so it matches the design spec exactly
(no Streamlit widget stands between the data and the pixels here)."""
import html

import pandas as pd

from src import analysis

PHIL_COLOR_VAR = {
    "Control": "var(--control)",
    "Progression": "var(--progression)",
    "Direct": "var(--direct)",
}
PHIL_SCORE_COL = {"Control": "phil_control", "Progression": "phil_progression", "Direct": "phil_direct"}


def render_result_row(rank, row, philosophy):
    phil_col = PHIL_SCORE_COL[philosophy]
    phil_score = row[phil_col]
    def_score = row["final_defensive_score"]
    color = PHIL_COLOR_VAR[philosophy]

    name = html.escape(str(row["player_name"]))
    nationality = html.escape(str(row["nationality"]))
    position = html.escape(str(row["primary_detailed_position"]))
    club = html.escape(str(row["season_club"])) if pd.notna(row["season_club"]) else "—"
    league = html.escape(str(row["league_label"]))
    age = f"{row['age']:.0f}y" if pd.notna(row["age"]) else "age n/a"
    minutes = f"{row['minutes_played']:,.0f} min" if pd.notna(row["minutes_played"]) else "min n/a"

    return f"""
    <div class="ntpr-drow">
      <div class="ntpr-idx">{rank:02d}</div>
      <div class="ntpr-who"><div class="nm">{name}</div><div class="sb">{nationality} · {age} · {position}</div></div>
      <div class="ntpr-meta"><div class="l1">{club} · {league}</div><div>{minutes}</div></div>
      <div class="ntpr-gauge"><div class="num" style="color:{color}">{phil_score:.0f}</div><div class="lab">{philosophy}</div>
        <div class="track"><div class="fill" style="width:{phil_score:.0f}%; background:{color}"></div></div></div>
      <div class="ntpr-gauge"><div class="num" style="color:var(--defensive)">{def_score:.0f}</div><div class="lab">Defence</div>
        <div class="track"><div class="fill" style="width:{def_score:.0f}%; background:var(--defensive)"></div></div></div>
    </div>
    """


def render_detail_panel(row, philosophy):
    name = html.escape(str(row["player_name"]))
    position = str(row["primary_detailed_position"])
    pid, sid, tid = int(row["player_id"]), int(row["season_id"]), int(row["team_id"])

    abilities = analysis.player_abilities(pid, sid, tid)
    top, bottom = analysis.top_bottom_abilities(abilities, n=3)

    def ability_rows(pairs):
        return "".join(
            f'<div class="li"><span>{html.escape(a)}</span><b>{s:.0f}</b></div>' for a, s in pairs
        ) or '<div class="li"><span style="color:var(--ink-faint);">Not enough matches to compute this yet.</span></div>'

    def desc_rows(pairs):
        return "".join(
            f'<div class="li"><span>{html.escape(analysis.ABILITY_DESCRIPTIONS.get(a, a))}</span></div>' for a, _ in pairs
        ) or '<div class="li"><span style="color:var(--ink-faint);">Not enough matches to compute this yet.</span></div>'

    score_tiles = ""
    for phil in ["Control", "Progression", "Direct"]:
        col = PHIL_SCORE_COL[phil]
        selected = phil == philosophy
        style = f'border-color:{PHIL_COLOR_VAR[phil]}; background:var(--{"control" if phil=="Control" else "progression" if phil=="Progression" else "direct"}-tint);' if selected else f'border-color:{PHIL_COLOR_VAR[phil]};'
        label = f"{phil} — selected" if selected else phil
        score_tiles += (f'<div class="ntpr-dan-score" style="{style}">'
                         f'<div class="lab" style="color:{PHIL_COLOR_VAR[phil]}">{label}</div>'
                         f'<div class="num">{row[col]:.0f}</div></div>')
    score_tiles += (f'<div class="ntpr-dan-score fixed"><div class="lab">Final Defensive Score</div>'
                     f'<div class="num">{row["final_defensive_score"]:.0f}</div>'
                     f'<div class="fixedtag">Fixed — independent of philosophy selection</div></div>')

    why_phil = analysis.why_philosophy_text(name, position, philosophy, abilities)
    why_def = analysis.defensive_explanation_text(name, position, abilities)

    return f"""
    <div class="ntpr-panel">
      <div class="ntpr-dan-scores">{score_tiles}</div>
      <div class="ntpr-dan-cols">
        <div class="ntpr-dan-block"><h4>Strengths</h4><div class="ntpr-dan-list">{desc_rows(top)}</div></div>
        <div class="ntpr-dan-block"><h4>Weaknesses</h4><div class="ntpr-dan-list">{desc_rows(bottom)}</div></div>
        <div class="ntpr-dan-block"><h4>Strongest Abilities</h4><div class="ntpr-dan-list">{ability_rows(top)}</div></div>
        <div class="ntpr-dan-block"><h4>Weakest Abilities</h4><div class="ntpr-dan-list">{ability_rows(bottom)}</div></div>
      </div>
      <div class="ntpr-dan-note"><b>Why this {philosophy} score:</b> {why_phil}</div>
      <div class="ntpr-dan-note"><b>About the Defensive Score:</b> {why_def}</div>
    </div>
    """
