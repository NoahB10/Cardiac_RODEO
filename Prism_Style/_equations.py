"""Canonical PK-PD equation names + shared color map for Fig 3 panels.

Used by both `generate_r2_bar.py` and `generate_loocv_scatter.py` so the
12 equations have identical colors across both panels.

Canonical names match the snake_case identifiers used in
`Output/PowerPoint_Figures/Fig_3/Fig_3d_data.xlsx`. The pretty display
names in `Fig_3c_data.xlsx` are mapped via `PRETTY_TO_CANONICAL`.
"""

from __future__ import annotations

import matplotlib.cm as mcm


# Alphabetical order — defines the color sequence (turbo palette).
EQUATIONS = [
    "adaptive_response",
    "biphasic_response",
    "bivariate_gaussian",
    "cumulative_exposure",
    "dual_exponential",
    "gaussian_hill_hybrid",
    "gaussian_ridge",
    "hormesis_v0",
    "modified_hill_hormesis",
    "modified_hill_simple",
    "pkpd_elimination",
    "recovery_model",
]


# Pretty display name (used in Fig 3c) -> canonical snake_case name.
PRETTY_TO_CANONICAL = {
    "Adaptive Response":     "adaptive_response",
    "Biphasic Response":     "biphasic_response",
    "Bivariate Gaussian":    "bivariate_gaussian",
    "Cumulative Exposure":   "cumulative_exposure",
    "Dual Exponential":      "dual_exponential",
    "Dual Hill Hormesis":    "modified_hill_hormesis",
    "Gaussian Ridge":        "gaussian_ridge",
    "Gaussian-Hill Hybrid":  "gaussian_hill_hybrid",
    "Hormesis Hill":         "hormesis_v0",
    "Modified Hill":         "modified_hill_simple",
    "PKPD Elimination":      "pkpd_elimination",
    "Recovery Model":        "recovery_model",
}


def equation_color_map(cmap_name: str = "turbo") -> dict[str, tuple]:
    """canonical_name -> RGBA tuple. Order matches `EQUATIONS`."""
    cmap = mcm.get_cmap(cmap_name)
    n = len(EQUATIONS)
    return {eq: cmap(0.05 + 0.90 * (i / max(1, n - 1)))
            for i, eq in enumerate(EQUATIONS)}


def color_for_pretty(name: str, cmap_name: str = "turbo"):
    """Look up the color for an equation by its pretty (Fig 3c) name."""
    canonical = PRETTY_TO_CANONICAL[name]
    return equation_color_map(cmap_name)[canonical]
