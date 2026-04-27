"""Apply the new layout (Prism panels in their new slot mapping) to
`Output/PowerPoint_Figures_Remake/Cardiac_RODEO_Remake.pptx`.

Slide map:
    slide 7  -> Figure 6 (Arrhythmia)
    slide 8  -> Figure 7 (HeartDamage)
    slide 9  -> Figure 8 (ConcernBinary)

Slide 7 already has Panel_6{letter} groups in the right positions — we just
swap the picture INSIDE each group.  Slides 8 and 9 don't have groups, so
we rebuild their picture set from scratch using the same box positions.

Panel letters are placed/aligned per the same layout boxes.  No re-rendering
of Prism PNGs is performed here; if a Prism image's aspect ratio doesn't
match its box exactly, PPT's fit-to-box scaling will preserve aspect (the
image is centred inside the box, with whitespace at the unused dim).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu, Pt, Inches
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from lxml import etree

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _layout import (ROW_LAYOUT, PANEL_ROW, MARGIN_B, CONTENT,
                     LEGEND_STASH_X, LEGEND_STASH_T_BY_LETTER,
                     LEGEND_FILE_BY_LETTER,
                     INPLACE_PANELS, INPLACE_FIG_NUM,
                     RESIZE_TO_NATIVE)  # noqa: E402
from _paths import panel_dir  # noqa: E402
from PIL import Image as _PILImage  # noqa: E402

EMU_PER_INCH = 914400

PPTX_IN  = PROJECT_ROOT / "Output" / "PowerPoint_Figures_Remake" / "Cardiac_RODEO_Remake.pptx"
PPTX_OUT = PROJECT_ROOT / "Output" / "PowerPoint_Figures_Remake" / "Cardiac_RODEO_Remake.pptx"  # in-place

FIGS = (6, 7, 8)


def _find_figure_slides(prs) -> dict[int, list[int]]:
    """Find every slide whose first text matches 'Figure {N}:' or 'Figure {N} '.

    Returns {fig_num: [zero_based_slide_index, ...]} ordered by slide order.
    Re-runnable: doesn't depend on hardcoded slide indices.
    """
    out: dict[int, list[int]] = {}
    for i, sl in enumerate(prs.slides):
        title = ""
        for sp in sl.shapes:
            if sp.has_text_frame and sp.text_frame.text.strip():
                title = sp.text_frame.text.strip()
                break
        for fig in FIGS:
            if title.startswith(f"Figure {fig}:") or title.startswith(f"Figure {fig} "):
                out.setdefault(fig, []).append(i)
                break
    return out

# Letter placement: offsets relative to the box's top-left corner.
LETTER_OFFSET_X_IN = -0.05
LETTER_OFFSET_Y_IN = -0.18
LETTER_BOX_W_IN = 0.30
LETTER_BOX_H_IN = 0.20
LETTER_FONT_PT = 12
LETTER_FONT_BOLD = True

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _swap_picture_source(sp, new_image_path: Path) -> None:
    """Replace the image bytes behind a python-pptx Picture, keeping its bbox."""
    a_ns = NS["a"]; r_ns = NS["r"]
    blip = sp._element.find(f".//{{{a_ns}}}blip")
    if blip is None:
        raise RuntimeError(f"no blip on shape {sp.name}")
    rid = blip.attrib.get(f"{{{r_ns}}}embed")
    rel = sp.part.rels[rid]
    rel.target_part._blob = Path(new_image_path).read_bytes()


def _delete_shape(slide, shape):
    sp = shape._element
    sp.getparent().remove(sp)


def _add_letter(slide, letter: str, position_in: tuple[float, float]):
    L, T = position_in
    x = (L + LETTER_OFFSET_X_IN) * EMU_PER_INCH
    y = (T + LETTER_OFFSET_Y_IN) * EMU_PER_INCH
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    tb = slide.shapes.add_textbox(int(x), int(y),
                                  int(LETTER_BOX_W_IN * EMU_PER_INCH),
                                  int(LETTER_BOX_H_IN * EMU_PER_INCH))
    tb.name = f"PanelLetter_{letter}"
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = letter
    run.font.name = "Helvetica"
    run.font.size = Pt(LETTER_FONT_PT)
    run.font.bold = LETTER_FONT_BOLD
    run.font.color.rgb = RGBColor(0, 0, 0)


def _native_size_in(image_path: Path) -> tuple[float, float]:
    """Read the PNG's native size in INCHES from its embedded DPI metadata."""
    im = _PILImage.open(image_path)
    dpi = im.info.get("dpi", (600, 600))[0]
    return im.size[0] / dpi, im.size[1] / dpi


def _add_picture(slide, image_path: Path, position_in: tuple[float, float]):
    """Place picture at native size — no width/height override = no stretching."""
    L, T = position_in
    w_in, h_in = _native_size_in(image_path)
    return slide.shapes.add_picture(
        str(image_path),
        Inches(L), Inches(T),
        width=Inches(w_in), height=Inches(h_in),
    )


def _is_any_picture(shape):
    """Any picture shape — used to wipe everything image-shaped on a figure
    slide before rebuilding.  Catches small legend PNGs that fall below the
    old 0.5" 'panel picture' threshold."""
    return shape.shape_type == MSO_SHAPE_TYPE.PICTURE


def _is_panel_letter(shape):
    if not (shape.has_text_frame and shape.text_frame.text.strip()):
        return False
    txt = shape.text_frame.text.strip()
    return (len(txt) == 1 and txt.lower() in "abcdefghijk"
            and shape.name.startswith(("PanelLetter_", "Label_")))


def _compute_picture_top(letter: str, image_h_in: float) -> float:
    """Top position so this panel's plot bottom sits at its row's plot_bottom.

    plot_bottom = T + image_h - margin_b   =>   T = plot_bottom + margin_b - image_h
    """
    row = ROW_LAYOUT[PANEL_ROW[letter]]
    return row["plot_bottom"] + MARGIN_B[letter] - image_h_in


def update_slide_loose(slide, fig_num: int):
    """Wipe ALL pictures + panel letters + groups, then rebuild from
    ROW_LAYOUT + CONTENT. Title text boxes are preserved.

    Removing ALL pictures (not just 'large' ones) prevents legend PNGs from
    accumulating across re-runs.
    """
    for shape in list(slide.shapes):
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            _delete_shape(slide, shape)
    for shape in list(slide.shapes):
        if _is_any_picture(shape):
            _delete_shape(slide, shape)
        elif _is_panel_letter(shape):
            _delete_shape(slide, shape)

    panel_positions: dict[str, tuple[float, float, float, float]] = {}
    for name in sorted(CONTENT[fig_num].keys()):
        letter = name[-1]
        png_name = CONTENT[fig_num][name]
        png = panel_dir(fig_num) / png_name
        if not png.exists():
            print(f"  [WARN] missing source {png.name} for {name}")
            continue
        w_in, h_in = _native_size_in(png)
        row = ROW_LAYOUT[PANEL_ROW[letter]]
        L = row["lefts"][letter]
        T = _compute_picture_top(letter, h_in)
        _add_picture(slide, png, (L, T))
        # Letter sits at row.letter_top (uniform within row).
        _add_letter(slide, letter, (L, row["letter_top"] - LETTER_OFFSET_Y_IN))
        panel_positions[letter] = (L, T, w_in, h_in)
        plot_bottom = T + h_in - MARGIN_B[letter]
        print(f"  add {name:12s} <- {png_name}  pos=({L:.2f},{T:.2f}) "
              f"native={w_in:.2f}x{h_in:.2f}\"  plot_bottom={plot_bottom:.2f}")

    # Legend overlays — stashed in the off-slide grey area (L > slide width)
    # so the user can drag each one onto the panel manually.  Only one of
    # each legend per slide; on re-runs the wipe step above clears any
    # prior copies.
    for legend_letter, suffix in LEGEND_FILE_BY_LETTER.items():
        if legend_letter not in panel_positions:
            continue
        legend_png = panel_dir(fig_num) / f"Fig_{fig_num}{suffix}"
        if not legend_png.exists():
            print(f"  [SKIP legend] missing {legend_png.name}")
            continue
        legend_L = LEGEND_STASH_X
        legend_T = LEGEND_STASH_T_BY_LETTER[legend_letter]
        _add_picture(slide, legend_png, (legend_L, legend_T))
        leg_w, leg_h = _native_size_in(legend_png)
        print(f"  stash legend <- {legend_png.name}  "
              f"pos=({legend_L:.2f},{legend_T:.2f}) (off-slide) "
              f"native={leg_w:.2f}x{leg_h:.2f}\"")


def _delete_slide(prs, slide_idx_zero_based: int):
    """Remove a slide from the presentation by 0-based index."""
    rId = prs.slides._sldIdLst[slide_idx_zero_based].rId
    prs.part.drop_rel(rId)
    del prs.slides._sldIdLst[slide_idx_zero_based]


def _walk_pictures(shapes):
    """Yield every picture shape, descending into groups."""
    for sp in shapes:
        if sp.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _walk_pictures(sp.shapes)
        elif sp.shape_type == MSO_SHAPE_TYPE.PICTURE:
            yield sp


def update_inplace_panels(prs, *, position_tol_in: float = 0.05):
    """Swap source bytes for in-place panel pictures on slides 2 and 3.

    Covers heatmaps AND line/sigmoid background panels — anything where the
    user has already placed the picture frame manually. The picture frames
    are identified by their (left_in, top_in) position; we don't move or
    resize them. Works for free-standing pictures AND for the BACKGROUND
    picture inside a group (whose left/top sits at the group origin).

    If a frame at the expected position isn't found, we log a warning and
    skip — the user may have repositioned it, in which case the swap should
    be redone manually.
    """
    for (slide_1based, letter), (exp_L, exp_T, png_name) in INPLACE_PANELS.items():
        if slide_1based - 1 >= len(prs.slides):
            print(f"  [SKIP] slide {slide_1based} out of range "
                  f"(deck has {len(prs.slides)})")
            continue
        slide = prs.slides[slide_1based - 1]
        fig_num = INPLACE_FIG_NUM[slide_1based]
        png_path = panel_dir(fig_num) / png_name
        if not png_path.exists():
            print(f"  [SKIP] {png_name} not found at {png_path}")
            continue

        match = None
        for sp in _walk_pictures(slide.shapes):
            L = sp.left / EMU_PER_INCH
            T = sp.top / EMU_PER_INCH
            if abs(L - exp_L) <= position_tol_in and abs(T - exp_T) <= position_tol_in:
                match = sp
                break

        if match is None:
            print(f"  [WARN] slide {slide_1based} panel {letter}: no picture "
                  f"frame at ({exp_L:.2f}, {exp_T:.2f})")
            continue

        _swap_picture_source(match, png_path)
        if (slide_1based, letter) in RESIZE_TO_NATIVE:
            new_w_in, new_h_in = _native_size_in(png_path)
            match.width = Inches(new_w_in)
            match.height = Inches(new_h_in)
            print(f"  swap+resize slide {slide_1based} panel {letter:s} <- "
                  f"{png_name}  frame=({exp_L:.2f},{exp_T:.2f}) "
                  f"{new_w_in:.2f}x{new_h_in:.2f}\" (native)")
        else:
            w_in = match.width / EMU_PER_INCH
            h_in = match.height / EMU_PER_INCH
            print(f"  swap slide {slide_1based} panel {letter:s} <- {png_name}  "
                  f"frame=({exp_L:.2f},{exp_T:.2f}) {w_in:.2f}x{h_in:.2f}\"")


def main():
    PPTX_OUT.parent.mkdir(parents=True, exist_ok=True)
    if PPTX_IN != PPTX_OUT:
        shutil.copy(PPTX_IN, PPTX_OUT)
    prs = Presentation(str(PPTX_OUT))

    found = _find_figure_slides(prs)
    canonical = {}      # fig_num -> 0-based slide index of the slide we'll keep
    duplicates = []     # 0-based indices to delete (older copies of each fig)
    for fig, idxs in found.items():
        # Prefer the LAST occurrence — that's where any recent edits live
        # (e.g. the user's manual alignment work).
        canonical[fig] = idxs[-1]
        duplicates.extend(idxs[:-1])

    # Phase 1: rebuild canonical slides with plot-base alignment.
    for fig, idx in canonical.items():
        slide = prs.slides[idx]
        print(f"\n=== Slide {idx + 1} (Figure {fig}) ===")
        update_slide_loose(slide, fig)

    # Phase 2: drop duplicate slides AFTER processing so canonical indices
    # don't shift mid-loop. Delete from highest-index first.
    if duplicates:
        print(f"\n=== Removing duplicates: slides "
              f"{[i + 1 for i in duplicates]} ===")
        for idx in sorted(duplicates, reverse=True):
            _delete_slide(prs, idx)
            print(f"  removed slide {idx + 1}")

    # Phase 3: swap in-place panel picture bytes on slides 2 and 3
    # (Figures 2 and 3). Frames stay where the user placed them; the picture
    # bytes get refreshed from the latest Prism PNG.
    print("\n=== In-place panels (slides 2, 3) ===")
    update_inplace_panels(prs)

    prs.save(str(PPTX_OUT))
    print(f"\n[done] -> {PPTX_OUT}")


if __name__ == "__main__":
    main()
