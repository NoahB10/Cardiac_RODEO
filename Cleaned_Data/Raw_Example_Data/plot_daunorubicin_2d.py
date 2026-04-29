"""Plot Daunorubicin 2D dose-response: O2 and Contractility.
Same heavy smoothing pipeline as Mexiletine/Cobimetinib plots.
Outputs individual + averaged plots for each.
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
DATA_DIR = BASE / 'Stage2_Tables' / 'Daunorubicin (F03)'
OUT_DIR = BASE / 'Daunorubicin'
OUT_DIR.mkdir(exist_ok=True)

FIG3_DIR = Path(__file__).resolve().parents[2] / 'Output' / 'PowerPoint_Figures' / 'Fig_3'
PROJECT_ROOT = Path(__file__).resolve().parents[2]

SAVE_DPI = 600
MAX_NAN_GAP = 7
KNOWN_CONCS = [8, 4, 2, 1, 0.5, 0.25, 0.125, 0.062]

CONFIGS = {
    'O2': {
        'csv': 'O2_mean.csv',
        'ylabel': r'$O_2$ (% Air)',
        'skip_wells': set(),
        'n_high_baseline': 0,
    },
    'Contractility': {
        'csv': 'Amp_std.csv',
        'ylabel': 'Contractility (%)',
        'skip_wells': set(),
        'n_high_baseline': 0,
        'scale': 100,  # multiply by 100 for display
    },
}


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


def load_data(config):
    df = pd.read_csv(DATA_DIR / config['csv'])
    time = df.iloc[:, 0].values.astype(float)

    wells = []
    for i, col in enumerate(df.columns[1:]):
        if i in config['skip_wells']:
            continue
        conc = clean_conc_label(col)
        vals = df[col].values.astype(float)
        wells.append((conc, vals))

    n_high = config['n_high_baseline']
    if n_high > 0:
        baselines = [(j, w[1][0]) for j, w in enumerate(wells) if not np.isnan(w[1][0])]
        baselines_sorted = sorted(baselines, key=lambda x: x[1], reverse=True)
        high_indices = {idx for idx, _ in baselines_sorted[:n_high]}
        low_baselines = [b for idx, b in baselines_sorted[n_high:]]
        avg_baseline = np.mean(low_baselines)
        for idx, bl in baselines_sorted[:n_high]:
            conc, vals = wells[idx]
            offset = bl - avg_baseline
            wells[idx] = (conc, vals - offset)

    return time, wells


def plot_individual(resp_type, config, time, wells):
    concs_unique = sorted(set(c for c, _ in wells), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_unique))
    conc_to_color = {c: cmap(i / max(len(concs_unique) - 1, 1))
                     for i, c in enumerate(concs_unique)}

    processed = []
    n_excluded = 0
    for conc, vals in wells:
        result = process_well(vals, time)
        if result is None:
            n_excluded += 1
            processed.append(None)
        else:
            processed.append(result)

    conc_starts = defaultdict(list)
    for idx, (conc, vals) in enumerate(wells):
        if processed[idx] is not None:
            conc_starts[conc].append(processed[idx][1][0])
    conc_avg_raw = {c: np.mean(s) for c, s in conc_starts.items()}
    global_avg = np.mean(list(conc_avg_raw.values()))
    COMPRESS = 0.3
    conc_avg_start = {c: global_avg + COMPRESS * (v - global_avg)
                      for c, v in conc_avg_raw.items()}

    fig, ax = plt.subplots(figsize=(4.5, 3.0))
    plotted_concs = set()
    scale = config.get('scale', 1)
    for idx, (conc, vals) in enumerate(wells):
        if processed[idx] is None:
            continue
        t_fine, v_fine = processed[idx]
        v_fine = v_fine - (v_fine[0] - conc_avg_start[conc])
        v_fine = v_fine * scale
        label = f'{conc}' if conc not in plotted_concs else None
        plotted_concs.add(conc)
        ax.plot(t_fine, v_fine, linewidth=0.8, alpha=0.7,
                color=conc_to_color[conc], label=label)

    ax.set_xlabel('Time (h)', fontsize=9)
    ax.set_ylabel(config['ylabel'], fontsize=9)
    ax.set_title(f'Daunorubicin {resp_type} — Individual Wells', fontsize=10, fontweight='bold')
    ax.set_xlim(time[0], time[-1])
    ax.tick_params(labelsize=7)

    handles, labels = ax.get_legend_handles_labels()
    sorted_pairs = sorted(zip(labels, handles), key=lambda x: -float(x[0]))
    ax.legend([h for _, h in sorted_pairs], [f'{l} mM' for l, _ in sorted_pairs],
              fontsize=5, title='Conc', title_fontsize=5,
              loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderpad=0.3, labelspacing=0.25, handlelength=1.2)

    out = OUT_DIR / f'Daunorubicin_{resp_type}_individual.png'
    fig.savefig(out, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f'  Saved: {out.name}  ({n_excluded} wells excluded)')


def load_pkpd_params(resp_type='O2'):
    """Load PKPD elimination coefficients for Daunorubicin."""
    coeff_path = PROJECT_ROOT / 'EQN_Coefficients' / 'all_equations_coefficients.xlsx'
    df = pd.read_excel(coeff_path, sheet_name='pkpd_elimination', header=1)
    df.columns = df.columns.str.strip()
    row = df[df['Drug'] == 'Daunorubicin'].iloc[0]
    sfx = '.1' if resp_type == 'O2' else ''
    return {
        'R0': float(row[f'R0{sfx}']),
        'Emax': float(row[f'Emax{sfx}']),
        'kappa': float(row[f'kappa{sfx}']),
        'n': float(row[f'n{sfx}']),
        'm': float(row[f'm{sfx}']),
        'tau': float(row[f'tau{sfx}']),
        'k_elim': float(row[f'k_elim{sfx}']),
        'Cmax': float(row[f'Cmax_used{sfx}']),
    }


def pkpd_elimination(t, dose_ratio, p):
    """Evaluate PKPD elimination equation for a single dose ratio over time."""
    t = np.maximum(t, 0)
    kappa = max(p['kappa'], 1e-9)
    tau = max(p['tau'], 1e-9)
    k_elim = max(p['k_elim'], 1e-9)
    C_t = dose_ratio * np.exp(-k_elim * t)
    driving = kappa * (C_t ** p['n']) * ((t / tau) ** p['m'])
    return p['R0'] + p['Emax'] * (1 - np.exp(-driving))


def plot_averaged(resp_type, config, time, wells):
    conc_groups = defaultdict(list)
    for conc, vals in wells:
        result = process_well(vals, time)
        if result is not None:
            conc_groups[conc].append(result)

    concs_sorted = sorted(conc_groups.keys(), reverse=True)
    cmap = plt.get_cmap('plasma', len(concs_sorted))

    conc_avg_raw = {c: np.mean([v[0] for _, v in traces])
                    for c, traces in conc_groups.items()}
    global_avg = np.mean(list(conc_avg_raw.values()))

    scale = config.get('scale', 1)

    # Load PKPD model params
    pkpd_params = load_pkpd_params(resp_type)

    fig, ax = plt.subplots(figsize=(12, 8))
    from matplotlib.lines import Line2D

    for i, conc in enumerate(concs_sorted):
        traces = conc_groups[conc]
        t_fine = traces[0][0]
        offset_traces = [v - (v[0] - global_avg) for _, v in traces]
        avg = np.mean(offset_traces, axis=0) * scale
        color = cmap(i / max(len(concs_sorted) - 1, 1))
        ax.plot(t_fine, avg, linewidth=2.5, color=color)

        # Overlay PKPD model prediction, shifted to match data baseline at t=0
        dose_ratio = conc / pkpd_params['Cmax']
        t_model = np.linspace(0, 100, 1000)
        r_model = pkpd_elimination(t_model, dose_ratio, pkpd_params)
        if resp_type == 'Contractility':
            r_model = r_model * 100
        # Shift model so its t=0 value matches the data's t=0 value
        data_start = avg[0]
        model_start = r_model[0]
        r_model = r_model + (data_start - model_start)
        ax.plot(t_model, r_model, linewidth=2.5, color=color,
                linestyle='--', alpha=0.8)

    ax.set_xlabel('Time from Exposure (h)', fontsize=26, fontweight='bold')
    ax.set_ylabel(config['ylabel'], fontsize=26, fontweight='bold')
    ax.set_xlim(time[0], 100)
    ax.tick_params(labelsize=20, width=1.5)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight('bold')
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
        spine.set_linewidth(3.0)

    # 2-column legend: split concs evenly, pad shorter, then Data/Model on same last row
    half = (len(concs_sorted) + 1) // 2
    col1_conc = list(range(half))
    col2_conc = list(range(half, len(concs_sorted)))

    col1_handles = [Line2D([0], [0], color=cmap(i / max(len(concs_sorted) - 1, 1)),
                           linewidth=2.5) for i in col1_conc]
    col1_labels = [f'{concs_sorted[i]} mM' for i in col1_conc]

    col2_handles = [Line2D([0], [0], color=cmap(i / max(len(concs_sorted) - 1, 1)),
                           linewidth=2.5) for i in col2_conc]
    col2_labels = [f'{concs_sorted[i]} mM' for i in col2_conc]

    while len(col1_handles) < len(col2_handles):
        col1_handles.append(Line2D([0], [0], alpha=0))
        col1_labels.append('')
    while len(col2_handles) < len(col1_handles):
        col2_handles.append(Line2D([0], [0], alpha=0))
        col2_labels.append('')

    col1_handles.append(Line2D([0], [0], color='black', linewidth=2.5, linestyle='-'))
    col1_labels.append('— Data')
    col2_handles.append(Line2D([0], [0], color='black', linewidth=2.5, linestyle='--'))
    col2_labels.append('-- Model')

    all_handles, all_labels = [], []
    for j in range(len(col1_handles)):
        all_handles.append(col1_handles[j])
        all_labels.append(col1_labels[j])
        all_handles.append(col2_handles[j])
        all_labels.append(col2_labels[j])

    legend_loc = 'lower left' if resp_type == 'Contractility' else 'upper left'
    ax.legend(all_handles, all_labels, fontsize=14,
              loc=legend_loc, ncol=2,
              borderpad=0.3, labelspacing=0.2, handlelength=1.2,
              columnspacing=0.8, handletextpad=0.4,
              framealpha=0.85, edgecolor='none')

    out = OUT_DIR / f'Daunorubicin_{resp_type}_offset_averaged.png'
    fig.savefig(out, dpi=SAVE_DPI, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    plt.close(fig)
    print(f'  Saved: {out.name}  ({len(concs_sorted)} concentrations)')


if __name__ == '__main__':
    for resp_type, config in CONFIGS.items():
        print(f'\n=== Daunorubicin {resp_type} ===')
        time, wells = load_data(config)
        print(f'  {len(wells)} wells, {len(time)} timepoints')
        print(f'  Concentrations: {sorted(set(c for c, _ in wells), reverse=True)}')
        plot_individual(resp_type, config, time, wells)
        plot_averaged(resp_type, config, time, wells)

    print('\nDone.')
