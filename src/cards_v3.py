"""
UI/UX Round 1 (2026-08-30) -- result row + detail panel, redesigned per the round-1 brief:
headline is the selected profile's Final Score + Global Rank only; Professional Score, Opponent
Multiplier, Own Club Level contribution and other internal components are NOT shown prominently
(methodology internals -- see docs/v2_ui_redesign_round1.md). Other valid profiles for the same
player are shown as a secondary, visually subordinate list. The detail panel adds a football
scouting explanation (strengths/weaknesses from real Signal data, explanation_engine_v2) instead
of a mathematical breakdown.
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


def render_other_profiles(other_rows):
    """other_rows: list of dicts {label, final_score, rank}. Visually subordinate to the headline
    result row -- small text, muted color, no gauges."""
    if not other_rows:
        return ""
    items = "".join(
        f'<div style="display:flex; justify-content:space-between; padding:3px 0; '
        f'font-size:12px; color:var(--ink-muted);">'
        f'<span>{html.escape(r["label"])}</span>'
        f'<span style="font-family:var(--font-mono);">{r["final_score"]:.1f} &nbsp; #{int(r["rank"])} globally</span>'
        f'</div>'
        for r in other_rows
    )
    return f"""
    <div style="margin: 4px 0 10px 46px; padding: 8px 12px; border-left: 2px solid var(--rule); background: var(--surface-2, transparent);">
      <div style="font-size:10.5px; text-transform:uppercase; letter-spacing:0.04em; color:var(--ink-faint); margin-bottom:3px;">Other Profiles</div>
      {items}
    </div>
    """


def render_detail_panel(row, score_row, combo_label, explanation):
    name = html.escape(str(row["player_name"]))
    pctile = round((1 - (score_row["rank"] - 1) / score_row["population"]) * 100, 1)

    def _bullets(items, empty_msg):
        if not items:
            return f'<div class="li"><span style="color:var(--ink-faint);">{empty_msg}</span></div>'
        return "".join(f'<div class="li"><span>{html.escape(s)}</span></div>' for s in items)

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
        <div class="ntpr-dan-block"><h4>Strengths</h4><div class="ntpr-dan-list">{_bullets(explanation['strengths'], "No standout strengths identified from the data.")}</div></div>
        <div class="ntpr-dan-block"><h4>Areas to watch</h4><div class="ntpr-dan-list">{_bullets(explanation['weaknesses'], "No significant weaknesses identified from the data.")}</div></div>
      </div>
      <div class="ntpr-dan-note"><b>How this rating works:</b> The final rating evaluates how well {name}
      performs in the selected football profile while accounting for the competitive environment those
      performances were produced in. Performances against stronger opposition carry greater weight, and
      the level of his current club provides additional context. There is no single "best player" score —
      the same player can rate very differently under a different Style or Role Emphasis, which is exactly
      the point: this tool matches players to the profile a team actually needs.</div>
    </div>
    """
