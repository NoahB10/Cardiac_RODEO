# Font Size Audit — Prism Panels in Remake PPTX

Audited: 2026-04-27. Single source of truth for the tick / axis-label /
title / legend / inset-annotation point sizes used by every Prism panel
that ends up in `Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`.

Use this when harmonising sizes across panels in the same figure: every
generator listed here has its size knobs as named module-level constants
near the top of the file, so changes are localised.

---

## Figure 2 — slide 2  (consistent: 9 pt ticks / 13 pt axes)

| Panel | Tick labels | Axis labels | Other text |
|-------|------------|-------------|------------|
| 2a Epirubicin O₂ multi-line | 9 pt | 13 pt | — |
| 2b Epirubicin TC50 sigmoid  | 9 pt | 13 pt | "TC50 = X mM" annotation: 8 pt |
| 2c Epirubicin O₂ heatmap    | 9 pt | 13 pt | — |
| 2d Mexiletine Contractility multi-line | 9 pt | 13 pt | — |
| 2e Mexiletine waveforms     | 9 pt | 13 pt | trace labels ("X mM, Y bpm"): 7 pt |
| 2f Mexiletine Contractility heatmap | 9 pt | 13 pt | — |

**Status:** all axis-label sizes uniform. Inset annotations at 7 / 8 pt are
intentionally smaller than the axis labels.

---

## Figure 3 — slide 3  (four different tick/axis scales across panels)

| Panel | Tick | Axis | Title / Legend / Value |
|-------|------|------|------------------------|
| 3a, 3c, 3e heatmaps (Dactin / Nifed / Mexil) | 7 pt | 7 pt | — |
| 3b, 3d, 3f 3D surfaces                       | (ticks hidden) | 10 pt (X/Y/Z all) | — |
| 3g R² bar                                    | 7 pt | 9 pt | value labels: 6 pt |
| 3i LOOCV Accuracy-vs-AUC scatter             | 7 pt | 9 pt | sub-panel titles: 9 pt bold |
| 3j, 3k Vandetanib / Sotalol multi-line       | 8 pt | 11 pt | legend: 7 pt |

**Mismatches in Figure 3:**
- Row 1 heatmaps use 7 / 7 pt; row 1 surfaces use 10 pt for every label.
- Row 2 (g + i) uses 7 pt ticks + 9 pt axes (heatmap-like).
- Row 3 (j + k) jumps to 8 pt ticks + 11 pt axes — visually larger than
  every panel above it.

**To unify:** decide on a single tick / axis-label pair for Figure 3 and
apply it to all 10 panels. The size constants live in:

```
generate_heatmaps.py            AXIS_LABEL_PT_SMALL=7,  TICK_LABEL_PT_SMALL=7
generate_fig3_surfaces.py       LABEL_PT=10
generate_r2_bar.py              TICK_FONT_PT=7,  AXIS_LABEL_PT=9
generate_loocv_scatter.py       TICK_FONT_PT=7,  AXIS_LABEL_PT=9, TITLE_FONT_PT=9
generate_fig3_multiline.py      TICK_FONT_PT=8,  AXIS_LABEL_PT=11, LEGEND_FONT_PT=7
```

---

## Figures 6, 7, 8 — slides 6/7/8  (consistent: 9 pt ticks / 13 pt axes)

| Panel | Tick | Axis | Other text |
|-------|------|------|------------|
| a ROC curve            | 9 pt | 13 pt | "AUC = …" annotation: 9 pt |
| b Confusion matrix     | 9 pt | 13 pt | cell count digits: 14 pt (intentional, large by design) |
| c 4-metric bar         | 9 pt | 13 pt | value labels above bars: 7 pt |
| d Threshold dot plot   | 9 pt | 13 pt | 25 drug labels: 5 pt (small to fit); value text: 7 pt |
| e SHAP beeswarm        | 9 pt | 13 pt | legend: 8 pt |
| f ROC comparison (Fig 6/7 only)       | 9 pt | 13 pt | legend: 8 pt |
| g Perf-compare bars   (Fig 6/7 only)  | 9 pt | 13 pt | value labels: 7 pt; legend: 7 pt |

**Status:** axis sizing uniform. Smaller inset values (5 / 7 / 8 / 14 pt) are
panel-specific by design, not mismatches.

---

## Source of truth — constants per file

```
prism_style.apply_prism_style    default tick_label_size_pt=9, ylabel_size_pt=13

generate_fig2_panels.py          tick=9, ylabel=13, xlabel=13
generate_heatmaps.py             AXIS_LABEL_PT_LARGE=13, TICK_LABEL_PT_LARGE=9   (Fig 2c/f)
                                 AXIS_LABEL_PT_SMALL=7,  TICK_LABEL_PT_SMALL=7   (Fig 3a/c/e)
generate_fig3_surfaces.py        LABEL_PT=10  (used for set_xlabel/ylabel and ax.text2D Z label)
generate_fig3_multiline.py       TICK_FONT_PT=8, AXIS_LABEL_PT=11, LEGEND_FONT_PT=7
generate_r2_bar.py               TICK_FONT_PT=7, AXIS_LABEL_PT=9, VALUE_LABEL_PT=6
generate_loocv_scatter.py        TICK_FONT_PT=7, AXIS_LABEL_PT=9, TITLE_FONT_PT=9
generate_roc_curves.py           TICK_FONT_PT=9, AXIS_LABEL_PT=13, ANNOTATION_PT=9
generate_confusion_matrices.py   TICK_FONT_PT=9, AXIS_LABEL_PT=13, CELL_FONT_PT=14
generate_bar_plots.py            tick=9, ylabel=13, VALUE_LABEL_PT=7, VALUE_LABEL_PT_H=7
generate_dot_plots.py            tick=9, ylabel=13, xlabel=13, drug_label_size_pt=5, value=7
generate_shap_aligned_pairs.py   TICK_FONT_PT=9, AXIS_LABEL_PT=13, LEGEND_FONT_PT=8
generate_roc_comparison.py       TICK_FONT_PT=9, AXIS_LABEL_PT=13, LEGEND_FONT_PT=8
```

---

## Decisions parked here for later

- [ ] Pick unified tick / axis-label sizes for Figure 3 (10 panels). Candidates:
  - **7 / 9 pt** — matches the small heatmaps and the row-2 g/i panels (most panels would change least).
  - **9 / 13 pt** — matches Fig 2 and Fig 6/7/8 (all multi-line, surface, bar, scatter panels would grow).
  - **8 / 11 pt** — matches current j/k multi-line (compromise).
