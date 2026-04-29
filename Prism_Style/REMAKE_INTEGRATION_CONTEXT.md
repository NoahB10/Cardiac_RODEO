# Remake PPTX — Master Integration Context

**Last updated:** 2026-04-27 (post font swap + cleanup + endpoint fixes)
**PPTX target:** `Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`
**Python interpreter:** `/Users/noahb/miniconda3/bin/python`
**Run all commands from project root:** `/Users/noahb/Documents/HebrewU Bioengineering/Cardiac_RODEO`

This is the single source of truth for the current state of the Remake PPTX
and the toolchain that generates it. For task-oriented edit recipes, see
`Prism_Style/EDITING_GUIDE.md`. For the per-panel font size matrix, see
`Prism_Style/FONT_AUDIT.md`.

---

## Quick rebuild (full)

```bash
cd "/Users/noahb/Documents/HebrewU Bioengineering/Cardiac_RODEO"
PY=/Users/noahb/miniconda3/bin/python

# Operation A — Fig 2 panels
$PY Prism_Style/generate_heatmaps.py          # 2c, 2f
$PY Prism_Style/generate_fig2_panels.py       # 2a, 2b, 2d, 2e
# (fig2_panels writes to Output/PowerPoint_Figures/Fig_2/; copy to sources)
for L in a b d e; do
  cp "Output/PowerPoint_Figures/Fig_2/Fig_2${L}_prism.png" \
     "Output/PowerPoint_Figures_Remake/sources/Fig_2/Fig_2${L}_prism.png"
  cp "Output/PowerPoint_Figures/Fig_2/Fig_2${L}_prism_data.xlsx" \
     "Output/PowerPoint_Figures_Remake/sources/Fig_2/Fig_2${L}_prism_data.xlsx"
done

# Operation B — Fig 3 panels
$PY Prism_Style/generate_heatmaps.py          # also covers 3a, 3c, 3e
$PY Prism_Style/generate_fig3_surfaces.py     # 3b, 3d, 3f
$PY Prism_Style/generate_fig3_multiline.py    # 3j, 3k
$PY Prism_Style/generate_r2_bar.py            # 3g
$PY Prism_Style/generate_loocv_scatter.py     # 3i

# Operation C — Fig 6, 7, 8 panels (slides 6, 7, 8)
$PY Prism_Style/generate_roc_curves.py
$PY Prism_Style/generate_confusion_matrices.py
$PY Prism_Style/generate_bar_plots.py
$PY Prism_Style/generate_dot_plots.py
$PY Prism_Style/generate_roc_comparison.py
$PY Prism_Style/generate_shap_aligned_pairs.py

# Operation D — Stamp everything into the PPTX
$PY Prism_Style/apply_layout_to_remake.py
```

The integration script is always safe to re-run.

---

## Slide map

| Slide (1-based) | Figure | Integration path |
|---|---|---|
| 2 | Figure 2 | INPLACE_PANELS swap (no group rebuild) |
| 3 | Figure 3 | INPLACE_PANELS swap + RESIZE_TO_NATIVE for variable-size panels |
| 6 | Figure 6 (Arrhythmia) | loose-rebuild (`update_slide_loose`) |
| 7 | Figure 7 (HeartDamage) | loose-rebuild |
| 8 | Figure 8 (ConcernBinary) | loose-rebuild |

Slides 4–5 are not managed by these scripts.

---

## Output path convention

All PNGs and paired data XLSX go to:
```
Output/PowerPoint_Figures_Remake/sources/Fig_N/Fig_N{letter}_prism.png
Output/PowerPoint_Figures_Remake/sources/Fig_N/Fig_N{letter}_prism_data.xlsx
```

`sources/Fig_2`, `Fig_6`, `Fig_7`, `Fig_8` are **real directories**.
`sources/Fig_3` is a **symlink → ../../PowerPoint_Figures/Fig_3`.

Stage git changes through the canonical (non-symlink) path:
```
Output/PowerPoint_Figures/Fig_3/<filename>   ← always use this for git add
```

---

## Font convention

**Arial everywhere.** As of 2026-04-27 the entire stack uses Arial:

- `figure_config.py` registers system Arial and puts it first in the
  matplotlib sans-serif fallback list.
- `prism_style.helvetica()` / `helvetica_bold()` are **aliases** that now
  resolve to Arial via `/System/Library/Fonts/Supplemental/Arial.ttf`.
  Modern code can use the canonical `arial()` / `arial_bold()` factories.
- `apply_layout_to_remake._add_letter()` sets `run.font.name = "Arial"`.

The bundled Helvetica TTFs in `fonts/` are kept as a fallback only.

For per-panel font sizes see `FONT_AUDIT.md`.

---

## Operation A — Figure 2 panels (slide 2)

### Panel inventory

| Letter | Size (in) | Generator | Description |
|--------|-----------|-----------|-------------|
| 2a | 2.31 × 1.82 | `generate_fig2_panels.py` | Epirubicin O₂ multi-line; ylim **0–80** (post fix), yticks every 10 |
| 2b | 2.33 × 1.82 | `generate_fig2_panels.py` | Epirubicin TC50 sigmoid; xlim **0.1–10** log, ylim **0–100** (post fix) |
| 2c | 2.60 × 1.78 | `generate_heatmaps.py` | Epirubicin O₂ heatmap (drop well `0.38.1`) |
| 2d | 2.25 × 1.74 | `generate_fig2_panels.py` | Mexiletine Contractility multi-line; ylim 2–12 every 2 |
| 2e | 2.06 × 1.76 | `generate_fig2_panels.py` | Mexiletine waveforms (Low/Med/High) |
| 2f | 2.60 × 1.74 | `generate_heatmaps.py` | Mexiletine Contractility heatmap |

### Slide 2 INPLACE_PANELS

```python
(2, "a"): (0.13, 4.92, "Fig_2a_prism.png"),
(2, "b"): (2.28, 4.88, "Fig_2b_prism.png"),
(2, "c"): (4.50, 4.90, "Fig_2c_prism.png"),
(2, "d"): (0.16, 6.72, "Fig_2d_prism.png"),
(2, "e"): (2.51, 6.68, "Fig_2e_prism.png"),
(2, "f"): (4.51, 6.69, "Fig_2f_prism.png"),
```

Slide 2 is **not** in `RESIZE_TO_NATIVE` — frames are fixed at the sizes above.

### Slide 2 cleanup (one-time, already applied)

- 6 `PanelLetter_*` textboxes removed.
- 14 axis-label `Rectangle` shapes removed (the `Oxygen (% Air)`,
  `Time from Exposure (h)`, etc. overlays for the OLD panels).
- 6 inset pictures inside Groups 65 / 94 / 101 / 18 removed (kept only the
  full-size Prism panel inside each group).
- Top-half `Rectangle 20` placeholder preserved.

---

## Operation B — Figure 3 panels (slide 3)

### Panel inventory

| Letter | Size (in) | Generator | Resize? | Description |
|--------|-----------|-----------|---------|-------------|
| 3a | 1.30 × 1.354 | `generate_heatmaps.py` | ✅ | Dactinomycin O₂ heatmap |
| 3b | 1.70 × 1.80 | `generate_fig3_surfaces.py` | ✅ | Dactinomycin O₂ surface (Eq3 gaussian_hill_hybrid) |
| 3c | 1.30 × 1.354 | `generate_heatmaps.py` | ✅ | Nifedipine O₂ heatmap |
| 3d | 1.70 × 1.80 | `generate_fig3_surfaces.py` | ✅ | Nifedipine O₂ surface (Eq10 modified_hill_simple) |
| 3e | 1.30 × 1.354 | `generate_heatmaps.py` | ✅ | Mexiletine O₂ heatmap |
| 3f | 1.70 × 1.80 | `generate_fig3_surfaces.py` | ✅ | Mexiletine O₂ surface (Eq7 biphasic_response) |
| 3g | 2.10 × 1.46 | `generate_r2_bar.py` | — | R² bar; tick algo rounds **outward** + xlim snaps to first/last tick |
| 3i | 3.88 × 1.49 | `generate_loocv_scatter.py` | — | 3-panel LOOCV Accuracy vs AUC ROC |
| 3j | 2.54 × 2.13 | `generate_fig3_multiline.py` | ✅ | Vandetanib O₂ multi-line; ylim **1–4** (post fix) |
| 3k | 2.54 × 2.13 | `generate_fig3_multiline.py` | ✅ | Sotalol Contractility multi-line; ylim **0.4–1.0** (post fix) |

Panel **h** (NN diagram, Picture 6 at L=2.26 / T=2.25) is externally managed —
do not touch.

### Slide 3 INPLACE_PANELS (current — reflects user's manual moves)

```python
# Row 1 — heatmaps + surfaces (positions reflect user's PowerPoint adjustments)
(3, "a"): (-0.02, 0.93, "Fig_3a_prism.png"),
(3, "c"): (2.39,  0.94, "Fig_3c_prism.png"),
(3, "e"): (4.83,  0.93, "Fig_3e_prism.png"),
(3, "b"): (0.87,  0.65, "Fig_3b_prism.png"),
(3, "d"): (3.30,  0.66, "Fig_3d_prism.png"),
(3, "f"): (5.74,  0.63, "Fig_3f_prism.png"),
# Row 2 — R² bar + LOOCV scatter
(3, "g"): (-0.01,  2.21, "Fig_3g_prism.png"),
(3, "i"): (3.23,  2.18, "Fig_3i_prism.png"),
# Row 3 — multi-line dose responses (inside Groups 41 / 42)
(3, "j"): (0.10,  3.88, "Fig_3j_prism.png"),
(3, "k"): (2.74,  3.87, "Fig_3k_prism.png"),
```

### RESIZE_TO_NATIVE

```python
RESIZE_TO_NATIVE = {
    (3, "a"), (3, "c"), (3, "e"),   # heatmaps
    (3, "b"), (3, "d"), (3, "f"),   # surfaces
    (3, "j"), (3, "k"),             # multi-line
}
# 3g and 3i are NOT in this set — they're sized to match their PPTX boxes exactly
```

### Slide 3 cleanup (one-time, already applied)

- 11 `PanelLetter_*` textboxes removed.
- 4 inset pictures inside Groups 41 / 42 removed (kept only the new Prism
  multi-line panel).
- Legacy Groups 82 (g slot) and 70 (i slot) deleted; replaced with
  fresh free-standing pictures at the INPLACE coords.

---

## Operation C — Figures 6, 7, 8 (slides 6, 7, 8)

These use the **loose-rebuild** path: `update_slide_loose()` wipes all
groups, pictures, and panel-letter textboxes, then re-adds everything from
`CONTENT[fig_num]` using `ROW_LAYOUT + PANEL_ROW`. Title text boxes are
preserved.

### CONTENT (`_layout.py`)

```python
CONTENT = {
    6: {"Panel_6a": "Fig_6a_prism.png", ..., "Panel_6g": "Fig_6g_prism.png"},
    7: {"Panel_7a": "Fig_7a_prism.png", ..., "Panel_7g": "Fig_7g_prism.png"},
    8: {"Panel_8a": "Fig_8a_prism.png", ..., "Panel_8e": "Fig_8e_prism.png"},
}
```

### ROW_LAYOUT (`_layout.py`)

```
Row 1 (a/b/c): plot_bottom=2.27", letter_top=0.62"
Row 2 (d/e):   plot_bottom=4.78", letter_top=2.82"
Row 3 (f/g):   plot_bottom=6.95", letter_top=5.21"
```

Plot bases are aligned per row via `_compute_picture_top()`:
`top = plot_bottom + MARGIN_B[letter] - image_h`.

### Generators for Fig 6/7/8

| Script | Panels |
|--------|--------|
| `generate_roc_curves.py` | Fig_Na_prism.png |
| `generate_confusion_matrices.py` | Fig_Nb_prism.png |
| `generate_bar_plots.py` | Fig_Nc_prism.png |
| `generate_dot_plots.py` | Fig_Nd_prism.png |
| `generate_shap_aligned_pairs.py` | Fig_Ne_prism.png |
| `generate_roc_comparison.py` | Fig_Nf_prism.png + Fig_Ng_prism.png + legends |

Legend PNGs (`Fig_Nf_prism_legend.png`, `Fig_Ng_prism_legend.png`) are stashed
off-slide at `L=8.0"`. Drag onto the panel manually.

---

## Operation D — Integration script

```bash
$PY Prism_Style/apply_layout_to_remake.py
```

### What it does

1. **Find figure slides** by scanning the first text shape (`Figure 2:`,
   `Figure 3:`, `Figure 6:`, etc.). Removes duplicate slides.
2. **Loose-rebuild** slides 6/7/8: wipe all groups + pictures + panel letters,
   re-add panels from `CONTENT` at positions from `ROW_LAYOUT + PANEL_ROW`.
   Stash legends off-slide at `LEGEND_STASH_X = 8.0`.
3. **In-place swap** slides 2/3: walk all picture frames (including inside
   groups), find each match by `(left, top)` within ±0.05", swap image bytes.
   If `(slide, letter) ∈ RESIZE_TO_NATIVE`, also resize the picture box to
   match the PNG's native dimensions.
4. **Strip panel letters** (`ADD_PANEL_LETTERS = False`): sweep every managed
   slide and remove any `PanelLetter_*` / `Label_*` textboxes left over.

### Toggles in `apply_layout_to_remake.py`

```python
ADD_PANEL_LETTERS = False   # Set True to resume adding "a"/"b"/... overlays.
LETTER_FONT_PT = 12         # Panel-letter font size (Arial Bold).
LETTER_OFFSET_X_IN = -0.05  # Letter X offset from panel left.
LETTER_OFFSET_Y_IN = -0.18  # Letter Y offset from panel top.
LEGEND_STASH_X = 8.0        # Off-slide left for legend PNGs.
```

### Recovery

```bash
git show HEAD:"Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx" > /tmp/clean.pptx
cp /tmp/clean.pptx "Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx"
$PY Prism_Style/apply_layout_to_remake.py
```

---

## Key files

```
Prism_Style/
├── _layout.py                  # INPLACE_PANELS, RESIZE_TO_NATIVE, ROW_LAYOUT, CONTENT
├── _paths.py                   # panel_dir(N), panel_png(N,l), panel_data(N,l)
├── _equations.py               # canonical equation order + turbo color map
├── _roc_bootstrap.py           # bootstrap CI for ROC bands
├── _legend_export.py           # external legend PNG export helper
├── prism_style.py              # apply_prism_style(), arial(), helvetica alias
├── apply_layout_to_remake.py   # MAIN orchestrator
├── generate_heatmaps.py        # Fig 2c, 2f, 3a, 3c, 3e
├── generate_fig2_panels.py     # Fig 2a, 2b, 2d, 2e
├── generate_fig3_surfaces.py   # Fig 3b, 3d, 3f
├── generate_fig3_multiline.py  # Fig 3j, 3k
├── generate_r2_bar.py          # Fig 3g
├── generate_loocv_scatter.py   # Fig 3i
├── generate_roc_curves.py      # Fig Na (N=6,7,8)
├── generate_confusion_matrices.py
├── generate_bar_plots.py
├── generate_dot_plots.py
├── generate_shap_aligned_pairs.py
├── generate_roc_comparison.py
├── REMAKE_INTEGRATION_CONTEXT.md  # this doc
├── EDITING_GUIDE.md               # task-oriented edit recipes
├── FONT_AUDIT.md                  # per-panel font size matrix
└── SESSION_*.md                   # historical hand-off notes (archive)
```

---

## Critical gotchas

**Python env:** always `/Users/noahb/miniconda3/bin/python` — system python lacks pptx, pandas, statsmodels.

**Symlink vs. real dir:** `sources/Fig_3` → `../../PowerPoint_Figures/Fig_3`. Always `git add` from `Output/PowerPoint_Figures/Fig_3/<file>`, not through the symlink.

**Frame position tolerance:** `(left, top)` in `INPLACE_PANELS` must match the actual PPTX frame within ±0.05". If you move a frame in PowerPoint, update the tuple in `_layout.py` (see `EDITING_GUIDE.md` recipe 10).

**Pandas duplicate column suffixes:** `.1`, `.2`, `.3` on column headers are pandas dedup artefacts, NOT separate concentrations. Strip them before display. `generate_heatmaps.py` does this automatically via `_build_conc_map()`.

**Render-at-scale:** all generators render at `SCALE=4` then PIL-LANCZOS downsample to `target × 600 DPI` pixels. PNG DPI metadata is stamped at 600 so python-pptx reads native size correctly.

**3D Z-label:** use `ax.text2D()` not `ax.set_zlabel()` — the latter line-wraps on narrow columns and `bbox_inches='tight'` doesn't capture it reliably.

**Fig 3 heatmaps — no_spines=True:** spines and tick marks are hidden; only tick numbers and axis title are shown. The x-label is placed via `fig.text()` so it centres under the heatmap.

**Endpoint-tick rule:** every continuous axis must label its first and last tick. xlim/ylim should equal the outer ticks (not extend beyond). See FIX entries in `_layout.py`/generators dated 2026-04-27.

**ADD_PANEL_LETTERS flag:** currently `False`. The `_add_letter()` function is intact; flip the flag to True and re-run apply to bring letters back.
