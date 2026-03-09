# Cardiac RODEO

Cardiac RODEO (Response-Outcome Drug Effect on Organoids) is a machine learning project for predicting cardiac outcomes from organoid experiments using PK-PD elimination equation coefficients.

## Overview

This project trains classifiers to predict cardiac outcomes:
- **Arrhythmia** (binary: true/false)
- **Heart Damage** (binary: true/false)
- **Concern** level (multiclass: most/less/no)

Each drug has two response types (Contractility and O2), each characterized by 7 PK-PD coefficients, creating a 14-feature input space.

### Core Equation

```
R(C0, t) = R0 + Emax * (1 - exp(-kappa * (C0/Cmax * exp(-k_elim * t))^n * (t/tau)^m))
```

**Parameters:** R0, Emax, kappa, n, m, tau, k_elim

## Quick Start

```powershell
# Install dependencies
python -m pip install pandas numpy scikit-learn xgboost joblib openpyxl matplotlib seaborn shap ipykernel jupyter

# Run interactive surface explorer
python interactive_pkpd_elimination_plotter.py

# Launch Jupyter for notebooks
python -m jupyter notebook
```

## Repository Layout

```
Cardiac_RODEO/
├── EQN_Coefficients/          # Equation coefficients (source of truth)
├── Cleaned_Data/              # Processed experimental data
├── Picking Equations/         # Equation fitting pipeline
├── Prediction_Models/         # ML model training
├── ADMET_Comparison/          # ADMET comparison analysis
├── Output/                    # All generated outputs
└── interactive_pkpd_elimination_plotter.py
```

## Main Entry Points

| Task | Entry Point |
|------|-------------|
| **Interactive exploration** | `python interactive_pkpd_elimination_plotter.py` |
| **Fit equations** | `python "Picking Equations/equation_fitting/run_pipeline.py"` |
| **Train models** | `python Prediction_Models/pipeline/run_pipeline.py` |
| **LOOCV comparison** | `python Prediction_Models/loocv_model_comparison.py` |
| **ADMET comparison** | `python ADMET_Comparison/Scripts/full_analysis.py` |

## Inputs and Outputs by Task

### Equation Fitting

- **Entry point:** `Picking Equations/equation_fitting/run_pipeline.py`
- **Inputs:**
  - `Cleaned_Data/Heart_Contractility_Averaged.xlsx`
  - `Cleaned_Data/O2_Mean_Averaged.xlsx`
  - `Cleaned_Data/drug_Cmax.csv`
- **Outputs:**
  - `EQN_Coefficients/all_equations_coefficients.xlsx`
  - `Output/Equation_Fitting/Coefficients/*.csv`
  - `Output/LaTeX_Reports/equation_analysis_report.*`

### Prediction Models

- **Entry point:** `Prediction_Models/pipeline/run_pipeline.py`
- **Inputs:** `EQN_Coefficients/all_equations_coefficients.xlsx`
- **Outputs:**
  - `Output/Model_Properties/*.joblib`
  - `Output/Performance_Metrics/*.csv`
  - `Output/SHAP_Data/`
  - `Output/LaTeX_Reports/prediction_models_report.pdf`

### LOOCV Model Comparison

- **Entry point:** `Prediction_Models/loocv_model_comparison.py`
- **Inputs:** `EQN_Coefficients/all_equations_coefficients.xlsx`
- **Outputs:** Organized by data type (each folder has a README.txt):
  - `Output/Performance_Metrics/` - CV results
  - `Output/ROC_Data/` - ROC curves
  - `Output/Confusion_Matrices/` - Confusion matrices
  - `Output/SHAP_Data/` - SHAP values
  - `Output/Prediction_Scatter_Data/` - Predictions
  - `Output/Cumulative_Plot_Data/` - Aggregated data

### ADMET Comparison

- **Entry point:** `ADMET_Comparison/Scripts/full_analysis.py`
- **Outputs:** `Output/ADMET_Comparison/`

### Interactive PKPD Surface Explorer

- **Entry point:** `interactive_pkpd_elimination_plotter.py`
- **Features:**
  - 3D surface visualization (left panel)
  - Equation displayed with LaTeX formatting (top right)
  - 7 parameter controls with text input and +/- buttons
  - Toggle between Contractility and O2 modes
  - Parameters bounded to match pipeline
- **No file outputs** - interactive window only

### 3D and 2D Surface Plots

- **Entry points:** `3D_Surface_Plots.ipynb`, `Paper_Plots_PKPD_Elimination_Surfaces.ipynb`
- **Inputs:** `EQN_Coefficients/all_equations_coefficients.xlsx`
- **Outputs:**
  - `Output/3D_Plots/`
  - `Output/2D_Plots/`

### TC50 O2 Concentration Plots

- **Entry point:** `TC50_O2_Concentration_Plots.ipynb`
- **Inputs:** `Cleaned_Data/DrugScreen19.11.25_compiled_O2_mean.xlsx`
- **Outputs:** `Output/TC50_Plots/*.png`

### Heart Rate Analysis

- **Entry point:** `heart_rate_analysis.ipynb`
- **Inputs:** `Cleaned_Data/Raw_Tables.zip` (extract to `Cleaned_Data/Stage1_Raw_Relaxed/`)
- **Outputs:** `Output/HeartRate_Analysis/`

### Raw QC Analysis

- **Entry points:** `analyze_raw_qc.py`, `raw_qc_analysis.ipynb`
- **Inputs:** `LogFiles/P*OxygenLogs/`
- **Outputs:** `Output/QC_Analysis/`

## Output Directory Map

| Folder | Contents |
|--------|----------|
| `Output/Model_Properties/` | Trained models (.joblib) |
| `Output/Performance_Metrics/` | CV results, performance summaries |
| `Output/ROC_Data/` | ROC curves and data |
| `Output/Confusion_Matrices/` | Confusion matrix plots |
| `Output/SHAP_Data/` | SHAP feature importance |
| `Output/Prediction_Scatter_Data/` | Prediction scatter data |
| `Output/Cumulative_Plot_Data/` | Aggregated statistics |
| `Output/Feature_Importance/` | Feature importance comparisons |
| `Output/Equation_Fitting/` | Equation fitting outputs |
| `Output/3D_Plots/` | 3D response surfaces |
| `Output/2D_Plots/` | 2D projections |
| `Output/LaTeX_Reports/` | PDF reports |
| `Output/ADMET_Comparison/` | ADMET comparison outputs |
| `Output/TC50_Plots/` | TC50 plots |
| `Output/HeartRate_Analysis/` | Heart rate analysis |
| `Output/QC_Analysis/` | QC analysis |

## Data Files

### Source of Truth
- **Coefficients + labels:** `EQN_Coefficients/all_equations_coefficients.xlsx`
  - Sheet: `pkpd_elimination`
  - Read with: `pd.read_excel(..., sheet_name='pkpd_elimination', header=1)`
  - Then: `df.columns = df.columns.str.strip()`

### Drug SMILES
- **Master copy:** `Cleaned_Data/drug_smiles.csv` - edit this file to correct SMILES

### Column Naming
- Contractility: `R0`, `Emax`, `kappa`, `n`, `m`, `tau`, `k_elim`
- O2: `R0.1`, `Emax.1`, `kappa.1`, `n.1`, `m.1`, `tau.1`, `k_elim.1`

## Parameter Bounds

| Parameter | Contractility | O2 |
|-----------|--------------|-----|
| R0 | [0, 0.2] | [5, 25] |
| Emax | [0, 0.2] | [0, 100] |
| kappa | [1e-6, 100] | [1e-6, 100] |
| n | [0.1, 6.0] | [0.1, 6.0] |
| m | [0.1, 6.0] | [0.1, 6.0] |
| tau | [0.1, 96] | [0.1, 96] |
| k_elim | [1e-6, 1.0] | [1e-6, 1.0] |

Modify bounds in: `Picking Equations/equation_fitting/config.py`

## AI Agent Instructions

See `CLAUDE.md` for detailed guidance on working with this codebase, including:
- Path discovery conventions
- Utility functions
- Plotting standards
- Common pitfalls
