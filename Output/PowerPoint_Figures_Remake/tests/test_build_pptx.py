"""Tests for Phase 3: build_pptx.

The MVP build_pptx copies the source pptx and substitutes images as
requested. The extract-then-rebuild path proves the round-trip: every
picture's EMU bbox is preserved bit-for-bit.
"""

import sys
from pathlib import Path

import pytest
from PIL import Image

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pptx_remake as R  # noqa: E402
import build_pptx as B    # noqa: E402

PROJECT_ROOT = HERE.parents[2]
PPTX = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Cardiac_RODEO.pptx"


@pytest.fixture(scope="module")
def source_manifest():
    return R.extract_layout(PPTX)


def test_clone_preserves_slide_count(tmp_path, source_manifest):
    out = tmp_path / "clone.pptx"
    B.build_pptx(source_manifest, PPTX, out)
    re_extracted = R.extract_layout(out)
    assert len(re_extracted.slides) == len(source_manifest.slides)


def test_clone_preserves_canvas_size(tmp_path, source_manifest):
    out = tmp_path / "clone.pptx"
    B.build_pptx(source_manifest, PPTX, out)
    re_extracted = R.extract_layout(out)
    assert re_extracted.slide_width_emu == source_manifest.slide_width_emu
    assert re_extracted.slide_height_emu == source_manifest.slide_height_emu


def test_clone_preserves_picture_positions(tmp_path, source_manifest):
    """Every picture's (left, top, width, height) in EMU must round-trip exactly."""
    out = tmp_path / "clone.pptx"
    B.build_pptx(source_manifest, PPTX, out)
    re_extracted = R.extract_layout(out)

    def index_pics(m):
        return {
            (s.index, sh.name): sh
            for s in m.slides for sh in s.shapes if sh.kind == "picture"
        }

    src = index_pics(source_manifest)
    dst = index_pics(re_extracted)
    assert set(src.keys()) == set(dst.keys()), \
        "picture set differs after round-trip"
    diffs = []
    for key, s_sh in src.items():
        d_sh = dst[key]
        for attr in ("left_emu", "top_emu", "width_emu", "height_emu"):
            if getattr(s_sh, attr) != getattr(d_sh, attr):
                diffs.append(f"{key} {attr}: {getattr(s_sh, attr)} -> {getattr(d_sh, attr)}")
    assert not diffs, "\n".join(diffs[:5])


def test_clone_preserves_groups(tmp_path, source_manifest):
    """Picture groups must survive round-trip."""
    out = tmp_path / "clone.pptx"
    B.build_pptx(source_manifest, PPTX, out)
    re_extracted = R.extract_layout(out)

    def group_counts(m):
        d = {}
        for s in m.slides:
            groups = {sh.group_name for sh in s.shapes if sh.group_name}
            d[s.index] = len(groups)
        return d

    assert group_counts(source_manifest) == group_counts(re_extracted)


def test_picture_swap(tmp_path, source_manifest):
    """Swapping a picture's blob must preserve its bbox but change the image bytes."""
    out = tmp_path / "swap.pptx"

    # Use one of our rendered overlays as the replacement
    overlay = HERE.parent / "overlays" / "Fig_2" / "Fig_2g_Epirubicin_O2_overlay.png"
    if not overlay.exists():
        pytest.skip(f"need rendered overlay at {overlay}")

    # Find a picture on slide 1 to swap (the simplest single-pic slide)
    target_name = None
    for s in source_manifest.slides:
        if s.index == 1:
            for sh in s.shapes:
                if sh.kind == "picture":
                    target_name = sh.name
                    break
    assert target_name is not None, "no picture on slide 1?"

    B.build_pptx(source_manifest, PPTX, out,
                 replacements={(1, target_name): overlay})

    # Verify position unchanged
    re_extracted = R.extract_layout(out)
    src_pic = next(sh for s in source_manifest.slides if s.index == 1
                    for sh in s.shapes if sh.name == target_name)
    dst_pic = next(sh for s in re_extracted.slides if s.index == 1
                    for sh in s.shapes if sh.name == target_name)
    assert (src_pic.left_emu, src_pic.top_emu,
            src_pic.width_emu, src_pic.height_emu) == \
           (dst_pic.left_emu, dst_pic.top_emu,
            dst_pic.width_emu, dst_pic.height_emu)

    # Verify the blob actually changed (via different file size on disk)
    assert out.stat().st_size != PPTX.stat().st_size, \
        "pptx byte-identical after swap — replacement didn't take"
