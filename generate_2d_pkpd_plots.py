"""
Generate 2D PK-PD Elimination Plots for Specific Drugs

Creates Time vs Response plots showing:
- Model prediction (mean curve across dose ratios)
- Model range (min-max shaded envelope)
- Raw experimental data overlay

Saves plot data to Excel for reproducibility.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from pathlib import Path

# Register Helvetica fonts from local fonts folder
_font_dir = Path(__file__).parent / 'fonts'
if _font_dir.exists():
    for _font_file in _font_dir.glob('*.ttf'):
        fm.fontManager.addfont(str(_font_file))
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# =============================================================================
# CONFIGURATION
# =============================================================================

# Drugs to plot
DRUGS = ['Bortezomib', 'Epirubicin', 'Vandetanib', 'Daunorubicin']

# Dose ratios - will be calculated dynamically from raw data for each drug
# Set to None to auto-detect, or specify a list like [0.5, 1.0, 1.5, 2.0]
DOSE_RATIOS = None  # Auto-detect from data

# Time range (hours)
TIME_POINTS = 1000  # Number of points for smooth curve
TIME_MAX = 96  # Hours

# Paths
PROJECT_ROOT = Path(__file__).parent
COEFF_PATH = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
O2_DATA_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'O2_Mean_Averaged.xlsx'
CONTRACTILITY_DATA_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'Heart_Contractility_Averaged.xlsx'
CMAX_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'drug_Cmax.csv'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / '2D_Plots'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# PK-PD ELIMINATION EQUATION
# =============================================================================

def pkpd_elimination_response(dose_ratio, time, R0, Emax, kappa, n, m, tau, k_elim):
    """
    Calculate PK-PD elimination response.

    R(C0, t) = R0 + Emax * (1 - exp(-kappa * (C0/Cmax * exp(-k_elim * t))^n * (t/tau)^m))

    Parameters:
    -----------
    dose_ratio : float or array
        Dose ratio (C0/Cmax), typically 0 to 2
    time : array
        Time (hours), typically 0 to 96
    R0, Emax, kappa, n, m, tau, k_elim : float
        Model parameters

    Returns:
    --------
    array
        Response values R(C0, t)
    """
    dose_ratio = np.asarray(dose_ratio)
    time = np.asarray(time)

    # Ensure positive values to avoid numerical issues
    kappa = max(kappa, 1e-9)
    tau = max(tau, 1e-9)
    k_elim = max(k_elim, 1e-9)
    time = np.maximum(time, 1e-9)

    # Concentration decays over time: C(t)/Cmax = (C0/Cmax) * exp(-k_elim * t)
    C_norm = dose_ratio * np.exp(-k_elim * time)

    # Time component: (t/tau)^m
    time_component = (time / tau) ** m

    # Concentration component: (C_norm)^n
    conc_component = C_norm ** n

    # Combined effect
    effect_term = kappa * conc_component * time_component

    # Full response
    response = R0 + Emax * (1 - np.exp(-effect_term))

    return response


# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

def load_cmax_dict():
    """Load Cmax values for all drugs."""
    df = pd.read_csv(CMAX_PATH)
    # Normalize drug names for matching
    cmax_dict = {}
    for _, row in df.iterrows():
        key = row['Drug'].lower().replace(' ', '')
        cmax_dict[key] = row['Cmax_uM']
    return cmax_dict


def get_cmax(drug_name, cmax_dict):
    """Get Cmax for a specific drug."""
    key = drug_name.lower().replace(' ', '')
    return cmax_dict.get(key)


def load_coefficients(drug_name, response_type):
    """
    Load PK-PD coefficients for a specific drug and response type.

    Parameters:
    -----------
    drug_name : str
        Name of the drug
    response_type : str
        'O2' or 'Contractility'

    Returns:
    --------
    dict
        Dictionary with R0, Emax, kappa, n, m, tau, k_elim
    """
    df = pd.read_excel(COEFF_PATH, sheet_name='pkpd_elimination', header=1)
    df.columns = df.columns.str.strip()

    row = df[df['Drug'] == drug_name]
    if row.empty:
        raise ValueError(f"Drug '{drug_name}' not found in coefficients file")
    row = row.iloc[0]

    # Column suffix: O2 uses '.1', Contractility uses no suffix
    suffix = '.1' if response_type == 'O2' else ''

    params = {
        'R0': row[f'R0{suffix}'],
        'Emax': row[f'Emax{suffix}'],
        'kappa': row[f'kappa{suffix}'],
        'n': row[f'n{suffix}'],
        'm': row[f'm{suffix}'],
        'tau': row[f'tau{suffix}'],
        'k_elim': row[f'k_elim{suffix}']
    }

    return params


def load_raw_data(drug_name, response_type, cmax=None):
    """
    Load raw experimental data for a specific drug.

    Parameters:
    -----------
    drug_name : str
        Name of the drug
    response_type : str
        'O2' or 'Contractility'
    cmax : float, optional
        Cmax value for calculating dose ratios

    Returns:
    --------
    dict
        Contains 'time', 'values', 'conc_labels', 'concentrations', 'dose_ratios'
    """
    data_path = O2_DATA_PATH if response_type == 'O2' else CONTRACTILITY_DATA_PATH

    try:
        df = pd.read_excel(data_path, sheet_name=drug_name)
        time_vals = df.iloc[:, 0].values
        data_vals = df.iloc[:, 1:].values
        conc_labels = df.columns[1:].tolist()

        # Parse concentrations from column labels
        concentrations = []
        for label in conc_labels:
            try:
                conc = float(str(label).replace('_', '.'))
                concentrations.append(conc)
            except:
                concentrations.append(np.nan)

        # Calculate dose ratios if Cmax provided
        dose_ratios = None
        if cmax is not None and cmax > 0:
            dose_ratios = [c / cmax for c in concentrations if not np.isnan(c)]

        return {
            'time': time_vals,
            'values': data_vals,
            'conc_labels': conc_labels,
            'concentrations': concentrations,
            'dose_ratios': dose_ratios
        }
    except Exception as e:
        print(f"  Warning: Could not load raw data for {drug_name} ({response_type}): {e}")
        return None


# =============================================================================
# MODEL COMPUTATION
# =============================================================================

def compute_model_predictions(params, time, dose_ratios):
    """
    Compute model predictions at multiple dose ratios.

    Returns:
    --------
    dict
        Contains 'time', 'mean', 'min', 'max', and individual dose ratio responses
    """
    all_responses = []
    response_by_dose = {}

    for dr in dose_ratios:
        response = pkpd_elimination_response(
            dr, time,
            params['R0'], params['Emax'], params['kappa'],
            params['n'], params['m'], params['tau'], params['k_elim']
        )
        all_responses.append(response)
        response_by_dose[f'dose_ratio_{dr}'] = response

    all_responses = np.array(all_responses)

    return {
        'time': time,
        'mean': np.mean(all_responses, axis=0),
        'min': np.min(all_responses, axis=0),
        'max': np.max(all_responses, axis=0),
        **response_by_dose
    }


# =============================================================================
# PLOTTING
# =============================================================================

def create_2d_plot(drug_name, response_type, model_data, raw_time, raw_values, conc_labels, dose_ratios=None):
    """
    Create a 2D Time vs Response plot with model and raw data.
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    # Colors and labels
    if response_type == 'O2':
        model_color = 'darkblue'
        raw_color = 'crimson'
        y_label = 'O₂ (% air saturation)'
        # Fixed Y-axis for O2
        y_min = 0
        y_max = 100
    else:
        model_color = 'darkgreen'
        raw_color = 'darkorange'
        y_label = 'Contractility (Amp std)'
        # Auto-scale Y-axis for Contractility based on actual data
        all_values = [model_data['mean'], model_data['min'], model_data['max']]
        if raw_values is not None:
            all_values.append(raw_values.flatten())
        all_values = np.concatenate([np.asarray(v).flatten() for v in all_values])
        all_values = all_values[np.isfinite(all_values)]
        y_min = max(0, np.min(all_values) * 0.9)
        y_max = np.max(all_values) * 1.1

    # Get model values
    time = model_data['time']
    mean = model_data['mean']
    min_vals = model_data['min']
    max_vals = model_data['max']

    # Clip values to y range for plotting
    mean = np.clip(mean, y_min, y_max)
    min_vals = np.clip(min_vals, y_min, y_max)
    max_vals = np.clip(max_vals, y_min, y_max)

    # Create label for model range
    if dose_ratios is not None and len(dose_ratios) > 0:
        min_dr = min(dose_ratios)
        max_dr = max(dose_ratios)
        range_label = f'Model Range ({min_dr:.1f}-{max_dr:.1f}× Cmax)'
    else:
        range_label = 'Model Range'

    ax.plot(time, mean, color=model_color, linewidth=2.5, alpha=0.9,
            label='Model Prediction', zorder=5)
    ax.fill_between(time, min_vals, max_vals, color=model_color, alpha=0.2,
                    label=range_label, zorder=4)

    # Plot raw data
    if raw_time is not None and raw_values is not None:
        for conc_idx in range(raw_values.shape[1]):
            conc_data = raw_values[:, conc_idx]
            valid = ~np.isnan(conc_data)
            if valid.sum() > 0:
                label = 'Raw Data' if conc_idx == 0 else None
                ax.scatter(raw_time[valid], conc_data[valid],
                          color=raw_color, alpha=0.4, s=25, zorder=3, label=label)

    # Formatting
    ax.set_xlabel('Time (hours)', fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.set_title(f'{drug_name} - {response_type}', fontsize=14, fontweight='bold')
    ax.set_xlim(0, TIME_MAX)
    ax.set_ylim(y_min, y_max)
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


# =============================================================================
# EXCEL EXPORT
# =============================================================================

def save_to_excel(all_data, output_path):
    """
    Save all plot data to Excel with multiple sheets.
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for drug_name, drug_data in all_data.items():
            for response_type, data in drug_data.items():
                sheet_name = f"{drug_name[:15]}_{response_type}"  # Excel sheet name limit

                # Model data
                model_df = pd.DataFrame({
                    'Time_hours': data['model']['time'],
                    'Model_Mean': data['model']['mean'],
                    'Model_Min': data['model']['min'],
                    'Model_Max': data['model']['max'],
                })

                # Add individual dose ratio columns (from actual data)
                dose_ratios_used = data['model'].get('dose_ratios_used', [])
                for dr in dose_ratios_used:
                    col_key = f'dose_ratio_{dr}'
                    if col_key in data['model']:
                        model_df[f'Dose_Ratio_{dr:.2f}'] = data['model'][col_key]

                # Raw data (if available)
                if data['raw_time'] is not None:
                    raw_df = pd.DataFrame({'Raw_Time_hours': data['raw_time']})
                    for i, label in enumerate(data['conc_labels']):
                        col_name = f'Raw_{label}' if isinstance(label, str) else f'Raw_Conc_{i+1}'
                        raw_df[col_name] = data['raw_values'][:, i]

                    # Combine model and raw data side by side
                    # Pad shorter dataframe
                    max_len = max(len(model_df), len(raw_df))
                    if len(model_df) < max_len:
                        model_df = model_df.reindex(range(max_len))
                    if len(raw_df) < max_len:
                        raw_df = raw_df.reindex(range(max_len))

                    combined_df = pd.concat([model_df, raw_df], axis=1)
                else:
                    combined_df = model_df

                combined_df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Add parameters sheet
        params_data = []
        for drug_name, drug_data in all_data.items():
            for response_type, data in drug_data.items():
                row = {'Drug': drug_name, 'Response_Type': response_type, 'Cmax': data.get('cmax')}
                row.update(data['params'])
                if data['dose_ratios']:
                    row['Min_Dose_Ratio'] = min(data['dose_ratios'])
                    row['Max_Dose_Ratio'] = max(data['dose_ratios'])
                params_data.append(row)

        params_df = pd.DataFrame(params_data)
        params_df.to_excel(writer, sheet_name='Parameters', index=False)

    print(f"\nData saved to: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("GENERATING 2D PK-PD ELIMINATION PLOTS")
    print("=" * 70)
    print(f"\nDrugs: {', '.join(DRUGS)}")
    print(f"Response types: O2, Contractility")
    print(f"Dose ratios: {'Auto-detect from data' if DOSE_RATIOS is None else DOSE_RATIOS}")
    print(f"Time range: 0-{TIME_MAX} hours")

    # Load Cmax dictionary
    cmax_dict = load_cmax_dict()

    # Time array for model
    time = np.linspace(0, TIME_MAX, TIME_POINTS)

    # Store all data for Excel export
    all_data = {}

    for drug_name in DRUGS:
        print(f"\n{'='*50}")
        print(f"Processing: {drug_name}")
        print('='*50)

        # Get Cmax for this drug
        cmax = get_cmax(drug_name, cmax_dict)
        if cmax is None:
            print(f"  WARNING: Cmax not found for {drug_name}, skipping")
            continue
        print(f"  Cmax: {cmax:.4f} uM")

        all_data[drug_name] = {}

        for response_type in ['O2', 'Contractility']:
            print(f"\n  {response_type}:")

            # Load coefficients
            try:
                params = load_coefficients(drug_name, response_type)
                print(f"    Coefficients loaded: R0={params['R0']:.4f}, Emax={params['Emax']:.4f}, "
                      f"kappa={params['kappa']:.4f}, n={params['n']:.4f}, m={params['m']:.4f}, "
                      f"tau={params['tau']:.4f}, k_elim={params['k_elim']:.4f}")
            except Exception as e:
                print(f"    ERROR loading coefficients: {e}")
                continue

            # Load raw data (with Cmax for dose ratio calculation)
            raw_data = load_raw_data(drug_name, response_type, cmax)
            if raw_data is not None:
                print(f"    Raw data loaded: {len(raw_data['time'])} time points, {raw_data['values'].shape[1]} concentrations")
                if raw_data['dose_ratios']:
                    print(f"    Dose ratio range: {min(raw_data['dose_ratios']):.2f} - {max(raw_data['dose_ratios']):.2f}")

            # Determine dose ratios to use for model
            if DOSE_RATIOS is not None:
                dose_ratios_to_use = DOSE_RATIOS
            elif raw_data is not None and raw_data['dose_ratios']:
                # Use actual dose ratios from data
                dose_ratios_to_use = sorted(raw_data['dose_ratios'])
                print(f"    Using {len(dose_ratios_to_use)} dose ratios from data")
            else:
                dose_ratios_to_use = [0.5, 1.0, 1.5, 2.0]  # Fallback

            # Compute model predictions
            model_data = compute_model_predictions(params, time, dose_ratios_to_use)
            model_data['dose_ratios_used'] = dose_ratios_to_use
            print(f"    Model computed: mean range [{model_data['mean'].min():.2f}, {model_data['mean'].max():.2f}]")

            # Store data
            all_data[drug_name][response_type] = {
                'params': params,
                'model': model_data,
                'raw_time': raw_data['time'] if raw_data else None,
                'raw_values': raw_data['values'] if raw_data else None,
                'conc_labels': raw_data['conc_labels'] if raw_data else None,
                'dose_ratios': raw_data['dose_ratios'] if raw_data else None,
                'cmax': cmax
            }

            # Create plot
            fig = create_2d_plot(drug_name, response_type, model_data,
                                raw_data['time'] if raw_data else None,
                                raw_data['values'] if raw_data else None,
                                raw_data['conc_labels'] if raw_data else None,
                                dose_ratios_to_use)

            # Save plot
            plot_filename = f"{drug_name}_{response_type}_2D_TimeSeries.png"
            plot_path = OUTPUT_DIR / plot_filename
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"    Plot saved: {plot_path.name}")

            # Also save as PDF
            pdf_path = OUTPUT_DIR / plot_filename.replace('.png', '.pdf')
            fig.savefig(pdf_path, bbox_inches='tight')
            print(f"    PDF saved: {pdf_path.name}")

            plt.close(fig)

    # Save all data to Excel
    excel_path = OUTPUT_DIR / '2D_PKPD_Plot_Data.xlsx'
    save_to_excel(all_data, excel_path)

    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("=" * 70)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Files created:")
    for f in sorted(OUTPUT_DIR.glob('*')):
        if f.name.startswith(tuple(DRUGS)) or f.name == '2D_PKPD_Plot_Data.xlsx':
            print(f"  - {f.name}")


if __name__ == '__main__':
    main()
