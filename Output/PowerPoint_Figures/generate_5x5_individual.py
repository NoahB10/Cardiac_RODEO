"""
Generate individual 5x5 grid plots at 600 DPI for PowerPoint placement.
Each drug gets its own high-quality image, then assembled in PowerPoint.

This script is located in Output/PowerPoint_Figures/ for figure management.
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
plt.rcParams['font.size'] = 14

# Find project root - this script is in Output/PowerPoint_Figures/
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Go up from PowerPoint_Figures -> Output -> Project Root
FIGURE_DIR = SCRIPT_DIR  # PowerPoint_Figures folder

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


def load_data():
    """Load and prepare coefficient data."""
    print("Loading data...")
    df_raw = pd.read_excel(EXCEL_PATH, sheet_name='pkpd_elimination', header=1)
    df_raw.columns = df_raw.columns.str.strip()
    df_raw = df_raw[df_raw['Drug'].notna() & (df_raw['Drug'].astype(str).str.strip() != '')]
    return df_raw


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


def filter_valid(df):
    valid_mask = df[param_names].notna().all(axis=1) & df[param_names].apply(lambda x: np.isfinite(x)).all(axis=1)
    return df[valid_mask].copy()


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


def generate_individual_plots(df, response_type, vmax, zmax, figure_dir, fig_num,
                              with_titles=True):
    """Generate individual high-DPI plots for each drug."""
    suffix = "" if with_titles else "_NoTitles"
    print(f"\nGenerating {response_type}{suffix} individual plots at 600 DPI...")

    sorted_drugs = df.sort_values('Drug').head(25)

    dose_ratio = np.linspace(0, 2, 60)
    time = np.linspace(0, 96, 60)
    T, Dr = np.meshgrid(time, dose_ratio)

    # Scale contractility ×100 for readability (display as ×10⁻²)
    scale = 100 if response_type == 'Contractility' else 1
    vmax = vmax * scale
    zmax = zmax * scale

    norm = Normalize(vmin=0, vmax=vmax)

    # Save to PowerPoint_Figures/Fig_X folder
    subdir_name = f"{response_type}_5x5_Individual{suffix}"
    output_subdir = figure_dir / f"Fig_{fig_num}" / subdir_name
    output_subdir.mkdir(parents=True, exist_ok=True)

    # Font sizes
    TITLE_SIZE = 28
    LABEL_SIZE = 24
    TICK_SIZE = 20

    from matplotlib.ticker import FuncFormatter, NullFormatter
    from PIL import Image as PILImage

    drug_list = []

    for i, (idx, row_data) in enumerate(sorted_drugs.iterrows()):
        if i >= 25:
            break

        grid_row = i // 5
        grid_col = i % 5

        drug_name = str(row_data['Drug'])
        R0 = row_data['R0']
        Emax = row_data['Emax']
        kappa = row_data['kappa']
        n = row_data['n']
        m = row_data['m']
        tau = row_data['tau']
        k_elim = row_data['k_elim']

        Response = pkpd_elimination_response(Dr, T, R0, Emax, kappa, n, m, tau, k_elim)
        Response = (Response - R0) * scale
        Response = np.clip(Response, 0, zmax)

        # Create individual figure - slightly wider for Z-axis label room
        fig = plt.figure(figsize=(7, 7.5))
        ax = fig.add_subplot(111, projection='3d', computed_zorder=False)

        # Plot surface
        surf = ax.plot_surface(T, Dr, Response, cmap='turbo', norm=norm, alpha=0.9,
                              linewidth=0, antialiased=True, edgecolor='none')

        # Same view angle as other plots
        ax.view_init(elev=25, azim=-158)
        ax.set_xlim(0, 96)
        ax.set_ylim(0, 2)
        ax.set_zlim(0, zmax)

        # Make panes transparent
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.grid(True, alpha=0.2)

        # Determine position for axis visibility
        is_left = (grid_col == 0)
        is_right = (grid_col == 4)
        is_bottom = (grid_row == 4)

        # Custom formatter - use enough decimal places for small values
        def format_tick(x, pos):
            if x == int(x):
                return f'{int(x)}'
            elif abs(x) < 0.1:
                return f'{x:.2f}'.rstrip('0').rstrip('.')
            else:
                return f'{x:.1f}'.rstrip('0').rstrip('.')

        if not with_titles:
            # No-titles version: strip ALL axis labels, ticks, and text
            ax.set_xlabel('')
            ax.set_ylabel('')
            ax.set_zlabel('')
            ax.xaxis.set_major_formatter(NullFormatter())
            ax.yaxis.set_major_formatter(NullFormatter())
            ax.zaxis.set_major_formatter(NullFormatter())
        else:
            # With-titles version: edge plots get labels/ticks
            # X-axis (Time) - only RIGHT column shows label and tick labels
            if is_right:
                ax.set_xlabel('Time (h)', fontsize=LABEL_SIZE, labelpad=6)
                ax.tick_params(axis='x', labelsize=TICK_SIZE, pad=0)
                ax.xaxis.set_major_formatter(FuncFormatter(format_tick))
            else:
                ax.set_xlabel('')
                ax.xaxis.set_major_formatter(NullFormatter())

            # Y-axis (Dose Ratio) - only BOTTOM row shows label and tick labels
            if is_bottom:
                ax.set_ylabel('Dose Ratio', fontsize=LABEL_SIZE, labelpad=6)
                ax.tick_params(axis='y', labelsize=TICK_SIZE, pad=0)
                ax.yaxis.set_major_formatter(FuncFormatter(format_tick))
            else:
                ax.set_ylabel('')
                ax.yaxis.set_major_formatter(NullFormatter())

            # Z-axis - only LEFT column shows label and tick labels
            if is_left:
                z_label = r'$O_2$ (%)' if response_type == 'O2' else r'Contractility ($\cdot 10^{-2}$)'
                ax.text2D(-0.02, 0.5, z_label, transform=ax.transAxes,
                          fontsize=LABEL_SIZE, rotation=90, va='center', ha='right')
                ax.tick_params(axis='z', labelsize=TICK_SIZE, pad=0)
                ax.zaxis.set_major_formatter(FuncFormatter(format_tick))
            else:
                ax.set_zlabel('')
                ax.zaxis.set_major_formatter(NullFormatter())

            # Drug name title
            ax.text2D(0.5, 0.97, drug_name, transform=ax.transAxes,
                      fontsize=TITLE_SIZE, fontweight='bold', ha='center', va='top')

        # Adjust subplot: keep left margin for Z-axis, trim right/top/bottom
        plt.subplots_adjust(left=0.25, right=0.98, top=0.96, bottom=0.02)

        # Save at 600 DPI with minimal padding
        safe_name = drug_name.replace(' ', '_').replace('/', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
        filename = f"{i:02d}_{safe_name}.png"
        filepath = output_subdir / filename

        fig.savefig(filepath, dpi=600, bbox_inches='tight',
                    facecolor='none', edgecolor='none', transparent=True, pad_inches=0.02)

        # Add extra left padding only (for Z-axis label + tick breathing room)
        img = PILImage.open(filepath).convert('RGBA')
        left_extra = int(0.08 * 600)  # 0.08" at 600 DPI
        new_img = PILImage.new('RGBA', (img.width + left_extra, img.height), (0, 0, 0, 0))
        new_img.paste(img, (left_extra, 0))
        new_img.save(filepath, dpi=(600, 600))
        plt.close(fig)

        drug_list.append({
            'index': i,
            'row': grid_row,
            'col': grid_col,
            'drug': drug_name,
            'filename': filename,
            'filepath': str(filepath)
        })

        if (i + 1) % 5 == 0:
            print(f"  Saved {i + 1}/25")

    print(f"Individual plots saved to: {output_subdir}")
    return drug_list, output_subdir


def generate_colorbar(response_type, display_max, color_cap, output_dir):
    """Generate standalone colorbar at 600 DPI with 0.57" width (bar + left label)."""
    print(f"\nGenerating {response_type} colorbar...")

    # Scale contractility ×100 for readability (display as ×10⁻²)
    scale = 100 if response_type == 'Contractility' else 1
    display_max = display_max * scale
    color_cap = color_cap * scale

    n_colors = 256
    turbo_red = plt.cm.turbo(1.0)

    cap_fraction = color_cap / display_max
    n_cap = int(n_colors * cap_fraction)
    colors = np.vstack([
        plt.cm.turbo(np.linspace(0, 1, n_cap)),
        np.tile(turbo_red, (n_colors - n_cap, 1))
    ])
    cmap_extended = LinearSegmentedColormap.from_list('extended', colors)

    # Colorbar dimensions: 0.57" total (0.42" bar + 0.15" label space)
    fig_width = 0.57
    fig_height = 5.5

    # Position bar to the right, leaving white space on left for label
    axes_left = 0.26
    axes_bottom = 0.08
    axes_width = 0.30
    axes_height = 0.84

    fig = plt.figure(figsize=(fig_width, fig_height))
    ax = fig.add_axes([axes_left, axes_bottom, axes_width, axes_height])

    norm = Normalize(vmin=0, vmax=display_max)
    sm = ScalarMappable(norm=norm, cmap=cmap_extended)
    sm.set_array([])

    cbar = plt.colorbar(sm, cax=ax, orientation='vertical')
    cbar.ax.tick_params(labelsize=7, pad=1)
    cbar.ax.yaxis.set_ticks_position('right')
    cbar.ax.yaxis.set_label_position('right')

    # Rotate tick labels to vertical
    for label in cbar.ax.get_yticklabels():
        label.set_rotation(90)
        label.set_va('center')

    # Format tick labels
    from matplotlib.ticker import FuncFormatter
    def format_tick(x, pos):
        if x == int(x):
            return f'{int(x)}'
        elif x * 100 == int(x * 100):
            return f'{x:.2f}'.rstrip('0').rstrip('.')
        else:
            return f'{x:.2f}'

    cbar.ax.yaxis.set_major_formatter(FuncFormatter(format_tick))

    # Set ticks and left label
    if response_type == 'O2':
        ticks = np.arange(0, int(display_max) + 1, 20)
        left_label = 'O₂'
    else:
        ticks = np.arange(0, display_max + 0.1, 2)
        left_label = r'Contr. ($\cdot 10^{-2}$)'
    cbar.set_ticks(ticks)

    # Add vertical label in the white space on the LEFT side
    fig.text(0.12, 0.50, left_label, ha='center', va='center', fontsize=7,
             fontweight='bold', rotation=90)

    # Save with exact dimensions
    filepath = output_dir / f"{response_type}_colorbar_600dpi.png"
    fig.savefig(filepath, dpi=600,
                facecolor='white', edgecolor='none', transparent=False)
    plt.close(fig)

    print(f"Colorbar saved to: {filepath}")
    return filepath


def main():
    """Main function to generate all plots."""
    # Load data
    df_raw = load_data()

    df_contractility = extract_coefficients(df_raw, 'Contractility')
    df_o2 = extract_coefficients(df_raw, 'O2')

    df_contractility_valid = filter_valid(df_contractility)
    df_o2_valid = filter_valid(df_o2)

    # Calculate global ranges
    o2_vmax_actual = calculate_global_range(df_o2_valid)
    contractility_vmax_actual = calculate_global_range(df_contractility_valid)

    o2_vmax = 35
    contractility_vmax = 0.04
    o2_zmax = o2_vmax_actual
    contractility_zmax = contractility_vmax_actual

    print(f"O2: cap={o2_vmax}, actual_max={o2_vmax_actual:.2f}")
    print(f"Contractility: cap={contractility_vmax}, actual_max={contractility_vmax_actual:.4f}")

    # Generate plots with titles
    o2_drugs, o2_dir = generate_individual_plots(df_o2_valid, 'O2', o2_vmax, o2_zmax, FIGURE_DIR, 4)
    con_drugs, con_dir = generate_individual_plots(df_contractility_valid, 'Contractility',
                                                    contractility_vmax, contractility_zmax, FIGURE_DIR, 5)

    # Generate plots without titles
    generate_individual_plots(df_o2_valid, 'O2', o2_vmax, o2_zmax, FIGURE_DIR, 4,
                              with_titles=False)
    generate_individual_plots(df_contractility_valid, 'Contractility',
                              contractility_vmax, contractility_zmax, FIGURE_DIR, 5,
                              with_titles=False)

    # Generate colorbars
    o2_cbar_dir = FIGURE_DIR / "Fig_4"
    o2_cbar_dir.mkdir(parents=True, exist_ok=True)
    o2_cbar = generate_colorbar('O2', 100, o2_vmax_actual, o2_cbar_dir)

    con_cbar_dir = FIGURE_DIR / "Fig_5"
    con_cbar_dir.mkdir(parents=True, exist_ok=True)
    con_cbar = generate_colorbar('Contractility', 0.10, contractility_vmax_actual, con_cbar_dir)

    print("\n" + "="*60)
    print("DONE! Individual plots generated at 600 DPI")
    print("="*60)
    print(f"\nO2 plots: {o2_dir}")
    print(f"Contractility plots: {con_dir}")
    print(f"\nO2 colorbar: {o2_cbar}")
    print(f"Contractility colorbar: {con_cbar}")
    print("\nNow run build_5x5_slides.py to assemble into PowerPoint.")


if __name__ == '__main__':
    main()
