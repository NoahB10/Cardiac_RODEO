"""
Fit All Equations to Drug Response Data

This script fits all 11 equations to Contractility and O2 data,
saving coefficient CSV files for each equation.
"""
import numpy as np
import pandas as pd
import re
import warnings
from pathlib import Path
from scipy.optimize import curve_fit
from config import (
    CONTRACTILITY_FILE, O2_FILE, CMAX_FILE, COEFF_DIR,
    EQUATION_NAMES, EQUATIONS, EXCLUDED_DRUGS, SKIP_SHEETS, get_bounds
)
from equations import EQUATION_FUNCTIONS

warnings.filterwarnings('ignore')

# =============================================================================
# DATA PARSING
# =============================================================================

def normalize_drug_name(name):
    """Normalize drug name for matching."""
    name_str = str(name).lower()
    name_str = re.sub(r'\s+(of|the)\s*$', '', name_str)
    name_str = re.sub(r'\s|\(.*?\)', '', name_str)
    return name_str

def parse_conc(col_name):
    """Extract concentration value from column name."""
    if pd.isna(col_name):
        return None
    col_str = str(col_name).replace('_', '.')
    match = re.search(r'(\d+\.?\d*)', col_str)
    if match:
        return float(match.group(1))
    return None

def load_cmax_data(cmax_file):
    """Load Cmax reference data."""
    df = pd.read_csv(cmax_file)
    df['DrugKey'] = df['Drug'].apply(normalize_drug_name)
    return dict(zip(df['DrugKey'], df['Cmax_uM']))

def parse_excel_data(excel_file, cmax_dict, response_type='Contractility'):
    """
    Parse Excel file to extract drug response data.

    Returns dict: {drug_name: {'time': array, 'conc': array, 'response': array, 'cmax': float}}
    """
    print(f"\nParsing {excel_file.name} for {response_type}...")

    xl = pd.ExcelFile(excel_file)
    skip_lower = [s.lower() for s in SKIP_SHEETS]

    data_dict = {}

    for sheet_name in xl.sheet_names:
        if sheet_name.lower() in skip_lower:
            continue
        if any(excl.lower() in sheet_name.lower() for excl in EXCLUDED_DRUGS):
            print(f"  [EXCLUDED] {sheet_name}")
            continue

        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            if df.empty or len(df.columns) < 2:
                continue

            # Extract time and response data
            time_col = pd.to_numeric(df.iloc[:, 0], errors='coerce').values
            time_list, conc_list, response_list = [], [], []

            for col_idx in range(1, len(df.columns)):
                col_name = df.columns[col_idx]
                conc_val = parse_conc(col_name)
                if conc_val is None:
                    continue

                response_vals = pd.to_numeric(df.iloc[:, col_idx], errors='coerce').values
                valid = np.isfinite(time_col) & np.isfinite(response_vals)
                valid &= (time_col >= 0) & (time_col <= 96)

                if response_type == 'O2':
                    valid &= (response_vals < 200)

                time_list.extend(time_col[valid])
                conc_list.extend([conc_val] * np.sum(valid))
                response_list.extend(response_vals[valid])

            if len(response_list) < 25:
                continue

            # Get Cmax
            drug_key = normalize_drug_name(sheet_name)
            cmax = cmax_dict.get(drug_key, max(conc_list) if conc_list else 1.0)

            data_dict[sheet_name] = {
                'time': np.array(time_list),
                'conc': np.array(conc_list),
                'response': np.array(response_list),
                'cmax': cmax
            }

        except Exception as e:
            print(f"  Warning: {sheet_name}: {e}")

    print(f"  Loaded {len(data_dict)} drugs")
    return data_dict

# =============================================================================
# FITTING FUNCTIONS
# =============================================================================

def get_initial_guess(eq_name, response_type, data):
    """Get initial parameter guesses for each equation.

    For pkpd_elimination, uses data-dependent initialization matching MATLAB.
    """
    bounds = get_bounds(response_type)
    R0_mean = np.mean([bounds['R0'][0], bounds['R0'][1]])
    Emax_mean = bounds['Emax'][1] * 0.3

    A_mean = bounds['A'][1] * 0.3

    # Special handling for pkpd_elimination - use data-dependent initialization
    if eq_name == 'pkpd_elimination':
        Response = data['response']
        # Initial R0 from median of response (matches MATLAB)
        R0_init = np.median(Response)
        R0_init = np.clip(R0_init, bounds['R0'][0], bounds['R0'][1])
        # Initial Emax from range of response
        Emax_init = max(0, (np.max(Response) - R0_init) * 0.5)
        Emax_init = np.clip(Emax_init, 0, bounds['Emax'][1])
        return [R0_init, Emax_init, 1.0, 2.0, 2.0, 24.0, 0.05]

    guesses = {
        'dual_exponential': [R0_mean, Emax_mean*0.2, Emax_mean*0.3, 1.0, 1.0, 24, 24, 2.0, 2.0, 2.0, 2.0],
        'bivariate_gaussian': [R0_mean, A_mean*0.2, A_mean*0.3, 0.5, 24, 0.3, 12, 0, 1.5, 48, 0.3, 12, 0],
        'gaussian_hill_hybrid': [R0_mean, Emax_mean, 0.5, 0.3, 24, 2.0, Emax_mean*0.3, 2.0, 0.5, 12],
        'modified_hill_hormesis': [R0_mean, Emax_mean*0.2, Emax_mean*0.3, 0.3, 1.0, 2.0, 2.0, 24, 24],
        'gaussian_ridge': [R0_mean, A_mean*0.3, A_mean*0.3, 0.5, 0.3, 1.5, 0.3, 1.0, 24, 2.0, 0.1],
        'adaptive_response': [R0_mean, Emax_mean*0.3, 0.3, 2.0, 12.0, 48.0],
        'biphasic_response': [R0_mean, Emax_mean*0.1, Emax_mean*0.3, 0.1, 1.0, 2.0, 2.0, 12.0, 24.0],
        'cumulative_exposure': [R0_mean, Emax_mean*0.3, 1.0, 1.0, 0.05],
        'recovery_model': [R0_mean, Emax_mean*0.3, 0.1, 0.05],
        'modified_hill_simple': [R0_mean, Emax_mean*0.3, 1.0, 24.0, 1.0, 1.0],
        'hormesis_v0': [R0_mean, Emax_mean*0.1, Emax_mean*0.3, 0.3, 1.0, 2.0, 2.0, 24, 24],
    }
    return guesses.get(eq_name, [R0_mean])

def get_param_bounds(eq_name, response_type):
    """Get parameter bounds for each equation."""
    b = get_bounds(response_type)

    bounds_dict = {
        'dual_exponential': (
            [b['R0'][0], 0, 0, 1e-6, 1e-6, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
            [b['R0'][1], b['Emax'][1], b['Emax'][1], 100, 100, 96, 96, 6, 6, 6, 6]
        ),
        'bivariate_gaussian': (
            [b['R0'][0], 0, 0, 0, 0, 0.01, 0.01, -0.9, 0, 0, 0.01, 0.01, -0.9],
            [b['R0'][1], b['A'][1], b['A'][1], 2, 96, 2, 96, 0.9, 2, 96, 2, 96, 0.9]
        ),
        'gaussian_hill_hybrid': (
            [b['R0'][0], 0, 0, 0.01, 0.1, 0.1, 0, 0.1, 0.01, 0.1],
            [b['R0'][1], b['Emax'][1], 2, 2, 96, 6, b['Emax'][1], 6, 2, 96]
        ),
        'modified_hill_hormesis': (
            [b['R0'][0], 0, 0, 0.01, 0.01, 0.1, 0.1, 0.1, 0.1],
            [b['R0'][1], b['Emax'][1], b['Emax'][1], 2, 2, 6, 6, 96, 96]
        ),
        'gaussian_ridge': (
            [b['R0'][0], 0, 0, 0, 0.01, 0, 0.01, 1e-6, 0.1, 0.1, 1e-6],
            [b['R0'][1], b['A'][1], b['A'][1], 2, 2, 2, 2, 100, 96, 6, 1]
        ),
        'adaptive_response': (
            [b['R0'][0], 0, 0.01, 0.1, 0.1, 0.1],
            [b['R0'][1], b['Emax'][1], 2.0, 6.0, 96.0, 96.0]
        ),
        'biphasic_response': (
            [b['R0'][0], 0, 0, 0.01, 0.01, 0.1, 0.1, 0.1, 0.1],
            [b['R0'][1], b['Emax'][1]*0.5, b['Emax'][1], 2.0, 2.0, 6.0, 6.0, 96.0, 96.0]
        ),
        'cumulative_exposure': (
            [b['R0'][0], 0, 0.1, 0.01, 1e-6],
            [b['R0'][1], b['Emax'][1], 10, 2.0, 1.0]
        ),
        'recovery_model': (
            [b['R0'][0], 0, 1e-6, 1e-6],
            [b['R0'][1], b['Emax'][1], 10, 1.0]
        ),
        'modified_hill_simple': (
            [b['R0'][0], 0, 1e-6, 1e-2, 0.5, 0.5],
            [b['R0'][1], b['Emax'][1], 1e3, 96, 6.0, 6.0]
        ),
        'pkpd_elimination': (
            [b['R0'][0], 0, 1e-6, 0.1, 0.1, 0.1, 1e-6],
            [b['R0'][1], b['Emax'][1], 100, 6.0, 6.0, 96, 1.0]
        ),
        'hormesis_v0': (
            [b['R0'][0], 0, 0, 0.01, 0.01, 0.1, 0.1, 0.1, 0.1],
            [b['R0'][1], b['Emax'][1]*0.5, b['Emax'][1], 2, 2, 6, 6, 96, 96]
        ),
    }
    return bounds_dict.get(eq_name, ([0], [1]))

def fit_single_drug(eq_name, drug_data, response_type):
    """
    Fit a single drug to a single equation using multi-start optimization.

    Returns dict with parameters, R2, SSE, N_points, or None if failed.
    """
    Time = drug_data['time']
    Conc = drug_data['conc']
    Response = drug_data['response']
    Cmax = drug_data['cmax']

    # Normalize concentration
    C_norm = Conc / Cmax
    X = np.array([C_norm, Time])

    # Get equation function
    eq_func = EQUATION_FUNCTIONS.get(eq_name)
    if eq_func is None:
        return None

    # Get bounds and initial guess
    lb, ub = get_param_bounds(eq_name, response_type)
    p0_base = get_initial_guess(eq_name, response_type, drug_data)

    # Data-driven initial values
    R0_data = np.median(Response)
    bounds = get_bounds(response_type)
    R0_data = np.clip(R0_data, bounds['R0'][0], bounds['R0'][1])
    response_range = np.max(Response) - np.min(Response)
    Emax_data = response_range * 0.5

    # Generate multiple initial guesses for multi-start
    n_params = len(p0_base)
    initial_guesses = [p0_base]  # Start with default guess

    # Add data-driven variations
    if n_params >= 3:
        p0_var1 = p0_base.copy()
        p0_var1[0] = R0_data
        if n_params > 1:
            p0_var1[1] = Emax_data * 0.3
        if n_params > 2:
            p0_var1[2] = Emax_data * 0.5
        initial_guesses.append(p0_var1)

        p0_var2 = p0_base.copy()
        p0_var2[0] = np.min(Response)
        if n_params > 1:
            p0_var2[1] = Emax_data * 0.5
        if n_params > 2:
            p0_var2[2] = Emax_data * 0.3
        initial_guesses.append(p0_var2)

    best_result = None
    best_r2 = -np.inf

    for p0 in initial_guesses:
        try:
            # Ensure p0 is within bounds
            p0_clipped = np.clip(p0, lb, ub)

            popt, _ = curve_fit(eq_func, X, Response, p0=p0_clipped, bounds=(lb, ub),
                               maxfev=50000, ftol=1e-8, xtol=1e-8,
                               method='trf', x_scale='jac')

            # Calculate metrics
            y_pred = eq_func(X, *popt)
            ss_res = np.sum((Response - y_pred) ** 2)
            ss_tot = np.sum((Response - np.mean(Response)) ** 2)
            r2 = 1 - ss_res / max(ss_tot, 1e-10)

            if r2 > best_r2:
                best_r2 = r2
                best_result = {
                    'params': popt,
                    'R2': r2,
                    'SSE': ss_res,
                    'SSY': ss_tot,
                    'N_points': len(Response),
                    'Cmax_used': Cmax
                }
        except Exception:
            continue

    return best_result

def fit_equation(eq_name, data_dict, response_type):
    """
    Fit one equation to all drugs.

    Returns DataFrame with columns: Drug, [params], Cmax_used, R2, N_points
    """
    print(f"\n  Fitting {eq_name}...")

    eq_meta = EQUATIONS.get(eq_name, {})
    param_names = eq_meta.get('params', [])

    results = []
    success = 0

    for drug_name, drug_data in data_dict.items():
        result = fit_single_drug(eq_name, drug_data, response_type)

        if result is not None:
            row = {'Drug': drug_name}
            for i, pname in enumerate(param_names):
                row[pname] = result['params'][i] if i < len(result['params']) else np.nan
            row['Cmax_used'] = result['Cmax_used']
            row['R2'] = result['R2']
            row['N_points'] = result['N_points']
            results.append(row)
            success += 1

    print(f"    {success}/{len(data_dict)} drugs fitted successfully")

    if results:
        return pd.DataFrame(results)
    return None

# =============================================================================
# MAIN FITTING PIPELINE
# =============================================================================

def fit_all_equations(response_type='Contractility'):
    """
    Fit all equations to the specified response type.

    Saves CSV files to COEFF_DIR/{eq_name}_coefficients_{response_type}.csv
    """
    print(f"\n{'='*80}")
    print(f"FITTING ALL EQUATIONS - {response_type}")
    print(f"{'='*80}")

    # Load data
    cmax_dict = load_cmax_data(CMAX_FILE)

    if response_type == 'Contractility':
        data_dict = parse_excel_data(CONTRACTILITY_FILE, cmax_dict, response_type)
    else:
        data_dict = parse_excel_data(O2_FILE, cmax_dict, response_type)

    # Fit each equation
    COEFF_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for eq_name in EQUATION_NAMES:
        df = fit_equation(eq_name, data_dict, response_type)

        if df is not None:
            # Save to CSV
            output_file = COEFF_DIR / f"{eq_name}_coefficients_{response_type.lower()}.csv"
            df.to_csv(output_file, index=False)
            print(f"    Saved: {output_file.name}")
            results[eq_name] = df

    return results

def run_all_fits():
    """Run fitting for both Contractility and O2."""
    print("\n" + "="*80)
    print("EQUATION FITTING PIPELINE")
    print("="*80)
    print("\nThis will fit all 11 equations to both Contractility and O2 data.")
    print("Coefficient files will be saved to:", COEFF_DIR)

    # Fit Contractility
    contract_results = fit_all_equations('Contractility')

    # Fit O2
    o2_results = fit_all_equations('O2')

    print("\n" + "="*80)
    print("FITTING COMPLETE")
    print("="*80)
    print(f"\nContractility: {len(contract_results)} equations fitted")
    print(f"O2: {len(o2_results)} equations fitted")
    print(f"\nCoefficient files saved to: {COEFF_DIR}")

    return contract_results, o2_results

if __name__ == "__main__":
    run_all_fits()
