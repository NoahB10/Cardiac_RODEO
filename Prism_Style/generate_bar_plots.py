"""Prism-style bar plots for Fig 6c/6h, 7c/7h, 8c.

c panels: single-model, 4 metrics (Accuracy / AUC / F1 / MCC) per target.
h panels: grouped bars (models × {Accuracy, F1, MCC}) comparing Organoid
          against CNN (fig 6) or ADMET methods (fig 7).

Sources:
- c: Output/PowerPoint_Figures/Fig_{N}/Fig_{N}c_data.xlsx -> "Metrics_Summary"
- h: Output/PowerPoint_Figures/Fig_{N}/Fig_{N}h_data.xlsx -> "Sheet1"
     (Model / Accuracy / F1 / MCC / *_Std columns)

Output: Prism_Style/Fig_{N}{letter}_prism.png
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
from _legend_export import render_legend_image
from matplotlib.patches import Patch

FIG_DIR = PROJECT_ROOT / "Output" / "PowerPoint_Figures"

# Prism palette (pixel-sampled)
BAR_COLORS_4 = ["#6C92ED", "#7DB88A", "#C98B8E", "#CCBC7E"]  # c panels
BAR_COLORS_3 = ["#6C92ED", "#7DB88A", "#C98B8E"]              # h panels (Acc/F1/MCC)

SCALE = 4  # render at scale×, downscale to final target


# --------------------------------------------------------------------------- #
# Shared styling knobs
# --------------------------------------------------------------------------- #

STYLE = dict(
    spine_width_pt=1.2,
    ytick_length_pt=7.2,
    ytick_width_pt=1.2,
    tick_label_size_pt=9,    # uniform across all Prism panels
    ylabel_size_pt=13,       # uniform across all Prism panels
    ylabel_pad_pt=3,
    xlabel_pad_pt=6,
    clean_y_ticks=True,
    bold=False,
)

# h panels share the same tick / axis sizes as c panels — uniform fonts.
STYLE_H = {**STYLE}

BAR_EDGE_PT = 1.2
ERR_ELW_PT  = 0.8
ERR_CAP_PT  = 4.0
ERR_CAPTH_PT = 0.8
VALUE_LABEL_PT = 7        # uniform value-label size across c and h panels
VALUE_LABEL_OFFSET_PT = 3
VALUE_LABEL_PT_H = 7


# --------------------------------------------------------------------------- #
# c-panel renderer (4 metrics, one model)
# --------------------------------------------------------------------------- #

def _c_plot_fn(means, stds):
    def _fn(fig, ax, scale):
        x = np.arange(4)
        bars = ax.bar(
            x, means, yerr=stds,
            width=0.67,
            color=BAR_COLORS_4, edgecolor="black",
            linewidth=BAR_EDGE_PT * scale,
            error_kw=dict(
                elinewidth=ERR_ELW_PT * scale,
                capsize=ERR_CAP_PT * scale,
                capthick=ERR_CAPTH_PT * scale,
                ecolor="black",
            ),
        )
        for bar, v, e in zip(bars, means, stds):
            ax.annotate(
                f"{v:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, v + e),
                xytext=(0, VALUE_LABEL_OFFSET_PT * scale),
                textcoords="offset points",
                ha="center", va="bottom",
                fontproperties=helvetica(VALUE_LABEL_PT * scale),
            )
        ax.set_xticks(x)
        ax.set_xticklabels(["Acc", "AUC\nROC", "F1", "MCC"])
        ax.set_ylabel("Score")
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.25, 0.50, 0.75, 1])
        apply_prism_style(ax, scale=scale, hide_spines=("top", "right"),
                           show_xticks=False, **STYLE)
    return _fn


# --------------------------------------------------------------------------- #
# h-panel renderer (grouped bars: models × {Acc, F1, MCC})
# --------------------------------------------------------------------------- #

def _wrap_model_label(s: str) -> str:
    """Break model names before a "(" onto a second line, if not already wrapped."""
    s = str(s)
    if "\n" in s:
        return s
    if "(" in s:
        i = s.rfind(" (")
        if i > 0:
            return s[:i] + "\n" + s[i + 1:]
    return s


def _h_plot_fn(df):
    """df: one row per model; columns Model, Accuracy, F1, MCC, *_Std."""
    metrics = ["Accuracy", "F1", "MCC"]
    std_cols = [f"{m}_Std" for m in metrics]

    def _fn(fig, ax, scale):
        n = len(df)
        k = len(metrics)
        total_w = 0.88       # wider cluster → tighter cluster-to-cluster gap
        bw = total_w / k
        x = np.arange(n)
        all_bars = []
        all_errs = []
        for i, (m, sc) in enumerate(zip(metrics, std_cols)):
            offs = (i - (k - 1) / 2) * bw
            means = df[m].to_numpy(dtype=float)
            stds = df[sc].to_numpy(dtype=float) if sc in df.columns else np.zeros(n)
            bars = ax.bar(
                x + offs, means, bw, yerr=stds,
                color=BAR_COLORS_3[i], edgecolor="black",
                linewidth=BAR_EDGE_PT * scale,
                label=m,
                error_kw=dict(
                    elinewidth=ERR_ELW_PT * scale,
                    capsize=ERR_CAP_PT * scale,
                    capthick=ERR_CAPTH_PT * scale,
                    ecolor="black",
                ),
            )
            all_bars.append((bars, means, stds))

        # Value labels above each bar's error cap (smaller for h)
        for bars, means, stds in all_bars:
            for bar, v, e in zip(bars, means, stds):
                ax.annotate(
                    f"{v:.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, v + e),
                    xytext=(0, VALUE_LABEL_OFFSET_PT * scale),
                    textcoords="offset points",
                    ha="center", va="bottom",
                    fontproperties=helvetica(VALUE_LABEL_PT_H * scale),
                )

        ax.set_xticks(x)
        # Always horizontal with 2-line wrapping — rotation regressed from 6h's look.
        labels = [_wrap_model_label(s) for s in df["Model"].tolist()]
        ax.set_xticklabels(labels, rotation=0, ha="center")
        ax.set_ylabel("Score")
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.25, 0.50, 0.75, 1])
        apply_prism_style(ax, scale=scale, hide_spines=("top", "right"),
                           show_xticks=False, **STYLE_H)
        # Legend is rendered to a separate PNG (Fig_Nh_prism_legend.png).

    return _fn


# --------------------------------------------------------------------------- #
# Panel descriptors
# --------------------------------------------------------------------------- #

def _axes_rect(plot_w, plot_h, fig_w, fig_h, margin_l, margin_b):
    return (margin_l / fig_w, margin_b / fig_h, plot_w / fig_w, plot_h / fig_h)


def _c_panel_descriptor(fig_num: int):
    xlsx = FIG_DIR / f"Fig_{fig_num}" / f"Fig_{fig_num}c_data.xlsx"
    df = pd.read_excel(xlsx, sheet_name="Metrics_Summary")
    df.columns = [c.strip() for c in df.columns]
    order = ["Accuracy", "AUC", "F1", "MCC"]
    df = df.set_index("Metric").loc[order]
    means = df["Mean"].to_numpy()
    stds = df["Std"].to_numpy()
    # Plot 1.526 x 1.422" (the prior good size), outer 2.5 x 2.11".
    fig_w, fig_h = 2.5, 2.11
    plot_w, plot_h = 1.526, 1.422
    margin_l, margin_b = 0.667, 0.44
    rect = _axes_rect(plot_w, plot_h, fig_w, fig_h, margin_l, margin_b)
    out = HERE / f"Fig_{fig_num}c_prism.png"
    return dict(plot_fn=_c_plot_fn(means, stds), figsize=(fig_w, fig_h),
                axes_rect=rect, out=out, src=xlsx, means=means, stds=stds)


def _h_panel_descriptor(fig_num: int):
    xlsx = FIG_DIR / f"Fig_{fig_num}" / f"Fig_{fig_num}h_data.xlsx"
    df = pd.read_excel(xlsx, sheet_name="Sheet1")
    df.columns = [c.strip() for c in df.columns]

    # Plot 1.42" tall (= 3.6 cm) — same as a/b/f plot height.  Width: at 9pt,
    # "(DIQT Transfer)" is ~0.95" so 3-model needs 8 cm plot so the labels
    # don't overlap; 5-model needs 9 cm.
    plot_h = 3.6 / 2.54   # 1.4173"
    n = len(df)
    plot_w_cm = max(8.0, 1.8 * n)
    plot_w = plot_w_cm / 2.54
    margin_l = 0.667
    margin_b = 0.85       # 2-line model names at 9 pt + tick gap
    margin_t = 0.30       # headroom for 7 pt value labels above bars
    margin_r = 0.10       # right edge — legend is in a separate PNG
    fig_w = plot_w + margin_l + margin_r
    fig_h = plot_h + margin_b + margin_t
    rect = _axes_rect(plot_w, plot_h, fig_w, fig_h, margin_l, margin_b)
    out = HERE / f"Fig_{fig_num}h_prism.png"
    return dict(plot_fn=_h_plot_fn(df), figsize=(fig_w, fig_h),
                axes_rect=rect, out=out, src=xlsx, df=df, kind="h")


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

PANELS = [
    ("6c", _c_panel_descriptor, 6),
    ("6h", _h_panel_descriptor, 6),
    ("7c", _c_panel_descriptor, 7),
    ("7h", _h_panel_descriptor, 7),
    ("8c", _c_panel_descriptor, 8),
]


def main():
    from PIL import Image
    for name, maker, n in PANELS:
        try:
            d = maker(n)
        except FileNotFoundError as e:
            print(f"[SKIP] {name}: {e}")
            continue
        out = render_at_scale(
            d["plot_fn"], d["figsize"], d["out"],
            scale=SCALE, dpi=600, transparent=True,
            axes_rect=d["axes_rect"],
        )
        im = Image.open(out)
        dpi = im.info.get("dpi", (600, 600))[0]
        fig_w, fig_h = d["figsize"]
        plot_w = d["axes_rect"][2] * fig_w
        plot_h = d["axes_rect"][3] * fig_h
        print(f"[{name}] -> {out.name}")
        print(f"    image  : {im.size} px = {im.size[0]/dpi:.3f}\" × {im.size[1]/dpi:.3f}\"")
        print(f"    plot   : {plot_w:.3f}\" × {plot_h:.3f}\"  ({plot_w*2.54:.2f} × {plot_h*2.54:.2f} cm)")
        print(f"    source : {d['src'].name}")

        # h panels: also write a standalone Acc/F1/MCC color-key legend.
        if d.get("kind") == "h":
            handles = [Patch(facecolor=BAR_COLORS_3[i], edgecolor="black",
                             linewidth=BAR_EDGE_PT * SCALE, label=lbl)
                       for i, lbl in enumerate(["Accuracy", "F1", "MCC"])]
            legend_out = d["out"].with_name(d["out"].stem + "_legend.png")
            render_legend_image(
                handles,
                prop=helvetica(VALUE_LABEL_PT_H * SCALE),
                out_path=legend_out,
                scale=SCALE,
                handlelength=1.0,
                handletextpad=0.4,
                labelspacing=0.3,
                borderpad=0.0,
            )
            leg_im = Image.open(legend_out)
            print(f"    legend : {legend_out.name}  {leg_im.size} px = "
                  f"{leg_im.size[0]/dpi:.3f}\" × {leg_im.size[1]/dpi:.3f}\"")

        if "means" in d:
            for m, μ, σ in zip(["Acc", "AUC", "F1", "MCC"], d["means"], d["stds"]):
                print(f"      {m:4s} = {μ:.3f} ± {σ:.3f}")
        else:
            for _, r in d["df"].iterrows():
                print(f"      {r['Model']:25s} "
                      f"Acc={r['Accuracy']:.3f}±{r.get('Accuracy_Std', 0):.3f}  "
                      f"F1={r['F1']:.3f}±{r.get('F1_Std', 0):.3f}  "
                      f"MCC={r['MCC']:.3f}±{r.get('MCC_Std', 0):.3f}")


if __name__ == "__main__":
    main()
