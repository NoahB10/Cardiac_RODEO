"""Create a detailed plan for integrating the manually-gathered features"""
import pandas as pd
from pathlib import Path
import json

# Paths
base = Path(r"C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO")
swiss_new = base / "ADMET_Comparison" / "23 drugs swissadme.csv"
admet_new = base / "ADMET_Comparison" / "25 drugs ADMET.xlsx"
drug_smiles = base / "Cleaned_Data" / "drug_smiles.csv"
drug_class = base / "Cleaned_Data" / "drug_classification.csv"
output_dir = base / "Output" / "ADMET_Comparison"

print("="*80)
print("INTEGRATION PLAN")
print("="*80)

# Load current files
df_drugs = pd.read_csv(drug_smiles).sort_values('Drug').reset_index(drop=True)
df_class = pd.read_csv(drug_class)

# Load new features
df_swiss_raw = pd.read_csv(swiss_new)
df_admet_raw = pd.read_excel(admet_new)

print("\n1. CURRENT STATE")
print("-"*80)
print(f"   Drug list: {len(df_drugs)} drugs")
print(f"   Classifications available: {len(df_class)} drugs")

# Check if old feature files exist
old_admet = output_dir / "cardiac_rodeo_full_ADMET.csv"
old_swiss = output_dir / "cardiac_rodeo_full_swissadme.csv"

if old_admet.exists():
    df_admet_old = pd.read_csv(old_admet)
    print(f"   Old ADMET features: {df_admet_old.shape} (exists)")
else:
    df_admet_old = None
    print(f"   Old ADMET features: NOT FOUND")

if old_swiss.exists():
    df_swiss_old = pd.read_csv(old_swiss)
    print(f"   Old SwissADME features: {df_swiss_old.shape} (exists)")
else:
    df_swiss_old = None
    print(f"   Old SwissADME features: NOT FOUND")

print("\n2. NEW FILES")
print("-"*80)
print(f"   New ADMET: {df_admet_raw.shape} - {admet_new.name}")
print(f"   New SwissADME: {df_swiss_raw.shape} - {swiss_new.name}")

# Create proper drug name mappings
all_drugs_sorted = df_drugs['Drug'].tolist()
expected_missing = ['Dactinomycin', 'Plicamycin']
expected_in_swiss = [d for d in all_drugs_sorted if d not in expected_missing]

# SwissADME mapping
swiss_drug_names = []
for drug in all_drugs_sorted:
    if drug not in expected_missing:
        swiss_drug_names.append(drug)

print("\n3. INTEGRATION STEPS")
print("-"*80)

print("\n   Step 1: Create cardiac_rodeo_full_ADMET.csv (25 drugs × 41 features)")
print("   -----------------------------------------------------------------------")
print("   - Load '25 drugs ADMET.xlsx'")
print("   - Add 'Drug' column with alphabetically sorted drug names")
print("   - Merge with drug_classification.csv to add target labels")
print("   - Columns: Drug, [41 ADMET features], Arrhythmia, Cardiotoxicity, heart_damage, Concern")
print(f"   - Output: {output_dir / 'cardiac_rodeo_full_ADMET.csv'}")

print("\n   Step 2: Create cardiac_rodeo_full_swissadme.csv (23 drugs × features)")
print("   -----------------------------------------------------------------------")
print("   - Load '23 drugs swissadme.csv'")
print("   - Add 'Drug' column with correctly mapped drug names (skip Dactinomycin, Plicamycin)")
print("   - Extract relevant features (drop Molecule, Canonical SMILES, Formula, etc.)")
print("   - Add NaN rows for Dactinomycin and Plicamycin to maintain 25-drug alignment")
print("   - Merge with drug_classification.csv to add target labels")
print(f"   - Output: {output_dir / 'cardiac_rodeo_full_swissadme.csv'}")

print("\n   Step 3: Update drug_smiles.csv with correct SMILES")
print("   ---------------------------------------------------")
print("   - Extract SMILES from SwissADME for the 23 drugs")
print("   - For Dactinomycin and Plicamycin, keep original SMILES (or update manually)")
print(f"   - Output: BACKUP original to drug_smiles_backup.csv")
print(f"   - Output: {drug_smiles}")

print("\n   Step 4: Validation")
print("   -------------------")
if df_admet_old is not None and df_swiss_old is not None:
    print("   - Compare old vs new ADMET features (sample drugs)")
    print("   - Compare old vs new SwissADME features (sample drugs)")
    print("   - Identify which features changed")
    print("   - Report statistics")
else:
    print("   - No old files to compare")

print("\n4. EXPECTED OUTPUTS")
print("-"*80)
print(f"   {output_dir / 'cardiac_rodeo_full_ADMET.csv'}")
print(f"     Shape: (25, ~46) - 1 Drug + 41 ADMET + 4 targets")
print(f"   {output_dir / 'cardiac_rodeo_full_swissadme.csv'}")
print(f"     Shape: (25, ~52) - 1 Drug + 47 SwissADME + 4 targets")
print(f"   {drug_smiles.parent / 'drug_smiles_backup.csv'}")
print(f"     Backup of original")
print(f"   {drug_smiles}")
print(f"     Updated with correct SMILES")

print("\n5. FILES TO UPDATE IN PIPELINE")
print("-"*80)
scripts = [
    "Scripts/full_analysis.py",
    "Scripts/retrain_dictrank_models.py",
    "Scripts/predict_swissadme.py",
    "Scripts/predict_retrained_dictrank.py"
]
for s in scripts:
    script_path = base / "ADMET_Comparison" / s
    if script_path.exists():
        print(f"   ✓ {s}")
    else:
        print(f"   ✗ {s} (not found)")

print("\n" + "="*80)
print("END OF INTEGRATION PLAN")
print("="*80)
