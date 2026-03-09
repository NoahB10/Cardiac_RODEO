# Cardiac RODEO - AI Coding Agent Guide

## Big Picture
- Purpose: Predict cardiac outcomes and visualize response surfaces using PK-PD elimination coefficients from organoid experiments.
- Targets: `Arrhythmia` (binary), `heart_damage` (binary), `Concern` (multiclass: most/less/no).
- Two responses per drug: Contractility and O2; each has 7 coefficients -> 14 features total.
- Core equation: R = R0 + Emax * (1 - exp(-kappa * (C0/Cmax * exp(-k_elim*t))^n * (t/tau)^m)).

## Source of Truth
- Coefficients + labels: `EQN_Coefficients/all_equations_coefficients.xlsx`, sheet `pkpd_elimination`.
- Excel duplicates headers: Contractility uses `R0,Emax,kappa,n,m,tau,k_elim`; O2 uses `R0.1,Emax.1,...,k_elim.1`.
- Read with: `pd.read_excel(..., sheet_name='pkpd_elimination', header=1)` then `df.columns = df.columns.str.strip()`.
- Drug SMILES: `Cleaned_Data/drug_smiles.csv` (MASTER COPY).

## Parameter Bounds (from pipeline)

| Parameter | Contractility | O2 |
|-----------|--------------|-----|
| R0 | [0, 0.2] | [5, 25] |
| Emax | [0, 0.2] | [0, 100] |
| kappa | [1e-6, 100] | [1e-6, 100] |
| n | [0.1, 6.0] | [0.1, 6.0] |
| m | [0.1, 6.0] | [0.1, 6.0] |
| tau | [0.1, 96] | [0.1, 96] |
| k_elim | [1e-6, 1.0] | [1e-6, 1.0] |

Modify in: `Picking Equations/equation_fitting/config.py`

## Conventions
- Path discovery (don't hardcode):
  - If CWD ends with `Prediction_Models`, `PROJECT_ROOT = cwd.parent`.
  - Else if `EQN_Coefficients` exists in CWD, `PROJECT_ROOT = cwd`.
  - Else if exists in parent, use parent; otherwise fallback to CWD.
- Meshgrid/axes for 3D surfaces: X=time `[0,96]`, Y=dose ratio `[0,2]`, Z=response; view `ax.view_init(25, -158)`.
- Use `.loc[idx]` not `iloc` for DataFrame rows; indices are labels, not positions.

## Core Helpers (see `Prediction_Models/utils.py`)
- `extract_features(df)`: Builds 14-feature matrix with names like `R0_Contractility` and `R0_O2` (handles `.1` suffixes).
- `preprocess_targets(df, target)`: Maps labels -> numbers: binary `'true'/'false'`->`1/0`; `Concern` `'most'/'less'/'no'`->`2/1/0`.

## Entry Points

| Task | Entry Point | Key Outputs |
|------|------------|-------------|
| Fit equations | `Picking Equations/equation_fitting/run_pipeline.py` | `EQN_Coefficients/all_equations_coefficients.xlsx` |
| Train prediction models | `Prediction_Models/pipeline/run_pipeline.py` | `Output/Model_Properties/*.joblib` |
| LOOCV comparison | `Prediction_Models/loocv_model_comparison.py` | `Output/Performance_Metrics/`, ROC, SHAP |
| ADMET comparison | `ADMET_Comparison/Scripts/full_analysis.py` | `Output/ADMET_Comparison/` |
| Interactive exploration | `interactive_pkpd_elimination_plotter.py` | Interactive window |
| Model training notebook | `Prediction_Models/Prediction_Models_AR_HD_Concern.ipynb` | Models, plots |
| Publication plots | `Prediction_Models/Paper_Plots_PKPD_Elimination_Surfaces.ipynb` | `Output/3D_Plots/` |

## Typical Workflows
- Model training: `Prediction_Models/Prediction_Models_AR_HD_Concern.ipynb`
  - Load Excel -> `extract_features` -> `preprocess_targets`.
  - Pipeline: `SimpleImputer(mean)` -> `StandardScaler` -> `XGBClassifier` (binary) / `LogisticRegression` (multiclass).
  - Stratified CV; save to `Output/Model_Properties/*.joblib` and metrics CSVs.
- Publication plots: `Prediction_Models/Paper_Plots_PKPD_Elimination_Surfaces.ipynb`
  - Preview first 3, compute global color limits once, then batch-generate 2D/3D plots.
- Interactive exploration: `interactive_pkpd_elimination_plotter.py`
  - 3D surface on left, equation + controls on right
  - Text input with +/- buttons for each parameter
  - Toggle between Contractility/O2 modes

## Plotting Standards
- Time (X) and Dose/Cmax (Y) mesh: `T, Dr = np.meshgrid(time, dose_ratio)`; call `ax.plot_surface(T, Dr, Response, ...)`.
- Enforce positivity: clamp `kappa, tau, k_elim >= 1e-9`; `time = np.maximum(time, 0)` before computing response.
- Prefer a single global `vmin/vmax` across comparable surfaces for publication figures.

## Outputs & Artifacts
- Models and reports: `Output/Model_Properties/` (e.g., `xgb_pkpd_elimination_Arrhythmia.joblib`).
- Figures: `Output/2D_Plots/`, `Output/3D_Plots/`. Sanitize filenames: replace spaces and `/`, allow `[A-Za-z0-9_-]`.
- Each output folder has a `README.txt` describing its contents.

## Quickstart (PowerShell)
```powershell
# From repo root
python -m pip install pandas numpy scikit-learn xgboost joblib openpyxl matplotlib seaborn shap ipykernel jupyter

# Launch Jupyter for notebooks
python -m jupyter notebook

# Run interactive surface explorer
python interactive_pkpd_elimination_plotter.py
```

## Pitfalls
- Excel headers: forgetting `header=1` or `.str.strip()` breaks column matching and feature extraction.
- Data filtering cells can overwrite `df_raw` globally; preview first and document OPTIONAL cells.
- NaNs/infs in coefficients: filter before plotting/training to avoid axis scaling glitches and training errors.
- Memory/perf: reduce grid resolution when aggregating across many drugs for 2D statistics.

## Where to Look
- Data/labels: `EQN_Coefficients/`
- Training & plots: `Prediction_Models/*.ipynb`
- Helpers: `Prediction_Models/utils.py`
- Interactive demo: `interactive_pkpd_elimination_plotter.py`
- Full docs: `CLAUDE.md`
