"""Prism-style LOOCV Accuracy vs AUC scatter strip for Fig 3d.

Three side-by-side sub-panels — one per target (Arrhythmia, heart_damage,
Concern_Binary).  Each sub-panel plots 12 colored dots (one per PK-PD
equation, spectral palette) with x=Accuracy and y=AUC ROC, both 0..1.  A
gray dashed reference diagonal (y=x) is drawn behind the points.

Reads `Output/PowerPoint_Figures/Fig_3/Fig_3d_data.xlsx` sheet
`LOOCV_Strip_Data` (36 rows = 12 equations x 3 targets).

Output:
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3d_prism.png
    Output/PowerPoint_Figures_Remake/sources/Fig_3/Fig_3d_prism_data.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.transforms import Bbox

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

import figure_config  # noqa: F401
from prism_style import apply_prism_style, helvetica, clean_decimal_formatter
from _paths import panel_named_png, panel_named_data
from _equations import equation_color_map

SRC = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Fig_3" / "Fig_3d_data.xlsx"

TARGETS = [
    ("Arrhythmia",     "Arrhythmia"),
    ("heart_damage",   "Heart Damage"),
    ("Concern_Binary", "Concern"),
]

# Sizing — 3 sub-panels of 1.5" × 1.5" plot area, side by side.
# Margins generous so the title, axis labels, and tick labels never clip.
SUB_PLOT = 1.50
MARGIN_L = 0.70     # left of leftmost sub-panel (Y label "AUC ROC" at 13 pt)
MARGIN_R = 0.20     # rightmost x-tick label "1" overshoot
MARGIN_T = 0.30     # title at 11 pt bold + small gap
MARGIN_B = 0.55     # X label + ticks (at 13 pt / 9 pt)
GAP = 0.50          # gap between sub-panels (room for inner Y axes)

PLOT_W = 3 * SUB_PLOT + 2 * GAP
PLOT_H = SUB_PLOT
FIG_W = PLOT_W + MARGIN_L + MARGIN_R
FIG_H = PLOT_H + MARGIN_T + MARGIN_B

DPI = 600
SCALE = 4
TICK_FONT_PT = 9
AXIS_LABEL_PT = 13
TITLE_FONT_PT = 11

DOT_SIZE = 28
DIAG_COLOR = "#9d9d9d"


def load() -> pd.DataFrame:
    df = pd.read_excel(SRC, sheet_name="LOOCV_Strip_Data")
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    return df


def _draw(df: pd.DataFrame, out_path: Path):
    fig = plt.figure(figsize=(FIG_W * SCALE, FIG_H * SCALE), dpi=DPI)

    colors = equation_color_map()  # canonical name -> color (shared with R² bar)

    for i, (target_key, title) in enumerate(TARGETS):
        sub_left_in = MARGIN_L + i * (SUB_PLOT + GAP)
        rect = (sub_left_in / FIG_W, MARGIN_B / FIG_H,
                SUB_PLOT / FIG_W, PLOT_H / FIG_H)
        ax = fig.add_axes(list(rect))

        sub = df[df["Target"] == target_key]
        # Reference diagonal
        ax.plot([0, 1], [0, 1], color=DIAG_COLOR, linestyle="--",
                dashes=(4, 3), linewidth=0.9 * SCALE, zorder=2)

        # 12 colored dots
        for _, row in sub.iterrows():
            ax.scatter(
                row["Accuracy"], row["AUC"],
                s=DOT_SIZE * SCALE * SCALE,
                c=[colors[row["Equation"]]],
                edgecolor="black", linewidth=0.5 * SCALE,
                zorder=4,
            )

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(clean_decimal_formatter))

        ax.set_xlabel("Accuracy")
        if i == 0:
            ax.set_ylabel("AUC ROC")

        # Title above each sub-panel
        ax.text(
            0.5, 1.04, title,
            transform=ax.transAxes,
            ha="center", va="bottom",
            fontproperties=helvetica(TITLE_FONT_PT * SCALE, bold=True),
        )

        apply_prism_style(
            ax,
            scale=SCALE,
            spine_width_pt=1.2,
            hide_spines=("top", "right"),
            show_xticks=True,
            ytick_length_pt=4.0,
            ytick_width_pt=1.0,
            tick_label_size_pt=TICK_FONT_PT,
            ylabel_size_pt=AXIS_LABEL_PT,
            xlabel_size_pt=AXIS_LABEL_PT,
            ylabel_pad_pt=2,
            xlabel_pad_pt=2,
            clean_y_ticks=True,
            bold=False,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    full_bbox = Bbox.from_bounds(0, 0, FIG_W * SCALE, FIG_H * SCALE)
    fig.savefig(str(out_path), dpi=DPI, transparent=True,
                bbox_inches=full_bbox, pad_inches=0)
    plt.close(fig)

    # Downscale to target physical size
    from PIL import Image
    target_px = (int(round(FIG_W * DPI)), int(round(FIG_H * DPI)))
    im = Image.open(out_path)
    im.resize(target_px, Image.LANCZOS).save(out_path, dpi=(DPI, DPI))


def _save_data(df: pd.DataFrame):
    out = panel_named_data(3, "LOOCV_scatter")
    metadata = pd.DataFrame([{
        "Panel": "Fig_3d (Prism)",
        "Description": "LOOCV Accuracy vs AUC ROC for 12 PK-PD equations across 3 targets",
        "Source_Script": "Prism_Style/generate_loocv_scatter.py",
        "Source_Data": str(SRC.relative_to(PROJECT_ROOT)),
        "Targets": ", ".join(t for t, _ in TARGETS),
        "Color_Map": "turbo",
    }])
    plotted = df[["Equation", "Target", "Model", "Accuracy", "AUC",
                  "N_samples", "N_features"]].copy()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        plotted.to_excel(w, sheet_name="Plotted", index=False)
        for target_key, title in TARGETS:
            sub = df[df["Target"] == target_key][
                ["Equation", "Model", "Accuracy", "AUC"]
            ]
            sub.to_excel(w, sheet_name=title[:31], index=False)
        metadata.to_excel(w, sheet_name="Metadata", index=False)
    return out


def main():
    from PIL import Image
    df = load()
    out = panel_named_png(3, "LOOCV_scatter")
    _draw(df, out)
    data_xlsx = _save_data(df)
    im = Image.open(out)
    dpi = im.info.get("dpi", (DPI, DPI))[0]
    print(f"[3 LOOCV] -> {out.relative_to(PROJECT_ROOT)}")
    print(f"    image  : {im.size} px = "
          f"{im.size[0]/dpi:.3f}\" x {im.size[1]/dpi:.3f}\"")
    print(f"    data   : {data_xlsx.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
