"""Output paths for the Prism panel pipeline.

PNGs and their paired data files are written into the Remake sources tree
(`Output/PowerPoint_Figures_Remake/sources/Fig_N/`) so that everything for
a given figure — original tracked content, Prism re-renders, and the data
behind both — sits in one folder per figure.

Bootstrap-band CSV cache is kept under Prism_Style/bands_cache/ because
it's an internal cache, not user-facing data.
"""

from __future__ import annotations
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
REMAKE_SOURCES = PROJECT_ROOT / "Output" / "PowerPoint_Figures_Remake" / "sources"


def panel_dir(fig_num: int) -> Path:
    """Where each figure's panel PNGs + data files live."""
    d = REMAKE_SOURCES / f"Fig_{fig_num}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def panel_png(fig_num: int, letter: str) -> Path:
    return panel_dir(fig_num) / f"Fig_{fig_num}{letter}_prism.png"


def panel_data(fig_num: int, letter: str) -> Path:
    return panel_dir(fig_num) / f"Fig_{fig_num}{letter}_prism_data.xlsx"


def panel_legend_png(fig_num: int, letter: str) -> Path:
    return panel_dir(fig_num) / f"Fig_{fig_num}{letter}_prism_legend.png"
