"""
Data Loading and Preprocessing

Handles loading coefficient data and extracting features for prediction models.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict, List

from . import config


def load_coefficients(
    file_path: Optional[Path] = None,
    sheet_name: str = "dual_exponential"
) -> pd.DataFrame:
    """
    Load coefficient data from Excel file.

    Parameters:
    -----------
    file_path : Path, optional
        Path to coefficients Excel file. Uses config default if not provided.
    sheet_name : str
        Name of the sheet to load (default: 'dual_exponential')

    Returns:
    --------
    pd.DataFrame
        Raw coefficient data with cleaned column names
    """
    if file_path is None:
        file_path = config.COEFFICIENTS_FILE

    # Read with header on row 1 (0-indexed) to skip the equation header
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)

    # Clean column names
    df.columns = df.columns.str.strip()

    # Drop any completely empty rows
    df = df.dropna(how='all')

    # Set Drug as index if present
    if 'Drug' in df.columns:
        df = df.set_index('Drug')

    print(f"Loaded {len(df)} drugs from sheet '{sheet_name}'")
    return df


def extract_features_dual_exponential(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract features from dual exponential coefficient data.

    Dual exponential has 11 parameters per response type:
    R0, A_benefit, A_tox, kb, kt, tau_b, tau_t, nb, nt, mb, mt

    Parameters:
    -----------
    df : pd.DataFrame
        Raw coefficient data

    Returns:
    --------
    pd.DataFrame
        Feature matrix with Contractility and O2 coefficients
    """
    # Parameter names for dual exponential
    param_names = ['R0', 'A_benefit', 'A_tox', 'kb', 'kt', 'tau_b', 'tau_t', 'nb', 'nt', 'mb', 'mt']

    features = {}

    # Extract Contractility coefficients (no suffix)
    for param in param_names:
        col_name = f"{param}_Contractility"
        if param in df.columns:
            features[col_name] = df[param].values
        else:
            features[col_name] = np.full(len(df), np.nan)

    # Extract O2 coefficients (with .1 suffix in Excel)
    for param in param_names:
        col_name = f"{param}_O2"
        param_o2 = f'{param}.1'
        if param_o2 in df.columns:
            features[col_name] = df[param_o2].values
        elif param in df.columns:
            # Fallback: check if O2 columns have different naming
            alt_cols = [c for c in df.columns if param in c and 'O2' in c]
            if alt_cols:
                features[col_name] = df[alt_cols[0]].values
            else:
                features[col_name] = np.full(len(df), np.nan)
        else:
            features[col_name] = np.full(len(df), np.nan)

    features_df = pd.DataFrame(features, index=df.index)

    # Report any NaN values
    nan_counts = features_df.isna().sum()
    if nan_counts.any():
        print(f"Warning: Found NaN values in features:")
        for col, count in nan_counts[nan_counts > 0].items():
            print(f"  {col}: {count} NaN values")

    return features_df


def extract_features_pkpd_elimination(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract features from PK-PD elimination coefficient data.

    PK-PD elimination has 7 parameters per response type:
    R0, Emax, kappa, n, m, tau, k_elim

    Parameters:
    -----------
    df : pd.DataFrame
        Raw coefficient data

    Returns:
    --------
    pd.DataFrame
        Feature matrix with Contractility and O2 coefficients
    """
    param_names = ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim']

    features = {}

    # Contractility coefficients
    for param in param_names:
        col_name = f"{param}_Contractility"
        if param in df.columns:
            features[col_name] = df[param].values
        else:
            features[col_name] = np.full(len(df), np.nan)

    # O2 coefficients
    for param in param_names:
        col_name = f"{param}_O2"
        param_o2 = f'{param}.1'
        if param_o2 in df.columns:
            features[col_name] = df[param_o2].values
        else:
            features[col_name] = np.full(len(df), np.nan)

    return pd.DataFrame(features, index=df.index)


def extract_features(
    df: pd.DataFrame,
    equation_name: str = "dual_exponential"
) -> pd.DataFrame:
    """
    Extract features based on equation type.

    Parameters:
    -----------
    df : pd.DataFrame
        Raw coefficient data
    equation_name : str
        Name of the equation ('dual_exponential' or 'pkpd_elimination')

    Returns:
    --------
    pd.DataFrame
        Feature matrix
    """
    if equation_name == "dual_exponential":
        return extract_features_dual_exponential(df)
    elif equation_name == "pkpd_elimination":
        return extract_features_pkpd_elimination(df)
    else:
        raise ValueError(f"Unknown equation: {equation_name}")


def preprocess_targets(
    df: pd.DataFrame,
    target_column: str
) -> Tuple[np.ndarray, Dict]:
    """
    Preprocess target column to numeric values.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing target column
    target_column : str
        Name of the target column

    Returns:
    --------
    Tuple[np.ndarray, Dict]
        Numeric target array and mapping dictionary
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found")

    target = df[target_column].copy()

    # Convert to string and normalize
    target = target.astype(str).str.strip().str.lower()

    # Define mappings
    if target_column in ['Arrhythmia', 'Cardiotoxicity', 'heart_damage']:
        mapping = {'true': 1, 'false': 0, '1': 1, '0': 0}
        target_type = 'binary'
    elif target_column == 'Concern':
        mapping = {'most': 2, 'less': 1, 'no': 0, '2': 2, '1': 1, '0': 0}
        target_type = 'multiclass'
    else:
        # Try numeric conversion
        return pd.to_numeric(target, errors='coerce').values, {}

    target_numeric = target.map(mapping)

    # Check for unmapped values
    unmapped = target_numeric.isna()
    if unmapped.any():
        print(f"Warning: {unmapped.sum()} unmapped values in {target_column}")
        print(f"  Unique values: {target[unmapped].unique()}")

    return target_numeric.values, {'mapping': mapping, 'type': target_type}


def load_and_prepare_data(
    equation_name: str = "dual_exponential",
    file_path: Optional[Path] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, np.ndarray]]:
    """
    Load data and prepare features and targets.

    This is the main entry point for data loading.

    Parameters:
    -----------
    equation_name : str
        Name of the equation to use
    file_path : Path, optional
        Path to coefficients file

    Returns:
    --------
    Tuple containing:
        - df_raw: Original DataFrame
        - features_df: Extracted features
        - targets: Dictionary of target arrays
    """
    print("="*60)
    print(f"LOADING DATA: {equation_name}")
    print("="*60)

    # Load raw data
    df_raw = load_coefficients(file_path, sheet_name=equation_name)

    # Extract features
    features_df = extract_features(df_raw, equation_name)
    print(f"Extracted {features_df.shape[1]} features for {features_df.shape[0]} drugs")

    # Prepare targets
    targets = {}

    # Arrhythmia (binary)
    if 'Arrhythmia' in df_raw.columns:
        targets['arrhythmia'], _ = preprocess_targets(df_raw, 'Arrhythmia')
        n_pos = np.sum(targets['arrhythmia'] == 1)
        print(f"Arrhythmia: {n_pos} positive, {len(targets['arrhythmia']) - n_pos} negative")

    # Heart Damage (binary) - check both column names
    hd_col = None
    if 'heart_damage' in df_raw.columns:
        hd_col = 'heart_damage'
    elif 'Cardiotoxicity' in df_raw.columns:
        hd_col = 'Cardiotoxicity'

    if hd_col:
        targets['heart_damage'], _ = preprocess_targets(df_raw, hd_col)
        n_pos = np.sum(targets['heart_damage'] == 1)
        print(f"Heart Damage: {n_pos} positive, {len(targets['heart_damage']) - n_pos} negative")

    # Concern (multiclass)
    if 'Concern' in df_raw.columns:
        targets['concern'], _ = preprocess_targets(df_raw, 'Concern')
        for i, label in enumerate(['no', 'less', 'most']):
            n = np.sum(targets['concern'] == i)
            print(f"Concern '{label}': {n} samples")

    print("="*60)

    return df_raw, features_df, targets


if __name__ == "__main__":
    # Test data loading
    df_raw, features_df, targets = load_and_prepare_data("dual_exponential")

    print("\nFeatures shape:", features_df.shape)
    print("Feature columns:", features_df.columns.tolist())
    print("\nTargets:", list(targets.keys()))
    print("\nFirst 5 drugs:", features_df.index[:5].tolist())
