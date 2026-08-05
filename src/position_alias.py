"""
Single source of truth for the position-spelling mismatch between master_player_dataset.csv's
primary_detailed_position and the weighting tables (ability_weighting_v1.csv /
position_defensive_weights.csv). Previously duplicated verbatim in src/analysis.py and
data/build_dashboard_data.py -- kept here, with zero dependencies, so both the runtime app and
the offline export script can import it without the export script picking up a Streamlit
dependency it otherwise doesn't need.
"""

# Real, confirmed mismatch: master uses "Left Wing"/"Right Wing"/"Left Midfield"/"Right
# Midfield"/"Secondary Striker"; the weighting tables use "Left Winger"/"Right Winger"/"Left
# Midfielder"/"Right Midfielder", and have no "Secondary Striker" row at all (Centre Forward
# covers it).
POSITION_ALIAS_FOR_WEIGHTS = {
    "Left Wing": "Left Winger", "Right Wing": "Right Winger",
    "Left Midfield": "Left Midfielder", "Right Midfield": "Right Midfielder",
    "Secondary Striker": "Centre Forward",
}
