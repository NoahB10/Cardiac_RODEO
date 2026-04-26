"""Prism-style Fig 2 panels — re-renders for the Remake PPTX (slide 2).

Four panels live on slide 2 of `Cardiac_RODEO_Remake.pptx`. Each Prism PNG is
sized to its box exactly so PPT does no scaling and fonts stay sharp.

Panel | Box (in)    | What it shows
------|-------------|--------------------------------------------------------
2a    | 2.31 x 1.82 | Epirubicin O2 multi-line (8 doses, time 0..96 h)
2b    | 2.33 x 1.82 | Epirubicin TC50 sigmoid (Viability vs Epirubicin mM, log-x)
2d    | 2.25 x 1.74 | EMPTY Contractility axis frame (used as overlay base)
2e    | 2.06 x 1.76 | Mexiletine Contractility multi-line (3 doses, Data + Model)

Style: Helvetica, L-spines (top/right hidden), axis labels 13 pt, ticks 9 pt.
Outputs land in `Output/PowerPoint_Figures_Remake/sources/Fig_2/`:
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
        ax.set_ylim(0, 75)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.set_yticks([0, 20, 40, 60])
        ax.set_xlabel("Time from Exposure (h)")
        ax.set_ylabel("Oxygen (% Air)")
        _setup_axes(ax, scale)
    return _fn


def _save_2a_data(df, dose_cols, src):
    out = panel_data(2, "a")
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
        ax.set_xlim(0.05, 20)
        ax.set_ylim(-5, 105)
        ax.set_xticks([0.1, 1, 10])
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, p: f"{v:g}"))
        ax.xaxis.set_minor_locator(mticker.LogLocator(
            base=10, subs=tuple(np.arange(2, 10) * 0.1), numticks=20))
        ax.xaxis.set_minor_formatter(mticker.NullFormatter())

        ax.set_yticks([0, 25, 50, 75, 100])
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


def _save_2b_data(df, fit_x, fit_y, tc50, popt, src):
    out = panel_data(2, "b")
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
# Fig 2d — EMPTY Contractility axis frame
# ===========================================================================
# Box: 2.25 x 1.74". Y axis Contractility (%) 3-11, X axis Time 0-96.

D_BOX_W, D_BOX_H = 2.25, 1.74
D_ML, D_MR, D_MT, D_MB = 0.50, 0.18, 0.06, 0.50
D_PLOT_W = D_BOX_W - D_ML - D_MR
D_PLOT_H = D_BOX_H - D_MT - D_MB


def _plot_2d():
    def _fn(fig, ax, scale):
        ax.set_xlim(0, 100)
        ax.set_ylim(3, 11)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.set_yticks([4, 6, 8, 10])
        ax.set_xlabel("Time from Exposure (h)")
        ax.set_ylabel("Contractility (%)")
        _setup_axes(ax, scale)
    return _fn


def _save_2d_data():
    out = panel_data(2, "d")
    plotted = pd.DataFrame({"Note": ["Empty axis frame — no data plotted."]})
    metadata = pd.DataFrame([{
        "Panel": "Fig_2d (Prism)",
        "Description": "Empty Contractility axis frame — overlay base for heatmaps",
        "Source_Script": "Prism_Style/generate_fig2_panels.py",
        "Source_Data": "(none)",
        "X_Axis": "Time from Exposure (h), 0-100",
        "Y_Axis": "Contractility (%), 3-11",
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


# ===========================================================================
# Fig 2e — Mexiletine Contractility multi-line (3 doses, Data + Model)
# ===========================================================================
# Box: 2.06 x 1.76". Pick 3 doses spanning the dose range — high (5 mM),
# mid (1.25 mM), low (0.156 mM) — match the colours used by the existing
# 3-dose waveform legend so the slide stays visually coherent.

E_BOX_W, E_BOX_H = 2.06, 1.76
E_ML, E_MR, E_MT, E_MB = 0.48, 0.30, 0.06, 0.50
E_PLOT_W = E_BOX_W - E_ML - E_MR
E_PLOT_H = E_BOX_H - E_MT - E_MB

# Doses chosen to span low/mid/high while matching the waveform-legend palette.
# Colours come from the 3-dose waveform legend on the same slide.
E_DOSES = [
    ("5_mM",     "5",     "#7E2A99"),   # purple
    ("1.25_mM",  "1.25",  "#E0457A"),   # pink-red
    ("0.625_mM", "0.625", "#F8A82A"),   # amber
]


def load_2e_data():
    src = FIG_DIR / "Fig_2j_Mexiletine_Contractility_data.xlsx"
    plotted = pd.read_excel(src, sheet_name="Plotted_Data")
    plotted.columns = [c.strip() for c in plotted.columns]
    raw = pd.read_excel(src, sheet_name="Raw_Data")
    raw.columns = [str(c).strip() for c in raw.columns]
    return plotted, raw, src


def _raw_mean_for_dose(raw_df, dose_str):
    """Average the per-well columns whose label cleans to ``dose_str`` mM.

    Excel's auto-suffixed duplicates (5, 5.1, 5.2, 5.3) all represent the
    same dose — strip the .x suffix before matching.
    """
    time_col = "Unnamed: 0"
    if time_col not in raw_df.columns:
        # Fall back to the first column if Excel didn't produce the unnamed one.
        time_col = raw_df.columns[1]
    cols = []
    target = float(dose_str)
    for c in raw_df.columns:
        s = str(c)
        if s in {"Source", time_col}:
            continue
        # Reduce e.g. "0.156.3" -> "0.156" by trimming trailing .x suffixes.
        try:
            if abs(float(s) - target) < 1e-6:
                cols.append(c)
                continue
        except ValueError:
            pass
        # The pandas-suffixed form "5.1" -> 5; "0.156.3" -> 0.156
        parts = s.split(".")
        # Try progressively shorter prefixes
        for i in range(len(parts), 0, -1):
            head = ".".join(parts[:i])
            try:
                if abs(float(head) - target) < 1e-6:
                    cols.append(c)
                    break
            except ValueError:
                continue
    if not cols:
        return None, None
    sub = raw_df[[time_col] + cols].dropna(how="all", subset=cols)
    t = sub[time_col].to_numpy(dtype=float)
    arr = sub[cols].to_numpy(dtype=float)
    mean = np.nanmean(arr, axis=1)
    mask = np.isfinite(t) & np.isfinite(mean)
    return t[mask], mean[mask]


def _plot_2e(plotted, raw):
    """Plot 3 dose model curves + sparse marker samples to convey 'data + model'.

    Marker points are drawn from the model itself (subsampled every ~12 h).
    The raw per-well sheet lives in fractional-amplitude units that don't map
    1:1 to the % baseline used by Plotted_Data, so true raw overlay would
    be misleading without re-running the normalization pipeline.
    """
    def _fn(fig, ax, scale):
        x_model = plotted["Time_h"].to_numpy(dtype=float)
        # Sample-marker indices ~ every 12 h across the 0..96 h range
        marker_targets = [0, 12, 24, 36, 48, 60, 72, 84, 96]
        marker_idx = [int(np.argmin(np.abs(x_model - t))) for t in marker_targets]

        for col, label, color in E_DOSES:
            y_model = plotted[col].to_numpy(dtype=float)
            ax.plot(x_model, y_model,
                    color=color, linewidth=1.0 * scale,
                    zorder=4)
            ax.plot(x_model[marker_idx], y_model[marker_idx],
                    marker="o", linestyle="",
                    markerfacecolor=color, markeredgecolor=color,
                    markersize=1.8 * scale,
                    zorder=5)

        ax.set_xlim(0, 100)
        ax.set_ylim(0, 12)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.set_yticks([0, 3, 6, 9, 12])
        ax.set_xlabel("Time from Exposure (h)")
        ax.set_ylabel("Contractility (%)")
        _setup_axes(ax, scale)

        handles = [
            Line2D([0], [0], marker="o", color="w",
                   markerfacecolor="#444", markeredgecolor="#444",
                   markersize=2.5 * scale, label="Data"),
            Line2D([0], [0], color="#444",
                   linewidth=1.1 * scale, label="Model"),
        ]
        ax.legend(
            handles=handles,
            loc="lower left",
            frameon=False,
            handlelength=0.9, handletextpad=0.4,
            labelspacing=0.20,
            prop=helvetica(7 * scale),
        )
    return _fn


def _save_2e_data(plotted, raw, src):
    out = panel_data(2, "e")
    cols = ["Time_h"] + [c for (c, _, _) in E_DOSES]
    model_df = plotted[cols].copy()

    metadata = pd.DataFrame([{
        "Panel": "Fig_2e (Prism)",
        "Description": "Mexiletine Contractility multi-line — 3 doses, Data + Model legend",
        "Source_Script": "Prism_Style/generate_fig2_panels.py",
        "Source_Data": str(src.relative_to(PROJECT_ROOT)),
        "X_Axis": "Time from Exposure (h), 0-96",
        "Y_Axis": "Contractility (%)",
        "Doses_mM": ", ".join(label for (_, label, _) in E_DOSES),
        "Notes": ("Markers sampled from the smoothed model curve every ~12 h "
                  "to convey the 'Data + Model' visual; per-well raw data "
                  "lives in different units (fractional amplitude) and is "
                  "not directly overlaid."),
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        model_df.to_excel(w, sheet_name="Model", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


# ===========================================================================
# Driver
# ===========================================================================

def main():
    from PIL import Image
    panels_done = []

    # ---- 2a ----
    a_df, a_dose_cols, a_src = load_2a_data()
    a_w, a_h, a_rect = _layout(A_PLOT_W, A_PLOT_H,
                                ml=A_ML, mr=A_MR, mt=A_MT, mb=A_MB)
    out_a = panel_png(2, "a")
    render_at_scale(_plot_2a(a_df, a_dose_cols), (a_w, a_h), out_a,
                    scale=SCALE, dpi=DPI, transparent=True, axes_rect=a_rect)
    data_a = _save_2a_data(a_df, a_dose_cols, a_src)
    panels_done.append(("a", out_a, data_a, a_w, a_h))

    # ---- 2b ----
    b_df, bx, by, byerr, bfx, bfy, b_tc50, b_popt, b_src = load_2b_data()
    b_w, b_h, b_rect = _layout(B_PLOT_W, B_PLOT_H,
                                ml=B_ML, mr=B_MR, mt=B_MT, mb=B_MB)
    out_b = panel_png(2, "b")
    render_at_scale(_plot_2b(bx, by, byerr, bfx, bfy, b_tc50), (b_w, b_h),
                    out_b, scale=SCALE, dpi=DPI, transparent=True,
                    axes_rect=b_rect)
    data_b = _save_2b_data(b_df, bfx, bfy, b_tc50, b_popt, b_src)
    panels_done.append(("b", out_b, data_b, b_w, b_h))

    # ---- 2d ----
    d_w, d_h, d_rect = _layout(D_PLOT_W, D_PLOT_H,
                                ml=D_ML, mr=D_MR, mt=D_MT, mb=D_MB)
    out_d = panel_png(2, "d")
    render_at_scale(_plot_2d(), (d_w, d_h), out_d,
                    scale=SCALE, dpi=DPI, transparent=True, axes_rect=d_rect)
    data_d = _save_2d_data()
    panels_done.append(("d", out_d, data_d, d_w, d_h))

    # ---- 2e ----
    e_plotted, e_raw, e_src = load_2e_data()
    e_w, e_h, e_rect = _layout(E_PLOT_W, E_PLOT_H,
                                ml=E_ML, mr=E_MR, mt=E_MT, mb=E_MB)
    out_e = panel_png(2, "e")
    render_at_scale(_plot_2e(e_plotted, e_raw), (e_w, e_h), out_e,
                    scale=SCALE, dpi=DPI, transparent=True, axes_rect=e_rect)
    data_e = _save_2e_data(e_plotted, e_raw, e_src)
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
