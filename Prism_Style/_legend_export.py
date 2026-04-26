"""Render a matplotlib legend by itself, as a transparent PNG.

Used for panels whose legend lives OUTSIDE the plot area (6g, 7g, 6h, 7h).
Splitting the legend off lets the user place it independently in PowerPoint.

The figure is sized just big enough for the legend; the legend extent is
measured after layout so the saved image is tight (transparent background,
no whitespace around the legend).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox

DPI = 600


def render_legend_image(handles, *, prop, out_path: Path,
                        scale: int = 4,
                        handlelength: float = 1.4,
                        handletextpad: float = 0.4,
                        labelspacing: float = 0.30,
                        borderpad: float = 0.0,
                        handler_map: dict | None = None,
                        transparent: bool = True) -> Path:
    """Render the given legend handles as a tight standalone PNG.

    `handles` are matplotlib artists with their `label` already set (Line2D,
    Patch, etc.). `prop` is the FontProperties to use for the labels — pass
    helvetica(LEGEND_FONT_PT * scale) so it matches the panel's font.
    """
    out_path = Path(out_path)
    # Big working canvas; we crop to the legend extent before saving.
    fig = plt.figure(figsize=(8.0 * scale, 4.0 * scale), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    legend_kwargs = dict(
        loc="center",
        frameon=False,
        handlelength=handlelength,
        handletextpad=handletextpad,
        labelspacing=labelspacing,
        borderpad=borderpad,
        prop=prop,
    )
    if handler_map is not None:
        legend_kwargs["handler_map"] = handler_map
    leg = ax.legend(handles=handles, **legend_kwargs)
    fig.canvas.draw()

    # Tight bbox in figure-inch coords, with a hair of padding (otherwise
    # antialiased glyph edges sometimes get clipped).
    bbox = leg.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    pad = 0.02 * scale
    bbox = Bbox.from_bounds(
        bbox.x0 - pad, bbox.y0 - pad,
        bbox.width + 2 * pad, bbox.height + 2 * pad,
    )

    fig.savefig(out_path, dpi=DPI, transparent=transparent,
                bbox_inches=bbox, pad_inches=0)
    plt.close(fig)

    # Downscale to "final" size = 1× the working canvas / scale, so the
    # legend's font ends up at LEGEND_FONT_PT pt at DPI.
    from PIL import Image
    im = Image.open(out_path)
    target_px = (max(1, im.size[0] // scale), max(1, im.size[1] // scale))
    resized = im.resize(target_px, Image.LANCZOS)
    resized.save(out_path, dpi=(DPI, DPI))

    return out_path
