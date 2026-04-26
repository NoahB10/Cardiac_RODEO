"""Prism-style horizontal R² bar chart for Fig 3c.

Reads `Output/PowerPoint_Figures/Fig_3/Fig_3c_data.xlsx` (sheet `R2_Data`),
sorts the 12 equations by R² (O2 column) descending, and draws one colored
horizontal bar per equation with the R² value annotated at the bar tip.
Colors follow a spectral / rainbow palette — best at top, worst at bottom.

Output:
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3c_prism.png
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3c_prism_data.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.cm as mcm

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import apply_prism_style, render_at_scale, helvetica
from _paths import panel_named_png, panel_named_data

SRC = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Fig_3" / "Fig_3c_data.xlsx"

# Plot tuning
PLOT_W = 2.50    # in
PLOT_H = 2.40
MARGIN_L = 1.20  # equation names go here (rotate-free)
MARGIN_R = 0.50  # value labels at bar tip
MARGIN_T = 0.05
MARGIN_B = 0.45  # X label "R² (O2)"
FIG_W = PLOT_W + MARGIN_L + MARGIN_R
FIG_H = PLOT_H + MARGIN_T + MARGIN_B
AXES_RECT = (MARGIN_L / FIG_W, MARGIN_B / FIG_H,
             PLOT_W / FIG_W, PLOT_H / FIG_H)

TICK_FONT_PT = 9
AXIS_LABEL_PT = 13
VALUE_LABEL_PT = 7

SCALE = 4
WHICH_COL = "O2"   # The O2 column matches reference image #12


def load() -> pd.DataFrame:
    df = pd.read_excel(SRC, sheet_name="R2_Data")
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    df = df[["Equation", "Contractility", "O2"]].copy()
    # Sort descending by R² in the chosen column → best at top.
    df = df.sort_values(WHICH_COL, ascending=False).reset_index(drop=True)
    return df


def _plot_fn(df: pd.DataFrame):
    n = len(df)
    values = df[WHICH_COL].to_numpy()
    labels = df["Equation"].tolist()
    cmap = mcm.get_cmap("turbo")
    # Top bar = warm color, bottom bar = cool.
    colors = [cmap(0.05 + 0.90 * (i / max(1, n - 1))) for i in range(n)]

    def _fn(fig, ax, scale):
        y = np.arange(n)
        bars = ax.barh(
            y, values,
            color=colors, edgecolor="black",
            linewidth=0.8 * scale,
            height=0.75,
        )
        # Vertical zero line (Prism style)
        ax.axvline(0, color="black", linewidth=1.0 * scale, zorder=4)

        # Numeric value at bar tip
        for v, yy in zip(values, y):
            ha = "left" if v >= 0 else "right"
            xoff = 4 * scale if v >= 0 else -4 * scale
            ax.annotate(
                f"{v:+.2f}".replace("+", " "),
                xy=(v, yy), xytext=(xoff, 0),
                textcoords="offset points",
                ha=ha, va="center",
                fontproperties=helvetica(VALUE_LABEL_PT * scale),
            )

        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()   # best on top
        # X limits: pad both sides so value labels fit
        vmin, vmax = values.min(), values.max()
        pad = 0.18
        ax.set_xlim(vmin - pad, vmax + pad)
        ax.set_xticks([round(t, 2) for t in np.linspace(np.ceil(vmin * 4) / 4,
                                                         np.floor(vmax * 4) / 4, 5)])
        ax.set_xlabel(r"R$^2$ (O$_2$ fit)")

        apply_prism_style(
            ax,
            scale=scale,
            spine_width_pt=1.2,
            hide_spines=("top", "right"),
            show_xticks=True,
            ytick_length_pt=0,        # no tick marks on Y (just equation names)
            ytick_width_pt=0,
            tick_label_size_pt=TICK_FONT_PT,
            ylabel_size_pt=AXIS_LABEL_PT,
            xlabel_size_pt=AXIS_LABEL_PT,
            ylabel_pad_pt=2,
            xlabel_pad_pt=4,
            clean_y_ticks=False,      # Y axis is categorical
            bold=False,
        )
        ax.tick_params(axis="y", length=0, width=0, pad=4 * scale)

    return _fn


def _save_data(df: pd.DataFrame):
    out = panel_named_data(3, "R2_bar")
    plotted = df.rename(columns={WHICH_COL: f"R2_{WHICH_COL}"})
    metadata = pd.DataFrame([{
        "Panel": "Fig_3c (Prism)",
        "Description": "Horizontal R² bar across 12 PK-PD equations (O₂ fit), sorted descending",
        "Source_Script": "Prism_Style/generate_r2_bar.py",
        "Source_Data": str(SRC.relative_to(PROJECT_ROOT)),
        "Sort_Column": f"R² ({WHICH_COL})",
        "Color_Map": "turbo",
    }])
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


def main():
    from PIL import Image
    df = load()
    out = panel_named_png(3, "R2_bar")
    render_at_scale(
        _plot_fn(df), (FIG_W, FIG_H), out,
        scale=SCALE, dpi=600, transparent=True,
        axes_rect=AXES_RECT,
    )
    data_xlsx = _save_data(df)
    im = Image.open(out)
    dpi = im.info.get("dpi", (600, 600))[0]
    print(f"[3 R²bar] -> {out.relative_to(PROJECT_ROOT)}")
    print(f"    image  : {im.size} px = "
          f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
    print(f"    data   : {data_xlsx.relative_to(PROJECT_ROOT)}")
    print(f"    sorted : {df[['Equation', WHICH_COL]].to_string(index=False)}")


if __name__ == "__main__":
    main()
