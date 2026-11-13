# Workshop Planner

A browser-based 2D floor planner for a shop or shed. It's a single `index.html` with no build step, so it runs straight from GitHub Pages or from a local copy.

## Features

- **Layout:** drag, rotate (0/90/180/270), resize, lock, and duplicate items. The snap grid is anchored to the inside wall faces.
- **Selection:** shift-click or box-select several items, then move them together or nudge them with the arrow keys.
- **Conflict checks:**
  - Overlapping equipment is outlined, and the overlapping area is hatched.
  - Per-item clearance zones (front/back/left/right) turn red when blocked.
  - Items inside a door's swing are flagged.
- **Heights:** ceiling height for the shed. Each item can also have a height and a mounting height. Leave height blank if unknown; unknown heights are treated as full height for overlaps and skipped for overhead checks. A side-elevation panel shows the selected item against the ceiling.
- **Overhead checks:**
  - Items taller than the ceiling.
  - Items reaching up into a garage-door track.
  - Doors whose lift type needs more headroom than the ceiling allows.
  - Stacked items (e.g. a wall cabinet over a bench) only clash when their height ranges overlap.
  - Items mounted at or above 80" don't block floor clearance or door swings.
- **Doors:** swing doors show arcs. Overhead doors take a door height, a lift type (standard, high-lift, vertical, low-headroom) and hardware (residential or commercial 2"/3" track). Track height, backroom depth and required ceiling are calculated from manufacturer published minimums (Clopay, Garaga), before any opener allowance.
- **Layers:** show or hide by category, including utility layers (Power, Air, Dust, Lighting, HVAC).
- **Library:** typical equipment presets, plus your own "My Items". Click a preset to add it at the center of the view, or drag it onto the floor.
- **Measure tool (M):** Shift draws a straight line; Alt turns snapping off.
- **Zoom:** 25–400%, fit to window, wheel or pinch zoom, and space-drag to pan.
- **Saving and sharing:**
  - Auto-saves to the browser.
  - Named versions.
  - JSON import/export.
  - A share link that carries the whole layout in the URL; nothing is uploaded.
- **Output:** PNG export (dark), and Print / Save as PDF (light).

## Keyboard

| Key | Action |
|---|---|
| Arrows / Shift+Arrows | Nudge (snap step / 5 ft) |
| R / Shift+R | Rotate clockwise / counter-clockwise |
| E or Enter, double-click | Edit |
| L / P | Lock / always show name |
| Ctrl+D / Ctrl+A | Duplicate / select all |
| Del | Delete |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| M | Measure |
| F / 0 / + / − | Fit / 100% / zoom |
| Esc | Cancel, then clear selection |

## Data

Layouts are stored in `localStorage` under `ws_planner_v14`. A layout saved by an older version (`ws_planner_v13`) is upgraded automatically on first load; the old key is left untouched. Old JSON exports and saved versions also load.

Library sizes are typical placeholders, not manufacturer specs. Edit each item after placing it.
