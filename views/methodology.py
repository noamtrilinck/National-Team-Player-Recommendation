"""
Methodology page -- Sprint 5.

The 7-stage plain-language walkthrough from the approved design mockup (bearing.html), ported
here as a real routed page rather than a modal or expander. Stage 02's example Ability names were
updated from the mockup's placeholder examples to the real production taxonomy (Progressive
Passing, Chance Creation, Defensive Ball-Winning) -- everything else is unchanged from the
approved copy.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.nav import render_nav

render_nav("meth")

st.markdown("""
<span class="ntpr-kicker">For football professionals, not data scientists</span>
<div class="ntpr-h1" style="max-width:none;">From raw match data to a recommendation</div>
<p class="ntpr-sub">Seven steps, no step skipped. Nothing here changes when you apply a chart filter — filters only touch the
descriptive statistics on the Comparison Charts, never a score.</p>
""", unsafe_allow_html=True)

STAGES = [
    ("01", "Raw match data",
     "Every statistic starts from real match events across 32 European leagues outside the top five, at the "
     "individual-match level wherever the data supports it.",
     "Foundation"),
    ("02", "Football Abilities",
     "Individual statistics are grouped into 11 Football Abilities that represent real football qualities — "
     "Progressive Passing, Chance Creation, Defensive Ball-Winning, and others — each built from several related "
     "statistics rather than any single number.",
     "8 attacking, 3 defensive"),
    ("03", "Position-relative scoring",
     "Every Ability is scored relative to other players in the same specific position — a Centre Back's passing "
     "is judged against other Centre Backs, never against a Winger.",
     "Fair comparison"),
    ("04", "Context adjustment",
     "Scores receive a light adjustment for the competitiveness of the player's league and club, so a strong "
     "season in a weaker league is neither dismissed nor treated identically to the same season in a stronger one.",
     "Levels the playing field"),
    ("05", "Three Philosophy scores",
     "The 8 attacking Abilities are combined three separate ways — once per philosophy — because the qualities "
     "that matter for Control aren't the qualities that matter for Direct. No step here ever averages the three "
     "together.",
     "Control · Progression · Direct"),
    ("06", "Final Defensive Score",
     "The 3 defensive Abilities combine into one Defensive Score, independent of attacking philosophy — "
     "defensive value doesn't change with attacking style, so it's calculated once and shown alongside every "
     "recommendation.",
     "Fixed, always shown"),
    ("07", "Recommendation",
     "Players are ranked purely by the philosophy score you selected. Match filters (Home/Away, recent form, "
     "opponent strength) can change which descriptive statistics appear in the comparison charts — they never "
     "recompute a score or reorder a recommendation.",
     "What you see is what you get"),
]

st.markdown('<div style="margin-top:36px;">', unsafe_allow_html=True)
for num, title, body, tag in STAGES:
    st.markdown(f"""
    <div class="ntpr-stage">
      <div class="sn">{num}</div>
      <div><h3>{title}</h3><p>{body}</p><span class="tag">{tag}</span></div>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
