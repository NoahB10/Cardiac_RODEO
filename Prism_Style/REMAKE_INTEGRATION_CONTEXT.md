# Remake PPTX — Master Integration Context

**Date written:** 2026-04-27  
**PPTX target:** `Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`  
**Python interpreter:** `/Users/noahb/miniconda3/bin/python`  
**Run all commands from project root:** `/Users/noahb/Documents/HebrewU Bioengineering/Cardiac_RODEO`

Read this end-to-end before touching anything. It is the single source of truth for the current state of all four operation plans and how they feed into the Remake PPTX.

---

## Quick-start (full rebuild)

```bash
cd "/Users/noahb/Documents/HebrewU Bioengineering/Cardiac_RODEO"

# Operation A — Fig 2 panels
python Prism_Style/generate_heatmaps.py          # 2c, 2f
python Prism_Style/generate_fig2_panels.py       # 2a, 2b, 2d, 2e

# Operation B — Fig 3 panels
python Prism_Style/generate_heatmaps.py          # 3a, 3c, 3e  (same script as above)
python Prism_Style/generate_fig3_surfaces.py     # 3b, 3d, 3f
python Prism_Style/generate_fig3_multiline.py    # 3j, 3k
python Prism_Style/generate_r2_bar.py            # 3g
python Prism_Style/generate_loocv_scatter.py     # 3i

# Operation C — Fig 6, 7, 8 panels (slides 7-9)
python Prism_Style/generate_roc_curves.py
python Prism_Style/generate_confusion_matrices.py
python Prism_Style/generate_bar_plots.py
python Prism_Style/generate_dot_plots.py
python Prism_Style/generate_roc_comparison.py
python Prism_Style/generate_shap_aligned_pairs.py

# Operation D — Integrate all into PPTX
python Prism_Style/apply_layout_to_remake.py
```

Any single generator can be re-run in isolation; the integration script is always safe to re-run (idempotent for its tracked panels).

---

## Slide map

| Slide (1-based) | Figure | Integration path |
|---|---|---|
| 2 | Figure 2 | INPLACE_PANELS swap (no group rebuild) |
| 3 | Figure 3 | INPLACE_PANELS swap + RESIZE_TO_NATIVE for larger panels |
| 7 | Figure 6 (Arrhythmia) | loose-rebuild (update_slide_loose) |
| 8 | Figure 7 (HeartDamage) | loose-rebuild |
| 9 | Figure 8 (ConcernBinary) | loose-rebuild |

Slides 4–6 are not managed by these scripts.

---

## Output path convention

All PNGs and their paired data XLSX go to:
```
Output/PowerPoint_Figures_Remake/sources/Fig_N/Fig_N{letter}_prism.png
Output/PowerPoint_Figures_Remake/sources/Fig_N/Fig_N{letter}_prism_data.xlsx
```

`sources/Fig_2` is a **real directory**.  
`sources/Fig_3` is a **symlink → ../../PowerPoint_Figures/Fig_3`.  
`sources/Fig_6`, `Fig_7`, `Fig_8` are **real directories**.

Stage git changes through the canonical (non-symlink) path:
```
Output/PowerPoint_Figures/Fig_3/<filename>   ← always use this for git add
```

---

## Operation A — Figure 2 panels (slide 2)

### Panel inventory

| Letter | Size (in) | Generator | Description |
|--------|-----------|-----------|-------------|
| 2a | 2.31 × 1.82 | `generate_fig2_panels.py` | Epirubicin O₂ multi-line (8 doses, 0–96 h) |
| 2b | 2.33 × 1.82 | `generate_fig2_panels.py` | Epirubicin TC50 sigmoid (Hill 4PL, log-x) |
| 2c | 2.60 × 1.78 | `generate_heatmaps.py` | Epirubicin O₂ heatmap — **see heatmap spec below** |
| 2d | 2.25 × 1.74 | `generate_fig2_panels.py` | Mexiletine Contractility multi-line (7 doses) |
| 2e | 2.06 × 1.76 | `generate_fig2_panels.py` | Mexiletine stacked waveforms (Low/Med/High @ 48 h) |
| 2f | 2.60 × 1.74 | `generate_heatmaps.py` | Mexiletine Contractility heatmap — **see heatmap spec below** |

### Fig 2 heatmap specs (2c, 2f)

Both rendered by `generate_heatmaps.py`. Key parameters:

```
fig_size : (2.60, 1.78) for 2c  /  (2.60, 1.74) for 2f
margins  : left=0.62  right=0.06  top=0.05  bottom=0.50
colormap : blue(#123BFF) → white → red(#FF2908)
AXIS_LABEL_PT_LARGE = 13 pt
TICK_LABEL_PT_LARGE = 9 pt
y_tick_decimals = 2   (round dose labels to hundredths — e.g. 0.38 not 0.375)
Spines   : L-shape (top+right hidden), SPINE_LW_PT=1.0
Axisless variant saved to: Output/PowerPoint_Figures/Fig_2/Axisless/Fig_2c_prism_axisless.png
```

Fig 2c drop: exclude well `"0.38.1"` (Epirubicin).  
Fig 2f drops: indices {4,5,6,7,14,15,17,21,22,24,26} + cols {"20","2.5.1","2.5"}.

### Fig 2a/b/d/e style

```
Helvetica, L-spines, axis labels 13 pt, ticks 9 pt, 600 dpi, transparent.
Color palettes:
  2a: 8-color sequential dark-blue→yellow (PALETTE_8)
  2b: blue #6C92ED points, black sigmoid, red #D6332B TC50, grey-dash 50% ref
  2d: plasma-7 (PALETTE_PLASMA_7), high→low dose, dark-blue→yellow
  2e: plasma 3-tone — Low=#fdb42f, Med=#cc4778, High=#9c179e
Y-axis:
  2a: ylim 0–75, yticks every 10
  2b: ylim -5–105, yticks every 10
  2d: ylim 2–12, yticks every 2
  2e: no y-ticks (stacked waveform panels with text labels)
```

### INPLACE_PANELS entries (slide 2)

```python
(2, "a"): (0.13, 4.92, "Fig_2a_prism.png"),
(2, "b"): (2.28, 4.88, "Fig_2b_prism.png"),
(2, "c"): (4.50, 4.90, "Fig_2c_prism.png"),
(2, "d"): (0.16, 6.72, "Fig_2d_prism.png"),
(2, "e"): (2.51, 6.68, "Fig_2e_prism.png"),
(2, "f"): (4.51, 6.69, "Fig_2f_prism.png"),
```

Frames are **not** in RESIZE_TO_NATIVE — they are fixed at the sizes above.

---

## Operation B — Figure 3 panels (slide 3)

### Panel inventory

| Letter | Size (in) | Generator | Resize? | Description |
|--------|-----------|-----------|---------|-------------|
| 3a | 1.30 × 1.354 | `generate_heatmaps.py` | ✅ RESIZE | Dactinomycin O₂ heatmap |
| 3b | 1.70 × 1.80 | `generate_fig3_surfaces.py` | ✅ RESIZE | Dactinomycin O₂ surface (Eq3 gaussian_hill_hybrid) |
| 3c | 1.30 × 1.354 | `generate_heatmaps.py` | ✅ RESIZE | Nifedipine O₂ heatmap |
| 3d | 1.70 × 1.80 | `generate_fig3_surfaces.py` | ✅ RESIZE | Nifedipine O₂ surface (Eq10 modified_hill_simple) |
| 3e | 1.30 × 1.354 | `generate_heatmaps.py` | ✅ RESIZE | Mexiletine O₂ heatmap |
| 3f | 1.70 × 1.80 | `generate_fig3_surfaces.py` | ✅ RESIZE | Mexiletine O₂ surface (Eq7 biphasic_response) |
| 3g | 2.10 × 1.46 | `generate_r2_bar.py` | — | R² bar (12 PK-PD equations) |
| 3i | 3.88 × 1.49 | `generate_loocv_scatter.py` | — | 3-panel LOOCV Accuracy vs AUC ROC |
| 3j | 2.54 × 2.13 | `generate_fig3_multiline.py` | ✅ RESIZE | Vandetanib O₂ multi-line dose-response |
| 3k | 2.54 × 2.13 | `generate_fig3_multiline.py` | ✅ RESIZE | Sotalol Contractility multi-line dose-response |

Panels **h** (NN diagram) is a manually placed external asset — do not touch.

### Fig 3 heatmap specs (3a, 3c, 3e) — **updated in latest session**

```
fig_size   : (1.30, 3.44/2.54) = 1.30" × 1.354" (~3.30 × 3.44 cm)
plot area  : 0.709" × 0.709"  (1.8 cm × 1.8 cm square heatmap)
margins    : left=0.40  right=0.19  top=0.15  bottom=0.495
colormap   : blue(#123BFF) → white → red(#FF2908)
AXIS_LABEL_PT_SMALL = 7 pt  (both x and y axes — must match)
TICK_LABEL_PT_SMALL = 7 pt
MAX_Y_TICK_LABELS_SMALL = 4  (avoids crowding after rounding)
y_tick_decimals = 2  (round dose labels to hundredths)
no_spines = True  (all 4 spines hidden; tick marks hidden; labels visible)
y_axis_label : "<DrugName> Dose"  single line, rotated 90°, 7 pt
x_axis_label : "Time from Exposure (h)"  placed via fig.text(x_axis_center_frac, y_frac)
               anchored just below tick numbers, centered on the plot axis
LOWESS w=16 per well, baseline compression for O₂
RESIZE_TO_NATIVE = True (apply_layout resizes PPTX frame to native PNG size)
```

Drug-specific data:
- **3a Dactinomycin**: `Cleaned_Data/Heatmaps/Dactinomycin/O2_mean_sorted.csv`; remove_rows={1,8,12,16,20,24,27}
- **3c Nifedipine**: `Cleaned_Data/Heatmaps/Nifedipine/O2_mean_sorted.csv`; remove_rows={5,6}
- **3e Mexiletine**: `Cleaned_Data/Heatmaps/Mexiletine/O2_mean_sorted.csv`; remove_rows={2,3,9,13,20}

### Fig 3 surface specs (3b, 3d, 3f)

```
fig_size   : 1.70" × 1.80"
inner 3D box ≈ 0.97" × 0.96" (axes inset rect [0.20, 0.22, 0.68, 0.70])
View       : elev=25, azim=-158
X label    : "Time (h)" via ax.set_xlabel(labelpad=6)
Y label    : "Dose Ratio" via ax.set_ylabel(labelpad=6)
Z label    : "O₂ (%)" via ax.text2D(-0.08, 0.47, ..., rotation=90)
             (text2D avoids line-wrap that set_zlabel produces on narrow columns)
LABEL_PT   : 10
Wireframe back walls, transparent faces, black edges; main axis lines hidden
RESIZE_TO_NATIVE = True
```

### Fig 3 multi-line specs (3j, 3k)

```
fig_size   : 2.54" × 2.13"
plot area  : 1.89" × 1.28"  (4.8 × 3.26 cm per user spec)
MARGIN_T   : 0.30"  (bumped so "Normalized Contractility" Y label clears top)
Colors     : plasma-3 — high dose = dark purple, mid = magenta, low = yellow
Data lines : solid, linewidth=0.22 pt, alpha=0.85
Model fit  : dashed (4,3), linewidth=0.55 pt
X axis     : ticks every 10 h, range 0–100, label "Time from exposure (h)"
j (Vandetanib O₂): ylim=(0.5,4.0), yticks=[1,2,3,4], legend lower-right
k (Sotalol Contr): ylim=(0.4,1.05), yticks=[0.4,0.6,0.8,1.0], legend lower-left
Source data: Output/PowerPoint_Figures/Fig_3/Fig_3e_data.xlsx (pre-smoothed t_fine/v_norm)
RESIZE_TO_NATIVE = True
```

### Fig 3g (R² bar) specs

```
fig_size   : 2.10" × 1.46"
PLOT_W=0.90, PLOT_H=1.00 (matches SUB_PLOT in 3i for aligned plot bottoms)
MARGIN_L=1.00 (12 equation names at 7 pt), MARGIN_R=0.20, MARGIN_T=0.04
Bars       : edgecolor="none" (flat, no black border)
Colors     : rank-based rainbow sorted by O₂ R² desc (top=red #d62728)
X label    : "R²" only
Value labels: positive bars → right of bar tip; negative bars → right of zero line
Source     : Output/PowerPoint_Figures/Fig_3/Fig_3c_data.xlsx → R2_Data sheet
```

### Fig 3i (LOOCV scatter) specs

```
fig_size   : 3.88" × 1.49"
SUB_PLOT=1.00, MARGIN_L=0.45, MARGIN_R=0.10, MARGIN_T=0.18, MARGIN_B=0.31, GAP=0.165
3 sub-panels: Arrhythmia / Heart Damage / Concern
Y label    : "AUC ROC" on leftmost sub-panel only
Titles     : 9 pt bold, ax.text(0.5, 1.04, ...) at 4% above axes top
Markers    : filled circles, s=22*SCALE*SCALE, edge 0.4*SCALE black
Colors     : spectral palette keyed on canonical equation names (EQ_COLORS)
Source     : Output/PowerPoint_Figures/Fig_3/Fig_3d_data.xlsx → LOOCV_Strip_Data sheet
```

### INPLACE_PANELS entries (slide 3)

```python
(3, "a"): (0.04, 0.93, "Fig_3a_prism.png"),
(3, "c"): (2.34, 0.94, "Fig_3c_prism.png"),
(3, "e"): (4.65, 0.94, "Fig_3e_prism.png"),
(3, "b"): (1.25, 0.79, "Fig_3b_prism.png"),
(3, "d"): (3.56, 0.79, "Fig_3d_prism.png"),
(3, "f"): (5.85, 0.79, "Fig_3f_prism.png"),
(3, "g"): (0.11, 2.13, "Fig_3g_prism.png"),   # R² bar — Group 82
(3, "i"): (3.35, 2.10, "Fig_3i_prism.png"),   # LOOCV — Group 70
(3, "j"): (0.10, 3.88, "Fig_3j_prism.png"),
(3, "k"): (2.74, 3.87, "Fig_3k_prism.png"),

RESIZE_TO_NATIVE = {
    (3, "a"), (3, "c"), (3, "e"),   # heatmaps at 1.30x1.354"
    (3, "b"), (3, "d"), (3, "f"),   # surfaces at 1.70x1.80"
    (3, "j"), (3, "k"),             # multi-line at 2.54x2.13"
}
# 3g and 3i are NOT in RESIZE_TO_NATIVE — they match their PPTX box sizes exactly
```

---

## Operation C — Figures 6, 7, 8 (slides 7, 8, 9)

These use the **loose-rebuild** path in `apply_layout_to_remake.py` — `update_slide_loose()` wipes all images and panel-letter textboxes on the slide then re-adds everything from `CONTENT[fig_num]`.

### Panel content map (from `_layout.py → CONTENT`)

```python
CONTENT = {
    6: {
        "Panel_6a": "Fig_6a_prism.png",   # ROC curve
        "Panel_6b": "Fig_6b_prism.png",   # Confusion matrix
        "Panel_6c": "Fig_6c_prism.png",   # 4-metric bar
        "Panel_6d": "Fig_6d_prism.png",   # threshold dot plot
        "Panel_6e": "Fig_6e_prism.png",   # SHAP
        "Panel_6f": "Fig_6f_prism.png",   # ROC compare
        "Panel_6g": "Fig_6g_prism.png",   # perf compare bars
    },
    7: { ... same pattern with Fig_7{letter}_prism.png ... },
    8: { ... same pattern, only panels a–e (no f/g) ... },
}
```

### Generators for Fig 6/7/8

| Script | Panels produced |
|--------|----------------|
| `generate_roc_curves.py` | Fig_Na_prism.png (ROC curve, N=6,7,8) |
| `generate_confusion_matrices.py` | Fig_Nb_prism.png (CM) |
| `generate_bar_plots.py` | Fig_Nc_prism.png (4-metric bar) |
| `generate_dot_plots.py` | Fig_Nd_prism.png (threshold dot) |
| `generate_shap_aligned_pairs.py` | Fig_Ne_prism.png (SHAP) |
| `generate_roc_comparison.py` | Fig_Nf_prism.png + legend, Fig_Ng_prism.png + legend |

### Row layout (from `_layout.py → ROW_LAYOUT`)

```
Row 1 (a, b, c): plot_bottom=2.27", letter_top=0.62"
Row 2 (d, e):    plot_bottom=4.78", letter_top=2.82"
Row 3 (f, g):    plot_bottom=6.95", letter_top=5.21"
```

Plot bases within each row are aligned. The `MARGIN_B` dict in `_layout.py` pins each panel's bottom margin so the script can compute `top = plot_bottom + MARGIN_B[letter] - image_h`.

### Style conventions (Figs 6/7/8)

```
ROC curve (a): Organoid = green #2ca02c, always first in legend
Confusion matrix (b): Blues cmap, 2×2, "Neg"/"Pos" labels
4-metric bar (c): Accuracy/Sensitivity/Specificity/F1 bars, 9 pt ticks
Threshold dot (d): dot plot at optimal threshold
SHAP (e): beeswarm, top features
ROC compare (f): multiple method comparison, green=Organoid first
Perf compare bars (g): Acc/F1/MCC across methods
Legend files: Fig_Nf_prism_legend.png, Fig_Ng_prism_legend.png — stashed
              off-slide at L=8.0 for manual drag-in.
```

---

## Operation D — Integration (`apply_layout_to_remake.py`)

Run this **after** all generators. It is always safe to re-run.

```bash
python Prism_Style/apply_layout_to_remake.py
```

### What it does

1. **Finds figure slides** by reading the first text shape on each slide — matches `"Figure 6:"`, `"Figure 7:"`, `"Figure 8:"`. Removes duplicate slides (keeps last occurrence).
2. **Loose-rebuild** (slides 7/8/9): wipes all group shapes + pictures + panel-letter textboxes, then re-adds images at positions from `ROW_LAYOUT + PANEL_ROW`, with plot-base alignment. Also stashes legends off-slide at L=8.0".
3. **In-place swap** (slides 2/3): walks all picture shapes (including inside groups) via `_walk_pictures()`, finds each picture whose `(left, top)` matches an `INPLACE_PANELS` entry within ±0.05", swaps the image bytes via `_swap_picture_source()`. If the entry is in `RESIZE_TO_NATIVE`, also resizes the picture box to match the PNG's native dimensions.

### Recovery if PPTX becomes corrupted

```bash
git show HEAD:"Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx" > /tmp/clean.pptx
cp /tmp/clean.pptx "Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx"
python Prism_Style/apply_layout_to_remake.py
```

---

## Key file locations

```
Prism_Style/
├── _layout.py                  # INPLACE_PANELS, RESIZE_TO_NATIVE, ROW_LAYOUT, CONTENT
├── _paths.py                   # panel_dir(N), panel_png(N,l), panel_data(N,l)
├── _equations.py               # canonical equation order + turbo color map
├── _roc_bootstrap.py           # bootstrap CI for ROC bands
├── prism_style.py              # apply_prism_style(), render_at_scale(), helvetica()
├── apply_layout_to_remake.py   # master integration script
├── generate_heatmaps.py        # Fig 2c, 2f, 3a, 3c, 3e
├── generate_fig2_panels.py     # Fig 2a, 2b, 2d, 2e
├── generate_fig3_surfaces.py   # Fig 3b, 3d, 3f
├── generate_fig3_multiline.py  # Fig 3j, 3k
├── generate_r2_bar.py          # Fig 3g
├── generate_loocv_scatter.py   # Fig 3i
├── generate_roc_curves.py      # Fig Na (N=6,7,8)
├── generate_confusion_matrices.py   # Fig Nb
├── generate_bar_plots.py       # Fig Nc
├── generate_dot_plots.py       # Fig Nd
├── generate_shap_aligned_pairs.py   # Fig Ne
└── generate_roc_comparison.py  # Fig Nf, Ng + legends
```

---

## Critical gotchas

**Python env:** always `/Users/noahb/miniconda3/bin/python` — system python lacks pptx, pandas, statsmodels.

**Symlink vs. real dir:** `sources/Fig_3` → `../../PowerPoint_Figures/Fig_3`. Both paths resolve the same file. Always `git add` from `Output/PowerPoint_Figures/Fig_3/<file>`, not through the symlink.

**Frame position tolerance:** the `(left, top)` in `INPLACE_PANELS` must match the actual PPTX frame position within ±0.05". If the user moves a frame in PowerPoint, update the tuple in `_layout.py`.

**Pandas duplicate column suffixes:** `.1`, `.2`, `.3` on column headers are pandas dedup artefacts, NOT separate concentrations. Strip them before display. `generate_heatmaps.py` does this automatically via `_build_conc_map()`.

**Render-at-scale:** all generators render at `SCALE=4` then PIL-LANCZOS downsample to `target × 600 DPI` pixels. PNG DPI metadata is stamped at 600 so python-pptx reads native size correctly.

**3D Z-label:** use `ax.text2D()` not `ax.set_zlabel()` — the latter line-wraps on narrow columns and `bbox_inches='tight'` doesn't capture it reliably.

**Fig 3 heatmaps — no_spines=True:** spines (frame lines) and tick marks are hidden; only the tick number labels and axis title text are shown. The x-label is placed with `fig.text(x_frac, y_frac)` where `x_frac` = plot axis center / figure width, so it centers under the heatmap.

**Fig 3g/i not RESIZE_TO_NATIVE:** these panels were sized to exactly match their PPTX group boxes (2.10×1.46 and 3.88×1.49). Do not add them to RESIZE_TO_NATIVE.

**Fig 6/7/8 legends:** `Fig_Nf_prism_legend.png` and `Fig_Ng_prism_legend.png` are placed off-slide at L=8.0" by the loose-rebuild. The user must drag them onto the panel manually after each run.
