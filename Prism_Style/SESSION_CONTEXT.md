# Prism_Style — Session Context for Remake PPTX Integration

This file is a hand-off note covering the four parallel "operation plan" sessions that build Prism-style replacements for the figures in `Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`. Read it end-to-end before continuing — it pins down conventions, file locations, the swap-into-PPTX mechanism, and which panels are done vs. still open.

---

## 1. Goal

Replace the publication figures inside `Cardiac_RODEO_Remake.pptx` with Prism-style versions that:
- Render at exact PPTX box dimensions so PPT does no scaling (fonts stay crisp).
- Use Helvetica throughout (loaded by `figure_config.py`).
- Use a clean Prism axis style: `apply_prism_style()` from `prism_style.py` — hides top/right spines, sets spine width, tick length/width, label fonts, removes redundant tick artefacts.
- Are render-at-scale (default `SCALE=4`) then LANCZOS-downsampled to the target pixel count so anti-aliased edges stay crisp.

Each generator writes:
- A `Fig_N{letter}_prism.png` into `Output/PowerPoint_Figures_Remake/sources/Fig_N/` (which is a symlink → `Output/PowerPoint_Figures/Fig_N/`).
- A paired `Fig_N{letter}_prism_data.xlsx` next to it (Plotted / Coefficients / Metadata sheets).

Then `apply_layout_to_remake.py` walks the PPTX and swaps the picture bytes for each tracked panel.

---

## 2. Slide Map

| Slide # (1-based) | Figure |
|---|---|
| 2 | Figure 2 (PK-PD curves, heatmaps, etc.) |
| 3 | Figure 3 (heatmaps + 3D surfaces + multi-line dose-response + R² bar + LOOCV scatter) |
| 7 | Figure 6 (Arrhythmia model) |
| 8 | Figure 7 (HeartDamage model) |
| 9 | Figure 8 (ConcernBinary model) |

Slides 4-6 are not Prism-style targets in this work.

---

## 3. The Four Sessions

> "Sessions" are scopes of work. They were not strict — re-reads and fixes happened across them. The list below is what each session shipped.

### Session A — Figure 2 heatmaps + Figure 3 heatmaps
- Slide 2: panels c, f (heatmaps) — generated as standalone Prism PNGs and registered in `INPLACE_PANELS`.
- Slide 3: panels a, c, e (Dactinomycin / Nifedipine / Mexiletine O2 heatmaps).
- Source data: `Cleaned_Data/Heatmaps/<Drug>/*_sorted.csv`, smoothed with LOWESS w=16 per-well, blue→white→red colormap.
- Generators live in `Prism_Style/`; named per-figure (e.g. `generate_fig2_heatmaps.py`, `generate_fig3_heatmaps.py`).

### Session B — Figure 2 line/sigmoid + Figure 2 panels d/e
- Slide 2: panels a, b, d, e (line plots, sigmoid fit, SNR, Mexiletine multi-line).
- Used `INPLACE_PANELS` to swap into background pictures of group panels created manually in PPTX.

### Session C — Figure 3 surfaces (b, d, f) + multi-line (j, k)  ← most of this session's work
- **Generators:**
  - `Prism_Style/generate_fig3_surfaces.py` — builds 3D surface PNGs for **b (Dactinomycin, Eq3 gaussian_hill_hybrid), d (Nifedipine, Eq10 modified_hill_simple), f (Mexiletine, Eq7 biphasic_response)**.
  - `Prism_Style/generate_fig3_multiline.py` — builds multi-line dose-response PNGs for **j (Vandetanib O2) and k (Sotalol Contractility)**.
- **Final dimensions (after iteration with the user):**
  - `b/d/f`: PANEL_W=1.70", PANEL_H=1.80" → inner 3D plot box ≈ 0.97×0.96" (per user measurement).
  - `j/k`: PANEL_W=2.54", PANEL_H=2.13" → inner plot area = **1.89×1.28"** (4.8×3.26 cm per user spec). MARGIN_T was bumped 0.12 → 0.30 so "Normalized Contractility" Y label clears the top.
- **Surface label convention** (CLAUDE.md "3D Surface Plots"):
  - View: `elev=25, azim=-158`.
  - Axes inset rect: `[0.20, 0.22, 0.68, 0.70]`.
  - X label "Time (h)" via `ax.set_xlabel(...)` with `labelpad=6` — auto-rotates to follow X axis projection.
  - Y label "Dose Ratio" via `ax.set_ylabel(...)` with `labelpad=6`.
  - Z label "O₂ (%)" via `ax.text2D(-0.08, 0.47, ...)` (rotation=90) — `set_zlabel` line-wraps "O2" / "(%)" on narrow columns; text2D avoids that. y=0.47 sits on the projected Z-axis midpoint.
  - LABEL_PT=10 (the panel is small).
  - Wireframe back walls (transparent face, black edges) instead of opaque panes; main 3D axis lines hidden.
- **Multi-line styling** (matches `generate_paper_figures.py` Fig_3e):
  - Colors: `plt.get_cmap("plasma", 3)` — high dose = dark purple, mid = magenta, low = yellow.
  - Replicate "Data" lines: solid, `linewidth=0.22pt`, alpha=0.85.
  - Model fit overlay: dashed `(4,3)`, `linewidth=0.55pt`.
  - X axis: `set_xticks(range(0,101,10))`, label "Time from exposure (h)".
  - Y axis: "Normalized Oxygen" (j) / "Normalized Contractility" (k).
  - Y range / ticks per panel:
    - j (O2 rising): `ylim=(0.5, 4.0)`, yticks `[1,2,3,4]`.
    - k (Contractility decay): `ylim=(0.4, 1.05)`, yticks `[0.4,0.6,0.8,1.0]`.
  - Legend: lower-right (j) / lower-left (k); 3 conc colors + Data + Model entries; frameless.
- **Source data: `Output/PowerPoint_Figures/Fig_3/Fig_3e_data.xlsx`** (already contains the heavily smoothed `t_fine, v_norm` per replicate from `generate_paper_figures.py`'s `_intensive_smooth` pipeline — no need to re-smooth in the Prism generator).

### Session D — Figure 3 panels g (R² bar) and i (LOOCV scatter)
- **Generators (already shipped before Session C):**
  - `Prism_Style/generate_r2_bar.py` — horizontal R² bar across drugs/equations, ~4.20×2.90".
  - `Prism_Style/generate_loocv_scatter.py` — 3-panel scatter (Arrhythmia / Heart Damage / Concern), ~6.05×2.13".
- Outputs use **panel_named_png(3, "R2_bar")** / **panel_named_png(3, "LOOCV_scatter")** — note these are NOT in the `Fig_N{letter}_prism.png` naming pattern.
- Saved as `Fig_3_R2_bar_prism.png` and `Fig_3_LOOCV_scatter_prism.png`.
- **NOT yet placed automatically** — Session D rendered them at sizes larger than their PPT slot boxes, so manual drag/drop is required (or extend `INPLACE_PANELS`/`RESIZE_TO_NATIVE` for them).
- Color map: `_equations.equation_color_map()` (turbo over the 12 canonical equation names).

---

## 4. Key Files

```
Prism_Style/
├── _layout.py                    # INPLACE_PANELS map + RESIZE_TO_NATIVE set + ROW_LAYOUT
├── _paths.py                     # panel_dir(N), panel_png(N, letter), panel_data(N, letter), panel_named_png(N, name)
├── _equations.py                 # canonical equation order + turbo color map
├── apply_layout_to_remake.py     # MAIN orchestrator — runs swaps + resizes for tracked panels
├── prism_style.py                # apply_prism_style() + render_at_scale() + helvetica()
├── figure_config.py              # registers Helvetica from project fonts/
├── generate_fig2_*.py            # Session A/B generators
├── generate_fig3_heatmaps.py     # Session A
├── generate_fig3_surfaces.py     # Session C  (b, d, f)
├── generate_fig3_multiline.py    # Session C  (j, k)
├── generate_r2_bar.py            # Session D  (g)
├── generate_loocv_scatter.py     # Session D  (i)
└── SESSION_CONTEXT.md            # this file
```

---

## 5. The Swap Mechanism

`apply_layout_to_remake.py` is the orchestrator. Two phases relevant here:

1. **Loose-rebuild (slides 7/8/9, Figures 6/7/8):** wipes all pictures + panel-letter textboxes, re-adds picture per `CONTENT[fig_num]` at positions from `ROW_LAYOUT` / `PANEL_ROW`.
2. **In-place swap (slides 2/3, Figures 2/3):** for each `(slide_1based, letter)` in `INPLACE_PANELS`, finds the picture frame at the expected `(left_in, top_in)` and replaces its image bytes — keeps the user's manual layout.
   - If `(slide_1based, letter) ∈ RESIZE_TO_NATIVE`, the picture box is *also* resized to match the rendered PNG's native dimensions (top-left position kept).
   - This is how the bigger-than-original Fig 3 surfaces (1.70×1.80") and multi-line panels (2.54×2.13") got their boxes grown beyond the original PPTX placeholder sizes.

Run with:
```bash
python Prism_Style/apply_layout_to_remake.py
```

PPTX is updated in place. **If the file gets corrupted** (zlib error from a partial write), recover via:
```bash
git show HEAD:"Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx" > /tmp/clean.pptx
cp /tmp/clean.pptx "Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx"
python Prism_Style/apply_layout_to_remake.py   # re-apply on top of clean baseline
```

---

## 6. INPLACE_PANELS — Current State

```python
INPLACE_PANELS = {
    # (slide_1based, letter): (left_in, top_in, png_filename)
    # Slide 2 (Figure 2):
    (2, "a"): (0.13, 4.92, "Fig_2a_prism.png"),
    (2, "b"): (2.28, 4.88, "Fig_2b_prism.png"),
    (2, "c"): (4.50, 4.90, "Fig_2c_prism.png"),
    (2, "d"): (0.16, 6.72, "Fig_2d_prism.png"),
    (2, "e"): (2.51, 6.68, "Fig_2e_prism.png"),
    (2, "f"): (4.51, 6.69, "Fig_2f_prism.png"),
    # Slide 3 (Figure 3):
    (3, "a"): (0.04, 0.93, "Fig_3a_prism.png"),
    (3, "c"): (2.34, 0.94, "Fig_3c_prism.png"),
    (3, "e"): (4.65, 0.94, "Fig_3e_prism.png"),
    (3, "b"): (1.25, 0.79, "Fig_3b_prism.png"),   # Dactinomycin O2 surface (1.70x1.80")
    (3, "d"): (3.56, 0.79, "Fig_3d_prism.png"),   # Nifedipine   O2 surface (1.70x1.80")
    (3, "f"): (5.85, 0.79, "Fig_3f_prism.png"),   # Mexiletine   O2 surface (1.70x1.80")
    (3, "j"): (0.10, 3.88, "Fig_3j_prism.png"),   # Vandetanib O2 multi-line (2.54x2.13")
    (3, "k"): (2.74, 3.87, "Fig_3k_prism.png"),   # Sotalol Contractility multi-line (2.54x2.13")
}

RESIZE_TO_NATIVE = {
    (3, "b"), (3, "d"), (3, "f"),
    (3, "j"), (3, "k"),
}
```

Panels NOT in `INPLACE_PANELS` for slide 3 (intentionally):
- **g** (R² bar) — Session D, manual placement; render is bigger than the original PPTX slot.
- **h** (NN diagram) — externally created asset, not script-managed.
- **i** (LOOCV scatter) — Session D, manual placement, same reason as g.

---

## 7. Run Order to Rebuild Everything

```bash
# Render PNGs (any subset can be re-run independently):
python Prism_Style/generate_fig2_heatmaps.py
python Prism_Style/generate_fig2_lines_sigmoid.py
python Prism_Style/generate_fig2_panels_de.py
python Prism_Style/generate_fig3_heatmaps.py
python Prism_Style/generate_fig3_surfaces.py        # Session C: b, d, f
python Prism_Style/generate_fig3_multiline.py       # Session C: j, k
python Prism_Style/generate_r2_bar.py               # Session D: g
python Prism_Style/generate_loocv_scatter.py        # Session D: i

# Stamp everything into the PPTX:
python Prism_Style/apply_layout_to_remake.py
```

(Generator filenames above are descriptive — verify with `ls Prism_Style/`.)

---

## 8. What's Done / What's Open

### Done (this session, Session C):
- ✅ Fig 3b/d/f — 3D surfaces with axis-aligned labels (X/Y via `set_xlabel/ylabel`, Z via `text2D` to avoid wrap), inner 3D box ~0.97×0.96", panel 1.70×1.80", auto-resize on swap.
- ✅ Fig 3j/k — multi-line dose-response, plasma colormap, line widths 0.22/0.55pt, plot area exactly 1.89×1.28", "Time from exposure (h)" / "Normalized Oxygen" + "Normalized Contractility" labels, X ticks every 10h, j legend lower-right / k legend lower-left, top margin 0.30" so the long Y label clears.

### Done (Session A/B):
- ✅ Fig 2 panels a-f — line/sigmoid + heatmaps via in-place swap.
- ✅ Fig 3 panels a/c/e — heatmaps via in-place swap.

### Done (Session D — but NOT auto-placed):
- ✅ R² bar (`Fig_3_R2_bar_prism.png`, ~4.20×2.90").
- ✅ LOOCV scatter (`Fig_3_LOOCV_scatter_prism.png`, ~6.05×2.13").
- ⚠ These need manual drag-drop into slide 3, OR add `(3, "g")` / `(3, "i")` to `INPLACE_PANELS` + `RESIZE_TO_NATIVE` with their picture-frame positions and corresponding filename (note: filename pattern differs from the `Fig_N{letter}_prism.png` convention — Session D used `panel_named_png()`).

### Open:
- 🔲 Slides 7/8/9 (Figures 6/7/8) — loose-rebuild path is wired in `update_slide_loose()`; per-panel generators (`generate_fig6_*.py`, etc.) need to be confirmed/re-run.
- 🔲 Decide whether to bring panels g and i under `apply_layout_to_remake.py` automation, or leave manual.
- 🔲 Slide-3 layout may need the user to rearrange now that b/d/f boxes are bigger than the original slots — boxes will overlap with adjacent panels until the user moves things in PowerPoint.

---

## 9. Conventions / Gotchas

- **Excel coefficient sheets:** load with `header=1` then `df.columns = df.columns.str.strip()`. Bare column names = Contractility; `.1`-suffix = O2.
- **Replicate-block detection** (used in `generate_fig3_multiline.py`): in `Fig_3e_data.xlsx`, multiple replicate wells are stacked sequentially per concentration — block boundaries are detected by `Time_h` decreasing.
- **Pandas duplicate-column suffixes** (`.1`, `.2`, ...) are NOT real values; always strip them when displaying or saving concentration values. See `MEMORY.md` "Pandas Duplicate Column Labels".
- **Symlink:** `Output/PowerPoint_Figures_Remake/sources/` is a symlink to `Output/PowerPoint_Figures/`. Both paths point to the same files. `git check-ignore` errors with "beyond a symbolic link" if you query through the symlink — stage from the real `Output/PowerPoint_Figures/Fig_N/` paths.
- **Render-at-scale + LANCZOS downsample:** generators render at `SCALE=4` then PIL downsample to the target pixel count. PNG metadata is stamped at `DPI=600` so `python-pptx` reads native size correctly.
- **3D label rotation:** `ax.set_xlabel/ax.set_ylabel` auto-rotate to follow projected axis direction. `ax.text2D` does NOT — only use it for the Z label (which `set_zlabel` line-wraps on narrow columns) and position it manually.

---

## 10. Recent Commits (this session, in order)

```
b519ba1  Fig 3j/k: bump top margin so Y label clears the figure top
5222a2b  Fig 3j/k: rename axes, 10-h ticks, j legend bottom-right
3297dcd  Fig 3b/d/f: lower O2 label so it sits on the Z-axis midpoint
948b8c5  Fig 3j/k: enlarge plot area to 1.89x1.28" + thinner lines
34265c0  Fig 3b/d/f: shrink to 1.70x1.80" so inner 3D box is ~0.97x0.96"
3fdaf46  Fig 3: bigger b/d/f surfaces (3.77x3.82") + plasma colormap for j/k   [reverted in 34265c0]
3103bee  Fig 3d: add Nifedipine surface (Eq10 modified_hill_simple)
43997cc  Fig 3b/f: axis-aligned labels close to edges via set_xlabel/ylabel
2e0dc3c  Fig 3b/f: text2D labels fully separated from 3D surface axes        [superseded by 43997cc]
cbbc8a1  Fig 3: fix surface label rotation + multi-line palette
```

`git log --oneline` for the full history.
