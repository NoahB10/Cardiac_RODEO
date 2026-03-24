"""
Generate 2D time-series plots of raw (unsmoothed) averaged data for each drug.

X-axis: Time (hours)
Y-axis: O2 (%) or Contractility
One line per concentration, color-coded by dose.

Data source: Cleaned_Data/O2_Mean_Averaged.xlsx and Heart_Contractility_Averaged.xlsx
These are simple means of replicate wells (no smoothing or interpolation).

Spike removal: detects isolated outliers that deviate sharply from their
neighbors using a rolling median filter, removes them, and linearly
interpolates across the gaps.

Usage:
    python generate_2d_raw_plots.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import shutil

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

# Try to load project font config
try:
    import figure_config  # noqa: F401
except ImportError:
    pass

O2_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'O2_Mean_Averaged.xlsx'
CON_PATH = PROJECT_ROOT / 'Cleaned_Data' / 'Heart_Contractility_Averaged.xlsx'
OUT_DIR = PROJECT_ROOT / 'Output' / '2D_Raw_Plots'

# Drugs to skip (averaged data doesn't match raw wells — possible well exclusion)
SKIP_DRUGS = {'Panobinostat', 'Vioxx'}

SAVE_DPI = 600

# Manual spike indices: {(drug, response_type, conc_label): [indices to NaN and interpolate]}
# Used for multi-point spikes that the automatic detector can't catch
MANUAL_SPIKE_INDICES = {
    ('Epirubicin', 'O2', '0.094'): [15, 16, 17, 18, 19],  # ramp artifact t=40-51h
    ('Epirubicin', 'O2', '0.38'): [5, 18, 19, 33, 36],     # isolated + 2-point spikes
}



def remove_spikes(vals, threshold_mult=5.0):
    """Detect and remove sharp isolated spikes from a 1D time series.

    Uses two passes:
    1. Single-point detector: compares each point to its 2 immediate neighbors.
    2. Rolling median detector: compares each point to a wider window median,
       catching multi-point spikes that the single-point detector misses.

    Parameters
    ----------
    vals : array-like
    threshold_mult : float, default 5.0
        Multiplier for spike detection. Lower = more aggressive.

    Returns
    -------
    cleaned : ndarray, with spikes replaced by linear interpolation
    n_removed : int
    """
    vals = np.array(vals, dtype=float)
    n = len(vals)
    if n < 3:
        return vals.copy(), 0

    # Compute typical step size (median of consecutive differences)
    diffs = np.abs(np.diff(vals))
    valid_diffs = diffs[~np.isnan(diffs)]
    if len(valid_diffs) == 0:
        return vals.copy(), 0
    typical_step = np.median(valid_diffs)
    if typical_step < 1e-9:
        typical_step = np.mean(valid_diffs) if np.mean(valid_diffs) > 1e-9 else 1.0

    spike_mask = np.zeros(n, dtype=bool)

    # Pass 1: single-point spike detection (original method)
    for i in range(1, n - 1):
        if np.isnan(vals[i]) or np.isnan(vals[i-1]) or np.isnan(vals[i+1]):
            continue
        neighbor_avg = (vals[i-1] + vals[i+1]) / 2.0
        dev = abs(vals[i] - neighbor_avg)
        neighbor_diff = abs(vals[i+1] - vals[i-1])
        if dev > threshold_mult * typical_step and dev > 2.0 * max(neighbor_diff, typical_step):
            spike_mask[i] = True

    # Pass 2: rolling median detector for multi-point spikes
    # Compare each point to the median of a wider window (±3 points)
    window = 3  # half-window size
    for i in range(n):
        if spike_mask[i] or np.isnan(vals[i]):
            continue
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        # Exclude the point itself and already-flagged points from the window
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
        # Flag if point deviates > 3× MAD from the local median
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


def plot_drug(drug_name, time, conc_labels, data, response_type, out_dir,
              mode='normalize'):
    """Plot one drug's time series with one line per concentration.

    Parameters
    ----------
    drug_name : str
    time : array-like, shape (n_timepoints,)
    conc_labels : list of str, concentration column headers
    data : DataFrame columns corresponding to conc_labels
    response_type : 'O2' or 'Contractility'
    out_dir : Path
    mode : 'normalize' or 'offset'
        normalize: divide by baseline (fraction of baseline)
        offset: subtract baseline so all traces start at 0

    Returns
    -------
    fname : str, output filename
    total_spikes : int, total spikes removed across all concentrations
    """
    fig, ax = plt.subplots(figsize=(4, 2.8))

    n_conc = len(conc_labels)
    cmap = plt.get_cmap('plasma', n_conc)

    # Sort concentrations high → low for legend order
    conc_floats = [float(c) for c in conc_labels]
    order = np.argsort(conc_floats)[::-1]

    # First pass: clean all traces and compute y-offsets
    all_cleaned = {}
    total_spikes = 0
    for idx in range(n_conc):
        label = conc_labels[idx]
        raw_vals = data.iloc[:, idx].values.copy()

        # Apply manual spike removal first (for multi-point artifacts)
        manual_key = (drug_name, response_type, label)
        if manual_key in MANUAL_SPIKE_INDICES:
            manual_idx = MANUAL_SPIKE_INDICES[manual_key]
            raw_vals[manual_idx] = np.nan
            valid = np.where(~np.isnan(raw_vals))[0]
            if len(valid) >= 2:
                raw_vals = np.interp(np.arange(len(raw_vals)), valid, raw_vals[valid])

        cleaned, n_removed = remove_spikes(raw_vals)
        total_spikes += n_removed

        all_cleaned[idx] = cleaned

    # Baseline alignment
    import statsmodels.api as sm
    for idx in all_cleaned:
        c = all_cleaned[idx]
        baseline = np.nanmean(c[:3]) if len(c) >= 3 else np.nanmean(c[:1])
        if not np.isnan(baseline):
            if mode == 'normalize':
                if baseline != 0:
                    c = c / baseline
            else:  # offset
                c = c - baseline
        # Second-pass spike removal on aligned data (more aggressive, threshold=3.0)
        c, _ = remove_spikes(c, threshold_mult=3.0)
        # Interpolate any NaNs from spike removal
        valid_idx = np.where(~np.isnan(c))[0]
        if len(valid_idx) >= 2:
            c = np.interp(np.arange(len(c)), valid_idx, c[valid_idx])
        # Light LOWESS smoothing (frac=0.2, half of original 0.4)
        valid = ~np.isnan(c)
        if valid.sum() >= 4:
            lowess = sm.nonparametric.lowess(c[valid], time[valid], frac=0.2)
            c = np.interp(time, lowess[:, 0], lowess[:, 1])
        all_cleaned[idx] = c

    # For offset mode: shift all traces up so no values are zero or negative
    if mode == 'offset':
        global_min = min(np.nanmin(c) for c in all_cleaned.values())
        if global_min <= 0:
            shift = abs(global_min) + 0.01  # small margin above zero
            for idx in all_cleaned:
                all_cleaned[idx] = all_cleaned[idx] + shift

    # Plot
    for rank, idx in enumerate(order):
        label = conc_labels[idx]
        cleaned = all_cleaned[idx]
        color = cmap(rank / max(n_conc - 1, 1))
        ax.plot(time, cleaned, linewidth=1.2, color=color, label=label)

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

    # Legend outside on the right
    ax.legend(fontsize=5, title='Conc', title_fontsize=5,
              loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderpad=0.3, labelspacing=0.25, handlelength=1.2)

    fig.tight_layout()
    suffix = 'raw' if mode == 'normalize' else 'offset'
    fname = f'{drug_name}_{response_type}_{suffix}.png'
    fig.savefig(out_dir / fname, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    return fname, total_spikes


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    o2_xls = pd.ExcelFile(O2_PATH)
    con_xls = pd.ExcelFile(CON_PATH)

    drugs = [s for s in o2_xls.sheet_names if s not in SKIP_DRUGS]

    for mode in ('normalize', 'offset'):
        if mode == 'normalize':
            mode_label = 'Normalized'
        else:
            mode_label = 'Baseline_Aligned'
        mode_dir = OUT_DIR / mode_label
        mode_dir.mkdir(parents=True, exist_ok=True)
        print(f'\n=== Generating {mode_label} plots for {len(drugs)} drugs ===')
        print(f'Output: {mode_dir}\n')

        count = 0
        total_all = 0
        for drug in drugs:
            # O2
            df_o2 = pd.read_excel(o2_xls, sheet_name=drug)
            time = df_o2.iloc[:, 0].values
            conc_labels = [str(c) for c in df_o2.columns[1:]]
            fname, spikes = plot_drug(drug, time, conc_labels, df_o2.iloc[:, 1:],
                                      'O2', mode_dir, mode=mode)
            spike_info = f' ({spikes} spikes removed)' if spikes else ''
            print(f'  {fname}{spike_info}')
            count += 1
            total_all += spikes

            # Contractility
            if drug in con_xls.sheet_names:
                df_con = pd.read_excel(con_xls, sheet_name=drug)
                time_c = df_con.iloc[:, 0].values
                conc_labels_c = [str(c) for c in df_con.columns[1:]]
                fname, spikes = plot_drug(drug, time_c, conc_labels_c, df_con.iloc[:, 1:],
                                          'Contractility', mode_dir, mode=mode)
                spike_info = f' ({spikes} spikes removed)' if spikes else ''
                print(f'  {fname}{spike_info}')
                count += 1
                total_all += spikes

        print(f'\n{mode_label}: {count} plots, {total_all} spikes removed')
        _categorize(mode_dir)


def _categorize(src_dir):
    """Copy plots into category subfolders based on drug classification."""
    df = pd.read_excel(
        PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx',
        sheet_name='pkpd_elimination', header=1)
    df.columns = df.columns.str.strip()

    cats = {
        'Arrhythmia_and_HeartDamage': [],
        'Arrhythmia_Only': [],
        'HeartDamage_Only': [],
        'Neither': []
    }

    for _, row in df.iterrows():
        drug = row['Drug'].strip()
        if drug in SKIP_DRUGS:
            continue
        arr = str(row['Arrhythmia']).strip().lower() == 'true'
        hd = str(row['heart_damage']).strip().lower() == 'true'

        if arr and hd:
            cats['Arrhythmia_and_HeartDamage'].append(drug)
        elif arr:
            cats['Arrhythmia_Only'].append(drug)
        elif hd:
            cats['HeartDamage_Only'].append(drug)
        else:
            cats['Neither'].append(drug)

    for cat, drugs in cats.items():
        cat_dir = src_dir / cat
        cat_dir.mkdir(exist_ok=True)
        for drug in drugs:
            for suffix in ['O2_raw.png', 'Contractility_raw.png',
                          'O2_offset.png', 'Contractility_offset.png']:
                src = src_dir / f'{drug}_{suffix}'
                if src.exists():
                    shutil.copy2(src, cat_dir / src.name)
        print(f'  {cat}: {len(drugs)} drugs')


if __name__ == '__main__':
    main()
