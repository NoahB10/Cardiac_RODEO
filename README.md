# Cardiac RODEO

A machine learning project for predicting cardiac outcomes using PK-PD elimination equation coefficients.

## Project Overview

This repository contains models and analysis for cardiac organoid research, focusing on:
- **Arrhythmia prediction** (binary classification)
- **Cardiotoxicity prediction** (binary classification)
- **Concern level prediction** (multiclass: most/less/no)

The models use XGBoost and are trained on PK-PD elimination equation coefficients.

## Project Structure

```
Cardiac_RODEO/
├── Cleaned_Data/              # Processed experimental data
│   ├── DrugScreen19.11.25_compiled_Amp_std.xlsx
│   ├── DrugScreen19.11.25_compiled_O2_mean.xlsx
│   ├── Heart_Contractility_Averaged.xlsx
│   ├── O2_Mean_Averaged.xlsx
│   └── organoid_sizes_all_plates_Data.xlsx
├── EQN_Coefficients/          # Equation coefficients
│   └── all_equations_coefficients.xlsx
├── Output/                    # Generated outputs
│   ├── 2D_Plots/
│   ├── 3D_Plots/
│   └── Model_Properties/
└── Prediction_Models/         # Jupyter notebooks for model training
    ├── Prediction_Models_AR_HD_Concern.ipynb
    └── Paper_Plots_PKPD_Elimination_Surfaces.ipynb
```

## Requirements

- Python 3.x
- pandas
- numpy
- scikit-learn
- xgboost
- joblib
- openpyxl
- matplotlib
- ipykernel
- jupyter

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd Cardiac_RODEO
```

2. Install required packages:
```bash
pip install pandas numpy scikit-learn xgboost joblib openpyxl matplotlib ipykernel jupyter
```

Or install from a requirements file (if available):
```bash
pip install -r requirements.txt
```

## Usage

Open the Jupyter notebooks in the `Prediction_Models/` directory:

- `Prediction_Models_AR_HD_Concern.ipynb`: Trains XGBoost models for arrhythmia, cardiotoxicity, and concern level predictions
- `Paper_Plots_PKPD_Elimination_Surfaces.ipynb`: Generates publication-quality plots

## Data

The `Cleaned_Data/` folder contains processed experimental data from cardiac organoid studies, including:
- Drug screening results
- Heart contractility measurements
- Oxygen consumption data
- Organoid size measurements

## Output

Generated plots and model properties are saved in the `Output/` directory.

## License

[Add your license information here]

## Authors

[Add author information here]

