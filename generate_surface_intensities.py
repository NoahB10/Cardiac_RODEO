"""
Generate Surface Intensity Variants for Figure 3b Candidates

Produces 5 intensity variants for each of Surfaces 1, 5, 11, and 12 (20 plots total).
Each variant uses a different drug's fitted O2 coefficients, selected to show
a spread from mild to intense response (evenly spaced across Z-range).

Equations:
  Surface 1  = dual_exponential
  Surface 5  = gaussian_ridge
  Surface 11 = pkpd_elimination
  Surface 12 = hormesis_v0
"""

import sys
import inspect
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Suppress runtime warnings from exp overflow etc.
warnings.filterwarnings('ignore', category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Setup paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(r'C:\Users\NoahB\Documents\HebrewU Bioengineering\Cardiac_RODEO')
EXCEL_PATH = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
OUTPUT_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures' / 'Fig_3b_candidates' / 'intensities'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Import equation functions
sys.path.insert(0, str(PROJECT_ROOT / 'Picking Equations' / 'equation_fitting'))
from equations import EQUATION_FUNCTIONS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SURFACE_CONFIG = {
    1:  {'name': 'dual_exponential',  'sheet': 'dual_exponential'},
    5:  {'name': 'gaussian_ridge',    'sheet': 'gaussian_ridge'},
    11: {'name': 'pkpd_elimination',  'sheet': 'pkpd_elimination'},
    12: {'name': 'hormesis_v0',       'sheet': 'hormesis_v0'},
}

# Grid for evaluation
N_GRID = 100
time = np.linspace(0, 96, N_GRID)
dose_ratio = np.linspace(0, 2, N_GRID)
T, Dr = np.meshgrid(time, dose_ratio)

# Percentile indices for drug selection (5 drugs spread across intensity range)
TARGET_PERCENTILES = [10, 30, 50, 70, 90]

EXCLUDED_DRUGS = {'DMSO', 'Troglitazone', 'Troglitarazine'}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_o2_params(func, row):
    """Extract O2 parameters from a DataFrame row for a given equation function.

    Uses inspect.signature to get parameter names, then looks for .1 suffix columns.
    """
    sig = inspect.signature(func)
    param_names = list(sig.parameters.keys())[1:]  # skip X
    values = []
    for p in param_names:
        col = f'{p}.1'
        if col in row.index:
            val = row[col]
        elif p in row.index:
            val = row[p]
        else:
            raise KeyError(f"Column '{col}' not found for parameter '{p}'")
        values.append(float(val))
    return values


def compute_surface(func, params):
    """Compute Z surface on the meshgrid, handling NaN/Inf."""
    try:
        X = [Dr, T]
        Z = func(X, *params)
        Z = np.array(Z, dtype=float)
        # Replace NaN/Inf with 0
        Z = np.where(np.isfinite(Z), Z, 0.0)
        # Clip extreme values to prevent visual artifacts
        Z = np.clip(Z, -500, 500)
        return Z
    except Exception as e:
        print(f"    Error computing surface: {e}")
        return None


def compute_z_range(Z):
    """Compute the Z range (max - min) of a surface."""
    if Z is None:
        return 0.0
    return float(np.max(Z) - np.min(Z))


def select_drugs_by_intensity(drug_zranges, n_select=5):
    """Select n drugs evenly spaced across the Z-range distribution.

    Filters out flat surfaces (Z range < 0.1) and NaN/Inf.
    Returns list of (drug_name, z_range) sorted from least to most intense.
    """
    # Filter valid drugs
    valid = [(drug, zr) for drug, zr in drug_zranges if zr >= 0.1 and np.isfinite(zr)]

    if len(valid) == 0:
        print("    WARNING: No valid drugs found!")
        return []

    # Sort by Z range (ascending)
    valid.sort(key=lambda x: x[1])

    if len(valid) <= n_select:
        return valid

    # Pick at target percentiles
    selected = []
    for pct in TARGET_PERCENTILES:
        idx = int(round((pct / 100.0) * (len(valid) - 1)))
        idx = max(0, min(idx, len(valid) - 1))
        candidate = valid[idx]
        # Avoid duplicates: if already selected, try nearby indices
        if candidate not in selected:
            selected.append(candidate)
        else:
            # Search outward from idx for an unused drug
            for offset in range(1, len(valid)):
                for direction in [1, -1]:
                    alt_idx = idx + offset * direction
                    if 0 <= alt_idx < len(valid) and valid[alt_idx] not in selected:
                        selected.append(valid[alt_idx])
                        break
                if len(selected) > len([s for s in selected if s == candidate]):
                    break

    # Sort final selection by Z range (ascending = v1 mildest, v5 most intense)
    selected.sort(key=lambda x: x[1])
    return selected[:n_select]


def plot_surface(Z, surface_num, drug_name, variant_num, output_dir):
    """Create and save a 3D surface plot."""
    fig = plt.figure(figsize=(6, 5))
    ax = fig.add_subplot(111, projection='3d')

    surf = ax.plot_surface(T, Dr, Z, cmap='turbo', edgecolor='none',
                           antialiased=True, rcount=100, ccount=100)

    ax.set_xlabel('Time (hours)', fontsize=10, labelpad=8)
    ax.set_ylabel('Dose Ratio (C₀/Cmax)', fontsize=10, labelpad=8)
    ax.set_zlabel('Response (O₂)', fontsize=10, labelpad=8)
    ax.set_title(f'Surface {surface_num} - {drug_name}', fontsize=12, fontweight='bold')
    ax.view_init(elev=25, azim=-158)

    ax.set_xlim(0, 96)
    ax.set_ylim(0, 2)

    fig.colorbar(surf, shrink=0.5, aspect=15, pad=0.1)

    filename = f'Surface_{surface_num}_v{variant_num}.png'
    filepath = output_dir / filename
    fig.savefig(filepath, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Generating Surface Intensity Variants")
    print("=" * 70)

    # Summary tracking
    summary_rows = []

    for surface_num, config in SURFACE_CONFIG.items():
        eq_name = config['name']
        sheet_name = config['sheet']
        func = EQUATION_FUNCTIONS[eq_name]

        print(f"\n{'-' * 60}")
        print(f"Surface {surface_num}: {eq_name} (sheet: {sheet_name})")
        print(f"{'-' * 60}")

        # Load data
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=1)
        df.columns = df.columns.str.strip()

        # Filter excluded drugs
        df = df[~df['Drug'].isin(EXCLUDED_DRUGS)].copy()

        # Compute Z range for each drug
        print(f"  Computing Z ranges for {len(df)} drugs...")
        drug_zranges = []
        drug_surfaces = {}

        for _, row in df.iterrows():
            drug = row['Drug']
            try:
                params = get_o2_params(func, row)
                # Check for NaN in params
                if any(not np.isfinite(p) for p in params):
                    print(f"    {drug}: skipped (NaN/Inf in parameters)")
                    continue
                Z = compute_surface(func, params)
                if Z is not None:
                    zr = compute_z_range(Z)
                    drug_zranges.append((drug, zr))
                    drug_surfaces[drug] = Z
                    print(f"    {drug}: Z range = {zr:.4f}")
                else:
                    print(f"    {drug}: skipped (computation failed)")
            except Exception as e:
                print(f"    {drug}: skipped ({e})")

        # Select 5 drugs at evenly spaced intensities
        selected = select_drugs_by_intensity(drug_zranges, n_select=5)

        if len(selected) == 0:
            print(f"  ERROR: No valid drugs for Surface {surface_num}!")
            continue

        print(f"\n  Selected {len(selected)} drugs (v1=mildest, v{len(selected)}=most intense):")
        for i, (drug, zr) in enumerate(selected, 1):
            print(f"    v{i}: {drug} (Z range = {zr:.4f})")

        # Generate plots
        for variant_num, (drug, zr) in enumerate(selected, 1):
            Z = drug_surfaces[drug]
            filepath = plot_surface(Z, surface_num, drug, variant_num, OUTPUT_DIR)
            print(f"  Saved: {filepath.name}")
            summary_rows.append({
                'Surface': surface_num,
                'Equation': eq_name,
                'Variant': f'v{variant_num}',
                'Drug': drug,
                'Z_Range': zr,
                'File': f'Surface_{surface_num}_v{variant_num}.png'
            })

    # Print summary table
    print("\n" + "=" * 70)
    print("SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Surface':<10} {'Equation':<22} {'Variant':<8} {'Drug':<18} {'Z Range':>10}")
    print("-" * 70)
    for row in summary_rows:
        print(f"{row['Surface']:<10} {row['Equation']:<22} {row['Variant']:<8} "
              f"{row['Drug']:<18} {row['Z_Range']:>10.4f}")

    print(f"\nTotal plots generated: {len(summary_rows)}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Save summary as CSV
    summary_df = pd.DataFrame(summary_rows)
    summary_path = OUTPUT_DIR / 'intensity_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"Summary saved: {summary_path}")


if __name__ == '__main__':
    main()
