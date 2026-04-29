"""Generate 3-panel waveform plots with stacked traces (2-peak window)."""
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
SKIP_EDGE = 1.5
SHOW_SECONDS = 8.0  # match the original overlaid plot window

# ======================== FILTERING (same as before) ========================

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

def process_drug(drug_name, xlsx_override=None):
    """Process with halfpower_adaptive, return per-(timepoint, level) waveforms."""
    fname = xlsx_override or f'{drug_name}_DoseResponse_Waveforms'
    path = BASE / f'{fname}.xlsx'
    summary = pd.read_excel(path, sheet_name='Summary')

    sheet_col = 'Sheet' if 'Sheet' in summary.columns else 'Sheet_Name'
    level_col = 'Level' if 'Level' in summary.columns else None

    conc_values = {}
    for _, row in summary.iterrows():
        label = row['Concentration']
        numeric = float(str(label).replace('mM', '').replace('_', '.'))
        conc_values[label] = numeric

    unique_concs = sorted(set(conc_values.values()), reverse=True)

    if level_col:
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

        df = pd.read_excel(path, sheet_name=row[sheet_col])
        time_s = df['time_s'].values
        signal_raw = df['amp1_vpp_raw'].values

        # Half-power adaptive filtering
        signal_wide = bandpass_filter_signal(time_s, signal_raw)
        dom_freq = compute_dominant_frequency(time_s, signal_wide)
        dom_freq_corr, _ = detect_harmonic_doubling(time_s, signal_raw, dom_freq)
        hp_bw = get_half_power_bandwidth(time_s, signal_raw, dom_freq_corr)
        signal_filtered = narrow_bandpass_around_peak(
            time_s, signal_raw, peak_freq=dom_freq_corr, bandwidth=hp_bw)
        bpm = dom_freq_corr * 60

        # Period for this trace (seconds per beat)
        period = 60.0 / bpm if bpm > 0 else 1.0

        # Same windowing as original overlaid plot: skip 1.5s, show 8s
        order = np.argsort(time_s)
        time_sorted = time_s[order]
        t0 = time_sorted[0] + SKIP_EDGE
        mask = (time_sorted >= t0) & (time_sorted <= t0 + SHOW_SECONDS)
        t_show = time_sorted[mask] - t0  # zero-based
        f_show = signal_filtered[mask] * 1000  # mV

        if len(t_show) >= 4:
            t_fine = np.linspace(t_show[0], t_show[-1], 600)
            f_fine = CubicSpline(t_show, f_show)(t_fine)
        else:
            t_fine, f_fine = t_show, f_show

        waveform_data[(tp, level)] = (t_fine, f_fine, bpm, period)

    return waveform_data, timepoints, unique_concs


# ======================== PLOTTING ========================

conc_colors = {'High': '#d62728', 'Med': '#ff7f0e', 'Low': '#2ca02c'}
level_order = ['Low', 'Med', 'High']  # bottom to top


def make_conc_label(val):
    if val >= 1:
        return f'{val:.0f}' if val == int(val) else f'{val:.1f}'
    return f'{val:.3g}'


def plot_drug_stacked(drug_name, waveform_data, timepoints, conc_mM_values,
                      clip_windows=None):
    """clip_windows: dict mapping timepoint -> (t_start, t_end) in the 8s coordinate system."""
    tp_labels = [tp.replace('h', '') + ' h' for tp in timepoints]

    level_to_mM = {}
    for i, val in enumerate(sorted(conc_mM_values, reverse=True)[:3]):
        level_to_mM[['High', 'Med', 'Low'][i]] = val

    # Find the max x-extent across all panels (each trace has its own length)
    max_x = 0
    for key, (t, f, bpm, per) in waveform_data.items():
        if len(t) > 0:
            max_x = max(max_x, t[-1])

    # Compute per-trace amplitudes to set spacing
    amplitudes = {}
    for key, (t, f, bpm, per) in waveform_data.items():
        amplitudes[key] = np.ptp(f) if len(f) > 0 else 0
    max_amp = max(amplitudes.values()) if amplitudes else 1.0
    spacing = max_amp * 1.5  # gap between stacked traces

    fig = plt.figure(figsize=(2.3, 2.3))
    gs = gridspec.GridSpec(1, 3, wspace=0.55, left=0.12, right=0.95,
                           top=0.78, bottom=0.12)
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]

    for panel_idx, (tp, tp_label) in enumerate(zip(timepoints, tp_labels)):
        ax = axes[panel_idx]

        # Determine clip window for this timepoint
        if clip_windows and tp in clip_windows:
            clip_start, clip_end = clip_windows[tp]
        else:
            clip_start, clip_end = 0, SHOW_SECONDS
        clip_duration = clip_end - clip_start

        for i, level in enumerate(level_order):
            if (tp, level) not in waveform_data:
                continue
            t_fine, f_fine, bpm, period = waveform_data[(tp, level)]
            # Clip to window, re-zero time
            cmask = (t_fine >= clip_start) & (t_fine <= clip_end)
            t_clip = t_fine[cmask] - clip_start
            f_clip = f_fine[cmask]
            offset = i * spacing
            ax.plot(t_clip, f_clip + offset, color=conc_colors[level],
                    linewidth=1.2, alpha=0.9)

            # BPM label to the right of the trace
            if len(t_clip) > 0:
                ax.text(t_clip[-1] + 0.02, offset, f'{bpm:.0f}\nBPM',
                        fontsize=5.5, fontweight='bold', color=conc_colors[level],
                        va='center', ha='left', clip_on=False)

        ax.set_xlim(0, clip_duration)
        ax.set_ylim(-spacing * 0.6, spacing * 2.8)
        ax.set_title(tp_label, fontsize=9, fontweight='bold')
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.set_xticks([0, clip_duration])
        ax.tick_params(labelsize=6)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        if panel_idx == 0:
            ax.set_ylabel('Contractility (mV)', fontsize=8)
            # Show y-ticks only on first panel — but since traces are offset,
            # remove numerical y-ticks and just label the levels
            ax.set_yticks([i * spacing for i in range(3)])
            ax.set_yticklabels([])
        else:
            ax.set_yticks([])

    # Legend
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

    fig.suptitle(f'{drug_name.title()} — Stacked Waveforms',
                 fontsize=10, fontweight='bold', y=1.06)

    out_path = BASE / f'{drug_name}_Stacked.png'
    fig.savefig(out_path, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved: {out_path}')
    return out_path


# ======================== MAIN ========================

if __name__ == '__main__':
    drug = 'doxorubicin'
    xlsx_name = 'doxorubicin_DoseResponse_Option8'
    print(f'Processing {drug} (Option8: 6h/27h/82h)...')
    waveform_data, timepoints, conc_values = process_drug(drug, xlsx_override=xlsx_name)
    for key, (t, f, bpm, per) in waveform_data.items():
        print(f'  {key}: BPM={bpm:.1f}, period={per:.2f}s, window={t[-1]:.2f}s, amp={np.ptp(f):.2f} mV')
    clip_windows = {
        '6h': (5.5, 7.0),
        '27h': (4.0, 5.5),
        '82h': (4.5, 6.0),
    }
    plot_drug_stacked(drug, waveform_data, timepoints, conc_values,
                      clip_windows=clip_windows)
