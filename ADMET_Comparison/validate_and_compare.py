"""Compare old vs new features to show what changed"""
import pandas as pd
import numpy as np
from pathlib import Path

base = Path(r"C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO")
output_dir = base / "Output" / "ADMET_Comparison"

# Load old files
old_admet = pd.read_csv(output_dir / "cardiac_rodeo_full_ADMET.csv")
old_swiss = pd.read_csv(output_dir / "cardiac_rodeo_full_swissadme.csv")

# Load new raw files
new_admet_raw = pd.read_excel(base / "ADMET_Comparison" / "25 drugs ADMET.xlsx")
new_swiss_raw = pd.read_csv(base / "ADMET_Comparison" / "23 drugs swissadme.csv")

# Load drug classification
df_drugs = pd.read_csv(base / "Cleaned_Data" / "drug_smiles.csv").sort_values('Drug').reset_index(drop=True)
all_drugs = df_drugs['Drug'].tolist()

print("="*80)
print("FEATURE COMPARISON: OLD vs NEW")
print("="*80)

print("\n1. OLD FILES STRUCTURE")
print("-"*80)
print(f"OLD ADMET: {old_admet.shape}")
print(f"  Columns: {old_admet.columns.tolist()[:10]}...")
if 'Drug' in old_admet.columns:
    print(f"  Drugs: {old_admet['Drug'].tolist()[:5]}...")
else:
    print(f"  No 'Drug' column - first col: {old_admet.columns[0]}")

print(f"\nOLD SwissADME: {old_swiss.shape}")
print(f"  Columns: {old_swiss.columns.tolist()[:10]}...")
if 'Drug' in old_swiss.columns:
    print(f"  Drugs: {old_swiss['Drug'].tolist()[:5]}...")
else:
    print(f"  No 'Drug' column - first col: {old_swiss.columns[0]}")

print("\n2. NEW FILES STRUCTURE")
print("-"*80)
print(f"NEW ADMET: {new_admet_raw.shape}")
print(f"  Columns: {new_admet_raw.columns.tolist()[:10]}...")
print(f"  First row values: {new_admet_raw.iloc[0, :5].tolist()}...")

print(f"\nNEW SwissADME: {new_swiss_raw.shape}")
print(f"  Columns: {new_swiss_raw.columns.tolist()[:10]}...")
print(f"  Drug mapping (Molecule 1-5):")
expected_missing = ['Dactinomycin', 'Plicamycin']
swiss_drugs = [d for d in all_drugs if d not in expected_missing]
for i in range(min(5, len(swiss_drugs))):
    print(f"    Molecule {i+1} -> {swiss_drugs[i]}")

print("\n3. SAMPLE COMPARISON (First 3 drugs)")
print("-"*80)

# Try to align data for comparison
if 'Drug' in old_admet.columns:
    sample_drugs = old_admet['Drug'].head(3).tolist()
else:
    sample_drugs = all_drugs[:3]

print(f"\nComparing: {', '.join(sample_drugs)}")

# Get common ADMET features (excluding Drug and targets)
target_cols = ['Arrhythmia', 'Cardiotoxicity', 'heart_damage', 'Concern']
old_admet_features = [c for c in old_admet.columns if c not in ['Drug'] + target_cols]
new_admet_features = new_admet_raw.columns.tolist()

print(f"\nADMET Features:")
print(f"  Old: {len(old_admet_features)} features")
print(f"  New: {len(new_admet_features)} features")

# Compare first 3 drugs for first 5 ADMET features
if 'Drug' in old_admet.columns:
    print(f"\n  Sample values for {sample_drugs[0]} (first 5 ADMET features):")
    for feat in old_admet_features[:5]:
        old_val = old_admet[old_admet['Drug'] == sample_drugs[0]][feat].values[0]
        # New file: row 0 = drug 0 (Amiodarone if sorted)
        new_val = new_admet_raw.iloc[0][feat] if feat in new_admet_features else np.nan
        diff = "CHANGED" if abs(old_val - new_val) > 1e-6 else "SAME"
        if not pd.isna(new_val):
            print(f"    {feat}: OLD={old_val:.4f} NEW={new_val:.4f} [{diff}]")
        else:
            print(f"    {feat}: OLD={old_val:.4f} NEW=N/A [MISSING]")

print("\n4. FEATURE NAME MATCHING")
print("-"*80)
common_features = set(old_admet_features) & set(new_admet_features)
only_old = set(old_admet_features) - set(new_admet_features)
only_new = set(new_admet_features) - set(old_admet_features)

print(f"  Common features: {len(common_features)}")
print(f"  Only in OLD: {len(only_old)}")
if only_old:
    print(f"    {list(only_old)[:5]}...")
print(f"  Only in NEW: {len(only_new)}")
if only_new:
    print(f"    {list(only_new)[:5]}...")

print("\n5. CHANGE STATISTICS")
print("-"*80)

if 'Drug' in old_admet.columns and len(common_features) > 0:
    # Calculate correlation for matching drugs and features
    changes = []
    for i, drug in enumerate(all_drugs[:5]):  # First 5 drugs
        if drug in old_admet['Drug'].values:
            for feat in list(common_features)[:10]:  # First 10 common features
                old_val = old_admet[old_admet['Drug'] == drug][feat].values[0]
                new_val = new_admet_raw.iloc[i][feat]
                if not pd.isna(old_val) and not pd.isna(new_val):
                    pct_change = abs((new_val - old_val) / (old_val + 1e-10)) * 100
                    changes.append({
                        'drug': drug,
                        'feature': feat,
                        'old': old_val,
                        'new': new_val,
                        'pct_change': pct_change
                    })

    if changes:
        df_changes = pd.DataFrame(changes)
        print(f"  Analyzed {len(changes)} feature-drug pairs")
        print(f"  Mean absolute % change: {df_changes['pct_change'].mean():.2f}%")
        print(f"  Median absolute % change: {df_changes['pct_change'].median():.2f}%")
        print(f"\n  Top 5 largest changes:")
        top_changes = df_changes.nlargest(5, 'pct_change')
        for _, row in top_changes.iterrows():
            print(f"    {row['drug']}, {row['feature']}: {row['old']:.4f} -> {row['new']:.4f} ({row['pct_change']:.1f}%)")

print("\n" + "="*80)
print("COMPARISON COMPLETE")
print("="*80)
print("\nRECOMMENDATION:")
print("  The new files should REPLACE the old files because:")
print("  1. Original SMILES were incorrect")
print("  2. New features are directly from ADMET-AI and SwissADME websites")
print("  3. This is the source of truth for correct molecular descriptors")
