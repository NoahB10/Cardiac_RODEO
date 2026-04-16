# 3D Pharmacodynamic Modeling for Organoid Drug Screening

## Overview

This repository contains tools for modeling 3D pharmacodynamic responses in organoid drug screening experiments. The models capture the relationship between **time**, **concentration** (normalized by Cmax), and **response** (O2 consumption or amplitude variability).

## Data Structure

The data consists of:
- **Time points**: Hours after drug induction (0, 7, 12, 14, 16, ...)
- **Concentrations**: Drug concentrations in µM (normalized by Cmax for cross-drug comparison)
- **Responses**: 
  - `O2_mean.csv`: Mean oxygen consumption values
  - `Amp_std.csv`: Standard deviation of heart rate amplitude

## Model Equation

The primary model used is a **Hill Equation with Time-Dependent Exponential Decay**:

```
R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * exp(-k*t)
```

Where:
- **R(t,C)**: Response at time t and concentration C
- **R0**: Baseline response (initial/control response)
- **Rmax**: Maximum achievable response
- **EC50**: Concentration at half-maximal effect (normalized by Cmax)
- **n**: Hill coefficient (sigmoidicity/slope of dose-response curve)
- **k**: Time decay constant (rate of response change over time)

### Model Components

1. **Concentration Component** (Hill Equation):
   ```
   Hill(C) = Cⁿ / (EC50ⁿ + Cⁿ)
   ```
   - Models sigmoidal dose-response relationship
   - EC50 represents the concentration where 50% of maximum effect is achieved
   - n controls the steepness of the curve

2. **Time Component** (Exponential Decay):
   ```
   Time(t) = exp(-k*t)
   ```
   - Models time-dependent decay or growth of response
   - k > 0: Response decays over time (e.g., organoid death)
   - k < 0: Response increases over time (e.g., delayed toxicity)

3. **Combined Model**:
   - Separable model where concentration and time effects multiply
   - Captures both dose-response and kinetic behavior

## Alternative Models

The script also includes alternative model formulations:

1. **Time Growth Model**: `R(t,C) = R0 + (Rmax - R0) * Hill(C) * [1 - exp(-k*t)]`
   - For gradual onset of effects over time

2. **Separable Response Surface**: More flexible separable formulation with time half-life parameter

## Usage

### Basic Usage

```python
python model_3d_pharmacodynamics.py
```

This will:
1. Load all drug data from subdirectories
2. Normalize concentrations by Cmax values
3. Fit the 3D model to each drug-response pair
4. Generate visualizations
5. Save parameter summary to CSV

### Outputs

- **Visualizations**: `model_visualizations/[Drug]_[ResponseType]_3d_model.png`
  - 3D surface plot
  - Contour map
  - Concentration-response curves at different time points

- **Summary**: `model_parameters_summary.csv`
  - Fitted parameters for all drugs
  - R² values for model fit quality

## Parameter Interpretation

### R0 (Baseline Response)
- Initial response before drug effects
- Should approximate control/zero concentration response

### Rmax (Maximum Response)
- Maximum achievable response at high concentrations
- May differ from R0 if drug enhances or suppresses response

### EC50 (Half-Maximal Effect Concentration)
- Normalized by Cmax (unitless: C/Cmax)
- Values near 1.0 indicate effect at therapeutic concentrations
- Values < 0.1 indicate high potency
- Values > 10 indicate low potency

### n (Hill Coefficient)
- Steepness of dose-response curve
- n = 1: Standard hyperbolic curve
- n > 1: Steeper curve (cooperative binding)
- n < 1: Shallower curve

### k (Time Decay Constant)
- Rate of response change over time (hours⁻¹)
- Positive k: Response decreases over time (toxicity/death)
- Negative k: Response increases over time (delayed effects)
- Larger |k|: Faster changes

## Model Selection Criteria

- **R² > 0.7**: Good fit
- **R² > 0.9**: Excellent fit
- **R² < 0.5**: Consider alternative models or check data quality

## Normalization by Cmax

Concentrations are normalized by Cmax (maximum plasma concentration) to:
- Enable cross-drug comparison
- Relate in-vitro concentrations to in-vivo therapeutic levels
- Identify drugs with effects at clinically relevant concentrations

## Future Enhancements

- Multiple drug combination modeling
- Time-delayed effects modeling
- Non-separable models (interaction terms)
- Bayesian parameter estimation
- Confidence interval visualization

