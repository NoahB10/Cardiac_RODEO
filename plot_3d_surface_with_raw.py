"""
Plot 3D PK-PD surface with raw data overlay for Bortezomib.
Matches the style from Paper_Plots_PKPD_Elimination_Surfaces.ipynb
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
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

DRUG_NAME = 'Bortezomib'
PROJECT_ROOT = Path(__file__).parent
COEFF_PATH = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
O2_DATA_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'O2_Mean_Averaged.xlsx'
CONTRACTILITY_DATA_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'Heart_Contractility_Averaged.xlsx'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / '3D_Plots'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# PK-PD ELIMINATION EQUATION (same as notebook)
# =============================================================================

def pkpd_elimination_response(dose_ratio, time, R0, Emax, kappa, n, m, tau, k_elim):
    """Calculate PK-PD elimination response."""
    dose_ratio = np.asarray(dose_ratio)
    time = np.asarray(time)

    # Create meshgrid if inputs are 1D
    if dose_ratio.ndim == 1 and time.ndim == 1:
        dose_ratio, time = np.meshgrid(dose_ratio, time)

    kappa = max(kappa, 1e-9)
    tau = max(tau, 1e-9)
    k_elim = max(k_elim, 1e-9)
    time = np.maximum(time, 1e-9)

    C_norm = dose_ratio * np.exp(-k_elim * time)
    time_component = (time / tau) ** m
    conc_component = C_norm ** n
    effect_term = kappa * conc_component * time_component
    response = R0 + Emax * (1 - np.exp(-effect_term))

    return response


# =============================================================================
# DATA LOADING
# =============================================================================

def load_coefficients(drug_name, response_type):
    """Load PK-PD coefficients for a drug."""
    df = pd.read_excel(COEFF_PATH, sheet_name='pkpd_elimination', header=1)
    df.columns = df.columns.str.strip()
    row = df[df['Drug'] == drug_name].iloc[0]

    suffix = '.1' if response_type == 'O2' else ''

    return {
        'R0': row[f'R0{suffix}'],
        'Emax': row[f'Emax{suffix}'],
        'kappa': row[f'kappa{suffix}'],
        'n': row[f'n{suffix}'],
        'm': row[f'm{suffix}'],
        'tau': row[f'tau{suffix}'],
        'k_elim': row[f'k_elim{suffix}'],
        'Cmax': row[f'Cmax_used{suffix}']
    }


def load_raw_data(drug_name, response_type):
    """Load raw data and convert to (time, dose_ratio, response) arrays."""
    data_path = O2_DATA_PATH if response_type == 'O2' else CONTRACTILITY_DATA_PATH
    df = pd.read_excel(data_path, sheet_name=drug_name)

    # Get Cmax for dose ratio conversion
    params = load_coefficients(drug_name, response_type)
    cmax = params['Cmax']

    # First column is time
    time_vals = df.iloc[:, 0].values

    # Remaining columns are concentrations
    conc_columns = df.columns[1:]

    # Build arrays for 3D scatter
    all_times = []
    all_dose_ratios = []
    all_responses = []

    for conc_col in conc_columns:
        try:
            conc = float(conc_col)
            dose_ratio = conc / cmax
            responses = df[conc_col].values

            for t, r in zip(time_vals, responses):
                if not np.isnan(r):
                    all_times.append(t)
                    all_dose_ratios.append(dose_ratio)
                    all_responses.append(r)
        except ValueError:
            continue

    return np.array(all_times), np.array(all_dose_ratios), np.array(all_responses)


# =============================================================================
# PLOTTING (matching notebook style)
# =============================================================================

def plot_3d_surface_with_raw(drug_name, response_type, remove_r0_offset=True):
    """
    Plot 3D surface with raw data overlay.
    Matches Paper_Plots_PKPD_Elimination_Surfaces.ipynb style.
    """
    # Load coefficients
    params = load_coefficients(drug_name, response_type)
    R0 = params['R0']
    Emax = params['Emax']
    kappa = params['kappa']
    n = params['n']
    m = params['m']
    tau = params['tau']
    k_elim = params['k_elim']

    print(f"\n{drug_name} - {response_type}")
    print(f"  Coefficients: R0={R0:.4f}, Emax={Emax:.4f}, kappa={kappa:.4f}")
    print(f"                n={n:.4f}, m={m:.4f}, tau={tau:.4f}, k_elim={k_elim:.4f}")
    print(f"  Cmax={params['Cmax']}")

    # Grid for surface (same as notebook: 60x60)
    dose_ratio = np.linspace(0, 2, 60)
    time = np.linspace(0, 96, 60)
    T, Dr = np.meshgrid(time, dose_ratio)

    # Calculate response surface
    Response = pkpd_elimination_response(Dr, T, R0, Emax, kappa, n, m, tau, k_elim)
    if remove_r0_offset:
        Response = Response - R0

    # Load raw data
    raw_times, raw_dose_ratios, raw_responses = load_raw_data(drug_name, response_type)
    if remove_r0_offset:
        raw_responses = raw_responses - R0

    print(f"  Raw data: {len(raw_times)} points")
    print(f"  Dose ratio range in raw data: {raw_dose_ratios.min():.2f} - {raw_dose_ratios.max():.2f}")

    # Create figure
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Color normalization
    vmin = 0
    vmax = np.nanmax(Response)
    norm = plt.Normalize(vmin=vmin, vmax=vmax)

    # Plot surface (same style as notebook)
    surf = ax.plot_surface(T, Dr, Response, cmap='turbo', norm=norm,
                          linewidth=0, antialiased=True, edgecolor='none', alpha=0.7)

    # Plot raw data as scatter points
    # Only plot points within the surface range (dose_ratio 0-2)
    mask = raw_dose_ratios <= 2.0
    ax.scatter(raw_times[mask], raw_dose_ratios[mask], raw_responses[mask],
               c='black', s=15, alpha=0.8, label='Raw Data', depthshade=True)

    # Also plot points outside range with different color (optional)
    mask_outside = raw_dose_ratios > 2.0
    if mask_outside.any():
        ax.scatter(raw_times[mask_outside], raw_dose_ratios[mask_outside], raw_responses[mask_outside],
                   c='red', s=15, alpha=0.6, marker='^', label='Raw Data (>2x Cmax)')

    # Set Z-axis limits
    z_min = min(0, np.nanmin(raw_responses))
    z_max = max(vmax, np.nanmax(raw_responses)) * 1.1
    ax.set_zlim(z_min, z_max)

    # Labels (same as notebook)
    ax.set_xlabel('Time (hours)', fontsize=10)
    ax.set_ylabel('Dose Ratio (C0/Cmax)', fontsize=10)
    z_label = f'{response_type} Response'
    if remove_r0_offset:
        z_label += ' (R0 removed)'
    ax.set_zlabel(z_label, fontsize=10)

    ax.set_title(f'{drug_name} - {response_type}', fontsize=12, pad=20)

    # Set view angle (same as notebook)
    ax.view_init(elev=25, azim=-158)

    # Add legend
    ax.legend(loc='upper left')

    plt.tight_layout()
    return fig


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("3D PK-PD SURFACE WITH RAW DATA OVERLAY")
    print("=" * 70)

    for response_type in ['O2', 'Contractility']:
        fig = plot_3d_surface_with_raw(DRUG_NAME, response_type, remove_r0_offset=True)

        # Save
        filename = f"{DRUG_NAME}_{response_type}_3D_Surface_with_Raw"
        fig.savefig(OUTPUT_DIR / f"{filename}.png", dpi=300, bbox_inches='tight')
        fig.savefig(OUTPUT_DIR / f"{filename}.pdf", bbox_inches='tight')
        print(f"  Saved: {filename}.png/pdf")

        plt.close(fig)

    print("\n" + "=" * 70)
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == '__main__':
    main()
