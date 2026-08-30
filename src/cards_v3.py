"""
UI/UX Round 2 (2026-08-30) -- result row + detail panel.

Collapsed row: identity, club/league/minutes, selected-profile Final Score + Global Rank only --
"Other Profiles" moved into the expanded panel (see render_detail_panel) so the recommendation
list stays scannable.

Expanded panel hierarchy (per the round-2 brief): A. Selected Profile headline (unchanged) ->
B. Why he stands out (2-4 scouting insights, headline+evidence+badges from explanation_engine_v2)
-> C. Areas to Watch (1-3) -> D. Other Profiles (compact table, visually secondary, shown last).
"""
import html
from datetime import date

import pandas as pd

from src.nationality_flags import get_flag_html
from src.league_coverage import country_from_league_label

SCORE_COLOR = "var(--progression)"


def _current_age(dob):
    if pd.isna(dob):
        return None
    dob = pd.Timestamp(dob).date()
    today = date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def _identity_fields(row):
    name = html.escape(str(row["player_name"]))
    if pd.notna(row["nationality"]):
        nat_value = str(row["nationality"])
        nationality = f'{get_flag_html(nat_value)} {html.escape(nat_value)}'
    else:
        nationality = "nationality n/a"
    club = html.escape(str(row["season_club"])) if pd.notna(row["season_club"]) else "—"
    if pd.notna(row["league_label"]):
        league_value = str(row["league_label"])
        league_country = country_from_league_label(league_value)
        league_flag = get_flag_html(league_country) if league_country else ""
        league = f'{league_flag} {html.escape(league_value)}' if league_flag else html.escape(league_value)
    else:
        league = "—"
    age_years = _current_age(row["date_of_birth"])
    age = f"{age_years}y" if age_years is not None else "age n/a"
    minutes = f"{row['minutes_played']:,.0f} min" if pd.notna(row["minutes_played"]) else "min n/a"
    return name, nationality, club, league, age, minutes


def render_result_row(rank_in_list, row, score_row, combo_label, position_label):
    name, nationality, club, league, age, minutes = _identity_fields(row)
    final_score = score_row["final_score"]
    pctile = round((1 - (score_row["rank"] - 1) / score_row["population"]) * 100, 1)

    return f"""
    <div class="ntpr-drow">
      <div class="ntpr-idx">{rank_in_list:02d}</div>
      <div class="ntpr-who"><div class="nm">{name}</div><div class="sb">{nationality} · {age} · {html.escape(position_label)}</div></div>
      <div class="ntpr-meta"><div class="l1">{club} · {league}</div><div>{minutes}</div></div>
      <div class="ntpr-gauge"><div class="num" style="color:{SCORE_COLOR}">{final_score:.0f}</div><div class="lab">Final Score</div>
        <div class="track"><div class="fill" style="width:{final_score:.0f}%; background:{SCORE_COLOR}"></div></div></div>
      <div class="ntpr-gauge"><div class="num" style="color:var(--defensive)">#{int(score_row['rank'])}</div><div class="lab">{pctile:.0f}th pctile</div>
        <div class="track"><div class="fill" style="width:{pctile:.0f}%; background:var(--defensive)"></div></div></div>
    </div>
    """


def _render_insight(insight):
    badges_html = "".join(
        f'<span style="display:inline-block; font-family:var(--font-mono); font-size:10px; '
        f'color:var(--ink-faint); border:1px solid var(--rule); border-radius:3px; padding:1px 5px; '
        f'margin-right:4px;">{html.escape(b)}</span>'
        for b in insight["badges"]
    )
    return (
        f'<div style="margin-bottom:9px;">'
        f'<div style="font-weight:600; font-size:13px; color:var(--ink);">{html.escape(insight["headline"])}</div>'
        f'<div style="font-size:12.5px; color:var(--ink-muted); margin:2px 0 3px;">{html.escape(insight["body"])}</div>'
        f'{badges_html}'
        f'</div>'
    )


def render_other_profiles_compact(other_rows):
    """Compact Other Profiles table for INSIDE the expanded panel (moved out of the collapsed
    row per the round-2 brief). Style | Emphasis | Final Score | Global Rank, visually secondary."""
    if not other_rows:
        return ""
    header = (
        '<div style="display:grid; grid-template-columns: 1.2fr 1.6fr 0.7fr 1fr; gap:6px; '
        'font-size:10px; text-transform:uppercase; letter-spacing:0.04em; color:var(--ink-faint); '
        'padding-bottom:4px; border-bottom:1px solid var(--rule);">'
        '<span>Style</span><span>Emphasis</span><span>Score</span><span>Global Rank</span></div>'
    )
    rows = "".join(
        f'<div style="display:grid; grid-template-columns: 1.2fr 1.6fr 0.7fr 1fr; gap:6px; '
        f'font-size:12px; color:var(--ink-muted); padding:4px 0; border-bottom:1px solid var(--rule);">'
        f'<span>{html.escape(r["style"])}</span><span>{html.escape(r["emphasis"])}</span>'
        f'<span style="font-family:var(--font-mono);">{r["final_score"]:.1f}</span>'
        f'<span style="font-family:var(--font-mono);">#{int(r["rank"])} of {int(r["population"])}</span></div>'
        for r in other_rows
    )
    return f"""
    <div style="margin-top:14px;">
      <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.04em; color:var(--ink-faint); margin-bottom:6px;">Other Profiles</div>
      {header}{rows}
    </div>
    """


def render_detail_panel(row, score_row, combo_label, explanation, other_rows):
    pctile = round((1 - (score_row["rank"] - 1) / score_row["population"]) * 100, 1)

    strengths_html = "".join(_render_insight(s) for s in explanation["strengths"]) or \
        '<div style="font-size:12.5px; color:var(--ink-faint);">No standout strengths identified from the data.</div>'
    weaknesses_html = "".join(_render_insight(w) for w in explanation["weaknesses"]) or \
        '<div style="font-size:12.5px; color:var(--ink-faint);">No significant weaknesses identified from the data.</div>'

    return f"""
    <div class="ntpr-panel">
      <div class="ntpr-dan-scores">
        <div class="ntpr-dan-score" style="border-color:{SCORE_COLOR}; background:var(--progression-tint);">
          <div class="lab" style="color:{SCORE_COLOR}">Final Score — {html.escape(combo_label)}</div>
          <div class="num">{score_row['final_score']:.1f}</div></div>
        <div class="ntpr-dan-score fixed"><div class="lab">Global Rank</div>
          <div class="num">#{int(score_row['rank'])}</div>
          <div class="fixedtag">of {int(score_row['population'])} eligible players — {pctile:.0f}th percentile</div></div>
      </div>
      <div class="ntpr-dan-cols">
        <div class="ntpr-dan-block"><h4>Why he stands out</h4><div class="ntpr-dan-list">{strengths_html}</div></div>
        <div class="ntpr-dan-block"><h4>Areas to watch</h4><div class="ntpr-dan-list">{weaknesses_html}</div></div>
      </div>
      {render_other_profiles_compact(other_rows)}
      <div class="ntpr-dan-note" style="margin-top:12px;"><b>How this rating works:</b> The final rating evaluates how
      well this player performs in the selected football profile while accounting for the competitive environment
      those performances were produced in. Performances against stronger opposition carry greater weight, and the
      level of his current club provides additional context. There is no single "best player" score — the same
      player can rate very differently under a different Style or Role Emphasis, which is exactly the point: this
      tool matches players to the profile a team actually needs.</div>
    </div>
    """
