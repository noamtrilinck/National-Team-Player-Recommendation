"""
UI/UX Round 2 (2026-08-30) -- result row + detail panel.

Collapsed row: identity, club/league/minutes, selected-profile Final Score + Profile Rank only --
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


def _ordinal(n: int) -> str:
    """1st/2nd/3rd/4th... -- found during the 2026-09 owner-review sanity check always rendering
    a hardcoded "th" (e.g. "91th pctile", "1th percentile"); cosmetic UI text only, no data or
    score involved."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


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
    # Multi-club lineage (2026-09-09): season_club_display/league_label_display show EVERY club
    # that actually contributed evidence to this player-season (e.g. "Derby County -> Rapid
    # Vienna"), never just the single primary club -- see data_loader_v2.load_players() and
    # production/match_level/build_multi_club_lineage.py. Falls back to the plain season_club/
    # league_label for the ~87% of player-seasons that are single-club (columns absent entirely
    # when this row came from a caller that didn't go through load_players(), e.g. a raw CSV read).
    club_field = row["season_club_display"] if "season_club_display" in row.index and pd.notna(row.get("season_club_display")) else row["season_club"]
    league_field = row["league_label_display"] if "league_label_display" in row.index and pd.notna(row.get("league_label_display")) else row["league_label"]
    club = html.escape(str(club_field)) if pd.notna(club_field) else "—"
    if pd.notna(league_field):
        league_value = str(league_field)
        # Cross-league lineage: country flag isn't well-defined for a combined multi-league label,
        # so it's shown without a single flag rather than a misleading one from only the first leg.
        league_country = country_from_league_label(league_value) if " → " not in league_value else None
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
      <div class="ntpr-gauge" title="Profile Rank/Percentile: compares this player with every eligible player rated for this exact position + Style + Role Emphasis profile."><div class="num" style="color:var(--defensive)">#{int(score_row['rank'])}</div><div class="lab">{_ordinal(int(round(pctile)))} pctile</div>
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
    row per the round-2 brief). Style | Emphasis | Final Score | Profile Rank, visually secondary."""
    if not other_rows:
        return ""
    header = (
        '<div style="display:grid; grid-template-columns: 1.2fr 1.6fr 0.7fr 1fr; gap:6px; '
        'font-size:10px; text-transform:uppercase; letter-spacing:0.04em; color:var(--ink-faint); '
        'padding-bottom:4px; border-bottom:1px solid var(--rule);">'
        '<span>Style</span><span>Emphasis</span><span>Score</span><span>Profile Rank</span></div>'
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


def _render_why_fits(why_fits):
    """UI/UX Round 3 -- 'Why He Fits [Emphasis]', shown only when build_why_fits() found genuine
    Emphasis-specific (Tier 1/2) evidence; omitted entirely otherwise (never forced)."""
    if not why_fits:
        return ""
    intro_html = f'<div style="font-size:12.5px; color:var(--ink-muted); margin-bottom:8px;">{html.escape(why_fits["intro"])}</div>' \
        if why_fits.get("intro") else ""
    bullets_html = "".join(
        f'<div style="margin-bottom:9px;">'
        f'<div style="font-weight:600; font-size:13px; color:var(--ink);">{html.escape(b["label"])}</div>'
        f'<div style="font-size:12.5px; color:var(--ink-muted); margin:2px 0;">{html.escape(b["body"])}</div>'
        f'</div>'
        for b in why_fits["bullets"]
    )
    return f"""
    <div style="margin-top:16px; padding:12px 14px; border:1px solid var(--rule); border-radius:6px; background:var(--progression-tint);">
      <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.04em; color:{SCORE_COLOR}; margin-bottom:6px; font-weight:600;">{html.escape(why_fits["title"])}</div>
      {intro_html}{bullets_html}
    </div>
    """


def render_detail_panel(row, score_row, combo_label, explanation, other_rows, why_fits=None):
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
        <div class="ntpr-dan-score fixed" title="Profile Rank compares the player with every eligible player rated for this exact profile — the same position, Style, and Role Emphasis combination — not the whole database or just this position.">
          <div class="lab">Profile Rank</div>
          <div class="num">#{int(score_row['rank'])}</div>
          <div class="fixedtag">of {int(score_row['population'])} eligible players rated for this exact profile ({html.escape(combo_label)}) — {_ordinal(int(round(pctile)))} percentile</div></div>
      </div>
      {_render_why_fits(why_fits)}
      <div class="ntpr-dan-cols">
        <div class="ntpr-dan-block"><h4>Why he stands out</h4><div class="ntpr-dan-list">{strengths_html}</div></div>
        <div class="ntpr-dan-block"><h4>Areas to watch</h4><div class="ntpr-dan-list">{weaknesses_html}</div></div>
      </div>
      {render_other_profiles_compact(other_rows)}
      <div class="ntpr-dan-note" style="margin-top:12px;"><b>How this rating works:</b> The final rating combines
      how well this player performs in the selected football profile, the strength of the opposition and of his
      own club across the season, and how much of the season's available playing time he actually delivered —
      full detail on the exact weighting is on the Methodology page. There is no single "best player" score — the
      same player can rate very differently under a different Style or Role Emphasis, which is exactly the
      point: this tool matches players to the profile a team actually needs.</div>
    </div>
    """
