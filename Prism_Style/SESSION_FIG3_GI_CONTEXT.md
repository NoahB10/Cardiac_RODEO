# Session Context — Fig 3 Prism Panels (g, i)

This file captures the state at the end of the Fig 3 g+i Prism re-render
session so a new terminal can pick up integration into the Remake PPTX.

This was **Session D** — generating the R² bar (panel g) and the LOOCV
Accuracy-vs-AUC scatter strip (panel i) on slide 3 of the Remake deck.

---

## What's Done

Two Prism-style panels for **slide 3** of the Remake deck have been
rendered at native size (matching their PPT picture-frame boxes exactly,
no PPT-side scaling):

| Panel | Box (in)     | Source data XLSX                              | Description                                                          |
|-------|--------------|-----------------------------------------------|----------------------------------------------------------------------|
| 3g    | 2.10 × 1.46  | `Fig_3c_data.xlsx` → `R2_Data`                | Horizontal R² bar, 12 PK-PD equations sorted desc by O₂ R²           |
| 3i    | 3.88 × 1.49  | `Fig_3d_data.xlsx` → `LOOCV_Strip_Data`       | 3-panel LOOCV Accuracy vs AUC ROC strip (Arrhythmia / HD / Concern)  |

**The "g" and "i" letters here are SLIDE-3 SLOT LETTERS, not the historical
Fig_3c/Fig_3d panel letters.** On slide 3 the row-1 a/b/c/d/e/f letters are
already taken by the heatmap+surface pairs, so the R² bar lives in slot g
(group `Panel 82`, slide 3) and the LOOCV scatter lives in slot i (group
`Panel 70`, slide 3). Slot h (a small adjacent panel) is **manually managed
by the user — DO NOT touch it.**

**Shared style:** Helvetica, L-spines (top/right hidden), 7 pt tick
labels, 9 pt axis labels, transparent background, 600 dpi. 4× upscale +
LANCZOS downscale for crisp text. Both generators write to the Fig_3
sources folder at native size — no PPT-side rescaling needed.

**Plot-area heights match between g and i (1.00" each)** so the data
axes line up across the row. Adjusted in this session per user request.

**Color palettes (rainbow, NOT turbo) — match `generate_paper_figures.py`:**
- 3g: rank-based rainbow, sorted by O₂ R² descending. Top (best) = red
  `#d62728`, bottom (worst) = pink `#e377c2`. 12 colors in
  `RAINBOW` constant in the generator. Matches `generate_paper_figures.py:1529`.
- 3i: spectral palette keyed on canonical equation snake_case names
  (alphabetical-ish order matching Fig 3c rank). 12 colors in
  `EQ_COLORS` constant. Matches `generate_paper_figures.py:1597`. Same
  color for the same equation across both g and i panels.

**Key visual details (per user feedback during this session):**
- 3g bars have **`edgecolor="none"`** — flat colored bars without black
  borders.
- 3g X label is **`R²`** only (no "(O₂ fit)" suffix).
- 3g value labels:
  - Positive bars: just right of bar tip, overflow into MARGIN_R.
  - Negative bars: just right of the **zero line** (NOT at the bar tip),
    so they don't crash into the equation names. Matches
    `generate_paper_figures.py:1564`.
- 3i Y-axis label "AUC ROC" appears only on the leftmost sub-panel
  (Arrhythmia). Inner sub-panels have empty `set_yticklabels([])` so
  ticks are visible but labels aren't repeated.
- 3i panel titles ("Arrhythmia" / "Heart Damage" / "Concern") at 9 pt
  bold, 4% above the axes top via `ax.text(0.5, 1.04, ...)`.
- 3i markers: filled circles, `s=22 * SCALE * SCALE` (=352 in render
  space), edge `0.4 * SCALE` black.

---

## File locations (current state)

### Generated outputs — saved into Remake-sources tree

```
Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3g_prism.png       (2.10"×1.46")
Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3g_prism_data.xlsx
Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3i_prism.png       (3.88"×1.49")
Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3i_prism_data.xlsx
```

NOTE: `Output/PowerPoint_Figures_Remake/sources/Fig_3` is a **symlink** to
`Output/PowerPoint_Figures/Fig_3`. Files appear at both paths; commit/stage
through the canonical `Output/PowerPoint_Figures/Fig_3/` path.

### Generators
```
Prism_Style/generate_r2_bar.py            # produces Fig_3g_prism.png
Prism_Style/generate_loocv_scatter.py     # produces Fig_3i_prism.png
```

Run with:
```bash
python3 Prism_Style/generate_r2_bar.py
python3 Prism_Style/generate_loocv_scatter.py
```

Each `main()` calls `panel_png(3, "g")` / `panel_png(3, "i")` from
`Prism_Style/_paths.py`, which resolves to
`Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3{letter}_prism.png`.

### Earlier descriptive-name outputs (deleted in this session)
The following files from earlier iterations were **removed** and should
not be restored:
```
Fig_3_R2_bar_prism.png
Fig_3_R2_bar_prism_data.xlsx
Fig_3_LOOCV_scatter_prism.png
Fig_3_LOOCV_scatter_prism_data.xlsx
```

---

## Sizing rationale (so re-rendering doesn't drift)

Both panels follow the **Fig 6/7/8 pattern**: pin the inner plot area
size, let the labels live in margins around it.

### 3g (R² bar)
```
FIG_W = 2.10           (matches Group 82 width)
FIG_H = 1.46           (matches Group 82 height)
PLOT_W = 0.90
PLOT_H = 1.00          (must match SUB_PLOT in 3i)
MARGIN_L = 1.00        (12 equation names at 7 pt)
MARGIN_R = 0.20        (positive bar value labels overflow here)
MARGIN_T = 0.04
MARGIN_B = 0.42        (X label + bottom whitespace; auto-computed)
```

12 equation names at 7 pt require ~0.91" of MARGIN_L; 1.00" leaves
breathing room. PLOT_H=1.00 gives 0.078" per bar (12 bars in 12.75
data units) — labels' visible character height (~5 pt for Helvetica
7 pt) fits without overlap.

3 x-ticks at PLOT_W=0.90" (5 ticks would overlap at this width).

### 3i (LOOCV scatter)
```
FIG_W = 3.88           (matches Group 70 width)
FIG_H = 1.49           (matches Group 70 height)
SUB_PLOT = 1.00        (must match PLOT_H in 3g)
MARGIN_L = 0.45        (Y label "AUC ROC" rotated + tick labels at 7 pt)
MARGIN_R = 0.10
MARGIN_T = 0.18        (title 9 pt bold)
MARGIN_B = 0.31        (X label + ticks; auto-computed)
GAP = 0.165            (between sub-panels; auto-computed)
```

MARGIN_L=0.45" was bumped up from 0.30" mid-session because at 0.30
the rotated "AUC ROC" label was clipped. GAP shrank to 0.165 to
absorb the extra MARGIN_L while keeping FIG_W locked at 3.88.

---

## Integration steps (for the next terminal)

`Prism_Style/apply_layout_to_remake.py` already includes (3,"g") and
(3,"i") in `INPLACE_PANELS` (in `_layout.py`)? **CHECK** — at the end
of this session, panels g and i are NOT yet wired into `INPLACE_PANELS`.
The comment in `_layout.py` says:

> Panels g (R² bar) and i (LOOCV scatter) are intentionally NOT in this
> map — Session D rendered them at sizes larger than their PPT boxes
> under descriptive names (Fig_3_R2_bar_prism.png /
> Fig_3_LOOCV_scatter_prism.png) and noted manual placement.

That comment is now **stale**. The panels are now sized to fit their
boxes exactly (2.10×1.46 and 3.88×1.49) and named per the slot-letter
convention. The integration agent should:

1. **Update `Prism_Style/_layout.py`** — add to `INPLACE_PANELS`:
   ```python
   (3, "g"): (0.11, 2.13, "Fig_3g_prism.png"),   # R² bar in Group 82
   (3, "i"): (3.35, 2.10, "Fig_3i_prism.png"),   # LOOCV scatter in Group 70
   ```
   (Coordinates from the slide-3 PPTX scan: Group 82 at L=0.11/T=2.13,
   Group 70 at L=3.35/T=2.10.)

2. **Remove the stale comment block** in `_layout.py` that says g/i are
   intentionally NOT in this map.

3. **Run** `python3 Prism_Style/apply_layout_to_remake.py` to swap the
   image bytes inside the existing groups.

4. **Verify in PowerPoint** that:
   - Bars in 3g are flush against the panel-letter "g" at L=-0.00 / T=2.10
   - "AUC ROC" Y-label is fully visible on the leftmost sub-panel of 3i
   - Plot bottoms align between 3g and 3i (both at 1.00" plot height)

---

## Inputs (don't regenerate these)

```
Output/PowerPoint_Figures/Fig_3/Fig_3c_data.xlsx   # sheet R2_Data — 12 equations × Contractility/O2
Output/PowerPoint_Figures/Fig_3/Fig_3d_data.xlsx   # sheet LOOCV_Strip_Data — 36 rows = 12 eqs × 3 targets
```

These were produced by the existing `generate_paper_figures.py` pipeline.
The Prism re-renders are downstream-only — they read these XLSX files,
they do not write back into them.

---

## Cross-session conventions (to keep in sync)

The other sessions (A heatmaps, B line/sigmoid panels, C surfaces)
follow the same conventions as Fig 2:
- PNGs go into `Output/PowerPoint_Figures_Remake/sources/Fig_N/` named
  `Fig_N{letter}_prism.png` where `letter` is the SLOT letter on the
  slide (not the historical panel letter from the original figures).
- Paired data XLSX uses the same basename: `Fig_N{letter}_prism_data.xlsx`.
- Native size = exact PPTX box size, so `apply_layout_to_remake.py` can
  swap picture bytes in place without resizing.
- Helvetica, 7 pt ticks, 9 pt axis labels, 600 dpi, transparent.

If another session is editing `_layout.py` concurrently, watch for
merge conflicts on `INPLACE_PANELS` — each session should be appending
its own (slide, letter) keys, not overwriting the dict.
