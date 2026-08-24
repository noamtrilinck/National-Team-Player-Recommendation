"""
League Coverage section -- ported from the "Agent's Player to Club Model" project (its
`dashboard/league_coverage.py`), which is the reference implementation. See that project's
`docs/stage7_sprint7_10_league_coverage_lock.md` for the full design rationale (why grouped by
country, why one line per country, why alphabetical-country/highest-first-division ordering, why
no internal methodology terms).

Architectural adaptation from the reference implementation (necessary, not cosmetic -- see the
audit that preceded this port): the reference project needed a separate build-time script joining
two warehouse tables (`club_level_tiers.csv` + the `leagues` table) because its country/league/
division facts lived in three separate columns across two files. This project's `league_label`
column (already present in `dashboard/data/players.csv`, e.g. "Belgium 1 - Pro League") already
encodes country + division level + league name in ONE string -- confirmed directly, format is
always `"{country} {division_level} - {league_name}"`. So no build-time script or database
connection is needed here at all: this module parses the already-loaded, already-cached
`players.csv` directly, which is simpler than the reference implementation, not a weaker port.

Verified directly (not assumed) before building this: this project's production population has
the exact same 33-league/29-country universe as the reference project's `club_level_tiers.csv`
(same countries, same division levels, same league names -- the one difference is this project's
data spells Turkey as "Turkey", matching `nationality_flags.py`'s primary key directly, so no join
alias is needed here at all, unlike the reference project).
"""
from __future__ import annotations

import html as _html
import re

import pandas as pd

from src.nationality_flags import get_flag_html

# Flags in this section are deliberately smaller than the per-player-row ones (compact/supporting
# information, not the main content -- same principle as the reference implementation).
LEAGUE_COVERAGE_FLAG_MAX_WIDTH_PX = 16
LEAGUE_COVERAGE_FLAG_MAX_HEIGHT_PX = 12

_LABEL_PATTERN = re.compile(r"^(?P<country>.+) (?P<division>\d+) - (?P<league>.+)$")

# production league_name -> client-facing override. Empty by deliberate decision, exactly like the
# reference implementation: every real league_label value here was inspected directly and none are
# provider-internal codes -- see the reference project's own league_coverage.py docstring for the
# full per-league reasoning (same league names, same conclusion). Kept as the one centralized place
# to add a rename later, rather than hand-editing call sites.
LEAGUE_DISPLAY_NAME_OVERRIDES: dict[str, str] = {}


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _division_label(levels: list[int]) -> str:
    ordinals = " + ".join(_ordinal(lv) for lv in sorted(levels))
    plural = "Divisions" if len(levels) > 1 else "Division"
    return f"{ordinals} {plural}"


def display_league_name(league_name: str) -> str:
    return LEAGUE_DISPLAY_NAME_OVERRIDES.get(league_name, league_name)


def parse_league_labels(league_labels: pd.Series) -> pd.DataFrame:
    """Parses the raw `league_label` column (e.g. "Belgium 1 - Pro League") into a
    country/league_name/division_level DataFrame -- one row per DISTINCT label, never per player
    (a league with 200 players must not appear 200 times). Raises loudly (never silently drops or
    guesses) if any non-null label doesn't match the expected format, since this project's whole
    premise is that the format is exactly `"{country} {division} - {league}"`."""
    unique_labels = sorted(league_labels.dropna().unique())
    rows = []
    for label in unique_labels:
        m = _LABEL_PATTERN.match(label)
        if not m:
            raise ValueError(f"league_label does not match the expected "
                              f"'{{country}} {{division}} - {{league}}' format: {label!r}")
        rows.append({"country": m.group("country"), "league_name": m.group("league"),
                     "division_level": int(m.group("division"))})
    return pd.DataFrame(rows, columns=["country", "league_name", "division_level"])


def prepare_league_coverage_display(coverage: pd.DataFrame) -> list[dict]:
    """Same shape/contract as the reference implementation: one dict per country, sorted
    alphabetically, divisions listed highest-to-lowest, no internal-methodology fields. Empty
    input -> empty output, never an error."""
    if coverage.empty:
        return []

    results = []
    for country, group in coverage.groupby("country", sort=True):
        group = group.sort_values("division_level")
        levels = group["division_level"].astype(int).tolist()
        league_names = [display_league_name(n) for n in group["league_name"].tolist()]
        results.append({
            "country": country,
            "division_label": _division_label(levels),
            "league_names": league_names,
            "flag_html": get_flag_html(country, max_width_px=LEAGUE_COVERAGE_FLAG_MAX_WIDTH_PX,
                                        max_height_px=LEAGUE_COVERAGE_FLAG_MAX_HEIGHT_PX),
        })
    return sorted(results, key=lambda r: r["country"])


def coverage_line_html(entry: dict) -> str:
    safe_country = _html.escape(entry["country"])
    safe_division = _html.escape(entry["division_label"])
    safe_leagues = _html.escape(", ".join(entry["league_names"]))
    return (f'{entry["flag_html"]} <b>{safe_country}</b> — {safe_division} '
            f'<span style="color:var(--ink-faint);">({safe_leagues})</span>')


# =================================================================================================
# Streamlit rendering (this function only -- everything above is framework-independent)
# =================================================================================================

COVERAGE_GRID_COLUMNS = 3  # compact desktop grid, same as the reference implementation


def render_league_coverage(entries: list[dict]) -> None:
    """Compact, informational-only section directly under the hero title/subtitle and above the
    Database Scope callout -- see recommendations.py. Renders nothing at all if `entries` is
    empty (never a broken/empty section header floating above the rest of the page)."""
    import streamlit as st

    if not entries:
        return

    st.markdown('<div class="ntpr-leaguecov-label">Leagues Covered</div>', unsafe_allow_html=True)
    st.markdown('<div class="ntpr-leaguecov">', unsafe_allow_html=True)

    for i in range(0, len(entries), COVERAGE_GRID_COLUMNS):
        row = entries[i:i + COVERAGE_GRID_COLUMNS]
        cols = st.columns(COVERAGE_GRID_COLUMNS)
        for col, entry in zip(cols, row):
            with col:
                st.markdown(f'<div class="ntpr-leaguecov-line">{coverage_line_html(entry)}</div>',
                            unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
