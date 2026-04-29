"""Prism-style multi-line dose-response plots for Fig 3 panels j and k.

Panel j: Vandetanib O2 (3 concs: 0.062, 0.125, 0.5 mM).
Panel k: Sotalol Contractility (3 concs: 0.313, 2.5, 5.0 mM).

Each panel shows, per concentration:
  * a solid thin line per replicate well ("Data")
  * one dashed thicker line for the model fit ("Model")
Color is chosen per concentration with a low→high gradient (dark
blue → yellow → red) so the dose response reads visually.

Source data: `Output/PowerPoint_Figures/Fig_3/Fig_3e_data.xlsx`,
sheets `Vandetanib_O2`/`Sotalol_Contractility` (long format with
columns Time_h, Value_Normalized, Concentration_mM, Type=Data|Model).

Output:
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3j_prism.png
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3j_prism_data.xlsx
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3k_prism.png
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3k_prism_data.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import apply_prism_style, render_at_scale, helvetica
from _paths import panel_png, panel_data

SRC = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Fig_3" / "Fig_3e_data.xlsx"

# Sized so the inner plot area (data box, excluding tick/label margins)
# measures 4.8 x 3.26 cm = 1.89 x 1.28" per user spec.
# PLOT_W = PANEL_W - MARGIN_L - MARGIN_R = 2.54 - 0.55 - 0.10 = 1.89
# PLOT_H = PANEL_H - MARGIN_T - MARGIN_B = 2.13 - 0.30 - 0.55 = 1.28
# (MARGIN_T bumped from 0.12 → 0.30 so the rotated Y label
# "Normalized Contractility" has room above the axis without clipping.)
PANEL_W = 2.54
PANEL_H = 2.13

# Plot-area margins (inches) — chosen so a 13 pt Y label and a 13 pt X
# label both fit, with a gap above for the small legend.
MARGIN_L = 0.55
MARGIN_R = 0.10
MARGIN_T = 0.30
MARGIN_B = 0.55

PLOT_W = PANEL_W - MARGIN_L - MARGIN_R
PLOT_H = PANEL_H - MARGIN_T - MARGIN_B
AXES_RECT = (MARGIN_L / PANEL_W, MARGIN_B / PANEL_H,
             PLOT_W / PANEL_W, PLOT_H / PANEL_H)

SCALE = 4
DPI = 600

TICK_FONT_PT = 7    # unified Fig 3 tick size
AXIS_LABEL_PT = 9   # unified Fig 3 axis-label size
LEGEND_FONT_PT = 7

# Use the SAME plasma colormap that generate_paper_figures.py uses for
# Fig_3e (`plt.get_cmap('plasma', n)`):
#   highest dose → cmap(0.0) ≈ dark purple
#   middle       → cmap(0.5) ≈ magenta/pink
#   lowest       → cmap(1.0) ≈ yellow
# This matches the original axisless plot exactly; sampled hex codes
# previously drifted the navy/pink/yellow.
_PLASMA = plt.get_cmap("plasma", 3)

# Trimmed thinner per user request — barely-visible replicate traces with
# a slightly bolder dashed model overlay.
DATA_LINEWIDTH_PT = 0.22
MODEL_LINEWIDTH_PT = 0.55

PANELS = {
    "j": dict(
        sheet="Vandetanib_O2",
        coef_sheet="Vandetanib_Coefficients",
        drug="Vandetanib",
        response="O2",
        y_label="Normalized Oxygen",
        # Listed HIGH→LOW so the legend reads in the same order as the
        # axisless render (0.5, 0.125, 0.062).
        concs=[0.5, 0.125, 0.062],
        conc_labels=["0.5 mM", "0.125 mM", "0.062 mM"],
    ),
    "k": dict(
        sheet="Sotalol_Contractility",
        coef_sheet="Sotalol_Coefficients",
        drug="Sotalol",
        response="Contractility",
        y_label="Normalized Contractility",
        concs=[5.0, 2.5, 0.313],
        conc_labels=["5 mM", "2.5 mM", "0.313 mM"],
    ),
}


def load(sheet: str) -> pd.DataFrame:
    df = pd.read_excel(SRC, sheet_name=sheet)
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    return df


def _replicate_blocks(df_one: pd.DataFrame) -> list[pd.DataFrame]:
    """Split a (conc, Type=Data) frame into per-replicate blocks.

    The source file stores N replicates by repeating the time grid N times,
    one block per well. We detect block boundaries where Time_h jumps back
    near zero (i.e. a new replicate starts).
    """
    if df_one.empty:
        return []
    df_one = df_one.reset_index(drop=True)
    times = df_one["Time_h"].to_numpy()
    boundaries = [0]
    for i in range(1, len(times)):
        if times[i] < times[i - 1] - 1e-6:
            boundaries.append(i)
    boundaries.append(len(times))
    blocks = []
    for a, b in zip(boundaries[:-1], boundaries[1:]):
        blocks.append(df_one.iloc[a:b])
    return blocks


def _conc_color(conc: float, all_concs: list[float]):
    """Map a concentration to its plasma-colormap color. Mirrors
    generate_paper_figures.py: with concs_sorted high→low and
    `cmap(i/(n-1))`, the highest dose gets cmap(0.0) (dark purple), the
    lowest gets cmap(1.0) (yellow).
    """
    concs_high_to_low = sorted(all_concs, reverse=True)
    n = len(concs_high_to_low)
    cmap = plt.get_cmap("plasma", n)
    i = concs_high_to_low.index(conc)
    return cmap(i / max(n - 1, 1))


def _plot_fn(df: pd.DataFrame, spec: dict):
    concs = spec["concs"]
    color_for = {c: _conc_color(c, concs) for c in concs}

    def _fn(fig, ax, scale):
        for conc in concs:
            color = color_for[conc]
            data_blocks = _replicate_blocks(
                df[(df["Concentration_mM"] == conc) & (df["Type"] == "Data")]
            )
            for block in data_blocks:
                ax.plot(
                    block["Time_h"], block["Value_Normalized"],
                    color=color, alpha=0.85,
                    linewidth=DATA_LINEWIDTH_PT * scale, zorder=2,
                )
            model = df[(df["Concentration_mM"] == conc) & (df["Type"] == "Model")]
            if not model.empty:
                ax.plot(
                    model["Time_h"], model["Value_Normalized"],
                    color=color, linestyle="--",
                    dashes=(4, 3),
                    linewidth=MODEL_LINEWIDTH_PT * scale, zorder=4,
                )

        ax.set_xlim(0, 100)
        ax.set_xticks(list(range(0, 101, 10)))
        ax.set_xlabel("Time from exposure (h)")
        ax.set_ylabel(spec["y_label"])

        # Per-panel Y range: O2 (Vandetanib) rises from 1 → ~4 fold;
        # Contractility (Sotalol) falls from 1 → ~0.55 fold. Hand-picked
        # so ticks land on round numbers and the data fills the panel.
        if spec["response"] == "O2":
            ax.set_ylim(1, 4)
            ax.set_yticks([1, 2, 3, 4])
        else:
            ax.set_ylim(0.4, 1.0)
            ax.set_yticks([0.4, 0.6, 0.8, 1.0])

        apply_prism_style(
            ax,
            scale=scale,
            spine_width_pt=1.2,
            hide_spines=("top", "right"),
            show_xticks=True,
            ytick_length_pt=4.0,
            ytick_width_pt=1.0,
            tick_label_size_pt=TICK_FONT_PT,
            ylabel_size_pt=AXIS_LABEL_PT,
            xlabel_size_pt=AXIS_LABEL_PT,
            ylabel_pad_pt=2,
            xlabel_pad_pt=3,
            clean_y_ticks=True,
            bold=False,
        )

        # Legend: 3 concentration colors then Data/Model line-style entries.
        # j (Vandetanib O2): bottom-right (rising curves clear that corner).
        # k (Sotalol Contractility): lower-left (decaying curves clear there).
        loc = "lower right" if spec["response"] == "O2" else "lower left"
        handles = [
            Line2D([0], [0], color=color_for[c], linewidth=2.4 * scale,
                   label=lab)
            for c, lab in zip(concs, spec["conc_labels"])
        ]
        handles += [
            Line2D([0], [0], color="black",
                   linewidth=DATA_LINEWIDTH_PT * scale * 1.6, label="Data"),
            Line2D([0], [0], color="black", linestyle="--", dashes=(4, 3),
                   linewidth=MODEL_LINEWIDTH_PT * scale, label="Model"),
        ]
        ax.legend(
            handles=handles,
            loc=loc,
            frameon=False,
            handlelength=1.4,
            handletextpad=0.4,
            labelspacing=0.20,
            borderaxespad=0.4,
            prop=helvetica(LEGEND_FONT_PT * scale),
        )

    return _fn


def _save_data(letter: str, df: pd.DataFrame, spec: dict, out_path: Path):
    """Write Plotted/Coefficients/Metadata workbook for the panel."""
    plotted = df[["Time_h", "Value_Normalized", "Concentration_mM", "Type"]].copy()
    coefficients = pd.read_excel(SRC, sheet_name=spec["coef_sheet"])

    metadata = pd.DataFrame([{
        "Panel": f"Fig_3{letter} (Prism)",
        "Description": (f"{spec['drug']} {spec['response']} "
                        f"dose-response over time — Data (replicate wells, "
                        f"solid) + Model fit (dashed) per concentration"),
        "Source_Script": "Prism_Style/generate_fig3_multiline.py",
        "Source_Data": str(SRC.relative_to(PROJECT_ROOT)),
        "Source_Sheet": spec["sheet"],
        "Coefficients_Sheet": spec["coef_sheet"],
        "Concentrations_mM": ", ".join(str(c) for c in spec["concs"]),
        "Time_h_min": 0, "Time_h_max": 100,
    }])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        coefficients.to_excel(w, sheet_name="Coefficients", index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)


def main():
    from PIL import Image
    for letter, spec in PANELS.items():
        df = load(spec["sheet"])
        png_out = panel_png(3, letter)
        data_out = panel_data(3, letter)
        render_at_scale(
            _plot_fn(df, spec), (PANEL_W, PANEL_H), png_out,
            scale=SCALE, dpi=DPI, transparent=True,
            axes_rect=AXES_RECT,
        )
        _save_data(letter, df, spec, data_out)
        im = Image.open(png_out)
        dpi = im.info.get("dpi", (DPI, DPI))[0]
        n_data_blocks = sum(
            len(_replicate_blocks(df[(df["Concentration_mM"] == c)
                                     & (df["Type"] == "Data")]))
            for c in spec["concs"]
        )
        print(f"[3{letter}] {spec['drug']} {spec['response']} "
              f"({len(spec['concs'])} concs, {n_data_blocks} replicate lines)")
        print(f"    image  : {im.size} px = "
              f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
        print(f"    data   : {data_out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
