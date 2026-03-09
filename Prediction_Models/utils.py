"""
Utility functions for Cardiac RODEO prediction models.

This module provides helper functions for feature extraction and target preprocessing.
"""

import pandas as pd
import numpy as np


def extract_features(df, equation_name='pkpd_elimination'):
    """
    Extract features (coefficients) from the raw dataframe for a given equation.
    
    This function extracts PK-PD elimination equation coefficients for both
    Contractility and O2 response types, creating a feature matrix suitable
    for machine learning models.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Raw dataframe containing equation coefficients with columns like
        R0, Emax, kappa, n, m, tau, k_elim (for Contractility) and
        R0.1, Emax.1, kappa.1, n.1, m.1, tau.1, k_elim.1 (for O2)
    equation_name : str
        Name of the equation sheet (default: 'pkpd_elimination')
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with extracted features. Each row corresponds to a drug,
        and columns are the coefficient features for Contractility and O2.
    """
    # Parameter names for PK-PD elimination equation
    param_names = ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim']
    
    # Initialize feature list
    features = []
    
    # Extract Contractility coefficients (no suffix)
    for param in param_names:
        if param in df.columns:
            features.append(df[param].values)
        else:
            # If column doesn't exist, fill with NaN
            features.append(np.full(len(df), np.nan))
    
    # Extract O2 coefficients (with .1 suffix)
    for param in param_names:
        param_o2 = f'{param}.1'
        if param_o2 in df.columns:
            features.append(df[param_o2].values)
        else:
            # Try alternative naming
            alt_cols = [c for c in df.columns if c.startswith(param) and c != param]
            if alt_cols:
                features.append(df[alt_cols[-1]].values)
            else:
                features.append(np.full(len(df), np.nan))
    
    # Create feature names
    feature_names = [f'{p}_Contractility' for p in param_names] + \
                    [f'{p}_O2' for p in param_names]
    
    # Create DataFrame
    features_df = pd.DataFrame(
        np.column_stack(features),
        columns=feature_names,
        index=df.index
    )
    
    return features_df


def preprocess_targets(df, target_column):
    """
    Preprocess target columns to numeric format.
    
    Converts target labels to numeric values:
    - Binary targets (Arrhythmia, Cardiotoxicity): 'true'/'false' → 1/0
    - Multiclass targets (Concern): 'most'/'less'/'no' → 2/1/0
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing target columns
    target_column : str
        Name of the target column to preprocess
        
    Returns:
    --------
    pd.Series
        Series with numeric target values
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataframe")
    
    target_series = df[target_column].copy()
    
    # Convert to string and normalize
    target_series = target_series.astype(str).str.strip().str.lower()
    
    # Handle binary targets (Arrhythmia, Cardiotoxicity, heart_damage)
    if target_column in ['Arrhythmia', 'Cardiotoxicity', 'heart_damage']:
        # Map 'true' → 1, 'false' → 0
        target_series = target_series.map({
            'true': 1,
            'false': 0,
            '1': 1,
            '0': 0
        })
    # Handle multiclass target (Concern)
    elif target_column == 'Concern':
        # Map 'most' → 2, 'less' → 1, 'no' → 0
        target_series = target_series.map({
            'most': 2,
            'less': 1,
            'no': 0,
            '2': 2,
            '1': 1,
            '0': 0
        })
    else:
        # For unknown targets, try to convert to numeric
        target_series = pd.to_numeric(target_series, errors='coerce')
    
    return target_series




