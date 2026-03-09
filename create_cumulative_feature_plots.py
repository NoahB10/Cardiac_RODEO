"""
Create PNG plots for Cumulative Feature Importance with threshold lines.
Reads data from Excel and generates separate plots for each target.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import json
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_PATH = PROJECT_ROOT / 'Output' / 'Cumulative_Plot_Data' / 'cumulative_feature_importance.xlsx'
THRESHOLD_PATH = PROJECT_ROOT / 'Output' / 'Prediction_Scatter_Data' / 'prediction_thresholds.json'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / 'Excel_Figures'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load thresholds
with open(THRESHOLD_PATH, 'r') as f:
    thresholds = json.load(f)

# Threshold mapping for each sheet
THRESHOLD_MAP = {
    'Arrhythmia': thresholds['Arrhythmia_threshold_pct'],
    'Heart Damage': thresholds['Heart_Damage_threshold_pct'],
    'Concern Binary': thresholds['Concern_Binary_threshold_pct'],
    'Concern No': thresholds['Concern_thresholds_pct']['No Concern'],
    'Concern Less': thresholds['Concern_thresholds_pct']['Less Concern'],
    'Concern Most': thresholds['Concern_thresholds_pct']['Most Concern'],
}

# Colors for plots
PLOT_COLORS = {
    'Arrhythmia': 'tab:blue',
    'Heart Damage': 'tab:red',
    'Concern Binary': 'tab:purple',
    'Concern No': 'tab:green',
    'Concern Less': 'tab:orange',
    'Concern Most': 'tab:red',
}

def create_cumulative_plot(df, sheet_name, threshold, output_dir):
    """Create cumulative feature importance plot with threshold line."""

    fig, ax = plt.subplots(figsize=(14, 8))

    # Get feature labels (first column)
    features = df['Cumulative_Coefficients'].values
    n_features = len(features)

    # Get drug columns (all except first)
    drug_cols = [col for col in df.columns if col != 'Cumulative_Coefficients']

    # Create rainbow colormap for drugs
    drug_list = sorted(drug_cols)
    cmap = plt.get_cmap('rainbow')
    color_map = {
        drug: cmap(0.0 if len(drug_list) == 1 else i / (len(drug_list) - 1))
        for i, drug in enumerate(drug_list)
    }

    # Plot each drug
    x = np.arange(1, n_features + 1)
    for drug in drug_list:
        y = df[drug].values
        ax.plot(x, y, marker='o', label=drug, alpha=0.7, linewidth=1.5,
                markersize=4, color=color_map[drug])

    # Add threshold line
    ax.axhline(y=threshold, color='red', linestyle='--', linewidth=2.5,
               label=f'Threshold = {threshold:.1f}%')

    # Create x-tick labels (stacked feature names)
    def stacked_label(rank):
        parts = features[rank-1].split(' + ')
        if len(parts) <= 5:
            return '\n'.join(parts)
        else:
            return '\n'.join(parts[:5]) + f'\n... (+{len(parts)-5})'

    xtick_labels = [stacked_label(i) for i in range(1, n_features + 1)]

    # Formatting
    ax.set_xticks(x)
    ax.set_xticklabels(xtick_labels, rotation=45, ha='right', fontsize=7)
    ax.set_yticks(np.linspace(0, 100, 11))
    ax.set_ylim(0, 100)
    ax.set_xlabel('Cumulative Features (ranked by importance)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Predicted Probability (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Cumulative Feature Importance - {sheet_name}', fontsize=14, fontweight='bold')
    ax.grid(True, axis='y', alpha=0.3)

    # Legend outside plot
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', ncol=1, fontsize=8)

    plt.tight_layout()

    # Save
    safe_name = sheet_name.replace(' ', '_')
    png_path = output_dir / f'Cumulative_Feature_Importance_{safe_name}.png'
    fig.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"Saved: {png_path.name}")


# Main
print("="*60)
print("CREATING CUMULATIVE FEATURE IMPORTANCE PLOTS")
print("="*60)

# Load Excel
xlsx = pd.ExcelFile(DATA_PATH)

for sheet_name in xlsx.sheet_names:
    print(f"\nProcessing: {sheet_name}")
    df = pd.read_excel(xlsx, sheet_name=sheet_name)
    threshold = THRESHOLD_MAP.get(sheet_name, 50.0)
    create_cumulative_plot(df, sheet_name, threshold, OUTPUT_DIR)

print("\n" + "="*60)
print("COMPLETE!")
print("="*60)
print(f"\nOutput directory: {OUTPUT_DIR}")
