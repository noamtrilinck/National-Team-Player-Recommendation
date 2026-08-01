"""
Visual system for the National Team Player Recommendation dashboard.

Ports the palette, typography, and component language from the approved Phase 9 design
specification into Streamlit. Streamlit's native widgets (selectbox, radio, button) can't be
restyled with the same freedom as the standalone HTML mockup -- this module gets them as close
as Streamlit's DOM allows via `data-testid` selectors, documented inline where a compromise was
made. Anything rendered as custom HTML (the hero, philosophy explainer, result rows) matches the
mockup exactly, since there's no Streamlit widget in the way.
"""
import base64
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# ---- Design tokens: identical values to bearing.html (the approved design spec) ----
LIGHT = {
    "bg": "#F1F4EE", "surface": "#FFFFFF", "surface_2": "#E7EAE1", "surface_3": "#DCE1D6",
    "ink": "#171F1A", "ink_muted": "#57614F", "ink_faint": "#838C7C", "border": "#D5DBCC", "rule": "#C6CDBC",
    "accent": "#7A2A36", "accent_strong": "#5C1F28", "accent_tint": "#F4E3E1", "on_accent": "#FBF3EF",
    "control": "#33587F", "control_tint": "#E4EBF2",
    "progression": "#1B7A50", "progression_tint": "#E1EFE6",
    "direct": "#A8650E", "direct_tint": "#F3E7D3",
    "defensive": "#57626C", "defensive_tint": "#E7EAEC", "context": "#7C8272",
}


def _font_b64(name):
    return base64.b64encode((ASSETS / name).read_bytes()).decode("ascii")


def build_css():
    fraunces = _font_b64("fraunces.woff2")
    plexsans = _font_b64("plexsans.woff2")
    plexmono400 = _font_b64("plexmono400.woff2")
    plexmono500 = _font_b64("plexmono500.woff2")
    t = LIGHT

    return f"""
<style>
  @font-face {{ font-family: 'Fraunces'; font-weight: 400 900; font-style: normal;
    src: url(data:font/woff2;base64,{fraunces}) format('woff2'); }}
  @font-face {{ font-family: 'Plex Sans'; font-weight: 100 900; font-style: normal;
    src: url(data:font/woff2;base64,{plexsans}) format('woff2'); }}
  @font-face {{ font-family: 'Plex Mono'; font-weight: 400; font-style: normal;
    src: url(data:font/woff2;base64,{plexmono400}) format('woff2'); }}
  @font-face {{ font-family: 'Plex Mono'; font-weight: 500; font-style: normal;
    src: url(data:font/woff2;base64,{plexmono500}) format('woff2'); }}

  :root {{
    --bg: {t['bg']}; --surface: {t['surface']}; --surface-2: {t['surface_2']}; --surface-3: {t['surface_3']};
    --ink: {t['ink']}; --ink-muted: {t['ink_muted']}; --ink-faint: {t['ink_faint']};
    --border: {t['border']}; --rule: {t['rule']};
    --accent: {t['accent']}; --accent-strong: {t['accent_strong']}; --accent-tint: {t['accent_tint']}; --on-accent: {t['on_accent']};
    --control: {t['control']}; --control-tint: {t['control_tint']};
    --progression: {t['progression']}; --progression-tint: {t['progression_tint']};
    --direct: {t['direct']}; --direct-tint: {t['direct_tint']};
    --defensive: {t['defensive']}; --defensive-tint: {t['defensive_tint']}; --context: {t['context']};
    --font-display: 'Fraunces', Georgia, serif;
    --font-body: 'Plex Sans', -apple-system, "Segoe UI", sans-serif;
    --font-mono: 'Plex Mono', ui-monospace, "SF Mono", Consolas, monospace;
  }}

  /* ---- Streamlit chrome: hide default menu/footer, adopt the ground colour + body font ---- */
  #MainMenu, footer, header {{ visibility: hidden; }}
  .stApp {{ background: var(--bg); font-family: var(--font-body); color: var(--ink); }}
  .block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1080px; }}
  h1, h2, h3, h4 {{ font-family: var(--font-display) !important; color: var(--ink); }}
  p, span, div, label {{ font-family: var(--font-body); }}

  /* ---- Masthead ---- */
  .ntpr-masthead {{ display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:14px;
    padding-bottom:14px; border-bottom:1px solid var(--border); margin-bottom:28px; }}
  .wordmark-lockup {{ display:flex; align-items:baseline; gap:10px; }}
  .ntpr-mark {{ font-family: var(--font-mono); font-size:11px; letter-spacing:.1em; border:1px solid var(--ink); padding:3px 6px; border-radius:3px; }}
  .ntpr-name {{ font-size:15px; font-weight:700; }}

  /* ---- Top nav (Sprint 5): two st.button-based links, state carried by container `key`,
     not by guessing Streamlit's internal button "kind" attribute. ---- */
  div[class*="st-key-ntpr_nav_active"] .stButton > button,
  div[class*="st-key-ntpr_nav_inactive"] .stButton > button {{
    background:transparent !important; border:none !important; box-shadow:none !important;
    padding:6px 2px !important; font-family: var(--font-body); font-size:13.5px !important;
    border-radius:0 !important; border-bottom:2px solid transparent !important; width:auto !important;
  }}
  div[class*="st-key-ntpr_nav_inactive"] .stButton > button {{ color: var(--ink-muted) !important; font-weight:500 !important; }}
  div[class*="st-key-ntpr_nav_inactive"] .stButton > button:hover {{ color: var(--ink) !important; }}
  div[class*="st-key-ntpr_nav_active"] .stButton > button {{
    color: var(--ink) !important; font-weight:600 !important; border-bottom-color: var(--accent) !important;
  }}

  /* ---- Hero ---- */
  .ntpr-kicker {{ font-family: var(--font-mono); font-size:11.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--ink-faint); }}
  .ntpr-h1 {{ font-family: var(--font-display); font-weight:700; font-size:clamp(28px,4vw,42px); margin-top:12px; max-width:18ch; line-height:1.05; }}
  .ntpr-h1 em {{ font-style:normal; box-shadow: inset 0 -0.3em 0 var(--progression-tint); }}
  .ntpr-sub {{ margin-top:14px; max-width:64ch; color:var(--ink-muted); font-size:15.5px; }}
  .ntpr-notthis {{ margin-top:18px; display:flex; gap:26px; flex-wrap:wrap; font-size:13px; }}
  .ntpr-notthis .lbl {{ font-family: var(--font-mono); font-size:10.5px; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-faint); }}
  .ntpr-notthis .no {{ color:var(--ink-faint); text-decoration:line-through; font-weight:500; }}
  .ntpr-notthis .yes {{ color:var(--accent); font-weight:600; }}

  /* ---- Database scope panel ---- */
  .ntpr-scope {{ display:flex; gap:12px; padding:14px 16px; border:1px solid var(--border); background:var(--surface); margin:22px 0; }}
  .ntpr-scope .ic {{ flex:none; font-size:17px; line-height:1.3; color:var(--ink-faint); }}
  .ntpr-scope b {{ display:block; font-size:12.5px; font-family: var(--font-mono); text-transform:uppercase; letter-spacing:.06em; color:var(--ink-faint); margin-bottom:4px; }}
  .ntpr-scope p {{ font-size:13px; color:var(--ink-muted); margin:0; max-width:78ch; }}

  /* ---- Philosophy explainer ---- */
  .ntpr-explain {{ display:grid; grid-template-columns:repeat(3,1fr); gap:1px; background:var(--border); border:1px solid var(--border); margin:26px 0; }}
  .ntpr-explain-cell {{ background:var(--surface); padding:18px; }}
  .ntpr-explain-cell h4 {{ font-size:15.5px; margin:8px 0 4px; }}
  .ntpr-explain-cell p {{ font-size:12.5px; color:var(--ink-muted); margin:0; }}

  /* ---- Control bar (Streamlit widgets live inside this visually) ---- */
  .ntpr-controlbar-label {{ font-family: var(--font-mono); font-size:10px; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-faint); margin-bottom:2px; }}
  div[data-testid="stVerticalBlockBorderWrapper"] {{ background: var(--surface-2); border: 1px solid var(--border) !important; border-radius: 0 !important; }}

  /* Selectbox / multiselect / radio restyle */
  div[data-baseweb="select"] > div {{ border-radius: 2px !important; border-color: var(--border) !important; font-family: var(--font-body); }}
  .stRadio > div {{ gap: 6px; }}
  .stRadio label {{ background: var(--surface); border: 1px solid var(--border); padding: 6px 12px; border-radius: 2px; font-size: 13px !important; }}

  /* Primary button = the accent claret, matching "Generate Recommendations" in the spec */
  .stButton > button {{ background: var(--ink); color: var(--surface); border: none; border-radius: 2px;
    font-weight: 700; padding: 10px 20px; font-family: var(--font-body); }}
  .stButton > button:hover {{ background: var(--accent); color: var(--on-accent); }}

  /* ---- Result dossier list (custom HTML, matches the design spec exactly) ---- */
  .ntpr-dossier {{ border-top: 1px solid var(--rule); margin-top: 10px; }}
  .ntpr-drow {{ display:grid; grid-template-columns: 32px 1.6fr 1.4fr 92px 92px; gap:14px; align-items:center; padding:15px 4px; border-bottom:1px solid var(--rule); }}
  .ntpr-drow:hover {{ background: var(--surface-2); }}
  .ntpr-idx {{ font-family: var(--font-mono); font-size:12px; color:var(--ink-faint); }}
  .ntpr-who .nm {{ font-weight:700; font-size:15px; }}
  .ntpr-who .sb {{ font-size:12px; color:var(--ink-muted); margin-top:1px; }}
  .ntpr-meta {{ font-size:12px; color:var(--ink-muted); font-family: var(--font-mono); }}
  .ntpr-meta .l1 {{ color:var(--ink); }}
  .ntpr-gauge {{ text-align:right; }}
  .ntpr-gauge .num {{ font-family: var(--font-display); font-weight:700; font-size:23px; line-height:1; }}
  .ntpr-gauge .lab {{ font-size:9.5px; text-transform:uppercase; letter-spacing:.07em; color:var(--ink-faint); margin-top:2px; }}
  .ntpr-gauge .track {{ height:3px; background:var(--surface-3); margin-top:6px; position:relative; }}
  .ntpr-gauge .fill {{ position:absolute; left:0; top:0; bottom:0; }}

  /* ---- Player detail panel (Sprint 2) ---- */
  .ntpr-toggle > button {{ background: var(--surface) !important; color: var(--ink-muted) !important;
    border: 1px solid var(--border) !important; font-weight: 600 !important; padding: 6px 10px !important;
    width: 100%; }}
  .ntpr-toggle > button:hover {{ border-color: var(--accent) !important; color: var(--accent) !important; }}
  .ntpr-panel {{ padding: 22px 18px 26px; background: var(--surface-2); border: 1px solid var(--border);
    border-top: none; margin-top: -1px; margin-bottom: 14px; }}
  .ntpr-dan-scores {{ display:flex; gap:10px; flex-wrap:wrap; }}
  .ntpr-dan-score {{ flex:1; min-width:130px; border:1px solid var(--border); background:var(--surface); padding:10px 12px; }}
  .ntpr-dan-score .lab {{ font-family: var(--font-mono); font-size:10px; text-transform:uppercase; letter-spacing:.06em; color:var(--ink-faint); }}
  .ntpr-dan-score .num {{ font-family: var(--font-display); font-size:22px; font-weight:700; margin-top:2px; }}
  .ntpr-dan-score.fixed {{ background: var(--defensive-tint); }}
  .ntpr-dan-score.fixed .fixedtag {{ font-size:10px; color:var(--ink-faint); margin-top:3px; }}
  .ntpr-dan-cols {{ display:grid; grid-template-columns:1fr 1fr; gap:22px; margin-top:20px; }}
  .ntpr-dan-block h4 {{ font-family: var(--font-mono) !important; font-size:10.5px; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-faint); font-weight:600; margin-bottom:8px; }}
  .ntpr-dan-list {{ display:flex; flex-direction:column; gap:6px; }}
  .ntpr-dan-list .li {{ display:flex; justify-content:space-between; gap:10px; font-size:13px; border-bottom:1px dotted var(--border); padding-bottom:5px; }}
  .ntpr-dan-list .li b {{ font-family: var(--font-mono); font-weight:600; flex:none; }}
  .ntpr-dan-note {{ margin-top:16px; padding:12px 14px; border-left:3px solid var(--accent); background:var(--surface); font-size:13px; color:var(--ink-muted); }}
  .ntpr-dan-note + .ntpr-dan-note {{ margin-top:10px; border-left-color:var(--defensive); }}

  .ntpr-empty {{ padding: 40px 20px; text-align:center; color:var(--ink-faint); border:1px dashed var(--border); font-size:13.5px; margin-top:10px; }}
  .ntpr-contextbar {{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding:10px 14px;
    background:var(--surface); border:1px solid var(--border); font-size:13px; flex-wrap:wrap; margin-top:22px; }}
  .ntpr-contextbar b {{ font-weight:600; }}

  /* ---- Methodology page (Sprint 5) ---- */
  .ntpr-stage {{ display:grid; grid-template-columns:64px 1fr; gap:20px; padding:26px 0; border-bottom:1px solid var(--rule); }}
  .ntpr-stage:last-child {{ border-bottom:none; }}
  .ntpr-stage .sn {{ font-family: var(--font-display); font-size:30px; font-weight:700; color:var(--ink-faint); }}
  .ntpr-stage h3 {{ font-size:17px; margin:0; }}
  .ntpr-stage p {{ font-size:14px; color:var(--ink-muted); margin-top:8px; max-width:66ch; }}
  .ntpr-stage .tag {{ font-family: var(--font-mono); font-size:10.5px; text-transform:uppercase; letter-spacing:.07em; color:var(--ink-faint); display:block; margin-top:8px; }}

  /* ---- Responsiveness (Sprint 6) ----
     Streamlit's own st.columns/st.container(horizontal=True) already stack vertically below its
     internal ~640px breakpoint, so the control bar, per-chart filter rows, and nav don't need
     help here. What DOES need help is the custom HTML built with fixed-column CSS grid, which
     doesn't reflow on its own: the result-row dossier, the philosophy explainer, and the detail
     panel's two-column layout. Not verified in an actual browser this session (no browser tool
     available) -- reviewed against real breakpoints and Streamlit's documented column behavior,
     worth a visual check when convenient. */
  @media (max-width: 700px) {{
    .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
    .ntpr-explain {{ grid-template-columns: 1fr; }}
    .ntpr-dan-cols {{ grid-template-columns: 1fr; }}
    .ntpr-stage {{ grid-template-columns: 40px 1fr; gap: 12px; }}
    .ntpr-stage .sn {{ font-size: 22px; }}
    /* The dossier row's 5-slot grid (idx/who/meta/2 gauges) is fixed-width and overflows a phone
       viewport -- switch to a wrapping flex layout instead, with meta (club/league/minutes)
       always forced onto its own full-width line below the name and scores. */
    .ntpr-drow {{ display: flex; flex-wrap: wrap; gap: 6px 14px; }}
    .ntpr-idx {{ order: 1; }}
    .ntpr-who {{ order: 2; flex: 1 1 55%; min-width: 150px; }}
    .ntpr-gauge {{ order: 3; flex: 0 0 auto; }}
    .ntpr-meta {{ order: 4; flex: 1 1 100%; }}
  }}
</style>
"""
