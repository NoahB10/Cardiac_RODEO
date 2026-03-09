"""
Consolidate Coefficient Files

Merges Contractility and O2 coefficient files into a single consolidated CSV
per equation, ready for Excel export.
"""
import pandas as pd
import numpy as np
import re
from pathlib import Path
from config import COEFF_DIR, EQUATION_NAMES, EQUATIONS, CLASSIFICATION_FILE

# =============================================================================
# DRUG CLASSIFICATION
# =============================================================================

DRUG_CLASSIFICATION = {}

def load_drug_classification():
    """Load drug classification from the reference Excel file."""
    global DRUG_CLASSIFICATION

    if CLASSIFICATION_FILE.exists():
        try:
            df = pd.read_excel(CLASSIFICATION_FILE, sheet_name='pkpd_elimination', header=1)
            df.columns = df.columns.str.strip()

            for _, row in df.iterrows():
                drug = str(row['Drug']).strip()
                DRUG_CLASSIFICATION[drug.lower()] = {
                    'Arrhythmia': str(row.get('Arrhythmia', 'false')).lower(),
                    'Cardiotoxicity': str(row.get('heart_damage', row.get('Cardiotoxicity', 'false'))).lower(),
                    'Concern': str(row.get('Concern', 'no')).lower()
                }
            print(f"Loaded classification for {len(DRUG_CLASSIFICATION)} drugs")
        except Exception as e:
            print(f"Warning: Could not load classification: {e}")
    else:
        print("Classification file not found, using defaults")

def normalize_drug_name(name):
    """Normalize drug name for matching."""
    return re.sub(r'\s|\(.*?\)', '', str(name).lower())

def get_drug_classification(drug_name):
    """Get classification for a drug."""
    drug_lower = drug_name.lower()

    if drug_lower in DRUG_CLASSIFICATION:
        return DRUG_CLASSIFICATION[drug_lower]

    # Try normalized matching
    normalized = normalize_drug_name(drug_name)
    for key, value in DRUG_CLASSIFICATION.items():
        if normalize_drug_name(key) == normalized:
            return value

    return {'Arrhythmia': 'false', 'Cardiotoxicity': 'false', 'Concern': 'no'}

def get_sort_key(drug_name):
    """Get sort key for organizing drugs by classification."""
    classification = get_drug_classification(drug_name)
    concern_order = {'most': 0, 'less': 1, 'no': 2}
    bool_order = {'true': 0, 'false': 1}

    return (
        concern_order.get(classification['Concern'], 2),
        bool_order.get(classification['Cardiotoxicity'], 1),
        bool_order.get(classification['Arrhythmia'], 1),
        drug_name.lower()
    )

# =============================================================================
# CONSOLIDATION FUNCTIONS
# =============================================================================

def consolidate_equation(eq_name, coeff_dir):
    """
    Consolidate Contractility and O2 files for a single equation.

    Creates a CSV with format:
    # Equation: [Name]
    # [Formula]
    # Parameters: [list]
    #
    Drug,Contractility,,,...,O2,,,
    Drug,Arrhythmia,Cardiotoxicity,Concern,param1,param2,...,,param1,param2,...
    data rows...
    """
    coeff_dir = Path(coeff_dir)
    eq_info = EQUATIONS.get(eq_name, {})

    contract_file = coeff_dir / f"{eq_name}_coefficients_contractility.csv"
    o2_file = coeff_dir / f"{eq_name}_coefficients_o2.csv"

    if not contract_file.exists() or not o2_file.exists():
        print(f"  Skipping {eq_name}: missing files")
        return None

    # Load data
    df_contract = pd.read_csv(contract_file)
    df_o2 = pd.read_csv(o2_file)

    # Normalize drug names for matching
    df_contract['DrugKey'] = df_contract['Drug'].apply(normalize_drug_name)
    df_o2['DrugKey'] = df_o2['Drug'].apply(normalize_drug_name)

    # Get parameter columns (exclude metadata)
    exclude_cols = {'Drug', 'DrugKey', 'Arrhythmia', 'Cardiotoxicity', 'heart_damage', 'Concern'}
    param_cols = [c for c in df_contract.columns if c not in exclude_cols]

    # Get all unique drugs
    all_drug_keys = set(df_contract['DrugKey'].unique()) | set(df_o2['DrugKey'].unique())
    all_drug_keys = sorted(all_drug_keys, key=lambda k: get_sort_key(
        df_contract[df_contract['DrugKey']==k]['Drug'].iloc[0]
        if k in df_contract['DrugKey'].values
        else df_o2[df_o2['DrugKey']==k]['Drug'].iloc[0]
    ))

    # Build consolidated data
    rows = []
    for drug_key in all_drug_keys:
        row_c = df_contract[df_contract['DrugKey'] == drug_key]
        row_o = df_o2[df_o2['DrugKey'] == drug_key]

        drug_name = row_c['Drug'].iloc[0] if len(row_c) > 0 else row_o['Drug'].iloc[0]
        classification = get_drug_classification(drug_name)

        row_data = {
            'Drug': drug_name,
            'Arrhythmia': classification['Arrhythmia'],
            'Cardiotoxicity': classification['Cardiotoxicity'],
            'Concern': classification['Concern']
        }

        # Add Contractility params
        for col in param_cols:
            row_data[f'C_{col}'] = row_c[col].iloc[0] if len(row_c) > 0 else np.nan

        # Add O2 params
        for col in param_cols:
            row_data[f'O2_{col}'] = row_o[col].iloc[0] if len(row_o) > 0 else np.nan

        rows.append(row_data)

    df_consolidated = pd.DataFrame(rows)

    # Write consolidated CSV with proper header format
    output_file = coeff_dir / f"{eq_name}_coefficients.csv"

    with open(output_file, 'w', encoding='utf-8') as f:
        # Comment header
        f.write(f"# Equation: {eq_info.get('name', eq_name)}\n")
        f.write(f"# {eq_info.get('formula', '')}\n")
        f.write(f"# Parameters: {eq_info.get('params', [])}\n")
        f.write("#\n")

        # Group header row
        header_row = ['Drug', 'Contractility']
        header_row.extend([''] * (3 + len(param_cols) - 1))  # classification + params
        header_row.append('')  # separator
        header_row.append('O2')
        header_row.extend([''] * (len(param_cols) - 1))
        f.write(','.join(header_row) + '\n')

        # Column names row
        col_row = ['Drug', 'Arrhythmia', 'Cardiotoxicity', 'Concern']
        col_row.extend(param_cols)
        col_row.append('')  # separator
        col_row.extend(param_cols)
        f.write(','.join(col_row) + '\n')

        # Data rows
        for _, row in df_consolidated.iterrows():
            data_row = [
                str(row['Drug']),
                str(row['Arrhythmia']),
                str(row['Cardiotoxicity']),
                str(row['Concern'])
            ]
            # Contractility values
            for col in param_cols:
                val = row.get(f'C_{col}', np.nan)
                data_row.append('' if pd.isna(val) else str(val))
            data_row.append('')  # separator
            # O2 values
            for col in param_cols:
                val = row.get(f'O2_{col}', np.nan)
                data_row.append('' if pd.isna(val) else str(val))
            f.write(','.join(data_row) + '\n')

    print(f"  Consolidated: {eq_name} ({len(df_consolidated)} drugs)")
    return output_file

def consolidate_all_equations():
    """Consolidate all equations."""
    print("\n" + "="*80)
    print("CONSOLIDATING COEFFICIENT FILES")
    print("="*80 + "\n")

    load_drug_classification()

    consolidated_files = []
    for eq_name in EQUATION_NAMES:
        result = consolidate_equation(eq_name, COEFF_DIR)
        if result:
            consolidated_files.append(result)

    print(f"\nConsolidated {len(consolidated_files)}/{len(EQUATION_NAMES)} equations")
    return consolidated_files

if __name__ == "__main__":
    consolidate_all_equations()
