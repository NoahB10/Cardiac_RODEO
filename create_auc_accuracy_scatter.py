"""
Create Accuracy vs AUC scatter plots for LOOCV results.
X-axis = Accuracy, Y-axis = AUC
Each point = one (equation, model) combination
Color by equation, marker by model
"""
import figure_config  # FIRST LINE - registers Helvetica
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Setup paths
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures' / 'Fig_4'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load LOOCV results
loocv_df = pd.read_csv(PROJECT_ROOT / 'Output' / 'Performance_Metrics' / 'loocv_results.csv')

# Colors by equation (using project palette)
equation_colors = {
    'dual_exponential': '#e74c3c',       # Red
    'modified_hill_hormesis': '#3498db',  # Blue
    'pkpd_elimination': '#2ecc71',        # Green
}

# Markers by model
model_markers = {
    'XGBoost': 'o',       # Circle
    'SVM_RBF': 's',       # Square
    'RandomForest': '^',  # Triangle
    'GaussianNB': 'D',    # Diamond
}

# Targets to plot
targets = ['Arrhythmia', 'heart_damage', 'Concern_Binary']
target_titles = {
    'Arrhythmia': 'Arrhythmia',
    'heart_damage': 'Heart Damage',
    'Concern_Binary': 'Concern (Binary)'
}

# Create one figure per target
for target in targets:
    target_df = loocv_df[loocv_df['Target'] == target].copy()

    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot each point
    for _, row in target_df.iterrows():
        eq = row['Equation']
        model = row['Model']
        acc = row['Accuracy']
        auc = row['AUC']

        if eq in equation_colors and model in model_markers:
            ax.scatter(
                acc, auc,
                c=equation_colors[eq],
                marker=model_markers[model],
                s=150,
                edgecolors='black',
                linewidth=1,
                zorder=3
            )

    # Reference lines at 0.5 (random baseline)
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)

    # Axis settings
    ax.set_xlabel('Accuracy', fontsize=12, fontweight='bold')
    ax.set_ylabel('AUC', fontsize=12, fontweight='bold')
    ax.set_title(f'Equation Comparison: {target_titles[target]}', fontsize=14, fontweight='bold')
    ax.set_xlim(0.3, 0.9)
    ax.set_ylim(0.1, 1.0)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    # Custom legends
    # Equation colors legend
    eq_legend = [Patch(facecolor=c, edgecolor='black', label=eq.replace('_', ' ').title())
                 for eq, c in equation_colors.items()]

    # Model markers legend
    model_legend = [Line2D([0], [0], marker=m, color='w', markerfacecolor='gray',
                           markersize=10, label=model.replace('_', ' '), markeredgecolor='black')
                    for model, m in model_markers.items()]

    legend1 = ax.legend(handles=eq_legend, title='Equation', loc='upper left', fontsize=9)
    ax.add_artist(legend1)
    ax.legend(handles=model_legend, title='Model', loc='lower right', fontsize=9)

    plt.tight_layout()

    # Save files
    safe_target = target.replace('/', '_').replace(' ', '_')
    fig_path_png = OUTPUT_DIR / f'Fig_4_Accuracy_vs_AUC_{safe_target}.png'
    fig_path_pdf = OUTPUT_DIR / f'Fig_4_Accuracy_vs_AUC_{safe_target}.pdf'

    plt.savefig(fig_path_png, dpi=600, bbox_inches='tight')
    plt.savefig(fig_path_pdf, bbox_inches='tight')
    plt.close()

    print(f"Saved: {fig_path_png}")
    print(f"Saved: {fig_path_pdf}")

# Also create a combined 3-panel figure
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

for idx, (target, ax) in enumerate(zip(targets, axes)):
    target_df = loocv_df[loocv_df['Target'] == target].copy()

    # Plot each point
    for _, row in target_df.iterrows():
        eq = row['Equation']
        model = row['Model']
        acc = row['Accuracy']
        auc = row['AUC']

        if eq in equation_colors and model in model_markers:
            ax.scatter(
                acc, auc,
                c=equation_colors[eq],
                marker=model_markers[model],
                s=120,
                edgecolors='black',
                linewidth=0.8,
                zorder=3
            )

    # Reference lines
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)

    # Axis settings
    ax.set_xlabel('Accuracy', fontsize=11, fontweight='bold')
    ax.set_ylabel('AUC', fontsize=11, fontweight='bold')
    ax.set_title(f'{target_titles[target]}', fontsize=12, fontweight='bold')
    ax.set_xlim(0.3, 0.9)
    ax.set_ylim(0.1, 1.0)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    # Panel label
    panel_label = chr(ord('a') + idx)
    ax.text(-0.12, 1.05, f'({panel_label})', transform=ax.transAxes,
            fontsize=14, fontweight='bold', va='top')

# Add shared legend to the right side
eq_legend = [Patch(facecolor=c, edgecolor='black', label=eq.replace('_', ' ').title())
             for eq, c in equation_colors.items()]
model_legend = [Line2D([0], [0], marker=m, color='w', markerfacecolor='gray',
                       markersize=10, label=model.replace('_', ' '), markeredgecolor='black')
                for model, m in model_markers.items()]

# Place legends outside the last axis
fig.legend(handles=eq_legend, title='Equation', loc='upper right',
           bbox_to_anchor=(0.99, 0.95), fontsize=9)
fig.legend(handles=model_legend, title='Model', loc='lower right',
           bbox_to_anchor=(0.99, 0.05), fontsize=9)

plt.tight_layout(rect=[0, 0, 0.88, 1])

# Save combined figure
combined_path_png = OUTPUT_DIR / 'Fig_4_Accuracy_vs_AUC_Combined.png'
combined_path_pdf = OUTPUT_DIR / 'Fig_4_Accuracy_vs_AUC_Combined.pdf'
plt.savefig(combined_path_png, dpi=600, bbox_inches='tight')
plt.savefig(combined_path_pdf, bbox_inches='tight')
plt.close()

print(f"\nSaved combined figure: {combined_path_png}")
print(f"Saved combined figure: {combined_path_pdf}")

# Save data to Excel for traceability
excel_path = OUTPUT_DIR / 'Fig_4_Accuracy_vs_AUC_data.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    loocv_df.to_excel(writer, sheet_name='LOOCV_Results', index=False)
    metadata = pd.DataFrame({
        'Field': ['Generated', 'Script', 'Source Data'],
        'Value': [pd.Timestamp.now().isoformat(), __file__, 'Output/Performance_Metrics/loocv_results.csv']
    })
    metadata.to_excel(writer, sheet_name='Metadata', index=False)

print(f"Saved Excel data: {excel_path}")
print("\nDone!")
