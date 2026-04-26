"""Demo: regenerate Fig_6c with Prism-look styling.

- Pulls metric means & stds from the tracked xlsx
  ``Output/PowerPoint_Figures/Fig_6/Fig_6c_data.xlsx`` (sheet ``Metrics_Summary``)
- Plot area sized to Prism's rectangle (1.526" × 1.422")
- Outer image 2.5" × 2.11" (extra bottom room for the 2-line "AUC / ROC")
- Rendered at scale=4, LANCZOS-downscaled to the target size
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))   # for figure_config
sys.path.insert(0, str(HERE))           # for prism_style

import figure_config  # noqa: F401 — registers Helvetica + savefig rcParams
from prism_style import apply_prism_style, render_at_scale, helvetica

DATA_XLSX = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Fig_6" / "Fig_6c_data.xlsx"
OUT_PATH = HERE / "Fig_6c_prism_demo.png"

# Prism's 4 colors (from pixel analysis)
BAR_COLORS = ["#6C92ED", "#7DB88A", "#C98B8E", "#CCBC7E"]

# Plot area = Prism (1.526" × 1.422"). Outer image 2.5" × 2.11" to fit
# the 2-line "AUC / ROC" X label below the axis.
TARGET_FIGSIZE = (2.5, 2.11)
SCALE = 4
AXES_RECT = (
    0.667 / 2.5,        # left   = 0.267
    0.44  / 2.11,       # bottom = 0.209
    1.526 / 2.5,        # width  = 0.610
    1.422 / 2.11,       # height = 0.674
)


def load_metrics_from_xlsx():
    """Read Mean/Std from Fig_6c_data.xlsx → Metrics_Summary sheet.

    Expected columns: Metric, Mean, Std, (+ Source/Target/Plot_Type).
    Returns arrays ordered Accuracy, AUC, F1, MCC.
    """
    df = pd.read_excel(DATA_XLSX, sheet_name="Metrics_Summary")
    df.columns = [c.strip() for c in df.columns]
    order = ["Accuracy", "AUC", "F1", "MCC"]
    df = df.set_index("Metric").loc[order]
    return df["Mean"].to_numpy(), df["Std"].to_numpy()


def plot_metrics_bar(fig, ax, scale: float = 1.0):
    means, stds = load_metrics_from_xlsx()
    x = np.arange(4)

    # All linework thinner per user feedback ("too wide")
    bar_edge_width_pt = 1.2      # was 1.3
    err_elinewidth_pt = 0.8      # was 1.44
    err_capsize_pt    = 4.0      # was 9.4 — tighter caps
    err_capthick_pt   = 0.8      # was 1.44
    value_label_size_pt = 7

    bars = ax.bar(
        x, means,
        yerr=stds,
        width=0.67,
        color=BAR_COLORS,
        edgecolor="black",
        linewidth=bar_edge_width_pt * scale,
        error_kw=dict(
            elinewidth=err_elinewidth_pt * scale,
            capsize=err_capsize_pt * scale,
            capthick=err_capthick_pt * scale,
            ecolor="black",
        ),
    )

    for bar, val, err in zip(bars, means, stds):
        ax.annotate(
            f"{val:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, val + err),
            xytext=(0, 3 * scale),   # closer to error-bar cap
            textcoords="offset points",
            ha="center", va="bottom",
            fontproperties=helvetica(value_label_size_pt * scale),
        )

    ax.set_xticks(x)
    ax.set_xticklabels(["Acc", "AUC\nROC", "F1", "MCC"])
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.50, 0.75, 1])

    apply_prism_style(
        ax,
        scale=scale,
        spine_width_pt=1.2,      # was 1.4 — thinner border
        hide_spines=("top", "right"),
        show_xticks=False,
        ytick_length_pt=7.2,
        ytick_width_pt=1.2,      # match spine
        tick_label_size_pt=9,
        ylabel_size_pt=13,
        ylabel_pad_pt=3,
        xlabel_pad_pt=6,
        clean_y_ticks=True,
        bold=False,
    )


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = render_at_scale(
        plot_metrics_bar,
        TARGET_FIGSIZE,
        OUT_PATH,
        scale=SCALE,
        dpi=600,
        transparent=True,
        axes_rect=AXES_RECT,
    )
    from PIL import Image
    im = Image.open(out)
    dpi = im.info.get("dpi", (600, 600))[0]
    means, stds = load_metrics_from_xlsx()
    print(f"Wrote {out}")
    print(f"  pixel size : {im.size}")
    print(f"  DPI        : {dpi}")
    print(f"  physical   : {im.size[0]/dpi:.3f}\" × {im.size[1]/dpi:.3f}\"")
    print(f"  plot area  : 1.526\" × 1.422\" (matches Prism)")
    print(f"  data source: {DATA_XLSX.name} -> Metrics_Summary")
    for m, μ, σ in zip(["Accuracy", "AUC", "F1", "MCC"], means, stds):
        print(f"    {m:10s} = {μ:.3f} ± {σ:.3f}")


if __name__ == "__main__":
    main()
