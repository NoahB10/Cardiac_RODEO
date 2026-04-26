"""Prism-look styling for matplotlib plots.

Two pieces:

1. ``apply_prism_style(ax, scale=...)`` — configures an existing Axes with
   Prism's visual defaults:
   - L-shape spines (left + bottom only)
   - Outward Y ticks, no X tick marks (just labels)
   - Helvetica **Bold** for every label, at explicit point sizes
   - Clean Y tick formatter ("0", "0.25", "0.50", "0.75", "1")
   Every size/linewidth knob is a kwarg — change font size, tick length,
   label pad, spine thickness independently.

2. ``render_at_scale(plot_fn, target_figsize, scale=4, dpi=600, ...)`` —
   renders the figure at ``scale × target_figsize`` for crisp rasterization,
   then downscales the PNG with PIL LANCZOS so the final image matches
   ``target_figsize × dpi`` pixels. Fonts, linewidths, and tick lengths passed
   to ``apply_prism_style`` should be the FINAL point sizes; this function
   scales them internally while rendering, so the API stays intuitive.
"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # one level up from Prism_Style/
_HELV_PATH = PROJECT_ROOT / "fonts" / "helvetica.ttf"
_HELV_BOLD_PATH = PROJECT_ROOT / "fonts" / "helvetica-bold.ttf"
for _p in (_HELV_PATH, _HELV_BOLD_PATH):
    if _p.exists():
        fm.fontManager.addfont(str(_p))


def helvetica(size_pt: float, bold: bool = False) -> fm.FontProperties:
    """Bundled Helvetica at ``size_pt`` points; regular by default."""
    path = _HELV_BOLD_PATH if bold else _HELV_PATH
    return fm.FontProperties(fname=str(path), size=size_pt)


def helvetica_bold(size_pt: float) -> fm.FontProperties:
    """Bundled Helvetica Bold at ``size_pt`` points."""
    return helvetica(size_pt, bold=True)


def _clean_y_tick(x, pos):
    """Prism-style Y formatter: ``0``, ``0.25``, ``0.50``, ``0.75``, ``1``."""
    if x == int(x):
        return f"{int(x)}"
    return f"{x:.2f}"


# Public alias so generators can also apply this formatter to the X axis.
clean_decimal_formatter = _clean_y_tick


def apply_prism_style(
    ax,
    *,
    scale: float = 1.0,
    spine_width_pt: float = 1.4,
    hide_spines=("top", "right"),
    show_xticks: bool = False,
    ytick_length_pt: float = 7.2,
    ytick_width_pt: float = 1.4,
    tick_label_size_pt: float = 9,     # Y and X tick numeric/category labels
    ylabel_size_pt: float | None = 13, # Y-axis title (e.g. "Score"); None = tick size
    xlabel_size_pt: float | None = None,  # X-axis title; None = tick size
    ylabel_pad_pt: float = 3,
    xlabel_pad_pt: float = 6,
    clean_y_ticks: bool = True,
    bold: bool = False,
):
    """Apply Prism styling to ``ax``.

    All point sizes / widths are in the final (post-downscale) image. Pass
    ``scale`` > 1 when rendering at an upscaled size so sizes multiply up.
    """
    for s in hide_spines:
        ax.spines[s].set_visible(False)
    for s in ("top", "bottom", "left", "right"):
        if s not in hide_spines:
            ax.spines[s].set_linewidth(spine_width_pt * scale)
            ax.spines[s].set_color("black")

    ax.tick_params(
        axis="y",
        direction="out",
        length=ytick_length_pt * scale,
        width=ytick_width_pt * scale,
        color="black",
        labelsize=tick_label_size_pt * scale,
        pad=4 * scale,
    )

    if show_xticks:
        ax.tick_params(
            axis="x", direction="out",
            length=ytick_length_pt * scale,
            width=ytick_width_pt * scale,
            color="black",
            labelsize=tick_label_size_pt * scale,
            pad=xlabel_pad_pt * scale,
        )
    else:
        ax.tick_params(
            axis="x", length=0, width=0,
            labelsize=tick_label_size_pt * scale,
            pad=xlabel_pad_pt * scale,
        )

    fp_tick = helvetica(tick_label_size_pt * scale, bold=bold)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(fp_tick)

    ylabel_sz = ylabel_size_pt if ylabel_size_pt is not None else tick_label_size_pt
    xlabel_sz = xlabel_size_pt if xlabel_size_pt is not None else tick_label_size_pt
    ax.yaxis.label.set_fontproperties(helvetica(ylabel_sz * scale, bold=bold))
    ax.yaxis.labelpad = ylabel_pad_pt * scale
    ax.xaxis.label.set_fontproperties(helvetica(xlabel_sz * scale, bold=bold))
    ax.xaxis.labelpad = xlabel_pad_pt * scale

    if clean_y_ticks:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_clean_y_tick))

    return dict(scale=scale, fp_bold=helvetica_bold)


def render_at_scale(
    plot_fn,
    target_figsize_in,
    out_path,
    *,
    scale: int = 4,
    dpi: int = 600,
    transparent: bool = True,
    axes_rect=None,
):
    """Render at ``scale × target_figsize`` then downscale to ``target × dpi`` px.

    ``plot_fn(fig, ax, scale)`` draws the content. ``axes_rect`` (normalized
    ``[left, bottom, width, height]``) lets you fix the axes position so the
    figure size is predictable regardless of tick/label extents.
    """
    from PIL import Image

    target_w, target_h = target_figsize_in
    big_size = (target_w * scale, target_h * scale)

    fig = plt.figure(figsize=big_size, dpi=dpi)
    if axes_rect is None:
        ax = fig.add_subplot(111)
    else:
        ax = fig.add_axes(list(axes_rect))
    plot_fn(fig, ax, scale=scale)

    tmp = NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    # Force NO bbox cropping — we want the figure to save at exactly big_size
    # so the pixel→inch mapping is predictable for the downscale. The project's
    # figure_config sets savefig.bbox='tight' globally, so we have to override.
    from matplotlib.transforms import Bbox
    full_bbox = Bbox.from_bounds(0, 0, *big_size)
    fig.savefig(tmp.name, dpi=dpi, transparent=transparent,
                bbox_inches=full_bbox, pad_inches=0)
    plt.close(fig)

    target_px = (int(round(target_w * dpi)), int(round(target_h * dpi)))
    im = Image.open(tmp.name)
    resized = im.resize(target_px, Image.LANCZOS)
    resized.save(out_path, dpi=(dpi, dpi))
    os.remove(tmp.name)
    return Path(out_path)
