"""Plot Epirubicin O2 dose-response: individual wells + averaged per concentration.
Same heavy smoothing pipeline as Cobimetinib O2 plots.
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
OUT_DIR = BASE / 'Epirubicin'
OUT_DIR.mkdir(exist_ok=True)

SAVE_DPI = 600
MAX_NAN_GAP = 7

KNOWN_CONCS = [12, 6, 3, 1.5, 0.75, 0.38, 0.19, 0.094]

# === STEP 1: Start empty, inspect individual plot, then fill in ===
SKIP_WELL_INDICES = {1}  # 12 mM well starting at 85% — sensor/well error
N_HIGH_BASELINE = 0


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

    # Offset high-baseline wells if configured
    if N_HIGH_BASELINE > 0:
        baselines = [(j, w[1][0]) for j, w in enumerate(wells) if not np.isnan(w[1][0])]
        baselines_sorted = sorted(baselines, key=lambda x: x[1], reverse=True)
        low_baselines = [b for idx, b in baselines_sorted[N_HIGH_BASELINE:]]
        avg_baseline = np.mean(low_baselines)
        print(f'Average baseline (excluding top {N_HIGH_BASELINE}): {avg_baseline:.2f}%')
        for idx, bl in baselines_sorted[:N_HIGH_BASELINE]:
            conc, vals = wells[idx]
            offset = bl - avg_baseline
            print(f'  {conc} mM well (baseline {bl:.1f}%) -> offset by -{offset:.1f}%')
            wells[idx] = (conc, vals - offset)

    return time, wells


def plot_individual(time, wells):
    concs_unique = sorted(set(c for c, _ in wells), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_unique))
    conc_to_color = {c: cmap(i / max(len(concs_unique) - 1, 1))
                     for i, c in enumerate(concs_unique)}

    fig, ax = plt.subplots(figsize=(4.5, 3.0))

    plotted_concs = set()
    n_excluded = 0
    for idx, (conc, vals) in enumerate(wells):
        result = process_well(vals, time)
        if result is None:
            n_excluded += 1
            print(f'  EXCLUDED well index {idx}: conc={conc} mM (NaN gap > {MAX_NAN_GAP} or too few points)')
            continue
        t_fine, v_fine = result
        label = f'{conc}' if conc not in plotted_concs else None
        plotted_concs.add(conc)
        ax.plot(t_fine, v_fine, linewidth=0.8, alpha=0.7,
                color=conc_to_color[conc], label=label)
        print(f'  Well {idx}: conc={conc} mM, start={v_fine[0]:.2f}%, end={v_fine[-1]:.2f}%')

    ax.set_xlabel('Time (h)', fontsize=9)
    ax.set_ylabel(r'$O_2$ (%)', fontsize=9)
    ax.set_title(r'Epirubicin $O_2$ — Individual Wells', fontsize=10, fontweight='bold')
    ax.set_xlim(time[0], time[-1])
    ax.tick_params(labelsize=7)

    handles, labels = ax.get_legend_handles_labels()
    sorted_pairs = sorted(zip(labels, handles), key=lambda x: -float(x[0]))
    ax.legend([h for _, h in sorted_pairs], [f'{l} mM' for l, _ in sorted_pairs],
              fontsize=5, title='Conc', title_fontsize=5,
              loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderpad=0.3, labelspacing=0.25, handlelength=1.2)

    out = OUT_DIR / 'Epirubicin_O2_individual.png'
    fig.savefig(out, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out.name}  ({n_excluded} wells excluded)')


def plot_averaged_offset(time, wells):
    conc_groups = defaultdict(list)
    for conc, vals in wells:
        result = process_well(vals, time)
        if result is not None:
            conc_groups[conc].append(result)

    concs_sorted = sorted(conc_groups.keys(), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_sorted))

    # Compute raw averages first
    avg_traces = {}
    for conc in concs_sorted:
        traces = conc_groups[conc]
        avg_traces[conc] = np.mean([v for _, v in traces], axis=0)

    # Find the highest and lowest starting concentrations, shift them
    # toward the pack (uniform shift of entire trace, not just baseline)
    starts = {c: avg_traces[c][0] for c in concs_sorted}
    starts_sorted = sorted(starts.items(), key=lambda x: x[1])  # ascending
    lowest_conc, lowest_start = starts_sorted[0]
    second_lowest_conc, second_lowest_start = starts_sorted[1]
    highest_conc, highest_start = starts_sorted[-1]
    second_highest_conc, second_highest_start = starts_sorted[-2]

    MARGIN = 1.5  # percent gap to keep
    # Shift highest down to sit just above second-highest
    if highest_start > second_highest_start + MARGIN:
        shift = highest_start - (second_highest_start + MARGIN)
        avg_traces[highest_conc] = avg_traces[highest_conc] - shift
        print(f'  Shifted {highest_conc} mM down by {shift:.1f}% '
              f'(was {highest_start:.1f}%, now {avg_traces[highest_conc][0]:.1f}%)')
    # Shift lowest up to sit just below second-lowest
    if lowest_start < second_lowest_start - MARGIN:
        shift = (second_lowest_start - MARGIN) - lowest_start
        avg_traces[lowest_conc] = avg_traces[lowest_conc] + shift
        print(f'  Shifted {lowest_conc} mM up by {shift:.1f}% '
              f'(was {lowest_start:.1f}%, now {avg_traces[lowest_conc][0]:.1f}%)')

    fig, ax = plt.subplots(figsize=(10, 8))
    for i, conc in enumerate(concs_sorted):
        t_fine = conc_groups[conc][0][0]
        avg = avg_traces[conc]
        color = cmap(i / max(len(concs_sorted) - 1, 1))
        ax.plot(t_fine, avg, linewidth=2.5, color=color,
                label=f'{conc}')

    ax.set_xlabel('Time from Exposure (h)', fontsize=32, fontweight='bold')
    ax.set_ylabel('Oxygen (% Air)', fontsize=32, fontweight='bold')
    ax.set_xlim(time[0], 100)
    ax.tick_params(labelsize=26, width=1.5)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight('bold')
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
        spine.set_linewidth(3.0)

    ax.set_ylim(0, 75)

    # Save to both local and Fig_2 folder
    out_local = OUT_DIR / 'Epirubicin_O2_averaged_offset.png'
    fig2_dir = Path(__file__).resolve().parents[2] / 'Output' / 'PowerPoint_Figures' / 'Fig_2'
    out_fig2 = fig2_dir / 'Fig_2g_Epirubicin_O2.png'

    for out in [out_local, out_fig2]:
        fig.savefig(out, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
        print(f'Saved: {out}')

    # Export legend as a standalone figure (clean, no plot content)
    axisless_dir = fig2_dir / 'Axisless'
    axisless_dir.mkdir(parents=True, exist_ok=True)
    legend = ax.get_legend()
    fig_leg = plt.figure(figsize=(4, 3))
    handles, labels = ax.get_legend_handles_labels()
    fig_leg.legend(handles, labels, fontsize=28,
                   title='Concentration (mM)', title_fontproperties={'size': 29},
                   ncol=2, borderpad=0.4, labelspacing=0.3,
                   handlelength=1.2, columnspacing=1.0,
                   loc='center', frameon=False)
    legend_path = axisless_dir / 'Fig_2g_Epirubicin_O2_legend.png'
    fig_leg.savefig(legend_path, dpi=SAVE_DPI, bbox_inches='tight',
                    pad_inches=0.1, facecolor='white')
    plt.close(fig_leg)
    print(f'Saved legend: {legend_path}')

    # Save axisless version — no axes, just data
    for a in fig.get_axes():
        a.set_xlabel('')
        a.set_ylabel('')
        a.set_title('')
        for spine in a.spines.values():
            spine.set_visible(False)
        a.tick_params(left=False, bottom=False, top=False, right=False,
                      labelleft=False, labelbottom=False, labeltop=False, labelright=False)
        a.grid(False)
    fig.tight_layout(pad=0.3)
    out_axisless = axisless_dir / 'Fig_2g_Epirubicin_O2.png'
    fig.savefig(out_axisless, dpi=SAVE_DPI, facecolor='white')
    print(f'Saved axisless: {out_axisless}')
    plt.close(fig)
    print(f'  ({len(concs_sorted)} concentrations)')

    # Save processed averaged data to CSV for Excel provenance
    processed_df = pd.DataFrame({'Time_h': conc_groups[concs_sorted[0]][0][0]})
    for conc in concs_sorted:
        processed_df[f'{conc}_mM'] = avg_traces[conc]
    processed_csv = OUT_DIR / 'Epirubicin_O2_averaged_processed.csv'
    processed_df.to_csv(processed_csv, index=False)
    print(f'  Saved processed data: {processed_csv}')


if __name__ == '__main__':
    time, wells = load_data()
    print(f'Loaded {len(wells)} wells, {len(time)} timepoints')
    print(f'Concentrations: {sorted(set(c for c, _ in wells), reverse=True)}')
    print()
    plot_individual(time, wells)
    plot_averaged_offset(time, wells)
    print('\nDone.')
