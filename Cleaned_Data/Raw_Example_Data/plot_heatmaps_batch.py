"""Generate smoothed heatmaps of O2 per-well data for Doxorubicin, Plicamycin, Vandetanib.
Each row = one well, labeled with well index and concentration.
Produces raw + smoothed heatmap for each drug for outlier review.
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2]))

import figure_config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT_BASE = Path(__file__).resolve().parents[2] / 'Output' / 'Surface_Feature_Comparison'

HEATMAP_BLUE = '#123BFF'
HEATMAP_RED = '#FF2908'
SIGMA = 1.5

DRUGS = {
    'Doxorubicin': {
        'folder': 'Doxorubicin (G03)',
        'csv': 'O2_mean.csv',
        'known_concs': [10, 5, 2.5, 1.25, 0.63, 0.31, 0.16],
        'skip_wells': set(),
        'vmin': 0, 'vmax': 80,
    },
    'Plicamycin': {
        'folder': 'Plicamycin',
        'csv': 'O2_mean.csv',
        'known_concs': [20, 10, 5, 2.5, 1.25, 0.625, 0.313, 0.156],
        'skip_wells': set(),
    },
    'Vandetanib': {
        'folder': 'Vandetanib (G11)',
        'csv': 'O2_mean.csv',
        'known_concs': [8, 4, 2, 1, 0.5, 0.25, 0.125, 0.062],
        'skip_wells': set(),
    },
}


def clean_conc_label(label, known_concs):
    s = str(label)
    for k in known_concs:
        ks = str(k)
        if s == ks or s.startswith(ks + '.'):
            return k
    return float(s)


def make_heatmap(drug_name, config):
    folder = BASE / config['folder']
    out_dir = OUTPUT_BASE / drug_name
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(folder / config['csv'], index_col=0)
    data = df.T  # rows=wells, cols=timepoints

    # Build row labels
    row_labels = []
    keep_mask = []
    for i, col in enumerate(df.columns):
        conc = clean_conc_label(col, config['known_concs'])
        if i in config['skip_wells']:
            keep_mask.append(False)
            continue
        keep_mask.append(True)
        row_labels.append(f'W{i}: {conc} mM')

    data_filtered = data.iloc[[j for j, k in enumerate(keep_mask) if k], :]
    values = data_filtered.values.astype(float)

    # Sort by concentration (descending) then well index within each conc
    concs = [clean_conc_label(df.columns[j], config['known_concs'])
             for j, k in enumerate(keep_mask) if k]
    original_indices = [j for j, k in enumerate(keep_mask) if k]
    sort_order = sorted(range(len(concs)),
                        key=lambda x: (-concs[x], original_indices[x]))
    values = values[sort_order]
    row_labels = [row_labels[i] for i in sort_order]

    time_labels = [str(t) for t in data_filtered.columns.tolist()]

    cmap = LinearSegmentedColormap.from_list('cardiac_rodeo',
                                              [HEATMAP_BLUE, 'white', HEATMAP_RED])
    cmap.set_bad('white')

    raw_vmin = config.get('vmin', np.nanpercentile(values, 1))
    raw_vmax = config.get('vmax', np.nanpercentile(values, 99))

    # --- Raw heatmap ---
    fig, ax = plt.subplots(figsize=(6.5, 5.0))
    sns.heatmap(
        pd.DataFrame(values, index=row_labels, columns=time_labels),
        annot=False, cmap=cmap,
        vmin=raw_vmin, vmax=raw_vmax,
        cbar_kws={'label': r'$O_2$ (%)', 'shrink': 0.8},
        xticklabels=True, yticklabels=True,
        square=False, linewidths=0.3, linecolor='#cccccc', ax=ax
    )
    ax.set_xlabel('Time (h)', fontsize=9)
    ax.set_ylabel('Well', fontsize=9)
    ax.set_title(f'{drug_name} $O_2$ — Raw Per-Well Heatmap',
                 fontsize=10, fontweight='bold')

    n_x = len(time_labels)
    x_step = max(1, n_x // 10)
    ax.set_xticks(range(0, n_x, x_step))
    ax.set_xticklabels([time_labels[i] for i in range(0, n_x, x_step)],
                        rotation=45, ha='right', fontsize=6)
    ax.tick_params(axis='y', labelsize=6)
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=6)

    fig.tight_layout()
    out = out_dir / f'{drug_name}_O2_heatmap_raw.png'
    fig.savefig(str(out), dpi=600, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out.name}')

    # --- Smoothed heatmap ---
    orig_mean = np.nanmean(values)
    orig_std = np.nanstd(values)

    values_filled = values.copy()
    for i in range(values_filled.shape[0]):
        row = values_filled[i]
        valid = np.where(~np.isnan(row))[0]
        if len(valid) >= 2:
            interped = np.interp(np.arange(len(row)), valid, row[valid])
            first_valid, last_valid = valid[0], valid[-1]
            values_filled[i, first_valid:last_valid+1] = interped[first_valid:last_valid+1]

    still_nan = np.isnan(values_filled)
    row_means = np.nanmean(values_filled, axis=1)
    for i in range(values_filled.shape[0]):
        values_filled[i, still_nan[i, :]] = row_means[i] if not np.isnan(row_means[i]) else 0

    smoothed = gaussian_filter(values_filled, sigma=SIGMA)

    smooth_mean = np.nanmean(smoothed)
    smooth_std = np.nanstd(smoothed)
    if smooth_std > 0:
        smoothed = (smoothed - smooth_mean) / smooth_std * orig_std + orig_mean

    fig, ax = plt.subplots(figsize=(6.5, 5.0))
    sns.heatmap(
        pd.DataFrame(smoothed, index=row_labels, columns=time_labels),
        annot=False, cmap=cmap,
        vmin=raw_vmin, vmax=raw_vmax,
        cbar_kws={'label': r'$O_2$ (%)', 'shrink': 0.8},
        xticklabels=True, yticklabels=True,
        square=False, linewidths=0.3, linecolor='#cccccc', ax=ax
    )
    ax.set_xlabel('Time (h)', fontsize=9)
    ax.set_ylabel('Well', fontsize=9)
    ax.set_title(f'{drug_name} $O_2$ — Smoothed Per-Well Heatmap',
                 fontsize=10, fontweight='bold')

    n_x = len(time_labels)
    x_step = max(1, n_x // 10)
    ax.set_xticks(range(0, n_x, x_step))
    ax.set_xticklabels([time_labels[i] for i in range(0, n_x, x_step)],
                        rotation=45, ha='right', fontsize=6)
    ax.tick_params(axis='y', labelsize=6)
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=6)

    fig.tight_layout()
    out = out_dir / f'{drug_name}_O2_heatmap_smoothed.png'
    fig.savefig(str(out), dpi=600, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out.name}')


if __name__ == '__main__':
    for drug_name, config in DRUGS.items():
        print(f'\n=== {drug_name} ===')
        make_heatmap(drug_name, config)
    print('\nDone.')
