"""Generate 3-panel waveform plots for all drugs × 2 filtering methods."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[3]))

import figure_config
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy.fft import fft, ifft, fftfreq
from scipy.signal import welch
from scipy.interpolate import CubicSpline
from matplotlib.lines import Line2D
from pathlib import Path

BASE = Path(__file__).resolve().parent
SHOW_SECONDS = 8.0
SKIP_EDGE = 1.5

# ======================== FILTERING FUNCTIONS ========================

def bandpass_filter_signal(time_s, signal, freq_band=(0.5, 2.0)):
    if len(signal) < 4:
        return signal
    signal_detrended = signal - np.nanmean(signal)
    order = np.argsort(time_s)
    signal_sorted = signal_detrended[order]
    dt = np.median(np.diff(time_s[order]))
    if dt <= 0:
        return signal
    signal_fft = fft(signal_sorted)
    freqs = fftfreq(len(signal_sorted), dt)
    signal_fft[(np.abs(freqs) < freq_band[0]) | (np.abs(freqs) > freq_band[1])] = 0
    return np.real(ifft(signal_fft))


def compute_dominant_frequency(time_s, signal, freq_band=(0.5, 2.0)):
    order = np.argsort(time_s)
    dt = np.median(np.diff(time_s[order]))
    freqs_w, power = welch((signal - np.nanmean(signal))[order],
                           fs=1.0/dt, nperseg=min(256, len(signal)))
    band_mask = (freqs_w >= freq_band[0]) & (freqs_w <= freq_band[1])
    if not band_mask.any():
        return np.nan
    return freqs_w[band_mask][np.argmax(power[band_mask])]


def detect_harmonic_doubling(time_s, signal, detected_freq, freq_band=(0.5, 2.0)):
    if np.isnan(detected_freq):
        return detected_freq, False
    order = np.argsort(time_s)
    dt = np.median(np.diff(time_s[order]))
    freqs_w, power = welch((signal - np.nanmean(signal))[order],
                           fs=1.0/dt, nperseg=min(256, len(signal)))
    peak_mask = (freqs_w >= detected_freq - 0.05) & (freqs_w <= detected_freq + 0.05)
    if not peak_mask.any():
        return detected_freq, False
    peak_power = np.max(power[peak_mask])
    half_freq = detected_freq / 2.0
    if half_freq >= freq_band[0]:
        half_mask = (freqs_w >= half_freq - 0.05) & (freqs_w <= half_freq + 0.05)
        if half_mask.any() and np.max(power[half_mask]) / peak_power > 0.7:
            return half_freq, True
    return detected_freq, False


def get_half_power_bandwidth(time_s, signal, peak_freq, freq_band=(0.5, 2.0)):
    if np.isnan(peak_freq) or len(signal) < 4:
        return 0.2
    order = np.argsort(time_s)
    dt = np.median(np.diff(time_s[order]))
    freqs_w, power = welch((signal - np.nanmean(signal))[order],
                           fs=1.0/dt, nperseg=min(256, len(signal)))
    peak_mask = (freqs_w >= peak_freq - 0.1) & (freqs_w <= peak_freq + 0.1)
    if not peak_mask.any():
        return 0.2
    half_power = np.max(power[peak_mask]) / 2.0
    hp_mask = ((freqs_w >= freq_band[0]) & (freqs_w <= freq_band[1])
               & (power >= half_power))
    if not hp_mask.any():
        return 0.2
    return np.clip((np.max(freqs_w[hp_mask]) - np.min(freqs_w[hp_mask])) / 2.0,
                   0.05, 1.0)


def narrow_bandpass_around_peak(time_s, signal, peak_freq, bandwidth=0.2):
    if len(signal) < 4:
        return signal
    signal_detrended = signal - np.nanmean(signal)
    order = np.argsort(time_s)
    signal_sorted = signal_detrended[order]
    dt = np.median(np.diff(time_s[order]))
    signal_fft = fft(signal_sorted)
    freqs = fftfreq(len(signal_sorted), dt)
    signal_fft[((np.abs(freqs) < peak_freq - bandwidth)
                | (np.abs(freqs) > peak_freq + bandwidth))] = 0
    return np.real(ifft(signal_fft))


# ======================== PROCESSING ========================

def process_drug(drug_name, method):
    path = BASE / f'{drug_name}_DoseResponse_Waveforms.xlsx'
    summary = pd.read_excel(path, sheet_name='Summary')

    # Handle both column naming conventions
    sheet_col = 'Sheet' if 'Sheet' in summary.columns else 'Sheet_Name'
    level_col = 'Level' if 'Level' in summary.columns else None

    # Map concentration labels to High/Med/Low
    conc_values = {}
    for _, row in summary.iterrows():
        label = row['Concentration']
        numeric = float(str(label).replace('mM', '').replace('_', '.'))
        conc_values[label] = numeric

    unique_concs = sorted(set(conc_values.values()), reverse=True)

    if level_col:
        # Level column already exists
        conc_to_level = {}
        for _, row in summary.iterrows():
            conc_to_level[row['Concentration']] = row[level_col]
    else:
        conc_to_level = {}
        level_names = ['High', 'Med', 'Low']
        for i, val in enumerate(unique_concs[:3]):
            for label, v in conc_values.items():
                if v == val:
                    conc_to_level[label] = level_names[i]

    timepoints = sorted(summary['Timepoint'].unique(),
                        key=lambda x: float(str(x).replace('h', '')))

    waveform_data = {}

    for _, row in summary.iterrows():
        level = conc_to_level.get(row['Concentration'], row['Concentration'])
        tp = row['Timepoint']
        bpm_summary = row['BPM']

        df = pd.read_excel(path, sheet_name=row[sheet_col])
        time_s = df['time_s'].values
        signal_raw = df['amp1_vpp_raw'].values

        if method == 'wide_bandpass':
            signal_filtered = bandpass_filter_signal(time_s, signal_raw)
            bpm = bpm_summary
        elif method == 'halfpower_adaptive':
            signal_wide = bandpass_filter_signal(time_s, signal_raw)
            dom_freq = compute_dominant_frequency(time_s, signal_wide)
            dom_freq_corr, _ = detect_harmonic_doubling(time_s, signal_raw, dom_freq)
            hp_bw = get_half_power_bandwidth(time_s, signal_raw, dom_freq_corr)
            signal_filtered = narrow_bandpass_around_peak(
                time_s, signal_raw, peak_freq=dom_freq_corr, bandwidth=hp_bw)
            bpm = dom_freq_corr * 60

        # Trim and spline smooth
        order = np.argsort(time_s)
        time_sorted = time_s[order]
        t0 = time_sorted[0] + SKIP_EDGE
        mask = (time_sorted >= t0) & (time_sorted <= t0 + SHOW_SECONDS)
        t_show = time_sorted[mask] - t0
        f_show = signal_filtered[mask] * 1000  # mV

        if len(t_show) >= 4:
            t_fine = np.linspace(t_show[0], t_show[-1], 800)
            f_fine = CubicSpline(t_show, f_show)(t_fine)
        else:
            t_fine, f_fine = t_show, f_show

        waveform_data[(tp, level)] = (t_fine, f_fine, bpm)

    return waveform_data, timepoints, unique_concs


# ======================== PLOTTING ========================

conc_colors = {'High': '#d62728', 'Med': '#ff7f0e', 'Low': '#2ca02c'}
conc_order_plot = ['High', 'Med', 'Low']
bpm_label_order = ['Low', 'Med', 'High']


def make_conc_label(val):
    if val >= 1:
        return f'{val:.0f}' if val == int(val) else f'{val:.1f}'
    return f'{val:.3g}'


def plot_drug(drug_name, waveform_data, timepoints, conc_mM_values,
              method_label, method_suffix):
    tp_labels = []
    for tp in timepoints:
        h = tp.replace('h', '')
        tp_labels.append(f'{h} h')
    # No baseline suffix — just the time label

    level_to_mM = {}
    for i, val in enumerate(sorted(conc_mM_values, reverse=True)[:3]):
        level_to_mM[['High', 'Med', 'Low'][i]] = val

    all_min = min(d[1].min() for d in waveform_data.values())
    all_max = max(d[1].max() for d in waveform_data.values())
    y_pad = (all_max - all_min) * 0.18
    y_lo, y_hi = all_min - y_pad, all_max + y_pad

    fig = plt.figure(figsize=(6.5, 2.2))
    gs = gridspec.GridSpec(1, 3, wspace=0.08, left=0.09, right=0.98,
                           top=0.78, bottom=0.20)
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]

    for panel_idx, (tp, tp_label) in enumerate(zip(timepoints, tp_labels)):
        ax = axes[panel_idx]
        for level in conc_order_plot:
            if (tp, level) not in waveform_data:
                continue
            t_fine, f_fine, _ = waveform_data[(tp, level)]
            ax.plot(t_fine, f_fine, color=conc_colors[level],
                    linewidth=1.0, alpha=0.9)

        ax.set_xlim(0, SHOW_SECONDS)
        ax.set_ylim(y_lo, y_hi)
        ax.set_title(tp_label, fontsize=9, fontweight='bold')
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if panel_idx == 0:
            ax.set_ylabel('Contractility (mV)', fontsize=8)
        else:
            ax.set_yticklabels([])

        x_positions = [0.17, 0.5, 0.83]
        for level, xp in zip(bpm_label_order, x_positions):
            if (tp, level) in waveform_data:
                _, _, bpm = waveform_data[(tp, level)]
                ax.text(xp, 0.02, f'{bpm:.0f} BPM', transform=ax.transAxes,
                        fontsize=6, fontweight='bold', color=conc_colors[level],
                        ha='center', va='bottom')

    legend_elements = [
        Line2D([0], [0], color=conc_colors['High'], lw=1.5,
               label=f'High ({make_conc_label(level_to_mM["High"])} mM)'),
        Line2D([0], [0], color=conc_colors['Med'], lw=1.5,
               label=f'Med ({make_conc_label(level_to_mM["Med"])} mM)'),
        Line2D([0], [0], color=conc_colors['Low'], lw=1.5,
               label=f'Low ({make_conc_label(level_to_mM["Low"])} mM)'),
    ]
    fig.legend(handles=legend_elements, loc='upper center', ncol=3, fontsize=7,
               bbox_to_anchor=(0.53, 0.98), frameon=False,
               handlelength=1.5, columnspacing=1.5)

    title = f'{drug_name.title()} \u2014 {method_label}'
    fig.suptitle(title, fontsize=10, fontweight='bold', y=1.06)

    out_path = BASE / f'{drug_name}_{method_suffix}.png'
    fig.savefig(out_path, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'  Saved: {out_path.name}')


# ======================== MAIN ========================

if __name__ == '__main__':
    drugs = ['chlorpromazine', 'cobimetinib', 'daunorubicin',
             'doxorubicin', 'epirubicin']

    methods = [
        ('wide_bandpass', 'Wide Bandpass (0.5-2.0 Hz)', 'WideBandpass'),
        ('halfpower_adaptive', 'Half-Power Adaptive Bandwidth', 'HalfPowerAdaptive'),
    ]

    for drug in drugs:
        print(f'\n=== {drug.upper()} ===')
        for method_key, method_label, method_suffix in methods:
            waveform_data, timepoints, conc_values = process_drug(drug, method_key)
            plot_drug(drug, waveform_data, timepoints, conc_values,
                      method_label, method_suffix)

    print('\nDone! All plots saved.')
