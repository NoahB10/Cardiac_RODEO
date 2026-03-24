"""Scatter plots of Accuracy vs AUC ROC for all 12 equations.

12 individual images (3 targets x 4 models). Each plot shows all 12
equations as colored dots in Accuracy vs AUC ROC space.

Styling matches existing Fig 3c reference scatter plots.

Output: Output/All_Equations_LOOCV/
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / 'Output' / 'All_Equations_LOOCV'
SAVE_DPI = 600

# 12 colors — spectral ordering (red → orange → yellow → green → blue → purple → pink)
EQUATIONS = [
    ('dual_exponential',       'Dual Exponential',     '#d62728'),  # red
    ('hormesis_v0',            'Hormesis Hill',         '#e6550d'),  # red-orange
    ('pkpd_elimination',       'PKPD Elimination',     '#ff7f0e'),  # orange
    ('biphasic_response',      'Biphasic Response',    '#ffc107'),  # amber
    ('modified_hill_hormesis', 'Dual Hill Hormesis',   '#8bc34a'),  # yellow-green
    ('modified_hill_simple',   'Modified Hill',        '#2ca02c'),  # green
    ('adaptive_response',      'Adaptive Response',    '#00897b'),  # teal
    ('gaussian_ridge',         'Gaussian Ridge',       '#17becf'),  # cyan
    ('bivariate_gaussian',     'Bivariate Gaussian',   '#1f77b4'),  # blue
    ('gaussian_hill_hybrid',   'Gaussian-Hill Hybrid', '#5c6bc0'),  # indigo
    ('recovery_model',         'Recovery Model',       '#9467bd'),  # purple
    ('cumulative_exposure',    'Cumulative Exposure',  '#e377c2'),  # pink
]

TARGETS = {
    'Arrhythmia':     'Arrhythmia',
    'heart_damage':   'Heart Damage',
    'Concern_Binary': 'Concern (Binary)',
}

MODELS = {
    'XGBoost':      'XGBoost',
    'SVM_RBF':      'SVM (RBF)',
    'RandomForest': 'Random Forest',
    'GaussianNB':   'Gaussian NB',
}


def make_plot(df_subset, target_label, model_label, out_path):
    fig, ax = plt.subplots(figsize=(4.5, 4.5))

    # Diagonal — random classifier reference
    ax.plot([0, 1], [0, 1], '--', color='gray', linewidth=1, alpha=0.5, zorder=1)

    # Grid
    ax.grid(True, alpha=0.3, zorder=0)

    # Plot each equation
    for eq_name, eq_label, eq_color in EQUATIONS:
        row = df_subset[df_subset['Equation'] == eq_name]
        if row.empty:
            continue
        ax.scatter(row['Accuracy'].values[0], row['AUC'].values[0],
                   c=eq_color, s=60, zorder=3,
                   edgecolors='black', linewidths=0.8)

    # Axes
    ax.set_xlabel('Prediction\nAccuracy', fontsize=9, fontweight='bold')
    ax.set_ylabel('AUC ROC', fontsize=9, fontweight='bold')
    ax.set_title(f'{target_label} - {model_label}', fontsize=10, fontweight='bold')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(labelsize=7)
    ax.set_box_aspect(1)

    # Legend — right side
    handles = [mlines.Line2D([], [], marker='o', color='w',
                              markerfacecolor=c, markeredgecolor='black',
                              markeredgewidth=0.8, markersize=7, label=lbl)
               for _, lbl, c in EQUATIONS]
    ax.legend(handles=handles, loc='center left',
              bbox_to_anchor=(1.02, 0.5), fontsize=7,
              title='Surface', title_fontsize=8,
              frameon=True, fancybox=True)

    fig.savefig(str(out_path), dpi=SAVE_DPI, bbox_inches='tight',
                pad_inches=0.05, facecolor='white')
    plt.close(fig)


def main():
    df = pd.read_csv(DATA_DIR / 'loocv_all_equations.csv')

    for target_key, target_label in TARGETS.items():
        for model_key, model_label in MODELS.items():
            subset = df[(df['Target'] == target_key) & (df['Model'] == model_key)]
            fname = f'scatter_{target_key}_{model_key}.png'
            out_path = DATA_DIR / fname
            make_plot(subset, target_label, model_label, out_path)
            print(f"Saved: {out_path.relative_to(PROJECT_ROOT)}")

    print(f"\n12 plots saved to {DATA_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == '__main__':
    main()
