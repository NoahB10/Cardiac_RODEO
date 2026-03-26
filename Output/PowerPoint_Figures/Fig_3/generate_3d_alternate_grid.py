"""
Generate Fig_3d_alternate_grid: 3x3 grid of Accuracy vs AUC scatter.
Rows = equations (surfaces), Columns = targets (Arrhythmia, Heart Damage, Concern).
Color = model type. X-axis labels only on bottom row. Y-axis labels only on left column.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
loocv_path = PROJECT_ROOT / 'Output' / 'Performance_Metrics' / 'loocv_results.csv'
out_dir = Path(__file__).resolve().parent  # Fig_3 folder

# --- Model colors (distinct, colorblind-friendly) ---
model_colors = {
    'RandomForest': '#2ca02c',   # green
    'SVM_RBF':      '#1f77b4',   # blue
    'XGBoost':      '#ff7f0e',   # orange
    'GaussianNB':   '#9467bd',   # purple
}

model_display = {
    'RandomForest': 'Random Forest',
    'SVM_RBF':      'SVM RBF',
    'XGBoost':      'XGBoost',
    'GaussianNB':   'Gaussian NB',
}

equations = ['pkpd_elimination', 'dual_exponential', 'modified_hill_hormesis']
eq_labels = {
    'pkpd_elimination': 'Surface 11',
    'dual_exponential': 'Surface 1',
    'modified_hill_hormesis': 'Surface 4',
}

targets = ['Arrhythmia', 'heart_damage', 'Concern_Binary']
target_titles = {'Arrhythmia': 'Arrhythmia', 'heart_damage': 'Heart Damage', 'Concern_Binary': 'Concern'}
all_models = ['RandomForest', 'SVM_RBF', 'XGBoost', 'GaussianNB']

# --- Load data ---
loocv_df = pd.read_csv(loocv_path)

# --- Plot: 3 rows (equations) x 3 cols (targets) using gridspec for tight control ---
cell = 2.0  # each cell is 2x2 inches
gap = 0.15  # gap between cells in inches
grid_w = cell * 3 + gap * 2
grid_h = cell * 3 + gap * 2
legend_w = 1.6
margin_l, margin_r, margin_t, margin_b = 0.7, 0.5, 0.4, 0.7

fig_w = margin_l + grid_w + margin_r + legend_w
fig_h = margin_b + grid_h + margin_t

fig = plt.figure(figsize=(fig_w, fig_h))

# GridSpec with equal spacing
gs = gridspec.GridSpec(3, 3, figure=fig,
                       left=margin_l / fig_w,
                       right=(margin_l + grid_w) / fig_w,
                       bottom=margin_b / fig_h,
                       top=(margin_b + grid_h) / fig_h,
                       wspace=gap / cell,
                       hspace=gap / cell)

axes = np.empty((3, 3), dtype=object)
for r in range(3):
    for c in range(3):
        axes[r, c] = fig.add_subplot(gs[r, c])

for row_idx, eq in enumerate(equations):
    for col_idx, target in enumerate(targets):
        ax = axes[row_idx, col_idx]

        subset = loocv_df[(loocv_df['Equation'] == eq) & (loocv_df['Target'] == target)]

        for _, r in subset.iterrows():
            model = r['Model']
            if model in model_colors:
                ax.scatter(r['Accuracy'], r['AUC'], c=model_colors[model],
                           marker='o', s=70, edgecolors='black', linewidth=0.7,
                           zorder=3, alpha=0.9)

        ax.plot([0, 1], [0, 1], color='gray', linestyle='--', alpha=0.5, linewidth=1, zorder=1)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=7)

        # Column titles (top row only)
        if row_idx == 0:
            ax.set_title(target_titles[target], fontsize=10, fontweight='bold')

        # Y-axis label (left column only)
        if col_idx == 0:
            ax.set_ylabel('AUC ROC', fontsize=9, fontweight='bold')
            ax.set_yticklabels(['0', '0.25', '0.5', '0.75', '1.0'])
        else:
            ax.tick_params(labelleft=False)

        # X-axis labels only on bottom row
        if row_idx == 2:
            ax.set_xlabel('Prediction\nAccuracy', fontsize=9, fontweight='bold')
            ax.set_xticklabels(['0', '0.25', '0.5', '0.75', '1.0'])
        else:
            ax.tick_params(labelbottom=False)

        # Row label on the right side of rightmost column
        if col_idx == 2:
            ax.annotate(eq_labels[eq], xy=(1.08, 0.5), xycoords='axes fraction',
                        fontsize=9, fontweight='bold', ha='left', va='center',
                        rotation=-90)

# --- Legend (models as colors) ---
legend_handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=model_colors[m],
                         markersize=8, label=model_display[m], markeredgecolor='black', markeredgewidth=0.7)
                  for m in all_models]

fig.legend(handles=legend_handles, title='Model', loc='center right',
           bbox_to_anchor=(0.99, 0.5), fontsize=8, title_fontsize=9)

# --- Save ---
out_path = out_dir / 'Fig_3d_alternate_grid.png'
fig.savefig(out_path, dpi=600, facecolor='white')
plt.close(fig)
print(f"Saved: {out_path}")

# --- Data excel ---
loocv_df_full = loocv_df.copy()
loocv_df_full['Source'] = str(loocv_path)
plotted = loocv_df[(loocv_df['Target'].isin(targets)) & (loocv_df['Model'].isin(all_models))]

excel_path = out_dir / 'Fig_3d_alternate_grid_data.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    loocv_df_full.to_excel(writer, sheet_name='LOOCV_Full', index=True)
    plotted.to_excel(writer, sheet_name='LOOCV_Plotted', index=True)
print(f"Saved: {excel_path}")
