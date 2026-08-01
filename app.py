"""
National Team Player Recommendation -- entry point / router (Sprint 5).

Sets up the page config and design system once, then hands off to st.navigation, which routes
between the two real pages in dashboard/views/: Recommendations (Sprints 1-4) and Methodology
(Sprint 5). Navigation itself is custom-styled (position="hidden" suppresses Streamlit's default
sidebar nav) -- see src/nav.py for the masthead + nav links rendered at the top of every page.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.styles import build_css

st.set_page_config(page_title="National Team Player Recommendation", page_icon="🛡️", layout="wide")
st.markdown(build_css(), unsafe_allow_html=True)

pg = st.navigation([
    st.Page("views/recommendations.py", title="Recommendations", default=True),
    st.Page("views/methodology.py", title="Methodology"),
], position="hidden")
pg.run()
