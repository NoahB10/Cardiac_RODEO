"""Generate individual TC50 dose-response plots for Epirubicin at each timepoint.

Uses the same approach as the paper figure (Fig 2h):
  - Average replicate wells per concentration
  - Min-max normalize to 0-100% O2 consumption
  - 4-parameter logistic sigmoid fit
  - Fixed x-ticks at known concentrations

Usage:
    python generate_tc50_per_timepoint.py          # all timepoints 24h-96h
    python generate_tc50_per_timepoint.py 32 64     # specific timepoints
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# --- Path discovery ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR
while PROJECT_ROOT != PROJECT_ROOT.parent:
    if (PROJECT_ROOT / 'EQN_Coefficients').exists():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent

RAW_O2_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'DrugScreen19.11.25_compiled_O2_mean.xlsx'
OUTPUT_DIR = SCRIPT_DIR  # same folder as this script

DRUG = 'Epirubicin'
SHEET = 'Epirubicin O2_mean'
DPI = 300

# Per-timepoint well exclusions: {timepoint_hour: [well_indices_to_exclude]}
EXCLUDE_WELLS = {
    40: [0, 4, 10, 11, 13, 15],
}


def logistic_4pl(xlog, bottom, top, logEC50, slope):
    return bottom + (top - bottom) / (1 + np.exp((logEC50 - xlog) * slope))


def load_data():
    df = pd.read_excel(RAW_O2_PATH, sheet_name=SHEET, header=None)
    time_points = df.iloc[0, 1:].astype(float).values
    concentrations = df.iloc[1:, 0].astype(float).values
    o2_matrix = df.iloc[1:, 1:].astype(float).values
    return time_points, concentrations, o2_matrix


def generate_single_tc50(time_points, concentrations, o2_matrix, time_hour,
                         extra_exclude=None, mean_only=False, suffix=''):
    """Generate one TC50 plot at a given timepoint."""
    idx_t = np.argmin(np.abs(time_points - time_hour))
    actual_t = time_points[idx_t]
    o2_at_t = o2_matrix[:, idx_t]

    # Build per-well dataframe (for showing individual points)
    df_wells = pd.DataFrame({
        'Well_idx': range(len(concentrations)),
        'Concentration': concentrations,
        'O2': o2_at_t,
    })
    df_wells = df_wells[df_wells['Concentration'] > 0].copy()

    # Apply well exclusions for this timepoint
    exclude = list(EXCLUDE_WELLS.get(int(actual_t), []))
    if extra_exclude:
        exclude.extend(extra_exclude)
    if exclude:
        df_excluded = df_wells[df_wells['Well_idx'].isin(exclude)]
        df_wells = df_wells[~df_wells['Well_idx'].isin(exclude)]
        print(f"  {int(actual_t)}h: excluded {len(exclude)} wells: {exclude}")
    else:
        df_excluded = pd.DataFrame()

    # Average replicates per concentration
    df_avg = df_wells.groupby('Concentration', as_index=False).mean().sort_values('Concentration')

    # Min-max normalize to 0-100%
    o2_min = df_avg['O2'].min()
    o2_max = df_avg['O2'].max()
    if o2_max - o2_min < 1e-6:
        print(f"  {time_hour}h: no O2 range, skipping")
        return

    df_avg['Consumption'] = (1 - (df_avg['O2'] - o2_min) / (o2_max - o2_min)) * 100
    # Same scaling for individual wells
    df_wells['Consumption'] = (1 - (df_wells['O2'] - o2_min) / (o2_max - o2_min)) * 100

    x_conc = df_avg['Concentration'].values
    y_cons = df_avg['Consumption'].values
    x_log = np.log10(x_conc)

    # Fit 4PL sigmoid
    tc50 = None
    popt = None
    try:
        p0 = [y_cons.min(), y_cons.max(), np.median(x_log), 1.0]
        popt, _ = curve_fit(logistic_4pl, x_log, y_cons, p0=p0, maxfev=20000)
        bottom, top, logEC50, slope = popt
        target = 50.0
        denom = top - bottom
        denom_target = target - bottom
        if slope != 0 and denom != 0 and denom_target != 0:
            ratio = denom / denom_target - 1.0
            if ratio > 0:
                tc50 = 10 ** (logEC50 - (1.0 / slope) * np.log(ratio))
    except Exception as e:
        print(f"  {time_hour}h: sigmoid fit failed: {e}")

    # Plot
    fig, ax = plt.subplots(figsize=(4, 2.8))

    if not mean_only:
        # Excluded wells as red X's
        if not df_excluded.empty:
            df_excluded['Consumption'] = (1 - (df_excluded['O2'] - o2_min) / (o2_max - o2_min)) * 100
            ax.plot(df_excluded['Concentration'], df_excluded['Consumption'].clip(-5, 105),
                    'x', markersize=6, color='red', alpha=0.5, zorder=4, label='Excluded')

        # Individual wells as faint dots
        ax.plot(df_wells['Concentration'], df_wells['Consumption'],
                'o', markersize=4, color='#1f77b4', alpha=0.3, zorder=3)

    # Averaged points
    ax.plot(x_conc, y_cons, 'o', markersize=7, color='#1f77b4', zorder=5,
            label='Mean consumption')

    # Sigmoid fit curve
    if popt is not None:
        x_smooth = np.linspace(x_log.min() - 0.2, x_log.max() + 0.2, 200)
        ax.plot(10 ** x_smooth, logistic_4pl(x_smooth, *popt), '-',
                color='#1f77b4', linewidth=2, label='Sigmoid fit')

    # TC50 markers
    if tc50 is not None and np.isfinite(tc50) and tc50 < x_conc.max() * 2:
        ax.axhline(50, color='grey', linestyle='--', linewidth=1, alpha=0.5)
        ax.axvline(tc50, color='red', linestyle='--', linewidth=1.5)
        ax.text(0.05, 0.08, f'TC50={tc50:.3f} mM', transform=ax.transAxes,
                fontsize=11, fontweight='bold')
    else:
        ax.text(0.05, 0.08, 'TC50 = N/A', transform=ax.transAxes,
                fontsize=11, fontweight='bold', color='grey')

    ax.set_xscale('log')
    ax.set_xlabel('Concentration (mM)', fontsize=12)
    ax.set_ylabel('O2 Consumption (%)', fontsize=12)
    ax.set_title(f'{DRUG} TC50 ({int(actual_t)}h)', fontsize=14, fontweight='bold')
    ax.set_ylim(-5, 105)
    ax.set_xticks(x_conc)
    ax.set_xticklabels([f'{c:.3g}' for c in x_conc], fontsize=9, rotation=45, ha='right')
    ax.tick_params(labelsize=10)
    ax.legend(fontsize=9, loc='upper right')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out_path = OUTPUT_DIR / f'{DRUG}_TC50_{int(actual_t)}h{suffix}.png'
    fig.savefig(out_path, dpi=DPI, bbox_inches='tight', pad_inches=0.05,
                facecolor='white')
    plt.close(fig)

    tc50_str = f'{tc50:.3f}' if (tc50 is not None and np.isfinite(tc50)
                                  and tc50 < x_conc.max() * 2) else 'N/A'
    print(f"  {int(actual_t)}h  TC50={tc50_str} mM  -> {out_path.name}")
    return tc50


def main():
    time_points, concentrations, o2_matrix = load_data()

    # Default: 24h onwards (skip early pre-drug timepoints)
    if len(sys.argv) > 1:
        requested = [float(t) for t in sys.argv[1:]]
    else:
        requested = [t for t in time_points if t >= 24]

    print(f"Generating {len(requested)} TC50 plots for {DRUG}...")
    results = []
    for tp in requested:
        tc50 = generate_single_tc50(time_points, concentrations, o2_matrix, tp)
        results.append((tp, tc50))

    print(f"\nDone. {len(results)} plots saved to {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
