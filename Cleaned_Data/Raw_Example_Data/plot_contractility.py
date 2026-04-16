"""Plot Amiodarone and Mexiletine contractility dose-response: individual + averaged.
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
SAVE_DPI = 600
MAX_NAN_GAP = 7

# Per-drug config: (folder, csv, known_concs, skip_wells, n_high_baseline)
DRUGS = {
    'Amiodarone': {
        'folder': 'Amiodarone',
        'csv': 'Amp_std.csv',
        'known_concs': [10, 5, 2.5, 1.25, 0.782, 0.625, 0.313, 0.156],
        'skip_wells': set(),
        'n_high_baseline': 0,
    },
    'Mexiletine': {
        'folder': 'Mexiletine',
        'csv': 'Amp_std.csv',
        'known_concs': [20, 10, 5, 2.5, 1.25, 0.625, 0.313, 0.156],
        'skip_wells': {20, 22, 23, 24, 25, 27},  # 20: 0.625mM hump, 23: 0.313mM drops, 25: 0.156mM rises, 22/24/27: drop low
        'n_high_baseline': 0,
    },
    'Daunorubicin': {
        'folder': 'Stage2_Tables/Daunorubicin (F03)',
        'csv': 'Amp_std.csv',
        'known_concs': [8, 4, 2, 1, 0.5, 0.25, 0.125, 0.062],
        'skip_wells': set(),
        'n_high_baseline': 0,
    },
}


def clean_conc_label(label, known_concs):
    s = str(label)
    for k in known_concs:
        ks = str(k)
        if s == ks or s.startswith(ks + '.'):
            return k
    return float(s)


def max_nan_gap(arr):
    max_gap = 0
    current = 0
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


def load_data(drug_name, config):
    folder = BASE / config['folder']
    df = pd.read_csv(folder / config['csv'])
    time = df.iloc[:, 0].values.astype(float)

    wells = []
    for i, col in enumerate(df.columns[1:]):
        if i in config['skip_wells']:
            continue
        conc = clean_conc_label(col, config['known_concs'])
        vals = df[col].values.astype(float)
        wells.append((conc, vals))

    # Offset high-baseline wells if configured
    n_high = config['n_high_baseline']
    if n_high > 0:
        baselines = [(j, w[1][0]) for j, w in enumerate(wells) if not np.isnan(w[1][0])]
        baselines_sorted = sorted(baselines, key=lambda x: x[1], reverse=True)
        high_indices = {idx for idx, _ in baselines_sorted[:n_high]}
        low_baselines = [b for idx, b in baselines_sorted[n_high:]]
        avg_baseline = np.mean(low_baselines)
        print(f'  Average baseline (excluding top {n_high}): {avg_baseline:.4f}')
        for idx, bl in baselines_sorted[:n_high]:
            conc, vals = wells[idx]
            offset = bl - avg_baseline
            print(f'    {conc} mM well (baseline {bl:.4f}) -> offset by -{offset:.4f}')
            wells[idx] = (conc, vals - offset)

    return time, wells


def plot_individual(drug_name, time, wells, out_dir):
    concs_unique = sorted(set(c for c, _ in wells), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_unique))
    conc_to_color = {c: cmap(i / max(len(concs_unique) - 1, 1))
                     for i, c in enumerate(concs_unique)}

    # Process all wells first
    processed = []
    n_excluded = 0
    for conc, vals in wells:
        result = process_well(vals, time)
        if result is None:
            n_excluded += 1
            processed.append(None)
        else:
            processed.append(result)

    # Compute average smoothed start per concentration, compressed toward global mean
    conc_starts = defaultdict(list)
    for idx, (conc, vals) in enumerate(wells):
        if processed[idx] is not None:
            conc_starts[conc].append(processed[idx][1][0])
    conc_avg_raw = {c: np.mean(s) for c, s in conc_starts.items()}
    global_avg = np.mean(list(conc_avg_raw.values()))
    COMPRESS = 0.3  # 0=all same, 1=original spread
    conc_avg_start = {c: global_avg + COMPRESS * (v - global_avg)
                      for c, v in conc_avg_raw.items()}

    fig, ax = plt.subplots(figsize=(4.5, 3.0))
    plotted_concs = set()
    for idx, (conc, vals) in enumerate(wells):
        if processed[idx] is None:
            continue
        t_fine, v_fine = processed[idx]
        v_fine = v_fine - (v_fine[0] - conc_avg_start[conc])
        label = f'{conc}' if conc not in plotted_concs else None
        plotted_concs.add(conc)
        ax.plot(t_fine, v_fine, linewidth=0.8, alpha=0.7,
                color=conc_to_color[conc], label=label)

    ax.set_xlabel('Time (h)', fontsize=9)
    ax.set_ylabel('Contractility (Amp std)', fontsize=9)
    ax.set_title(f'{drug_name} — Individual Wells', fontsize=10, fontweight='bold')
    ax.set_xlim(time[0], time[-1])
    ax.tick_params(labelsize=7)

    handles, labels = ax.get_legend_handles_labels()
    sorted_pairs = sorted(zip(labels, handles), key=lambda x: -float(x[0]))
    ax.legend([h for _, h in sorted_pairs], [f'{l} mM' for l, _ in sorted_pairs],
              fontsize=5, title='Conc', title_fontsize=5,
              loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderpad=0.3, labelspacing=0.25, handlelength=1.2)

    out = out_dir / f'{drug_name}_Contractility_individual.png'
    fig.savefig(out, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f'  Saved: {out.name}  ({n_excluded} wells excluded)')


def plot_averaged(drug_name, time, wells, out_dir):
    conc_groups = defaultdict(list)
    for conc, vals in wells:
        result = process_well(vals, time)
        if result is not None:
            conc_groups[conc].append(result)

    concs_sorted = sorted(conc_groups.keys(), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_sorted))

    # Compute global average start across all concentrations
    conc_avg_raw = {c: np.mean([v[0] for _, v in traces])
                    for c, traces in conc_groups.items()}
    global_avg = np.mean(list(conc_avg_raw.values()))

    fig, ax = plt.subplots(figsize=(10, 8))
    for i, conc in enumerate(concs_sorted):
        traces = conc_groups[conc]
        t_fine = traces[0][0]
        # Offset each trace so it starts at global_avg (uniform shift)
        offset_traces = [v - (v[0] - global_avg) for _, v in traces]
        avg = np.mean(offset_traces, axis=0) * 100  # scale to percentage
        color = cmap(i / max(len(concs_sorted) - 1, 1))
        ax.plot(t_fine, avg, linewidth=2.5, color=color,
                label=f'{conc}')

    ax.set_xlabel('Time from Exposure (h)', fontsize=36, fontweight='bold')
    ax.set_ylabel('Contractility (%)', fontsize=36, fontweight='bold')
    ax.set_xlim(time[0], 100)
    ax.tick_params(labelsize=30, width=1.5)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight('bold')
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
        spine.set_linewidth(3.0)

    # Save locally (with legend for standalone use)
    ax.legend(fontsize=32, title='Concentration (mM)', title_fontsize=33,
              loc='lower left', ncol=2,
              borderpad=0.4, labelspacing=0.3, handlelength=1.2,
              columnspacing=1.0,
              framealpha=0.85, edgecolor='none')
    out_local = out_dir / f'{drug_name}_Contractility_offset_averaged.png'
    fig.savefig(out_local, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    print(f'  Saved: {out_local}')

    # Only Mexiletine goes to Fig_2
    if drug_name == 'Mexiletine':
        fig2_dir = Path(__file__).resolve().parents[2] / 'Output' / 'PowerPoint_Figures' / 'Fig_2'
        axisless_dir = fig2_dir / 'Axisless'
        axisless_dir.mkdir(parents=True, exist_ok=True)

        # Export legend as standalone image
        handles, labels = ax.get_legend_handles_labels()
        fig_leg = plt.figure(figsize=(4, 3))
        fig_leg.legend(handles, labels, fontsize=32,
                       title='Concentration (mM)', title_fontproperties={'size': 33},
                       ncol=2, borderpad=0.4, labelspacing=0.3,
                       handlelength=1.2, columnspacing=1.0,
                       loc='center', frameon=False)
        legend_path = axisless_dir / 'Fig_2j_Mexiletine_Contractility_legend.png'
        fig_leg.savefig(legend_path, dpi=SAVE_DPI, bbox_inches='tight',
                        pad_inches=0.1, facecolor='white')
        plt.close(fig_leg)
        print(f'  Saved legend: {legend_path}')

        # Remove legend from main figure, save original (no legend)
        ax.get_legend().remove()
        out_fig2 = fig2_dir / 'Fig_2j_Mexiletine_Contractility.png'
        fig.savefig(out_fig2, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
        print(f'  Saved: {out_fig2}')

        # Save axisless version — no axes, no legend, just data
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
        out_axisless = axisless_dir / 'Fig_2j_Mexiletine_Contractility.png'
        fig.savefig(out_axisless, dpi=SAVE_DPI, facecolor='white')
        print(f'  Saved axisless: {out_axisless}')
    plt.close(fig)
    print(f'  ({len(concs_sorted)} concentrations)')

    # Save processed averaged data to CSV for Excel provenance
    t_fine = conc_groups[concs_sorted[0]][0][0]
    processed_df = pd.DataFrame({'Time_h': t_fine})
    for conc in concs_sorted:
        traces = conc_groups[conc]
        offset_traces = [v - (v[0] - global_avg) for _, v in traces]
        avg = np.mean(offset_traces, axis=0) * 100
        processed_df[f'{conc}_mM'] = avg
    processed_csv = out_dir / f'{drug_name}_Contractility_averaged_processed.csv'
    processed_df.to_csv(processed_csv, index=False)
    print(f'  Saved processed data: {processed_csv}')


if __name__ == '__main__':
    for drug_name, config in DRUGS.items():
        out_dir = BASE / config['folder']
        out_dir.mkdir(exist_ok=True)
        print(f'\n=== {drug_name} ===')
        time, wells = load_data(drug_name, config)
        print(f'  {len(wells)} wells, {len(time)} timepoints')
        print(f'  Concentrations: {sorted(set(c for c, _ in wells), reverse=True)}')
        plot_individual(drug_name, time, wells, out_dir)
        plot_averaged(drug_name, time, wells, out_dir)

    print('\nDone.')
