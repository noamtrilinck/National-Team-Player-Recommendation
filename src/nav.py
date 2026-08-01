"""Shared masthead + top navigation, rendered identically at the top of every page (Sprint 5).

Uses st.navigation's file-based routing (st.Page pointing at real .py files in dashboard/views/)
rather than passing callables, specifically so AppTest.switch_page -- which is path-based -- can
exercise both pages the same way every other Sprint in this project has been tested.
"""
import streamlit as st

PAGES = {
    "rec": ("Recommendations", "views/recommendations.py"),
    "meth": ("Methodology", "views/methodology.py"),
}


def render_nav(active):
    st.markdown(
        '<div class="ntpr-masthead"><div class="wordmark-lockup">'
        '<span class="ntpr-mark">NTPR</span><span class="ntpr-name">National Team Player Recommendation</span>'
        '</div>', unsafe_allow_html=True,
    )
    with st.container(key="ntpr_nav_row", horizontal=True, gap="medium"):
        for key, (label, path) in PAGES.items():
            is_active = key == active
            # The active/inactive state is encoded in the container's own `key` (Streamlit exposes
            # it as a `st-key-<key>` class on the wrapping div) rather than guessed from the
            # button's internal "kind" attribute, so the CSS selector below doesn't depend on
            # Streamlit's undocumented DOM internals.
            state = "active" if is_active else "inactive"
            with st.container(key=f"ntpr_nav_{state}_{key}"):
                if st.button(label, key=f"navbtn_{key}") and not is_active:
                    st.switch_page(path)
    st.markdown('</div>', unsafe_allow_html=True)
