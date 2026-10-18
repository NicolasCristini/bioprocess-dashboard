# DESIGN.md: Bioprocess Phase Planner visual system

The visual spec for the app. Edit it to restyle the app later:
1. change the values in `app/ui/tokens.py` (the code reads only that file);
2. run `python3 scripts/sync_theme.py` (native config);
3. reload. The in-browser build picks up the tokens automatically.

**Design read:** a dense scientific planning tool for bioprocess engineers. Dark, technical and calm: the data is the
colour, the chrome stays quiet.
- **References:** Linear (near-black canvas, hairline borders, one accent), the Cell Culture Analyzer (header + card
  panels, inputs left and results right), MediaTrack (dark by default, ink/graphite neutrals, editable spec).
- **Dials:** variance 4, motion 3, density 7.

## Colour

One theme (dark) for the whole app. One accent. Data colours carry meaning only.

| Token | Value | Use |
|---|---|---|
| `CANVAS` | `#0B0C0E` | page background |
| `SURFACE` | `#131519` | cards, sidebar, KPI tiles |
| `SURFACE_2` | `#1A1D22` | inputs, table headers, selected tab |
| `HAIRLINE` / `HAIRLINE_STRONG` | `#262A31` / `#363B45` | borders, chart grid |
| `TEXT` | `#E8EAED` | primary text (16.2:1 on canvas) |
| `TEXT_MUTED` | `#A3A9B3` | labels, secondary text (7.7:1 on surface) |
| `TEXT_SUBTLE` | `#80868F` | captions, axis ticks (5.0:1 on surface) |
| `ACCENT` | `#3FB8A0` (teal) | primary buttons, active nav, focus, key series, "OK" |
| `ON_ACCENT` | `#06110E` | text on accent fill (7.8:1) |

| Data colour | Value | Meaning |
|---|---|---|
| Batch | `#7D8590` | phase type |
| Fed-batch | `#E39A4F` | phase type, fed-batch feed |
| Continuous | `#6C9BEA` | phase type |
| Chart series | teal, amber, blue, rose, ochre, lavender, grey | in that order (`CHART`) |
| Danger / warning / info | `#E5585E` / `#DDA449` / `#6C9BEA` | blocking, check, note |

Rules:
- Never pure black or pure white.
- The accent never decorates; it marks the primary action or the current state.
- The phase colours are the same everywhere: timeline, phase badges, chart bands.

## Type

- **Geist** for UI and headings, **Geist Mono** for every number (KPI values, chips, inputs, axis ticks, hover labels).
  Both are self-hosted in `app/static/fonts/` (SIL Open Font License). No external font requests.
- Base 14 px. Headings weight 600 with negative tracking (-0.02em). The page title is 1.6 rem; there is no oversized hero type.

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

- Transparent background, hairline grid, Geist Mono ticks, legend top-left, hover in a dark surface label.
- Phase bands at 10 % opacity in the phase colours. The inspect-hour marker is a 1 px dotted muted line.
- Limits are dashed lines in the series colour; the volume window is red dashed with an accent wash.

## Motion

Minimal and motivated only:
- 150 ms colour transitions on buttons;
- 0.98 scale on press;
- the boot progress bar.

`prefers-reduced-motion` disables transitions.

## Copy

- Plain functional labels: "Results", "Checks: 0 blocking, 3 to review".
- No em-dashes, no emoji, no decorative dots or numbering.
