"""
Plot ADMET-AI DICT concern predictions for all 25 drugs
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load predictions
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]

OUTPUT_DIR = PROJECT_ROOT / "Output" / "ADMET_Comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
results = pd.read_csv(OUTPUT_DIR / 'cardiac_rodeo_DICT_predictions.csv')

# Sort by probability
results = results.sort_values('DICT_Concern_Prob', ascending=True).reset_index(drop=True)

# Create figure
fig, ax = plt.subplots(figsize=(12, 8))

# Color by risk level
colors = ['#99d594' if p < 0.5 else '#df65b0' for p in results['DICT_Concern_Prob']]

# Horizontal bar plot
y_pos = np.arange(len(results))
bars = ax.barh(y_pos, results['DICT_Concern_Prob'], color=colors,
               edgecolor='black', linewidth=1.5, alpha=0.8)

# Threshold line at 0.5
ax.axvline(0.5, color='red', linestyle='--', linewidth=2.5,
           label='Risk Threshold (0.5)', zorder=10)

# Styling
ax.set_yticks(y_pos)
ax.set_yticklabels(results['Drug'], fontsize=10)
ax.set_xlabel('DICT Concern Probability', fontsize=14, fontweight='bold')
ax.set_ylabel('Drug', fontsize=14, fontweight='bold')
ax.set_title('ADMET-AI DICT Concern Predictions\nCardiac RODEO Drugs (N=25)',
             fontsize=16, fontweight='bold', pad=20)
ax.set_xlim(0, 1.0)

# Grid
ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.8)
ax.set_axisbelow(True)

# Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#df65b0', edgecolor='black', label='High Risk (≥0.5)'),
    Patch(facecolor='#99d594', edgecolor='black', label='Low Risk (<0.5)'),
    plt.Line2D([0], [0], color='red', linewidth=2.5, linestyle='--', label='Threshold (0.5)')
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=11, framealpha=0.95)

# Add probability values on bars
for i, (idx, row) in enumerate(results.iterrows()):
    prob = row['DICT_Concern_Prob']
    ax.text(prob + 0.02, i, f'{prob:.3f}',
            va='center', fontsize=8, fontweight='bold')

# Summary statistics
high_risk = (results['DICT_Concern_Prob'] >= 0.5).sum()
low_risk = (results['DICT_Concern_Prob'] < 0.5).sum()

# Add text box with summary
textstr = f'High Risk: {high_risk}/25 ({100*high_risk/25:.0f}%)\nLow Risk: {low_risk}/25 ({100*low_risk/25:.0f}%)'
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=12,
        verticalalignment='top', bbox=props)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'ADMET_AI_Predictions_Plot.png', dpi=300, bbox_inches='tight')
plt.savefig(OUTPUT_DIR / 'ADMET_AI_Predictions_Plot.pdf', bbox_inches='tight')
print(f"Saved plots to {OUTPUT_DIR}")

# Print summary
print("\n" + "="*70)
print("ADMET-AI DICT CONCERN PREDICTIONS SUMMARY")
print("="*70)
print(f"\nHigh Risk (≥0.5): {high_risk}/25 drugs ({100*high_risk/25:.0f}%)")
print(f"Low Risk (<0.5):  {low_risk}/25 drugs ({100*low_risk/25:.0f}%)")

print("\n" + "-"*70)
print("TOP 5 HIGHEST RISK:")
print("-"*70)
for i, row in results.tail(5).iloc[::-1].iterrows():
    print(f"  {row['Drug']:<20} {row['DICT_Concern_Prob']:.3f}")

print("\n" + "-"*70)
print("TOP 5 LOWEST RISK:")
print("-"*70)
for i, row in results.head(5).iterrows():
    print(f"  {row['Drug']:<20} {row['DICT_Concern_Prob']:.3f}")

plt.show()
