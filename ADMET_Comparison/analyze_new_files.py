"""Analyze the manually-gathered ADMET and SwissADME files"""
import pandas as pd
from pathlib import Path

# Paths
base = Path(r"C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO")
swiss_new = base / "ADMET_Comparison" / "23 drugs swissadme.csv"
admet_new = base / "ADMET_Comparison" / "25 drugs ADMET.xlsx"
drug_smiles = base / "Cleaned_Data" / "drug_smiles.csv"

print("="*80)
print("ANALYZING MANUALLY-GATHERED FEATURES")
print("="*80)

# Load drug_smiles to get the ground truth drug list and SMILES
df_drugs = pd.read_csv(drug_smiles)
print(f"\n1. Source of truth (drug_smiles.csv): {len(df_drugs)} drugs")
print(f"   Columns: {df_drugs.columns.tolist()}")

# Sort drugs alphabetically (this is the order they were submitted to the websites)
df_drugs_sorted = df_drugs.sort_values('Drug').reset_index(drop=True)
print("\n   Drugs in alphabetical order:")
for i, drug in enumerate(df_drugs_sorted['Drug'], 1):
    print(f"   {i:2d}. {drug}")

# Load SwissADME (23 drugs - missing Plicamycin and Dactinomycin)
df_swiss = pd.read_csv(swiss_new)
print(f"\n2. SwissADME file (23 drugs swissadme.csv): {len(df_swiss)} drugs")
print(f"   Columns: {len(df_swiss.columns)} features")
print(f"   First 10 columns: {df_swiss.columns.tolist()[:10]}")

# Match SwissADME SMILES to drug names
print("\n   Matching SwissADME SMILES to drug names:")
swiss_smiles = df_swiss['Canonical SMILES'].str.strip().str.upper()
drug_smiles_map = dict(zip(
    df_drugs['SMILES'].str.strip().str.upper(),
    df_drugs['Drug']
))

matched_drugs = []
for i, smi in enumerate(swiss_smiles):
    if smi in drug_smiles_map:
        matched_drugs.append(drug_smiles_map[smi])
        print(f"   Molecule {i+1} -> {drug_smiles_map[smi]}")
    else:
        matched_drugs.append(f"UNMATCHED_{i+1}")
        print(f"   Molecule {i+1} -> NOT FOUND")

# Load ADMET (25 drugs - all should be present)
df_admet = pd.read_excel(admet_new)
print(f"\n3. ADMET-AI file (25 drugs ADMET.xlsx): {len(df_admet)} drugs")
print(f"   Columns: {len(df_admet.columns)} features")
print(f"   First 10 columns: {df_admet.columns.tolist()[:10]}")

# Check which drugs should be missing from SwissADME
all_drugs_sorted = df_drugs_sorted['Drug'].tolist()
expected_missing = ['Dactinomycin', 'Plicamycin']
expected_in_swiss = [d for d in all_drugs_sorted if d not in expected_missing]

print(f"\n4. Expected drugs in SwissADME (23 drugs, excluding {expected_missing}):")
for i, drug in enumerate(expected_in_swiss, 1):
    print(f"   {i:2d}. {drug}")

print(f"\n5. Verification:")
print(f"   - Total drugs: {len(all_drugs_sorted)}")
print(f"   - Expected in SwissADME: {len(expected_in_swiss)}")
print(f"   - Actual in SwissADME file: {len(df_swiss)}")
print(f"   - Expected in ADMET: {len(all_drugs_sorted)}")
print(f"   - Actual in ADMET file: {len(df_admet)}")

# Create mapping for SwissADME
# Assuming alphabetical order, skipping Dactinomycin (5th) and Plicamycin (18th)
print("\n6. Creating SwissADME mapping (alphabetical, skipping Dactinomycin and Plicamycin):")
swiss_drug_names = []
drug_idx = 0
for i, drug in enumerate(all_drugs_sorted):
    if drug in expected_missing:
        print(f"   Skipping: {drug} (not in SwissADME)")
        continue
    else:
        swiss_drug_names.append(drug)
        drug_idx += 1
        print(f"   Molecule {drug_idx:2d} -> {drug}")

print(f"\n   Total mapped: {len(swiss_drug_names)}")
print(f"   Match with file: {len(swiss_drug_names) == len(df_swiss)}")
