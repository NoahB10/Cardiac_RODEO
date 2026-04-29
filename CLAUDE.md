# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Cardiac RODEO (Response-Outcome Drug Effect on Organoids) predicts cardiac outcomes from organoid experiments using PK-PD elimination equation coefficients. The project trains classifiers for:
- **Arrhythmia** (binary: true/false)
- **heart_damage** (binary: true/false)
- **Concern** (multiclass: most/less/no)

Each drug has two response types (Contractility and O2), each characterized by 7 PK-PD coefficients, creating a 14-feature input space.

## Core Equation

The PK-PD elimination equation (Eq11) models drug response over time:

```
R(C0, t) = R0 + Emax * (1 - exp(-kappa * (C0/Cmax * exp(-k_elim * t))^n * (t/tau)^m))
```

**Parameters (7 per response type):** R0, Emax, kappa, n, m, tau, k_elim

| Parameter | Contractility | O2 | Description |
|-----------|--------------|-----|-------------|
| R0 | [0, 0.2] | [5, 25] | Baseline response |
| Emax | [0, 0.2] | [0, 100] | Maximum effect amplitude |
| kappa | [1e-6, 100] | [1e-6, 100] | Potency parameter |
| n | [0.1, 6.0] | [0.1, 6.0] | Hill coefficient (concentration) |
| m | [0.1, 6.0] | [0.1, 6.0] | Hill coefficient (time) |
| tau | [0.1, 96] | [0.1, 96] | Time scale (hours) |
| k_elim | [1e-6, 1.0] | [1e-6, 1.0] | Elimination rate (1/h) |

Modify bounds in: `Picking Equations/equation_fitting/config.py` → `get_bounds()`

## Data Source of Truth

**Primary data file:** `EQN_Coefficients/all_equations_coefficients.xlsx`
- Sheet: `pkpd_elimination`
- **Critical:** Excel has duplicate headers. Always load with:
```python
df = pd.read_excel(path, sheet_name='pkpd_elimination', header=1)
df.columns = df.columns.str.strip()
```

**Column naming:**
- Contractility: `R0`, `Emax`, `kappa`, `n`, `m`, `tau`, `k_elim`
- O2 (suffix `.1`): `R0.1`, `Emax.1`, `kappa.1`, `n.1`, `m.1`, `tau.1`, `k_elim.1`

**Drug SMILES master copy:** `Cleaned_Data/drug_smiles.csv` (25 drugs)

**Excluded drugs:** `DMSO`, `Troglitazone`, `Troglitarazine`

## Essential Utilities (`Prediction_Models/utils.py`)

### extract_features(df)
Builds 14-feature matrix from raw coefficient data:
- Returns DataFrame with columns: `R0_Contractility`, `Emax_Contractility`, ..., `R0_O2`, `Emax_O2`, ...
- Handles `.1` suffix for O2 coefficients

### preprocess_targets(df, target_column)
Converts target labels to numeric:
- Binary (`Arrhythmia`, `heart_damage`): `'true'/'false'` → `1/0`
- Multiclass (`Concern`): `'most'/'less'/'no'` → `2/1/0`

## Path Discovery Convention

**Never hardcode paths.** Use this pattern:
```python
from pathlib import Path

current_dir = Path.cwd()
if current_dir.name == 'Prediction_Models':
    PROJECT_ROOT = current_dir.parent
elif (current_dir / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir
elif (current_dir.parent / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir.parent
else:
    PROJECT_ROOT = current_dir

EXCEL_PATH = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
```

## Entry Points

| Task | Entry Point | Key Outputs |
|------|------------|-------------|
| Fit equations | `Picking Equations/equation_fitting/run_pipeline.py` | `EQN_Coefficients/all_equations_coefficients.xlsx` |
| Train models | `Prediction_Models/pipeline/run_pipeline.py` | `Output/Model_Properties/*.joblib` |
| LOOCV comparison | `Prediction_Models/loocv_model_comparison.py` | `Output/Performance_Metrics/`, ROC, SHAP |
| ADMET comparison | `ADMET_Comparison/Scripts/full_analysis.py` | `Output/ADMET_Comparison/` |
| Interactive explorer | `interactive_pkpd_elimination_plotter.py` | Interactive window |
| Model training notebook | `Prediction_Models/Prediction_Models_AR_HD_Concern.ipynb` | Models, plots |
| Publication plots | `Prediction_Models/Paper_Plots_PKPD_Elimination_Surfaces.ipynb` | `Output/3D_Plots/` |
| Heart rate analysis | `heart_rate_analysis.ipynb` | `Output/HeartRate_Analysis/` |
| Raw QC analysis | `analyze_raw_qc.py`, `raw_qc_analysis.ipynb` | `Output/QC_Analysis/` |

## Pipeline Details

### Equation Fitting Pipeline
```powershell
cd "Picking Equations/equation_fitting"
python run_pipeline.py
```

Steps: `--fit` → `--consolidate` → `--excel` → `--report`

**Inputs:**
- `Cleaned_Data/Heart_Contractility_Averaged.xlsx`
- `Cleaned_Data/O2_Mean_Averaged.xlsx`
- `Cleaned_Data/drug_Cmax.csv`

**12 equations fitted:** dual_exponential, bivariate_gaussian, gaussian_hill_hybrid, modified_hill_hormesis, gaussian_ridge, adaptive_response, biphasic_response, cumulative_exposure, recovery_model, modified_hill_simple, pkpd_elimination, hormesis_v0

### Model Training Workflow
1. Load data with `header=1` and `.str.strip()` column names
2. `extract_features(df)` → 14-feature matrix
3. `preprocess_targets(df, target_col)` → numeric labels
4. Pipeline: `SimpleImputer(mean)` → `StandardScaler` → `XGBClassifier` (binary) / `LogisticRegression` (multiclass)
5. Stratified cross-validation with `StratifiedKFold`

## Plotting Standards

### Axisless Image Sizing (Overlay Rule)
Every figure has a "with-axis" copy and an "axisless" copy in `Output/PowerPoint_Figures/Fig_X/` and `Fig_X/Axisless/`. The axisless PNG MUST be saved at the exact axes-bbox size — i.e. the rectangle inside the with-axis image where data is plotted, with tick labels and axis labels excluded.

**Why:** when the axisless image is overlaid on the with-axis image and aligned to the axes area, it must fit pixel-perfect with no resizing. Any whitespace *inside* the axes is kept (it's part of the plot area); any margin *outside* the axes (for ticks/labels) is excluded.

**How:** `generate_axisless_figures.py` monkey-patches `Figure.savefig` and for the axisless copy passes `bbox_inches=<axes extent in inches>` plus `pad_inches=0`. The axes extent comes from `ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())`. Do NOT use `bbox_inches='tight'` for the axisless save (that would crop to the visible content and break the overlay). Do NOT post-crop uniform-white borders with PIL — that removes legitimate whitespace inside the axes.

For figures with a colorbar axes, the colorbar (narrowest axes) is excluded and the main data axes is used for the bbox.

### 3D Surface Plots
- **X-axis:** Time (hours), range `[0, 96]`
- **Y-axis:** Dose ratio (C0/Cmax), range `[0, 2]`
- **Z-axis:** Response value
- **View angle:** `ax.view_init(elev=25, azim=-158)`
- **Meshgrid:** `T, Dr = np.meshgrid(time, dose_ratio)`; call `ax.plot_surface(T, Dr, Response, ...)`

**Critical: use `ax.text2D()` for labels and titles on 3D plots.**
Matplotlib's `ax.set_zlabel()` and `ax.set_title()` are NOT reliably captured by `bbox_inches='tight'` on 3D axes. Always use `ax.text2D()` instead:
```python
# Font sizes for individual 600 DPI images
TITLE_SIZE = 28
LABEL_SIZE = 24
TICK_SIZE = 20

# Title — centered above plot, no gap
ax.text2D(0.5, 0.97, drug_name, transform=ax.transAxes,
          fontsize=TITLE_SIZE, fontweight='bold', ha='center', va='top')

# Z-axis label — tight against tick labels
ax.text2D(-0.02, 0.5, z_label, transform=ax.transAxes,
          fontsize=LABEL_SIZE, rotation=90, va='center', ha='right')

# O2 label — use mathtext for subscript (Unicode ₂ won't render in all fonts)
z_label = r'$O_2$ (%)'
```

**Asymmetric padding for tight 3D images:**
Save with `bbox_inches='tight', pad_inches=0.02, transparent=True`, then add left-only padding via PIL (RGBA for transparency):
```python
from PIL import Image as PILImage
img = PILImage.open(filepath).convert('RGBA')
left_extra = int(0.08 * 600)  # 0.08" at 600 DPI
new_img = PILImage.new('RGBA', (img.width + left_extra, img.height), (0, 0, 0, 0))
new_img.paste(img, (left_extra, 0))
new_img.save(filepath, dpi=(600, 600))
```

### Parameter Validation
- Clamp positive: `kappa = max(kappa, 1e-9)`, same for `tau`, `k_elim`
- Non-negative time: `time = np.maximum(time, 0)` before computing response
- Use single global `vmin`/`vmax` across comparable surfaces

### Filename Sanitization
Replace spaces and `/`; allow only `[A-Za-z0-9_-]`

### 5x5 Grid Generation (Individual Images → PowerPoint)

**Scripts (in `Output/PowerPoint_Figures/`):**
1. `generate_5x5_individual.py` — Generates 25 individual high-DPI images per response type
2. `build_5x5_slides.py` — Assembles them into PowerPoint slides with colorbar

**Purpose:** Generate 25 individual 3D surface plots at 600 DPI, then assemble into a 5x5 grid in PowerPoint for publication.

**Key Features:**
- 25 separate images per response type (not one combined figure)
- Generates both **with-titles** and **no-titles** (`_NoTitles`) variants
- Only edge plots have axis labels/ticks:
  - **Left column (col 0):** Z-axis label + tick labels
  - **Right column (col 4):** X-axis label (Time) + tick labels
  - **Bottom row (row 4):** Y-axis label (Dose Ratio) + tick labels
- Z-axis label uses `ax.text2D()` (not `ax.set_zlabel()`) so `bbox_inches='tight'` captures it
- Tight image padding: `pad_inches=0.02` + PIL adds 0.08" extra on left only
- Title uses `ax.text2D(0.5, 0.97, ...)` to sit directly on the wireframe top
- Figure size: `figsize=(7, 7.5)` — slightly wider for Z-axis room
- Font sizes: TITLE=28, LABEL=24, TICK=20 (large for readability at 1.22" in PowerPoint)
- Transparent backgrounds (RGBA) for flexible PowerPoint composition

**Tick Formatting:**
- Values < 0.1: `:.2f` (e.g., 0.01, 0.02, ... for contractility)
- Values >= 0.1: `:.1f` (e.g., 10, 20, ... for O2)
- Integer values shown without decimals

**Color Scaling:**
- O2: Display cap at 35, actual max ~50 (values >35 shown as red)
- Contractility: Display cap at 0.04, actual max ~0.069 (values >0.04 shown as red)
- Extended colormap: turbo with solid red for values above cap

**Usage:**
```bash
cd "Output/PowerPoint_Figures"
python generate_5x5_individual.py   # Step 1: generate images + colorbars
python build_5x5_slides.py          # Step 2: assemble into PowerPoint
```

**Outputs:**
- `Output/PowerPoint_Figures/Fig_4/O2_5x5_Individual/` — 25 O2 images (with titles)
- `Output/PowerPoint_Figures/Fig_4/O2_5x5_Individual_NoTitles/` — 25 O2 images (no titles)
- `Output/PowerPoint_Figures/Fig_5/Contractility_5x5_Individual/` — 25 Contractility images (with titles)
- `Output/PowerPoint_Figures/Fig_5/Contractility_5x5_Individual_NoTitles/` — 25 Contractility images (no titles)
- `Output/PowerPoint_Figures/Fig_4/O2_colorbar_600dpi.png`
- `Output/PowerPoint_Figures/Fig_5/Contractility_colorbar_600dpi.png`
- `Output/PowerPoint_Figures/Cardiac_RODEO_Tracked.pptx` — Slides 4-5

**Legacy combined image script:** `generate_5x5_grids.py` (generates single combined PNG, not used for PowerPoint)

## Environment Setup

```powershell
# Install dependencies
python -m pip install pandas numpy scikit-learn xgboost joblib openpyxl matplotlib seaborn shap ipykernel jupyter

# Launch Jupyter
python -m jupyter notebook

# Run interactive plotter
python interactive_pkpd_elimination_plotter.py
```

## Common Pitfalls

| Problem | Solution |
|---------|----------|
| Forgetting `header=1` or `.str.strip()` | Always use both when loading Excel |
| Data filtering cells overwrite `df_raw` | Mark filtering cells OPTIONAL; preview first |
| NaN/Inf in coefficients | Filter before plotting/training |
| Using `.iloc[idx]` with labeled indices | Use `.loc[idx]` for drug name indices |
| High-resolution grids consume memory | Reduce grid resolution for aggregated statistics |

## Output Directory Structure

Each output folder contains a `README.txt` describing its contents:
- `Output/Model_Properties/` - Trained models (`*.joblib`)
- `Output/Performance_Metrics/` - CV scores, confusion matrices
- `Output/ROC_Data/` - ROC curves
- `Output/SHAP_Data/` - Feature importance
- `Output/Equation_Fitting/` - Coefficient CSVs
- `Output/3D_Plots/`, `Output/2D_Plots/` - Surface visualizations
- `Output/LaTeX_Reports/` - PDF reports
- `Output/ADMET_Comparison/` - ADMET analysis
- `Output/PowerPoint_Figures/` - Publication figures with tracking

## Figure Tracking System

All publication figures are tracked with full data provenance:

**Key Files:**
- `Output/PowerPoint_Figures/figure_registry.csv` - Master tracking of all figures
- `Output/PowerPoint_Figures/FIGURE_CHANGE_LOG.md` - Change history and data sources
- `Output/PowerPoint_Figures/Cardiac_RODEO_Tracked.pptx` - PowerPoint with linked figures

**Figure Generation:**
```bash
python generate_paper_figures.py --all    # All figures
python generate_paper_figures.py --figure 7   # Specific figure
```

**Figure Style Conventions:**
- **ROC comparison graphs**: Organoid is always **green** (`#2ca02c`) and **first in the legend**. Consistent across all figures (arrhythmia, heart damage, etc.)
- **ROC comparison colors**: CNN DIQT=red (`#d62728`), CNN 5-fold=purple (`#9467bd`), ADMET-AI DICTrank=blue (`#1f77b4`), SwissADME DICTrank=orange (`#ff7f0e`), ADMET-AI Scaffold=purple (`#9467bd`), SwissADME Scaffold=red (`#d62728`)
- **Y-axis on AUC plots**: Always label as "AUC ROC" (not just "AUC")
- **Confusion matrices**: Percentages in parentheses, e.g. `73\n(66.4%)`
- **Scatter plot X-axis**: Split long labels across 2 lines to prevent overlap, e.g. `'Coefficient of\nDetermination (R²)'`

**Data Tracking Requirements:**
1. Each figure has a corresponding `*_data.xlsx` file
2. Excel files include `Source` column with original file path
3. Save FULL source data, not just plotted subsets
4. ROC curves include `TPR_Lower`/`TPR_Upper` for confidence bands
5. `figure_registry.csv` tracks the generating script for each figure

**Registry Columns:**
| Column | Description |
|--------|-------------|
| Figure_ID | Figure number (1, 2, S1, etc.) |
| Letter | Panel letter (a, b, c) |
| PNG_Path | Path to generated figure |
| Excel_Path | Path to data file for recreation |
| Source_Script | Script that generates the figure |
| Notes | Additional context |
