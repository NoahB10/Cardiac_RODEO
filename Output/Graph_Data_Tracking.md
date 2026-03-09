# Graph Data Tracking Document

This document tracks the locations of key graphs and their corresponding Excel data files for reproducibility.

**Note:** All Excel files are automatically generated when running the pipelines:
- `Prediction_Models/loocv_model_comparison.py` - Generates all prediction model Excel files
- `Picking Equations/equation_fitting/run_pipeline.py` - Generates equation fitting Excel files
- `ADMET_Comparison/Scripts/full_analysis.py` - Generates ADMET comparison Excel files

---

## Stage 0: Equation Selection (R2 Comparison)

### O2 Mean R2 by Equation (Picking Equations)

| Item | Path |
|------|------|
| **Plot** | `Output/Equation_Fitting/Plots/r2_distributions.pdf` |
| **Data Excel** | `Output/Equation_Fitting/Plots/r2_comparison_by_equation.xlsx` |

**Data Contents:**
- `Equation`: Internal equation name
- `Equation_Display`: Display name with equation number (e.g., "Dual Exponential (Eq1)")
- `Mean_R2_Contractility`, `Std_R2_Contractility`, `Min_R2_Contractility`, `Max_R2_Contractility`
- `Mean_R2_O2`, `Std_R2_O2`, `Min_R2_O2`, `Max_R2_O2`

**Source Data:** Individual coefficient CSVs in `Output/Equation_Fitting/Coefficients/`

---

## Stage 1: Model & Equation Selection (LOOCV)

### LOOCV ROC Curves

| Item | Path |
|------|------|
| **Plot** | `Output/ROC_Data/ROC_All_LOOCV.png` |
| **Data Excel** | `Output/ROC_Data/loocv_model_comparison.xlsx` |

**Sheets:**
- `All_Results`: Full LOOCV results (Equation, Target, Model, Accuracy, AUC, N_samples, Confusion_Matrix)
- `Summary`: Best model per equation/target combination

### LOOCV Model Performance Summary

| Item | Path |
|------|------|
| **Data Excel** | `Output/Performance_Metrics/all_performance_metrics.xlsx` |

**Relevant Sheets:**
- `loocv_results`: Full LOOCV comparison across equations and models
- `model_performance_summary`: Final selected models with cross-validation metrics

---

## Final Analysis: Optimal Configuration Results

### ROC Curves (Final Models)

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/ROC_Data/final_roc_curves.pdf` |
| **Plot (PNG)** | `Output/ROC_Data/final_roc_curves.png` |
| **Data Excel** | `Output/ROC_Data/final_roc_curves.xlsx` |

**Sheets:**
- `Arrhythmia`: FPR, TPR values for ROC curve
- `heart_damage`: FPR, TPR values for ROC curve
- `Concern_Binary`: FPR, TPR values for binary concern ROC curve
- `Concern_most`, `Concern_less`, `Concern_no`: Multi-class ROC data

### Confusion Matrices

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/Confusion_Matrices/final_confusion_matrices.pdf` |
| **Plot (PNG)** | `Output/Confusion_Matrices/final_confusion_matrices.png` |
| **Data Excel** | `Output/Confusion_Matrices/confusion_matrices_all.xlsx` |

**Sheets:**
- `arrhythmia`: Confusion matrix values
- `heart_damage`: Confusion matrix values
- `concern`: Confusion matrix values (multiclass)
- `concern_binary`: Confusion matrix values (binary: No+Less vs Most)
- `arrhythmia_report`: Classification report (precision, recall, F1)
- `heart_damage_report`: Classification report
- `concern_report`: Classification report
- `concern_binary_report`: Classification report

### SHAP Feature Importance (Arrhythmia)

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/SHAP_Data/shap_arrhythmia_bar.pdf` |
| **Data Excel** | `Output/SHAP_Data/shap_arrhythmia_bar.xlsx` |

**Sheets:**
- `mean_importance`: Feature, Mean_Abs_SHAP (sorted by importance)
- `values`: Drug-level SHAP values for each feature

### SHAP Feature Importance (Heart Damage)

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/SHAP_Data/shap_heart_damage_bar.pdf` |
| **Data Excel** | `Output/SHAP_Data/shap_heart_damage_bar.xlsx` |

**Sheets:**
- `mean_importance`: Feature, Mean_Abs_SHAP
- `values`: Drug-level SHAP values

### SHAP Feature Importance (Concern - Binary)

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/SHAP_Data/shap_concern_binary_bar.pdf` |
| **Data Excel** | `Output/SHAP_Data/shap_concern_binary_bar.xlsx` |

**Sheets:**
- `mean_importance`: Feature, Mean_Abs_SHAP
- `values`: Drug-level SHAP values

### SHAP Feature Importance (Concern - Most)

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/SHAP_Data/shap_concern_most_concern_bar.pdf` |
| **Data Excel** | `Output/SHAP_Data/shap_concern_most_concern_bar.xlsx` |

**Sheets:**
- `mean_importance`: Feature, Mean_Abs_SHAP
- `values`: Drug-level SHAP values

### SHAP Aligned Pairs (Arrhythmia vs Heart Damage)

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/SHAP_Data/shap_aligned_pairs.pdf` |
| **Plot (PNG)** | `Output/SHAP_Data/shap_aligned_pairs.png` |
| **Data Excel** | `Output/SHAP_Data/shap_aligned_pairs_data.xlsx` |

### Complete SHAP Analysis

| Item | Path |
|------|------|
| **Data Excel** | `Output/SHAP_Data/shap_complete_analysis.xlsx` |

**Sheets:**
- `arrhythmia_mean`: Mean absolute SHAP values
- `arrhythmia_values`: Individual SHAP values per drug
- `heart_damage_mean`: Mean absolute SHAP values
- `heart_damage_values`: Individual SHAP values per drug
- `concern_binary_mean`: Mean absolute SHAP values for binary concern
- `concern_binary_values`: Individual SHAP values per drug
- `concern_no_mean`, `concern_less_mean`, `concern_most_mean`: Concern class SHAP
- `feature_values_raw`: Raw feature values used
- `feature_values_scaled`: Scaled feature values
- `summary`: Combined summary across all models

### Prediction Scatter Plots

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/Prediction_Scatter_Data/prediction_scatter_all.pdf` |
| **Data Excel** | `Output/Prediction_Scatter_Data/prediction_scatter_all.xlsx` |

**Sheets:**
- `arrhythmia`: Drug, True_Label, Predicted_Prob, Predicted_Class
- `heart_damage`: Drug, True_Label, Predicted_Prob, Predicted_Class
- `concern_binary`: Drug, True_Label, Predicted_Prob (binary: High Concern)
- `concern`: Drug, True_Label, Predicted_Prob (per class)

### Cumulative Feature Importance

| Item | Path |
|------|------|
| **Plot (PDF)** | `Output/Cumulative_Plot_Data/cumulative_feature_importance.pdf` |
| **Plot (PNG)** | `Output/Cumulative_Plot_Data/cumulative_feature_importance.png` |
| **Data Excel** | `Output/Cumulative_Plot_Data/cumulative_feature_importance.xlsx` |

**Sheets:**
- `Arrhythmia`: Cumulative importance by number of features
- `Heart Damage`: Cumulative importance
- `Concern Binary`: Cumulative importance for binary concern
- `Concern No`, `Concern Less`, `Concern Most`: Multi-class cumulative

---

## ADMET Comparison Analysis

### ROC Curves (ADMET-AI vs SwissADME)

| Item | Path |
|------|------|
| **Overall ROC Comparison** | `Output/ADMET_Comparison/Overall_ROC_Comparison.png` |
| **LOOCV ROC** | `Output/ADMET_Comparison/LOOCV_ROC.png` |
| **Scaffold ROC** | `Output/ADMET_Comparison/Scaffold_ROC.png` |
| **DICTrank ROC** | `Output/ADMET_Comparison/DICTrank_ROC_25.png` |
| **Organoid ROC** | `Output/ADMET_Comparison/Organoid_ROC.png` |
| **Data Excel** | `Output/ADMET_Comparison/admet_analysis_summary.xlsx` |

### Accuracy/AUC Bar Charts

| Item | Path |
|------|------|
| **AUC Comparison** | `Output/ADMET_Comparison/AUC_Comparison.png` |
| **Accuracy Comparison** | `Output/ADMET_Comparison/Accuracy_Comparison.png` |
| **DICTrank AUC Bar** | `Output/ADMET_Comparison/DICTrank_AUC_Bar.png` |
| **DICTrank Accuracy Bar** | `Output/ADMET_Comparison/DICTrank_Accuracy_Bar.png` |
| **LOOCV AUC Bar** | `Output/ADMET_Comparison/LOOCV_AUC_Bar.png` |
| **LOOCV Accuracy Bar** | `Output/ADMET_Comparison/LOOCV_Accuracy_Bar.png` |
| **Scaffold AUC Bar** | `Output/ADMET_Comparison/Scaffold_AUC_Bar.png` |
| **Scaffold Accuracy Bar** | `Output/ADMET_Comparison/Scaffold_Accuracy_Bar.png` |
| **Organoid AUC Bar** | `Output/ADMET_Comparison/Organoid_AUC_Bar.png` |
| **Organoid Accuracy Bar** | `Output/ADMET_Comparison/Organoid_Accuracy_Bar.png` |

### Confusion Matrices

| Item | Path |
|------|------|
| **DICTrank Confusion** | `Output/ADMET_Comparison/DICTrank_Confusion_Matrices.png` |
| **DICTrank Training Confusion** | `Output/ADMET_Comparison/DICTrank_Training_Confusion.png` |
| **LOOCV Confusion** | `Output/ADMET_Comparison/LOOCV_Confusion_Matrices.png` |
| **Scaffold Confusion** | `Output/ADMET_Comparison/Scaffold_Confusion_Matrices.png` |
| **Organoid Confusion** | `Output/ADMET_Comparison/Organoid_Confusion_Matrix.png` |

### Drug Prediction Plots

| Item | Path |
|------|------|
| **DICTrank Predictions** | `Output/ADMET_Comparison/DICTrank_Predictions.png` |
| **LOOCV Predictions** | `Output/ADMET_Comparison/LOOCV_Predictions.png` |
| **Scaffold Predictions** | `Output/ADMET_Comparison/Scaffold_Predictions.png` |
| **Data Excel** | `Output/ADMET_Comparison/drug_predictions_all.xlsx` |

**Sheets in drug_predictions_all.xlsx:**
- `All_Predictions`: ADMET-AI vs SwissADME predictions for all drugs
- `DICTrank_25`: DICTrank model predictions on 25 drugs
- `Scaffold_Input`: Scaffold CV input data
- `DICT_Predictions`: DICTrank binary predictions

### SHAP Feature Importance (ADMET)

| Item | Path |
|------|------|
| **Data Excel** | `Output/ADMET_Comparison/shap_feature_importance_admet.xlsx` |

**Sheets:**
- `DICTrank`: Top SHAP features from DICTrank-trained model
- `LOOCV`: Top SHAP features from LOOCV model
- `Scaffold`: Top SHAP features from scaffold CV model

### Complete ADMET Summary

| Item | Path |
|------|------|
| **Data Excel** | `Output/ADMET_Comparison/admet_analysis_summary.xlsx` |

**Sheets:**
- `AUC_Accuracy`: All accuracy and AUC metrics across settings
- `Drug_Predictions`: Full drug prediction table
- `Drug_Database`: Drug SMILES and metadata

### Additional Data Files

| File | Description |
|------|-------------|
| `cardiac_rodeo_drugs_smiles.csv` | Drug names and SMILES structures |
| `cardiac_rodeo_full_ADMET.csv` | Full ADMET-AI feature predictions |
| `cardiac_rodeo_full_swissadme.csv` | Full SwissADME feature predictions |
| `dictrank_retrain_metrics.csv` | DICTrank retraining metrics |
| `dictrank_retrain_metrics.xlsx` | Excel version with Full_Training and 25_Drugs sheets |

---

## Quick Reference: File Locations

| Analysis Stage | Plots Directory | Data Directory |
|----------------|-----------------|----------------|
| Equation Selection | `Output/Equation_Fitting/Plots/` | `Output/Equation_Fitting/Coefficients/` |
| LOOCV Comparison | `Output/ROC_Data/` | `Output/Performance_Metrics/` |
| Final ROC | `Output/ROC_Data/` | `Output/ROC_Data/` |
| Confusion Matrices | `Output/Confusion_Matrices/` | `Output/Confusion_Matrices/` |
| SHAP Analysis | `Output/SHAP_Data/` | `Output/SHAP_Data/` |
| Predictions | `Output/Prediction_Scatter_Data/` | `Output/Prediction_Scatter_Data/` |
| ADMET Comparison | `Output/ADMET_Comparison/` | `Output/ADMET_Comparison/` |

---

## Regenerating Graphs

All graphs can be regenerated from the Excel data files using standard plotting libraries. The Excel files contain the exact numerical values used to create each visualization.

**Pipeline Scripts (auto-generate plots AND Excel files):**
- `Prediction_Models/loocv_model_comparison.py` - Full prediction pipeline (run from project root)
- `Picking Equations/equation_fitting/run_pipeline.py` - Equation fitting pipeline
- `ADMET_Comparison/Scripts/full_analysis.py` - ADMET comparison pipeline

**Notebooks (for interactive analysis):**
- `Prediction_Models/Prediction_Models_AR_HD_Concern.ipynb` - Main model training and evaluation
