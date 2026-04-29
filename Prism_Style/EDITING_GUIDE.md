# Editing Guide — Cardiac RODEO Remake PPTX

Task-oriented recipes for every common edit you make to the Prism panels in
`Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`.

For the master spec (slide map, INPLACE_PANELS, gotchas) see
`REMAKE_INTEGRATION_CONTEXT.md`. For per-panel font sizes see
`FONT_AUDIT.md`.

---

## How to use this guide

Each recipe has the same shape:

> **Goal** — what you want to change.
> **File / Constant** — the exact place to edit.
> **Re-render** — single command to regenerate that panel's PNG.
> **Apply** — push the new PNG into the PPTX.

The two universal commands:

```bash
PY=/Users/noahb/miniconda3/bin/python
APPLY="$PY Prism_Style/apply_layout_to_remake.py"
```

---

## Table of contents

**Text & fonts**
1. [Change tick-label size on a single panel](#1-change-tick-label-size-on-a-single-panel)
2. [Change axis-label size on a single panel](#2-change-axis-label-size-on-a-single-panel)
3. [Change inset annotation size (TC50 / waveform / AUC text)](#3-change-inset-annotation-size)
4. [Change value-label size (bars, dots)](#4-change-value-label-size)
5. [Change legend size](#5-change-legend-size)
6. [Change LOOCV sub-panel title size](#6-change-loocv-sub-panel-title-size)
7. [Change drug-label size on the dot plot](#7-change-drug-label-size-on-the-dot-plot)
8. [Change confusion-matrix cell-number size](#8-change-confusion-matrix-cell-number-size)
9. [Bring back panel-letter overlays](#9-bring-back-panel-letter-overlays)
10. [Change panel-letter font size and offset](#10-change-panel-letter-font-size-and-offset)
11. [Change the slide title font / size](#11-change-the-slide-title-font--size)
12. [Move the slide title position](#12-move-the-slide-title-position)
13. [Switch the project font (Arial → something else)](#13-switch-the-project-font)

**Layout & positioning**
14. [Capture a panel I moved manually in PowerPoint](#14-capture-a-panel-i-moved-manually-in-powerpoint)
15. [Move a panel programmatically (without opening PowerPoint)](#15-move-a-panel-programmatically)
16. [Resize a panel](#16-resize-a-panel)
17. [Align panels by plot bottom (current default)](#17-align-panels-by-plot-bottom-current-default)
18. [Align panels by top edge instead](#18-align-panels-by-top-edge-instead)
19. [Force same height for every panel in a row](#19-force-same-height-for-every-panel-in-a-row)
20. [Adjust the row positions (Fig 6/7/8)](#20-adjust-the-row-positions-fig-678)
21. [Adjust the off-slide legend stash position](#21-adjust-the-off-slide-legend-stash-position)

**Colors**
22. [Change a heatmap colormap](#22-change-a-heatmap-colormap)
23. [Change a multi-line palette](#23-change-a-multi-line-palette)
24. [Change the Organoid ROC line color](#24-change-the-organoid-roc-line-color)
25. [Change the R² bar / LOOCV scatter colormap](#25-change-the-r-bar--loocv-scatter-colormap)

**Axis ranges & ticks**
26. [Change xlim / ylim on a panel](#26-change-xlim--ylim-on-a-panel)
27. [Change tick spacing on a panel](#27-change-tick-spacing-on-a-panel)
28. [Make sure first + last ticks always show](#28-make-sure-first--last-ticks-always-show)
29. [Adjust R² bar tick rounding](#29-adjust-r-bar-tick-rounding)

**Adding / removing**
30. [Add a new panel to an existing figure](#30-add-a-new-panel-to-an-existing-figure)
31. [Remove a panel](#31-remove-a-panel)
32. [Add a brand-new figure / slide](#32-add-a-brand-new-figure--slide)

**Re-render & apply**
33. [Re-render a single panel](#33-re-render-a-single-panel)
34. [Re-render an entire figure](#34-re-render-an-entire-figure)
35. [Apply layout to the PPTX](#35-apply-layout-to-the-pptx)
36. [Re-render everything from scratch](#36-re-render-everything-from-scratch)

**Recovery & maintenance**
37. [Recover a corrupted PPTX](#37-recover-a-corrupted-pptx)
38. [Roll back a botched edit](#38-roll-back-a-botched-edit)
39. [Verify the PPTX matches the source PNGs](#39-verify-the-pptx-matches-the-source-pngs)
40. [Update FONT_AUDIT.md after a font-size change](#40-update-font_auditmd-after-a-font-size-change)

---

# Text & fonts

## 1. Change tick-label size on a single panel

| Panel(s) | Constant | File |
|---|---|---|
| 2a, 2b, 2d, 2e | (default 9 — `tick_label_size_pt=9` arg) | `generate_fig2_panels.py:78,...` |
| 2c, 2f | `TICK_LABEL_PT_LARGE = 9` | `generate_heatmaps.py:64` |
| 3a, 3c, 3e | `TICK_LABEL_PT_SMALL = 7` | `generate_heatmaps.py:66` |
| 3b, 3d, 3f | (no tick labels — set in `LABEL_PT`) | `generate_fig3_surfaces.py:74` |
| 3g | `TICK_FONT_PT = 7` | `generate_r2_bar.py:52` |
| 3i | `TICK_FONT_PT = 7` | `generate_loocv_scatter.py:76` |
| 3j, 3k | `TICK_FONT_PT = 8` | `generate_fig3_multiline.py:68` |
| 6/7/8 a | `TICK_FONT_PT = 9` | `generate_roc_curves.py:61` |
| 6/7/8 b | `TICK_FONT_PT = 9` | `generate_confusion_matrices.py:55` |
| 6/7/8 c | (default 9 in apply_prism_style call) | `generate_bar_plots.py:51` |
| 6/7/8 d | (default 9 in apply_prism_style call) | `generate_dot_plots.py:125` |
| 6/7/8 e | `TICK_FONT_PT = 9` | `generate_shap_aligned_pairs.py:76` |
| 6/7 f, g | `TICK_FONT_PT = 9` | `generate_roc_comparison.py:81` |

**Recipe:**
```bash
# Edit the constant, then re-render the affected generator + re-apply:
$PY Prism_Style/<generator>.py
$APPLY
```

## 2. Change axis-label size on a single panel

Same files, look for `AXIS_LABEL_PT*` / `ylabel_size_pt=` / `xlabel_size_pt=`:

| Panel(s) | Constant | File |
|---|---|---|
| 2a, 2b, 2d, 2e | `ylabel_size_pt=13, xlabel_size_pt=13` | `generate_fig2_panels.py:79-80,...` |
| 2c, 2f | `AXIS_LABEL_PT_LARGE = 13` | `generate_heatmaps.py:63` |
| 3a, 3c, 3e | `AXIS_LABEL_PT_SMALL = 7` | `generate_heatmaps.py:65` |
| 3b, 3d, 3f | `LABEL_PT = 10` | `generate_fig3_surfaces.py:74` |
| 3g | `AXIS_LABEL_PT = 9` | `generate_r2_bar.py:53` |
| 3i | `AXIS_LABEL_PT = 9` | `generate_loocv_scatter.py:77` |
| 3j, 3k | `AXIS_LABEL_PT = 11` | `generate_fig3_multiline.py:69` |
| 6/7/8 a | `AXIS_LABEL_PT = 13` | `generate_roc_curves.py:62` |
| 6/7/8 b | `AXIS_LABEL_PT = 13` | `generate_confusion_matrices.py:56` |
| 6/7/8 c | `ylabel_size_pt=13` | `generate_bar_plots.py:52` |
| 6/7/8 d | `ylabel_size_pt=13, xlabel_size_pt=13` | `generate_dot_plots.py:126-127` |
| 6/7/8 e | `AXIS_LABEL_PT = 13` | `generate_shap_aligned_pairs.py:77` |
| 6/7 f, g | `AXIS_LABEL_PT = 13` | `generate_roc_comparison.py:82` |

**To unify Fig 3** (currently four scales — see `FONT_AUDIT.md`):
edit the four files above so all use the same pair (e.g. `tick=7, axis=9`).

## 3. Change inset annotation size

| Where | Constant | File |
|---|---|---|
| 2b "TC50 = X mM" | inline `helvetica(8 * scale)` | `generate_fig2_panels.py:237` |
| 2e waveform labels ("X mM, Y bpm") | inline `helvetica(7 * scale)` | `generate_fig2_panels.py:401` |
| 6/7/8 a "AUC = …" annotation | `ANNOTATION_PT = 9` | `generate_roc_curves.py:63` |

## 4. Change value-label size

| Where | Constant | File |
|---|---|---|
| 3g R² value labels | `VALUE_LABEL_PT = 6` | `generate_r2_bar.py:54` |
| 6/7/8 c bar values | `VALUE_LABEL_PT = 7` | `generate_bar_plots.py:66` |
| 6/7 g compare-bar values | `VALUE_LABEL_PT_H = 7` | `generate_bar_plots.py:68` |
| 6/7/8 d dot values | inline `helvetica(7 * scale)` | `generate_dot_plots.py:104` |

## 5. Change legend size

| Panel | Constant | File |
|---|---|---|
| 3j, 3k inline legend | `LEGEND_FONT_PT = 7` | `generate_fig3_multiline.py:70` |
| 6/7/8 e SHAP legend | `LEGEND_FONT_PT = 8` | `generate_shap_aligned_pairs.py:78` |
| 6/7 f, g comparison legends | `LEGEND_FONT_PT = 8` | `generate_roc_comparison.py:83` |
| 6/7/8 d dot plot legend | inline `helvetica(7 * scale)` | `generate_dot_plots.py:153` |
| 6/7 g compare-bar legend | inline `helvetica(VALUE_LABEL_PT_H * SCALE)` | `generate_bar_plots.py:321` |

## 6. Change LOOCV sub-panel title size

`generate_loocv_scatter.py:78` — `TITLE_FONT_PT = 9` controls the
"Arrhythmia" / "Heart Damage" / "Concern" headers.

## 7. Change drug-label size on the dot plot

`generate_dot_plots.py:77` — `drug_label_size_pt = 5`. Increase if you reduce
the number of drugs displayed; the 5-pt size was chosen to fit 25 drugs.

## 8. Change confusion-matrix cell-number size

`generate_confusion_matrices.py:54` — `CELL_FONT_PT = 14`. These are the
large digits inside each CM cell.

## 9. Bring back panel-letter overlays

`apply_layout_to_remake.py:83` — flip `ADD_PANEL_LETTERS = False` to `True`,
then re-apply:

```bash
$APPLY
```

The script will add `PanelLetter_a/b/c/...` textboxes back to slides 2/3/6/7/8
at each panel's top-left corner with the offset constants below.

## 10. Change panel-letter font size and offset

In `apply_layout_to_remake.py:71-77`:

```python
LETTER_OFFSET_X_IN = -0.05   # how far left of the panel left edge
LETTER_OFFSET_Y_IN = -0.18   # how far above the panel top edge
LETTER_BOX_W_IN = 0.30       # textbox width
LETTER_BOX_H_IN = 0.20       # textbox height
LETTER_FONT_PT = 12          # font size (Arial Bold)
LETTER_FONT_BOLD = True
```

Letters are only re-added when `ADD_PANEL_LETTERS = True` (recipe 9).

## 11. Change the slide title font / size

The slide title (`Figure 2: …`, `Figure 3: …`, etc.) is the `TextBox 1`
shape on each slide. The script does NOT touch it — edit directly in
PowerPoint, or programmatically:

```python
from pptx import Presentation
from pptx.util import Pt
prs = Presentation("Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx")
for slide_idx in (1, 2, 5, 6, 7):  # 0-based: slides 2,3,6,7,8
    sl = prs.slides[slide_idx]
    for sp in sl.shapes:
        if sp.name == "TextBox 1":
            for para in sp.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(14)   # change as needed
                    run.font.name = "Arial"
                    run.font.bold = True
prs.save("Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx")
```

## 12. Move the slide title position

Same approach — `sp.left` / `sp.top` set position (in EMU; 914400 EMU = 1 inch):

```python
from pptx.util import Inches
for slide_idx in (1, 2, 5, 6, 7):
    sl = prs.slides[slide_idx]
    for sp in sl.shapes:
        if sp.name == "TextBox 1":
            sp.left = Inches(0.30)   # new X
            sp.top  = Inches(0.10)   # new Y
            sp.width = Inches(6.49)
            sp.height = Inches(0.40)
prs.save(...)
```

## 13. Switch the project font

Today the stack is on Arial. To change globally:

1. **`figure_config.py`** — update the `Path` at line ~30 (`/System/Library/Fonts/Supplemental/Arial.ttf`) and reorder `plt.rcParams['font.sans-serif']`.
2. **`prism_style.py`** — update `_ARIAL_PATH` and `_ARIAL_BOLD_PATH` (line ~37) to point at the new font's TTFs. Optionally rename `arial()` → `something_else()` and update the alias.
3. **`apply_layout_to_remake.py:128`** — change `run.font.name = "Arial"`.
4. Re-render all PNGs (recipe 36) + apply (recipe 35).

---

# Layout & positioning

## 14. Capture a panel I moved manually in PowerPoint

After moving panels in PowerPoint, run:

```bash
$PY <<'PY'
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
EMU = 914400
prs = Presentation("Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx")
def walk(shapes):
    for sp in shapes:
        if sp.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(sp.shapes)
        elif sp.shape_type == MSO_SHAPE_TYPE.PICTURE:
            yield sp
for idx, label in [(1,"Slide 2"), (2,"Slide 3")]:
    sl = prs.slides[idx]
    print(f"\n=== {label} ===")
    for sp in walk(sl.shapes):
        L = sp.left/EMU; T = sp.top/EMU
        W = sp.width/EMU; H = sp.height/EMU
        if -0.5 <= L <= 7.6:
            print(f"  ({L:5.2f}, {T:5.2f})  {W:5.2f} x {H:5.2f}  {sp.name}")
PY
```

Match each new `(L, T)` against the old INPLACE_PANELS coords in
`Prism_Style/_layout.py` and edit the tuple. Then `$APPLY`.

## 15. Move a panel programmatically

Edit `Prism_Style/_layout.py` → `INPLACE_PANELS`:

```python
(3, "g"): (0.11, 2.13, "Fig_3g_prism.png"),   # change to (NEW_L, NEW_T, ...)
```

The frame's existing `(L, T)` must still be at the OLD coords for the script
to find it. If you change the coord here while the frame in the PPTX is at
a different spot, the swap will warn and skip. Either:
- Move the frame in PowerPoint first to the new spot, OR
- Use a one-shot script to set `sp.left = Inches(new_L)`.

## 16. Resize a panel

Two modes:

**A — generator-side** (preferred): change the panel's `target_figsize_in`
in its generator and add the slide/letter to `RESIZE_TO_NATIVE` in
`_layout.py`. The script will resize the PPTX frame to match the PNG's
native size on next apply.

**B — pptx-side**: open PowerPoint, drag the corner. Then capture the new
size into the panel-spec docstring (the `INPLACE_PANELS` tuple itself
doesn't store W/H, only L/T).

## 17. Align panels by plot bottom (current default)

Already the default for slides 6/7/8. Configured by:

```python
ROW_LAYOUT["row1"]["plot_bottom"] = 2.27   # in inches
MARGIN_B["a"] = 0.55                        # bottom margin of panel a's PNG
# top = plot_bottom + MARGIN_B[letter] - image_h
```

Slides 2/3 use INPLACE_PANELS positions verbatim (no auto-alignment).

## 18. Align panels by top edge instead

Patch `update_slide_loose()` in `apply_layout_to_remake.py`:

```python
# Replace the line:
T = _compute_picture_top(letter, h_in)
# With:
T = ROW_LAYOUT[PANEL_ROW[letter]].get("top", row["letter_top"] + 0.20)
```

…and add `"top"` keys to each row in `ROW_LAYOUT`. Caveat: panels with
different heights will end at different bottoms.

## 19. Force same height for every panel in a row

Add a `target_h` to each `ROW_LAYOUT` row, then in `update_slide_loose()`
override the picture's `height = Inches(target_h)` and stretch the width
proportionally (`width = Inches(target_h * w_in / h_in)`). Caveat: if the
PNG aspect ratios differ a lot, panels will have inconsistent widths.

A cleaner approach is to **change the generator** so PNGs are produced at
a consistent target_h:
```python
target_figsize_in = (target_w, ROW_TARGET_H)
```
Then re-render that figure (recipe 34).

## 20. Adjust the row positions (Fig 6/7/8)

`Prism_Style/_layout.py` → `ROW_LAYOUT`:

```python
ROW_LAYOUT = {
    "row1": {"plot_bottom": 2.27, "letter_top": 0.62, "lefts": {...}},
    "row2": {"plot_bottom": 4.78, "letter_top": 2.82, "lefts": {...}},
    "row3": {"plot_bottom": 6.95, "letter_top": 5.21, "lefts": {...}},
}
```

`plot_bottom` is the inches-from-slide-top where each panel's plotted data
ends. `letter_top` is where panel-letter textboxes sit (only relevant when
ADD_PANEL_LETTERS=True). Edit, then `$APPLY`.

## 21. Adjust the off-slide legend stash position

`Prism_Style/_layout.py` →

```python
LEGEND_STASH_X = 8.0
LEGEND_STASH_T_BY_LETTER = {"f": 0.50, "g": 1.30}
```

Set `X` < 7.09 to put legends on-slide. Then `$APPLY`.

---

# Colors

## 22. Change a heatmap colormap

`generate_heatmaps.py:59-60`:
```python
HEATMAP_BLUE = "#123BFF"   # cool end
HEATMAP_RED  = "#FF2908"   # warm end
```
The middle is hard-coded white in the `LinearSegmentedColormap` (line 320).
For a different gradient, replace `[HEATMAP_BLUE, "white", HEATMAP_RED]`.

## 23. Change a multi-line palette

| Panel | Constant | File |
|---|---|---|
| 2a Epirubicin O₂ multi-line (8 doses) | `PALETTE_8` | `generate_fig2_panels.py:53-` |
| 2d Mexiletine Contractility (7 doses) | `PALETTE_PLASMA_7` | `generate_fig2_panels.py:285-` |
| 2e Mexiletine waveforms (3 levels) | `WAVEFORM_LEVELS` (level→color) | `generate_fig2_panels.py:~330` |
| 3j, 3k (3 conc plasma) | `_PLASMA = plt.get_cmap("plasma", 3)` | `generate_fig3_multiline.py:79` |

Edit the list (each entry a hex color), re-render that generator, apply.

## 24. Change the Organoid ROC line color

`generate_roc_curves.py` and `generate_roc_comparison.py` — search for
`#2ca02c` (the green that's hardcoded throughout). The convention is
**Organoid is always green and always first in the legend**.

## 25. Change the R² bar / LOOCV scatter colormap

| Panel | Constant | File |
|---|---|---|
| 3g R² bar | `RAINBOW = [...]` (12 hex colors, ranked best→worst) | `generate_r2_bar.py:62` |
| 3i LOOCV scatter | `EQ_COLORS = [(eq_name, hex), ...]` | `generate_loocv_scatter.py:47` |

Both palettes are aligned across panels by canonical equation name — keep
the EQ_COLORS keys in `generate_loocv_scatter.py` matching the equation
order in `RAINBOW` if you want g and i to colour-match.

---

# Axis ranges & ticks

## 26. Change xlim / ylim on a panel

| Panel | File:line |
|---|---|
| 2a | `generate_fig2_panels.py:122-123` |
| 2b | `generate_fig2_panels.py:215-216` |
| 2d | `generate_fig2_panels.py:312-313` |
| 2e | `generate_fig2_panels.py:405-407` |
| 2c, 2f, 3a, 3c, 3e | `generate_heatmaps.py:389-390` (data-driven; edit `vmin`/`vmax` at line 365 for color scale) |
| 3b, 3d, 3f | `generate_fig3_surfaces.py` — surface mesh fixed by data |
| 3g | `generate_r2_bar.py:118-128` (xlim auto from data; see recipe 29) |
| 3i | `generate_loocv_scatter.py:121-122` |
| 3j, 3k | `generate_fig3_multiline.py:176, 184-189` |
| 6/7/8 a | `generate_roc_curves.py:104-105` |
| 6/7/8 c | `generate_bar_plots.py:102, 173` (ylim only) |
| 6/7/8 d | `generate_dot_plots.py:111` (xlim only) |
| 6/7 f, g | `generate_roc_comparison.py:294-295` |

## 27. Change tick spacing on a panel

| Panel | File:line |
|---|---|
| 2a | `generate_fig2_panels.py:124-125` (xticks/yticks lists) |
| 2b | `generate_fig2_panels.py:217, 224` |
| 2d | `generate_fig2_panels.py:314-315` |
| 2e | `generate_fig2_panels.py:408-409` (yticks intentionally `[]`) |
| 3i | `generate_loocv_scatter.py:123-124` |
| 3j, 3k | `generate_fig3_multiline.py:177, 186, 189` |
| 6/7/8 a | `generate_roc_curves.py:106-107` |
| 6/7/8 c | `generate_bar_plots.py:103, 174` |
| 6/7/8 d | `generate_dot_plots.py:112` |
| 6/7 f, g | `generate_roc_comparison.py:296-297` |

For heatmaps, tick centers are computed at runtime from data (4 X ticks for
small Fig 3, 5 for large Fig 2; `MAX_Y_TICK_LABELS_*` for Y).

## 28. Make sure first + last ticks always show

The endpoint-tick rule (no padding past the last labelled tick): set
`xlim` / `ylim` exactly equal to the first and last tick values.

✅ Compliant: `set_xlim(0, 1); set_xticks([0, 0.25, 0.5, 0.75, 1.0])`
❌ Non-compliant: `set_xlim(-2, 102); set_xticks([0, 25, 50, 75, 100])`

If you change a panel's range, double-check the ticks include both ends.

## 29. Adjust R² bar tick rounding

`generate_r2_bar.py:118-128`:

```python
xtick_lo = np.floor(vmin * 4) / 4   # outward round to 0.25
xtick_hi = np.ceil(vmax * 4) / 4
step = 0.25 if (xtick_hi - xtick_lo) <= 1.5 else 0.5
```

To round to 0.1 instead, change `* 4` → `* 10` and `0.25` → `0.1`.

---

# Adding / removing

## 30. Add a new panel to an existing figure

**For Fig 2/3 (in-place swap path):**

1. Build a new generator (or extend an existing one) that writes
   `Fig_N{letter}_prism.png` + `_data.xlsx` to
   `Output/PowerPoint_Figures_Remake/sources/Fig_N/`.
2. In PowerPoint, place a picture frame on slide N at your chosen `(L, T)`
   with any image (or a placeholder).
3. Add to `INPLACE_PANELS` in `_layout.py`:
   ```python
   (N, "newletter"): (L, T, "Fig_N{newletter}_prism.png"),
   ```
4. If the PNG's native size differs from the placeholder frame, also add
   `(N, "newletter")` to `RESIZE_TO_NATIVE`.
5. Run the generator + `$APPLY`.

**For Fig 6/7/8 (loose-rebuild path):**

1. Build a generator that writes `Fig_N{letter}_prism.png`.
2. Add to `CONTENT[N]` in `_layout.py`:
   ```python
   "Panel_Nh": "Fig_Nh_prism.png",
   ```
3. Add the letter to `PANEL_ROW`, set its row's `lefts[letter]` and add a
   `MARGIN_B[letter]` entry.
4. Apply.

## 31. Remove a panel

**Slides 2/3:** Remove the entry from `INPLACE_PANELS` + `RESIZE_TO_NATIVE`,
and delete the picture frame in PowerPoint (the script doesn't auto-delete
free-standing pictures on slides 2/3).

**Slides 6/7/8:** Remove the entry from `CONTENT[N]`. The script's wipe step
will clean up automatically on next apply.

## 32. Add a brand-new figure / slide

1. Add a new slide in PowerPoint with a `TextBox 1` whose text starts with
   `"Figure 9:"` (or whatever number).
2. If using loose-rebuild: add `9` to `FIGS = (6, 7, 8)` in
   `apply_layout_to_remake.py:49`, add `CONTENT[9]`, `REMOVE[9]`, etc.
3. If using INPLACE: add new entries to `INPLACE_PANELS` and a fresh slide
   index to `INPLACE_FIG_NUM`.
4. Apply.

---

# Re-render & apply

## 33. Re-render a single panel

Each generator script regenerates ALL panels it owns, but the cost is small
(<1 min each). Recipes:

| Panel | Command |
|---|---|
| 2a/b/d/e | `$PY Prism_Style/generate_fig2_panels.py` |
| 2c, 2f, 3a, 3c, 3e | `$PY Prism_Style/generate_heatmaps.py` |
| 3b/d/f | `$PY Prism_Style/generate_fig3_surfaces.py` |
| 3j/k | `$PY Prism_Style/generate_fig3_multiline.py` |
| 3g | `$PY Prism_Style/generate_r2_bar.py` |
| 3i | `$PY Prism_Style/generate_loocv_scatter.py` |
| 6/7/8 a | `$PY Prism_Style/generate_roc_curves.py` |
| 6/7/8 b | `$PY Prism_Style/generate_confusion_matrices.py` |
| 6/7/8 c | `$PY Prism_Style/generate_bar_plots.py` |
| 6/7/8 d | `$PY Prism_Style/generate_dot_plots.py` |
| 6/7/8 e | `$PY Prism_Style/generate_shap_aligned_pairs.py` |
| 6/7 f/g | `$PY Prism_Style/generate_roc_comparison.py` |

## 34. Re-render an entire figure

Call every generator that targets that figure. Example (Fig 3):

```bash
$PY Prism_Style/generate_heatmaps.py
$PY Prism_Style/generate_fig3_surfaces.py
$PY Prism_Style/generate_fig3_multiline.py
$PY Prism_Style/generate_r2_bar.py
$PY Prism_Style/generate_loocv_scatter.py
```

## 35. Apply layout to the PPTX

```bash
$PY Prism_Style/apply_layout_to_remake.py
```

Always safe to re-run. Watch for `[WARN]` lines indicating frames the script
couldn't find at the expected positions.

## 36. Re-render everything from scratch

See `REMAKE_INTEGRATION_CONTEXT.md` → "Quick rebuild (full)". Run the whole
block, then apply.

---

# Recovery & maintenance

## 37. Recover a corrupted PPTX

```bash
git show HEAD:"Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx" > /tmp/clean.pptx
cp /tmp/clean.pptx "Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx"
$APPLY
```

## 38. Roll back a botched edit

```bash
# See what was last committed:
git log --oneline -10 -- Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx

# Restore the PPTX to that commit:
git checkout <commit-sha> -- Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx

# Restore _layout.py / generator changes too:
git checkout <commit-sha> -- Prism_Style/
```

## 39. Verify the PPTX matches the source PNGs

```bash
$PY <<'PY'
import hashlib
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
EMU = 914400
prs = Presentation("Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx")
def walk(shapes):
    for s in shapes:
        if s.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(s.shapes)
        elif s.shape_type == MSO_SHAPE_TYPE.PICTURE:
            yield s
import sys
sys.path.insert(0, "Prism_Style")
from _layout import INPLACE_PANELS, INPLACE_FIG_NUM
for (slide, letter), (L, T, fname) in INPLACE_PANELS.items():
    sl = prs.slides[slide-1]
    fig = INPLACE_FIG_NUM[slide]
    src = Path(f"Output/PowerPoint_Figures_Remake/sources/Fig_{fig}/{fname}")
    src_md5 = hashlib.md5(src.read_bytes()).hexdigest()[:10]
    pic = next((sp for sp in walk(sl.shapes)
                if abs(sp.left/EMU - L) < 0.05 and abs(sp.top/EMU - T) < 0.05), None)
    if pic is None:
        print(f"  ({slide},{letter})  NO FRAME at ({L:.2f},{T:.2f})")
        continue
    blip = pic._element.find(f".//{{{NS_A}}}blip")
    rid = blip.attrib[f"{{{NS_R}}}embed"]
    pptx_md5 = hashlib.md5(pic.part.rels[rid].target_part.blob).hexdigest()[:10]
    ok = "OK" if pptx_md5 == src_md5 else "STALE"
    print(f"  ({slide},{letter})  {ok}  pptx={pptx_md5}  src={src_md5}")
PY
```

## 40. Update FONT_AUDIT.md after a font-size change

Edit `Prism_Style/FONT_AUDIT.md` and update the relevant row in the matrix.
The constants are documented in the "Source of truth — constants per file"
section at the bottom. Keep that section in sync with the actual `*_PT`
constants in each generator.

---

## See also

- `REMAKE_INTEGRATION_CONTEXT.md` — full integration spec and slide map.
- `FONT_AUDIT.md` — per-panel font size matrix; parked decisions for Fig 3.
- `SESSION_*.md` — historical hand-off notes from the original 4-session
  build (kept for archaeology only; do not consult for current state).
