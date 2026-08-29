"""
Result row + detail panel rendering for the V2/F50 Recommendations page (migration, 2026-08-29).

Replaces cards.py's Philosophy/Defensive rendering. Reuses the EXISTING CSS classes/markup shape
from styles.py (.ntpr-drow / .ntpr-idx / .ntpr-who / .ntpr-meta / .ntpr-gauge / .ntpr-panel /
.ntpr-dan-*) so no new stylesheet work is needed and the visual language stays consistent -- only
the score content changes: one Final Score gauge (for the selected Position x Style x Emphasis
combination) instead of a fixed Philosophy + Defence pair, and a detail panel that explains the
F50 Professional / Context / Own-Level breakdown instead of the old Ability strengths/weaknesses.
"""
import html
from datetime import date

import pandas as pd

from src.nationality_flags import get_flag_html
from src.league_coverage import country_from_league_label

SCORE_COLOR = "var(--progression)"  # a single, position/style-agnostic accent for the Final Score gauge


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


def render_result_row(rank_in_list, row, score_row, combo_label):
    """row: a players.csv row. score_row: the matching f50_scores.csv row for the currently
    selected Position x Style x Emphasis combo. combo_label: short display string, e.g.
    "Progression / Ball-Playing"."""
    name, nationality, club, league, age, minutes = _identity_fields(row)
    position = html.escape(str(row["primary_detailed_position"]))
    final_score = score_row["final_score"]
    pctile = round((1 - (score_row["rank"] - 1) / score_row["population"]) * 100, 1)

    return f"""
    <div class="ntpr-drow">
      <div class="ntpr-idx">{rank_in_list:02d}</div>
      <div class="ntpr-who"><div class="nm">{name}</div><div class="sb">{nationality} · {age} · {position}</div></div>
      <div class="ntpr-meta"><div class="l1">{club} · {league}</div><div>{minutes}</div></div>
      <div class="ntpr-gauge"><div class="num" style="color:{SCORE_COLOR}">{final_score:.0f}</div><div class="lab">Final Score</div>
        <div class="track"><div class="fill" style="width:{final_score:.0f}%; background:{SCORE_COLOR}"></div></div></div>
      <div class="ntpr-gauge"><div class="num" style="color:var(--defensive)">#{int(score_row['rank'])}</div><div class="lab">Rank</div>
        <div class="track"><div class="fill" style="width:{pctile:.0f}%; background:var(--defensive)"></div></div></div>
    </div>
    """


def render_detail_panel(row, score_row, combo_label):
    name = html.escape(str(row["player_name"]))
    pctile = round((1 - (score_row["rank"] - 1) / score_row["population"]) * 100, 1)

    score_tiles = "".join([
        f'<div class="ntpr-dan-score" style="border-color:{SCORE_COLOR}; background:var(--progression-tint);">'
        f'<div class="lab" style="color:{SCORE_COLOR}">Final Score — selected</div>'
        f'<div class="num">{score_row["final_score"]:.1f}</div></div>',
        f'<div class="ntpr-dan-score fixed"><div class="lab">Professional Score</div>'
        f'<div class="num">{score_row["professional_score"]:.1f}</div>'
        f'<div class="fixedtag">Playing quality before opponent context</div></div>',
        f'<div class="ntpr-dan-score fixed"><div class="lab">Opponent Multiplier</div>'
        f'<div class="num">{score_row["opponent_multiplier"]:.3f}</div>'
        f'<div class="fixedtag">0.50 (weakest faced) to 1.00 (strongest faced)</div></div>',
        f'<div class="ntpr-dan-score fixed"><div class="lab">Rank</div>'
        f'<div class="num">{int(score_row["rank"])}/{int(score_row["population"])}</div>'
        f'<div class="fixedtag">{pctile:.0f}th percentile for this exact profile</div></div>',
    ])

    return f"""
    <div class="ntpr-panel">
      <div class="ntpr-dan-scores">{score_tiles}</div>
      <div class="ntpr-dan-note"><b>Profile evaluated:</b> {html.escape(combo_label)}. This score answers
      "how good is {name} <i>at this specific football profile</i>" — not a universal rating. The same player
      can rank very differently under a different Style or Emphasis; that is intentional.</div>
      <div class="ntpr-dan-note"><b>How the Final Score is built:</b> Professional Score (pure playing quality
      for this profile) is multiplied by the Opponent Multiplier (0.50 + 0.50 &times; the average strength of
      the opposition actually faced this season), then a fixed Own Club Level contribution is added, then the
      locked tail-safe calibration is applied. A lower Professional Score earned against much stronger
      opposition can legitimately outrank a higher Professional Score earned against much weaker opposition —
      this is a deliberate design choice, not an error.</div>
    </div>
    """
