"""
Generate combined 5x5 grid plots for O2 and Contractility response surfaces.
- Single combined image (not 25 separate files)
- Only edge plots have axis labels
- Bigger plots with minimal white space
- Colorbar (scale bar) included
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set Helvetica font globally
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
plt.rcParams['font.size'] = 12

# Find project root
current_dir = Path.cwd()
if current_dir.name == 'Prediction_Models':
    PROJECT_ROOT = current_dir.parent
elif (current_dir / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir
elif (current_dir.parent / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir.parent
else:
    PROJECT_ROOT = current_dir

EXCEL_PATH = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / '3D_Plots'

# PK-PD Elimination equation
def pkpd_elimination_response(dose_ratio, time, R0, Emax, kappa, n, m, tau, k_elim):
    dose_ratio = np.asarray(dose_ratio)
    time = np.asarray(time)
    if dose_ratio.ndim == 1 and time.ndim == 1:
        dose_ratio, time = np.meshgrid(dose_ratio, time)
    kappa = max(kappa, 1e-9)
    tau = max(tau, 1e-9)
    k_elim = max(k_elim, 1e-9)
    time = np.maximum(time, 1e-9)
    C_norm = dose_ratio * np.exp(-k_elim * time)
    time_component = (time / tau) ** m
    conc_component = C_norm ** n
    combined = kappa * conc_component * time_component
    response = R0 + Emax * (1 - np.exp(-combined))
    return response

# Load data
print("Loading data...")
df_raw = pd.read_excel(EXCEL_PATH, sheet_name='pkpd_elimination', header=1)
df_raw.columns = df_raw.columns.str.strip()
df_raw = df_raw[df_raw['Drug'].notna() & (df_raw['Drug'].astype(str).str.strip() != '')]

param_names = ['R0', 'Emax', 'kappa', 'n', 'm', 'tau', 'k_elim']

def extract_coefficients(df, response_type):
    base_cols = ['Drug', 'Arrhythmia', 'heart_damage', 'Concern']
    if response_type == 'Contractility':
        param_cols = param_names.copy()
    else:
        param_cols = [f'{p}.1' if f'{p}.1' in df.columns else f'{p}_1' for p in param_names]

    result = df[base_cols].copy()
    for i, param in enumerate(param_names):
        if i < len(param_cols) and param_cols[i] in df.columns:
            result[param] = df[param_cols[i]]
        else:
            result[param] = np.nan
    return result

df_contractility = extract_coefficients(df_raw, 'Contractility')
df_o2 = extract_coefficients(df_raw, 'O2')

# Filter valid
def filter_valid(df):
    valid_mask = df[param_names].notna().all(axis=1) & df[param_names].apply(lambda x: np.isfinite(x)).all(axis=1)
    return df[valid_mask].copy()

df_contractility_valid = filter_valid(df_contractility)
df_o2_valid = filter_valid(df_o2)

# Calculate global ranges
def calculate_global_range(df):
    dose_ratio = np.linspace(0, 2, 60)
    time = np.linspace(0, 96, 60)
    T, Dr = np.meshgrid(time, dose_ratio)
    all_max = []
    for idx in df.index:
        row = df.loc[idx]
        Response = pkpd_elimination_response(Dr, T, row['R0'], row['Emax'], row['kappa'],
                                             row['n'], row['m'], row['tau'], row['k_elim'])
        Response_no_r0 = Response - row['R0']
        if np.isfinite(np.nanmax(Response_no_r0)):
            all_max.append(np.nanmax(Response_no_r0))
    return max(all_max) if all_max else 1.0

o2_vmax_actual = calculate_global_range(df_o2_valid)
contractility_vmax_actual = calculate_global_range(df_contractility_valid)

# Capped values for color scaling
o2_vmax = 35
contractility_vmax = 0.04
o2_zmax = o2_vmax_actual
contractility_zmax = contractility_vmax_actual

print(f"O2: cap={o2_vmax}, actual_max={o2_vmax_actual:.2f}")
print(f"Contractility: cap={contractility_vmax}, actual_max={contractility_vmax_actual:.4f}")

# Extended colormaps with display max beyond actual max
n_colors = 256
turbo_red = plt.cm.turbo(1.0)

# O2: display 0-100, turbo colors 0-50, red 50-100
o2_display_max = 100
o2_color_cap = o2_vmax_actual  # ~50, where red starts
cap_fraction_o2 = o2_color_cap / o2_display_max
n_cap_o2 = int(n_colors * cap_fraction_o2)
colors_o2 = np.vstack([
    plt.cm.turbo(np.linspace(0, 1, n_cap_o2)),
    np.tile(turbo_red, (n_colors - n_cap_o2, 1))
])
o2_cmap_extended = LinearSegmentedColormap.from_list('o2_extended', colors_o2)

# Contractility: display 0-0.10, turbo colors 0-0.07, red 0.07-0.10
contractility_display_max = 0.10
contractility_color_cap = contractility_vmax_actual  # ~0.069, where red starts
cap_fraction_con = contractility_color_cap / contractility_display_max
n_cap_con = int(n_colors * cap_fraction_con)
colors_con = np.vstack([
    plt.cm.turbo(np.linspace(0, 1, n_cap_con)),
    np.tile(turbo_red, (n_colors - n_cap_con, 1))
])
con_cmap_extended = LinearSegmentedColormap.from_list('con_extended', colors_con)

print(f"O2 colorbar: 0-{o2_display_max}, red above {o2_color_cap:.1f}")
print(f"Contractility colorbar: 0-{contractility_display_max}, red above {contractility_color_cap:.4f}")


def create_grid(df, response_type, vmax, zmax, cmap_extended, output_path, display_max,
                n_cols=5, with_titles=True):
    """Create a combined grid with colorbar.

    Args:
        n_cols: number of columns in the grid (rows calculated from drug count)
        with_titles: whether to show drug name titles on each subplot
    """
    sorted_drugs = df.sort_values('Drug')
    n_drugs = len(sorted_drugs)
    n_rows = int(np.ceil(n_drugs / n_cols))
    print(f"\nCreating {response_type} {n_rows}x{n_cols} grid ({n_drugs} drugs)...")

    dose_ratio = np.linspace(0, 2, 60)
    time = np.linspace(0, 96, 60)
    T, Dr = np.meshgrid(time, dose_ratio)

    # Scale contractility ×100 for readability (display as ·10⁻²)
    scale = 100 if response_type == 'Contractility' else 1
    vmax_s = vmax * scale
    zmax_s = zmax * scale
    display_max_s = display_max * scale

    # Figure size scales with rows
    fig_h = 14 * n_rows / 5
    fig = plt.figure(figsize=(16, fig_h))

    # Grid area (leaving room for colorbar on right)
    grid_left = 0.0
    grid_right = 0.87
    grid_bottom = 0.0
    grid_top = 1.0

    cell_w = (grid_right - grid_left) / n_cols
    cell_h = (grid_top - grid_bottom) / n_rows

    # Overflow to eat 3D internal margins
    overflow_right = 0.04
    overflow_top = 0.03
    overflow_bottom = 0.04

    norm = Normalize(vmin=0, vmax=vmax_s)

    for i, (idx, row_data) in enumerate(sorted_drugs.iterrows()):
        if i >= n_drugs:
            break

        grid_row = i // n_cols
        grid_col = i % n_cols

        drug_name = str(row_data['Drug'])
        R0 = row_data['R0']
        Emax = row_data['Emax']
        kappa = row_data['kappa']
        n_param = row_data['n']
        m = row_data['m']
        tau = row_data['tau']
        k_elim = row_data['k_elim']

        Response = pkpd_elimination_response(Dr, T, R0, Emax, kappa, n_param, m, tau, k_elim)
        Response = (Response - R0) * scale
        Response = np.clip(Response, 0, zmax_s)

        # Cell position (row 0 = top)
        x0 = grid_left + grid_col * cell_w
        y0 = grid_top - (grid_row + 1) * cell_h
        rect = [x0, y0 - overflow_bottom, cell_w + overflow_right, cell_h + overflow_top + overflow_bottom]

        ax = fig.add_axes(rect, projection='3d')

        surf = ax.plot_surface(T, Dr, Response, cmap='turbo', norm=norm, alpha=0.9,
                              linewidth=0, antialiased=True, edgecolor='none')

        ax.view_init(elev=25, azim=-158)
        ax.set_xlim(0, 96)
        ax.set_ylim(0, 2)
        ax.set_zlim(0, zmax_s)

        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.grid(True, alpha=0.2)

        is_left = (grid_col == 0)
        is_right = (grid_col == n_cols - 1)
        is_bottom = (grid_row == n_rows - 1)

        # X-axis (Time) - only RIGHT column, label on separate line from ticks
        if is_right:
            ax.set_xlabel('Time (h)', fontsize=12, labelpad=10)
            ax.tick_params(axis='x', labelsize=10, pad=2)
        else:
            ax.set_xlabel('')
            ax.set_xticklabels([])

        # Y-axis (Dose) - only BOTTOM row, label on separate line from ticks
        if is_bottom:
            ax.set_ylabel('Dose Ratio', fontsize=12, labelpad=10)
            ax.tick_params(axis='y', labelsize=10, pad=2)
        else:
            ax.set_ylabel('')
            ax.set_yticklabels([])

        # Z-axis - only LEFT column
        if is_left:
            ax.zaxis.set_rotate_label(False)
            if response_type == 'O2':
                z_label = r'$O_2$ (%)'
            else:
                z_label = r'Contractility ($\cdot 10^{-2}$)'
            ax.set_zlabel(z_label, fontsize=12, labelpad=1, rotation=90)
            ax.tick_params(axis='z', labelsize=10, pad=0)
        else:
            ax.set_zticklabels([])

        # Drug name title
        if with_titles:
            ax.set_title(drug_name, fontsize=16, pad=-14, fontweight='bold')

    # Colorbar
    cbar_ax = fig.add_axes([0.91, 0.15, 0.02, 0.7])

    norm_cbar = Normalize(vmin=0, vmax=display_max_s)
    sm = ScalarMappable(norm=norm_cbar, cmap=cmap_extended)
    sm.set_array([])

    cbar = plt.colorbar(sm, cax=cbar_ax, orientation='vertical')
    cbar.ax.tick_params(labelsize=12)

    if response_type == 'O2':
        cbar.set_label(r'$O_2$ Response', fontsize=14, labelpad=10)
        ticks = np.arange(0, int(display_max_s) + 1, 20)
    else:
        cbar.set_label(r'Contractility ($\cdot 10^{-2}$)', fontsize=14, labelpad=10)
        ticks = np.arange(0, display_max_s + 0.1, 2)
    cbar.set_ticks(ticks)

    fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Saved: {output_path}")


# Generate both 5x5 grids (all 25 drugs)
create_grid(df_o2_valid, 'O2', o2_vmax, o2_zmax, o2_cmap_extended,
            OUTPUT_DIR / 'O2_5x5_Combined.png', o2_display_max)

create_grid(df_contractility_valid, 'Contractility', contractility_vmax,
            contractility_zmax, con_cmap_extended,
            OUTPUT_DIR / 'Contractility_5x5_Combined.png', contractility_display_max)

# Generate arrhythmia-only grids (no titles)
df_o2_arr = df_o2_valid[df_o2_valid['Arrhythmia'].astype(str).str.lower() == 'true']
df_con_arr = df_contractility_valid[df_contractility_valid['Arrhythmia'].astype(str).str.lower() == 'true']

create_grid(df_o2_arr, 'O2', o2_vmax, o2_zmax, o2_cmap_extended,
            OUTPUT_DIR / 'O2_Arrhythmia_Combined.png', o2_display_max,
            with_titles=False)

create_grid(df_con_arr, 'Contractility', contractility_vmax,
            contractility_zmax, con_cmap_extended,
            OUTPUT_DIR / 'Contractility_Arrhythmia_Combined.png', contractility_display_max,
            with_titles=False)

print("\nDone! All grids saved.")
