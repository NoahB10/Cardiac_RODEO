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
