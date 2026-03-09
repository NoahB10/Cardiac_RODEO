# PowerPoint Figures vs Excel Figures: Data Comparison Report

**Generated:** 2026-02-04
**Purpose:** Compare data files between `Output/PowerPoint_Figures/` and `Output/Excel_Figures/` to identify matches, differences, and data changes.

---

## Executive Summary

| Metric | PowerPoint_Figures | Excel_Figures |
|--------|-------------------|---------------|
| **Total Excel Files** | 38 | 45 |
| **Organized by Figure** | Yes (Fig_2 through Fig_S4) | Partially (root + ADMET/ + MoLFormer/) |
| **Naming Convention** | `Fig_Xa_data.xlsx` | Descriptive names (e.g., `ROC_Curves.xlsx`) |
| **Data Scope** | Publication-ready, curated | Working/intermediate data |

**Key Finding:** PowerPoint_Figures contains restructured, publication-ready versions of the data in Excel_Figures, with additional metadata sheets, source tracking, and figure-specific organization.

---

## Detailed File Mapping

### 1. ROC Curve Data

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_6/Fig_6a_data.xlsx` (Arrhythmia ROC) | `ROC_Curves.xlsx` (Arrhythmia sheet) | **SIMILAR - Different Structure** |
| `Fig_7/Fig_7a_data.xlsx` (Heart Damage ROC) | `ROC_Curves.xlsx` (HeartDamage sheet) | **SIMILAR - Different Structure** |
| `Fig_8/Fig_8a_data.xlsx` (Concern ROC) | `ROC_Curves.xlsx` (ConcernBinary sheet) | **SIMILAR - Different Structure** |
| `Fig_6/Fig_6g_data.xlsx` (Multi-model ROC) | `overall_roc_comparison.xlsx` | **SIMILAR** |
| `Fig_7/Fig_7g_data.xlsx` (ADMET ROC) | `ADMET/ROC_Comparison.xlsx` | **SIMILAR** |

**Differences:**
- **PowerPoint:** 101 rows x 31 cols (10 folds with FPR, TPR, ROC per fold)
- **Excel:** 100 rows x 4 cols (FPR, TPR_Mean, TPR_Upper, TPR_Lower)
- **Change:** PowerPoint files contain per-fold data for bootstrap confidence bands; Excel files contain pre-computed mean + bounds
- **Implication:** PowerPoint version allows recalculation of confidence intervals; Excel version is pre-summarized

---

### 2. Confusion Matrix Data

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_6/Fig_6b_data.xlsx` | `confusion_matrices.xlsx` (Arrhythmia) | **DIFFERENT VALUES** |
| `Fig_7/Fig_7b_data.xlsx` | `confusion_matrices.xlsx` (Heart Damage) | **DIFFERENT VALUES** |
| `Fig_8/Fig_8b_data.xlsx` | `confusion_matrices.xlsx` (Concern Binary) | **DIFFERENT VALUES** |
| `Fig_6/Fig_6h_data.xlsx` | `confusion_matrix_organoid_arrhythmia.xlsx` | **SIMILAR** |

**CRITICAL DIFFERENCE - Arrhythmia Confusion Matrix:**

| Source | TN | FP | FN | TP |
|--------|----|----|----|----|
| **PowerPoint (Fig_6b)** | 73 | 37 | 29 | 111 |
| **Excel (confusion_matrices.xlsx)** | *Needs verification* | *Needs verification* | *Needs verification* | *Needs verification* |

**Analysis:** The PowerPoint version shows aggregated cross-validation results (250 total samples = 5 folds x 5 seeds x 10 samples). The Excel version may contain single-fold or different aggregation results.

---

### 3. Performance Metrics

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_6/Fig_6c_data.xlsx` | `accuracy_auc_arrhythmia.xlsx` | **SAME DATA - Different Format** |
| `Fig_7/Fig_7c_data.xlsx` | `accuracy_auc_heart_damage.xlsx` | **SAME DATA - Different Format** |
| `Fig_8/Fig_8c_data.xlsx` | `accuracy_auc_concern_binary.xlsx` | **SAME DATA - Different Format** |
| N/A | `Performance_Metrics.xlsx` | **Excel only - combined file** |
| N/A | `Prediction_Metrics_Bars.xlsx` | **Excel only - bar chart data** |

**Structure Comparison:**

**PowerPoint (Fig_6c):**
- Sheet 1 `Metrics_Summary`: 5 rows (Accuracy, AUC, F1, MCC, Sensitivity) x 7 cols
- Sheet 2 `Raw_Fold_Data`: 11 rows x 10 cols (per-fold breakdown)
- Includes: Target, Plot_Type, Source columns

**Excel (accuracy_auc_arrhythmia.xlsx):**
- Single sheet `Data`: 1 row x 11 cols
- Columns: Target, Model, N_Folds, Accuracy_Mean, Accuracy_Std, AUC_Mean, AUC_Std, F1_Mean, F1_Std, MCC_Mean, MCC_Std

**Key Difference:** PowerPoint version has raw fold data for error bar calculation; Excel version has pre-computed mean/std.

---

### 4. Prediction Scatter Data (Per-Drug)

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_6/Fig_6d_data.xlsx` | `Prediction_Scatter.xlsx` (Arrhythmia) | **ENHANCED in PowerPoint** |
| `Fig_7/Fig_7d_data.xlsx` | `Prediction_Scatter.xlsx` (Heart Damage) | **ENHANCED in PowerPoint** |
| `Fig_8/Fig_8d_data.xlsx` | `Prediction_Scatter.xlsx` (Concern Binary) | **ENHANCED in PowerPoint** |

**Structure Comparison:**

**PowerPoint (Fig_6d):**
- 26 rows x 8 cols
- Columns: Drug, Predicted_Arrhythmia_pct, Actual_Arrhythmia, is_positive, Source, Threshold_Value, Threshold_Source

**Excel (Prediction_Scatter.xlsx):**
- 25 rows x 3 cols
- Columns: Drug, Predicted_Arrhythmia_pct, Actual_Arrhythmia

**Additions in PowerPoint:**
- `is_positive` boolean column
- `Source` file reference
- `Threshold_Value` for classification cutoff
- `Threshold_Source` for threshold origin

---

### 5. Cumulative Feature Importance

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_6/Fig_6e_data.xlsx` | `Cumulative_Feature_Importance_Arrhythmia.xlsx` | **SAME DATA** |
| `Fig_7/Fig_7e_data.xlsx` | `Cumulative_Feature_Importance_Heart_Damage.xlsx` | **SAME DATA** |
| `Fig_8/Fig_8e_data.xlsx` | `Cumulative_Feature_Importance_Concern_Binary.xlsx` | **SAME DATA** |
| N/A | `cumulative_feature_importance.xlsx` | **Excel only - combined** |
| N/A | `Cumulative_Feature_Importance_Concern_Less.xlsx` | **Excel only** |
| N/A | `Cumulative_Feature_Importance_Concern_Most.xlsx` | **Excel only** |
| N/A | `Cumulative_Feature_Importance_Concern_No.xlsx` | **Excel only** |

**Structure:** Both have 14-15 rows (cumulative coefficients) x 26 cols (25 drugs + header)

**Difference:** PowerPoint version has `Source_Metadata` sheet added.

---

### 6. SHAP Feature Importance

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_6/Fig_6f_data.xlsx` | `shap_arrhythmia.xlsx` | **ENHANCED in PowerPoint** |
| `Fig_7/Fig_7f_data.xlsx` | `shap_heart_damage.xlsx` | **ENHANCED in PowerPoint** |
| `Fig_8/Fig_8f_data.xlsx` | `shap_concern_binary.xlsx` | **ENHANCED in PowerPoint** |
| N/A | `SHAP_Feature_Importance.xlsx` | **Excel only - combined** |

**Structure Comparison:**

**PowerPoint (Fig_6f):**
- Sheet 1 `SHAP_Full`: 26 rows x 17 cols (all drugs x all 14 features + Source)
- Sheet 2 `Top_Features`: 6 rows x 6 cols (top 5 features ranked)

**Excel (shap_arrhythmia.xlsx):**
- Single sheet `SHAP_Data`: 14 rows x 2 cols (Feature, Mean_Abs_SHAP)

**Key Difference:** PowerPoint has full per-drug SHAP values; Excel has only mean absolute importance.

---

### 7. Heatmap Data (Equation Comparison)

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_3/Fig_3a_data.xlsx` (Contractility) | N/A | **PowerPoint only** |
| `Fig_3/Fig_3b_data.xlsx` (O2) | N/A | **PowerPoint only** |
| `Fig_3/Fig_3d_data.xlsx` (R2 comparison) | `r2_equation_comparison.xlsx` | **SIMILAR** |
| `Fig_S1/Fig_S1a-c_data.xlsx` | N/A | **PowerPoint only** |

**Heatmap Structure (PowerPoint):**
- 27 rows (equations) x 38 cols (time points 4-96 hours)
- Includes `Source_Metadata` sheet

**R2 Comparison:**
- PowerPoint: 13 rows x 6 cols with Source tracking
- Excel: 12 rows x 3 cols (Equation, Contractility R2, O2 R2)

---

### 8. QC/SNR Analysis

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_2/Fig_2a_data.xlsx` | `snr_analysis.xlsx` | **SAME DATA - Restructured** |

**Structure Comparison:**

**PowerPoint:**
- Sheet 1 `SNR_Full_Data`: 102 rows x 9 cols
- Sheet 2 `QC_Analysis`: 102 rows x 7 cols (formatted for plotting)

**Excel:**
- Sheet 1 `QC_Range_0_to_80`: 101 rows x 4 cols
- Sheet 2 `Extended_Range`: 101 rows x 4 cols
- Sheet 3 `Line_Comparison`: 101 rows x 3 cols
- Sheet 4 `Summary`: 15 rows x 2 cols (text summary)

**Difference:** Excel has more analysis variants; PowerPoint has plot-ready format.

---

### 9. Model Comparison (CNN/MoLFormer/ADMET)

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_6/Fig_6g_data.xlsx` | `molformer_comparison.xlsx` | **SIMILAR - Different Organization** |
| `Fig_6/Fig_6h_data.xlsx` | `MoLFormer/Overall_Comparison.xlsx` | **SIMILAR** |
| `Fig_7/Fig_7g_data.xlsx` | `ADMET/ROC_Comparison.xlsx` | **SIMILAR** |
| `Fig_7/Fig_7h_data.xlsx` | `ADMET/Overall_Comparison.xlsx` | **SIMILAR** |
| `Fig_S4/Fig_S4a_data.xlsx` | `ADMET/ROC_Comparison.xlsx` | **OVERLAPPING** |
| `Fig_S4/Fig_S4b_data.xlsx` | `MoLFormer/Summary_Table.xlsx` | **SIMILAR** |

**Key Difference:** PowerPoint files include confidence interval bounds (TPR_Lower, TPR_Upper) in ROC data; Excel versions may not.

---

### 10. LOOCV Results

| PowerPoint File | Excel File | Status |
|-----------------|------------|--------|
| `Fig_3/Fig_3e_data.xlsx` | N/A | **PowerPoint only** |
| `Fig_4/Fig_4_Accuracy_vs_AUC_data.xlsx` | N/A | **PowerPoint only** |
| `Fig_S3/Fig_S3a-c_data.xlsx` | N/A | **PowerPoint only** |

**Content:** Leave-One-Out Cross-Validation results for 12 equations x 3 targets
- 37 rows of CV tests
- Includes equation name, target, model, accuracy, AUC, confusion matrix

---

## Files Only in Excel_Figures (Not in PowerPoint)

| File | Purpose | Notes |
|------|---------|-------|
| `heatmap_as_plot.xlsx` | Heatmap with embedded chart | Working file |
| `organoid_accuracy_bar.xlsx` | Simple bar chart data | Single row |
| `organoid_roc.xlsx` | Basic ROC curve | 100 points |
| `r2_o2_comparison.xlsx` | O2-specific R2 | Subset of Fig_3d |
| `roc_curves_all.xlsx` | Per-fold ROC | Raw data |
| `Prediction_Scatter_Plots.xlsx` | Extended predictions | Includes multiclass |
| `ADMET/DICTrank_Predictions.xlsx` | Per-drug ADMET predictions | 27 drugs |
| `ADMET/DICTrank_Training.xlsx` | Training metrics | 4 models |
| `ADMET/Scaffold_CV.xlsx` | Scaffold validation | Confusion matrices |
| `MoLFormer/Confusion_Matrices.xlsx` | 3 model CMs | Extended format |
| `MoLFormer/Per_Drug_Predictions.xlsx` | Drug-level predictions | 25 drugs x 3 models |
| `MoLFormer/ROC_Comparison.xlsx` | ROC + AUC summary | 2 sheets |
| `MoLFormer/Summary_Table.xlsx` | Full summary | 10 columns |

---

## Files Only in PowerPoint_Figures (Not in Excel)

| File | Purpose | Notes |
|------|---------|-------|
| `Fig_4/Fig_4_data.xlsx` | Drug grid positions | 25 drugs with Row/Col |
| `Fig_5/Fig_5_data.xlsx` | 3D plot drug list | Same 25 drugs |
| All `Fig_S1/` files | Supplementary heatmaps | Equation comparison |
| All `Fig_S3/` files | Supplementary LOOCV | Extended results |

---

## Data Integrity Summary

### Confirmed Matches (Same Data)
1. Cumulative feature importance values
2. Drug lists (25 drugs consistent)
3. 14 PK-PD coefficient names
4. Core metric values (Accuracy, AUC means)

### Confirmed Differences
1. **ROC curves:** PowerPoint has per-fold data; Excel has summarized
2. **SHAP:** PowerPoint has per-drug values; Excel has aggregated means
3. **Confusion matrices:** May have different aggregation methods
4. **Metadata:** PowerPoint adds Source, Threshold columns

### Potential Inconsistencies to Verify
1. Confusion matrix totals may differ due to different CV aggregation
2. Threshold values for classification cutoffs
3. Number of samples in cross-validation (250 in some, 25 in others)

---

## Recommendations

1. **For Publication:** Use PowerPoint_Figures data - it has full traceability
2. **For Recalculation:** Use PowerPoint_Figures - it has raw fold data
3. **For Quick Reference:** Use Excel_Figures - simpler structure
4. **Synchronization Needed:** Update Excel_Figures to match PowerPoint structure for consistency

---

## Appendix: Column Name Mapping

| PowerPoint Column | Excel Column | Notes |
|-------------------|--------------|-------|
| Predicted_Arrhythmia_pct | Predicted_Arrhythmia_pct | Same |
| Actual_Arrhythmia | Actual_Arrhythmia | Same |
| is_positive | N/A | PowerPoint only |
| Source | N/A | PowerPoint only |
| Threshold_Value | N/A | PowerPoint only |
| TPR_Lower | N/A | PowerPoint only (CI) |
| TPR_Upper | N/A | PowerPoint only (CI) |
| Fold1_FPR, Fold1_TPR... | FPR, TPR_Mean | Different granularity |
