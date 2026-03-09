"""
Validate ADMEThyst DICT predictions against actual cardiotoxicity labels from Cardiac RODEO.
Creates ROC curve and threshold scatter plots.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc, confusion_matrix, classification_report
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).resolve().parent.parent.parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Set up paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]

OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load actual labels from the coefficients file
print("Loading actual cardiotoxicity labels...")
excel_path = PROJECT_ROOT / "EQN_Coefficients" / "all_equations_coefficients.xlsx"
df_labels = pd.read_excel(excel_path, sheet_name='pkpd_elimination', header=1)
df_labels.columns = df_labels.columns.str.strip()

# Get unique drugs with their labels
drugs_labels = df_labels[['Drug', 'Arrhythmia', 'heart_damage', 'Concern']].drop_duplicates()
drugs_labels = drugs_labels.dropna(subset=['Arrhythmia', 'heart_damage', 'Concern'])
print(f"Found {len(drugs_labels)} drugs with labels")

# Load ADMEThyst predictions
print("\nLoading ADMEThyst predictions...")
preds_df = pd.read_csv(OUTPUT_DIR / "cardiac_rodeo_DICT_predictions.csv")
print(f"Loaded predictions for {len(preds_df)} drugs")

# Merge predictions with actual labels
merged = preds_df.merge(drugs_labels, on='Drug', how='inner')
print(f"\nMatched {len(merged)} drugs between predictions and labels")

# Print the merged data
print("\n" + "="*80)
print("DRUG LABELS vs DICT PREDICTIONS")
print("="*80)
print(f"{'Drug':<18} {'Arrhythmia':<12} {'Heart Dam.':<12} {'Concern':<10} {'DICT Prob':>10} {'Pred':>8}")
print("-"*80)
for _, row in merged.iterrows():
    print(f"{row['Drug']:<18} {str(row['Arrhythmia']):<12} {str(row['heart_damage']):<12} "
          f"{str(row['Concern']):<10} {row['DICT_Concern_Prob']:>10.3f} {row['DICT_Class']:>8}")

# Convert labels to binary for evaluation
# Cardiotoxicity = True if Arrhythmia OR heart_damage is true
def to_binary(val):
    if pd.isna(val):
        return np.nan
    val_str = str(val).lower().strip()
    return 1 if val_str == 'true' else 0

merged['AR_binary'] = merged['Arrhythmia'].apply(to_binary)
merged['HD_binary'] = merged['heart_damage'].apply(to_binary)

# Create combined cardiotoxicity label (any cardiotoxicity)
merged['Any_Cardiotox'] = ((merged['AR_binary'] == 1) | (merged['HD_binary'] == 1)).astype(int)

# Convert Concern to binary (most/less = 1, no = 0)
def concern_to_binary(val):
    val_str = str(val).lower().strip()
    return 1 if val_str in ['most', 'less'] else 0

merged['Concern_binary'] = merged['Concern'].apply(concern_to_binary)

print("\n" + "="*80)
print("BINARY LABEL SUMMARY")
print("="*80)
print(f"Arrhythmia:        {merged['AR_binary'].sum():.0f} positive, {(merged['AR_binary']==0).sum():.0f} negative")
print(f"Heart Damage:      {merged['HD_binary'].sum():.0f} positive, {(merged['HD_binary']==0).sum():.0f} negative")
print(f"Any Cardiotoxicity:{merged['Any_Cardiotox'].sum():.0f} positive, {(merged['Any_Cardiotox']==0).sum():.0f} negative")
print(f"Concern (most/less):{merged['Concern_binary'].sum():.0f} positive, {(merged['Concern_binary']==0).sum():.0f} negative")

# ============================================================================
# FIGURE 1: ROC Curves
# ============================================================================
print("\n" + "="*80)
print("GENERATING ROC CURVES")
print("="*80)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

y_pred_prob = merged['DICT_Concern_Prob'].values

targets = [
    ('Arrhythmia', merged['AR_binary'].values, '#a3c9f9'),
    ('Heart Damage', merged['HD_binary'].values, '#c8b7ff'),
    ('Any Cardiotoxicity', merged['Any_Cardiotox'].values, '#f8b4b4'),
]

for ax, (name, y_true, color) in zip(axes, targets):
    # Compute ROC curve
    fpr, tpr, thresholds = roc_curve(y_true, y_pred_prob)
    roc_auc = auc(fpr, tpr)

    # Plot
    ax.plot(fpr, tpr, color=color, lw=3, label=f'ROC curve (AUC = {roc_auc:.3f})')
    ax.plot([0, 1], [0, 1], 'k--', lw=1.5, label='Random (AUC = 0.500)')
    ax.fill_between(fpr, tpr, alpha=0.3, color=color)

    # Find optimal threshold
    optimal_idx = np.argmax(tpr - fpr)
    optimal_threshold = thresholds[optimal_idx]
    ax.scatter([fpr[optimal_idx]], [tpr[optimal_idx]], marker='o', s=100,
               color='red', zorder=5, label=f'Optimal (thr={optimal_threshold:.2f})')

    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title(f'ROC: DICT vs {name}', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=10)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.grid(True, alpha=0.3)

    print(f"\n{name}:")
    print(f"  ROC AUC: {roc_auc:.3f}")
    print(f"  Optimal threshold: {optimal_threshold:.3f}")

plt.tight_layout()
fig.savefig(OUTPUT_DIR / "DICT_ROC_curves.png", dpi=300, bbox_inches='tight')
fig.savefig(OUTPUT_DIR / "DICT_ROC_curves.pdf", bbox_inches='tight')
print(f"\nROC curves saved to: {OUTPUT_DIR / 'DICT_ROC_curves.png'}")
plt.close()

# ============================================================================
# FIGURE 2: Threshold Scatter Plot (styled like notebook)
# ============================================================================
print("\n" + "="*80)
print("GENERATING THRESHOLD SCATTER PLOTS")
print("="*80)

# Colors matching notebook style
arr_color = '#a3c9f9'      # Arrhythmia
hd_color = '#c8b7ff'       # Heart Damage
neg_color = 'lightgray'
threshold_color = 'red'

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# Sort drugs by DICT prediction
merged_sorted = merged.sort_values('DICT_Concern_Prob', ascending=False).reset_index(drop=True)
drugs = merged_sorted['Drug'].tolist()
positions = np.arange(len(drugs))
preds_pct = merged_sorted['DICT_Concern_Prob'].values * 100  # Convert to percentage

# Plot 1: DICT vs Arrhythmia
ax = axes[0]
status = merged_sorted['AR_binary'] == 1
point_colors = [arr_color if s else neg_color for s in status]
ax.scatter(positions, preds_pct, c=point_colors, alpha=0.8, s=80, edgecolors='black', linewidth=0.5)

# Add threshold line at 50%
threshold = 50
ax.axhline(threshold, color=threshold_color, linestyle='--', linewidth=2)
ax.text(len(drugs) - 0.5, threshold + 2, f'{threshold}%', color=threshold_color,
        fontsize=10, fontweight='bold', ha='right')

# Labels
ax.set_xticks(positions)
ax.set_xticklabels(drugs, rotation=45, ha='right', fontsize=9)
ax.set_ylabel('DICT Concern Probability (%)', fontsize=12)
ax.set_title('DICT Prediction vs Arrhythmia (Actual)', fontsize=13, fontweight='bold')
ax.set_ylim(0, 105)
ax.grid(True, axis='y', alpha=0.3)

# Legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=arr_color, markersize=10, label='Arrhythmia = True'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=neg_color, markersize=10, label='Arrhythmia = False'),
    Line2D([0], [0], color=threshold_color, linestyle='--', linewidth=2, label='Threshold (50%)')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

# Plot 2: DICT vs Heart Damage
ax = axes[1]
status = merged_sorted['HD_binary'] == 1
point_colors = [hd_color if s else neg_color for s in status]
ax.scatter(positions, preds_pct, c=point_colors, alpha=0.8, s=80, edgecolors='black', linewidth=0.5)

ax.axhline(threshold, color=threshold_color, linestyle='--', linewidth=2)
ax.text(len(drugs) - 0.5, threshold + 2, f'{threshold}%', color=threshold_color,
        fontsize=10, fontweight='bold', ha='right')

ax.set_xticks(positions)
ax.set_xticklabels(drugs, rotation=45, ha='right', fontsize=9)
ax.set_ylabel('DICT Concern Probability (%)', fontsize=12)
ax.set_title('DICT Prediction vs Heart Damage (Actual)', fontsize=13, fontweight='bold')
ax.set_ylim(0, 105)
ax.grid(True, axis='y', alpha=0.3)

legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=hd_color, markersize=10, label='Heart Damage = True'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=neg_color, markersize=10, label='Heart Damage = False'),
    Line2D([0], [0], color=threshold_color, linestyle='--', linewidth=2, label='Threshold (50%)')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

# Plot 3: DICT vs Any Cardiotoxicity
ax = axes[2]
cardiotox_color = '#f8b4b4'
status = merged_sorted['Any_Cardiotox'] == 1
point_colors = [cardiotox_color if s else neg_color for s in status]
ax.scatter(positions, preds_pct, c=point_colors, alpha=0.8, s=80, edgecolors='black', linewidth=0.5)

ax.axhline(threshold, color=threshold_color, linestyle='--', linewidth=2)
ax.text(len(drugs) - 0.5, threshold + 2, f'{threshold}%', color=threshold_color,
        fontsize=10, fontweight='bold', ha='right')

ax.set_xticks(positions)
ax.set_xticklabels(drugs, rotation=45, ha='right', fontsize=9)
ax.set_ylabel('DICT Concern Probability (%)', fontsize=12)
ax.set_title('DICT Prediction vs Any Cardiotoxicity (Actual)', fontsize=13, fontweight='bold')
ax.set_ylim(0, 105)
ax.grid(True, axis='y', alpha=0.3)

legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=cardiotox_color, markersize=10, label='Cardiotoxic = True'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=neg_color, markersize=10, label='Cardiotoxic = False'),
    Line2D([0], [0], color=threshold_color, linestyle='--', linewidth=2, label='Threshold (50%)')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

plt.tight_layout()
fig.savefig(OUTPUT_DIR / "DICT_threshold_scatter.png", dpi=300, bbox_inches='tight')
fig.savefig(OUTPUT_DIR / "DICT_threshold_scatter.pdf", bbox_inches='tight')
print(f"Threshold scatter plots saved to: {OUTPUT_DIR / 'DICT_threshold_scatter.png'}")
plt.close()

# ============================================================================
# FIGURE 3: Confusion Matrices
# ============================================================================
print("\n" + "="*80)
print("GENERATING CONFUSION MATRICES")
print("="*80)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

y_pred_binary = (merged['DICT_Concern_Prob'] >= 0.5).astype(int)

for ax, (name, y_true, color) in zip(axes, targets):
    cm = confusion_matrix(y_true, y_pred_binary)

    # Plot confusion matrix
    im = ax.imshow(cm, cmap='Blues')

    # Add text annotations
    for i in range(2):
        for j in range(2):
            text = ax.text(j, i, cm[i, j], ha="center", va="center",
                          fontsize=20, fontweight='bold',
                          color="white" if cm[i, j] > cm.max()/2 else "black")

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(['Pred: Low Risk', 'Pred: High Risk'], fontsize=11)
    ax.set_yticklabels(['Actual: Negative', 'Actual: Positive'], fontsize=11)
    ax.set_xlabel('Predicted', fontsize=12)
    ax.set_ylabel('Actual', fontsize=12)
    ax.set_title(f'Confusion Matrix: {name}', fontsize=13, fontweight='bold')

    # Calculate metrics
    tn, fp, fn, tp = cm.ravel()
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    print(f"\n{name}:")
    print(f"  Accuracy: {accuracy:.3f}")
    print(f"  Sensitivity (Recall): {sensitivity:.3f}")
    print(f"  Specificity: {specificity:.3f}")
    print(f"  TP={tp}, TN={tn}, FP={fp}, FN={fn}")

plt.tight_layout()
fig.savefig(OUTPUT_DIR / "DICT_confusion_matrices.png", dpi=300, bbox_inches='tight')
print(f"\nConfusion matrices saved to: {OUTPUT_DIR / 'DICT_confusion_matrices.png'}")
plt.close()

# ============================================================================
# Save summary to CSV
# ============================================================================
summary_df = merged[['Drug', 'DICT_Concern_Prob', 'DICT_Class', 'Arrhythmia', 'heart_damage',
                     'Concern', 'AR_binary', 'HD_binary', 'Any_Cardiotox']].copy()
summary_df = summary_df.sort_values('DICT_Concern_Prob', ascending=False)
summary_df.to_csv(OUTPUT_DIR / "DICT_validation_summary.csv", index=False)
print(f"\nValidation summary saved to: {OUTPUT_DIR / 'DICT_validation_summary.csv'}")

print("\n" + "="*80)
print("VALIDATION COMPLETE!")
print("="*80)
