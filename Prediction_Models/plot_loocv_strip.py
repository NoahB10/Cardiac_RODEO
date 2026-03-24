"""3-panel strip: Accuracy vs AUC ROC for selected model+target combos.

All 12 equations shown as colored dots per panel. No legend.
Shared y-axis on leftmost panel only.

Output: Output/All_Equations_LOOCV/scatter_strip.png
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / 'Output' / 'All_Equations_LOOCV'
SAVE_DPI = 600

# Spectral color scheme
EQUATIONS = [
    ('dual_exponential',       '#d62728'),
    ('hormesis_v0',            '#e6550d'),
    ('pkpd_elimination',       '#ff7f0e'),
    ('biphasic_response',      '#ffc107'),
    ('modified_hill_hormesis', '#8bc34a'),
    ('modified_hill_simple',   '#2ca02c'),
    ('adaptive_response',      '#00897b'),
    ('gaussian_ridge',         '#17becf'),
    ('bivariate_gaussian',     '#1f77b4'),
    ('gaussian_hill_hybrid',   '#5c6bc0'),
    ('recovery_model',         '#9467bd'),
    ('cumulative_exposure',    '#e377c2'),
]

# The 3 chosen panels: (target_key, model_key, panel_title)
PANELS = [
    ('Arrhythmia',     'XGBoost',    'Arrhythmia'),
    ('heart_damage',   'GaussianNB', 'Heart Damage'),
    ('Concern_Binary', 'GaussianNB', 'Concern (Binary)'),
]


def main():
    df = pd.read_csv(DATA_DIR / 'loocv_all_equations.csv')

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))

    for i, (ax, (target, model, title)) in enumerate(zip(axes, PANELS)):
        subset = df[(df['Target'] == target) & (df['Model'] == model)]

        # Diagonal reference
        ax.plot([0, 1], [0, 1], '--', color='gray', linewidth=1, alpha=0.5, zorder=1)

        # Plot each equation
        for eq_name, eq_color in EQUATIONS:
            row = subset[subset['Equation'] == eq_name]
            if row.empty:
                continue
            ax.scatter(row['Accuracy'].values[0], row['AUC'].values[0],
                       c=eq_color, s=70, zorder=3,
                       edgecolors='black', linewidths=0.8)

        # Axes
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(['0', '0.25', '0.5', '0.75', '1'],
                           fontsize=11, fontweight='bold')
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_box_aspect(1)

        ax.set_xlabel('Accuracy', fontsize=14, fontweight='bold')
        ax.set_title(title, fontsize=15, fontweight='bold')

        # Y-axis label only on leftmost
        if i == 0:
            ax.set_ylabel('AUC ROC', fontsize=14, fontweight='bold')
            ax.set_yticklabels(['0', '0.25', '0.5', '0.75', '1'],
                               fontsize=11, fontweight='bold')
        else:
            ax.set_yticklabels([])

        # Thick black spines, no grid
        for spine in ax.spines.values():
            spine.set_edgecolor('black')
            spine.set_linewidth(1.8)
        ax.grid(False)

    fig.tight_layout(w_pad=1.0)

    out_path = DATA_DIR / 'scatter_strip.png'
    fig.savefig(str(out_path), dpi=SAVE_DPI, bbox_inches='tight',
                pad_inches=0.08, facecolor='white')
    plt.close(fig)
    print(f"Saved: {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == '__main__':
    main()
