"""
Replot Vandetanib heatmaps:
 1. Restore originals (raw per-well data) → Fig_3a_1.png, Fig_3a_2.png
 2. Generate smoothed versions (averaged + Gaussian) → Fig_3a_1_smoothed.png, Fig_3a_2_smoothed.png
    - No titles on smoothed versions
    - Same graphical settings as originals
"""

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
HEATMAP_DIR = PROJECT_ROOT / 'Cleaned_Data' / 'Heatmaps' / 'Vandetanib (G11)'
OUT_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures' / 'Fig_3'
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEATMAP_BLUE = '#123BFF'
HEATMAP_RED = '#FF2908'
HEATMAP_WIDTH = 3.1

cmap = LinearSegmentedColormap.from_list('cardiac_rodeo', [HEATMAP_BLUE, 'white', HEATMAP_RED])
cmap.set_bad('white')


def clean_concentration_labels(labels):
    """Clean pandas-disambiguated concentration labels (e.g. '0.5.1' → '0.5', '8.1' → '8')."""
    known_concs = {8, 4, 2, 1, 0.5, 0.25, 0.125, 0.062}
    cleaned = []
    for label in labels:
        s = str(label)
        # Try as-is first
        try:
            v = float(s)
            if v in known_concs:
                cleaned.append(str(v))
                continue
        except ValueError:
            pass
        # Strip trailing pandas suffix: '0.5.1' → '0.5', '8.2' → '8'
        # Try removing last '.N' where N is a digit
        m = re.match(r'^(.+)\.(\d+)$', s)
        if m:
            base = m.group(1)
            try:
                v = float(base)
                if v in known_concs:
                    cleaned.append(str(v))
                    continue
            except ValueError:
                pass
        cleaned.append(s)
    return cleaned


def get_true_concentrations(csv_path):
    """Read the first line of the CSV to get the original concentration values before pandas disambiguation."""
    with open(csv_path, 'r') as f:
        header = f.readline().strip()
    # First field is empty (index column), rest are concentrations
    parts = header.split(',')[1:]
    return [float(p) for p in parts]


def load_raw(csv_path):
    """Load CSV and transpose (raw per-well, no averaging)."""
    data_raw = pd.read_csv(csv_path, index_col=0)
    data = data_raw.T
    return data


def load_smoothed(csv_path, sigma=1.5):
    """Load CSV and apply Gaussian smoothing. Same rows/cols as raw — no merging.
    Rescales smoothed data to preserve the original intensity range."""
    data_raw = pd.read_csv(csv_path, index_col=0)
    data = data_raw.T  # same structure as load_raw

    # Apply Gaussian smoothing (handle NaN)
    values = data.values.astype(float)
    nan_mask = np.isnan(values)

    # Remember original stats for rescaling
    orig_mean = np.nanmean(values)
    orig_std = np.nanstd(values)

    # Fill NaN temporarily with row mean for smoothing
    row_means = np.nanmean(values, axis=1)
    for i in range(values.shape[0]):
        values[i, nan_mask[i, :]] = row_means[i] if not np.isnan(row_means[i]) else 0

    smoothed = gaussian_filter(values, sigma=sigma)

    # Rescale: match mean and std of original data so intensity is preserved
    smooth_mean = np.nanmean(smoothed)
    smooth_std = np.nanstd(smoothed)
    if smooth_std > 0:
        smoothed = (smoothed - smooth_mean) / smooth_std * orig_std + orig_mean

    smoothed[nan_mask] = np.nan

    return pd.DataFrame(smoothed, index=data.index, columns=data.columns)


def plot_heatmap(data, title_label, out_path, y_labels, show_title=True,
                 vmin=None, vmax=None):
    """Plot a heatmap with the standard Fig_3a graphical settings."""
    x_labels = [str(t) for t in data.columns.tolist()]
    heatmap_w = HEATMAP_WIDTH * 1.6

    fig, ax = plt.subplots(figsize=(heatmap_w, HEATMAP_WIDTH * 0.6))

    sns.heatmap(
        data, annot=False, cmap=cmap,
        vmin=vmin, vmax=vmax,
        cbar_kws={'label': title_label, 'shrink': 0.8},
        xticklabels=x_labels, yticklabels=y_labels,
        square=True, linewidths=0, ax=ax
    )

    ax.set_xlabel('Time (h)', fontsize=6)
    ax.set_ylabel('Conc (mM)', fontsize=6)

    if show_title:
        ax.set_title(f'Vandetanib {title_label}', fontsize=7, fontweight='bold')

    # Reduce x tick density
    n_x = len(x_labels)
    x_step = max(1, n_x // 8)
    ax.set_xticks(range(0, n_x, x_step))
    ax.set_xticklabels([x_labels[i] for i in range(0, n_x, x_step)],
                        rotation=45, ha='right', fontsize=5)

    # Y ticks
    n_y = len(y_labels)
    y_step = max(1, n_y // 6)
    ax.set_yticks(range(0, n_y, y_step))
    ax.set_yticklabels([y_labels[i] for i in range(0, n_y, y_step)],
                        fontsize=5, rotation=0)

    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=5)
    cbar.set_label(title_label, fontsize=5)

    fig.tight_layout()
    fig.savefig(str(out_path), dpi=600, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


# ---- Generate both versions ----
heatmap_files = [
    ('O2_mean.csv', 'O2 Mean', 'Fig_3a_1'),
    ('Amp_std.csv', 'Contractility', 'Fig_3a_2'),
]

for fname, title_label, base_name in heatmap_files:
    fpath = HEATMAP_DIR / fname
    if not fpath.exists():
        print(f"  Warning: {fpath} not found")
        continue

    # --- Original (raw per-well) ---
    raw_data = load_raw(fpath)
    raw_y_labels = clean_concentration_labels(raw_data.index.tolist())
    plot_heatmap(raw_data, title_label,
                 OUT_DIR / f'{base_name}.png',
                 raw_y_labels, show_title=True)

    # Lock color scale to the raw data range
    raw_vmin = np.nanmin(raw_data.values.astype(float))
    raw_vmax = np.nanmax(raw_data.values.astype(float))

    # --- Smoothed (Gaussian filter only, same rows, same color scale) ---
    smooth_data = load_smoothed(fpath, sigma=1.5)
    smooth_y_labels = clean_concentration_labels(smooth_data.index.tolist())
    plot_heatmap(smooth_data, title_label,
                 OUT_DIR / f'{base_name}_smoothed.png',
                 smooth_y_labels, show_title=False,
                 vmin=raw_vmin, vmax=raw_vmax)

print("\nDone — originals restored, smoothed versions saved separately.")
