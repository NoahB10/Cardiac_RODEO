"""Quick regeneration of just Figure 3d with updated x-axis label."""
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
OUT_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures' / 'Fig_3'

COLORS = {
    'blue': '#6C92ED',
    'green': '#7DB88A',
    'dusty_rose': '#C98B8E',
}

loocv_path = PROJECT_ROOT / 'Output' / 'Performance_Metrics' / 'loocv_results.csv'
loocv_df = pd.read_csv(loocv_path)

equation_colors = {
    'pkpd_elimination': COLORS['green'],
    'dual_exponential': COLORS['blue'],
    'modified_hill_hormesis': COLORS['dusty_rose'],
}

targets = ['Arrhythmia', 'heart_damage', 'Concern_Binary']
target_titles = {'Arrhythmia': 'Arrhythmia', 'heart_damage': 'Heart Damage', 'Concern_Binary': 'Concern'}
main_model = 'RandomForest'

panel_size = 2.0
fig_width = panel_size * 3 + 1.5
fig_height = panel_size + 0.6

fig, axes = plt.subplots(1, 3, figsize=(fig_width, fig_height), sharey=True)
fig.subplots_adjust(left=0.10, right=0.78, wspace=0.08, top=0.85, bottom=0.18)

for idx, (target, ax) in enumerate(zip(targets, axes)):
    target_df = loocv_df[(loocv_df['Target'] == target) & (loocv_df['Model'] == main_model)].copy()

    for _, row in target_df.iterrows():
        eq = row['Equation']
        acc = row['Accuracy']
        auc_val = row['AUC']

        if eq in equation_colors:
            ax.scatter(acc, auc_val, c=equation_colors[eq], marker='o',
                      s=60, edgecolors='black', linewidth=0.8, zorder=3)

    ax.plot([0, 1], [0, 1], color='gray', linestyle='--', alpha=0.5, linewidth=1, zorder=1)

    ax.set_xlabel('Coefficient of\nDetermination (R²)', fontsize=9, fontweight='bold')
    if idx == 0:
        ax.set_ylabel('AUC ROC', fontsize=9, fontweight='bold')
    ax.set_title(target_titles[target], fontsize=10, fontweight='bold')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_box_aspect(1)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=7)

_eq_labels = {
    'pkpd_elimination': 'Surface 11',
    'dual_exponential': 'Surface 1',
    'modified_hill_hormesis': 'Surface 4',
}
eq_legend = [Patch(facecolor=c, edgecolor='black',
                   label=_eq_labels.get(eq, eq.replace('_', ' ').title()))
             for eq, c in equation_colors.items()]

fig.legend(handles=eq_legend, title='Surface', loc='center right',
           bbox_to_anchor=(0.98, 0.5), fontsize=7, title_fontsize=8)
fig.suptitle('Random Forest Model', fontsize=8, y=0.98, style='italic')

dst = OUT_DIR / 'Fig_3d.png'
fig.savefig(str(dst), dpi=600, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {dst}")
