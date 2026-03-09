"""
SHAP Aligned Positive-Negative Pairs Plot

Creates a compact visualization where positive and negative SHAP values
are paired by magnitude and drawn as symmetric horizontal line segments.
Color indicates actual arrhythmia status: blue = arrhythmogenic, grey = not.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Load SHAP values
shap_df = pd.read_csv(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\Output\SHAP_Data\shap_arrhythmia_values.csv')

# Load drug classification to get actual arrhythmia labels
drug_class = pd.read_csv(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\Cleaned_Data\drug_classification.csv')

# Create a dictionary: drug -> arrhythmia status (True/False)
# Handle different possible formats of the Arrhythmia column
arrhythmia_map = {}
for _, row in drug_class.iterrows():
    drug = row['Drug']
    arr_val = row['Arrhythmia']
    # Convert to boolean
    if isinstance(arr_val, str):
        arrhythmia_map[drug] = arr_val.lower() == 'true'
    else:
        arrhythmia_map[drug] = bool(arr_val)

print("Arrhythmia status per drug:")
for drug, status in arrhythmia_map.items():
    print(f"  {drug}: {'Arrhythmogenic' if status else 'Not arrhythmogenic'}")

# Get feature columns (exclude Drug)
feature_cols = [col for col in shap_df.columns if col != 'Drug']

# Step 1: Calculate MEAN SHAP (signed) for each feature
mean_shap = shap_df[feature_cols].mean()

# Rank by absolute mean SHAP magnitude and select top 5
top_5_features = mean_shap.abs().nlargest(5).index.tolist()

print("\nTop 5 features by |mean SHAP|:")
for i, feat in enumerate(top_5_features, 1):
    print(f"  {i}. {feat}: mean={mean_shap[feat]:.6f}, |mean|={abs(mean_shap[feat]):.6f}")

# Create figure - single plot with all features
fig, ax = plt.subplots(figsize=(12, 6))

# Settings
color_arrhythmogenic = '#1f77b4'  # Blue for arrhythmogenic drugs
color_not_arrhythmogenic = '#888888'  # Grey for non-arrhythmogenic drugs
line_width = 1.5
feature_spacing = 1.0  # Vertical spacing between features
line_spacing = 0.03    # Vertical spacing between lines within a feature

# Process each feature
y_positions = []
y_labels = []

for feat_idx, feature in enumerate(reversed(top_5_features)):  # Reverse so first is at top
    base_y = feat_idx * feature_spacing
    y_positions.append(base_y)
    y_labels.append(feature)

    # Get SHAP values and drug names for this feature
    values = shap_df[feature].values
    drugs = shap_df['Drug'].values

    # Split into positive and negative, keeping track of drug names
    positive_data = [(v, d) for v, d in zip(values, drugs) if v > 0]
    negative_data = [(abs(v), d) for v, d in zip(values, drugs) if v < 0]

    # Sort DESCENDING by magnitude (largest first)
    positive_data = sorted(positive_data, key=lambda x: x[0], reverse=True)
    negative_data = sorted(negative_data, key=lambda x: x[0], reverse=True)

    # Determine number of pairs (minimum of the two sets)
    n_pairs = min(len(positive_data), len(negative_data))

    # Handle "unpaired" values (if one set is larger)
    unpaired_positive = positive_data[n_pairs:] if len(positive_data) > n_pairs else []
    unpaired_negative = negative_data[n_pairs:] if len(negative_data) > n_pairs else []

    # Draw paired lines
    for i in range(n_pairs):
        y = base_y + i * line_spacing
        pos_val, pos_drug = positive_data[i]
        neg_val, neg_drug = negative_data[i]

        # Get colors based on arrhythmia status
        pos_color = color_arrhythmogenic if arrhythmia_map.get(pos_drug, False) else color_not_arrhythmogenic
        neg_color = color_arrhythmogenic if arrhythmia_map.get(neg_drug, False) else color_not_arrhythmogenic

        # Draw positive line (0 to positive value)
        ax.hlines(y, 0, pos_val, colors=pos_color, linewidth=line_width)

        # Draw negative line (-negative magnitude to 0)
        ax.hlines(y, -neg_val, 0, colors=neg_color, linewidth=line_width)

    # Draw unpaired positive lines (if any)
    for i, (pos_val, pos_drug) in enumerate(unpaired_positive):
        y = base_y + (n_pairs + i) * line_spacing
        pos_color = color_arrhythmogenic if arrhythmia_map.get(pos_drug, False) else color_not_arrhythmogenic
        ax.hlines(y, 0, pos_val, colors=pos_color, linewidth=line_width)

    # Draw unpaired negative lines (if any)
    for i, (neg_val, neg_drug) in enumerate(unpaired_negative):
        y = base_y + (n_pairs + i) * line_spacing
        neg_color = color_arrhythmogenic if arrhythmia_map.get(neg_drug, False) else color_not_arrhythmogenic
        ax.hlines(y, -neg_val, 0, colors=neg_color, linewidth=line_width)

# Add vertical line at x=0
ax.axvline(x=0, color='black', linewidth=0.8, linestyle='-')

# Set y-axis labels at feature positions
ax.set_yticks(y_positions)
ax.set_yticklabels(y_labels, fontsize=11)

# Labels and title
ax.set_xlabel('SHAP value', fontsize=12)
ax.set_title('Aligned positive-negative SHAP pairs per feature', fontsize=14)

# Remove top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Add light grid on x-axis only
ax.grid(axis='x', alpha=0.3, linestyle='-')
ax.set_axisbelow(True)

# Adjust y-limits to give some padding
ax.set_ylim(-0.3, len(top_5_features) * feature_spacing + 0.3)

# Add legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], color=color_arrhythmogenic, linewidth=2, label='Arrhythmogenic'),
    Line2D([0], [0], color=color_not_arrhythmogenic, linewidth=2, label='Not arrhythmogenic')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

plt.tight_layout()

# Save
output_path = r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\Output\SHAP_Data\shap_aligned_pairs.pdf'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.savefig(output_path.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')

print(f"\nPlot saved to: {output_path}")
print(f"Plot saved to: {output_path.replace('.pdf', '.png')}")
