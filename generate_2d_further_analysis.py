"""
Intensive smoothing for selected drugs in the further_analysis set.

Applies much heavier smoothing than the standard pipeline:
  1. Manual spike removal (known artifacts)
  2. Auto spike removal (threshold=5.0)
  3. Baseline alignment (normalize or offset)
  4. Second auto spike removal (threshold=2.5, more aggressive)
  5. Savitzky-Golay filter (window=11, polyorder=3) — removes high-freq noise
  6. Heavy LOWESS smoothing (frac=0.35) — captures broad trends
  7. Optional second LOWESS pass (frac=0.25) — extra polish
  8. Gaussian smoothing (sigma=1.5) — final gentle polish

Drugs: Amiodarone (O2), Doxorubicin (O2+Con), Epirubicin (O2+Con), Erlotinib (O2)

Usage:
    python generate_2d_further_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d

# ---------------------------------------------------------------------------
# Path discovery
# ---------------------------------------------------------------------------
current_dir = Path.cwd()
if current_dir.name == 'Prediction_Models':
    PROJECT_ROOT = current_dir.parent
elif (current_dir / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir
elif (current_dir.parent / 'EQN_Coefficients').exists():
    PROJECT_ROOT = current_dir.parent
else:
    PROJECT_ROOT = current_dir

try:
    import figure_config  # noqa: F401
except ImportError:
    pass

O2_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'O2_Mean_Averaged.xlsx'
CON_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'Heart_Contractility_Averaged.xlsx'
OUT_DIR = PROJECT_ROOT / 'Output' / '2D_Raw_Plots' / 'further_analysis' / 'favorites'
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAVE_DPI = 600

# Target drugs, response types, and mode
TARGETS = [
    ('Epirubicin', 'Contractility', 'offset'),
    ('Cobimetinib', 'O2', 'offset'),
]

# Concentrations to exclude per drug/response
SKIP_CONCENTRATIONS = {
    ('Epirubicin', 'Contractility'): {'0.094'},
}

# Manual spike indices (same as main script + extras for these drugs)
MANUAL_SPIKE_INDICES = {
    ('Epirubicin', 'O2', '0.094'): [15, 16, 17, 18, 19],
    ('Epirubicin', 'O2', '0.38'): [5, 18, 19, 33, 36],
}


def remove_spikes(vals, threshold_mult=5.0):
    """Detect and remove sharp isolated spikes from a 1D time series."""
    vals = np.array(vals, dtype=float)
    n = len(vals)
    if n < 3:
        return vals.copy(), 0

    diffs = np.abs(np.diff(vals))
    valid_diffs = diffs[~np.isnan(diffs)]
    if len(valid_diffs) == 0:
        return vals.copy(), 0
    typical_step = np.median(valid_diffs)
    if typical_step < 1e-9:
        typical_step = np.mean(valid_diffs) if np.mean(valid_diffs) > 1e-9 else 1.0

    spike_mask = np.zeros(n, dtype=bool)

    # Pass 1: single-point detector
    for i in range(1, n - 1):
        if np.isnan(vals[i]) or np.isnan(vals[i-1]) or np.isnan(vals[i+1]):
            continue
        neighbor_avg = (vals[i-1] + vals[i+1]) / 2.0
        dev = abs(vals[i] - neighbor_avg)
        neighbor_diff = abs(vals[i+1] - vals[i-1])
        if dev > threshold_mult * typical_step and dev > 2.0 * max(neighbor_diff, typical_step):
            spike_mask[i] = True

    # Pass 2: rolling median detector (±3 window)
    window = 3
    for i in range(n):
        if spike_mask[i] or np.isnan(vals[i]):
            continue
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        window_vals = []
        for j in range(lo, hi):
            if j != i and not spike_mask[j] and not np.isnan(vals[j]):
                window_vals.append(vals[j])
        if len(window_vals) < 3:
            continue
        med = np.median(window_vals)
        mad = np.median(np.abs(np.array(window_vals) - med))
        if mad < 1e-9:
            mad = typical_step
        dev = abs(vals[i] - med)
        if dev > max(3.0 * mad, threshold_mult * typical_step * 0.5):
            spike_mask[i] = True

    n_removed = int(spike_mask.sum())
    if n_removed == 0:
        return vals.copy(), 0

    cleaned = vals.copy()
    cleaned[spike_mask] = np.nan
    valid_idx = np.where(~np.isnan(cleaned))[0]
    if len(valid_idx) >= 2:
        cleaned = np.interp(np.arange(n), valid_idx, cleaned[valid_idx])

    return cleaned, n_removed


def intensive_smooth(vals, time):
    """Apply extreme smoothing with zero-slope baseline constraint.

    Uses CubicSpline with clamped boundary (zero derivative at start)
    on heavily pre-smoothed data, evaluated on a 1000-point fine grid.
    """
    from scipy.interpolate import CubicSpline
    import statsmodels.api as sm

    c = vals.copy()

    # Pre-smooth with LOWESS passes
    valid = ~np.isnan(c)
    if valid.sum() >= 4:
        lowess = sm.nonparametric.lowess(c[valid], time[valid], frac=0.55)
        c = np.interp(time, lowess[:, 0], lowess[:, 1])

    lowess = sm.nonparametric.lowess(c, time, frac=0.45)
    c = np.interp(time, lowess[:, 0], lowess[:, 1])

    lowess = sm.nonparametric.lowess(c, time, frac=0.35)
    c = np.interp(time, lowess[:, 0], lowess[:, 1])

    # Gaussian smooth
    c = gaussian_filter1d(c, sigma=3.0)

    # CubicSpline with clamped start (zero slope at baseline)
    # bc_type: first value gets zero derivative, last is natural (free)
    cs = CubicSpline(time, c, bc_type=((1, 0.0), (2, 0.0)))

    time_fine = np.linspace(time[0], time[-1], 1000)
    c_fine = cs(time_fine)

    return time_fine, c_fine


def plot_drug(drug_name, time, conc_labels, data, response_type, out_dir, mode='normalize'):
    """Plot one drug's time series with intensive smoothing."""
    fig, ax = plt.subplots(figsize=(4, 2.8))

    # Filter out skipped concentrations
    skip_set = SKIP_CONCENTRATIONS.get((drug_name, response_type), set())
    active_indices = [i for i in range(len(conc_labels)) if conc_labels[i] not in skip_set]
    n_active = len(active_indices)
    cmap = plt.get_cmap('plasma', n_active)
    conc_floats = [float(conc_labels[i]) for i in active_indices]
    order = [active_indices[j] for j in np.argsort(conc_floats)[::-1]]

    # First pass: clean all traces
    all_cleaned = {}
    total_spikes = 0
    for idx in active_indices:
        label = conc_labels[idx]
        raw_vals = data.iloc[:, idx].values.copy()

        # Manual spike removal
        manual_key = (drug_name, response_type, label)
        if manual_key in MANUAL_SPIKE_INDICES:
            manual_idx = MANUAL_SPIKE_INDICES[manual_key]
            raw_vals[manual_idx] = np.nan
            valid = np.where(~np.isnan(raw_vals))[0]
            if len(valid) >= 2:
                raw_vals = np.interp(np.arange(len(raw_vals)), valid, raw_vals[valid])

        # Auto spike removal (standard)
        cleaned, n_removed = remove_spikes(raw_vals, threshold_mult=5.0)
        total_spikes += n_removed
        all_cleaned[idx] = cleaned

    # Baseline alignment
    for idx in all_cleaned:
        c = all_cleaned[idx]
        baseline = np.nanmean(c[:3]) if len(c) >= 3 else np.nanmean(c[:1])
        if not np.isnan(baseline):
            if mode == 'normalize':
                if baseline != 0:
                    c = c / baseline
            else:  # offset
                c = c - baseline

        # More aggressive second spike removal (threshold=2.5)
        c, extra = remove_spikes(c, threshold_mult=2.5)
        total_spikes += extra

        # Interpolate NaNs
        valid_idx = np.where(~np.isnan(c))[0]
        if len(valid_idx) >= 2:
            c = np.interp(np.arange(len(c)), valid_idx, c[valid_idx])

        # Intensive smoothing — returns (time_fine, values_fine)
        t_fine, c_fine = intensive_smooth(c, time)

        all_cleaned[idx] = (t_fine, c_fine)

    # For normalize mode: re-align all traces to start at 1.0
    if mode == 'normalize':
        for idx in all_cleaned:
            t_f, c_f = all_cleaned[idx]
            all_cleaned[idx] = (t_f, c_f - c_f[0] + 1.0)

    # Shift traces: O2 starts at 15, Contractility starts just above 0
    if mode == 'offset':
        if response_type == 'O2':
            baseline_start = 15.0
        else:
            baseline_start = 0.01
        # Find the global min so nothing goes negative after shift
        global_min = min(np.nanmin(tc[1]) for tc in all_cleaned.values())
        shift = baseline_start - global_min if global_min < baseline_start else baseline_start
        for idx in all_cleaned:
            t_f, c_f = all_cleaned[idx]
            all_cleaned[idx] = (t_f, c_f + shift)

    # Plot
    for rank, idx in enumerate(order):
        label = conc_labels[idx]
        t_fine, c_fine = all_cleaned[idx]
        color = cmap(rank / max(n_active - 1, 1))
        ax.plot(t_fine, c_fine, linewidth=1.5, color=color, label=label)

    ax.set_xlabel('Time (h)', fontsize=9)
    if mode == 'normalize':
        if response_type == 'O2':
            ax.set_ylabel(r'$O_2$ (fraction of baseline)', fontsize=9)
        else:
            ax.set_ylabel('Contractility (fraction of baseline)', fontsize=9)
    else:
        if response_type == 'O2':
            ax.set_ylabel(r'$O_2$ (%)', fontsize=9)
        else:
            ax.set_ylabel('Contractility', fontsize=9)
    ax.set_title(drug_name, fontsize=10, fontweight='bold')
    ax.set_xlim(0, 96)
    ax.tick_params(labelsize=7)

    ax.legend(fontsize=5, title='Conc', title_fontsize=5,
              loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderpad=0.3, labelspacing=0.25, handlelength=1.2)

    fig.tight_layout()
    suffix = 'raw' if mode == 'normalize' else 'offset'
    fname = f'{drug_name}_{response_type}_{suffix}_smooth.png'
    fig.savefig(out_dir / fname, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    return fname, total_spikes


def main():
    o2_xls = pd.ExcelFile(O2_PATH)
    con_xls = pd.ExcelFile(CON_PATH)

    print(f'Output: {OUT_DIR}\n')
    print(f'=== Intensive smoothing — {len(TARGETS)} plots ===\n')

    for drug_name, resp_type, mode in TARGETS:
        if resp_type == 'O2':
            if drug_name not in o2_xls.sheet_names:
                print(f'  SKIP: {drug_name} O2 not found')
                continue
            df = pd.read_excel(o2_xls, sheet_name=drug_name)
        else:
            if drug_name not in con_xls.sheet_names:
                print(f'  SKIP: {drug_name} Contractility not found')
                continue
            df = pd.read_excel(con_xls, sheet_name=drug_name)

        time = df.iloc[:, 0].values
        conc_labels = [str(c) for c in df.columns[1:]]
        fname, spikes = plot_drug(drug_name, time, conc_labels, df.iloc[:, 1:],
                                  resp_type, OUT_DIR, mode=mode)
        spike_info = f' ({spikes} spikes removed)' if spikes else ''
        mode_label = 'normalized' if mode == 'normalize' else 'offset'
        print(f'  {fname} [{mode_label}]{spike_info}')

    print(f'\nDone. All plots saved to: {OUT_DIR}')


if __name__ == '__main__':
    main()
