"""Compare XGBoost vs CNN approaches for MoLFormer-based prediction."""
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "Output" / "MoLFormer_Comparison"

# Load both prediction files
xgb_df = pd.read_csv(OUTPUT_DIR / "molformer_predictions_25.csv")
cnn_df = pd.read_csv(OUTPUT_DIR / "molformer_cnn_predictions_25.csv")

# Merge
merged = xgb_df[['Drug', 'Arrhythmia_label', 'DIQT_prob', 'DIQT_pred']].merge(
    cnn_df[['Drug', 'CNN_prob', 'CNN_pred']], on='Drug'
)

# Compare predictions
print("="*70)
print("MoLFormer: XGBoost vs CNN Comparison")
print("="*70)
print(f"\n{'Drug':<20} {'True':>6} {'XGB_prob':>10} {'CNN_prob':>10} {'XGB':>5} {'CNN':>5}")
print("-"*70)

for _, row in merged.iterrows():
    true_label = "+" if row['Arrhythmia_label'] == 1 else "-"
    xgb_match = "✓" if row['DIQT_pred'] == row['Arrhythmia_label'] else "✗"
    cnn_match = "✓" if row['CNN_pred'] == row['Arrhythmia_label'] else "✗"
    print(f"{row['Drug']:<20} {true_label:>6} {row['DIQT_prob']:>10.4f} {row['CNN_prob']:>10.4f} {xgb_match:>5} {cnn_match:>5}")

# Summary statistics
xgb_correct = (merged['DIQT_pred'] == merged['Arrhythmia_label']).sum()
cnn_correct = (merged['CNN_pred'] == merged['Arrhythmia_label']).sum()
both_correct = ((merged['DIQT_pred'] == merged['Arrhythmia_label']) &
                (merged['CNN_pred'] == merged['Arrhythmia_label'])).sum()
xgb_only = ((merged['DIQT_pred'] == merged['Arrhythmia_label']) &
            (merged['CNN_pred'] != merged['Arrhythmia_label'])).sum()
cnn_only = ((merged['DIQT_pred'] != merged['Arrhythmia_label']) &
            (merged['CNN_pred'] == merged['Arrhythmia_label'])).sum()
both_wrong = ((merged['DIQT_pred'] != merged['Arrhythmia_label']) &
              (merged['CNN_pred'] != merged['Arrhythmia_label'])).sum()

print("\n" + "="*70)
print("Summary")
print("="*70)
print(f"XGBoost correct: {xgb_correct}/25 ({xgb_correct/25*100:.1f}%)")
print(f"CNN correct:     {cnn_correct}/25 ({cnn_correct/25*100:.1f}%)")
print(f"\nBoth correct:    {both_correct}")
print(f"Only XGBoost:    {xgb_only}")
print(f"Only CNN:        {cnn_only}")
print(f"Both wrong:      {both_wrong}")

# Calculate correlation
corr = merged['DIQT_prob'].corr(merged['CNN_prob'])
print(f"\nProbability correlation: {corr:.4f}")

# Save comparison
merged.to_csv(OUTPUT_DIR / "xgb_vs_cnn_comparison.csv", index=False)
print(f"\nSaved to {OUTPUT_DIR / 'xgb_vs_cnn_comparison.csv'}")
