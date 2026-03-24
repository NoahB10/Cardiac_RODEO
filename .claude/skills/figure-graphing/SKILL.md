---
name: figure-graphing
description: "Create publication-quality figures and graphs for scientific analysis. Use when creating bar charts, ROC curves, confusion matrices, scatter plots, heatmaps, 3D surface plots, or any data visualization. Supports PDF and PNG output with consistent styling."
---

# Figure Graphing Skill

Create publication-quality figures for scientific papers and reports.

## Automatic PowerPoint Sync

**IMPORTANT:** When generating figures using `generate_paper_figures.py`, the PowerPoint is **automatically updated**:

```bash
# Generate figure and auto-update PowerPoint
python generate_paper_figures.py --figure 3

# Skip PowerPoint update (figures only)
python generate_paper_figures.py --figure 3 --no-pptx
```

The script automatically:
1. Generates figure PNGs to `Output/PowerPoint_Figures/Fig_X/`
2. Unpacks `Output/PowerPoint_Figures/Cardiac_RODEO_Tracked.pptx`
3. Copies updated images to the correct media slots
4. Repacks the PowerPoint

**Figure-to-Image Mapping:**

**Slide 2 (Fig 2) — Runtime Panel Discovery (NOT hardcoded rIds):**
Slide 2 uses named groups `Panel_2a` through `Panel_2l` in the PPTX.
The script discovers rIds at runtime by parsing group names — this survives
PowerPoint re-saves that renumber rIds. Defined in `SLIDE2_PANEL_MAP`:

| Panel | Filename in Fig_2/ | Description |
|-------|-------------------|-------------|
| a–f | *external* | Not replaced (plate photo, microscopy, diagrams) |
| d | `Fig_2i.png` | SNR Quality Analysis |
| g | `Fig_2_Epirubicin_O2.png` | Metabolic Dose Dependent Response (averaged) |
| h | `Fig_2_Epirubicin_TC50.png` | Epirubicin TC50 (32h) |
| i | `Fig_2_Epirubicin_O2_heatmap.png` | Epirubicin O2 heatmap (LOWESS w=16) |
| j | `Fig_2_Mexiletine_Contractility.png` | Mexiletine Contractility 2D dose-response |
| k | `Fig_2k_Mexiletine_Waveforms.png` | Mexiletine heart rate waveforms (48h) |
| l | `Fig_2_Mexiletine_Contractility_heatmap.png` | Mexiletine Contractility heatmap |

To change which image goes to which panel, edit `SLIDE2_PANEL_MAP` in
`generate_paper_figures.py`. The key is the panel letter, the value is the
filename (relative to `Output/PowerPoint_Figures/Fig_2/`).

Slide 2 is in `MANUAL_GROUP_SLIDES` — the script does NOT auto-group/label
this slide. Panel groups and labels are managed manually in PowerPoint.
The `_discover_slide2_rids()` function handles the rId lookup.

**Other slides — position-based or explicit rId mapping:**
| Figure | PowerPoint Images | Slide |
|--------|------------------|-------|
| Fig_3 (a-e) | SLIDE3_RID_MAP (explicit) | 3 |
| Fig_6 (a-h) | position-based | 6 |
| Fig_7 (a-h) | position-based | 7 |
| Fig_8 (a-f) | position-based | 8 |

**CRITICAL — Cross-Slide Panel Alignment (Figures 6, 7, 8):**
Figures 6, 7, and 8 show the same panel layout (a–f) for different drug categories
(Arrhythmia+HeartDamage, ADMET comparison, SwissADME comparison). Panels a–f MUST
be at identical positions across all three slides so they align when flipping between pages.

Reference positions (from Fig 7, the canonical source):
| Panel | x | y | w | h |
|-------|------|------|------|------|
| a | 0.30 | 0.80 | 1.70 | 1.70 |
| b | 2.15 | 0.80 | 1.70 | 1.70 |
| c | 4.00 | 0.80 | 1.70 | 1.70 |
| d | 0.30 | 2.65 | 1.55 | 1.87 |
| e | 2.00 | 2.65 | 2.47 | 1.78 |
| f | 0.30 | 4.67 | 3.40 | 1.70 |

When regenerating or repositioning panels on slides 6–8, always use these exact
positions. Extract and verify from the PPTX directly (not just slide_layout.json)
since manual edits in PowerPoint can introduce sub-pixel drift.

## Quick Reference

### Standard Figure Types
1. **Bar Charts** - Accuracy, AUC, metric comparisons (always with error bars)
2. **Grouped Bar Charts** - Multiple metrics per model (always with error bars)
3. **ROC Curves** - MUST have shaded confidence bands (bootstrap ±1 std, use `fill_between`)
4. **Confusion Matrices** - With counts and percentages (`Blues` cmap)
5. **Scatter Plots** - Per-drug/per-sample predictions
6. **Heatmaps** - Correlation (`RdBu_r`), performance (`RdYlGn`), SHAP (`coolwarm`)
7. **Threshold Analysis** - Horizontal scatter, drugs on Y-axis, green/red colors
8. **3D Surface Plots** - PK-PD response surfaces
9. **SHAP Aligned Pairs** - Positive/negative SHAP paired by magnitude, blue/grey colors
10. **Accuracy vs AUC Scatter** - X=Accuracy, Y=AUC, comparing equations across ML models

## Color Palettes

### Primary Color Palette (MANDATORY)
**Use these colors consistently across ALL figures:**
```python
PRIMARY_COLORS = {
    'beige': '#E3D5B2',      # Warm neutral - backgrounds, secondary elements
    'blue': '#6C92ED',       # Primary accent - main data series
    'pink': '#ECA0C0',       # Secondary accent - comparison data
    'orange': '#F8B274',     # Tertiary accent - highlights
}

# Extended palette (same theme)
EXTENDED_COLORS = {
    'dark_blue': '#4A6FBF',  # Darker blue for emphasis
    'light_pink': '#F5C6D6', # Lighter pink for fills
    'coral': '#E89B7A',      # Warm coral
    'sage': '#A8C4A2',       # Muted green
    'lavender': '#B8A9D9',   # Soft purple
    'cream': '#F5EFE0',      # Light background
}
```

### Model Comparison Colors
```python
colors = {
    'CNN (DIQT Transfer)': '#ECA0C0',   # Pink
    'CNN (5-fold on 25)': '#6C92ED',    # Blue
    'Organoid (5-fold)': '#F8B274',     # Orange
    'ADMET-AI': '#6C92ED',              # Blue
    'SwissADME': '#ECA0C0',             # Pink
}
```

### Metric Colors
```python
metric_colors = {
    'Accuracy': '#6C92ED',    # Blue
    'F1 Score': '#F8B274',    # Orange
    'MCC': '#ECA0C0',         # Pink
    'AUC': '#4A6FBF',         # Dark Blue
    'Sensitivity': '#E89B7A', # Coral
    'Specificity': '#A8C4A2', # Sage
}
```

### Equation Colors (Rainbow by R² Rank — Fig 3c)
Used in the R² comparison bar chart and any figure referencing equations by name.
Colors are assigned in rainbow order from best R² (red) to worst (pink).

```python
EQUATION_COLORS = {
    'Dual Exponential':     '#d62728',  # Red
    'Hormesis Hill':        '#e6550d',  # Red-Orange
    'PKPD Elimination':     '#ff7f0e',  # Orange
    'Biphasic Response':    '#ffc107',  # Amber
    'Dual Hill Hormesis':   '#8bc34a',  # Yellow-Green
    'Modified Hill':        '#2ca02c',  # Green
    'Adaptive Response':    '#00897b',  # Teal
    'Gaussian Ridge':       '#17becf',  # Cyan
    'Bivariate Gaussian':   '#1f77b4',  # Blue
    'Gaussian-Hill Hybrid': '#5c6bc0',  # Indigo
    'Recovery Model':       '#9467bd',  # Purple
    'Cumulative Exposure':  '#e377c2',  # Pink
}

# Internal code names → display names
EQUATION_DISPLAY_NAMES = {
    'dual_exponential':      'Dual Exponential',
    'bivariate_gaussian':    'Bivariate Gaussian',
    'gaussian_hill_hybrid':  'Gaussian-Hill Hybrid',
    'modified_hill_hormesis':'Hormesis Hill',
    'gaussian_ridge':        'Gaussian Ridge',
    'adaptive_response':     'Adaptive Response',
    'biphasic_response':     'Biphasic Response',
    'cumulative_exposure':   'Cumulative Exposure',
    'recovery_model':        'Recovery Model',
    'modified_hill_simple':  'Modified Hill',
    'pkpd_elimination':      'PKPD Elimination',
    'hormesis_v0':           'Dual Hill Hormesis',
}
```

### Classification Colors
```python
class_colors = {
    'Positive': '#ECA0C0',    # Pink
    'Negative': '#6C92ED',    # Blue
    'True Positive': '#6C92ED',
    'False Positive': '#F8B274',
    'True Negative': '#A8C4A2',
    'False Negative': '#E89B7A',
}
```

## Output Requirements

### CRITICAL: Size Changes Mean GRAPH Size, Not Image Canvas

**When the user asks to change figure dimensions (e.g., "make it smaller", "1.7 inches"), they mean the ACTUAL GRAPH/PLOT size, not the overall image canvas.**

**DO NOT:**
- Shrink the graph while keeping the image canvas the same size (creates wasted whitespace)
- Add padding/margins to achieve a target image size
- Scale down the plot area within a larger figure

**DO:**
- Change `figsize=(width, height)` to directly control the plot dimensions
- The graph should fill the figure with minimal margins
- Use `bbox_inches='tight'` when saving to remove excess whitespace

```python
# CORRECT: figsize controls the actual graph size
fig, ax = plt.subplots(figsize=(1.7, 1.7))  # Graph is 1.7" x 1.7"
plt.savefig('output.png', dpi=600, bbox_inches='tight')

# WRONG: Large canvas with small graph inside
fig, ax = plt.subplots(figsize=(4, 4))  # 4" canvas
ax.set_position([0.3, 0.3, 0.4, 0.4])  # Graph only 1.6" - DON'T DO THIS
```

**The `figsize` parameter IS the graph size** (plus minimal axis labels/title). When asked for "1.7 inch square", use `figsize=(1.7, 1.7)`.

### Always Save Both Formats
```python
# Save PDF for LaTeX/publication
plt.savefig('Output/path/figures/figure_name.pdf', bbox_inches='tight')
# Save PNG at 600 DPI for high-quality viewing
plt.savefig('Output/path/Figure_Name.png', dpi=600, bbox_inches='tight')
plt.close()
```

### Standard Figure Sizes
```python
# Single panel
fig, ax = plt.subplots(figsize=(8, 6))

# Side-by-side panels
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Three panels horizontal
fig, axes = plt.subplots(1, 3, figsize=(14, 4))

# Grid layout
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Wide scatter plot (per-drug)
fig, ax = plt.subplots(figsize=(16, 6))

# Default square graph (for bar charts, scatter plots, Accuracy vs AUC, etc.)
SQUARE_SIZE = 1.7  # inches - standard square panel
fig, ax = plt.subplots(figsize=(SQUARE_SIZE, SQUARE_SIZE))

# Heatmap (MANDATORY size - 1:2 ratio)
HEATMAP_HEIGHT = 1.7   # inches
HEATMAP_WIDTH = 3.4    # inches (2x height)
fig, ax = plt.subplots(figsize=(HEATMAP_WIDTH, HEATMAP_HEIGHT))

# Accuracy vs AUC scatter (use square size, same as bar charts)
fig, ax = plt.subplots(figsize=(1.7, 1.7))  # 1:1 square
# Or for 3-panel comparison with shared axis:
fig, axes = plt.subplots(1, 3, figsize=(5.1, 1.7), sharey=True)  # 3 × 1.7" width

# Bar chart (use square size)
fig, ax = plt.subplots(figsize=(1.7, 1.7))  # Standard square
```

## Common Figure Templates

### 1. Grouped Bar Chart (Accuracy, F1, MCC) with Error Bars
```python
import numpy as np
import matplotlib.pyplot as plt

models = ['Model A', 'Model B', 'Model C']
metrics = ['Accuracy', 'F1 Score', 'MCC']
# Mean values
data = np.array([
    [0.56, 0.72, 0.00],  # Model A
    [0.68, 0.73, 0.34],  # Model B
    [0.74, 0.77, 0.46],  # Model C
])
# Standard deviations (ALWAYS include error bars)
data_std = np.array([
    [0.05, 0.04, 0.00],  # Model A
    [0.03, 0.05, 0.08],  # Model B
    [0.04, 0.03, 0.06],  # Model C
])

x = np.arange(len(models))
width = 0.25
colors = ['#6C92ED', '#F8B274', '#ECA0C0']  # Use project color palette

# Use 1.7" square for single bar charts (or scale up for grouped)
SQUARE_SIZE = 1.7
fig, ax = plt.subplots(figsize=(SQUARE_SIZE * 2, SQUARE_SIZE))  # 2:1 ratio for grouped
for i, (metric, color) in enumerate(zip(metrics, colors)):
    bars = ax.bar(x + i*width - width, data[:, i], width,
                  yerr=data_std[:, i], capsize=4,  # Error bars with caps
                  label=metric, color=color, edgecolor='black')
    # Add value labels above error bars
    for j, bar in enumerate(bars):
        height = bar.get_height()
        err = data_std[j, i]
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width()/2, height + err),
                    xytext=(0, 3), textcoords='offset points',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_ylabel('Score', fontsize=9)
ax.set_title('Performance Comparison', fontsize=10, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(models, fontsize=8)
ax.tick_params(axis='both', labelsize=8)
ax.legend(loc='upper left', fontsize=8)
ax.set_ylim(0, 1.1)  # Extra space for error bars
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
```

### 2. ROC Curve with Bootstrap Confidence Bands (MANDATORY)

**CRITICAL: ALL ROC curves MUST include shaded confidence bands.** ROC curves without shaded uncertainty regions are NOT acceptable for publication figures.

**What the shaded band represents:**
- The band shows ±1 standard deviation of TPR at each FPR point
- Computed via bootstrap resampling (default: 300 iterations)
- Wider bands = more uncertainty, narrower bands = more confidence
- Band is clamped to [0, 1] range (valid probability bounds)

```python
import figure_config  # FIRST LINE - registers Helvetica
from sklearn.metrics import roc_curve, auc
import numpy as np
import matplotlib.pyplot as plt

def bootstrap_roc_stats(y_true, y_prob, n_boot=300, seed=42):
    """
    Bootstrap ROC statistics for confidence intervals.

    Returns:
        mean_fpr: Common FPR points (0 to 1, 100 points)
        mean_tpr: Mean TPR at each FPR point
        std_tpr: Standard deviation of TPR (for shaded band)
        auc_mean: Mean AUC across bootstrap samples
        auc_std: Standard deviation of AUC
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

def plot_roc_with_bands(ax, mean_fpr, mean_tpr, std_tpr, auc_val, auc_std, color, label):
    """
    Plot ROC curve with MANDATORY shaded confidence band.

    The shaded region represents ±1 std of TPR at each FPR point,
    showing the uncertainty from bootstrap resampling.
    """
    # Plot the mean ROC curve
    ax.plot(mean_fpr, mean_tpr, color=color, lw=2,
            label=f'{label} (AUC={auc_val:.2f}±{auc_std:.2f})')

    # MANDATORY: Shaded confidence band between upper and lower bounds
    lower_bound = np.maximum(mean_tpr - std_tpr, 0)  # Clamp to 0 minimum
    upper_bound = np.minimum(mean_tpr + std_tpr, 1)  # Clamp to 1 maximum

    ax.fill_between(
        mean_fpr,           # X values (FPR points)
        lower_bound,        # Lower edge of shaded region
        upper_bound,        # Upper edge of shaded region
        color=color,
        alpha=0.2,          # Semi-transparent shading
        edgecolor='none'    # No edge line on the shaded region
    )

# COMPLETE USAGE EXAMPLE
fig, ax = plt.subplots(figsize=(7, 6))

# Example: Plot ROC for multiple models
models_data = [
    ('Model A', y_true_a, y_prob_a, '#6C92ED'),  # Blue
    ('Model B', y_true_b, y_prob_b, '#ECA0C0'),  # Pink
    ('Model C', y_true_c, y_prob_c, '#F8B274'),  # Orange
]

for label, y_true, y_prob, color in models_data:
    # Compute bootstrap statistics
    mean_fpr, mean_tpr, std_tpr, auc_val, auc_std = bootstrap_roc_stats(y_true, y_prob)
    # Plot with MANDATORY shaded band
    plot_roc_with_bands(ax, mean_fpr, mean_tpr, std_tpr, auc_val, auc_std, color, label)

# Random classifier baseline (diagonal)
ax.plot([0, 1], [0, 1], 'k--', lw=1, label='Random (AUC=0.50)')

ax.set_xlabel('False Positive Rate', fontsize=9)
ax.set_ylabel('True Positive Rate', fontsize=9)
ax.set_title('ROC Curves with Confidence Bands', fontsize=10, fontweight='bold')
ax.tick_params(axis='both', labelsize=8)
ax.legend(loc='lower right', fontsize=8)
ax.set_xlim([0, 1])
ax.set_ylim([0, 1])
ax.grid(alpha=0.3)
plt.tight_layout()

# Save both formats
plt.savefig('roc_curves.pdf', bbox_inches='tight')
plt.savefig('roc_curves.png', dpi=600, bbox_inches='tight')
plt.close()
```

**Visual representation of shaded band:**
```
TPR
 1 ┤                    ╭───────── Upper bound (mean + std)
   │                 ╭──┤░░░░░░░░░
   │              ╭──┤░░░░░░░░░░░│ ← Shaded region shows uncertainty
   │           ╭──┤░░░░░░░░░░░░░│
   │        ╭──┤░░░░░░░░░░░░░░░─╯
   │     ╭──┤░░░░░░░░░░░░░░░╯     ← Mean ROC curve (solid line)
   │  ╭──┤░░░░░░░░░░░░░╯
   │╭─┤░░░░░░░░░░░░╯               Lower bound (mean - std)
 0 ┼──────────────────────────────
   0                            1  FPR
```

### 3. Confusion Matrix with Percentages

**CRITICAL Sizing Rules:**
- Use square figure size (`SQUARE_SIZE` = 1.7")
- Use `aspect='equal'` in `imshow()` to force square cells
- Margins: `left=0.18, right=0.98, top=0.85, bottom=0.18` to maximize plot area
- **DO NOT use `set_box_aspect(1)`** - it constrains plot size and wastes space

```python
import figure_config  # FIRST LINE - registers Helvetica
import numpy as np
import matplotlib.pyplot as plt

SQUARE_SIZE = 1.7  # Standard square panel size

def plot_confusion_matrix(cm, labels, title, output_path=None):
    """
    Plot confusion matrix with counts and row percentages.
    Uses square cells that fill the figure properly.
    """
    cm = np.asarray(cm, dtype=float)
    row_sums = cm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    row_pct = cm / row_sums

    # Square figure with tight margins to maximize plot area
    fig, ax = plt.subplots(figsize=(SQUARE_SIZE, SQUARE_SIZE))
    fig.subplots_adjust(left=0.18, right=0.98, top=0.85, bottom=0.18)

    # CRITICAL: Use aspect='equal' for square cells (NOT set_box_aspect)
    im = ax.imshow(cm, cmap='Blues', aspect='equal')

    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Predicted', fontsize=9)
    ax.set_ylabel('Actual', fontsize=9)

    max_val = cm.max() if cm.size else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            count = int(cm[i, j])
            pct = row_pct[i, j] * 100
            color = 'white' if max_val > 0 and cm[i, j] > max_val / 2 else 'black'
            ax.text(j, i, f"{count}\n{pct:.1f}%",
                    ha='center', va='center', color=color, fontsize=9)

    if output_path:
        plt.savefig(output_path, dpi=600, bbox_inches='tight')
        plt.close()
    return fig, ax, im
```

### 4. Per-Drug Scatter Plot
```python
fig, ax = plt.subplots(figsize=(16, 6))
x_pos = np.arange(len(drugs))

# Plot each model with offset
for i, (model, probs, color, marker) in enumerate(model_data):
    offset = (i - 1) * 0.15
    mask = true_labels.astype(bool)
    colors_arr = np.where(mask, color, 'lightgray')
    ax.scatter(x_pos + offset, probs, s=100, c=colors_arr,
               marker=marker, edgecolor='black', linewidth=1.5,
               zorder=3, label=model)

ax.axhline(0.5, color='red', linestyle='--', linewidth=2, alpha=0.7)
ax.set_ylabel('Probability', fontsize=9)
ax.set_xlabel('Drug', fontsize=9)
ax.set_xticks(x_pos)
ax.set_xticklabels(drugs, rotation=45, ha='right', fontsize=8)
ax.tick_params(axis='both', labelsize=8)
ax.set_ylim(-0.05, 1.15)
ax.grid(axis='y', alpha=0.3)
ax.legend(loc='upper right')
```

### 5. Heatmap (Red-White-Blue Diverging)

**CRITICAL Heatmap Rules:**
1. **Square cells** - Always use `square=True`, never rectangles
2. **No borders/gaps** - Always use `linewidths=0` (no white space between cells)
3. **Axis orientation** - X-axis = Time (hours), Y-axis = Concentration (mM)
4. **Data matrix** - Rows = concentrations, Columns = time points
5. **Clean labels** - Remove duplicate decimal suffixes (8.1 → 8), keep meaningful ones (0.1 stays 0.1)

```python
import figure_config  # FIRST LINE - registers Helvetica
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import re

def clean_concentration_labels(labels):
    """
    Clean concentration labels by removing duplicate decimal suffixes.

    Examples:
        '8.1' → '8'      (removes .1 suffix that's just numbering)
        '8.2' → '8'      (removes .2 suffix)
        '0.1' → '0.1'    (keeps meaningful decimal - it's the actual value)
        '0.1.1' → '0.1'  (removes duplicate suffix from 0.1)
    """
    cleaned = []
    for label in labels:
        label_str = str(label)
        # Pattern: number.number.number (like 0.1.1) → keep first two parts
        if re.match(r'^\d+\.\d+\.\d+$', label_str):
            parts = label_str.split('.')
            cleaned.append(f"{parts[0]}.{parts[1]}")
        # Pattern: integer.single_digit at end (like 8.1, 8.2) → remove suffix
        elif re.match(r'^(\d+)\.[1-9]$', label_str):
            cleaned.append(re.match(r'^(\d+)\.[1-9]$', label_str).group(1))
        else:
            cleaned.append(label_str)
    return cleaned

# Example: Drug response heatmap
# CRITICAL: Rows = concentrations (Y-axis), Columns = time (X-axis)
n_concentrations = 8
n_timepoints = 40

data_matrix = pd.DataFrame(
    np.random.randn(n_concentrations, n_timepoints),
    index=[f'{c}' for c in [0, 0.1, 1, 2, 4, 8, 16, 32]],  # Concentration labels
    columns=[f'{t}' for t in range(0, n_timepoints * 2, 2)]  # Time labels (hours)
)

# Clean concentration labels (Y-axis)
y_labels = clean_concentration_labels(data_matrix.index.tolist())
x_labels = data_matrix.columns.tolist()  # Time labels (X-axis)

# Setup custom colormap with project colors
from matplotlib.colors import LinearSegmentedColormap

# Project heatmap colors (MANDATORY)
HEATMAP_BLUE = '#123BFF'   # Low values
HEATMAP_RED = '#FF2908'    # High values

# Create custom diverging colormap: Blue -> White -> Red
cmap = LinearSegmentedColormap.from_list(
    'cardiac_rodeo',
    [HEATMAP_BLUE, 'white', HEATMAP_RED]
)
cmap.set_bad('white')  # NaN values display as white

# MANDATORY Figure size for heatmaps (1:2 ratio)
HEATMAP_HEIGHT = 1.7   # inches
HEATMAP_WIDTH = 3.4    # inches (2x height)
fig, ax = plt.subplots(figsize=(HEATMAP_WIDTH, HEATMAP_HEIGHT))

# Create heatmap with SQUARE cells and NO borders/gaps
sns.heatmap(
    data_matrix,
    annot=False,              # No cell annotations
    cmap=cmap,
    cbar_kws={'label': 'Response', 'shrink': 0.8},
    xticklabels=x_labels,     # Time labels (X-axis)
    yticklabels=y_labels,     # Concentration labels (Y-axis)
    square=True,              # CRITICAL: Square cells, not rectangles
    mask=False,
    linewidths=0               # CRITICAL: No borders/gaps between cells
)

# Customize tick labels - FIXED SIZES
ax.set_xticklabels(x_labels, rotation=0, ha='center', fontsize=8)
ax.set_yticklabels(y_labels, fontsize=8, rotation=0)

# CRITICAL: X = Time, Y = Concentration - FIXED FONT SIZES
ax.set_xlabel('Time (Hours)', fontsize=9)
ax.set_ylabel('Concentration (mM)', fontsize=9)
ax.set_title('Drug Response Heatmap', fontsize=10, fontweight='bold')

plt.tight_layout()
```

**Heatmap Axis Orientation (MANDATORY):**
```
         X-axis: Time (Hours) →
        ┌─────────────────────────┐
    Y   │  0   2   4   6  ...  78 │
    a   ├─────────────────────────┤
    x   │ 32 │ ■ │ ■ │ ■ │     │ ■ │
    i   │ 16 │ ■ │ ■ │ ■ │     │ ■ │
    s   │  8 │ ■ │ ■ │ ■ │     │ ■ │
    :   │  4 │ ■ │ ■ │ ■ │     │ ■ │
    C   │  2 │ ■ │ ■ │ ■ │     │ ■ │
    o   │  1 │ ■ │ ■ │ ■ │     │ ■ │
    n   │0.1 │ ■ │ ■ │ ■ │     │ ■ │
    c   │  0 │ ■ │ ■ │ ■ │     │ ■ │
        └─────────────────────────┘
```

**Heatmap Colormap Reference:**
| Data Type | Colormap | Setup | Notes |
|-----------|----------|-------|-------|
| **Drug response (DEFAULT)** | Custom `cardiac_rodeo` | See code above | `#123BFF` (blue) → White → `#FF2908` (red) |
| Correlation | Custom or `RdBu_r` | `center=0, vmin=-1, vmax=1` | Symmetric around zero |
| Performance (R², accuracy) | `RdYlGn` | `center=0` | Red (bad) → Yellow → Green (good) |
| Confusion Matrix | `Blues` | N/A | One-sided, counts only |
| SHAP values | `coolwarm` | N/A | Blue (neg) → White → Red (pos) |

**MANDATORY Heatmap Colors:**
```python
HEATMAP_BLUE = '#123BFF'  # For low values
HEATMAP_RED = '#FF2908'   # For high values
```

### 6. Threshold Analysis Scatter Plot (Horizontal)
```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# Example data
drugs = ['Amiodarone', 'Bortezomib', 'Chlorpromazine', 'Doxorubicin', 'Erlotinib',
         'Ibuprofen', 'Nifedipine', 'Sotalol', 'Vincristine', 'Vioxx']
predictions = np.array([85, 72, 45, 90, 30, 25, 55, 78, 40, 65])  # Probability %
actual_positive = np.array([True, True, False, True, False, False, True, True, False, True])

# Sort drugs: by classification (positive first), then alphabetically
df = pd.DataFrame({'Drug': drugs, 'Pred': predictions, 'Positive': actual_positive})
df = df.sort_values(['Positive', 'Drug'], ascending=[False, True])
drugs_sorted = df['Drug'].tolist()
preds_sorted = df['Pred'].values
status_sorted = df['Positive'].values

# Colors: Green = positive, Red = negative
pos_color = '#2ca02c'   # Green
neg_color = '#d62728'   # Red
threshold_color = '#1f77b4'  # Blue for threshold line

# Create horizontal scatter plot (drugs on Y-axis)
fig, ax = plt.subplots(figsize=(10, max(6, len(drugs) * 0.4)))

positions = np.arange(len(drugs_sorted))
point_colors = [pos_color if s else neg_color for s in status_sorted]

# Scatter: X = probability, Y = drug position
ax.scatter(preds_sorted, positions, c=point_colors, s=100,
           edgecolors='black', linewidth=0.5, zorder=3)

# Compute threshold: max(negative samples) + margin, rounded to nearest 5
margin_pp = 2.0
neg_preds = preds_sorted[~status_sorted]
if len(neg_preds) > 0:
    threshold = float(np.max(neg_preds)) + margin_pp
else:
    threshold = 50.0
threshold = float(5 * np.ceil(threshold / 5.0))  # Round up to nearest 5

# Vertical threshold line
ax.axvline(threshold, color=threshold_color, linestyle='--', linewidth=2, zorder=2)
ax.text(threshold + 1, len(drugs_sorted) - 0.5, f'{threshold:.0f}%',
        color=threshold_color, fontsize=10, fontweight='bold', va='top')

# Axis setup with padding for 0% and 100% visibility
ax.set_xlim(-5, 105)  # Padding so edge points are visible
ax.set_ylim(-0.5, len(drugs_sorted) - 0.5)

ax.set_yticks(positions)
ax.set_yticklabels(drugs_sorted, fontsize=8)
ax.set_xlabel('Predicted Probability (%)', fontsize=9)
ax.set_title('Threshold Analysis: Arrhythmia Prediction', fontsize=10, fontweight='bold')
ax.tick_params(axis='both', labelsize=8)

ax.grid(axis='x', linestyle='--', alpha=0.4)
ax.invert_yaxis()  # First drug at top

# Legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=pos_color,
           markersize=10, label='Positive (Actual)'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=neg_color,
           markersize=10, label='Negative (Actual)'),
    Line2D([0], [0], color=threshold_color, linestyle='--', linewidth=2, label='Threshold')
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=8)

plt.tight_layout()
```

**Key Features:**
- Drugs on Y-axis for readable labels
- X-axis: 0-100% with `-5, 105` limits for edge visibility
- Green = positive class, Red = negative class
- Sorted by classification (positive first) then alphabetically
- Threshold = max(negative) + margin, rounded to nearest 5%
- Vertical threshold line with `axvline`

### 7. 3D Surface Plot (PK-PD)
```python
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Create meshgrid
time = np.linspace(0, 96, 50)
dose_ratio = np.linspace(0, 2, 50)
T, Dr = np.meshgrid(time, dose_ratio)
Response = compute_response(T, Dr, params)  # Your function

surf = ax.plot_surface(T, Dr, Response, cmap='viridis',
                       edgecolor='none', alpha=0.9)
ax.set_xlabel('Time (hours)', fontsize=9)
ax.set_ylabel('Dose Ratio (C0/Cmax)', fontsize=9)
ax.set_zlabel('Response', fontsize=9)
ax.set_title('Drug Response Surface', fontsize=10, fontweight='bold')
ax.tick_params(axis='both', labelsize=8)
ax.view_init(elev=25, azim=-158)
fig.colorbar(surf, shrink=0.5, aspect=10)
```

### 8. SHAP Aligned Pairs Plot
```python
import figure_config  # FIRST LINE - registers Helvetica
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

# Load SHAP values (example: arrhythmia)
shap_df = pd.read_csv('Output/SHAP_Data/shap_arrhythmia_values.csv')
drug_class = pd.read_csv('Cleaned_Data/drug_classification.csv')

# Create label map: drug -> actual class (True/False)
label_map = {}
for _, row in drug_class.iterrows():
    drug = row['Drug']
    val = row['Arrhythmia']  # or 'heart_damage', 'Concern', etc.
    label_map[drug] = str(val).lower() == 'true' if isinstance(val, str) else bool(val)

# Colors: Blue for positive class, Grey for negative class
COLORS = {
    'pass': '#6C92ED',   # Blue - positive class
    'fail': '#888888',   # Grey - negative class
}

# Get feature columns and select top 5 by |mean SHAP|
feature_cols = [col for col in shap_df.columns if col != 'Drug']
mean_shap = shap_df[feature_cols].abs().mean()
top_5_features = mean_shap.nlargest(5).index.tolist()

# Figure size: 2x width for SHAP plots
SQUARE_SIZE = 1.7
fig, ax = plt.subplots(figsize=(SQUARE_SIZE * 2, SQUARE_SIZE))
fig.subplots_adjust(left=0.25, right=0.85, top=0.88, bottom=0.12)

n_features = len(top_5_features)
n_drugs = len(shap_df)
feature_spacing = 1.0
drug_offset = 0.03

y_positions = []
y_labels = []

for feat_idx, feature in enumerate(reversed(top_5_features)):
    base_y = feat_idx * feature_spacing
    y_positions.append(base_y)
    y_labels.append(feature)

    # Sort drugs by SHAP value for this feature
    sorted_idx = np.argsort(shap_df[feature].values)

    for i, idx in enumerate(sorted_idx):
        drug = shap_df['Drug'].iloc[idx]
        val = shap_df[feature].iloc[idx]
        y = base_y + (i - n_drugs/2) * drug_offset

        # Color by actual class
        is_positive = label_map.get(drug, False)
        color = COLORS['pass'] if is_positive else COLORS['fail']

        # Draw line from 0 to SHAP value
        ax.hlines(y, 0, val, colors=color, linewidth=1.2, alpha=0.8)

ax.axvline(x=0, color='black', linewidth=0.8)
ax.set_yticks(y_positions)
ax.set_yticklabels(y_labels, fontsize=8)
ax.set_xlabel('SHAP Value', fontsize=9)
ax.set_title('SHAP Feature Importance', fontsize=10, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='x', alpha=0.3)
ax.tick_params(axis='x', labelsize=8)

legend_elements = [
    Line2D([0], [0], color=COLORS['pass'], linewidth=2, label='Pos'),
    Line2D([0], [0], color=COLORS['fail'], linewidth=2, label='Neg'),
]
ax.legend(handles=legend_elements, fontsize=8, loc='upper right')

plt.savefig('Output/SHAP_Data/shap_aligned_target.png', dpi=600)
plt.close()
```

**Key Features:**
- Shows top 5 features by |mean SHAP|
- For each feature, all drugs are plotted as horizontal lines from 0 to their SHAP value
- Lines sorted by SHAP value within each feature group
- Color indicates **actual class** (not SHAP sign): blue=positive, grey=negative
- Simple, clean visualization without complex pairing logic
- Compact size (3.4" × 1.7") for PowerPoint integration

**Data Export Pattern (for Excel recreation):**
```python
excel_data = []
for feature, y_pos, shap_val, drug, actual in plot_records:
    excel_data.append({
        'Feature': feature,
        'Y_Position': y_pos,
        'SHAP_Value': shap_val,
        'Drug': drug,
        'Actual_Class': 'Positive' if actual else 'Negative'
    })
pd.DataFrame(excel_data).to_excel('shap_aligned_pairs_data.xlsx', index=False)
```

### 9. Accuracy vs AUC Scatter Plot (Equation/Model Comparison)

**NOT a bar chart!** This is a scatter plot comparing equations across ML models.
- **X-axis** = Accuracy
- **Y-axis** = AUC
- Each point = one (equation, model) combination
- Color/marker by equation, grouped by model

```python
import figure_config  # FIRST LINE - registers Helvetica
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# Example data: 3 equations × 3 ML models = 9 points
equations = ['dual_exponential', 'modified_hill_hormesis', 'pkpd_elimination']
models = ['XGBoost', 'SVM_RBF', 'RandomForest']

# Simulated results (replace with actual loocv_results.csv data)
data = {
    ('dual_exponential', 'XGBoost'): {'Accuracy': 0.72, 'AUC': 0.78},
    ('dual_exponential', 'SVM_RBF'): {'Accuracy': 0.68, 'AUC': 0.72},
    ('dual_exponential', 'RandomForest'): {'Accuracy': 0.70, 'AUC': 0.75},
    ('modified_hill_hormesis', 'XGBoost'): {'Accuracy': 0.76, 'AUC': 0.82},
    ('modified_hill_hormesis', 'SVM_RBF'): {'Accuracy': 0.74, 'AUC': 0.80},
    ('modified_hill_hormesis', 'RandomForest'): {'Accuracy': 0.73, 'AUC': 0.78},
    ('pkpd_elimination', 'XGBoost'): {'Accuracy': 0.80, 'AUC': 0.86},
    ('pkpd_elimination', 'SVM_RBF'): {'Accuracy': 0.78, 'AUC': 0.84},
    ('pkpd_elimination', 'RandomForest'): {'Accuracy': 0.77, 'AUC': 0.82},
}

# Colors by equation
equation_colors = {
    'dual_exponential': '#e74c3c',      # Red
    'modified_hill_hormesis': '#3498db', # Blue
    'pkpd_elimination': '#2ecc71',       # Green
}

# Markers by model
model_markers = {
    'XGBoost': 'o',       # Circle
    'SVM_RBF': 's',       # Square
    'RandomForest': '^',  # Triangle
}

# Use 1.7" square (same as bar charts)
SQUARE_SIZE = 1.7
fig, ax = plt.subplots(figsize=(SQUARE_SIZE, SQUARE_SIZE))

# Plot each point
for (eq, model), metrics in data.items():
    ax.scatter(
        metrics['Accuracy'], metrics['AUC'],
        c=equation_colors[eq],
        marker=model_markers[model],
        s=40,  # Appropriate markers for 1.7" square
        edgecolors='black',
        linewidth=1,
        label=f'{eq} / {model}' if model == models[0] else '',  # Only label once per equation
        zorder=3
    )

# Reference lines
ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)  # AUC baseline
ax.axvline(0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)  # Accuracy baseline

# Axis settings - FIXED FONT SIZES
ax.set_xlabel('Accuracy', fontsize=9)
ax.set_ylabel('AUC', fontsize=9)
ax.set_title('Equation Comparison: Accuracy vs AUC', fontsize=10, fontweight='bold')
ax.tick_params(axis='both', labelsize=8)
ax.set_xlim(0.4, 1.0)
ax.set_ylim(0.4, 1.0)
ax.set_aspect('equal')  # Square plot for equal scaling
ax.grid(True, alpha=0.3)

# Custom legend
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Equation colors legend
eq_legend = [Patch(facecolor=c, edgecolor='black', label=eq.replace('_', ' ').title())
             for eq, c in equation_colors.items()]

# Model markers legend
model_legend = [Line2D([0], [0], marker=m, color='w', markerfacecolor='gray',
                       markersize=10, label=model, markeredgecolor='black')
                for model, m in model_markers.items()]

legend1 = ax.legend(handles=eq_legend, title='Equation', loc='upper left', fontsize=8)
ax.add_artist(legend1)
ax.legend(handles=model_legend, title='Model', loc='lower right', fontsize=8)

plt.tight_layout()
```

**Key Features:**
- X = Accuracy, Y = AUC (NOT bar chart)
- Each point represents one (equation, model) combination
- Color distinguishes equations
- Marker shape distinguishes ML models
- Square plot with equal scaling for fair comparison
- Reference lines at 0.5 for both axes (random baseline)

## Space-Saving Rules for Multi-Panel Figures

### CRITICAL: Shared Axes for Same-Scale Graphs

**When multiple graphs share the same axis scale, place them side-by-side and show only ONE axis instead of repeating.**

This eliminates wasted space from duplicate axis labels and tick marks.

```python
import figure_config
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# WRONG: Each subplot has its own Y-axis (wastes space)
fig, axes = plt.subplots(1, 3, figsize=(9, 3))
for ax in axes:
    ax.set_ylabel('Response')  # Repeated 3 times!

# CORRECT: Share Y-axis, only label the leftmost
fig, axes = plt.subplots(1, 3, figsize=(7, 3), sharey=True)
axes[0].set_ylabel('Response')  # Only once on the left
for ax in axes[1:]:
    ax.tick_params(labelleft=False)  # Hide Y tick labels on others

# BEST: Use GridSpec for tight control and minimal gaps
fig = plt.figure(figsize=(5.19, 1.44))  # 3 heatmaps side-by-side
gs = gridspec.GridSpec(1, 3, wspace=0.05)  # Minimal horizontal gap

axes = [fig.add_subplot(gs[0, i]) for i in range(3)]
axes[0].set_ylabel('Concentration (mM)')  # Only on leftmost
for ax in axes[1:]:
    ax.set_yticklabels([])  # No Y labels on middle/right panels
```

**Visual comparison:**
```
WRONG (wasted space):                    CORRECT (shared axis):
┌─────────┐ ┌─────────┐ ┌─────────┐     ┌─────────────────────────┐
│  Y      │ │  Y      │ │  Y      │     │  Y                      │
│  │ ■■■  │ │  │ ■■■  │ │  │ ■■■  │     │  │ ■■■ │ ■■■ │ ■■■     │
│  │ ■■■  │ │  │ ■■■  │ │  │ ■■■  │     │  │ ■■■ │ ■■■ │ ■■■     │
│  └──X   │ │  └──X   │ │  └──X   │     │  └──────────────X       │
└─────────┘ └─────────┘ └─────────┘     └─────────────────────────┘
 Drug A      Drug B      Drug C           Drug A  Drug B  Drug C
```

### CRITICAL: Shared Legends and Colorbars

**When multiple graphs in the same panel use the same color scale or legend, show only ONE colorbar/legend for all of them.**

```python
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

# Example: 3 heatmaps with one shared colorbar
fig = plt.figure(figsize=(5.5, 1.44))

# Create GridSpec: 3 heatmaps + 1 narrow colorbar column
gs = gridspec.GridSpec(1, 4, width_ratios=[1, 1, 1, 0.05], wspace=0.1)

# Determine shared vmin/vmax across all data
all_data = [data1, data2, data3]
vmin = min(d.min() for d in all_data)
vmax = max(d.max() for d in all_data)

# Plot heatmaps with same color scale
for i, data in enumerate(all_data):
    ax = fig.add_subplot(gs[0, i])
    im = ax.imshow(data, vmin=vmin, vmax=vmax, cmap='RdBu_r')
    if i == 0:
        ax.set_ylabel('Concentration')
    else:
        ax.set_yticklabels([])  # No Y labels on non-leftmost

# Single colorbar for all three
cbar_ax = fig.add_subplot(gs[0, 3])
fig.colorbar(im, cax=cbar_ax, label='Response')
```

**Rules summary:**
| Element | When to Share | How to Implement |
|---------|---------------|------------------|
| Y-axis | Same units & range | `sharey=True`, label only leftmost |
| X-axis | Same units & range | `sharex=True`, label only bottom |
| Colorbar | Same color scale | Single `colorbar()` with `cax=` |
| Legend | Same categories | Single `fig.legend()` outside subplots |

### Applying to Heatmaps

For multiple drug heatmaps (e.g., Contractility responses for different drugs):

```python
import figure_config
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

# Standard heatmap dimensions (1:2 ratio)
HEATMAP_HEIGHT = 1.7   # inches
HEATMAP_WIDTH = 3.4    # inches (2x height)

n_drugs = 3
fig = plt.figure(figsize=(HEATMAP_WIDTH * n_drugs + 0.3, HEATMAP_HEIGHT))

# GridSpec: n heatmaps + colorbar
gs = gridspec.GridSpec(1, n_drugs + 1,
                       width_ratios=[1]*n_drugs + [0.05],
                       wspace=0.05)

# Shared color scale
vmin, vmax = 0, 100  # Or compute from data

# Create custom colormap with project colors
from matplotlib.colors import LinearSegmentedColormap
HEATMAP_BLUE = '#123BFF'
HEATMAP_RED = '#FF2908'
cmap = LinearSegmentedColormap.from_list('cardiac_rodeo', [HEATMAP_BLUE, 'white', HEATMAP_RED])

for i, drug in enumerate(drugs):
    ax = fig.add_subplot(gs[0, i])
    sns.heatmap(data[drug], ax=ax, vmin=vmin, vmax=vmax,
                cmap=cmap, cbar=False, square=True)
    ax.set_title(drug, fontsize=10)

    if i == 0:
        ax.set_ylabel('Concentration (mM)', fontsize=10)
    else:
        ax.set_ylabel('')
        ax.set_yticklabels([])

    ax.set_xlabel('Time (h)', fontsize=10)

# Single shared colorbar
cbar_ax = fig.add_subplot(gs[0, -1])
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
fig.colorbar(sm, cax=cbar_ax, label='Response')

plt.tight_layout()
```

## Style Guidelines

### Font Settings (MANDATORY: Use Helvetica)
**ALWAYS use Helvetica as the default font for all figures. No fallbacks.**

**CRITICAL: Add `import figure_config` as the FIRST line of any plotting code.**

### Font Sizes (MANDATORY: Fixed Sizes for ALL Text Elements)

**CRITICAL: Use these EXACT font sizes for ALL text in ALL figures regardless of figure dimensions. This applies to EVERYTHING:**
- **Titles**
- **Axis labels (xlabel, ylabel)**
- **Tick labels**
- **Legend text**
- **Annotations**
- **Panel labels (a), (b), (c)**
- **Colorbar labels**

**Font sizes must be UNIFORM across all graphs - never scale fonts based on figure size.**

#### How Font Sizes Work in Matplotlib

**Font sizes are in POINTS (absolute units), where 1 point = 1/72 inch.**

This means:
- A 10pt title is ALWAYS 10/72 = 0.139 inches tall when printed/saved
- A 9pt axis label is ALWAYS 9/72 = 0.125 inches tall
- An 8pt tick label is ALWAYS 8/72 = 0.111 inches tall
- This is true regardless of `figsize` - fonts don't scale with the figure
- When you save at 600 DPI, fonts render at their true point size

**The result:** A 1.7" figure and a 4" figure with the same font sizes will have ALL text (titles, axis labels, tick labels, legends, etc.) at the SAME PHYSICAL SIZE when printed. Text takes up MORE of the small figure's area, but is the same size in inches.

**This is the desired behavior for publication consistency.** When figures are placed side-by-side or in a grid, all text elements are the same readable size.

```python
# MANDATORY FONT SIZE CONSTANTS - use these exact values everywhere
FONT_SIZES = {
    'title': 10,           # Figure/panel titles (0.139")
    'axis_label': 9,       # X and Y axis labels (0.125")
    'tick_label': 8,       # Tick mark labels (0.111")
    'legend': 8,           # Legend text
    'annotation': 8,       # Text annotations on plots
    'panel_label': 10,     # Panel labels (a), (b), (c)
    'colorbar_label': 8,   # Colorbar labels
}

# Apply in every figure:
ax.set_title('Title', fontsize=10, fontweight='bold')
ax.set_xlabel('X Label', fontsize=9)
ax.set_ylabel('Y Label', fontsize=9)
ax.tick_params(axis='both', labelsize=8)
ax.legend(fontsize=8)
```

#### Why This Ensures Consistency

When you have multiple figures of different sizes:
- 1.7" square confusion matrix
- 3.4" wide ROC curve
- 6" wide per-drug scatter

**All will have 10pt titles that are physically the same size.** This means:
- Readers can compare figures without adjusting to different text sizes
- Printed/PDF figures look professional and consistent
- PowerPoint slides have uniform text regardless of figure dimensions

**DO NOT do this:**
```python
# WRONG - scaling font based on figure size
fontsize = fig.get_figwidth() * 2  # NO!
ax.set_title('Title', fontsize=14)  # NO - not standard
ax.set_xlabel('Label', fontsize=12)  # NO - not standard

# WRONG - trying to make text "fit" smaller figures
small_fig_fontsize = 6  # NO - will be unreadable and inconsistent
```

**DO this:**
```python
# CORRECT - fixed sizes from standard (same for ALL figures)
ax.set_title('Title', fontsize=10, fontweight='bold')  # Always 10pt
ax.set_xlabel('Label', fontsize=9)  # Always 9pt
ax.tick_params(labelsize=8)  # Always 8pt

# This applies to 1.7" figures AND 6" figures - same font sizes
```

#### Ensuring Fonts Look Consistent When Viewing

Since fonts are absolute, a 1.7" figure will have relatively larger text (more of the figure area is text). To verify consistency:

1. **Save at consistent DPI (600)** - ensures font rendering matches
2. **View figures at 100% zoom** - see actual print size
3. **Never resize figures non-proportionally** - stretching changes aspect but not fonts

```python
import figure_config  # LINE 1 - registers Helvetica from fonts/ folder
import matplotlib.pyplot as plt
import numpy as np

# Now plot - Helvetica is already configured
fig, ax = plt.subplots(figsize=(8, 6))
# ... your plotting code
```

The `figure_config.py` module (located at project root) automatically:
- Registers all fonts from the `fonts/` directory
- Sets Helvetica as the default font family
- Configures standard font sizes and weights

**For inline/ad-hoc code without figure_config:**
```python
from pathlib import Path
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# Register Helvetica from fonts/ folder
font_dir = Path(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\fonts')
for font_file in font_dir.glob('*.ttf'):
    fm.fontManager.addfont(str(font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica']
```

### Always Include
- Clear axis labels with units where applicable
- Title with fontweight='bold'
- Grid with alpha=0.3 for readability
- Legend in appropriate location
- tight_layout() before saving

## Directory Structure

```
Output/
├── MoLFormer_Comparison/
│   ├── figures/           # PDF versions
│   │   ├── accuracy_bar.pdf
│   │   ├── roc_curves_all.pdf
│   │   └── confusion_matrices_all.pdf
│   ├── Accuracy_Bar.png   # PNG versions (capitalized)
│   └── ROC_Curves_All.png
├── ADMET_Comparison/
│   └── figures/
└── LaTeX_Reports/
    └── figures/           # Symlink or copy PDFs here
```

## Checklist Before Saving

- [ ] **`import figure_config` is the first line** (registers Helvetica)
- [ ] **Font sizes are UNIFORM** (title=10, axis_label=9, tick_label=8, legend=8)
- [ ] Title is descriptive and bold
- [ ] Axis labels include units if applicable
- [ ] Legend doesn't obscure data
- [ ] Color scheme is consistent with project
- [ ] Saved as both PDF and PNG
- [ ] tight_layout() called
- [ ] Figure closed with plt.close()
- [ ] **ROC curves: Shaded confidence band included** (use `fill_between` with bootstrap ±1 std)
- [ ] **Heatmaps: No borders/gaps between cells** (use `linewidths=0`, `square=True`)

## PowerPoint Figure System

This section defines the conventions for creating figures intended for PowerPoint presentations and publication, with full traceability and consistency.

### CRITICAL: Automatic PowerPoint Insertion

**When generating or modifying a tracked figure, you MUST automatically insert it into the target PowerPoint file.**

This is NOT optional. After saving the PNG/PDF and Excel files, the figure must be placed into the PowerPoint at its designated location with proper sizing and labels.

**Target file:** `Output/PowerPoint_Figures/Cardiac_RODEO_Tracked.pptx`

#### CRITICAL: Link Images, Don't Embed

**Always LINK images to PowerPoint instead of embedding them.** This enables automatic updates when figures are regenerated.

**Why link instead of embed:**
- When you regenerate a figure with Python, the PowerPoint updates automatically
- No need to manually delete and re-insert figures
- Keeps file size smaller (images stored once on disk)
- Enables rapid iteration: edit Python → run script → switch to PowerPoint → see updated figure

**Workflow:**
1. Python script saves figure to a fixed path (e.g., `Output/PowerPoint_Figures/Fig_2/Fig_2_a_ROC.png`)
2. PowerPoint links to that exact path
3. When you re-run the script, the PNG is overwritten
4. PowerPoint automatically shows the new version (may need to refresh/reopen)

**python-pptx: Link instead of embed:**
```python
from pptx import Presentation
from pptx.util import Inches
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml
from lxml import etree

def add_linked_picture(slide, image_path, left, top, width=None, height=None):
    """
    Add a picture to a slide as a LINKED image (not embedded).
    The image will update automatically when the source file changes.

    Args:
        slide: pptx slide object
        image_path: Absolute path to the image file
        left, top: Position in Inches
        width, height: Size in Inches (optional, preserves aspect ratio if only one given)
    """
    from pptx.util import Emu
    from PIL import Image
    import os

    # Get image dimensions for aspect ratio
    with Image.open(image_path) as img:
        img_width, img_height = img.size
        aspect = img_width / img_height

    # Calculate size
    if width and not height:
        height = width / aspect
    elif height and not width:
        width = height * aspect
    elif not width and not height:
        width = Inches(4)  # default
        height = width / aspect

    # Add picture shape (this embeds, but we'll convert to link)
    picture = slide.shapes.add_picture(
        image_path,
        Inches(left), Inches(top),
        Inches(width), Inches(height)
    )

    # To make it a TRUE linked picture, you need to manually edit the .pptx
    # after creation, or use the method below to store the path for reference

    # Store the source path in the shape's name for tracking
    picture.name = f"LINKED:{image_path}"

    return picture

# For true linking, use Insert > Picture > Link to File in PowerPoint GUI
# python-pptx doesn't natively support linked pictures, but you can:
# 1. Use the GUI to insert linked pictures initially
# 2. Use python-pptx only for positioning/sizing
# 3. Or manually edit the XML (advanced)
```

**Recommended workflow for linked images:**
1. **Initial setup (GUI):** Insert pictures using PowerPoint's "Insert → Pictures → This Device" then click the dropdown arrow on "Insert" and select **"Link to File"**
2. **Subsequent updates:** Just re-run your Python scripts - the linked images update automatically
3. **Tracking:** Keep `figure_registry.csv` updated with exact file paths

**PowerPoint GUI steps to link an image:**
1. Insert → Pictures → This Device
2. Navigate to your figure (e.g., `Output/PowerPoint_Figures/Fig_2/Fig_2_a_ROC.png`)
3. Click the dropdown arrow next to "Insert" button
4. Select **"Link to File"** (not "Insert")
5. The image is now linked - it will update when the source file changes

#### Slide Dimensions (MANDATORY)
```python
SLIDE_WIDTH = 7.09   # inches
SLIDE_HEIGHT = 8.47  # inches (portrait orientation)
MARGIN = 0.5         # inches from edges
GAP = 0.15           # inches between figures
```

#### Figure Hierarchy

**Structure:**
- **Figure number (1, 2, 3...)** = Main figure, gets its own slide
- **Panel letter (a, b, c...)** = Subfigure boxes within that figure
- **Images** = One or more graphics inside each panel box

**CRITICAL: Horizontal-First Panel Filling**
Panels fill **horizontally first** (left to right), then wrap to next row:
- Panels a, b fill the first row side-by-side
- If there's room, panel c goes next to b
- If not, panel c starts a new row below
- Never stack panels vertically if horizontal space is available

```
CORRECT (horizontal-first):           WRONG (vertical stacking):
┌──────────────────────────────┐      ┌──────────────────────────────┐
│  Figure 3                    │      │  Figure 3                    │
├──────────────────────────────┤      ├──────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  │      │  ┌──────────────────────┐    │
│  │ (a) ROC  │  │ (b) CM   │  │      │  │ (a) ROC              │    │
│  └──────────┘  └──────────┘  │      │  └──────────────────────┘    │
│  ┌──────────┐                │      │  ┌──────────────────────┐    │
│  │ (c) SHAP │                │      │  │ (b) Confusion Matrix │    │
│  └──────────┘                │      │  └──────────────────────┘    │
└──────────────────────────────┘      │  ┌──────────────────────┐    │
                                      │  │ (c) SHAP             │    │
Layout: '2x2' with 3 panels           │  └──────────────────────┘    │
(a=top-left, b=top-right, c=btm-left) └──────────────────────────────┘

                                      Layout: '3x1' - DON'T USE unless
                                      panels are very wide

File naming:  Fig_3_a_ROC.png      →  Figure 3, Panel a
              Fig_3_b_SHAP.png     →  Figure 3, Panel b
              Fig_3_c_scatter.png  →  Figure 3, Panel c
```

**Panel Count to Layout Mapping:**
| Panels | Preferred Layout | Panel Positions |
|--------|------------------|-----------------|
| 2 | `1x2` | a=left, b=right |
| 3 | `2x2` | a=top-left, b=top-right, c=bottom-left |
| 4 | `2x2` | a=top-left, b=top-right, c=bottom-left, d=bottom-right |
| 5-6 | `2x3` | Fill left-to-right, top-to-bottom |

#### Multi-Figure Layouts
Use these standard layouts for placing subfigure boxes (e.g., Fig 3a, 3b, 3c) on the same slide:

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pathlib import Path

# Slide dimensions
SLIDE_WIDTH = 7.09
SLIDE_HEIGHT = 8.47
MARGIN = 0.5
GAP = 0.15

# Usable area
USABLE_WIDTH = SLIDE_WIDTH - 2 * MARGIN   # 6.09"
USABLE_HEIGHT = SLIDE_HEIGHT - 2 * MARGIN  # 7.47"

def get_layout_positions(layout, title_height=0.6):
    """
    Get positions and sizes for standard multi-figure layouts.

    Args:
        layout: '1x1', '1x2', '2x1', '2x2', '3x1', '1x3', '2x3', '3x2'
        title_height: Height reserved for slide title (inches)

    Returns:
        List of (left, top, width, height) tuples for each panel position
    """
    top_start = MARGIN + title_height
    available_height = USABLE_HEIGHT - title_height

    layouts = {
        # Single figure (full width)
        '1x1': [
            (MARGIN, top_start, USABLE_WIDTH, available_height)
        ],
        # 2 figures side-by-side (1 row, 2 cols)
        '1x2': [
            (MARGIN, top_start, (USABLE_WIDTH - GAP) / 2, available_height),
            (MARGIN + (USABLE_WIDTH + GAP) / 2, top_start, (USABLE_WIDTH - GAP) / 2, available_height),
        ],
        # 2 figures stacked (2 rows, 1 col)
        '2x1': [
            (MARGIN, top_start, USABLE_WIDTH, (available_height - GAP) / 2),
            (MARGIN, top_start + (available_height + GAP) / 2, USABLE_WIDTH, (available_height - GAP) / 2),
        ],
        # 2x2 grid (4 panels)
        '2x2': [
            (MARGIN, top_start, (USABLE_WIDTH - GAP) / 2, (available_height - GAP) / 2),
            (MARGIN + (USABLE_WIDTH + GAP) / 2, top_start, (USABLE_WIDTH - GAP) / 2, (available_height - GAP) / 2),
            (MARGIN, top_start + (available_height + GAP) / 2, (USABLE_WIDTH - GAP) / 2, (available_height - GAP) / 2),
            (MARGIN + (USABLE_WIDTH + GAP) / 2, top_start + (available_height + GAP) / 2, (USABLE_WIDTH - GAP) / 2, (available_height - GAP) / 2),
        ],
        # 3 figures stacked vertically (3 rows, 1 col)
        '3x1': [
            (MARGIN, top_start, USABLE_WIDTH, (available_height - 2 * GAP) / 3),
            (MARGIN, top_start + (available_height + GAP) / 3, USABLE_WIDTH, (available_height - 2 * GAP) / 3),
            (MARGIN, top_start + 2 * (available_height + GAP) / 3, USABLE_WIDTH, (available_height - 2 * GAP) / 3),
        ],
        # 3 figures side-by-side (1 row, 3 cols)
        '1x3': [
            (MARGIN, top_start, (USABLE_WIDTH - 2 * GAP) / 3, available_height),
            (MARGIN + (USABLE_WIDTH + GAP) / 3, top_start, (USABLE_WIDTH - 2 * GAP) / 3, available_height),
            (MARGIN + 2 * (USABLE_WIDTH + GAP) / 3, top_start, (USABLE_WIDTH - 2 * GAP) / 3, available_height),
        ],
        # 2 rows x 3 cols (6 panels)
        '2x3': [
            (MARGIN, top_start, (USABLE_WIDTH - 2 * GAP) / 3, (available_height - GAP) / 2),
            (MARGIN + (USABLE_WIDTH + GAP) / 3, top_start, (USABLE_WIDTH - 2 * GAP) / 3, (available_height - GAP) / 2),
            (MARGIN + 2 * (USABLE_WIDTH + GAP) / 3, top_start, (USABLE_WIDTH - 2 * GAP) / 3, (available_height - GAP) / 2),
            (MARGIN, top_start + (available_height + GAP) / 2, (USABLE_WIDTH - 2 * GAP) / 3, (available_height - GAP) / 2),
            (MARGIN + (USABLE_WIDTH + GAP) / 3, top_start + (available_height + GAP) / 2, (USABLE_WIDTH - 2 * GAP) / 3, (available_height - GAP) / 2),
            (MARGIN + 2 * (USABLE_WIDTH + GAP) / 3, top_start + (available_height + GAP) / 2, (USABLE_WIDTH - 2 * GAP) / 3, (available_height - GAP) / 2),
        ],
    }
    return layouts.get(layout, layouts['1x1'])


def insert_subfigure_boxes(pptx_path, slide_index, subfigures, layout, title=None):
    """
    Insert subfigure boxes onto a slide, where each box can contain multiple images.

    Args:
        pptx_path: Path to the .pptx file
        slide_index: 0-based slide index
        subfigures: List of subfigure definitions, each is:
                    {'label': 'a', 'images': [path1, path2, ...], 'image_layout': '1x2'}
        layout: Layout for subfigure BOXES ('1x1', '2x1', '3x1', etc.)
        title: Optional slide title (e.g., 'Figure 3')
    """
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE

    prs = Presentation(pptx_path)
    slide = prs.slides[slide_index]

    # Add title if specified
    title_height = 0.6 if title else 0
    if title:
        txBox = slide.shapes.add_textbox(Inches(MARGIN), Inches(MARGIN),
                                          Inches(USABLE_WIDTH), Inches(title_height))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(18)
        p.font.bold = True

    # Get positions for subfigure boxes
    box_positions = get_layout_positions(layout, title_height)

    for i, subfig in enumerate(subfigures):
        if i >= len(box_positions):
            print(f"Warning: More subfigures than layout positions. Skipping box {subfig['label']}")
            continue

        box_left, box_top, box_width, box_height = box_positions[i]
        label = subfig.get('label', '')
        images = subfig.get('images', [])
        img_layout = subfig.get('image_layout', '1x1')

        # Add subfigure box border (optional - light gray rectangle)
        box_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(box_left), Inches(box_top),
            Inches(box_width), Inches(box_height)
        )
        box_shape.fill.background()  # Transparent fill
        box_shape.line.color.rgb = RGBColor(200, 200, 200)  # Light gray border
        box_shape.line.width = Pt(0.5)

        # Add label in top-left corner of box
        if label:
            lbl_box = slide.shapes.add_textbox(
                Inches(box_left + 0.05), Inches(box_top + 0.05),
                Inches(0.3), Inches(0.25)
            )
            tf = lbl_box.text_frame
            p = tf.paragraphs[0]
            p.text = f"({label})"
            p.font.size = Pt(12)
            p.font.bold = True

        # Calculate image positions within the box
        label_offset = 0.3  # Space for label
        inner_left = box_left + 0.1
        inner_top = box_top + label_offset
        inner_width = box_width - 0.2
        inner_height = box_height - label_offset - 0.1
        inner_gap = 0.1

        # Parse image layout (e.g., '1x2' = 1 row, 2 cols)
        if 'x' in img_layout:
            rows, cols = map(int, img_layout.split('x'))
        else:
            rows, cols = 1, len(images)

        img_width = (inner_width - (cols - 1) * inner_gap) / cols
        img_height = (inner_height - (rows - 1) * inner_gap) / rows

        # Place images in grid within box
        for j, img_path in enumerate(images):
            row = j // cols
            col = j % cols
            img_left = inner_left + col * (img_width + inner_gap)
            img_top = inner_top + row * (img_height + inner_gap)

            slide.shapes.add_picture(
                str(img_path),
                Inches(img_left), Inches(img_top),
                width=Inches(img_width), height=Inches(img_height)
            )

    prs.save(pptx_path)
    print(f"Inserted {len(subfigures)} subfigure boxes into slide {slide_index + 1}")


# Example: Figure 3 with subfigure boxes a, b, c
pptx_path = Path('Output/PowerPoint_Figures/Cardiac_RODEO_Tracked.pptx')

subfigures = [
    {
        'label': 'a',
        'images': [
            Path('Output/ROC_Data/roc_arrhythmia.png'),
            Path('Output/Confusion_Matrices/cm_arrhythmia.png'),
        ],
        'image_layout': '1x2'  # 2 images side-by-side within box a
    },
    {
        'label': 'b',
        'images': [
            Path('Output/ROC_Data/roc_heart_damage.png'),
            Path('Output/Confusion_Matrices/cm_heart_damage.png'),
        ],
        'image_layout': '1x2'  # 2 images side-by-side within box b
    },
    {
        'label': 'c',
        'images': [
            Path('Output/SHAP_Data/shap_aligned_arrhythmia.png'),
        ],
        'image_layout': '1x1'  # 1 image in box c
    },
]

insert_subfigure_boxes(
    pptx_path=pptx_path,
    slide_index=2,           # Slide 3 (0-indexed)
    subfigures=subfigures,
    layout='3x1',            # 3 subfigure boxes stacked vertically
    title='Figure 3'
)
```

#### Layout Reference Table

| Layout | Description | Panel Count | Best For |
|--------|-------------|-------------|----------|
| `1x1` | Single full-width | 1 | Single large figure |
| `1x2` | Side-by-side | 2 | Comparison (e.g., ROC vs Confusion) |
| `2x1` | Stacked vertical | 2 | Sequential data |
| `2x2` | 2×2 grid | 4 | Four related panels |
| `3x1` | 3 stacked vertical | 3 | Fig 3a, 3b, 3c stacked |
| `1x3` | 3 side-by-side | 3 | Wide comparison |
| `2x3` | 2×3 grid | 6 | Six panels |

**Workflow for tracked figures:**
1. Generate and save PNG at 600 DPI
2. Save Excel with data and metadata
3. **Insert into PowerPoint using `insert_figures_to_slide()` with appropriate layout**
4. Update `figure_registry.csv`

**If replacing an existing figure:**
1. Delete the old shape from the slide first
2. Insert the new figure at the same position
3. Preserve any existing labels/annotations

### Figure Tracking System

**Every figure must have a corresponding Excel file with the exact data used to generate it.**

#### Naming Convention
```
Fig_X_letter_description.png   # The figure image
Fig_X_letter_description.xlsx  # The source data
```

Examples:
- `Fig_2_a_pipeline_overview.png` / `Fig_2_a_pipeline_overview.xlsx`
- `Fig_2_b_ROC_Arrhythmia.png` / `Fig_2_b_ROC_Arrhythmia.xlsx`
- `Fig_3_c_SHAP_importance.png` / `Fig_3_c_SHAP_importance.xlsx`

**Excel file contents should include:**
- Raw data used for plotting
- Any computed values (means, standard deviations, etc.)
- Column headers matching axis labels
- A "Metadata" sheet with generation timestamp and source script

### Folder Structure for PowerPoint Projects

```
Output/PowerPoint_Figures/
├── Fig_1/
│   ├── Fig_1a_pipeline_diagram.png
│   ├── Fig_1a_pipeline_diagram.xlsx (if applicable)
│   ├── Fig_1b_experimental_setup.png
│   └── Fig_1b_experimental_setup.xlsx
├── Fig_2/
│   ├── Fig_2a_organoid_formation.png
│   ├── Fig_2a_organoid_formation.xlsx
│   ├── Fig_2b_ROC_Arrhythmia.png
│   └── Fig_2b_ROC_Arrhythmia.xlsx
├── Fig_3/
│   └── ...
├── scripts_reference.txt   # Lists all source scripts used
├── external_sources.txt    # Notes externally generated images
└── figure_registry.csv     # Master tracking file
```

### Figure Registry (CSV format)

The `figure_registry.csv` file tracks all figures in the project.

**Columns:**
| Column | Description |
|--------|-------------|
| Figure_ID | Figure number (e.g., "1", "2", "3") |
| Letter | Panel letter (e.g., "a", "b", "c") |
| Description | Brief description of the figure |
| PNG_Path | Relative path to PNG file |
| Excel_Path | Relative path to Excel data file (or "N/A") |
| Source_Script | Script that generated the figure (or "N/A") |
| External | "TRUE" if externally generated, "FALSE" otherwise |
| Notes | Additional notes (source software, manual edits, etc.) |

**Example `figure_registry.csv`:**
```csv
Figure_ID,Letter,Description,PNG_Path,Excel_Path,Source_Script,External,Notes
1,a,Pipeline diagram,Fig_1/Fig_1_a_pipeline_diagram.png,N/A,N/A,TRUE,Created in BioRender
1,b,Experimental setup,Fig_1/Fig_1_b_experimental_setup.png,Fig_1/Fig_1_b_experimental_setup.xlsx,generate_setup_fig.py,FALSE,
2,a,ROC Arrhythmia,Fig_2/Fig_2_a_ROC_Arrhythmia.png,Fig_2/Fig_2_a_ROC_Arrhythmia.xlsx,plot_roc_curves.py,FALSE,
2,b,ROC Heart Damage,Fig_2/Fig_2_b_ROC_HeartDamage.png,Fig_2/Fig_2_b_ROC_HeartDamage.xlsx,plot_roc_curves.py,FALSE,
3,a,SHAP importance,Fig_3/Fig_3_a_SHAP_importance.png,Fig_3/Fig_3_a_SHAP_importance.xlsx,shap_analysis.py,FALSE,Updated 2026-01-15
```

### Consistency Rules

**CRITICAL: If one figure changes style, ALL figures must be regenerated.**

1. **Font Consistency**
   - Always use `import figure_config` as the first line
   - Helvetica is mandatory for all text
   - Standard sizes: title=14pt bold, axis labels=12pt, tick labels=10pt

2. **Color Palette Consistency**
   - Use the defined color palettes from this skill
   - Document any custom colors in `figure_registry.csv` Notes column

3. **DPI Requirement**
   - All figures must be saved at **600 DPI**
   ```python
   plt.savefig('Fig_2_a_ROC.png', dpi=600, bbox_inches='tight')
   ```

4. **Error Bars / Standard Deviation (MANDATORY)**
   - **Always include error bars** on bar plots, grouped bar charts, and box-and-whisker plots

5. **Shared Axes for Multi-Panel Figures (MANDATORY)**
   - When multiple panels have the **same axis range**, share that axis
   - Use `sharey=True` or `sharex=True` in `plt.subplots()`
   - Only show axis labels on the leftmost (Y) or bottom (X) panel
   - This reduces redundancy and makes comparisons easier
   ```python
   # CORRECT: Share Y-axis across 3 panels
   fig, axes = plt.subplots(1, 3, figsize=(8, 3), sharey=True)
   for idx, ax in enumerate(axes):
       if idx == 0:
           ax.set_ylabel('AUC')  # Only first panel gets Y label
       ax.set_xlabel('Accuracy')

   # WRONG: Repeating same Y-axis 3 times
   fig, axes = plt.subplots(1, 3, figsize=(8, 3))
   for ax in axes:
       ax.set_ylabel('AUC')  # Redundant!
   ```

6. **Square Scatter Plots (MANDATORY for Accuracy vs AUC)**
   - Use `ax.set_box_aspect(1)` to force square aspect ratio
   - X and Y axis ranges must be identical (e.g., both 0.3-0.9)
   ```python
   ax.set_xlim(0.3, 0.9)
   ax.set_ylim(0.3, 0.9)
   ax.set_box_aspect(1)  # Force square
   ```
   - Use standard deviation (std) or standard error of the mean (SEM) as appropriate
   - Error bars must be clearly visible with cap lines
   ```python
   # Bar plot with error bars
   ax.bar(x, means, yerr=stds, capsize=5, color='#6C92ED', edgecolor='black')

   # Grouped bar chart with error bars
   bars = ax.bar(x + offset, values, width, yerr=errors, capsize=3,
                 label=label, color=color, edgecolor='black')
   ```

5. **Regeneration Protocol**
   When any style element changes:
   - Update `figure_config.py` with new settings
   - Run all source scripts listed in `scripts_reference.txt`
   - Verify all figures in `figure_registry.csv` are updated
   - Update timestamps in Excel metadata sheets

### PowerPoint Integration

#### Panel Labels
Figures should include letter labels (a, b, c) in boxes for multi-panel figures.

```python
# Add panel label in upper-left corner
ax.text(-0.12, 1.05, 'a', transform=ax.transAxes,
        fontsize=16, fontweight='bold', va='top',
        bbox=dict(boxstyle='square,pad=0.3', facecolor='white', edgecolor='black'))
```

#### Standard Panel Sizes
Based on slide dimensions: **7.09" × 8.47"** (portrait), with 0.5" margins:

| Layout | Panel Width | Panel Height | Use Case |
|--------|-------------|--------------|----------|
| Full slide (`1x1`) | 6.09" | 6.87" | Single large figure |
| Half width (`1x2`) | 2.97" | 6.87" | Side-by-side panels |
| Half height (`2x1`) | 6.09" | 3.36" | Stacked panels |
| Quarter (`2x2`) | 2.97" | 3.36" | 4-panel grid |
| Third height (`3x1`) | 6.09" | 2.19" | 3 stacked (Fig 3a,b,c) |
| Third width (`1x3`) | 1.93" | 6.87" | 3 side-by-side |

Convert to matplotlib figsize (use 3x scale for 600 DPI export):
```python
# Single full-slide figure
fig, ax = plt.subplots(figsize=(6.09 * 3, 6.87 * 3))

# Half-height panel (for 2x1 or 3x1 layouts)
fig, ax = plt.subplots(figsize=(6.09 * 3, 3.36 * 3))

# Third-height panel (for 3 stacked figures)
fig, ax = plt.subplots(figsize=(6.09 * 3, 2.19 * 3))

# Quarter panel (for 2x2 grid)
fig, ax = plt.subplots(figsize=(2.97 * 3, 3.36 * 3))
```

#### Alignment on Slides
- Use consistent margins (0.5" from slide edges)
- Align panel edges to PowerPoint grid
- Group related panels with consistent spacing (0.1" gap)

### External Images

For images not generated by Python scripts (e.g., BioRender, microscopy, schematics):

1. **Mark as "EXTERNAL" in registry**
   ```csv
   1,a,Pipeline diagram,Fig_1/Fig_1_a_pipeline.png,N/A,N/A,TRUE,Created in BioRender
   ```

2. **Note original source in `external_sources.txt`**
   ```
   Fig_1a_pipeline_diagram.png
   - Source: BioRender
   - Created: 2026-01-10
   - Author: Noah B.
   - License: Academic license, BioRender.com
   - Original file: pipeline_biorender_v3.png

   Fig_1b_microscopy.png
   - Source: Confocal microscope (Zeiss LSM 880)
   - Acquisition date: 2025-11-15
   - Sample: Cardiac organoid batch #42
   - Settings: 40x objective, 488nm excitation
   ```

3. **Still follow naming convention**
   - Rename external files to match `Fig_X_letter_description.png` format
   - Keep originals in a separate `_originals/` subfolder if needed

### Template: Creating a New PowerPoint Figure Set

```python
import figure_config  # FIRST LINE - registers Helvetica
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from datetime import datetime

# Setup paths
output_dir = Path('Output/PowerPoint_Figures/Fig_2')
output_dir.mkdir(parents=True, exist_ok=True)

# Your data
data = pd.DataFrame({
    'Model': ['Model A', 'Model B', 'Model C'],
    'AUC': [0.85, 0.92, 0.78],
    'AUC_std': [0.03, 0.02, 0.05]
})

# Create figure
fig, ax = plt.subplots(figsize=(2.42 * 3, 1.36 * 3))  # 3x scale for high-res

# ... plotting code ...

# Add panel label
ax.text(-0.12, 1.05, 'a', transform=ax.transAxes,
        fontsize=16, fontweight='bold', va='top',
        bbox=dict(boxstyle='square,pad=0.3', facecolor='white', edgecolor='black'))

plt.tight_layout()

# Save figure at 600 DPI
fig_path = output_dir / 'Fig_2_a_AUC_comparison.png'
plt.savefig(fig_path, dpi=600, bbox_inches='tight')
plt.close()

# Save Excel with data and metadata
excel_path = output_dir / 'Fig_2_a_AUC_comparison.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    data.to_excel(writer, sheet_name='Data', index=False)
    metadata = pd.DataFrame({
        'Field': ['Generated', 'Script', 'Figure ID'],
        'Value': [datetime.now().isoformat(), __file__, 'Fig_2_a']
    })
    metadata.to_excel(writer, sheet_name='Metadata', index=False)

print(f"Saved: {fig_path}")
print(f"Saved: {excel_path}")
```

### Checklist for PowerPoint Figures

- [ ] `import figure_config` is the first line
- [ ] Figure saved at 600 DPI
- [ ] Naming follows `Fig_Xletter.png` convention (e.g., `Fig_6a.png`, `Fig_3c.png`)
- [ ] Excel file created with matching name (e.g., `Fig_6a_data.xlsx`)
- [ ] Panel label added (if multi-panel figure)
- [ ] **CRITICAL: Figure inserted into PowerPoint at designated position**
- [ ] Entry added to `figure_registry.csv`
- [ ] External sources documented in `external_sources.txt`
- [ ] All related figures use consistent colors/fonts/styles
- [ ] **Error bars included** on bar plots and box-and-whisker plots (std or SEM)
- [ ] **`exact_size` used** for square panels (ROC, CM, threshold) where dimensions must be precise
- [ ] **`get_layout_size()` called** to check if PPTX aspect ratio requires dimension adjustment
- [ ] **Compound panels** use correct suffix naming (e.g., `Fig_3a_1.png`, `Fig_3a_2.png`)

## Script Architecture Reference (`generate_paper_figures.py`)

This section documents the internal mechanisms of the figure generation script. **Always reference these when editing the script to avoid breaking the pipeline.**

### File Naming Convention (ACTUAL)

**CRITICAL: The script does NOT use `Fig_X_letter_description.png`.** The actual convention is:

```
Fig_{FigureID}{Letter}.png        # Standard panels
Fig_{FigureID}{Letter}_{Suffix}.png  # Compound panel sub-images
Fig_{FigureID}{Letter}_data.xlsx  # Data tracking file
```

**Examples:**
```
Fig_6a.png              # Figure 6, panel a (ROC curve)
Fig_6b.png              # Figure 6, panel b (confusion matrix)
Fig_3a_1.png            # Figure 3, panel a, sub-image 1 (heatmap O2)
Fig_3a_2.png            # Figure 3, panel a, sub-image 2 (heatmap contractility)
Fig_3b_colorbar.png     # Figure 3, panel b, shared colorbar
Fig_3e_O2.png           # Figure 3, panel e, O2 3D surface
Fig_3e_Contractility.png # Figure 3, panel e, contractility 3D surface
Fig_6a_data.xlsx        # Tracking data for Fig 6a
```

This naming is baked into `save_figure()` at line ~198:
```python
png_path = folder / f'Fig_{fig_id}{letter}.png'
```

### `save_figure()` — Central Save Function

All figure saving goes through this function. Understand it before changing any save logic.

```python
def save_figure(fig, fig_id, letter, description, data_dict=None,
                width=SINGLE_W, height=SINGLE_H, notes='', exact_size=False,
                source_script='generate_paper_figures.py'):
```

**Parameters:**
| Parameter | Purpose |
|-----------|---------|
| `fig` | Matplotlib figure object |
| `fig_id` | Figure number as string (e.g., `'6'`, `'S1'`) |
| `letter` | Panel letter (e.g., `'a'`, `'b'`) or compound label (e.g., `'Epirubicin_TC50'`) |
| `description` | Human-readable description for the registry |
| `data_dict` | `{sheet_name: DataFrame}` — saved to `*_data.xlsx` for tracking |
| `exact_size` | **CRITICAL** — see below |
| `source_script` | Script name for provenance tracking |

**`exact_size` parameter (CRITICAL):**

- `exact_size=False` (default): Saves with `bbox_inches='tight'`, which crops whitespace. The final image may be slightly different from `figsize`. Good for figures where content matters more than exact pixel dimensions.

- `exact_size=True`: Saves at the exact `figsize` dimensions — no cropping, no whitespace removal. **Use this for square panels** (ROC, confusion matrix, threshold scatter) where the figure dimensions must precisely match the PPTX slot to avoid distortion.

```python
# CORRECT: Square panels use exact_size=True
save_figure(fig, fig_num, 'a', 'ROC Curve',
            {'ROC_Data': roc_df}, width=SQUARE_SIZE, height=SQUARE_SIZE, exact_size=True)

# CORRECT: Non-square panels use exact_size=False (default)
save_figure(fig, '3', 'c', 'R² Equation Comparison',
            {'R2_Data': r2_df}, width=5.0, height=3.5)
```

**When to use `exact_size=True`:**
- ROC curves (panel a)
- Confusion matrices (panel b)
- Threshold scatter plots (panel d)
- Cumulative probability plots (panel e)
- Any panel where `fig.subplots_adjust()` is used to manually control margins

### `get_layout_size()` — PPTX Aspect Ratio Matching

This function ensures generated figures match the aspect ratio of their PPTX placeholder shapes. **Always call it when defining panel dimensions.**

```python
def get_layout_size(fig_id, letter, default=None):
    """Get figure dimensions that match the PPTX aspect ratio at the default scale.

    Returns the *default* size adjusted to match the PPTX panel's aspect ratio.
    PowerPoint then scales the high-res image down to fit, keeping it sharp.
    """
```

**How it works:**
1. Reads `slide_layout.json` (populated via `--extract-layout`)
2. Looks up the PPTX shape dimensions for `Fig_{fig_id}{letter}`
3. Compares PPTX aspect ratio with the `default` aspect ratio
4. If they differ by >5%, adjusts the default to match PPTX AR while keeping the larger dimension at the default scale
5. Returns `None` if no adjustment is needed (aspect ratios already match)

**Usage pattern (MANDATORY for all panels in Figures 6/7/8):**
```python
_def_a = (SQUARE_SIZE, SQUARE_SIZE)  # Default: 1.7" × 1.7" square
size_a = get_layout_size(fig_num, 'a', default=_def_a) or _def_a
# size_a is now either adjusted to match PPTX AR, or the original default

fig, ax = plt.subplots(figsize=(size_a[0], size_a[1]))  # Use adjusted size
```

**Why this matters:**
- Without `get_layout_size()`, a 1.7" × 1.7" figure placed into a non-square PPTX slot gets stretched/squished
- The function preserves resolution (generates at default scale) while matching the target shape's proportions
- Figures 6, 7, 8 all use this for panels a through h

**`slide_layout.json` format:**
```json
{
    "slides": {
        "6": {
            "Fig_6a": {"w": 1555750, "h": 1555750, "x": 274320, "y": 731520},
            "Fig_6b": {"w": 1555750, "h": 1555750, "x": 1966820, "y": 731520},
            ...
        }
    }
}
```
Dimensions are in EMU (English Metric Units): 914400 EMU = 1 inch.

**To update `slide_layout.json` after manual PPTX edits:**
```bash
python generate_paper_figures.py --extract-layout
```

### `render_scale` — High-Resolution Rendering for Small Panels

Some panels (e.g., ROC curves) are displayed small in PPTX (1.7") but need crisp text. The solution: render at a multiple of the display size, then save with `exact_size=True` at the target dimensions.

**How it works:**
```python
_def_a = (SQUARE_SIZE, SQUARE_SIZE)   # Display size: 1.7" × 1.7"
size_a = get_layout_size(fig_num, 'a', default=_def_a) or _def_a

render_scale = 2.0  # Render at 2x size for crisp text
fig, ax = plt.subplots(figsize=(size_a[0] * render_scale, size_a[1] * render_scale))
# figsize is now 3.4" × 3.4" — all text/lines are physically larger

# Scale ALL font sizes by render_scale so they appear correct at display size
ax.set_xlabel('False Positive Rate', fontsize=8 * render_scale)   # 16pt
ax.set_ylabel('True Positive Rate', fontsize=8 * render_scale)    # 16pt
ax.set_title('AUC ROC', fontsize=9 * render_scale, fontweight='bold')  # 18pt
ax.legend(fontsize=4.5 * render_scale)   # 9pt
ax.tick_params(labelsize=7 * render_scale)  # 14pt

# Save at the DISPLAY size (not render size) — PPTX sees a 1.7" image with 2x detail
save_figure(fig, fig_num, 'a', 'ROC Curve',
            {'ROC_Data': roc_df}, width=SQUARE_SIZE, height=SQUARE_SIZE, exact_size=True)
```

**Key rules for `render_scale`:**
1. Multiply `figsize` by `render_scale` to create a larger canvas
2. Multiply ALL font sizes and line widths by `render_scale`
3. Save with `exact_size=True` and `width`/`height` set to the DISPLAY size (not render size)
4. The saved image will be 600 DPI at `render_scale × display_size` — PowerPoint scales it down, keeping it sharp

**Currently used for:**
- Panel a (ROC curves): `render_scale = 2.0`
- Panel g (ROC comparisons in Fig 6/7): `render_scale = 3.0`

### Compound Panels — One Letter, Multiple Images

Some panels consist of multiple side-by-side images sharing a single panel letter. The `COMPOUND_PANELS` dict maps `(fig_id, letter)` to a list of filename suffixes.

```python
COMPOUND_PANELS = {
    # Panel 3a: two heatmaps side-by-side
    ('3', 'a'): ['1', '2'],
    # Panel 3b: four 3D surfaces in 2×2 grid + shared colorbar
    # Order matches position sort: top-left, top-right, colorbar, bottom-left, bottom-right
    ('3', 'b'): ['1', '2', 'colorbar', '3', '4'],
    # Panel 3e: two 3D surfaces (O2 + Contractility)
    ('3', 'e'): ['O2', 'Contractility'],
}
```

**File naming for compound panels:**
```
Fig_{FigureID}{Letter}_{Suffix}.png
```
Examples:
- `Fig_3a_1.png`, `Fig_3a_2.png` — Panel 3a sub-images
- `Fig_3b_1.png`, `Fig_3b_2.png`, `Fig_3b_colorbar.png`, `Fig_3b_3.png`, `Fig_3b_4.png`
- `Fig_3e_O2.png`, `Fig_3e_Contractility.png`

**How compound panels affect the PPTX pipeline:**
1. **Image slot counting:** Each suffix uses one image slot in the PPTX. Panel 3b needs 5 slots even though it's one "panel."
2. **Position sorting:** The update function assigns sub-images to PPTX slots in position order (top-left first, reading left-to-right, top-to-bottom).
3. **Outlier detection:** For compound panels with ≥3 images, the script checks if any assigned slot is >1.0" from the median x-position. If so, it swaps that slot with a closer non-panel image to keep the grid intact.
4. **Panel labels:** All sub-images within a compound panel get the SAME panel letter label in the PPTX grouping.

**Adding a new compound panel:**
1. Add the entry to `COMPOUND_PANELS`
2. Generate each sub-image with the matching suffix filename
3. Ensure the PPTX slide has enough image slots (the script auto-adds slots if needed)
4. Registry entry goes under the main letter (e.g., `('3', 'b')`) — not per sub-image

### `MANUAL_GROUP_SLIDES` — Slides Excluded from Auto-Grouping

```python
MANUAL_GROUP_SLIDES = {3, 4, 5}
```

The `_add_panel_labels()` function normally auto-groups each `(image, letter-label)` pair into `<p:grpSp>` groups in the PPTX XML. **Slides in `MANUAL_GROUP_SLIDES` are skipped** — the user manages groups and labels manually in PowerPoint.

**Why certain slides are manual:**
- **Slide 3:** Complex layout with compound panels (heatmaps, 2×2 surface grid, scatter plot). Auto-grouping can't handle the nested structure.
- **Slides 4 & 5:** 5×5 drug grids with 25+ individual images. Grouping is done by the grid generation scripts, not the main pipeline.

**If you add a new slide that needs manual layout control,** add its slide number to `MANUAL_GROUP_SLIDES`.

### PowerPoint Update Pipeline (OOXML XML Approach)

**IMPORTANT: The script does NOT use `python-pptx` for updates.** It uses raw OOXML XML manipulation:

```
1. UNPACK:  Cardiac_RODEO_Tracked.pptx → workspace/pptx_unpack/ (ZIP extraction)
2. MAP:     Read slide XML rels to find which imageN.png corresponds to each panel
3. REPLACE: Copy new PNGs over the existing media files in ppt/media/
4. LABELS:  Add/update panel letter labels in slide XML
5. REPACK:  workspace/pptx_unpack/ → Cardiac_RODEO_Tracked.pptx (ZIP compression)
```

**Scripts used:**
- `~/.claude/skills/pptx/ooxml/scripts/unpack.py` — extracts PPTX to directory
- `~/.claude/skills/pptx/ooxml/scripts/pack.py` — recompresses directory to PPTX

**Image mapping strategies (in order of priority):**

1. **Explicit rId maps** (slides 2, 3): `SLIDE2_RID_MAP`, `SLIDE3_RID_MAP` — hardcoded `rId → source_filename` mappings that bypass position sorting entirely. Used for slides with complex layouts where position sorting would fail.

2. **Position-based sorting** (all other slides): Reads image positions from slide XML, sorts by visual position (top-to-bottom, left-to-right), then assigns panels in letter order.

**Offset parameter in `_get_mappings()`:**
```python
# Each mapping tuple: (fig_prefix, letters, slide_num, offset)
('Fig_2', 'ijkl', 2, -1),   # offset=-1: panels aligned to LAST images on slide
('Fig_6', 'abcdefgh', 6),   # offset=0 (default): panels start at first image
```
- `offset=0`: Panels start at the first image (most common)
- `offset=-1`: Panels are the last N images on the slide (external images come first)
- `offset=N>0`: Skip the first N images (they are external)

**What happens to excess image slots:**
If a slide has more image slots than panels, excess slots beyond the panels are blanked (replaced with 1×1 transparent PNGs) — unless the image is shared with another slide or the slide uses an offset.

### Figure-to-Slide Mapping Reference

```python
_get_mappings() returns:
    ('Fig_1', '', 1),            # External schematic (not auto-updated)
    ('Fig_2', 'ijkl', 2, -1),   # Generated panels are last 4 images
    ('Fig_3', 'abcde', 3),      # 5 panels (a,b have compound sub-images)
    ('Fig_4', '', 4),            # O2 5×5 grid (managed by separate script)
    ('Fig_5', '', 5),            # Contractility 5×5 grid (separate script)
    ('Fig_6', 'abcdefgh', 6),   # Arrhythmia + Heart Damage + MoLFormer comparison
    ('Fig_7', 'abcdefgh', 7),   # Arrhythmia + Heart Damage + ADMET comparison
    ('Fig_8', 'abcdef', 8),     # Concern Binary (no comparison panels g/h)
    ('Fig_S1', 'abc', 9),       # Supplement: Vandetanib heatmaps
    ('Fig_S2', 'ab', 10),       # Supplement: Daunorubicin 2D time series
    ('Fig_S3', 'a', 11),        # Supplement: Other models scatter
    ('Fig_S4', 'ab', 12),       # Supplement: LOOCV comparison
```

**Auto-extension:** `_get_effective_mappings()` auto-discovers extra panels if a slide has more images than the base mapping. This is used by `--extract-layout` and `_add_panel_labels()` but NOT by `update_powerpoint()` (which only replaces known panels).
