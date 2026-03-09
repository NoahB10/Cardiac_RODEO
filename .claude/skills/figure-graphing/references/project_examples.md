# Project-Specific Figure Examples

## MoLFormer Comparison Figures

### Location
- Scripts: `MoLFormer_Comparison/Scripts/generate_comparison_figures.py`
- Output: `Output/MoLFormer_Comparison/figures/`

### Models Being Compared
```python
models = ['CNN (DIQT Transfer)', 'CNN (5-fold on 25)', 'Organoid (5-fold)']
colors = {
    'CNN (DIQT Transfer)': '#E91E63',   # Pink
    'CNN (5-fold on 25)': '#9C27B0',    # Purple
    'Organoid (5-fold)': '#4CAF50',     # Green
}
```

### Data Sources
```python
# CNN DIQT Transfer predictions
cnn_diqt = pd.read_csv('Output/MoLFormer_Comparison/molformer_cnn_predictions_25.csv')
# Columns: Drug, CNN_prob, CNN_pred

# CNN 5-fold on 25 drugs predictions
cnn_25 = pd.read_csv('Output/MoLFormer_Comparison/molformer_cnn_25drugs_cv.csv')
# Columns: Drug, Arrhythmia_label, CNN_25_prob, CNN_25_pred

# Organoid predictions
organoid = pd.read_csv('Output/Prediction_Scatter_Data/arrhythmia_predictions.csv')
# Columns: Drug, Predicted_Arrhythmia_pct, Actual_Arrhythmia

# Organoid 5-fold CV metrics
stage2 = pd.read_csv('Output/Performance_Metrics/stage2_results_5fold.csv')
# Filter: Target=='Arrhythmia', N_Folds==5
# Columns: Accuracy, AUC, F1, MCC
```

## ADMET Comparison Figures

### Location
- Scripts: `ADMET_Comparison/Scripts/full_analysis.py`
- Output: `Output/ADMET_Comparison/`

### Models Being Compared
```python
models = ['ADMET-AI', 'SwissADME', 'Organoid']
colors = {
    'ADMET-AI': '#2196F3',    # Blue
    'SwissADME': '#FF9800',   # Orange
    'Organoid': '#4CAF50',    # Green
}
```

## Organoid Model Figures

### Location
- Notebook: `Prediction_Models/Prediction_Models_AR_HD_Concern.ipynb`
- Output: `Output/` (various subdirectories)

### Targets
```python
targets = ['Arrhythmia', 'heart_damage', 'Concern_Binary']
```

### Feature Data Source
```python
# Load coefficients
df = pd.read_excel('EQN_Coefficients/all_equations_coefficients.xlsx',
                   sheet_name='pkpd_elimination', header=1)
df.columns = df.columns.str.strip()

# 14 features: 7 Contractility + 7 O2
features = ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim',
            'R0.1', 'Emax.1', 'kappa.1', 'n.1', 'm.1', 'tau.1', 'k_elim.1']
```

## 3D Surface Plots (PK-PD)

### Location
- Notebook: `Paper_Plots_PKPD_Elimination_Surfaces.ipynb`
- Output: `Output/3D_Plots/`

### Standard View Angle
```python
ax.view_init(elev=25, azim=-158)
```

### Axis Ranges
```python
time = np.linspace(0, 96, 50)      # X: Time (hours)
dose_ratio = np.linspace(0, 2, 50) # Y: C0/Cmax
# Z: Response (Contractility or O2)
```

### Colorbar Settings
```python
# Contractility
vmin, vmax = 0, 0.2

# O2
vmin, vmax = 5, 25
```

## SHAP Feature Importance

### Location
- Output: `Output/SHAP_Data/`

### Plot Type
```python
import shap

# Bar plot
shap.summary_plot(shap_values, X, plot_type='bar', show=False)

# Beeswarm plot
shap.summary_plot(shap_values, X, show=False)
```

## LaTeX Integration

### Figure Inclusion Pattern
```latex
\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{../MoLFormer_Comparison/figures/figure_name.pdf}
\caption{Description of what the figure shows.}
\end{figure}
```

### Side-by-Side Figures
```latex
\begin{figure}[H]
\centering
\begin{minipage}{0.48\textwidth}
\centering
\includegraphics[width=\textwidth]{../path/figure1.pdf}
\end{minipage}
\hfill
\begin{minipage}{0.48\textwidth}
\centering
\includegraphics[width=\textwidth]{../path/figure2.pdf}
\end{minipage}
\caption{Combined caption for both figures.}
\end{figure}
```

## Metric Calculations

### From Confusion Matrix
```python
from sklearn.metrics import accuracy_score, f1_score, matthews_corrcoef

accuracy = accuracy_score(y_true, y_pred)
f1 = f1_score(y_true, y_pred)
mcc = matthews_corrcoef(y_true, y_pred)

# From confusion matrix values
# cm = [[TN, FP], [FN, TP]]
sensitivity = TP / (TP + FN)  # Recall
specificity = TN / (TN + FP)
precision = TP / (TP + FP)
```

### Bootstrap AUC with Confidence Interval (for shaded bands)

**MANDATORY: All ROC curves must have shaded confidence bands using `fill_between`.**

```python
from sklearn.metrics import roc_auc_score, roc_curve, auc
import numpy as np

def bootstrap_roc_with_bands(y_true, y_prob, n_boot=300, seed=42):
    """
    Bootstrap ROC for shaded confidence bands.

    Returns mean_fpr, mean_tpr, std_tpr (for fill_between), auc_mean, auc_std
    """
    rng = np.random.default_rng(seed)
    y_true, y_prob = np.asarray(y_true), np.asarray(y_prob)
    n = len(y_true)
    mean_fpr = np.linspace(0, 1, 100)
    tprs, aucs = [], []

    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        fpr, tpr, _ = roc_curve(y_true[idx], y_prob[idx])
        tpr_interp = np.interp(mean_fpr, fpr, tpr)
        tpr_interp[0] = 0.0
        tprs.append(tpr_interp)
        aucs.append(auc(mean_fpr, tpr_interp))

    tprs = np.array(tprs)
    return mean_fpr, tprs.mean(axis=0), tprs.std(axis=0), np.mean(aucs), np.std(aucs)

# MANDATORY: Plot with shaded band
mean_fpr, mean_tpr, std_tpr, auc_mean, auc_std = bootstrap_roc_with_bands(y_true, y_prob)

ax.plot(mean_fpr, mean_tpr, color=color, lw=2, label=f'Model (AUC={auc_mean:.2f}±{auc_std:.2f})')
ax.fill_between(mean_fpr,
                np.maximum(mean_tpr - std_tpr, 0),  # Lower bound
                np.minimum(mean_tpr + std_tpr, 1),  # Upper bound
                color=color, alpha=0.2)
```
