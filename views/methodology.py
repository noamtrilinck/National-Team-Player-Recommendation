"""
Methodology page -- UI/UX Round 1 rewrite (2026-08-30).

Public-facing account of the locked methodology in football-readable language. Internal
implementation names (T2, F50, calibD, sprint/stage numbers, owner-lock terminology) are
deliberately not used here -- they remain in the internal technical documentation
(../../docs/v2_methodology_CANONICAL.md). This page translates the same real architecture into
concepts a football professional recognizes: Player Profile, Style, Role Emphasis, Professional
Performance, Opposition Strength, Club Level, Final Rating. Every number on this page is measured
live from the current data export, never hand-typed. The pre-redesign version is preserved at
Archive/dashboard_v1/views/methodology.py.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.nav import render_nav
from src.data_loader_v2 import load_players, load_f50_registry

render_nav("meth")

players = load_players()
registry = load_f50_registry()
N_PLAYER_SEASONS = len(players)
N_LEAGUES = players["league_label"].nunique()
N_COMBOS = len(registry)

st.markdown("""
<span class="ntpr-kicker">For football professionals, not data scientists</span>
<div class="ntpr-h1" style="max-width:none;">How a player is rated</div>
<p class="ntpr-sub">A player is never given one universal score. Instead, every eligible player is rated against
every valid Player Profile for their position -- a Style and Role Emphasis combination -- and the strength of
the opposition they actually faced is built into the final rating.</p>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="ntpr-scope">
  <div class="ic">🛈</div>
  <div>
    <b>Player pool, measured from the current data export</b>
    <p><b>{N_PLAYER_SEASONS:,}</b> player-seasons across <b>{N_LEAGUES}</b> European leagues, evaluated across
    <b>{N_COMBOS}</b> valid Player Profiles. Goalkeepers are out of scope entirely; every remaining outfield
    player needs at least 900 minutes played for that club in that season to be included.</p>
  </div>
</div>
""", unsafe_allow_html=True)

STAGES = [
    ("01", "Population & eligibility",
     "Every statistic starts from real match events. A player-season needs at least 900 minutes for a given "
     "club in a given season to be included -- below that, per-90 rates get too noisy to trust. Goalkeepers are "
     "excluded entirely. A player who plays for more than one club in a season has their appearances combined "
     "into a single season record, weighted by minutes played at each club.",
     "Foundation", None),

    ("02", "Position groups",
     "Every player is rated within one of 8 position groups: Centre Back, Full Back, Wide Midfielder, Winger, "
     "Defensive Midfielder, Central Midfielder, Attacking Midfielder, Centre Forward. A player is always compared "
     "only against other players in the same position group -- never pooled across positions, never compared to "
     "a different role.",
     "Foundation", None),

    ("03", "Match statistics",
     "54 individual match statistics are measured per 90 minutes or as a rate/share, grouped into footballing "
     "concepts (passing, tackling, dribbling, aerial duels, shooting, crossing, and more). Each statistic is "
     "compared only against other players in the same position, so a Centre Back's tackle numbers are judged "
     "against other Centre Backs, not the whole player pool.",
     "Foundation",
     "Every statistic also carries a sample-reliability weighting -- a player with fewer matches has his numbers "
     "pulled gently toward the position average, rather than an unreliable small sample swinging his rating."),

    ("04", "Position Quality",
     "The statistics that matter most for a given position are combined into a single Position Quality figure -- "
     "the foundation of that player's rating before any Style or Role Emphasis is applied.",
     "Quality", None),

    ("05", "Style",
     "Every player is additionally rated on how well his play matches one of three attacking Styles: "
     "Control (patient possession), Progression (purposeful advancement through the lines), or Direct "
     "(vertical, fast forward play). A player can be viewed under 'Any Style' (no Style preference applied) "
     "or under a specific one.",
     "Profile", None),

    ("06", "Role Emphasis",
     "Within a position, one or more Role Emphases narrow the profile further -- e.g. a Centre Back's "
     "'Ball-Playing' Emphasis rewards passing and build-up involvement specifically. Not every position has the "
     "same Role Emphasis options, and some combinations can be selected together. Only combinations that "
     "genuinely exist in the underlying model are ever offered -- there is no free-text combination.",
     "Profile", None),

    ("07", "Professional Performance",
     "Position Quality, Style fit, and Role Emphasis fit are combined into a single Professional Performance "
     "rating for the selected profile -- pure playing quality, before any adjustment for the strength of the "
     "opposition faced. This is deliberately kept separate from the competitive-environment adjustment below, so "
     "the two can be reasoned about independently.",
     "Rating", None),

    ("08", "Club Level",
     "Every club a player has played for or faced is rated on a single Club Level scale, built primarily from "
     "squad market value -- a real, transparent measure of a club's overall resources and standing.",
     "Context", None),

    ("09", "Opposition Strength",
     "For every player, the actual opponents faced across the season are looked up match by match, and their "
     "Club Level ratings are averaged, weighted by minutes played in each match. This is a real, measured "
     "reflection of how strong the competition actually was -- not an assumption based on league reputation.",
     "Context", None),

    ("10", "Accounting for opposition",
     "A strong performance against significantly stronger opposition counts for more than the identical "
     "performance against weaker opposition. The reverse also holds. This adjustment is applied on top of "
     "Professional Performance, and is scaled so it can meaningfully shift a rating without ever being able to "
     "manufacture a top rating out of a weak underlying performance.",
     "Context",
     "This is a deliberate design choice: a lower Professional Performance rating earned against much stronger "
     "opposition can legitimately outrate a higher Professional Performance rating earned against much weaker "
     "opposition. That is intended, not an error — the tool is measuring performance in context, not raw output."),

    ("11", "Own club's level",
     "A player's own club is rated on the same Club Level scale (weighted across clubs for a player who changed "
     "clubs mid-season), and contributes additional context to the level at which he is currently competing.",
     "Context", None),

    ("12", "Final Rating",
     "Professional Performance, the opposition-strength adjustment, and the player's own Club Level are combined "
     "and rescaled onto a consistent 0-100 Final Rating for each position -- rank-preserving, with no artificial "
     "clipping at the extremes. This is the number shown on the Recommendations page.",
     "Rating", None),
]

for num, title, summary, tag, detail in STAGES:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display:flex; gap:14px; align-items:flex-start;">
          <div style="font-family:var(--font-mono); font-size:12px; color:var(--ink-faint); padding-top:3px;">{num}</div>
          <div style="flex:1;">
            <div style="display:flex; align-items:center; gap:10px;">
              <h3 style="font-family:var(--font-display); font-size:17px; margin:0;">{title}</h3>
              <span style="font-family:var(--font-mono); font-size:10px; text-transform:uppercase; letter-spacing:0.04em;
                color:var(--ink-faint); border:1px solid var(--rule); border-radius:4px; padding:1px 6px;">{tag}</span>
            </div>
            <p style="font-size:13.5px; color:var(--ink-muted); margin:6px 0 0;">{summary}</p>
          </div>
        </div>
        """, unsafe_allow_html=True)
        if detail:
            with st.expander("Show the detail"):
                st.markdown(f'<p style="font-size:13px; color:var(--ink-muted);">{detail}</p>', unsafe_allow_html=True)

st.markdown("""
<div class="ntpr-scope" style="margin-top:24px;">
  <div class="ic">🛈</div>
  <div>
    <b>Why there's no single "best player" score</b>
    <p>A player who excels at patient possession play (Control) may not be the right recommendation for a team
    that wants fast, vertical football (Direct) -- and vice versa. Collapsing every profile into one number would
    hide exactly the information a recruiter needs. The Recommendations page always asks "best for this specific
    profile," never "best overall."</p>
  </div>
</div>
""", unsafe_allow_html=True)
