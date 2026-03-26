"""
Generate Fig_3d_alternate: Accuracy vs AUC scatter with ALL 4 models.
Combines Fig 3d (RandomForest) + Fig S3a (SVM_RBF, XGBoost, GaussianNB).
Color = equation (surface), shape = model.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
loocv_path = PROJECT_ROOT / 'Output' / 'Performance_Metrics' / 'loocv_results.csv'
out_dir = Path(__file__).resolve().parent  # Fig_3 folder

COLORS = {
    'blue': '#6C92ED',
    'green': '#7DB88A',
    'dusty_rose': '#C98B8E',
}

equation_colors = {
    'pkpd_elimination': COLORS['green'],
    'dual_exponential': COLORS['blue'],
    'modified_hill_hormesis': COLORS['dusty_rose'],
}

model_markers = {
    'RandomForest': 'o',     # circle (same as original 3d)
    'SVM_RBF': 's',          # square
    'XGBoost': '^',          # triangle
    'GaussianNB': 'D',       # diamond
}

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

# --- Plot ---
panel_size = 2.0
fig_width = panel_size * 3 + 1.5
fig_height = panel_size + 0.6

fig, axes = plt.subplots(1, 3, figsize=(fig_width, fig_height), sharey=True)
fig.subplots_adjust(left=0.10, right=0.72, wspace=0.08, top=0.85, bottom=0.25)

for idx, (target, ax) in enumerate(zip(targets, axes)):
    for model in all_models:
        target_df = loocv_df[(loocv_df['Target'] == target) & (loocv_df['Model'] == model)].copy()

        for _, row in target_df.iterrows():
            eq = row['Equation']
            acc = row['Accuracy']
            auc_val = row['AUC']

            if eq in equation_colors:
                ax.scatter(acc, auc_val, c=equation_colors[eq], marker=model_markers[model],
                          s=55, edgecolors='black', linewidth=0.6, zorder=3, alpha=0.85)

    ax.plot([0, 1], [0, 1], color='gray', linestyle='--', alpha=0.5, linewidth=1, zorder=1)

    ax.set_xlabel('Prediction\nAccuracy', fontsize=9, fontweight='bold')
    if idx == 0:
        ax.set_ylabel('AUC ROC', fontsize=9, fontweight='bold')
    ax.set_title(target_titles[target], fontsize=10, fontweight='bold')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(['0', '0.25', '0.5', '0.75', '1.0'])
    if idx == 0:
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(['0', '0.25', '0.5', '0.75', '1.0'])
    ax.set_box_aspect(1)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=7)

# --- Two legends: color = surface, shape = model ---
surface_legend = [Patch(facecolor=c, edgecolor='black',
                        label=eq_labels.get(eq, eq))
                  for eq, c in equation_colors.items()]

model_legend = [Line2D([0], [0], marker=model_markers[m], color='w', markerfacecolor='gray',
                       markersize=7, label=m.replace('_', ' '), markeredgecolor='black')
                for m in all_models]

leg1 = fig.legend(handles=surface_legend, title='Surface', loc='upper right',
                  bbox_to_anchor=(0.99, 0.85), fontsize=7, title_fontsize=8)
fig.legend(handles=model_legend, title='Model', loc='lower right',
           bbox_to_anchor=(0.99, 0.15), fontsize=7, title_fontsize=8)
fig.add_artist(leg1)

# --- Save ---
out_path = out_dir / 'Fig_3d_alternate.png'
fig.savefig(out_path, dpi=600, bbox_inches='tight', facecolor='white')
plt.close(fig)
print(f"Saved: {out_path}")

# --- Also save data excel ---
loocv_df_full = loocv_df.copy()
loocv_df_full['Source'] = str(loocv_path)
plotted = loocv_df[(loocv_df['Target'].isin(targets)) & (loocv_df['Model'].isin(all_models))]

excel_path = out_dir / 'Fig_3d_alternate_data.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    loocv_df_full.to_excel(writer, sheet_name='LOOCV_Full', index=True)
    plotted.to_excel(writer, sheet_name='LOOCV_Plotted', index=True)
print(f"Saved: {excel_path}")
