"""Plot Cobimetinib O2 dose-response with two normalization approaches:
  1. Offset: all traces shifted to start at the same point (global average baseline)
  2. Normalized: all traces divided by their starting value (start at 100%)
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2]))

import figure_config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import CubicSpline
import statsmodels.api as sm
from collections import defaultdict

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / 'Cobimetinib (E03)'
OUT_DIR.mkdir(exist_ok=True)

SAVE_DPI = 600
MAX_NAN_GAP = 7

KNOWN_CONCS = [4, 2, 1, 0.5, 0.25, 0.125, 0.063, 0.031]
SKIP_WELL_INDICES = {13, 23, 26}


def clean_conc_label(label):
    s = str(label)
    for k in KNOWN_CONCS:
        ks = str(k)
        if s == ks or s.startswith(ks + '.'):
            return k
    return float(s)


def max_nan_gap(arr):
    max_gap = current = 0
    for v in arr:
        if np.isnan(v):
            current += 1
            max_gap = max(max_gap, current)
        else:
            current = 0
    return max_gap


def interpolate_limited(arr, max_gap):
    if max_nan_gap(arr) > max_gap:
        return None
    valid = np.where(~np.isnan(arr))[0]
    if len(valid) < 2:
        return None
    return np.interp(np.arange(len(arr)), valid, arr[valid])


def remove_spikes(vals, threshold_mult=5.0):
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
    for i in range(1, n - 1):
        if np.isnan(vals[i]) or np.isnan(vals[i-1]) or np.isnan(vals[i+1]):
            continue
        neighbor_avg = (vals[i-1] + vals[i+1]) / 2.0
        dev = abs(vals[i] - neighbor_avg)
        neighbor_diff = abs(vals[i+1] - vals[i-1])
        if dev > threshold_mult * typical_step and dev > 2.0 * max(neighbor_diff, typical_step):
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
    c = vals.copy()
    valid = ~np.isnan(c)
    if valid.sum() >= 4:
        lowess = sm.nonparametric.lowess(c[valid], time[valid], frac=0.55)
        c = np.interp(time, lowess[:, 0], lowess[:, 1])
    lowess = sm.nonparametric.lowess(c, time, frac=0.45)
    c = np.interp(time, lowess[:, 0], lowess[:, 1])
    lowess = sm.nonparametric.lowess(c, time, frac=0.35)
    c = np.interp(time, lowess[:, 0], lowess[:, 1])
    c = gaussian_filter1d(c, sigma=3.0)
    cs = CubicSpline(time, c, bc_type=((1, 0.0), (2, 0.0)))
    time_fine = np.linspace(time[0], time[-1], 1000)
    c_fine = cs(time_fine)
    return time_fine, c_fine


def process_well(vals, time):
    cleaned, _ = remove_spikes(vals, threshold_mult=5.0)
    interped = interpolate_limited(cleaned, MAX_NAN_GAP)
    if interped is None:
        return None
    interped, _ = remove_spikes(interped, threshold_mult=2.5)
    valid_idx = np.where(~np.isnan(interped))[0]
    if len(valid_idx) < 4:
        return None
    interped = np.interp(np.arange(len(interped)), valid_idx, interped[valid_idx])
    t_fine, v_fine = intensive_smooth(interped, time)
    return t_fine, v_fine


def load_data():
    df = pd.read_csv(OUT_DIR / 'O2_mean.csv')
    time = df.iloc[:, 0].values.astype(float)
    wells = []
    for i, col in enumerate(df.columns[1:]):
        if i in SKIP_WELL_INDICES:
            continue
        conc = clean_conc_label(col)
        vals = df[col].values.astype(float)
        wells.append((conc, vals))
    return time, wells


def plot_averaged_offset(time, wells):
    """All concentrations offset to start at the same point (global average baseline)."""
    conc_groups = defaultdict(list)
    for conc, vals in wells:
        result = process_well(vals, time)
        if result is not None:
            conc_groups[conc].append(result)

    # Compute each concentration's average start value
    conc_avg_start = {c: np.mean([v[0] for _, v in traces])
                      for c, traces in conc_groups.items()}
    # Global average baseline across all concentrations
    global_avg = np.mean(list(conc_avg_start.values()))

    concs_sorted = sorted(conc_groups.keys(), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_sorted))

    fig, ax = plt.subplots(figsize=(4.5, 3.0))
    for i, conc in enumerate(concs_sorted):
        traces = conc_groups[conc]
        t_fine = traces[0][0]
        # Offset each trace so it starts at global_avg
        offset_traces = [v - (v[0] - global_avg) for _, v in traces]
        avg = np.mean(offset_traces, axis=0)
        n_wells = len(traces)
        color = cmap(i / max(len(concs_sorted) - 1, 1))
        ax.plot(t_fine, avg, linewidth=1.5, color=color,
                label=f'{conc} mM (n={n_wells})')

    ax.set_xlabel('Time (h)', fontsize=9)
    ax.set_ylabel(r'$O_2$ (%)', fontsize=9)
    ax.set_title(r'Cobimetinib $O_2$ — Offset (Common Baseline)', fontsize=10, fontweight='bold')
    ax.set_xlim(time[0], time[-1])
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=5, title='Conc', title_fontsize=5,
              loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderpad=0.3, labelspacing=0.25, handlelength=1.2)

    out = OUT_DIR / 'Cobimetinib_O2_offset.png'
    fig.savefig(out, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f'Saved: {out.name}')


def plot_averaged_normalized(time, wells):
    """All concentrations normalized to start at 100% of their baseline."""
    conc_groups = defaultdict(list)
    for conc, vals in wells:
        result = process_well(vals, time)
        if result is not None:
            conc_groups[conc].append(result)

    concs_sorted = sorted(conc_groups.keys(), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_sorted))

    fig, ax = plt.subplots(figsize=(4.5, 3.0))
    for i, conc in enumerate(concs_sorted):
        traces = conc_groups[conc]
        t_fine = traces[0][0]
        # Normalize each trace: divide by its starting value -> starts at 100%
        norm_traces = []
        for _, v in traces:
            baseline = v[0]
            if abs(baseline) > 1e-6:
                norm_traces.append((v / baseline) * 100.0)
        if not norm_traces:
            continue
        avg = np.mean(norm_traces, axis=0)
        n_wells = len(norm_traces)
        color = cmap(i / max(len(concs_sorted) - 1, 1))
        ax.plot(t_fine, avg, linewidth=1.5, color=color,
                label=f'{conc} mM (n={n_wells})')

    ax.axhline(y=100, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.set_xlabel('Time (h)', fontsize=9)
    ax.set_ylabel(r'$O_2$ (% of baseline)', fontsize=9)
    ax.set_title(r'Cobimetinib $O_2$ — Normalized (% of Baseline)', fontsize=10, fontweight='bold')
    ax.set_xlim(time[0], time[-1])
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=5, title='Conc', title_fontsize=5,
              loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderpad=0.3, labelspacing=0.25, handlelength=1.2)

    out = OUT_DIR / 'Cobimetinib_O2_normalized.png'
    fig.savefig(out, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f'Saved: {out.name}')


if __name__ == '__main__':
    time, wells = load_data()
    print(f'Loaded {len(wells)} wells, {len(time)} timepoints')
    print(f'Concentrations: {sorted(set(c for c, _ in wells), reverse=True)}')
    print()
    plot_averaged_offset(time, wells)
    plot_averaged_normalized(time, wells)
    print('\nDone.')
