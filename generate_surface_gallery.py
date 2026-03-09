"""
Generate 3D surface plot gallery for all 12 equations.
Each plot uses real fitted O2 coefficients from the best-looking drug.
Output: Surface_1.png through Surface_12.png
"""

import sys
import os
import inspect
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# --- Setup paths ---
PROJECT_ROOT = Path(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO')
EXCEL_PATH = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures' / 'Fig_3b_candidates'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Import equation functions
sys.path.insert(0, str(PROJECT_ROOT / 'Picking Equations' / 'equation_fitting'))
from equations import EQUATION_FUNCTIONS

# --- Equation ordering (1-12) ---
EQUATION_ORDER = [
    'dual_exponential',       # Surface 1
    'bivariate_gaussian',     # Surface 2
    'gaussian_hill_hybrid',   # Surface 3
    'modified_hill_hormesis', # Surface 4
    'gaussian_ridge',         # Surface 5
    'adaptive_response',      # Surface 6
    'biphasic_response',      # Surface 7
    'cumulative_exposure',    # Surface 8
    'recovery_model',         # Surface 9
    'modified_hill_simple',   # Surface 10
    'pkpd_elimination',       # Surface 11
    'hormesis_v0',            # Surface 12
]

# Candidate drugs to try (known to produce interesting surfaces)
CANDIDATE_DRUGS = [
    'Daunorubicin', 'Isoproterenol', 'Amiodarone', 'Sunitinib',
    'Doxorubicin', 'Epirubicin', 'Panobinostat', 'Bortezomib',
    'Vandetanib', 'Cobimetinib'
]


def get_param_names(eq_name):
    """Get parameter names (excluding X) for a given equation."""
    func = EQUATION_FUNCTIONS[eq_name]
    sig = inspect.signature(func)
    return [p for p in sig.parameters if p != 'X']


def load_params(eq_name, drug_name, response_type='O2'):
    """
    Load coefficients for a specific drug from the equation's sheet.
    response_type: 'O2' uses '.1' suffix columns, 'Contractility' uses base columns.
    Returns list of parameter values in function order.
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name=eq_name, header=1)
    df.columns = df.columns.str.strip()

    row = df[df['Drug'] == drug_name]
    if row.empty:
        return None

    row = row.iloc[0]
    param_names = get_param_names(eq_name)

    suffix = '.1' if response_type == 'O2' else ''
    values = []
    for p in param_names:
        col = p + suffix if suffix else p
        if col in df.columns:
            val = row[col]
        else:
            print(f"  WARNING: Column '{col}' not found for {eq_name}")
            return None

        if pd.isna(val) or not np.isfinite(val):
            return None
        values.append(float(val))

    return values


def compute_surface(eq_name, params, time, dose_ratio):
    """Compute the response surface for given equation and parameters."""
    func = EQUATION_FUNCTIONS[eq_name]
    T, Dr = np.meshgrid(time, dose_ratio)
    X = [Dr, T]  # X = [C_norm, time]

    try:
        Z = func(X, *params)
        # Handle any NaN/Inf
        Z = np.nan_to_num(Z, nan=0.0, posinf=0.0, neginf=0.0)
        return T, Dr, Z
    except Exception as e:
        print(f"  Error computing surface for {eq_name}: {e}")
        return None, None, None


def z_range(Z):
    """Compute the range (max - min) of a surface, ignoring issues."""
    if Z is None:
        return 0
    finite = Z[np.isfinite(Z)]
    if len(finite) == 0:
        return 0
    return float(np.ptp(finite))


def get_all_drugs(eq_name):
    """Get list of all drug names from a sheet."""
    df = pd.read_excel(EXCEL_PATH, sheet_name=eq_name, header=1)
    df.columns = df.columns.str.strip()
    return df['Drug'].tolist()


def pick_best_drug(eq_name, time, dose_ratio):
    """
    Try candidate drugs and pick the one producing the largest Z range
    (most visually interesting surface). First tries O2, then falls back
    to Contractility if all O2 surfaces are flat.
    """
    MIN_Z_RANGE = 0.5  # Threshold below which a surface is considered flat

    best_drug = None
    best_range = -1
    best_params = None
    best_Z = None
    best_T = None
    best_Dr = None
    best_response = 'O2'

    all_drugs = get_all_drugs(eq_name)
    # Prioritize candidate drugs, then try all others
    ordered_drugs = CANDIDATE_DRUGS + [d for d in all_drugs if d not in CANDIDATE_DRUGS]

    for response_type in ['O2', 'Contractility']:
        for drug in ordered_drugs:
            params = load_params(eq_name, drug, response_type)
            if params is None:
                continue

            T, Dr, Z = compute_surface(eq_name, params, time, dose_ratio)
            if Z is None:
                continue

            zr = z_range(Z)
            if zr > best_range:
                best_range = zr
                best_drug = drug
                best_params = params
                best_T = T
                best_Dr = Dr
                best_Z = Z
                best_response = response_type

        # If we found a good O2 surface, use it; otherwise try Contractility
        if best_range >= MIN_Z_RANGE:
            break

    if best_response != 'O2':
        print(f"  Note: Using {best_response} (O2 surfaces were flat)")

    return best_drug, best_params, best_T, best_Dr, best_Z, best_range


def plot_surface(T, Dr, Z, surface_num, drug_name, eq_name, output_path):
    """Generate and save a single 3D surface plot."""
    fig = plt.figure(figsize=(6, 5))
    ax = fig.add_subplot(111, projection='3d')

    # Plot surface with turbo colormap
    surf = ax.plot_surface(
        T, Dr, Z,
        cmap='turbo',
        edgecolor='none',
        alpha=0.95,
        rstride=2,
        cstride=2,
        antialiased=True
    )

    # View angle matching existing plots
    ax.view_init(elev=25, azim=-158)

    # Labels
    ax.set_xlabel('Time (h)', fontsize=10, labelpad=8)
    ax.set_ylabel('Dose Ratio', fontsize=10, labelpad=8)
    ax.set_zlabel('Response', fontsize=10, labelpad=8)

    # Title
    ax.set_title(f'Surface {surface_num}', fontsize=14, fontweight='bold', pad=10)

    # Axis ranges
    ax.set_xlim(0, 96)
    ax.set_ylim(0, 2)

    # Tick size
    ax.tick_params(axis='both', which='major', labelsize=8)

    # Add colorbar
    cbar = fig.colorbar(surf, ax=ax, shrink=0.6, aspect=15, pad=0.1)
    cbar.ax.tick_params(labelsize=8)

    plt.tight_layout()
    fig.savefig(output_path, dpi=600, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"  Saved: {output_path.name} ({drug_name}, Z range={z_range(Z):.4f})")


def main():
    print("=" * 70)
    print("Generating 3D Surface Gallery for All 12 Equations")
    print("=" * 70)
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Create meshgrid
    time = np.linspace(0, 96, 100)
    dose_ratio = np.linspace(0, 2, 100)

    results = []

    for idx, eq_name in enumerate(EQUATION_ORDER, start=1):
        print(f"[{idx}/12] {eq_name}...")

        drug, params, T, Dr, Z, zr = pick_best_drug(eq_name, time, dose_ratio)

        if drug is None:
            print(f"  SKIPPED: Could not find any valid parameters for {eq_name}")
            continue

        output_path = OUTPUT_DIR / f'Surface_{idx}.png'
        plot_surface(T, Dr, Z, idx, drug, eq_name, output_path)
        results.append((idx, eq_name, drug, zr))

    print()
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    for idx, eq_name, drug, zr in results:
        print(f"  Surface {idx:2d}: {eq_name:30s} | Drug: {drug:15s} | Z range: {zr:.4f}")
    print(f"\nTotal surfaces generated: {len(results)}/12")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
