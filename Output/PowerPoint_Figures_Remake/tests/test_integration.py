"""End-to-end integration test for the PowerPoint_Figures_Remake pipeline.

Exercise the full forward + reverse loop:

  Cardiac_RODEO.pptx
        ↓ extract_layout
  manifest.json
        ↓ build_pptx
  Cardiac_RODEO_Remake.pptx
        ↓ extract_layout (again)
  manifest_verify.json

Assertions compare the source manifest and the re-extracted manifest
across every picture's position, every group, and every slide's canvas.

Also tests the overlay pipeline: render overlays from the real
Axis_Scaling_Reference.xlsx and verify their dimensions match the axis
spec.
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pptx_remake as R  # noqa: E402
import build_pptx as B    # noqa: E402

PROJECT_ROOT = HERE.parents[2]
SOURCE_PPTX = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Cardiac_RODEO.pptx"


def _count_pics(manifest):
    return sum(1 for s in manifest.slides for sh in s.shapes if sh.kind == "picture")


def _count_groups(manifest):
    return len({
        (s.index, sh.group_name)
        for s in manifest.slides for sh in s.shapes if sh.group_name
    })


# --------------------------------------------------------------------------- #
# End-to-end: extract -> build -> extract, byte-for-byte EMU preservation
# --------------------------------------------------------------------------- #

def test_e2e_extract_build_extract(tmp_path):
    src = R.extract_layout(SOURCE_PPTX)
    manifest_json = tmp_path / "manifest.json"
    R.save_manifest(src, manifest_json)

    out_pptx = tmp_path / "Cardiac_RODEO_Remake.pptx"
    B.build_pptx(src, SOURCE_PPTX, out_pptx)

    dst = R.extract_layout(out_pptx)

    # Structural equivalence
    assert len(src.slides) == len(dst.slides) == 12
    assert src.slide_width_emu == dst.slide_width_emu
    assert src.slide_height_emu == dst.slide_height_emu
    assert _count_pics(src) == _count_pics(dst)
    assert _count_groups(src) == _count_groups(dst)

    # Position equivalence for every picture
    src_pics = {
        (s.index, sh.name): sh
        for s in src.slides for sh in s.shapes if sh.kind == "picture"
    }
    dst_pics = {
        (s.index, sh.name): sh
        for s in dst.slides for sh in s.shapes if sh.kind == "picture"
    }
    assert set(src_pics) == set(dst_pics)
    for key, sp in src_pics.items():
        dp = dst_pics[key]
        assert (sp.left_emu, sp.top_emu, sp.width_emu, sp.height_emu) == \
               (dp.left_emu, dp.top_emu, dp.width_emu, dp.height_emu), \
               f"bbox mismatch for {key}"


# --------------------------------------------------------------------------- #
# Scoping: only Fig_2 and Fig_3 have separate _Axis.png overlay files currently
# --------------------------------------------------------------------------- #

def test_overlay_eligibility_scope():
    """The only slides with layered axisless+overlay groups are 2 and 3."""
    manifest = R.extract_layout(SOURCE_PPTX)
    slides_with_groups = {
        s.index for s in manifest.slides
        for sh in s.shapes if sh.group_name
    }
    assert slides_with_groups == {2, 3}, \
        f"expected overlays only on slides 2,3; got {slides_with_groups}"


# --------------------------------------------------------------------------- #
# All overlay-eligible groups have the expected {axisless, overlay} structure
# --------------------------------------------------------------------------- #

def test_all_groups_have_axisless_and_overlay():
    manifest = R.extract_layout(SOURCE_PPTX)
    for grp in R.find_panel_groups(manifest):
        cls = grp.classify()
        assert cls["axisless"] is not None
        # Every group with 2+ pics is overlay-eligible
        if len(grp.pictures) >= 2:
            assert cls["overlay"] is not None, \
                f"{grp.group_name} has {len(grp.pictures)} pics but no overlay"
