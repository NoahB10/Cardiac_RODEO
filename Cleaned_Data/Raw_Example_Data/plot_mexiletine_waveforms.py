"""Plot Mexiletine stacked waveforms for Figure 2.
Shorter aspect ratio, concentration labels above x-axis (green→red bottom to top),
larger fonts. Saves to both local and Fig_2 folder.
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2]))

import figure_config
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from matplotlib.lines import Line2D
from pathlib import Path

BASE = Path(__file__).resolve().parent / 'Mexiletine'
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WAVEFORM_DATA_DIR = PROJECT_ROOT / 'Output' / '2D_Raw_Plots' / 'Raw_Example_Outputs' / 'Mexiletine'
FIG2_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures' / 'Fig_2'
FIG2_DIR.mkdir(parents=True, exist_ok=True)

SAVE_DPI = 600

# Colors: green (low) -> orange (med) -> red (high), bottom to top
LEVEL_COLORS = {'High': '#d62728', 'Med': '#ff7f0e', 'Low': '#2ca02c'}
LEVEL_ORDER = ['Low', 'Med', 'High']  # bottom to top


def load_and_plot(xlsx_path, option_label, is_main=False):
    """Load waveform data and create stacked plot."""
    summary = pd.read_excel(xlsx_path, sheet_name='Summary')

    # Build level -> (time, signal, bpm, conc_mM)
    waveforms = {}
    for _, row in summary.iterrows():
        level = row['Level']
        conc = row['Concentration_mM']
        bpm = row['BPM']
        sheet = f"{level}_{conc}mM_{row['Well']}"

        df = pd.read_excel(xlsx_path, sheet_name=sheet)
        t = df['time_s'].values
        sig = df['amp1_vpp_filtered'].values * 1000  # mV

        # Spline smooth
        if len(t) >= 4:
            t_fine = np.linspace(t[0], t[-1], 800)
            sig_fine = CubicSpline(t, sig)(t_fine)
        else:
            t_fine, sig_fine = t, sig

        waveforms[level] = (t_fine, sig_fine, bpm, conc)

    # Compute spacing from max amplitude
    amplitudes = {k: np.ptp(v[1]) for k, v in waveforms.items()}
    max_amp = max(amplitudes.values()) if amplitudes else 1.0
    spacing = max_amp * 1.5

    # Time window: focus on 5-12s of recording, display as 0-7s
    T_START, T_END = 5.0, 12.0
    T_DURATION = T_END - T_START

    # Figure: wide and short
    fig, ax = plt.subplots(figsize=(10, 4.5))

    for i, level in enumerate(LEVEL_ORDER):
        if level not in waveforms:
            continue
        t_fine, sig_fine, bpm, conc = waveforms[level]

        # Clip to window and shift to start at 0
        mask = (t_fine >= T_START) & (t_fine <= T_END)
        t_clip = t_fine[mask] - T_START
        s_clip = sig_fine[mask]

        offset = i * spacing
        color = LEVEL_COLORS[level]

        ax.plot(t_clip, s_clip + offset, color=color, linewidth=1.8, alpha=0.9)

        # Dose + BPM label on top-left of each trace
        y_peak = np.max(s_clip + offset)
        ax.text(0.1, y_peak + spacing * 0.08,
                f'{conc} mM, {bpm:.0f} bpm',
                fontsize=24, fontweight='bold', color=color,
                va='bottom', ha='left')

    ax.set_xlim(0, T_DURATION)
    ax.set_ylim(-spacing * 0.5, spacing * 2.8)
    ax.set_xlabel('Time (s)', fontsize=30, fontweight='bold')
    ax.set_ylabel('Contractility', fontsize=30, fontweight='bold')
    ax.tick_params(labelsize=24, width=1.5)
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(3.0)
    ax.spines['left'].set_linewidth(3.0)

    # Save
    suffix = '_main' if is_main else f'_{option_label.replace(" ", "_")}'
    out_local = BASE / f'Mexiletine_Waveforms{suffix}.png'
    fig.savefig(out_local, dpi=SAVE_DPI, bbox_inches='tight',
                pad_inches=0.05, facecolor='white')
    print(f'Saved: {out_local.name}')

    if is_main:
        out_fig2 = FIG2_DIR / 'Fig_2k_Mexiletine_Waveforms.png'
    else:
        out_fig2 = FIG2_DIR / f'Fig_2k_Mexiletine_Waveforms_{option_label.replace(" ", "_")}_option.png'
    fig.savefig(out_fig2, dpi=SAVE_DPI, bbox_inches='tight',
                pad_inches=0.05, facecolor='white')
    print(f'Saved: {out_fig2.name}')

    plt.close(fig)

    # Save processed waveform data for Excel provenance
    if is_main:
        T_START_W, T_END_W = 5.0, 12.0
        processed_frames = []
        for level in LEVEL_ORDER:
            if level not in waveforms:
                continue
            t_fine, sig_fine, bpm, conc = waveforms[level]
            mask = (t_fine >= T_START_W) & (t_fine <= T_END_W)
            t_clip = t_fine[mask] - T_START_W
            s_clip = sig_fine[mask]
            frame = pd.DataFrame({
                f'{level}_{conc}mM_time_s': t_clip,
                f'{level}_{conc}mM_{bpm:.0f}BPM': s_clip,
            })
            processed_frames.append(frame)
        if processed_frames:
            processed_df = pd.concat(processed_frames, axis=1)
            processed_csv = BASE / 'Mexiletine_Waveforms_processed.csv'
            processed_df.to_csv(processed_csv, index=False)
            print(f'Saved processed data: {processed_csv.name}')

    return out_fig2


if __name__ == '__main__':
    # Option 2 = main (Med=2.5 mM), Option 4 = alternative (Med=1.25 mM)
    opt2 = WAVEFORM_DATA_DIR / 'Mexiletine_DoseResponse_48h_Option2.xlsx'
    opt4 = WAVEFORM_DATA_DIR / 'Mexiletine_DoseResponse_48h_Option4.xlsx'

    print('=== Option 2 (main) ===')
    load_and_plot(opt2, 'Option 2', is_main=True)

    print('\n=== Option 4 (alternative) ===')
    load_and_plot(opt4, 'Option 4', is_main=False)

    print('\nDone.')
