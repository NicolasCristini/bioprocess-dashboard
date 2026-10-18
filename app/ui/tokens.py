"""Design tokens: the single source of truth for colours, type, radii and the chart palette.

DESIGN.md describes them for humans; this file is what the code reads. After changing a value, run
`python3 scripts/sync_theme.py` so the native config (.streamlit/config.toml) follows; the in-browser build
reads these tokens directly (scripts/build_site.py).
"""

# ---- neutrals (cool zinc, dark only)
CANVAS = "#0B0C0E"        # page background
SURFACE = "#131519"       # cards, sidebar, tiles
SURFACE_2 = "#1A1D22"     # inputs, table headers, hover
HAIRLINE = "#262A31"      # borders, grid lines
HAIRLINE_STRONG = "#363B45"
TEXT = "#E8EAED"          # primary text (off-white, never #fff)
TEXT_MUTED = "#A3A9B3"    # secondary text, labels
TEXT_SUBTLE = "#80868F"   # captions, axis ticks (4.9:1 on SURFACE)

# ---- the one accent (teal): primary buttons, focus, active nav, key series
ACCENT = "#3FB8A0"
ACCENT_HOVER = "#5ACAB3"
ON_ACCENT = "#06110E"     # text on accent fill (7.8:1)
ACCENT_SOFT = "rgba(63, 184, 160, 0.12)"

# ---- data colours (meaning, not decoration)
PHASE = {"Batch": "#7D8590", "Fed-batch": "#E39A4F", "Continuous": "#6C9BEA"}
CHART = ["#3FB8A0", "#E39A4F", "#6C9BEA", "#E46F7A", "#D2B555", "#A48BD6", "#7D8590"]

# ---- semantic
DANGER = "#E5585E"
WARNING = "#DDA449"
INFO = "#6C9BEA"
SUCCESS = ACCENT

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
        "base": "dark",
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
        "baseFontSize": 14,
        "headingFontWeights": [600, 600, 600, 600, 600, 600],
        "metricValueFontWeight": 500,
        "baseRadius": RADIUS_INPUT,
        "buttonRadius": "full",
        "showSidebarBorder": True,
        "chartCategoricalColors": CHART,
        "fontFaces": [{"family": FONT, "url": FONT_FILES[FONT], "weight": "100 900"},
                      {"family": FONT_MONO, "url": FONT_FILES[FONT_MONO], "weight": "100 900"}],
        "sidebar.backgroundColor": SURFACE,
        "sidebar.secondaryBackgroundColor": SURFACE_2,
        "sidebar.borderColor": HAIRLINE,
    }
