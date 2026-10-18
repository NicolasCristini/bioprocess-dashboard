"""Design tokens: the single source of truth for colours, type, radii and the chart palette.

DESIGN.md describes them for humans; this file is what the code reads. After changing a value, run
`python3 scripts/sync_theme.py` so the native config (.streamlit/config.toml) follows; the in-browser build
reads these tokens directly (scripts/build_site.py).
"""

# ---- neutrals (cool grey, light theme): mid-light grey canvas, light panels, white charts and inputs
CANVAS = "#D7DBE0"        # page background (mid-light grey)
SURFACE = "#EEF0F3"       # cards, KPI tiles
SIDEBAR = "#E4E7EB"       # left panel
SURFACE_2 = "#FFFFFF"     # inputs, tables, charts (white)
HAIRLINE = "#C3C8CF"      # borders
HAIRLINE_STRONG = "#A9AFB8"
GRID = "#E6E9ED"          # chart grid lines on white
TEXT = "#15181C"          # primary text (never pure black)
TEXT_MUTED = "#3F454E"    # secondary text, labels
TEXT_SUBTLE = "#545B65"   # captions, axis ticks

# ---- the one accent (deep teal): primary buttons, focus, active nav, key series
ACCENT = "#0F685A"
ACCENT_HOVER = "#0B544A"
ON_ACCENT = "#FFFFFF"
ACCENT_SOFT = "rgba(15, 104, 90, 0.13)"

# ---- data colours (meaning, not decoration), chosen to read on white
PHASE = {"Batch": "#8E96A0", "Fed-batch": "#E08A35", "Continuous": "#4C86DE"}
CHART = ["#0F685A", "#D9822B", "#2F6BC7", "#C8414B", "#A8892A", "#7D5BB8", "#6B7280"]

# ---- semantic
DANGER = "#B4323A"
WARNING = "#99600E"
INFO = "#2F6BC7"
SUCCESS = ACCENT
DANGER_SOFT = "rgba(180, 50, 58, 0.12)"
WARNING_SOFT = "rgba(153, 96, 14, 0.13)"

# ---- type
FONT = "Geist"
FONT_MONO = "Geist Mono"
FONT_FILES = {FONT: "app/static/fonts/Geist-Variable.woff2", FONT_MONO: "app/static/fonts/GeistMono-Variable.woff2"}

# ---- shape (one documented rule): pills for anything you click, 14px cards, 10px inputs
RADIUS_CARD = "14px"
RADIUS_INPUT = "10px"
RADIUS_PILL = "999px"


def streamlit_theme() -> dict:
    """Theme options in Streamlit's config naming (flat keys without the 'theme.' prefix)."""
    return {
        "base": "light",
        "primaryColor": ACCENT,
        "backgroundColor": CANVAS,
        "secondaryBackgroundColor": SURFACE_2,
        "textColor": TEXT,
        "borderColor": HAIRLINE,
        "dataframeBorderColor": HAIRLINE,
        "dataframeHeaderBackgroundColor": SURFACE_2,
        "showWidgetBorder": True,
        "linkColor": ACCENT,
        "redColor": DANGER,
        "orangeColor": WARNING,
        "yellowColor": WARNING,
        "blueColor": INFO,
        "greenColor": ACCENT,
        "font": FONT,
        "headingFont": FONT,
        "codeFont": FONT_MONO,
        "baseFontSize": 15,
        "headingFontWeights": [600, 600, 600, 600, 600, 600],
        "metricValueFontWeight": 500,
        "baseRadius": RADIUS_INPUT,
        "buttonRadius": "full",
        "showSidebarBorder": True,
        "chartCategoricalColors": CHART,
        "fontFaces": [{"family": FONT, "url": FONT_FILES[FONT], "weight": "100 900"},
                      {"family": FONT_MONO, "url": FONT_FILES[FONT_MONO], "weight": "100 900"}],
        "sidebar.backgroundColor": SIDEBAR,
        "sidebar.secondaryBackgroundColor": SURFACE_2,
        "sidebar.borderColor": HAIRLINE,
    }
