"""Generate smoothed heatmap of Epirubicin O2 per-well data.
Each row = one well, labeled with well index and concentration.
Excludes well 1 (85% baseline outlier, same as dose-response plot).
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
OUT_DIR = BASE / 'Epirubicin'
OUT_DIR.mkdir(exist_ok=True)

KNOWN_CONCS = [12, 6, 3, 1.5, 0.75, 0.38, 0.19, 0.094]
SKIP_WELL_INDICES = {1}  # 12 mM at 85% — sensor/well error

HEATMAP_BLUE = '#123BFF'
HEATMAP_RED = '#FF2908'
SIGMA = 1.5


def clean_conc_label(label):
    s = str(label)
    for k in KNOWN_CONCS:
        ks = str(k)
        if s == ks or s.startswith(ks + '.'):
            return k
    return float(s)


def make_heatmap():
    df = pd.read_csv(OUT_DIR / 'O2_mean.csv', index_col=0)
    # df: rows = timepoints, cols = wells (concentration headers)
    # Transpose so rows = wells, cols = timepoints
    data = df.T

    # Build row labels with well index and concentration
    row_labels = []
    keep_mask = []
    for i, col in enumerate(df.columns):
        conc = clean_conc_label(col)
        if i in SKIP_WELL_INDICES:
            keep_mask.append(False)
            continue
        keep_mask.append(True)
        row_labels.append(f'W{i}: {conc} mM')

    data_filtered = data.iloc[[j for j, k in enumerate(keep_mask) if k], :]
    values = data_filtered.values.astype(float)

    # Sort by concentration (descending) then by well index within each conc
    concs = [clean_conc_label(df.columns[j]) for j, k in enumerate(keep_mask) if k]
    original_indices = [j for j, k in enumerate(keep_mask) if k]
    sort_order = sorted(range(len(concs)), key=lambda x: (-concs[x], original_indices[x]))
    values = values[sort_order]
    row_labels = [row_labels[i] for i in sort_order]

    # Time labels
    time_labels = [str(t) for t in data_filtered.columns.tolist()]

    # --- Raw heatmap ---
    cmap = LinearSegmentedColormap.from_list('cardiac_rodeo',
                                              [HEATMAP_BLUE, 'white', HEATMAP_RED])
    cmap.set_bad('white')

    raw_vmin = np.nanmin(values)
    raw_vmax = np.nanmax(values)

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
    ax.set_title(r'Epirubicin $O_2$ — Raw Per-Well Heatmap', fontsize=10, fontweight='bold')

    # Thin out x ticks
    n_x = len(time_labels)
    x_step = max(1, n_x // 10)
    ax.set_xticks(range(0, n_x, x_step))
    ax.set_xticklabels([time_labels[i] for i in range(0, n_x, x_step)],
                        rotation=45, ha='right', fontsize=6)
    ax.tick_params(axis='y', labelsize=6)

    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=6)

    fig.tight_layout()
    out = OUT_DIR / 'Epirubicin_O2_heatmap_raw.png'
    fig.savefig(str(out), dpi=600, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out.name}')

    # --- Smoothed heatmap ---
    orig_mean = np.nanmean(values)
    orig_std = np.nanstd(values)

    # Interpolate interior NaN gaps along time axis per row
    # (do NOT extrapolate leading/trailing edges)
    values_filled = values.copy()
    for i in range(values_filled.shape[0]):
        row = values_filled[i]
        valid = np.where(~np.isnan(row))[0]
        if len(valid) >= 2:
            # Interpolate between first and last valid points
            interped = np.interp(np.arange(len(row)), valid, row[valid])
            # Only fill interior — keep leading/trailing NaN
            first_valid, last_valid = valid[0], valid[-1]
            values_filled[i, first_valid:last_valid+1] = interped[first_valid:last_valid+1]

    # Fill any remaining NaN (leading/trailing) with row mean
    still_nan = np.isnan(values_filled)
    row_means = np.nanmean(values_filled, axis=1)
    for i in range(values_filled.shape[0]):
        values_filled[i, still_nan[i, :]] = row_means[i] if not np.isnan(row_means[i]) else 0

    smoothed = gaussian_filter(values_filled, sigma=SIGMA)

    # Rescale to preserve original intensity range
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
    ax.set_title(r'Epirubicin $O_2$ — Smoothed Per-Well Heatmap', fontsize=10, fontweight='bold')

    n_x = len(time_labels)
    x_step = max(1, n_x // 10)
    ax.set_xticks(range(0, n_x, x_step))
    ax.set_xticklabels([time_labels[i] for i in range(0, n_x, x_step)],
                        rotation=45, ha='right', fontsize=6)
    ax.tick_params(axis='y', labelsize=6)

    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=6)

    fig.tight_layout()
    out = OUT_DIR / 'Epirubicin_O2_heatmap_smoothed.png'
    fig.savefig(str(out), dpi=600, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out.name}')


if __name__ == '__main__':
    make_heatmap()
    print('\nDone.')
