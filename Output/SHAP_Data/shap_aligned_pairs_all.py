"""
SHAP Aligned Positive-Negative Pairs Plot - All Targets

Creates aligned SHAP pair plots for:
1. Arrhythmia
2. Heart Damage (Cardiac Toxicity)

Excludes zero and near-zero SHAP values for visual clarity.
Also exports data to Excel for external plotting.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path for figure_config import
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

# Import figure_config FIRST to set up Helvetica and consistent font sizes
import figure_config
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Paths
SHAP_DIR = Path(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\Output\SHAP_Data')
CLEANED_DIR = Path(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\Cleaned_Data')

# Load drug classification
drug_class = pd.read_csv(CLEANED_DIR / 'drug_classification.csv')

# Create dictionaries for each target
def get_label_map(drug_class_df, column):
    """Create drug -> boolean map for a target column."""
    label_map = {}
    for _, row in drug_class_df.iterrows():
        drug = row['Drug']
        val = row[column]
        if isinstance(val, str):
            label_map[drug] = val.lower() == 'true'
        else:
            label_map[drug] = bool(val)
    return label_map

arrhythmia_map = get_label_map(drug_class, 'Arrhythmia')
heart_damage_map = get_label_map(drug_class, 'heart_damage')

# Create concern_binary map (most = True, less/no = False)
concern_binary_map = {}
for _, row in drug_class.iterrows():
    drug = row['Drug']
    concern = row['Concern']
    concern_binary_map[drug] = str(concern).lower() == 'most'

# Count positive class drugs
n_arrhythmogenic = sum(arrhythmia_map.values())
n_cardiotoxic = sum(heart_damage_map.values())
n_concern_binary = sum(concern_binary_map.values())
print(f"Arrhythmogenic drugs: {n_arrhythmogenic}/25")
print(f"Cardiotoxic drugs: {n_cardiotoxic}/25")
print(f"Most concern drugs: {n_concern_binary}/25")

# Settings - with visible white gaps between lines (aligned pairs style like ver3)
color_positive_class = '#1f77b4'  # Blue for positive class
color_negative_class = '#888888'  # Grey for negative class
line_width = 1.5  # Line thickness (slightly thicker for visibility)
feature_spacing = 2.0  # Larger spacing between features for clear separation
line_spacing = 0.08  # Larger spacing between individual lines for visible white gaps
ZERO_THRESHOLD = 1e-6  # Exclude SHAP values smaller than this

# PowerPoint-linked output directory
PPTX_OUTPUT_DIR = Path(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO\Output\PowerPoint_Figures\Fig_SHAP')
PPTX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def create_aligned_pairs_plot(shap_csv_path, label_map, target_name, positive_label, negative_label, output_prefix, n_positive_class):
    """
    Create aligned positive-negative SHAP pairs plot.

    Drugs with |SHAP| < threshold are excluded for visual clarity.
    Returns data for Excel export and exclusion statistics.
    """
    # Load SHAP values
    shap_df = pd.read_csv(shap_csv_path)

    # Get feature columns
    feature_cols = [col for col in shap_df.columns if col != 'Drug']

    # Calculate mean SHAP (signed) and select top 5 by |mean|
    mean_shap = shap_df[feature_cols].mean()
    top_5_features = mean_shap.abs().nlargest(5).index.tolist()

    print(f"\n{'='*60}")
    print(f"Target: {target_name}")
    print(f"{'='*60}")
    print("Top 5 features by |mean SHAP|:")
    for i, feat in enumerate(top_5_features, 1):
        print(f"  {i}. {feat}: mean={mean_shap[feat]:.6f}")

    # Create figure - sized for PowerPoint with more vertical space for white gaps
    fig, ax = plt.subplots(figsize=(3.4, 3.2))

    # Data storage for Excel export
    excel_data = []
    exclusion_stats = []

    y_positions = []
    y_labels = []

    for feat_idx, feature in enumerate(reversed(top_5_features)):
        base_y = feat_idx * feature_spacing
        y_positions.append(base_y)
        y_labels.append(feature)

        # Get SHAP values and drug names
        values = shap_df[feature].values
        drugs = shap_df['Drug'].values

        # Count excluded drugs
        n_excluded = sum(abs(v) < ZERO_THRESHOLD for v in values)
        exclusion_stats.append((feature, n_excluded))

        # Split into positive and negative, excluding near-zero
        positive_data = [(v, d) for v, d in zip(values, drugs) if v >= ZERO_THRESHOLD]
        negative_data = [(abs(v), d) for v, d in zip(values, drugs) if v <= -ZERO_THRESHOLD]

        # Sort DESCENDING by magnitude (largest first)
        positive_data = sorted(positive_data, key=lambda x: x[0], reverse=True)
        negative_data = sorted(negative_data, key=lambda x: x[0], reverse=True)

        n_pairs = min(len(positive_data), len(negative_data))
        unpaired_positive = positive_data[n_pairs:]
        unpaired_negative = negative_data[n_pairs:]

        # Draw paired lines
        for i in range(n_pairs):
            y = base_y + i * line_spacing
            pos_val, pos_drug = positive_data[i]
            neg_val, neg_drug = negative_data[i]

            pos_is_positive_class = label_map.get(pos_drug, False)
            neg_is_positive_class = label_map.get(neg_drug, False)

            pos_color = color_positive_class if pos_is_positive_class else color_negative_class
            neg_color = color_positive_class if neg_is_positive_class else color_negative_class

            # Draw lines with spacing (white background shows through as gaps)
            ax.hlines(y, 0, pos_val, colors=pos_color, linewidth=line_width)
            ax.hlines(y, -neg_val, 0, colors=neg_color, linewidth=line_width)

            # Store for Excel
            excel_data.append({
                'Feature': feature,
                'Pair_Index': i,
                'Y_Position': y,
                'Positive_SHAP': pos_val,
                'Positive_Drug': pos_drug,
                'Positive_Actual_Class': positive_label if pos_is_positive_class else negative_label,
                'Negative_SHAP': -neg_val,
                'Negative_Drug': neg_drug,
                'Negative_Actual_Class': positive_label if neg_is_positive_class else negative_label,
            })

        # Draw unpaired positive lines
        for i, (pos_val, pos_drug) in enumerate(unpaired_positive):
            y = base_y + (n_pairs + i) * line_spacing
            pos_is_positive_class = label_map.get(pos_drug, False)
            pos_color = color_positive_class if pos_is_positive_class else color_negative_class
            ax.hlines(y, 0, pos_val, colors=pos_color, linewidth=line_width)

            excel_data.append({
                'Feature': feature,
                'Pair_Index': n_pairs + i,
                'Y_Position': y,
                'Positive_SHAP': pos_val,
                'Positive_Drug': pos_drug,
                'Positive_Actual_Class': positive_label if pos_is_positive_class else negative_label,
                'Negative_SHAP': None,
                'Negative_Drug': None,
                'Negative_Actual_Class': None,
            })

        # Draw unpaired negative lines
        for i, (neg_val, neg_drug) in enumerate(unpaired_negative):
            y = base_y + (n_pairs + len(unpaired_positive) + i) * line_spacing
            neg_is_positive_class = label_map.get(neg_drug, False)
            neg_color = color_positive_class if neg_is_positive_class else color_negative_class
            ax.hlines(y, -neg_val, 0, colors=neg_color, linewidth=line_width)

            excel_data.append({
                'Feature': feature,
                'Pair_Index': n_pairs + len(unpaired_positive) + i,
                'Y_Position': y,
                'Positive_SHAP': None,
                'Positive_Drug': None,
                'Positive_Actual_Class': None,
                'Negative_SHAP': -neg_val,
                'Negative_Drug': neg_drug,
                'Negative_Actual_Class': positive_label if neg_is_positive_class else negative_label,
            })

    # Formatting - sized for visibility with white gaps
    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=9)
    ax.set_xlabel('SHAP value', fontsize=10)

    # Title
    title = f'Aligned positive-negative SHAP pairs: {target_name}'
    ax.set_title(title, fontsize=11)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_ylim(-0.5, len(top_5_features) * feature_spacing + 0.5)

    # Legend - upper right like ver3
    legend_elements = [
        Line2D([0], [0], color=color_positive_class, linewidth=2, label=f'{positive_label} ({n_positive_class})'),
        Line2D([0], [0], color=color_negative_class, linewidth=2, label=f'{negative_label} ({25 - n_positive_class})')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8, framealpha=0.9,
              handlelength=1.5, handletextpad=0.4, borderpad=0.3)

    plt.tight_layout()

    # Save to SHAP_DIR
    pdf_path = SHAP_DIR / f'{output_prefix}.pdf'
    png_path = SHAP_DIR / f'{output_prefix}.png'
    plt.savefig(pdf_path, dpi=300, bbox_inches='tight')
    plt.savefig(png_path, dpi=600, bbox_inches='tight')

    # Also save to PowerPoint-linked directory (these files will auto-update in PowerPoint)
    pptx_png_path = PPTX_OUTPUT_DIR / f'{output_prefix}.png'
    pptx_pdf_path = PPTX_OUTPUT_DIR / f'{output_prefix}.pdf'
    plt.savefig(pptx_png_path, dpi=600, bbox_inches='tight')
    plt.savefig(pptx_pdf_path, bbox_inches='tight')
    plt.close()

    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")
    print(f"Saved (PowerPoint link): {pptx_png_path}")
    print(f"\nExclusion statistics (|SHAP| < {ZERO_THRESHOLD}):")
    for feat, n_excl in exclusion_stats:
        print(f"  {feat}: {n_excl} drugs excluded")

    return pd.DataFrame(excel_data), top_5_features, exclusion_stats

# ============================================================================
# Generate plots for both targets
# ============================================================================

# Arrhythmia
arr_data, arr_features, arr_excl = create_aligned_pairs_plot(
    shap_csv_path=SHAP_DIR / 'shap_arrhythmia_values.csv',
    label_map=arrhythmia_map,
    target_name='Arrhythmia',
    positive_label='Arrhythmogenic',
    negative_label='Not arrhythmogenic',
    output_prefix='shap_aligned_arrhythmia',
    n_positive_class=n_arrhythmogenic
)

# Heart Damage
hd_data, hd_features, hd_excl = create_aligned_pairs_plot(
    shap_csv_path=SHAP_DIR / 'shap_heart_damage_values.csv',
    label_map=heart_damage_map,
    target_name='Heart Damage',
    positive_label='Cardiotoxic',
    negative_label='Not cardiotoxic',
    output_prefix='shap_aligned_heart_damage',
    n_positive_class=n_cardiotoxic
)

# Concern Binary (most concern vs less/no concern)
cb_data, cb_features, cb_excl = create_aligned_pairs_plot(
    shap_csv_path=SHAP_DIR / 'shap_concern_binary_values.csv',
    label_map=concern_binary_map,
    target_name='Concern (Binary)',
    positive_label='Most Concern',
    negative_label='Less/No Concern',
    output_prefix='shap_aligned_concern_binary',
    n_positive_class=n_concern_binary
)

# ============================================================================
# Export to Excel for external plotting
# ============================================================================

excel_path = SHAP_DIR / 'shap_aligned_pairs_data.xlsx'

with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    # Arrhythmia plot data
    arr_data.to_excel(writer, sheet_name='Arrhythmia_PlotData', index=False)

    # Heart Damage plot data
    hd_data.to_excel(writer, sheet_name='HeartDamage_PlotData', index=False)

    # Concern Binary plot data
    cb_data.to_excel(writer, sheet_name='ConcernBinary_PlotData', index=False)

    # Exclusion statistics
    excl_df = pd.DataFrame({
        'Target': ['Arrhythmia'] * len(arr_excl) + ['Heart Damage'] * len(hd_excl) + ['Concern Binary'] * len(cb_excl),
        'Feature': [f for f, _ in arr_excl] + [f for f, _ in hd_excl] + [f for f, _ in cb_excl],
        'Drugs_Excluded': [n for _, n in arr_excl] + [n for _, n in hd_excl] + [n for _, n in cb_excl]
    })
    excl_df.to_excel(writer, sheet_name='Exclusion_Stats', index=False)

    # Raw SHAP values for arrhythmia (all features)
    arr_shap = pd.read_csv(SHAP_DIR / 'shap_arrhythmia_values.csv')
    arr_shap.to_excel(writer, sheet_name='Arrhythmia_RawSHAP', index=False)

    # Raw SHAP values for heart damage (all features)
    hd_shap = pd.read_csv(SHAP_DIR / 'shap_heart_damage_values.csv')
    hd_shap.to_excel(writer, sheet_name='HeartDamage_RawSHAP', index=False)

    # Raw SHAP values for concern binary (all features)
    cb_shap = pd.read_csv(SHAP_DIR / 'shap_concern_binary_values.csv')
    cb_shap.to_excel(writer, sheet_name='ConcernBinary_RawSHAP', index=False)

    # Drug classifications
    drug_class.to_excel(writer, sheet_name='DrugClassifications', index=False)

    # Feature ranking summary
    arr_mean = arr_shap[[c for c in arr_shap.columns if c != 'Drug']].mean()
    hd_mean = hd_shap[[c for c in hd_shap.columns if c != 'Drug']].mean()
    cb_mean = cb_shap[[c for c in cb_shap.columns if c != 'Drug']].mean()

    feature_summary = pd.DataFrame({
        'Feature': arr_mean.index,
        'Arrhythmia_MeanSHAP': arr_mean.values,
        'Arrhythmia_AbsMeanSHAP': arr_mean.abs().values,
        'HeartDamage_MeanSHAP': hd_mean.values,
        'HeartDamage_AbsMeanSHAP': hd_mean.abs().values,
        'ConcernBinary_MeanSHAP': cb_mean.values,
        'ConcernBinary_AbsMeanSHAP': cb_mean.abs().values,
    })
    feature_summary = feature_summary.sort_values('Arrhythmia_AbsMeanSHAP', ascending=False)
    feature_summary.to_excel(writer, sheet_name='FeatureRanking', index=False)

    # Instructions sheet
    instructions = pd.DataFrame({
        'Item': [
            'Purpose',
            'Plot structure',
            'Exclusion threshold',
            'Arrhythmia_PlotData',
            'HeartDamage_PlotData',
            'Exclusion_Stats',
            'How to recreate',
            'Color scheme',
        ],
        'Description': [
            'Data for recreating aligned SHAP pair plots externally',
            'Drugs sorted by |SHAP| (largest at top). Positive SHAP extends right, negative extends left.',
            f'Drugs with |SHAP| < {ZERO_THRESHOLD} are excluded from plots for visual clarity',
            'Plot data with Y positions, paired SHAP values, drug names, actual class',
            'Same structure for heart damage',
            'Number of drugs excluded per feature due to near-zero SHAP',
            'For each row: draw hline from 0 to Positive_SHAP or from Negative_SHAP to 0. Color by Actual_Class.',
            'Blue (#1f77b4) = positive class, Grey (#888888) = negative class',
        ]
    })
    instructions.to_excel(writer, sheet_name='README', index=False)

print(f"\n{'='*60}")
print(f"Excel export saved to: {excel_path}")
print(f"{'='*60}")

# Create exclusion summary for LaTeX
total_arr_excl = sum(n for _, n in arr_excl)
total_hd_excl = sum(n for _, n in hd_excl)
total_cb_excl = sum(n for _, n in cb_excl)
print(f"\nTotal exclusions:")
print(f"  Arrhythmia: {total_arr_excl} drug-feature combinations")
print(f"  Heart Damage: {total_hd_excl} drug-feature combinations")
print(f"  Concern Binary: {total_cb_excl} drug-feature combinations")

print(f"\nPowerPoint-linked figures saved to: {PPTX_OUTPUT_DIR}")
print("To use in PowerPoint: Insert > Pictures > This Device > [dropdown] Link to File")
