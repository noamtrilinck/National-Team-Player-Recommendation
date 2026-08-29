"""
UI/UX Round 1 (2026-08-30) -- Position search resolution logic.

Deliberately separate from data_loader_v2.py: this module encodes the RULES for turning a
user's side-specific, possibly-multi-position search into one or more real, existing, locked V2
combinations -- never a new score. See docs/v2_ui_redesign_round1.md for the full design record
and the registry audit that established these rules are always resolvable (every position has a
Generic/None-Emphasis combo for every Style -- confirmed for all 192 rows of registry_192.csv).

Search-side taxonomy is the 11-way source taxonomy (side-specific); scoring-side taxonomy is the
locked 8-group V2 architecture. This module is the ONLY place that bridges the two -- everything
downstream (data_loader_v2, recommendations.py) works in whichever taxonomy is appropriate for
that layer and never re-derives this mapping.
"""
from dataclasses import dataclass

import pandas as pd

# UI-facing side-specific position -> (locked V2 scoring group, raw primary_detailed_position
# value(s) as they appear in players.csv). Order is the display order in the position dropdown.
SIDE_POSITIONS = {
    "Centre Back": ("CB", ["Centre Back"]),
    "Right Back": ("FB", ["Right Back"]),
    "Left Back": ("FB", ["Left Back"]),
    "Defensive Midfielder": ("DM", ["Defensive Midfield"]),
    "Central Midfielder": ("CM", ["Central Midfield"]),
    "Right Midfielder": ("WM", ["Right Midfield"]),
    "Left Midfielder": ("WM", ["Left Midfield"]),
    "Attacking Midfielder": ("AM", ["Attacking Midfield"]),
    "Right Winger": ("Winger", ["Right Wing"]),
    "Left Winger": ("Winger", ["Left Wing"]),
    "Centre Forward": ("CF", ["Centre Forward", "Secondary Striker"]),
}
SIDE_POSITION_ORDER = list(SIDE_POSITIONS.keys())
ALL_GROUP8 = ["CB", "FB", "WM", "Winger", "DM", "CM", "AM", "CF"]


@dataclass
class SearchPlan:
    mode: str  # "single_full" | "multi_style_only" | "all_positions"
    group8s: list  # locked V2 scoring groups involved
    side_filter: dict  # group8 -> list of raw primary_detailed_position values to keep (None = no filter, keep whole group)
    label: str  # human-readable description of what was searched


def plan_search(selected_ui_positions, all_positions_mode):
    """Turns the user's raw selection into a SearchPlan. Pure logic, no data access."""
    if all_positions_mode or not selected_ui_positions:
        return SearchPlan(mode="all_positions", group8s=list(ALL_GROUP8),
                           side_filter={g: None for g in ALL_GROUP8}, label="All Positions")

    group8s_selected = {}
    for ui_pos in selected_ui_positions:
        g8, raw_vals = SIDE_POSITIONS[ui_pos]
        group8s_selected.setdefault(g8, []).extend(raw_vals)

    if len(group8s_selected) == 1:
        g8 = next(iter(group8s_selected))
        raw_vals = group8s_selected[g8]
        # if every side of this group was selected, it's equivalent to "no side filter" (the
        # whole group) -- e.g. Right Back + Left Back together = the whole FB group.
        all_raw_for_group = [v for ui_pos, (g, vals) in SIDE_POSITIONS.items() if g == g8 for v in vals]
        side_filter_vals = None if set(raw_vals) == set(all_raw_for_group) else raw_vals
        return SearchPlan(mode="single_full", group8s=[g8], side_filter={g8: side_filter_vals},
                           label=" + ".join(selected_ui_positions))

    side_filter = {g8: vals for g8, vals in group8s_selected.items()}
    return SearchPlan(mode="multi_style_only", group8s=list(group8s_selected.keys()),
                       side_filter=side_filter, label=" + ".join(selected_ui_positions))


def resolve_combo_ids(plan, style, registry):
    """Returns {group8: combo_id} for this plan under the given Style. In single_full mode,
    `style` may be None/"NoStyle" with an explicit emphasis handled by the caller instead (this
    function only resolves the Style-only / no-emphasis case used by multi-position and
    All Positions modes -- single_full mode's combo is resolved directly by the caller via
    data_loader_v2.combo_id_for, which supports the full Emphasis selection)."""
    out = {}
    for g8 in plan.group8s:
        sub = registry[(registry["position"] == g8) & (registry["style"] == style)]
        generic = sub[sub["emphasis_list"].apply(lambda x: len(x) == 0)]
        if generic.empty:
            # Should never happen -- confirmed by registry audit that every position x style has
            # a Generic combo. If this ever fires, it's a genuine registry gap, not something to
            # paper over with a synthetic combination.
            raise ValueError(f"No Generic (no-Emphasis) combo found for position={g8} style={style} "
                              f"-- registry conflict, cannot resolve without inventing a score.")
        out[g8] = generic.iloc[0]["combo_id"]
    return out


STYLE_ORDER = ["NoStyle", "Control", "Progression", "Direct"]


def style_options_for_plan(plan, registry):
    """Style options valid across every group8 in the plan (intersection) -- in practice always
    all 4, since every position offers all 4 Styles (confirmed by the registry audit), but computed
    generically rather than assumed."""
    sets = []
    for g8 in plan.group8s:
        sets.append(set(registry[registry["position"] == g8]["style"].unique()))
    common = set.intersection(*sets) if sets else set()
    return [s for s in STYLE_ORDER if s in common]


def emphasis_options_for_plan(plan, registry):
    """Only meaningful in single_full mode (exactly one scoring group involved)."""
    g8 = plan.group8s[0]
    sub = registry[registry["position"] == g8]
    opts = sorted(sub["emphasis_list"].unique().tolist(), key=lambda lst: (len(lst), lst))
    return opts


def resolve_search(plan, style, emphasis, registry):
    """Returns {group8: combo_id} for the given plan+style(+emphasis, single_full mode only)."""
    if plan.mode == "single_full":
        g8 = plan.group8s[0]
        sub = registry[(registry["position"] == g8) & (registry["style"] == style)]
        match = sub[sub["emphasis_list"].apply(lambda x: tuple(x) == tuple(emphasis or ()))]
        if match.empty:
            raise ValueError(f"No combo found for position={g8} style={style} emphasis={emphasis} "
                              f"-- registry conflict, cannot resolve without inventing a score.")
        return {g8: match.iloc[0]["combo_id"]}
    return resolve_combo_ids(plan, style, registry)


def other_profiles(f50_scores, player_row, current_style, registry, exclude_combo, max_items=3):
    """For a player already shown under `current_style` (and whichever combo produced their
    headline result), returns up to `max_items` OTHER real, existing combos for their own scoring
    group -- one per other Style, each at that player's own single best Emphasis for that Style
    (never averaged, never synthetic). Used for the visually-secondary 'Other Profiles' list."""
    g8 = player_row["position_v2"]
    mine = f50_scores[(f50_scores.player_id == player_row["player_id"]) &
                       (f50_scores.season_id == player_row["season_id"]) &
                       (f50_scores.team_id == player_row["team_id"]) &
                       (f50_scores.position == g8) & (f50_scores.combo_id != exclude_combo)]
    out = []
    for style in STYLE_ORDER:
        sub = mine[mine["style"] == style]
        if sub.empty:
            continue
        best = sub.loc[sub.final_score.idxmax()]
        emph_label = "Generic" if best.emphasis == "(none)" else best.emphasis
        style_label = "Generic" if style == "NoStyle" else style
        out.append(dict(label=f"{style_label} · {emph_label}", final_score=best.final_score, rank=best["rank"]))
        if len(out) >= max_items:
            break
    return out


def apply_side_filter(df, plan):
    """df: a DataFrame with columns player_id/position_v2/primary_detailed_position already
    merged in. Filters to exactly the players the plan's side selection implies, per group8."""
    frames = []
    for g8 in plan.group8s:
        sub = df[df["position_v2"] == g8]
        raw_vals = plan.side_filter.get(g8)
        if raw_vals is not None:
            sub = sub[sub["primary_detailed_position"].isin(raw_vals)]
        frames.append(sub)
    return pd.concat(frames, ignore_index=True) if frames else df.iloc[0:0]
