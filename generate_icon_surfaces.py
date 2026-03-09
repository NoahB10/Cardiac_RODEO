"""
Generate two icon-style 3D surface plots.
- Smooth, minimal, no axis labels/ticks
- Two distinct surface shapes using the PK-PD elimination equation
- Transparent background, clean icon aesthetic
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "Output" / "3D_Plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pkpd_response(time, dose_ratio, R0, Emax, kappa, n, m, tau, k_elim):
    """PK-PD elimination equation."""
    time = np.maximum(time, 0)
    kappa = max(kappa, 1e-9)
    tau = max(tau, 1e-9)
    k_elim = max(k_elim, 1e-9)
    conc = dose_ratio * np.exp(-k_elim * time)
    return R0 + Emax * (1 - np.exp(-kappa * (conc ** n) * ((time / tau) ** m)))


# Smooth grid
time = np.linspace(0, 96, 120)
dose = np.linspace(0, 2, 120)
T, D = np.meshgrid(time, dose)

# --- Surface 1: Gentle hill (O2-like, warm tones) ---
Z1 = pkpd_response(T, D, R0=10, Emax=30, kappa=0.8, n=1.2, m=1.5, tau=20, k_elim=0.03)

# --- Surface 2: Sharp peak then decay (Contractility-like, cool tones) ---
Z2 = pkpd_response(T, D, R0=0.0, Emax=0.06, kappa=15, n=2.5, m=2.0, tau=8, k_elim=0.12)


def make_icon(Z, cmap_name, filename, elev=28, azim=-155):
    """Render a clean icon-style 3D surface."""
    fig = plt.figure(figsize=(4, 4), dpi=200)
    ax = fig.add_subplot(111, projection='3d')

    # Plot surface
    norm = plt.Normalize(vmin=Z.min(), vmax=Z.max())
    surf = ax.plot_surface(
        T, D, Z,
        cmap=cmap_name,
        norm=norm,
        rstride=2, cstride=2,
        antialiased=True,
        shade=True,
        lightsource=plt.matplotlib.colors.LightSource(azdeg=315, altdeg=45),
        alpha=0.95,
    )

    # Light gray panes for subtle depth
    pane_color = (0.95, 0.95, 0.95, 0.3)
    ax.xaxis.pane.fill = True
    ax.yaxis.pane.fill = True
    ax.zaxis.pane.fill = True
    ax.xaxis.pane.set_facecolor(pane_color)
    ax.yaxis.pane.set_facecolor(pane_color)
    ax.zaxis.pane.set_facecolor(pane_color)

    # Thin dark gray axis edges
    edge_color = (0.4, 0.4, 0.4, 0.8)
    ax.xaxis.pane.set_edgecolor(edge_color)
    ax.yaxis.pane.set_edgecolor(edge_color)
    ax.zaxis.pane.set_edgecolor(edge_color)
    ax.xaxis.pane.set_linewidth(0.8)
    ax.yaxis.pane.set_linewidth(0.8)
    ax.zaxis.pane.set_linewidth(0.8)

    # Thin axis lines
    ax.xaxis.line.set_color(edge_color)
    ax.yaxis.line.set_color(edge_color)
    ax.zaxis.line.set_color(edge_color)
    ax.xaxis.line.set_linewidth(0.8)
    ax.yaxis.line.set_linewidth(0.8)
    ax.zaxis.line.set_linewidth(0.8)

    # Simple background grid on the panes
    grid_color = (0.75, 0.75, 0.75, 0.4)
    ax.xaxis._axinfo['grid'].update({'color': grid_color, 'linewidth': 0.4})
    ax.yaxis._axinfo['grid'].update({'color': grid_color, 'linewidth': 0.4})
    ax.zaxis._axinfo['grid'].update({'color': grid_color, 'linewidth': 0.4})
    # Place ~6 grid lines per axis for small squares
    x_range = [T.min(), T.max()]
    y_range = [D.min(), D.max()]
    z_range = [Z.min(), Z.max()]
    ax.set_xticks(np.linspace(x_range[0], x_range[1], 7))
    ax.set_yticks(np.linspace(y_range[0], y_range[1], 7))
    ax.set_zticks(np.linspace(z_range[0], z_range[1], 7))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])
    ax.tick_params(length=0)  # hide tick marks

    # Simple axis label on x only
    ax.set_xlabel('Time (h)', fontsize=7, labelpad=-8, color=(0.3, 0.3, 0.3))

    ax.view_init(elev=elev, azim=azim)
    ax.set_box_aspect([1.2, 1.0, 0.7])

    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    out = OUTPUT_DIR / filename
    fig.savefig(out, dpi=200, transparent=True)
    plt.close(fig)
    print(f"Saved: {out}")


make_icon(Z1, 'coolwarm', 'icon_surface_warm.png')
make_icon(Z2, 'viridis', 'icon_surface_cool.png')

print("Done — 2 icon surfaces generated.")
