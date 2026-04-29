"""Prism-style Fig 2 panels — re-renders for the Remake PPTX (slide 2).

Four panels live on slide 2 of `Cardiac_RODEO_Remake.pptx`. Each Prism PNG is
sized to its box exactly so PPT does no scaling and fonts stay sharp.

Panel | Box (in)    | What it shows
------|-------------|--------------------------------------------------------
2a    | 2.31 x 1.82 | Epirubicin O2 multi-line (8 doses, time 0..96 h)
2b    | 2.33 x 1.82 | Epirubicin TC50 sigmoid (Viability vs Epirubicin mM, log-x)
2d    | 2.25 x 1.74 | Mexiletine Contractility multi-line (7 doses, time 0..96 h)
2e    | 2.06 x 1.76 | Mexiletine stacked waveforms (Low/Med/High @ 48 h)

Style: Helvetica, L-spines (top/right hidden), axis labels 13 pt, ticks 9 pt.
Outputs land in `Output/PowerPoint_Figures/Fig_2/`:
    Fig_2{letter}_prism.png        — the panel image (native size = box size)
    Fig_2{letter}_prism_data.xlsx  — paired data XLSX (Plotted + Metadata)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
import matplotlib.ticker as mticker
from scipy.optimize import curve_fit

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import apply_prism_style, render_at_scale, helvetica
from _paths import panel_png, panel_data

FIG_DIR = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Fig_2"

SCALE = 4
DPI = 600
POS_BLUE = "#6C92ED"      # project Pos blue
TC50_RED = "#D6332B"      # vertical TC50 line
GREY_DASH = "#9A9A9A"     # 50% horizontal reference
BLACK = "#000000"


# ---------------------------------------------------------------------------
# Multi-line color palette — 8 doses, sequential turbo-ish (matches existing
# axisless overlays in Fig_2g.png so the visual identity is preserved).
# Order: high concentration -> dark/cool, low concentration -> light/warm.
PALETTE_8 = [
    "#1B0D7A",   # darkest blue
    "#4B1E9A",   # deep purple
    "#7E2A99",   # purple
    "#B7338F",   # magenta
    "#E0457A",   # pink-red
    "#F26B36",   # orange
    "#F8A82A",   # amber
    "#F2EE2A",   # yellow
]


# ---------------------------------------------------------------------------
# Helpers

def _setup_axes(ax, scale, *, show_xticks=True, show_yticks=True,
                ytick_length_pt=4.0):
    apply_prism_style(
        ax,
        scale=scale,
        spine_width_pt=1.2,
        hide_spines=("top", "right"),
        show_xticks=show_xticks,
        ytick_length_pt=ytick_length_pt,
        ytick_width_pt=1.0,
        tick_label_size_pt=9,
        ylabel_size_pt=13,
        xlabel_size_pt=13,
        ylabel_pad_pt=2,
        xlabel_pad_pt=2,
        clean_y_ticks=False,
        bold=False,
    )


def _layout(plot_w, plot_h, *, ml, mr, mt, mb):
    fig_w = plot_w + ml + mr
    fig_h = plot_h + mt + mb
    rect = (ml / fig_w, mb / fig_h, plot_w / fig_w, plot_h / fig_h)
    return fig_w, fig_h, rect


# ===========================================================================
# Fig 2a — Epirubicin O2 multi-line
# ===========================================================================
# Box: 2.31 x 1.82"

A_BOX_W, A_BOX_H = 2.31, 1.82
A_ML, A_MR, A_MT, A_MB = 0.50, 0.15, 0.06, 0.50
A_PLOT_W = A_BOX_W - A_ML - A_MR        # 1.66"
A_PLOT_H = A_BOX_H - A_MT - A_MB        # 1.26"


def load_2a_data():
    src = FIG_DIR / "Fig_2g_Epirubicin_O2_data.xlsx"
    df = pd.read_excel(src, sheet_name="Plotted_Data")
    df.columns = [c.strip() for c in df.columns]
    dose_cols = [c for c in df.columns if c.endswith("_mM")]
    return df, dose_cols, src


def _plot_2a(df, dose_cols):
    def _fn(fig, ax, scale):
        x = df["Time_h"].to_numpy(dtype=float)
        for col, color in zip(dose_cols, PALETTE_8):
            y = df[col].to_numpy(dtype=float)
            ax.plot(x, y, color=color, linewidth=1.0 * scale,
                    solid_capstyle="round", zorder=3)

        ax.set_xlim(0, 100)
        ax.set_ylim(0, 80)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.set_yticks([0, 10, 20, 30, 40, 50, 60, 70, 80])
        ax.set_xlabel("Time from exposure (h)")
        ax.set_ylabel("Oxygen (% Air)")
        _setup_axes(ax, scale)
    return _fn


def _save_2a_data_to(df, dose_cols, src, out):
    plotted = df[["Time_h"] + dose_cols].copy()
    metadata = pd.DataFrame([{
        "Panel": "Fig_2a (Prism)",
        "Description": "Epirubicin O2 multi-line — % Air vs Time from Exposure",
        "Source_Script": "Prism_Style/generate_fig2_panels.py",
        "Source_Data": str(src.relative_to(PROJECT_ROOT)),
        "X_Axis": "Time_h (0-96, 1000 interpolated points)",
        "Y_Axis": "Oxygen (% Air)",
        "Doses_mM": ", ".join(c.replace("_mM", "") for c in dose_cols),
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


# ===========================================================================
# Fig 2b — Epirubicin TC50 sigmoid
# ===========================================================================
# Box: 2.33 x 1.82". Log X (0.05 .. 20 mM), Y 0..100 viability.

B_BOX_W, B_BOX_H = 2.33, 1.82
B_ML, B_MR, B_MT, B_MB = 0.50, 0.15, 0.06, 0.50
B_PLOT_W = B_BOX_W - B_ML - B_MR
B_PLOT_H = B_BOX_H - B_MT - B_MB


def _hill_decreasing(x, top, bottom, ec50, hill):
    return bottom + (top - bottom) / (1.0 + (x / ec50) ** hill)


def load_2b_data():
    src = FIG_DIR / "Fig_2h_Epirubicin_TC50_data.xlsx"
    df = pd.read_excel(src, sheet_name="TC50")
    df.columns = [c.strip() for c in df.columns]
    df = df.sort_values("Concentration").reset_index(drop=True)
    tc50 = float(df["TC50_mM"].dropna().iloc[0])

    # Mean ± std at each concentration (Consumption is the viability proxy).
    x = df["Concentration"].to_numpy(dtype=float)
    y = df["Consumption"].to_numpy(dtype=float)
    yerr = df["Consumption_std"].to_numpy(dtype=float)

    # Fit a 4-parameter hill curve. Initial guesses from the data.
    p0 = [100.0, 0.0, tc50, 4.0]
    bounds = ([50, -5, 0.05, 0.5], [105, 30, 20, 12])
    try:
        popt, _ = curve_fit(_hill_decreasing, x, y, p0=p0, bounds=bounds,
                            maxfev=10000)
    except Exception:
        popt = p0
    fit_x = np.geomspace(0.05, 20.0, 400)
    fit_y = _hill_decreasing(fit_x, *popt)
    return df, x, y, yerr, fit_x, fit_y, tc50, popt, src


def _plot_2b(x, y, yerr, fit_x, fit_y, tc50):
    def _fn(fig, ax, scale):
        # 50% reference
        ax.axhline(50.0, color=GREY_DASH, linestyle="--",
                   dashes=(4, 3), linewidth=0.8 * scale, zorder=2)
        # TC50 vertical
        ax.axvline(tc50, color=TC50_RED, linestyle="--",
                   dashes=(4, 3), linewidth=1.0 * scale, zorder=3)
        # Sigmoid fit
        ax.plot(fit_x, fit_y, color=BLACK, linewidth=1.2 * scale, zorder=4)
        # Mean viability with error bars
        ax.errorbar(
            x, y,
            yerr=np.where(np.isfinite(yerr), yerr, 0.0),
            fmt="o",
            color=POS_BLUE,
            markerfacecolor=POS_BLUE,
            markeredgecolor=POS_BLUE,
            markersize=3.5 * scale,
            elinewidth=0.9 * scale,
            capsize=2.0 * scale,
            capthick=0.9 * scale,
            zorder=5,
        )

        ax.set_xscale("log")
        ax.set_xlim(0.1, 10)
        ax.set_ylim(0, 100)
        ax.set_xticks([0.1, 1, 10])
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, p: f"{v:g}"))
        ax.xaxis.set_minor_locator(mticker.LogLocator(
            base=10, subs=tuple(np.arange(2, 10) * 0.1), numticks=20))
        ax.xaxis.set_minor_formatter(mticker.NullFormatter())

        ax.set_yticks([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        ax.set_xlabel("Epirubicin (mM)")
        ax.set_ylabel("Viability (%)")
        _setup_axes(ax, scale)
        ax.tick_params(axis="x", which="minor",
                       length=2.0 * scale, width=0.8 * scale,
                       direction="out", color="black")

        ax.text(
            0.96, 0.92,
            f"TC50 = {tc50:.2f} mM",
            transform=ax.transAxes,
            ha="right", va="top",
            fontproperties=helvetica(8 * scale),
            zorder=6,
        )
    return _fn


def _save_2b_data_to(df, fit_x, fit_y, tc50, popt, src, out):
    plotted = df[["Concentration", "Consumption", "Consumption_std",
                  "O2_mean", "O2_std", "N_wells"]].copy()
    plotted.rename(columns={"Consumption": "Viability_pct",
                            "Consumption_std": "Viability_std"}, inplace=True)
    fit_df = pd.DataFrame({"Concentration_mM": fit_x, "Viability_fit_pct": fit_y})
    summary = pd.DataFrame([{
        "TC50_mM": tc50,
        "Top": popt[0], "Bottom": popt[1],
        "EC50": popt[2], "Hill": popt[3],
    }])
    metadata = pd.DataFrame([{
        "Panel": "Fig_2b (Prism)",
        "Description": "Epirubicin viability sigmoid (Hill, decreasing) with TC50",
        "Source_Script": "Prism_Style/generate_fig2_panels.py",
        "Source_Data": str(src.relative_to(PROJECT_ROOT)),
        "X_Axis": "Epirubicin (mM), log10",
        "Y_Axis": "Viability (%)",
        "Fit_Form": "bottom + (top - bottom) / (1 + (x/EC50)^hill)",
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        fit_df.to_excel(w, sheet_name="Sigmoid_Fit", index=False)
        summary.to_excel(w, sheet_name="Fit_Params", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


# ===========================================================================
# Fig 2d — Mexiletine Contractility multi-line (parallel to 2a)
# ===========================================================================
# Box: 2.25 x 1.74". 7 doses (20, 10, 5, 2.5, 1.25, 0.625, 0.156 mM).
# Data: Plotted_Data sheet of Fig_2j_Mexiletine_Contractility_data.xlsx
# Colors: plasma colormap (matches tracked Fig_2j_Mexiletine_Contractility.png).

D_BOX_W, D_BOX_H = 2.25, 1.74
D_ML, D_MR, D_MT, D_MB = 0.50, 0.18, 0.06, 0.50
D_PLOT_W = D_BOX_W - D_ML - D_MR
D_PLOT_H = D_BOX_H - D_MT - D_MB

# Plasma palette sampled at i/(N-1) for N=7 doses (high -> low).
# Matches plt.get_cmap('plasma', 7) used by plot_contractility.py.
PALETTE_PLASMA_7 = [
    "#0d0887",   # 20 mM    (i=0, dark blue)
    "#5402a3",   # 10 mM    (i=1, deep purple)
    "#8b0aa5",   # 5 mM     (i=2, magenta-purple)
    "#b83289",   # 2.5 mM   (i=3, pink)
    "#db5c68",   # 1.25 mM  (i=4, red-pink)
    "#f1834b",   # 0.625 mM (i=5, orange)
    "#f0f921",   # 0.156 mM (i=6, yellow)
]


def load_2d_data():
    src = FIG_DIR / "Fig_2j_Mexiletine_Contractility_data.xlsx"
    df = pd.read_excel(src, sheet_name="Plotted_Data")
    df.columns = [c.strip() for c in df.columns]
    dose_cols = [c for c in df.columns if c.endswith("_mM")]
    return df, dose_cols, src


def _plot_2d(df, dose_cols):
    def _fn(fig, ax, scale):
        x = df["Time_h"].to_numpy(dtype=float)
        for col, color in zip(dose_cols, PALETTE_PLASMA_7):
            y = df[col].to_numpy(dtype=float)
            ax.plot(x, y, color=color, linewidth=1.0 * scale,
                    solid_capstyle="round", zorder=3)

        ax.set_xlim(0, 100)
        ax.set_ylim(2, 12)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.set_yticks([2, 4, 6, 8, 10, 12])
        ax.set_xlabel("Time from exposure (h)")
        ax.set_ylabel("Contractility (%)")
        _setup_axes(ax, scale)
    return _fn


def _save_2d_data_to(df, dose_cols, src, out):
    plotted = df[["Time_h"] + dose_cols].copy()
    metadata = pd.DataFrame([{
        "Panel": "Fig_2d (Prism)",
        "Description": "Mexiletine Contractility multi-line — 7 doses",
        "Source_Script": "Prism_Style/generate_fig2_panels.py",
        "Source_Data": str(src.relative_to(PROJECT_ROOT)),
        "X_Axis": "Time_h (0-95, 1000 interpolated points)",
        "Y_Axis": "Contractility (%)",
        "Doses_mM": ", ".join(c.replace("_mM", "") for c in dose_cols),
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


# ===========================================================================
# Fig 2e — Mexiletine Waveforms (3 stacked traces at 48 h)
# ===========================================================================
# Box: 2.06 x 1.76". Three stacked contractility waveforms (Low/Med/High
# concentration), each with a "X mM, Y bpm" text label colored to the trace.
# Data: Plotted_Data sheet of Fig_2k_Mexiletine_Waveforms_data.xlsx.

E_BOX_W, E_BOX_H = 2.06, 1.76
E_ML, E_MR, E_MT, E_MB = 0.30, 0.10, 0.06, 0.50
E_PLOT_W = E_BOX_W - E_ML - E_MR
E_PLOT_H = E_BOX_H - E_MT - E_MB

# Plasma colors matching plot_mexiletine_waveforms.py (Low=yellow, High=purple).
WAVEFORM_LEVELS = [
    ("Low",  "#fdb42f"),   # yellow/amber, bottom waveform
    ("Med",  "#cc4778"),   # pink,         middle waveform
    ("High", "#9c179e"),   # purple,       top waveform
]


def load_2e_data():
    src = FIG_DIR / "Fig_2k_Mexiletine_Waveforms_data.xlsx"
    df = pd.read_excel(src, sheet_name="Plotted_Data")
    df.columns = [c.strip() for c in df.columns]
    return df, src


def _extract_waveform(df, level):
    """Return (time, signal, conc_mM, bpm) for one of Low/Med/High."""
    time_col = next(c for c in df.columns
                    if c.startswith(level + "_") and c.endswith("_time_s"))
    sig_col = next(c for c in df.columns
                   if c.startswith(level + "_") and c.endswith("BPM"))
    # column form: e.g. "Low_0.625mM_time_s" -> conc "0.625"
    conc_str = time_col.split("_")[1].replace("mM", "")
    bpm_str = sig_col.split("_")[-1].replace("BPM", "")
    t = df[time_col].to_numpy(dtype=float)
    s = df[sig_col].to_numpy(dtype=float)
    mask = np.isfinite(t) & np.isfinite(s)
    return t[mask], s[mask], conc_str, bpm_str


def _plot_2e(df):
    def _fn(fig, ax, scale):
        # Compute peak-to-peak per waveform for stacking spacing.
        traces = []
        for level, color in WAVEFORM_LEVELS:
            t, s, conc, bpm = _extract_waveform(df, level)
            traces.append((level, color, t, s, conc, bpm))
        amplitudes = [np.ptp(s) for (_, _, _, s, _, _) in traces]
        max_amp = max(amplitudes) if amplitudes else 1.0
        spacing = max_amp * 1.5

        for i, (level, color, t, s, conc, bpm) in enumerate(traces):
            offset = i * spacing
            ax.plot(t, s + offset, color=color,
                    linewidth=1.0 * scale, alpha=0.95, zorder=3)
            # Concentration + BPM label, colored to match the trace,
            # placed at the top-left of each trace.
            y_peak = float(np.max(s + offset))
            ax.text(0.10, y_peak + spacing * 0.10,
                    f"{conc} mM, {bpm} bpm",
                    fontproperties=helvetica(7 * scale),
                    color=color, va="bottom", ha="left",
                    zorder=4)

        ax.set_xlim(0, 7)
        # Reserve headroom above topmost label, room below bottom waveform.
        ax.set_ylim(-spacing * 0.5, spacing * 2.85)
        ax.set_xticks([0, 1, 2, 3, 4, 5, 6, 7])
        ax.set_yticks([])
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Contractility")
        _setup_axes(ax, scale, ytick_length_pt=0.0)
        # Hide the y-axis tick marks entirely (no values shown).
        ax.tick_params(axis="y", which="both", left=False, right=False)
    return _fn


def _save_2e_data_to(df, src, out):
    metadata = pd.DataFrame([{
        "Panel": "Fig_2e (Prism)",
        "Description": "Mexiletine stacked waveforms — 3 doses at 48 h",
        "Source_Script": "Prism_Style/generate_fig2_panels.py",
        "Source_Data": str(src.relative_to(PROJECT_ROOT)),
        "X_Axis": "Time (s), 0-7",
        "Y_Axis": "Contractility (mV, stacked with offset)",
        "Levels": "Low (0.625 mM, 59 BPM), Med (2.5 mM, 73 BPM), High (5.0 mM, 119 BPM)",
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Plotted", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


# ===========================================================================
# Driver
# ===========================================================================

def main():
    from PIL import Image
    panels_done = []

    # Panels a and b save directly to the tracked figures folder (not Remake).
    OUT_DIR = FIG_DIR

    # ---- 2a ----
    a_df, a_dose_cols, a_src = load_2a_data()
    a_w, a_h, a_rect = _layout(A_PLOT_W, A_PLOT_H,
                                ml=A_ML, mr=A_MR, mt=A_MT, mb=A_MB)
    out_a = OUT_DIR / "Fig_2a_prism.png"
    data_a = OUT_DIR / "Fig_2a_prism_data.xlsx"
    render_at_scale(_plot_2a(a_df, a_dose_cols), (a_w, a_h), out_a,
                    scale=SCALE, dpi=DPI, transparent=True, axes_rect=a_rect)
    _save_2a_data_to(a_df, a_dose_cols, a_src, data_a)
    panels_done.append(("a", out_a, data_a, a_w, a_h))

    # ---- 2b ----
    b_df, bx, by, byerr, bfx, bfy, b_tc50, b_popt, b_src = load_2b_data()
    b_w, b_h, b_rect = _layout(B_PLOT_W, B_PLOT_H,
                                ml=B_ML, mr=B_MR, mt=B_MT, mb=B_MB)
    out_b = OUT_DIR / "Fig_2b_prism.png"
    data_b = OUT_DIR / "Fig_2b_prism_data.xlsx"
    render_at_scale(_plot_2b(bx, by, byerr, bfx, bfy, b_tc50), (b_w, b_h),
                    out_b, scale=SCALE, dpi=DPI, transparent=True,
                    axes_rect=b_rect)
    _save_2b_data_to(b_df, bfx, bfy, b_tc50, b_popt, b_src, data_b)
    panels_done.append(("b", out_b, data_b, b_w, b_h))

    # ---- 2d ----
    d_df, d_dose_cols, d_src = load_2d_data()
    d_w, d_h, d_rect = _layout(D_PLOT_W, D_PLOT_H,
                                ml=D_ML, mr=D_MR, mt=D_MT, mb=D_MB)
    out_d = OUT_DIR / "Fig_2d_prism.png"
    data_d = OUT_DIR / "Fig_2d_prism_data.xlsx"
    render_at_scale(_plot_2d(d_df, d_dose_cols), (d_w, d_h), out_d,
                    scale=SCALE, dpi=DPI, transparent=True, axes_rect=d_rect)
    _save_2d_data_to(d_df, d_dose_cols, d_src, data_d)
    panels_done.append(("d", out_d, data_d, d_w, d_h))

    # ---- 2e ----
    e_df, e_src = load_2e_data()
    e_w, e_h, e_rect = _layout(E_PLOT_W, E_PLOT_H,
                                ml=E_ML, mr=E_MR, mt=E_MT, mb=E_MB)
    out_e = OUT_DIR / "Fig_2e_prism.png"
    data_e = OUT_DIR / "Fig_2e_prism_data.xlsx"
    render_at_scale(_plot_2e(e_df), (e_w, e_h), out_e,
                    scale=SCALE, dpi=DPI, transparent=True, axes_rect=e_rect)
    _save_2e_data_to(e_df, e_src, data_e)
    panels_done.append(("e", out_e, data_e, e_w, e_h))

    # ---- Report ----
    for letter, png, xlsx, w, h in panels_done:
        im = Image.open(png)
        dpi = im.info.get("dpi", (DPI, DPI))[0]
        print(f"[2{letter}] -> {png.relative_to(PROJECT_ROOT)}")
        print(f"    image  : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\""
              f"  (target {w:.2f}\" x {h:.2f}\")")
        print(f"    data   : {xlsx.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
