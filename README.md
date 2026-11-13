# Workshop Planner

A browser-based 2D floor planner for a shop or shed. It's a single `index.html` with no build step, so it runs straight from GitHub Pages or from a local copy.

## Features

- **Properties panel (right):** click an item to edit it in place, with no pop-up dialog.
  - **Actions:** rotate, duplicate, lock, pin, front/back and delete.
  - **Fields:** size and position, height and mounting height, a four-sided clearance editor, and door settings. Only the fields that apply to that item are shown.
  - **Side view:** floor to ceiling.
  - Every change applies live and is one undo step.
  - With several items selected the panel offers align and distribute. With nothing selected it shows shop size and the issues list.
- **Issues:** the header badge counts problems. The list says what's wrong with which item; click a row to select and center it.
  - Overlaps are outlined and hatched red.
  - Blocked clearance is amber.
  - Overhead conflicts get a ↥ badge.
- **Layout:** drag, rotate (0/90/180/270), resize, lock, and duplicate items. The snap grid is anchored to the inside wall faces.
- **Selection:** shift-click or box-select several items, then move them together or nudge them with the arrow keys.
- **Heights and overhead checks:**
  - Ceiling height for the shop; height and mounting height for each item.
  - Garage doors take a door height, lift type and hardware. Track height, backroom and required ceiling are calculated from manufacturer published minimums (Clopay, Garaga), before any opener allowance.
  - Stacked items only clash when their height ranges overlap.
  - Items mounted at or above 80" (or the door height for swing doors) don't block floor clearance or swings.
- **Labels:** fitted to the on-screen size, so small items gain names as you zoom in.
- **Layers:** show or hide by category, including utility layers (Power, Air, Dust, Lighting, HVAC). Empty layers are tucked away.
- **Library:** typical equipment presets with sizes and heights, plus your own "My Items". Click a preset to add it, or drag it onto the floor.
- **Measure tool (M):** Shift draws a straight line; Alt turns snapping off.
- **Zoom:** 25–400% with fit, wheel or pinch zoom, and space-drag to pan.
- **File menu:** versions, share link (the layout lives in the URL; nothing is uploaded), PNG export, Print/PDF, and JSON export/import.
- **Tablet:** larger touch targets. In portrait the properties panel becomes a bottom sheet.

## Keyboard

| Key | Action |
|---|---|
| Arrows / Shift+Arrows | Nudge (snap step / 5 ft) |
| R / Shift+R | Rotate clockwise / counter-clockwise |
| E or Enter, double-click | Rename (focus the properties panel) |
| L / P | Lock / always show name |
| Ctrl+D / Ctrl+A | Duplicate / select all |
| Del | Delete |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| M | Measure |
| F / 0 / + / − | Fit / 100% / zoom |
| Esc | Cancel, then clear selection |

## Data

Layouts are stored in `localStorage` under `ws_planner_v14`. A layout saved by an older version (`ws_planner_v13`) is upgraded automatically on first load; the old key is left untouched. Old JSON exports and saved versions also load.

Library sizes and heights are typical placeholders, not manufacturer specs. Adjust each item after placing it.
