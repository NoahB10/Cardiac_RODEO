"""
Integration Script: Replace old features with manually-gathered correct features
Updated: SwissADME is 23 drugs (NOT 25 with NaN)

This script will:
1. Backup old feature files
2. Create new cardiac_rodeo_full_ADMET.csv with correct ADMET features (25 drugs)
3. Create new cardiac_rodeo_full_swissadme.csv with correct SwissADME features (23 drugs)
4. Update drug_smiles.csv with correct SMILES from SwissADME
"""
import pandas as pd
import numpy as np
from pathlib import Path
import shutil
from datetime import datetime

# Paths
base = Path(r"C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO")
admet_comp_dir = base / "ADMET_Comparison"
output_dir = base / "Output" / "ADMET_Comparison"
cleaned_data_dir = base / "Cleaned_Data"
admethyst_dir = base / "ADMEThyst-main"

# Input files (manually gathered)
swiss_new_path = admet_comp_dir / "23 drugs swissadme.csv"
admet_new_path = admet_comp_dir / "25 drugs ADMET.xlsx"

# Output files (will be replaced)
admet_output = output_dir / "cardiac_rodeo_full_ADMET.csv"
swiss_output = output_dir / "cardiac_rodeo_full_swissadme.csv"
smiles_output = cleaned_data_dir / "drug_smiles.csv"

# Reference files
drug_smiles_path = cleaned_data_dir / "drug_smiles.csv"
drug_class_path = cleaned_data_dir / "drug_classification.csv"

# ADMEThyst training data (for feature alignment)
swiss_training_path = admethyst_dir / "data" / "SwissADME_Xvals.csv"

def backup_file(filepath):
    """Backup a file with timestamp"""
    if filepath.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.parent / f"{filepath.stem}_backup_{timestamp}{filepath.suffix}"
        shutil.copy2(filepath, backup_path)
        print(f"  Backed up: {filepath.name} -> {backup_path.name}")
        return backup_path
    else:
        print(f"  File not found (skip backup): {filepath.name}")
        return None

def main():
    print("="*80)
    print("FEATURE INTEGRATION SCRIPT (23 SwissADME, 25 ADMET)")
    print("="*80)

    # -------------------------------------------------------------------------
    # STEP 1: Backup old files
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Backing up old files...")
    print("-"*80)
    backup_file(admet_output)
    backup_file(swiss_output)
    backup_file(smiles_output)

    # -------------------------------------------------------------------------
    # STEP 2: Load reference data
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Loading reference data...")
    print("-"*80)

    # Load drug names and classifications
    df_drugs = pd.read_csv(drug_smiles_path)
    df_class = pd.read_csv(drug_class_path)

    # Sort drugs alphabetically (this is the submission order)
    all_drugs_sorted = sorted(df_drugs['Drug'].tolist())
    print(f"  Loaded {len(all_drugs_sorted)} drugs (alphabetically sorted)")

    # Load new raw features
    df_admet_raw = pd.read_excel(admet_new_path)
    df_swiss_raw = pd.read_csv(swiss_new_path)

    print(f"  Loaded ADMET: {df_admet_raw.shape}")
    print(f"  Loaded SwissADME: {df_swiss_raw.shape}")

    # Load ADMEThyst training features for alignment
    df_swiss_training = pd.read_csv(swiss_training_path)
    training_features = [c for c in df_swiss_training.columns if c != 'Unnamed: 0']
    print(f"  ADMEThyst SwissADME training features: {len(training_features)}")

    # -------------------------------------------------------------------------
    # STEP 3: Create new cardiac_rodeo_full_ADMET.csv (25 drugs)
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Creating new cardiac_rodeo_full_ADMET.csv (25 drugs)...")
    print("-"*80)

    # Add drug names as first column
    df_admet_new = df_admet_raw.copy()
    df_admet_new.insert(0, 'Drug', all_drugs_sorted)

    # Merge with classifications
    df_admet_new = df_admet_new.merge(
        df_class[['Drug', 'Arrhythmia', 'heart_damage', 'Concern']],
        on='Drug',
        how='left'
    )

    print(f"  Created ADMET table: {df_admet_new.shape}")
    print(f"    Columns: Drug + {len(df_admet_raw.columns)} ADMET features + 4 targets")
    print(f"    All 25 drugs: {df_admet_new['Drug'].tolist()}")

    # Save
    df_admet_new.to_csv(admet_output, index=False)
    print(f"  Saved: {admet_output}")

    # -------------------------------------------------------------------------
    # STEP 4: Create new cardiac_rodeo_full_swissadme.csv (23 drugs)
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Creating new cardiac_rodeo_full_swissadme.csv (23 drugs)...")
    print("-"*80)

    # Map Molecule 1-23 to drug names (skip Dactinomycin and Plicamycin)
    expected_missing = ['Dactinomycin', 'Plicamycin']
    swiss_drug_names = [d for d in all_drugs_sorted if d not in expected_missing]

    print(f"  SwissADME has 23 drugs (missing: {expected_missing})")
    print(f"  23 drugs: {swiss_drug_names}")

    # Add drug names to SwissADME data
    df_swiss_raw['Drug'] = swiss_drug_names

    # Drop columns that are NOT in training data
    # Keep only: Drug + 42 training features
    cols_to_drop = ['Molecule', 'Canonical SMILES', 'Formula',
                    'ESOL Class', 'Ali Class', 'Silicos-IT class']
    df_swiss_features = df_swiss_raw.drop(columns=cols_to_drop, errors='ignore')

    # Reorder columns to match training: Drug first, then training features
    available_features = [c for c in training_features if c in df_swiss_features.columns]
    missing_features = [c for c in training_features if c not in df_swiss_features.columns]

    if missing_features:
        print(f"  Warning: Missing features from training: {missing_features}")

    print(f"  Available features: {len(available_features)}/{len(training_features)}")

    df_swiss_new = df_swiss_features[['Drug'] + available_features].copy()

    # Convert categorical columns to numeric (Yes/No, High/Low -> 1/0)
    binary_cols = ['GI absorption', 'BBB permeant', 'Pgp substrate',
                   'CYP1A2 inhibitor', 'CYP2C19 inhibitor', 'CYP2C9 inhibitor',
                   'CYP2D6 inhibitor', 'CYP3A4 inhibitor']

    for col in binary_cols:
        if col in df_swiss_new.columns:
            df_swiss_new[col] = df_swiss_new[col].map(
                {'Yes': 1, 'No': 0, 'High': 1, 'Low': 0, 1: 1, 0: 0}
            ).fillna(0).astype(int)

    # Merge with classifications
    df_swiss_new = df_swiss_new.merge(
        df_class[['Drug', 'Arrhythmia', 'heart_damage', 'Concern']],
        on='Drug',
        how='left'
    )

    print(f"  Created SwissADME table: {df_swiss_new.shape}")
    print(f"    Columns: Drug + {len(available_features)} SwissADME features + 4 targets")

    # Save
    df_swiss_new.to_csv(swiss_output, index=False)
    print(f"  Saved: {swiss_output}")

    # -------------------------------------------------------------------------
    # STEP 5: Update drug_smiles.csv with correct SMILES
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Updating drug_smiles.csv with correct SMILES...")
    print("-"*80)

    # Extract correct SMILES from SwissADME
    df_swiss_smiles_raw = pd.read_csv(swiss_new_path)
    smiles_map = dict(zip(swiss_drug_names, df_swiss_smiles_raw['Canonical SMILES']))

    # Update SMILES for the 23 drugs
    df_drugs_updated = df_drugs.copy()
    smiles_updated_count = 0
    for drug in swiss_drug_names:
        if drug in smiles_map:
            old_smiles = df_drugs_updated.loc[df_drugs_updated['Drug'] == drug, 'SMILES'].values[0]
            new_smiles = smiles_map[drug]
            if old_smiles != new_smiles:
                df_drugs_updated.loc[df_drugs_updated['Drug'] == drug, 'SMILES'] = new_smiles
                smiles_updated_count += 1

    print(f"  Updated {smiles_updated_count} SMILES")
    print(f"  Dactinomycin and Plicamycin SMILES unchanged (not in SwissADME)")

    # Save updated SMILES
    df_drugs_updated.to_csv(smiles_output, index=False)
    print(f"  Saved: {smiles_output}")

    # -------------------------------------------------------------------------
    # STEP 6: Validation
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Validation checks...")
    print("-"*80)

    # Check ADMET
    assert df_admet_new.shape[0] == 25, f"ADMET should have 25 rows, got {df_admet_new.shape[0]}"
    assert 'Drug' in df_admet_new.columns, "ADMET should have Drug column"
    print("  ADMET validation passed: 25 drugs")

    # Check SwissADME
    assert df_swiss_new.shape[0] == 23, f"SwissADME should have 23 rows, got {df_swiss_new.shape[0]}"
    assert 'Drug' in df_swiss_new.columns, "SwissADME should have Drug column"
    assert 'Dactinomycin' not in df_swiss_new['Drug'].values, "Dactinomycin should NOT be in SwissADME"
    assert 'Plicamycin' not in df_swiss_new['Drug'].values, "Plicamycin should NOT be in SwissADME"
    print("  SwissADME validation passed: 23 drugs (no Dactinomycin, no Plicamycin)")

    # Check SMILES
    assert len(df_drugs_updated) == 25, "SMILES should have 25 rows"
    print("  SMILES validation passed: 25 drugs")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "="*80)
    print("INTEGRATION COMPLETE")
    print("="*80)
    print("\nGenerated files:")
    print(f"  1. {admet_output}")
    print(f"     Shape: {df_admet_new.shape} (25 drugs x {df_admet_new.shape[1]} cols)")
    print(f"  2. {swiss_output}")
    print(f"     Shape: {df_swiss_new.shape} (23 drugs x {df_swiss_new.shape[1]} cols)")
    print(f"  3. {smiles_output}")
    print(f"     Updated: {smiles_updated_count} SMILES")

    print("\nDrug breakdown:")
    print(f"  ADMET-AI: 25 drugs (all)")
    print(f"  SwissADME: 23 drugs (missing Dactinomycin, Plicamycin)")

    print("\nNext steps:")
    print("  1. Modify full_analysis.py to handle 23 SwissADME drugs separately")
    print("  2. Run full_analysis.py to retrain models")
    print("  3. Generate new report with corrected values")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
