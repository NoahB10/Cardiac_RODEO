#!/usr/bin/env python3
"""
generate_axisless_figures.py — Regenerate all publication figures without axes.

Saves to Axisless subfolders within each Fig_X directory.
Removes: axis labels, titles, tick labels, tick marks, spines, grid
Keeps:   legends, data annotations (e.g. confusion matrix cell values), plot content

Usage:
    python generate_axisless_figures.py --all              # All figures
    python generate_axisless_figures.py --figure 6         # Specific figure
    python generate_axisless_figures.py --5x5              # Just 5x5 surface grids
    python generate_axisless_figures.py --quick            # Skip 5x5 grids (faster)
"""

import sys
from pathlib import Path
import argparse

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'Output' / 'PowerPoint_Figures'))

import figure_config  # Register Helvetica font — must be first
import matplotlib
import matplotlib.figure
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import NullFormatter


FIGURES_DIR = PROJECT_ROOT / 'Output' / 'PowerPoint_Figures'
SAVE_DPI = 600


# ============================================================================
# CORE: Strip all axis decorations from a matplotlib figure
# ============================================================================

def strip_axes(fig):
    """
    Strip all axis decorations from every axes in a figure.

    Removes: axis labels, titles, tick labels, tick marks, spines, grid lines
    Keeps:   legends, data annotations (ax.text), plotted content, colorbars (colors only),
             the figure/axes background fill (white stays white — we just crop tight)
    """
    for ax in fig.get_axes():
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.set_title('')

        is_3d = hasattr(ax, 'zaxis')

        if is_3d:
            ax.set_zlabel('')
            # Remove text2D elements (titles and labels added via ax.text2D)
            for text in list(ax.texts):
                text.set_visible(False)
            # Remove tick formatters and marks
            ax.xaxis.set_major_formatter(NullFormatter())
            ax.yaxis.set_major_formatter(NullFormatter())
            ax.zaxis.set_major_formatter(NullFormatter())
            ax.tick_params(axis='x', which='both', length=0)
            ax.tick_params(axis='y', which='both', length=0)
            ax.tick_params(axis='z', which='both', length=0)
        else:
            # 2D axes: remove spines, ticks, grid
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(left=False, bottom=False, top=False, right=False,
                           labelleft=False, labelbottom=False,
                           labeltop=False, labelright=False)
            ax.grid(False)


# ============================================================================
# MONKEY-PATCH: Intercept Figure.savefig to also produce axisless versions
# ============================================================================

# Per-panel axisless-height overrides (in centimetres). The saved axisless PNG
# will be resized (aspect preserved) to match these heights. Add entries here
# when a specific panel must land at an exact size in the layout.
AXISLESS_HEIGHT_OVERRIDES_CM = {
    'Fig_6c.png': 3.56,
}

_orig_savefig = matplotlib.figure.Figure.savefig
_savefig_active = False  # Guard against recursion


def _patched_savefig(self, fname, *args, **kwargs):
    """Intercept all fig.savefig() calls to also produce axisless versions."""
    global _savefig_active

    # Save original normally
    _orig_savefig(self, fname, *args, **kwargs)

    # Guard: don't recurse when we call savefig for the axisless version
    if _savefig_active:
        return

    fname_path = Path(str(fname))

    # Only process PNGs saved to Fig_X directories
    if fname_path.suffix.lower() != '.png':
        return
    if 'Fig_' not in str(fname_path):
        return
    # Skip if already saving to an Axisless folder
    if 'Axisless' in str(fname_path):
        return

    # Determine axisless output path
    axisless_dir = fname_path.parent / 'Axisless'
    axisless_dir.mkdir(parents=True, exist_ok=True)
    axisless_path = axisless_dir / fname_path.name

    # Strip axes and save axisless version sized to the plot-area bbox only.
    # The axisless image must match the axes rectangle exactly, so that
    # when it's overlaid on the with-axis image, it lines up pixel-perfect
    # with the inside of the axes — no margin for labels/ticks, but all
    # whitespace *inside* the axes preserved.
    strip_axes(self)
    axisless_kwargs = dict(kwargs)
    plot_bbox = _main_axes_bbox_in_inches(self)
    if plot_bbox is not None:
        axisless_kwargs['bbox_inches'] = plot_bbox
        axisless_kwargs['pad_inches'] = 0
    else:
        # Fallback: no axes found, use tight
        axisless_kwargs['bbox_inches'] = 'tight'
        axisless_kwargs['pad_inches'] = 0
    _savefig_active = True
    try:
        _orig_savefig(self, str(axisless_path), *args, **axisless_kwargs)
        _apply_height_override(axisless_path)
        print(f"  Saved axisless: {axisless_path}")

        # For heatmaps: also save body and colorbar as separate images
        if 'eatmap' in fname_path.stem:
            _split_heatmap_colorbar(self, axisless_path, *args, **axisless_kwargs)
    finally:
        _savefig_active = False


def _apply_height_override(axisless_path):
    """If this panel has an entry in AXISLESS_HEIGHT_OVERRIDES_CM, resize the
    saved axisless PNG to that exact height (aspect preserved)."""
    target_cm = AXISLESS_HEIGHT_OVERRIDES_CM.get(axisless_path.name)
    if not target_cm:
        return
    try:
        from PIL import Image
        im = Image.open(axisless_path)
        dpi = im.info.get('dpi', (SAVE_DPI, SAVE_DPI))[1]
        target_px = int(round(target_cm / 2.54 * dpi))
        if im.size[1] == target_px:
            return
        scale = target_px / im.size[1]
        new_size = (int(round(im.size[0] * scale)), target_px)
        resized = im.resize(new_size, Image.LANCZOS)
        resized.save(axisless_path, dpi=(dpi, dpi))
    except Exception as e:
        print(f"  (height override failed for {axisless_path.name}: {e})")


def _main_axes_bbox_in_inches(fig):
    """Return the primary data-axes bbox in figure-inch coords, or None.

    For figures with a single axes this is that axes. For figures with
    multiple axes (e.g. heatmap + colorbar), we return the union of the
    non-colorbar axes — i.e. every axes whose width is not the narrowest.
    """
    axes = fig.get_axes()
    if not axes:
        return None
    # Identify colorbar-like axes (narrowest; skip from main region).
    widths = sorted(((ax.get_position().width, i, ax) for i, ax in enumerate(axes)),
                    key=lambda t: t[0])
    if len(axes) >= 2 and widths[0][0] < widths[-1][0] * 0.25:
        main_axes = [t[2] for t in widths[1:]]
    else:
        main_axes = axes

    # Union of display-coord bboxes, then convert to inches
    bboxes = []
    for ax in main_axes:
        try:
            bboxes.append(ax.get_window_extent())
        except Exception:
            continue
    if not bboxes:
        return None
    from matplotlib.transforms import Bbox
    union = Bbox.union(bboxes)
    return union.transformed(fig.dpi_scale_trans.inverted())


def _split_heatmap_colorbar(fig, axisless_path, *args, **kwargs):
    """Split a heatmap figure into body (no colorbar) and colorbar-only images."""
    all_axes = fig.get_axes()
    if len(all_axes) < 2:
        return

    # Identify colorbar axis: the narrowest one (width in figure coords)
    ax_widths = []
    for ax in all_axes:
        bbox = ax.get_position()
        ax_widths.append((bbox.width, ax))
    ax_widths.sort(key=lambda x: x[0])
    cbar_ax = ax_widths[0][1]  # narrowest = colorbar
    main_axes = [ax for _, ax in ax_widths[1:]]

    stem = axisless_path.stem
    parent = axisless_path.parent

    # Save heatmap body only (hide colorbar)
    cbar_ax.set_visible(False)
    body_path = parent / f"{stem}_no_cbar.png"
    _orig_savefig(fig, str(body_path), *args, **kwargs)
    print(f"  Saved heatmap body: {body_path}")
    cbar_ax.set_visible(True)

    # Save colorbar only (hide main axes)
    for ax in main_axes:
        ax.set_visible(False)
    cbar_path = parent / f"{stem}_colorbar.png"
    _orig_savefig(fig, str(cbar_path), *args, **kwargs)
    print(f"  Saved colorbar: {cbar_path}")
    for ax in main_axes:
        ax.set_visible(True)


# Apply the patch
matplotlib.figure.Figure.savefig = _patched_savefig


# ============================================================================
# 5x5 GRID: Generate axisless individual 3D surface plots
# ============================================================================

def generate_axisless_5x5():
    """Generate 5x5 grid surface plots with ALL axis elements stripped."""
    import generate_5x5_individual as g5x5
    from matplotlib.colors import Normalize

    print("\n=== Generating Axisless 5x5 Surface Grids ===")

    df_raw = g5x5.load_data()
    df_con = g5x5.extract_coefficients(df_raw, 'Contractility')
    df_o2 = g5x5.extract_coefficients(df_raw, 'O2')
    df_con = g5x5.filter_valid(df_con)
    df_o2 = g5x5.filter_valid(df_o2)

    o2_vmax = 35
    con_vmax = 0.04
    o2_zmax = g5x5.calculate_global_range(df_o2)
    con_zmax = g5x5.calculate_global_range(df_con)

    configs = [
        (df_o2,  'O2',            1,   o2_vmax,  o2_zmax,  '4'),
        (df_con, 'Contractility', 100, con_vmax, con_zmax, '5'),
    ]

    dose_ratio = np.linspace(0, 2, 60)
    time = np.linspace(0, 96, 60)
    T, Dr = np.meshgrid(time, dose_ratio)

    for df, resp_type, scale, vmax, zmax, fig_num in configs:
        vmax_s = vmax * scale
        zmax_s = zmax * scale
        norm = Normalize(vmin=0, vmax=vmax_s)

        out_dir = FIGURES_DIR / f'Fig_{fig_num}' / f'{resp_type}_5x5_Individual_Axisless'
        out_dir.mkdir(parents=True, exist_ok=True)

        sorted_drugs = df.sort_values('Drug').head(25)
        print(f"\n  {resp_type} -> {out_dir.name}")

        for i, (idx, row_data) in enumerate(sorted_drugs.iterrows()):
            if i >= 25:
                break

            drug_name = str(row_data['Drug'])
            Response = g5x5.pkpd_elimination_response(
                Dr, T, row_data['R0'], row_data['Emax'], row_data['kappa'],
                row_data['n'], row_data['m'], row_data['tau'], row_data['k_elim'])
            Response = (Response - row_data['R0']) * scale
            Response = np.clip(Response, 0, zmax_s)

            fig = plt.figure(figsize=(7, 7.5))
            ax = fig.add_subplot(111, projection='3d', computed_zorder=False)

            ax.plot_surface(T, Dr, Response, cmap='turbo', norm=norm,
                            alpha=0.9, linewidth=0, antialiased=True)

            ax.view_init(elev=25, azim=-158)
            ax.set_xlim(0, 96)
            ax.set_ylim(0, 2)
            ax.set_zlim(0, zmax_s)

            # Transparent panes, keep grid for depth
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.grid(True, alpha=0.2)

            # Strip ALL axis elements
            ax.set_xlabel('')
            ax.set_ylabel('')
            ax.set_zlabel('')
            ax.xaxis.set_major_formatter(NullFormatter())
            ax.yaxis.set_major_formatter(NullFormatter())
            ax.zaxis.set_major_formatter(NullFormatter())
            ax.tick_params(axis='x', which='both', length=0)
            ax.tick_params(axis='y', which='both', length=0)
            ax.tick_params(axis='z', which='both', length=0)

            plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)

            safe_name = drug_name.replace(' ', '_').replace('/', '_')
            safe_name = ''.join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
            filename = f"{i:02d}_{safe_name}.png"
            filepath = out_dir / filename

            # Save directly (the savefig patch is bypassed for Axisless paths)
            _orig_savefig(fig, str(filepath), dpi=600, bbox_inches='tight',
                          facecolor='none', edgecolor='none', transparent=True,
                          pad_inches=0.02)
            plt.close(fig)

            if (i + 1) % 5 == 0:
                print(f"    Saved {i + 1}/25")

        print(f"    Done: {out_dir}")


# ============================================================================
# POST-PROCESSING: catch subprocess-generated PNGs missed by the monkey-patch
# ============================================================================

def _backfill_axisless(fig_dir):
    """For any PNGs in fig_dir without an Axisless counterpart, create one.

    This handles images generated by subprocess calls (which bypass the
    monkey-patch). Loads the original, renders it in a frameless figure,
    and saves to the Axisless/ subfolder.
    """
    axisless_dir = fig_dir / 'Axisless'
    if not fig_dir.exists():
        return

    existing_axisless = set()
    if axisless_dir.exists():
        existing_axisless = {f.name for f in axisless_dir.glob('*.png')}

    for png in sorted(fig_dir.glob('*.png')):
        if png.name in existing_axisless:
            continue
        # Skip variant/alternate files
        if any(tag in png.name for tag in ('_with_pct', '_with_stats', '_alternate',
                                            '_NoTitle', '_Option', 'placeholder')):
            continue

        axisless_dir.mkdir(parents=True, exist_ok=True)
        from PIL import Image as PILImage
        img = PILImage.open(png)
        w_px, h_px = img.size
        dpi = img.info.get('dpi', (600, 600))
        dpi_val = dpi[0]

        fig_w = w_px / dpi_val
        fig_h = h_px / dpi_val
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        ax.imshow(np.array(img))
        ax.axis('off')
        ax.set_position([0, 0, 1, 1])

        out_path = axisless_dir / png.name
        _orig_savefig(fig, str(out_path), dpi=dpi_val,
                      bbox_inches='tight', pad_inches=0, facecolor='white')
        plt.close(fig)
        print(f"  Backfilled axisless: {out_path}")


# ============================================================================
# FIGURE DISPATCH
# ============================================================================

import generate_paper_figures as gpf


def _axisless_generate_fig_4_5():
    """Override: generate 5x5 grids axisless instead of calling subprocess."""
    generate_axisless_5x5()


def generate_all(skip_5x5=False):
    """Generate all axisless figures."""
    # Override fig 4/5 to use our axisless generator
    if not skip_5x5:
        gpf.generate_fig_4_5 = _axisless_generate_fig_4_5

    print("=" * 60)
    print("Generating Axisless Figures -> Axisless folders")
    print("=" * 60)

    figures_dir = gpf.FIGURES_DIR

    gpf.generate_fig_1()
    _backfill_axisless(figures_dir / 'Fig_1')
    gpf.generate_fig_2()
    _backfill_axisless(figures_dir / 'Fig_2')
    gpf.generate_fig_3()
    _backfill_axisless(figures_dir / 'Fig_3')

    if not skip_5x5:
        gpf.generate_fig_4_5()

    gpf.generate_prediction_figures('Arrhythmia', '6', comparison_type='MoLFormer')
    _backfill_axisless(figures_dir / 'Fig_6')
    gpf.generate_prediction_figures('HeartDamage', '7', comparison_type='ADMET')
    _backfill_axisless(figures_dir / 'Fig_7')
    gpf.generate_prediction_figures('ConcernBinary', '8', comparison_type=None)
    _backfill_axisless(figures_dir / 'Fig_8')

    gpf.generate_supplements()
    for s in ('Fig_S1', 'Fig_S2', 'Fig_S3', 'Fig_S4'):
        _backfill_axisless(figures_dir / s)

    print("\n" + "=" * 60)
    print("All axisless figures generated!")
    print("=" * 60)


def generate_figure(fig_num):
    """Generate a specific figure's axisless version."""
    figures_dir = gpf.FIGURES_DIR
    fig_num = str(fig_num)
    if fig_num == '1':
        gpf.generate_fig_1()
        _backfill_axisless(figures_dir / 'Fig_1')
    elif fig_num == '2':
        gpf.generate_fig_2()
        _backfill_axisless(figures_dir / 'Fig_2')
    elif fig_num == '3':
        gpf.generate_fig_3()
        _backfill_axisless(figures_dir / 'Fig_3')
    elif fig_num in ('4', '5'):
        generate_axisless_5x5()
    elif fig_num == '6':
        gpf.generate_prediction_figures('Arrhythmia', '6', comparison_type='MoLFormer')
        _backfill_axisless(figures_dir / 'Fig_6')
    elif fig_num == '7':
        gpf.generate_prediction_figures('HeartDamage', '7', comparison_type='ADMET')
        _backfill_axisless(figures_dir / 'Fig_7')
    elif fig_num == '8':
        gpf.generate_prediction_figures('ConcernBinary', '8', comparison_type=None)
        _backfill_axisless(figures_dir / 'Fig_8')
    elif fig_num.upper().startswith('S'):
        gpf.generate_supplements()
        for s in ('Fig_S1', 'Fig_S2', 'Fig_S3', 'Fig_S4'):
            _backfill_axisless(figures_dir / s)
    else:
        print(f"Unknown figure: {fig_num}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate axisless publication figures (Axisless folders)')
    parser.add_argument('--all', action='store_true',
                        help='Generate all figures')
    parser.add_argument('--figure', type=str, default=None,
                        help='Generate specific figure (e.g. 6, S1)')
    parser.add_argument('--5x5', dest='fivex5', action='store_true',
                        help='Generate only the 5x5 surface grids')
    parser.add_argument('--quick', action='store_true',
                        help='All figures except 5x5 grids (faster)')
    args = parser.parse_args()

    if args.fivex5:
        generate_axisless_5x5()
    elif args.figure:
        generate_figure(args.figure)
    elif args.quick:
        generate_all(skip_5x5=True)
    elif args.all:
        generate_all()
    else:
        parser.print_help()
        print("\nUse --all to generate everything, --quick to skip 5x5 grids.")


if __name__ == '__main__':
    main()
