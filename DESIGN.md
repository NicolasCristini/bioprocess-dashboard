# DESIGN.md: Bioprocess Phase Planner visual system

The visual spec for the app. Edit it to restyle the app later:
1. change the values in `app/ui/tokens.py` (the code reads only that file);
2. run `python3 scripts/sync_theme.py` (native config);
3. reload. The in-browser build picks up the tokens automatically.

**Design read:** a dense scientific planning tool for bioprocess engineers. Calm and technical: a mid-light grey
canvas, light panels, and every chart on white so it can go straight into a report.
- **References:** Linear (hairline borders, one accent), the Cell Culture Analyzer (header + card panels, inputs left
  and results right), MediaTrack (editable spec).
- **Dials:** variance 4, motion 3, density 7.
- **Revision 2 (Nicolas, 2026-10-18):**
  - light grey instead of black;
  - charts on white;
  - bigger text, especially in the left panel;
  - download buttons per chart, plus a legend-only download.

## Colour

One theme (light grey) for the whole app. One accent. Data colours carry meaning only.

| Token | Value | Use |
|---|---|---|
| `CANVAS` | `#D7DBE0` | page background (mid-light grey) |
| `SIDEBAR` | `#E4E7EB` | left panel |
| `SURFACE` | `#EEF0F3` | cards, KPI tiles |
| `SURFACE_2` | `#FFFFFF` | inputs, tables, **charts** |
| `HAIRLINE` / `HAIRLINE_STRONG` | `#C3C8CF` / `#A9AFB8` | borders |
| `GRID` | `#E6E9ED` | chart grid lines on white |
| `TEXT` | `#15181C` | primary text (12.8:1 on canvas) |
| `TEXT_MUTED` | `#3F454E` | labels, secondary text (7.0:1 on canvas) |
| `TEXT_SUBTLE` | `#545B65` | captions, axis ticks (4.9:1 on canvas) |
| `ACCENT` | `#0F685A` (deep teal) | primary buttons, active nav, focus, key series, "OK" (4.8:1 on canvas) |
| `ON_ACCENT` | `#FFFFFF` | text on accent fill (6.7:1) |

| Data colour | Value | Meaning |
|---|---|---|
| Batch | `#8E96A0` | phase type |
| Fed-batch | `#E08A35` | phase type, fed-batch feed |
| Continuous | `#4C86DE` | phase type |
| Chart series | teal, amber, blue, rose, ochre, violet, grey | in that order (`CHART`), chosen to read on white |
| Danger / warning / info | `#B4323A` / `#99600E` / `#2F6BC7` | blocking, check, note |

Rules:
- Never pure black.
- The accent never decorates; it marks the primary action or the current state.
- Status chips are white with coloured text and border. A tinted fill on the grey canvas fails contrast.
- The phase colours are the same everywhere: timeline, phase badges, chart bands.

## Type

- **Geist** for UI and headings, **Geist Mono** for every number (KPI values, chips, inputs, axis ticks, hover labels).
  Both are self-hosted in `app/static/fonts/` (SIL Open Font License). No external font requests.
- Base 15 px. The left panel is larger: navigation 16.5 px, status rows 15.5 px, section labels 13 px.
- Headings weight 600 with negative tracking (-0.02em). The page title is 1.6 rem; there is no oversized hero type.

## Shape (one rule, everywhere)

| Element | Radius |
|---|---|
| Anything you click (buttons, chips, tabs, nav items, timeline) | full pill |
| Cards, KPI tiles, expanders, step tiles | 14 px |
| Inputs, tables, alerts, issue rows | 10 px |

## Components (`app/ui/theme.py`)

- `top(title, subtitle, chips)`: page header with a status-chip row on the right and a hairline below.
- `kpis([...])`: tile grid. One `lead` tile per page (accent-tinted) for the headline number.
- `chips([...])`: inline value chips (label + mono value). Tones: neutral, accent, warning, danger.
- `issues([...])`: compact rows. A level label (Blocking / Check / Note) is followed by the phase and the message.
- `panel_title(title, sub)`: card heading.
- Bordered `st.container` = card (surface + hairline + 14 px).
- Tabs render as a segmented pill control.
- Icons: Material Symbols through Streamlit's `:material/...:` (no emoji in the UI).

## Charts (Plotly template `bioprocess`)

- **White background** inside a white card with a hairline border, light grid, Geist Mono ticks, legend top-left.
- Each figure sets `paper_bgcolor` explicitly (`theme.white`) and is drawn with `theme=None`. Otherwise Streamlit
  repaints it in the page colour.
- Phase bands at 12 % opacity in the phase colours. The inspect-hour marker is a 1 px dotted muted line.
- Limits are dashed lines in the series colour; the volume window is red dashed with an accent wash.

## Chart downloads (`charts.show`)

Under every chart:
- **Plot SVG:** a vector image on white (`app/ui/svg_export.py`, written in Python because image engines do not run in
  the browser);
- **Legend:** the colour key only, as SVG (series, phase bands, limits);
- **Data CSV:** the plotted values.

The camera icon on the chart saves a 3x PNG on white, in the browser. Downloads do not rerun the app
(`on_click="ignore"`).

## Motion

Minimal and motivated only:
- 150 ms colour transitions on buttons;
- 0.98 scale on press;
- the boot progress bar.

`prefers-reduced-motion` disables transitions.

## Copy

- Plain functional labels: "Results", "Checks: 0 blocking, 3 to review".
- No em-dashes, no emoji, no decorative dots or numbering.
