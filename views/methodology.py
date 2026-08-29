"""
Methodology page -- V2/F50 migration (2026-08-29).

Replaces the old 14-stage Ability/Philosophy/Context-Ability walkthrough with an accurate account
of the locked V2/F50 pipeline: Signals -> Domains -> Position Quality -> Style -> Emphasis ->
Professional Score -> Opponent Context (T2 / Average Opponent Level / F50) -> Own Club Level ->
Final Score. Every number on this page is measured live from the current data export, never
hand-typed. The old page is preserved at Archive/dashboard_v1/views/methodology.py.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.nav import render_nav
from src.data_loader_v2 import load_players, load_f50_registry, POSITION_LABELS

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
every valid Style and Emphasis combination for their position -- 192 in total -- and the strength of the
opposition they actually faced is built into the final number.</p>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="ntpr-scope">
  <div class="ic">🛈</div>
  <div>
    <b>Player pool, measured from the current data export</b>
    <p><b>{N_PLAYER_SEASONS:,}</b> player-seasons across <b>{N_LEAGUES}</b> European leagues, evaluated across
    <b>{N_COMBOS}</b> valid Position &times; Style &times; Emphasis combinations. Goalkeepers are out of scope
    entirely; every remaining outfield player needs at least 900 minutes played for that club in that season
    to be scored at all.</p>
  </div>
</div>
""", unsafe_allow_html=True)

STAGES = [
    ("01", "Population & eligibility",
     "Every statistic starts from real match events. A player-season needs at least 900 minutes for a given "
     "club in a given season to be scored -- below that, per-90 rates get too noisy to trust. Goalkeepers are "
     "excluded entirely. A player who plays for more than one club in a season has their appearances combined "
     "into a single season record, minutes-weighted across clubs.",
     "Foundation", None),

    ("02", "Position groups",
     "Every player is scored within one of 8 position groups: Centre Back, Full Back, Wide Midfielder, Winger, "
     "Defensive Midfielder, Central Midfielder, Attacking Midfielder, Centre Forward. A player is always compared "
     "only against other players in the same position group -- never pooled across positions, never compared to "
     "a different role.",
     "Foundation", None),

    ("03", "Signals",
     "54 individual match statistics (Signals) are computed per90 or as a rate/share, grouped into footballing "
     "concepts (passing, tackling, dribbling, aerial duels, shooting, crossing, and more). Each Signal is "
     "compared only against other players in the same position, so a Centre Back's tackle numbers are judged "
     "against other Centre Backs, not the whole player pool.",
     "Foundation",
     "Every Signal also carries a sample-size confidence weighting -- a player with fewer matches has their "
     "Signal scores pulled gently toward the position average, rather than an unreliable small sample swinging "
     "their rating."),

    ("04", "Position Quality",
     "The Signals that matter most for a given position are combined into a single Position Quality figure -- "
     "the foundation of that player's rating before any Style or Emphasis is applied.",
     "Quality", None),

    ("05", "Style",
     "Every player is additionally scored on how well their play matches one of three attacking Styles: "
     "Control (patient possession), Progression (purposeful advancement through the lines), or Direct "
     "(vertical, fast forward play). A player can be selected under 'Any Style' (no Style preference applied) "
     "or under a specific one.",
     "Profile", None),

    ("06", "Emphasis",
     "Within a position, one or more Emphases narrow the profile further -- e.g. a Centre Back's 'Ball-Playing' "
     "Emphasis rewards passing and build-up involvement specifically. Not every position has the same Emphasis "
     "options, and some combinations of Emphases can be selected together (up to 3 at once, where the position "
     "defines them). Only combinations the registry defines as valid are ever offered -- there is no free-text "
     "combination.",
     "Profile", None),

    ("07", "Professional Score",
     "Position Quality, Style fit, and Emphasis fit are combined into a single Professional Score (0-100) for "
     "the selected profile -- pure playing quality, before any adjustment for the strength of the opposition "
     "faced. This is deliberately kept separate from club/opponent context so the two can be reasoned about "
     "independently.",
     "Scoring", None),

    ("08", "Club Strength",
     "Every club a player has faced (and their own club) is rated on a single Club Strength scale, built "
     "primarily from squad market value. This produces the T2 Club Level Rating, a 0-1 scale where a club "
     "exactly at the population average sits at 0.50.",
     "Context", None),

    ("09", "Average Opponent Level",
     "For every player, the actual opponents they faced across the season are looked up match-by-match, and "
     "their T2 Club Level Ratings are averaged, weighted by how many minutes were played in each match. This is "
     "a real measure of how strong the competition actually was -- not an assumption based on league reputation.",
     "Context", None),

    ("10", "Opponent Multiplier & Contextual Score",
     "The Average Opponent Level is converted into an Opponent Multiplier between 0.50 (weakest opposition "
     "faced) and 1.00 (strongest). The Professional Score is multiplied by this factor: "
     "Opponent Multiplier = 0.50 + 0.50 &times; Average Opponent Level. "
     "Contextual Professional Score = Professional Score &times; Opponent Multiplier. A strong performance "
     "against weak opposition is discounted; the same performance against strong opposition is not.",
     "Context",
     "This is a deliberate design choice: a lower Professional Score earned against much stronger opposition "
     "can legitimately outrank a higher Professional Score earned against much weaker opposition. That is "
     "intended, not an error."),

    ("11", "Own Club Level",
     "A player's own club is rated on the same T2 scale (minutes-weighted across clubs for a player who "
     "changed clubs mid-season), and contributes a fixed addition to the final score: "
     "Own Club Level Contribution = 10 &times; Own Club Level.",
     "Context", None),

    ("12", "Final Score",
     "Combined Raw Score = Contextual Professional Score + Own Club Level Contribution. This is then passed "
     "through a final calibration step (fit separately for each position) that produces the 0-100 Final Score "
     "shown on the Recommendations page -- rank-preserving, with no artificial clipping at the extremes.",
     "Scoring", None),
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
