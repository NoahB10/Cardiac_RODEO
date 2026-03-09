"""
Regenerate SHAP aligned positive-negative pairs plots with VISIBLE WHITE GAPS.

Key technique: "Make it big then scale down" - large figsize (12x7) at 600 DPI
preserves visual details (white gaps between lines) when displayed smaller.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
from pathlib import Path

# Paths
PROJECT_ROOT = Path(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO')
SHAP_DIR = PROJECT_ROOT / 'Output' / 'SHAP_Data'
PPTX_FIG_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures'

# Settings for aligned pairs plot - BIG figure that scales down with visible white gaps
color_positive = '#1f77b4'  # Blue
color_negative = '#888888'  # Grey
ZERO_THRESHOLD = 1e-6

# Final tuned parameters for visible gaps
FIGSIZE = (12, 7)
LINE_WIDTH = 2.0
FEATURE_SPACING = 0.85
LINE_SPACING = 0.03

def generate_shap_aligned_pairs():
    """Generate SHAP aligned positive-negative pairs plots for binary targets."""

    # Load drug classification
    drug_class_path = PROJECT_ROOT / 'Cleaned_Data' / 'drug_classification.csv'
    drug_class = pd.read_csv(drug_class_path)

    # Target configurations: (shap_prefix, target_col, title, pos_label, neg_label, fig_id, is_concern_binary)
    targets = [
        ('arrhythmia', 'Arrhythmia', 'Arrhythmia', 'Arrhythmogenic', 'Not arrhythmogenic', 'Fig_6f', False),
        ('heart_damage', 'heart_damage', 'Heart Damage', 'Cardiotoxic', 'Not cardiotoxic', 'Fig_7f', False),
        ('concern_binary', 'Concern', 'Concern (Binary)', 'High Concern', 'Low/No Concern', 'Fig_8f', True),
    ]

    for shap_prefix, target_col, title, pos_label, neg_label, fig_id, is_concern_binary in targets:
        shap_file = SHAP_DIR / f'shap_{shap_prefix}_values.csv'
        if not shap_file.exists():
            print(f"  SHAP values file not found: {shap_file}")
            continue

        print(f"Processing {title}...")

        # Load SHAP values
        shap_df = pd.read_csv(shap_file)

        # Create class membership map
        class_map = {}
        for _, row in drug_class.iterrows():
            drug = row['Drug']
            val = row[target_col]
            if is_concern_binary:
                class_map[drug] = val.lower() == 'most' if isinstance(val, str) else False
            elif isinstance(val, str):
                class_map[drug] = val.lower() == 'true'
            else:
                class_map[drug] = bool(val)

        # Get feature columns
        feature_cols = [col for col in shap_df.columns if col != 'Drug']

        # Calculate mean SHAP and get top 5 features by |mean|
        mean_shap = shap_df[feature_cols].mean()
        top_5_features = mean_shap.abs().nlargest(5).index.tolist()

        # Count positive class drugs
        n_positive = sum(1 for d in shap_df['Drug'].values if class_map.get(d, False))

        # Create BIG figure (scales down with visible white gaps)
        fig, ax = plt.subplots(figsize=FIGSIZE)

        y_positions = []
        y_labels = []

        for feat_idx, feature in enumerate(reversed(top_5_features)):
            base_y = feat_idx * FEATURE_SPACING
            y_positions.append(base_y)

            # Clean feature name for display
            display_name = feature.replace('_Contractility', ' (C)').replace('_O2', ' (O₂)')
            display_name = display_name.replace('R0', 'R₀').replace('Emax', 'Eₘₐₓ')
            display_name = display_name.replace('kappa', 'κ').replace('k_elim', 'kₑₗᵢₘ').replace('tau', 'τ')
            y_labels.append(display_name)

            # Get SHAP values and drugs
            values = shap_df[feature].values
            drugs = shap_df['Drug'].values

            # Split into positive and negative SHAP values
            positive_data = [(v, d) for v, d in zip(values, drugs) if v > ZERO_THRESHOLD]
            negative_data = [(abs(v), d) for v, d in zip(values, drugs) if v < -ZERO_THRESHOLD]

            # Sort descending by magnitude
            positive_data = sorted(positive_data, key=lambda x: x[0], reverse=True)
            negative_data = sorted(negative_data, key=lambda x: x[0], reverse=True)

            n_pairs = min(len(positive_data), len(negative_data))
            unpaired_positive = positive_data[n_pairs:]
            unpaired_negative = negative_data[n_pairs:]

            # Draw paired lines
            for i in range(n_pairs):
                y = base_y + i * LINE_SPACING
                pos_val, pos_drug = positive_data[i]
                neg_val, neg_drug = negative_data[i]

                pos_color = color_positive if class_map.get(pos_drug, False) else color_negative
                neg_color = color_positive if class_map.get(neg_drug, False) else color_negative

                ax.hlines(y, 0, pos_val, colors=pos_color, linewidth=LINE_WIDTH)
                ax.hlines(y, -neg_val, 0, colors=neg_color, linewidth=LINE_WIDTH)

            # Draw unpaired lines
            for i, (pos_val, pos_drug) in enumerate(unpaired_positive):
                y = base_y + (n_pairs + i) * LINE_SPACING
                pos_color = color_positive if class_map.get(pos_drug, False) else color_negative
                ax.hlines(y, 0, pos_val, colors=pos_color, linewidth=LINE_WIDTH)

            for i, (neg_val, neg_drug) in enumerate(unpaired_negative):
                y = base_y + (n_pairs + i) * LINE_SPACING
                neg_color = color_positive if class_map.get(neg_drug, False) else color_negative
                ax.hlines(y, -neg_val, 0, colors=neg_color, linewidth=LINE_WIDTH)

        # Formatting - larger fonts for big figure
        ax.axvline(x=0, color='black', linewidth=0.8)
        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels, fontsize=14)
        ax.set_xlabel('SHAP value', fontsize=16)
        ax.set_title(f'Aligned positive-negative SHAP pairs: {title}', fontsize=22, fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.3)
        ax.set_axisbelow(True)
        ax.set_ylim(-0.25, len(top_5_features) * FEATURE_SPACING + 0.25)

        # X-axis ticks every 0.1
        ax.xaxis.set_major_locator(MultipleLocator(0.1))
        ax.tick_params(axis='x', labelsize=12)

        # Legend with counts
        legend_elements = [
            Line2D([0], [0], color=color_positive, linewidth=2.5,
                   label=f'{pos_label} ({n_positive})'),
            Line2D([0], [0], color=color_negative, linewidth=2.5,
                   label=f'{neg_label} ({25 - n_positive})')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=12, framealpha=0.9)

        plt.tight_layout()

        # Determine output folder based on fig_id
        fig_num = fig_id.split('_')[1][0]  # "6", "7", or "8"
        output_folder = PPTX_FIG_DIR / f'Fig_{fig_num}'
        output_folder.mkdir(parents=True, exist_ok=True)

        # Save with high DPI for quality when scaled down
        output_path = output_folder / f'{fig_id}.png'
        plt.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white')
        plt.close()

        print(f"  Saved: {output_path}")

        # Also save to SHAP_Data folder
        shap_output = SHAP_DIR / f'shap_aligned_{shap_prefix}.png'
        fig2, ax2 = plt.subplots(figsize=FIGSIZE)

        # Recreate the plot for SHAP_Data folder
        y_positions2 = []
        y_labels2 = []

        for feat_idx, feature in enumerate(reversed(top_5_features)):
            base_y = feat_idx * FEATURE_SPACING
            y_positions2.append(base_y)

            display_name = feature.replace('_Contractility', ' (C)').replace('_O2', ' (O₂)')
            display_name = display_name.replace('R0', 'R₀').replace('Emax', 'Eₘₐₓ')
            display_name = display_name.replace('kappa', 'κ').replace('k_elim', 'kₑₗᵢₘ').replace('tau', 'τ')
            y_labels2.append(display_name)

            values = shap_df[feature].values
            drugs = shap_df['Drug'].values

            positive_data = [(v, d) for v, d in zip(values, drugs) if v > ZERO_THRESHOLD]
            negative_data = [(abs(v), d) for v, d in zip(values, drugs) if v < -ZERO_THRESHOLD]

            positive_data = sorted(positive_data, key=lambda x: x[0], reverse=True)
            negative_data = sorted(negative_data, key=lambda x: x[0], reverse=True)

            n_pairs = min(len(positive_data), len(negative_data))
            unpaired_positive = positive_data[n_pairs:]
            unpaired_negative = negative_data[n_pairs:]

            for i in range(n_pairs):
                y = base_y + i * LINE_SPACING
                pos_val, pos_drug = positive_data[i]
                neg_val, neg_drug = negative_data[i]

                pos_color = color_positive if class_map.get(pos_drug, False) else color_negative
                neg_color = color_positive if class_map.get(neg_drug, False) else color_negative

                ax2.hlines(y, 0, pos_val, colors=pos_color, linewidth=LINE_WIDTH)
                ax2.hlines(y, -neg_val, 0, colors=neg_color, linewidth=LINE_WIDTH)

            for i, (pos_val, pos_drug) in enumerate(unpaired_positive):
                y = base_y + (n_pairs + i) * LINE_SPACING
                pos_color = color_positive if class_map.get(pos_drug, False) else color_negative
                ax2.hlines(y, 0, pos_val, colors=pos_color, linewidth=LINE_WIDTH)

            for i, (neg_val, neg_drug) in enumerate(unpaired_negative):
                y = base_y + (n_pairs + i) * LINE_SPACING
                neg_color = color_positive if class_map.get(neg_drug, False) else color_negative
                ax2.hlines(y, -neg_val, 0, colors=neg_color, linewidth=LINE_WIDTH)

        ax2.axvline(x=0, color='black', linewidth=0.8)
        ax2.set_yticks(y_positions2)
        ax2.set_yticklabels(y_labels2, fontsize=14)
        ax2.set_xlabel('SHAP value', fontsize=16)
        ax2.set_title(f'Aligned positive-negative SHAP pairs: {title}', fontsize=22, fontweight='bold')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.grid(axis='x', alpha=0.3)
        ax2.set_axisbelow(True)
        ax2.set_ylim(-0.25, len(top_5_features) * FEATURE_SPACING + 0.25)
        ax2.xaxis.set_major_locator(MultipleLocator(0.1))
        ax2.tick_params(axis='x', labelsize=12)
        ax2.legend(handles=legend_elements, loc='upper right', fontsize=12, framealpha=0.9)

        plt.tight_layout()
        plt.savefig(shap_output, dpi=600, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"  Also saved: {shap_output}")

if __name__ == '__main__':
    generate_shap_aligned_pairs()
    print("\nDone! SHAP figures regenerated with visible white gaps.")
