# Figure Change Log

This document tracks all changes to figures, their data sources, and generating scripts.

## Last Updated: 2026-02-04

---

## Figure Registry Summary

All figures are tracked in `figure_registry.csv` with the following fields:
- **Figure_ID**: Figure number (1, 2, 3, etc.) or supplement ID (S1, S2, etc.)
- **Letter**: Panel letter (a, b, c, etc.)
- **PNG_Path**: Path to the generated figure image
- **Excel_Path**: Path to the Excel file containing source data for recreation
- **Source_Script**: The Python script that generates this figure
- **Notes**: Additional information about the figure

---

## Data Sources by Figure

### Figure 2: Robust Generation
| Panel | Data Source | Script |
|-------|-------------|--------|
| 2a (SNR Distribution) | `Output/Excel_Figures/snr_analysis.xlsx` | `generate_paper_figures.py` |
| | Additional: `Output/QC_Analysis/BucketAnalysis_QC_Range.xlsx` | |

### Figure 3: Fitting Kinetics
| Panel | Data Source | Script |
|-------|-------------|--------|
| 3a (O2 Heatmap) | `Cleaned_Data/Heatmaps/Vandetanib (G11)/O2_mean.csv` | `generate_paper_figures.py` |
| 3b (Contractility Heatmap) | `Cleaned_Data/Heatmaps/Vandetanib (G11)/Amp_std.csv` | `generate_paper_figures.py` |
| 3d (R² Comparison) | `Output/Excel_Figures/r2_equation_comparison.xlsx` | `generate_paper_figures.py` |
| 3e (Accuracy vs AUC) | `Output/Performance_Metrics/loocv_results.csv` | `generate_paper_figures.py` |

### Figure 4 & 5: 3D Surface Grids
| Panel | Data Source | Script |
|-------|-------------|--------|
| 4 (O2 Surfaces) | `Output/3D_Plots/O2/*.png` | `generate_paper_figures.py` |
| 5 (Contractility Surfaces) | `Output/3D_Plots/Contractility/*.png` | `generate_paper_figures.py` |

### Figure 6: Arrhythmia Prediction
| Panel | Data Source | Script |
|-------|-------------|--------|
| 6a (ROC) | `Output/ROC_Data/roc_curves_all_models.xlsx` (Sheet: Arrhythmia) | `generate_paper_figures.py` |
| 6b (Confusion Matrix) | `Output/Excel_Figures/confusion_matrix_organoid_arrhythmia.xlsx` | `generate_paper_figures.py` |
| 6c (Metrics Bar) | `Output/Performance_Metrics/stage2_results_5fold.csv` | `generate_paper_figures.py` |
| 6d (Threshold) | `Output/Prediction_Scatter_Data/arrhythmia_predictions.csv` | `generate_paper_figures.py` |
| 6e (Cumulative) | `Output/Cumulative_Plot_Data/arrhythmia_cumulative_predictions.csv` | `generate_paper_figures.py` |
| 6f (SHAP) | `Output/SHAP_Data/shap_arrhythmia_values.csv` | `Output/SHAP_Data/shap_aligned_pairs_all.py` |
| 6g (MoLFormer ROC) | `Output/MoLFormer_Comparison/organoid_5fold_roc.csv`, `molformer_cnn_25drugs_cv.csv`, `molformer_predictions_25.csv` | `Output/MoLFormer_Comparison/generate_comparison_figures.py` |
| 6h (MoLFormer Metrics) | `Output/MoLFormer_Comparison/comparison_metrics_all.csv` | `Output/MoLFormer_Comparison/generate_comparison_figures.py` |

### Figure 7: Heart Damage Prediction
| Panel | Data Source | Script |
|-------|-------------|--------|
| 7a (ROC) | `Output/ROC_Data/roc_curves_all_models.xlsx` (Sheet: HeartDamage) | `generate_paper_figures.py` |
| 7b (Confusion Matrix) | `Output/Excel_Figures/confusion_matrix_organoid_heart_damage.xlsx` | `generate_paper_figures.py` |
| 7c (Metrics Bar) | `Output/Performance_Metrics/stage2_results_5fold.csv` | `generate_paper_figures.py` |
| 7d (Threshold) | `Output/Prediction_Scatter_Data/heart_damage_predictions.csv` | `generate_paper_figures.py` |
| 7e (Cumulative) | `Output/Cumulative_Plot_Data/heart_damage_cumulative_predictions.csv` | `generate_paper_figures.py` |
| 7f (SHAP) | `Output/SHAP_Data/shap_heart_damage_values.csv` | `Output/SHAP_Data/shap_aligned_pairs_all.py` |
| 7g (ADMET ROC) | `Output/ADMET_Comparison/roc_curves_admet.xlsx` (DICTrank + Scaffold sheets) | `generate_paper_figures.py` |
| 7h (ADMET Metrics) | `Output/ADMET_Comparison/final_comparison_dictrank_vs_organoid.csv` | `generate_paper_figures.py` |

### Figure 8: Concern Binary Prediction
| Panel | Data Source | Script |
|-------|-------------|--------|
| 8a (ROC) | `Output/ROC_Data/roc_curves_all_models.xlsx` (Sheet: ConcernBinary) | `generate_paper_figures.py` |
| 8b (Confusion Matrix) | `Output/Excel_Figures/confusion_matrix_organoid_concern_binary.xlsx` | `generate_paper_figures.py` |
| 8c (Metrics Bar) | `Output/Performance_Metrics/stage2_results_5fold.csv` | `generate_paper_figures.py` |
| 8d (Threshold) | `Output/Prediction_Scatter_Data/concern_binary_predictions.csv` | `generate_paper_figures.py` |
| 8e (Cumulative) | `Output/Cumulative_Plot_Data/concern_binary_cumulative_predictions.csv` | `generate_paper_figures.py` |
| 8f (SHAP) | `Output/SHAP_Data/shap_concern_binary_values.csv` | `Output/SHAP_Data/shap_aligned_pairs_all.py` |

### Supplement S1: Additional Heatmaps
| Panel | Data Source | Script |
|-------|-------------|--------|
| S1a | `Cleaned_Data/Heatmaps/Vandetanib (G11)/O2_std.csv` | `generate_paper_figures.py` |
| S1b | `Cleaned_Data/Heatmaps/Vandetanib (G11)/O2_dom_freq.csv` | `generate_paper_figures.py` |
| S1c | `Cleaned_Data/Heatmaps/Vandetanib (G11)/Amp_dom_freq.csv` | `generate_paper_figures.py` |

### Supplement S3: Other Model Comparisons
| Panel | Data Source | Script |
|-------|-------------|--------|
| S3a | `Output/Performance_Metrics/loocv_results.csv` | `generate_paper_figures.py` |

### Supplement S4: LOOCV Comparison
| Panel | Data Source | Script |
|-------|-------------|--------|
| S4a (ADMET LOOCV ROC) | `Output/ADMET_Comparison/roc_curves_admet.xlsx` (LOOCV sheets) | `generate_paper_figures.py` |
| S4b (MoLFormer LOOCV) | `Output/MoLFormer_Comparison/loocv_comparison_molformer_vs_organoid.csv` | `generate_paper_figures.py` |

---

## Change History

### 2026-02-04
- **Heatmaps (3a, 3b, S1a-c)**: Removed white borders between cells (`linewidths=0`)
- **Figure 7g**: Moved legend outside plot to avoid overlap
- **Figure 7h**: Made figure wider, reformatted model names on two lines
- **All figures**: Added full source data tracking (not just plotted subsets)
- **Figure 2a**: Added bucket boundary columns (Bucket_Lower, Bucket_Upper, Bucket_Definition)
- **ROC curves (6g, 7g)**: Added TPR_Lower/TPR_Upper columns for confidence band recreation
- **Updated `figure_registry.csv`**: Now tracks correct source scripts for each figure

### Data Tracking Improvements
- Excel data files now include:
  - `Source` column with original file path
  - Full datasets (not just filtered/plotted data)
  - Metadata sheets where applicable
  - Bucket definitions for SNR analysis

---

## How to Regenerate Figures

```bash
# Regenerate all figures
python generate_paper_figures.py --all

# Regenerate specific figure
python generate_paper_figures.py --figure 3
python generate_paper_figures.py --figure 7

# Regenerate supplements only
python generate_paper_figures.py --supplements

# Skip PowerPoint update
python generate_paper_figures.py --figure 3 --no-pptx
```

---

## Verifying Data Tracking

Each figure's Excel data file contains:
1. **Data sheet(s)**: The actual data used in the plot
2. **Source column**: Path to the original data file
3. **Metadata sheet** (where applicable): Additional context

To verify a figure can be recreated:
1. Open the `*_data.xlsx` file for that figure
2. Check the `Source` column for original data path
3. Confirm data matches the original source file

---

## 2026-04-26 — Prism re-render of Fig 6 / 7 / 8

Added a parallel Prism-styled rendering path for the three Machine Learning prediction
figures (Arrhythmia, Heart Damage, Concern). PNGs and paired data files now live in
`Output/PowerPoint_Figures_Remake/sources/Fig_{N}/Fig_{N}{letter}_prism.{png,xlsx}`
alongside the original Tracked content. Generators are in `Prism_Style/` and write
directly to the Remake sources tree.

### What changed
- **Plot-base alignment**: each row's plot bottoms align (rather than bbox tops). T
  for each panel is computed from the row's `plot_bottom` minus the panel's `margin_b`
  minus image height. Letters per row align at a uniform `letter_top`.
- **Native-size placement**: `apply_layout_to_remake.py` writes pictures at their
  native PNG dimensions (no width/height override) so PPT does zero scaling — fonts
  stay sharp.
- **Slot remap on slides 6/7/8**:
  - `e` slot now hosts SHAP (was: cumulative features in old Tracked layout)
  - `f` slot = ROC compare (square plot, ~1.85" wide)
  - `g` slot = perf-compare bars (wide plot, varies by model count)
  - `h` slot REMOVED
- **Panel sizes** (locked, per-letter):

  | Letter | Plot area | Image |
  |---|---|---|
  | a | 3.6 × 3.6 cm | 2.14 × 2.02" |
  | b | 3.6 × 3.6 cm | 2.02 × 1.97" |
  | c | 1.526 × 1.422" | 2.50 × 2.11" |
  | d | 0.90" × 4.3 cm | 1.70 × 2.22" |
  | e | 3.5" × 4.3 cm | 4.90 × 2.14" |
  | f | 1.85 × 3.6 cm | 2.57 × 2.02" |
  | g | 8 × 3.6 cm (3-mod) / 9 × 3.6 cm (5-mod) | 3.92 × 2.57" / 4.31 × 2.57" |

- **Uniform fonts** across all Prism panels: tick 9 pt, axis label 13 pt, value/annotation 7 pt.
- **Bootstrap-band methodology** for ROC uncertainty: n=300, seed=42 (matches
  `ADMET_Comparison/Scripts/full_analysis.py:bootstrap_roc_stats`), cached per-model
  to `Prism_Style/bands_cache/Fig_{N}{letter}_{model}.csv` for deterministic re-runs.
  Replaces the binomial-SE shortcut that `generate_paper_figures.py:2882` had been
  using for 7g.
- **Outside legends** (f and g panels) split into separate `Fig_{N}{letter}_prism_legend.png`
  files. Stashed in the off-slide grey area at L=8.0" so the user drags them onto the
  panel after generation.
- **Tick labels** 0.00 → "0", 1.00 → "1" on ROC axes via `clean_decimal_formatter`.

### Data files
Each Prism panel now has a paired `Fig_{N}{letter}_prism_data.xlsx` with sheets:
- **Plotted**: the actual numeric data drawn on the panel (not derived stats)
- **Metadata**: source script + source data file paths, methodology, bootstrap params
- Additional sheets vary by panel — e.g. `Top5_Features` and `RawSHAP_AllFeatures`
  for SHAP, one sheet per model for the ROC comparison panel, etc.

### Slide map (Remake PPTX)
- Slide 6 = Figure 6 (Arrhythmia)
- Slide 7 = Figure 7 (Heart Damage)
- Slide 8 = Figure 8 (Concern)
- Earlier duplicate "Figure 6 WIP" slide deleted.

### Files
- Generators: `Prism_Style/generate_*.py`
- Layout / applier: `Prism_Style/_layout.py`, `Prism_Style/apply_layout_to_remake.py`
- Path helper: `Prism_Style/_paths.py`
- Bootstrap module: `Prism_Style/_roc_bootstrap.py`
- Legend export: `Prism_Style/_legend_export.py`
- Cache: `Prism_Style/bands_cache/`
- Outputs: `Output/PowerPoint_Figures_Remake/sources/Fig_{6,7,8}/Fig_*_prism.{png,xlsx}`
