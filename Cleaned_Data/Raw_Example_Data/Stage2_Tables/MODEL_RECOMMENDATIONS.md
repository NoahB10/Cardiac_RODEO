# 3D Pharmacodynamic Modeling Recommendations for Organoid Drug Screening

## Current Situation Analysis

Based on your existing model parameters, the current **Hill Equation with Exponential Decay** model shows:
- **R² values**: 0.001 - 0.676 (mostly low, indicating poor fit)
- **Issues identified**:
  1. Exponential decay may not capture organoid death dynamics well
  2. Some drugs show extremely small EC50 values (near zero), suggesting threshold effects
  3. Very high Rmax values (e.g., Vorinostat: 3462) indicate model instability
  4. Simple separable models may miss concentration-time interactions

## Recommended Model Improvements

### **Model 1: Logistic Decay Model** ⭐ **RECOMMENDED AS PRIMARY**

```
R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * [1 / (1 + exp(k*(t - t50)))]
```

**Why this is better:**
- **Logistic decay** is more realistic for organoid death/toxicity than exponential
- Logistic function provides S-shaped time response (slow onset, rapid middle phase, slow decay)
- Better captures the sigmoidal nature of biological death processes
- Still separable, making it interpretable and easier to fit

**Parameters:**
- `R0`: Baseline response
- `Rmax`: Maximum response
- `EC50`: Concentration at half-maximal effect (normalized by Cmax)
- `n`: Hill coefficient (sigmoidicity)
- `k`: Time decay rate (positive = decay, negative = growth)
- `t50`: Time at which response reaches 50% of maximum change

**Best for:** Most drugs showing gradual decline over time

---

### **Model 2: Threshold + Logistic Decay Model**

```
R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * [1 / (1 + exp(k*(t - t50)))] * H(C - Cthresh)
```

**Why this helps:**
- Many drugs show **no effect below a certain concentration threshold**
- Your data shows some drugs with EC50 ≈ 0, suggesting threshold behavior
- Heaviside step function `H(C - Cthresh)` enforces minimum concentration requirement

**Parameters:**
- All from Model 1, plus:
- `Cthresh`: Minimum concentration for any effect (normalized by Cmax)

**Best for:** Drugs with apparent threshold effects

---

### **Model 3: Interactive Response Surface Model** (Non-Separable)

```
R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * 
         [1 / (1 + exp(k_t*(t - t50) + k_c*c + k_interaction*t*c))]
```

**Why this is important:**
- **Allows concentration-time interactions** (non-separable model)
- Captures cases where time-dependent decay depends on concentration
- Higher concentrations may decay faster/slower than lower ones
- More flexible, though harder to interpret

**Parameters:**
- `k_t`: Time decay coefficient
- `k_c`: Concentration-dependent time adjustment
- `k_interaction`: Interaction term (t × c)

**Best for:** Drugs where decay rate depends on concentration

---

### **Model 4: Delayed Onset + Logistic Decay Model**

```
R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * 
         [1 / (1 + exp(k*(t - t50 - t_delay)))] * H(t - t_delay)
```

**Why this matters:**
- Some drugs show **delayed onset** of effects
- Organoids may have latency period before responding
- Models time-delayed toxicity/death

**Parameters:**
- All from Model 1, plus:
- `t_delay`: Delay time before effects begin (hours)

**Best for:** Drugs with noticeable latency in response

---

### **Model 5: Weibull Survival Model**

```
R(t,C) = R0 + (Rmax - R0) * [Cⁿ / (EC50ⁿ + Cⁿ)] * exp(-(t/λ)^k * (1 + α*c))
```

**Why this is valuable:**
- **Weibull distribution** is standard in survival/toxicity analysis
- Flexible shape parameter allows various decay patterns
- Concentration modifies the survival time scale
- Well-established in toxicology literature

**Parameters:**
- `λ` (lambda_scale): Scale parameter (time units)
- `k` (k_shape): Shape parameter (flexibility)
- `α` (alpha): Concentration-dependent survival modifier

**Best for:** Drugs with survival-like decay patterns

---

## Model Selection Strategy

### Step 1: Start with Logistic Decay (Model 1)
- Fit Model 1 to all drugs
- Calculate R² for each

### Step 2: Identify Poor Fits (R² < 0.5)
- Fit Models 2-5 to poorly fitting drugs
- Compare AIC/BIC or use cross-validation

### Step 3: Model Comparison
For each drug, compare:
- **R²**: Goodness of fit
- **AIC**: Penalized by model complexity (lower is better)
- **RMSE**: Prediction error
- **Visual inspection**: Does the model capture data patterns?

### Step 4: Final Selection
- Choose model with best balance of fit quality and interpretability
- Prefer simpler models when R² difference < 0.05

---

## Parameter Interpretation Guide

### Concentration Parameters (C/Cmax normalized)

**EC50 (Normalized):**
- **< 0.1**: Very potent (effect at << Cmax)
- **0.1 - 1.0**: Therapeutic range (effect near Cmax)
- **1.0 - 10.0**: Moderate potency
- **> 10.0**: Low potency (requires >> Cmax)

**n (Hill Coefficient):**
- **< 1**: Shallow dose-response (cooperative inhibition)
- **= 1**: Standard hyperbolic
- **> 1**: Steep dose-response (cooperative binding)
- **>> 1**: All-or-nothing response

### Time Parameters

**k (Decay Rate):**
- **Positive**: Response decreases over time (toxicity/death)
- **Negative**: Response increases over time (delayed effects)
- **Magnitude**: Rate of change (higher = faster)

**t50 or λ (Time Scale):**
- Time at which response reaches 50% change
- Lower = faster effects
- Higher = slower effects

---

## Implementation Recommendations

### 1. **Normalize Concentrations by Cmax** ✅ (You're already doing this)
- Enables cross-drug comparison
- Relates in-vitro to in-vivo concentrations
- EC50 values are unitless (C/Cmax)

### 2. **Robust Fitting**
- Use multiple initial guesses
- Try both `curve_fit` and `differential_evolution`
- Implement bounds checking
- Handle edge cases (near-zero concentrations, missing data)

### 3. **Model Validation**
- **Cross-validation**: Split time points or concentrations
- **Leave-one-out**: Test prediction on held-out data
- **Bootstrap**: Resample data to estimate parameter confidence intervals

### 4. **Visualization**
- 3D surface plots
- Contour maps
- Time slices (concentration-response at fixed times)
- Concentration slices (time-response at fixed concentrations)

### 5. **Quality Control**
- Remove outliers (> 3 standard deviations)
- Handle missing data appropriately
- Check for numerical stability
- Validate parameter bounds

---

## Expected Improvements

### With Logistic Decay Model:
- **R² improvements**: Expected 0.1-0.3 increase for most drugs
- **Better capture of death dynamics**: More realistic S-shaped time response
- **Improved stability**: Fewer extreme parameter values

### With Threshold Model:
- **Better fit for low-EC50 drugs**: Captures threshold behavior explicitly
- **Biological interpretation**: Minimum effective concentration

### With Interactive Model:
- **Better fit for complex drugs**: Captures concentration-dependent decay rates
- **More realistic**: Higher concentrations may have different kinetics

---

## Next Steps

1. **Run the improved model script** (`improved_3d_models.py`)
   ```bash
   python improved_3d_models.py
   ```

2. **Compare results**:
   - Check `model_comparison_summary.csv`
   - Review visualizations in `model_visualizations_improved/`
   - Identify best model for each drug

3. **Select final models**:
   - For each drug, choose model with highest R² (if > 0.5)
   - Document model selection rationale

4. **Validate selected models**:
   - Cross-validation on held-out data
   - Check prediction on new time points/concentrations

5. **Interpret parameters**:
   - Compare EC50 values across drugs
   - Identify most/least potent drugs
   - Understand time dynamics

---

## Biological Interpretation Examples

### High Potency Drug (EC50 < 0.1 × Cmax)
- **Example**: If Cmax = 1 µM and EC50 = 0.01 (normalized), actual EC50 ≈ 0.01 µM
- **Interpretation**: Very potent, effects at sub-therapeutic concentrations
- **Clinical relevance**: Risk of toxicity at therapeutic doses

### Therapeutic Range Drug (EC50 ≈ 1.0 × Cmax)
- **Example**: If Cmax = 1 µM and EC50 = 1.0 (normalized), actual EC50 ≈ 1 µM
- **Interpretation**: Effects occur at therapeutic concentrations
- **Clinical relevance**: Good therapeutic window

### Low Potency Drug (EC50 > 10 × Cmax)
- **Example**: If Cmax = 1 µM and EC50 = 10 (normalized), actual EC50 ≈ 10 µM
- **Interpretation**: Requires very high concentrations
- **Clinical relevance**: May not show effects at therapeutic doses

### Time Dynamics
- **Fast decay (k > 0.1, t50 < 24h)**: Rapid organoid death
- **Slow decay (k < 0.01, t50 > 48h)**: Gradual decline
- **Growth (k < 0)**: Delayed toxicity or adaptation

---

## Code Usage

```python
from improved_3d_models import (
    model_logistic_decay,
    model_threshold_logistic,
    fit_model_robust,
    load_drug_data
)

# Load data
time_data, conc_data, response_data, drug_name = load_drug_data(
    'Troglitazone', cmax_dict, 'O2_mean'
)

# Fit logistic decay model
params, pcov = fit_model_robust(
    time_data, conc_data, response_data,
    model_logistic_decay
)

# Predict
predictions = model_logistic_decay(params, time_data, conc_data)
```

---

## Questions to Consider

1. **Do all drugs show similar time dynamics?**
   - Compare `k` and `t50` values across drugs
   - Group drugs by decay patterns

2. **Are there concentration thresholds?**
   - Check if threshold model improves fit
   - Identify minimum effective concentrations

3. **Do high concentrations decay faster?**
   - Use interactive model if concentration affects decay rate
   - Compare decay parameters at different concentrations

4. **Is there delayed onset?**
   - Check if delayed model improves fit
   - Identify drugs with latency periods

---

## References

- **Hill Equation**: Standard dose-response modeling
- **Logistic Function**: Biological growth/decay modeling
- **Weibull Distribution**: Survival analysis in toxicology
- **Pharmacokinetic/Pharmacodynamic (PK/PD) Modeling**: Standard in drug development

---

## Support

For issues or questions:
1. Check model fit quality (R² > 0.5 is good)
2. Review parameter bounds (may need adjustment)
3. Try different initial guesses
4. Check data quality (outliers, missing values)

