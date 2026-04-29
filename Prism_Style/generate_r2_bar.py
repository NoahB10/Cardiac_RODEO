"""Prism-style horizontal R² bar chart for Fig 3 panel g.

Reads `Output/PowerPoint_Figures/Fig_3/Fig_3c_data.xlsx` (sheet `R2_Data`),
sorts the 12 equations by R² (O₂ column) descending, and draws one colored
horizontal bar per equation. Visual style follows
`generate_paper_figures.py:1508+`:
  - Rainbow palette by rank (top = red, bottom = pink)
  - Positive bar value labels just right of the bar tip
  - Negative bar value labels just right of the ZERO LINE (not at bar tip),
    so they don't crowd the equation names

Sized to fit Group 82 on slide 3 (2.10" × 1.46").

Output:
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3g_prism.png
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3g_prism_data.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import apply_prism_style, render_at_scale, helvetica
from _paths import panel_png, panel_data

SRC = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Fig_3" / "Fig_3c_data.xlsx"

# Sized to Group 82 on slide 3: 2.10" × 1.46". PLOT_H pinned to 1.00"
# so the data axis matches Fig 3i's sub-panel height (same row = same plot
# area height). Extra vertical space goes into MARGIN_B as whitespace.
FIG_W = 2.10
FIG_H = 1.46
PLOT_W = 0.90
PLOT_H = 1.00     # MUST match SUB_PLOT in generate_loocv_scatter.py
MARGIN_L = 1.00   # equation names at 7 pt ("Gaussian-Hill Hybrid" longest)
MARGIN_R = 0.20   # positive value labels overflow here
MARGIN_T = 0.04
MARGIN_B = FIG_H - MARGIN_T - PLOT_H   # 0.42" (X label + bottom whitespace)
AXES_RECT = (MARGIN_L / FIG_W, MARGIN_B / FIG_H,
             PLOT_W / FIG_W, PLOT_H / FIG_H)

TICK_FONT_PT = 7
AXIS_LABEL_PT = 9
VALUE_LABEL_PT = 6

SCALE = 4
WHICH_COL = "O2"   # The O2 column matches reference image #12

# Rainbow palette by rank (top = best = red, bottom = worst = pink). Matches
# generate_paper_figures.py:1529 so the bar order/colors line up with the
# original figure 3c.
RAINBOW = [
    "#d62728",  # red          (rank 1, best)
    "#e6550d",  # red-orange
    "#ff7f0e",  # orange
    "#ffc107",  # amber
    "#8bc34a",  # yellow-green
    "#2ca02c",  # green
    "#00897b",  # teal
    "#17becf",  # cyan
    "#1f77b4",  # blue
    "#5c6bc0",  # indigo
    "#9467bd",  # purple
    "#e377c2",  # pink         (rank 12, worst)
]


def load() -> pd.DataFrame:
    df = pd.read_excel(SRC, sheet_name="R2_Data")
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    df = df[["Equation", "Contractility", "O2"]].copy()
    df = df.sort_values(WHICH_COL, ascending=False).reset_index(drop=True)
    return df


def _plot_fn(df: pd.DataFrame):
    n = len(df)
    values = df[WHICH_COL].to_numpy()
    labels = df["Equation"].tolist()
    # Rank-based rainbow (best = red at top).
    colors = [RAINBOW[i] if i < len(RAINBOW) else "#808080" for i in range(n)]

    def _fn(fig, ax, scale):
        y = np.arange(n)
        ax.barh(
            y, values,
            color=colors, edgecolor="none",
            height=0.75,
        )
        ax.axvline(0, color="black", linewidth=0.8 * scale, zorder=4)

        # Positive: label just right of bar tip (overflows into MARGIN_R).
        # Negative: label just right of zero line (NOT at bar tip — keeps
        # equation names on the left readable). Matches original Fig 3c.
        for v, yy in zip(values, y):
            x_anchor = v if v >= 0 else 0
            ax.annotate(
                f"{v:.2f}",
                xy=(x_anchor, yy), xytext=(3 * scale, 0),
                textcoords="offset points",
                ha="left", va="center",
                fontproperties=helvetica(VALUE_LABEL_PT * scale),
            )

        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        # Round OUTWARD to nearest 0.25 so axis endpoints snap to clean ticks.
        # Set xlim equal to those rounded boundaries so the first/last visible
        # ticks are exactly at the spine endpoints (no unlabelled padding).
        # Round outward to nearest 0.25 for clean endpoints, then use exactly
        # 3 ticks [lo, 0, hi] — PLOT_W=0.90" at 7pt can only fit ~3 labels
        # before they collide (5-char labels like "-0.75" are ≈0.28" wide).
        vmin, vmax = values.min(), values.max()
        xtick_lo = np.floor(vmin * 4) / 4
        xtick_hi = np.ceil(vmax * 4) / 4
        ax.set_xlim(xtick_lo, xtick_hi)
        ax.set_xticks([round(xtick_lo, 2), 0.0, round(xtick_hi, 2)])
        ax.set_xlabel(r"R$^2$")

        apply_prism_style(
            ax,
            scale=scale,
            spine_width_pt=1.0,
            hide_spines=("top", "right"),
            show_xticks=True,
            ytick_length_pt=0,
            ytick_width_pt=0,
            tick_label_size_pt=TICK_FONT_PT,
            ylabel_size_pt=AXIS_LABEL_PT,
            xlabel_size_pt=AXIS_LABEL_PT,
            ylabel_pad_pt=2,
            xlabel_pad_pt=3,
            clean_y_ticks=False,
            bold=False,
        )
        ax.tick_params(axis="y", length=0, width=0, pad=3 * scale)

    return _fn


def _save_data(df: pd.DataFrame):
    out = panel_data(3, "g")
    plotted = df.rename(columns={WHICH_COL: f"R2_{WHICH_COL}"})
    metadata = pd.DataFrame([{
        "Panel": "Fig_3g (Prism)",
        "Description": "Horizontal R² bar across 12 PK-PD equations (O₂ fit), sorted descending",
        "Source_Script": "Prism_Style/generate_r2_bar.py",
        "Source_Data": str(SRC.relative_to(PROJECT_ROOT)),
        "Sort_Column": f"R² ({WHICH_COL})",
        "Color_Map": "rainbow_by_rank",
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


def main():
    from PIL import Image
    df = load()
    out = panel_png(3, "g")
    render_at_scale(
        _plot_fn(df), (FIG_W, FIG_H), out,
        scale=SCALE, dpi=600, transparent=True,
        axes_rect=AXES_RECT,
    )
    data_xlsx = _save_data(df)
    im = Image.open(out)
    dpi = im.info.get("dpi", (600, 600))[0]
    print(f"[3g R²bar] -> {out.relative_to(PROJECT_ROOT)}")
    print(f"    image  : {im.size} px = "
          f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
    print(f"    data   : {data_xlsx.relative_to(PROJECT_ROOT)}")
    print(f"    sorted : {df[['Equation', WHICH_COL]].to_string(index=False)}")


if __name__ == "__main__":
    main()
