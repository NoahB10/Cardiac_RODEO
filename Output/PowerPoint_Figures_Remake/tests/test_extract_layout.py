"""Tests for Phase 1: extract_layout.

Compares the extracted manifest from Cardiac_RODEO.pptx against the
authoritative shape inventory CSV (workspace/pptx_shapes.csv) produced
by our prior reverse-engineering.
"""

import csv
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pptx_remake as R  # noqa: E402

PROJECT_ROOT = HERE.parents[2]
PPTX_PATH = PROJECT_ROOT / "Output" / "PowerPoint_Figures" / "Cardiac_RODEO.pptx"
SHAPES_CSV = PROJECT_ROOT / "workspace" / "pptx_shapes.csv"


@pytest.fixture(scope="module")
def manifest():
    assert PPTX_PATH.exists(), f"missing {PPTX_PATH}"
    return R.extract_layout(PPTX_PATH)


@pytest.fixture(scope="module")
def reference_rows():
    rows = list(csv.DictReader(open(SHAPES_CSV)))
    for r in rows:
        r["slide"] = int(r["slide"])
    return rows


def test_slide_count(manifest):
    assert len(manifest.slides) == 12, f"expected 12 slides, got {len(manifest.slides)}"


def test_canvas_size(manifest):
    # Per inventory: 7.09" x 8.47" (custom slide size)
    w_in = manifest.slide_width_emu / R.EMU_PER_INCH
    h_in = manifest.slide_height_emu / R.EMU_PER_INCH
    assert abs(w_in - 7.09) < 0.02, f"width {w_in} != 7.09"
    assert abs(h_in - 8.47) < 0.02, f"height {h_in} != 8.47"


def test_picture_count_per_slide(manifest, reference_rows):
    """Each slide's picture count must match the CSV."""
    from collections import Counter
    ref = Counter(r["slide"] for r in reference_rows if r["type"] == "picture")
    for s in manifest.slides:
        n = sum(1 for sh in s.shapes if sh.kind == "picture")
        assert n == ref[s.index], f"slide {s.index}: got {n} pics, expected {ref[s.index]}"


def test_group_count_per_slide(manifest, reference_rows):
    """Slides 2 and 3 must have the same NUMBER of picture groups as the CSV.

    (The CSV used "first picture name" as the group id; python-pptx returns the
    true XML group name, so we compare counts, not names.)
    """
    ref_groups = {}
    for r in reference_rows:
        if r["type"] == "picture" and r["group"] and r["group"] != "None":
            ref_groups.setdefault(r["slide"], set()).add(r["group"])

    for s in manifest.slides:
        actual = {sh.group_name for sh in s.shapes if sh.group_name}
        expected_count = len(ref_groups.get(s.index, set()))
        assert len(actual) == expected_count, \
            f"slide {s.index}: got {len(actual)} groups, expected {expected_count}"


def test_total_groups(manifest):
    """Must find exactly 8 picture groups across the whole deck (4 in slide 2, 4 in slide 3)."""
    groups = R.find_panel_groups(manifest)
    assert len(groups) == 8, f"expected 8 panel groups, got {len(groups)}"


def test_group_classification(manifest):
    """Every 2-pic group has {axisless, overlay}, every 3-pic group has {axisless, overlay, legend}."""
    for grp in R.find_panel_groups(manifest):
        cls = grp.classify()
        n = len(grp.pictures)
        assert cls["axisless"] is not None, f"{grp.group_name}: no axisless"
        if n >= 2:
            assert cls["overlay"] is not None, f"{grp.group_name}: no overlay"
            # overlay must be larger than axisless
            a_area = cls["axisless"].width_emu * cls["axisless"].height_emu
            o_area = cls["overlay"].width_emu * cls["overlay"].height_emu
            assert o_area >= a_area, f"{grp.group_name}: overlay smaller than axisless"
        if n >= 3:
            assert cls["legend"] is not None, f"{grp.group_name}: no legend"


def test_positions_match_csv(manifest, reference_rows):
    """Spot-check: position of each picture matches CSV (±0.01 inch tolerance)."""
    # Index CSV picture positions by (slide, name)
    ref = {(r["slide"], r["name"]): r for r in reference_rows if r["type"] == "picture"}
    mismatches = []
    for s in manifest.slides:
        for sh in s.shapes:
            if sh.kind != "picture":
                continue
            key = (s.index, sh.name)
            if key not in ref:
                continue
            r = ref[key]
            L, T, W, H = sh.bbox_in()
            for col, got in [("left_in", L), ("top_in", T), ("width_in", W), ("height_in", H)]:
                expected = float(r[col])
                if abs(got - expected) > 0.01:
                    mismatches.append(f"slide{s.index} {sh.name}.{col}: got {got:.3f}, expected {expected:.3f}")
    assert not mismatches, "\n".join(mismatches[:10])


def test_manifest_roundtrip(tmp_path, manifest):
    """Serialize to JSON and reload — must round-trip cleanly."""
    import json
    out = tmp_path / "manifest.json"
    R.save_manifest(manifest, out)
    loaded = R.load_manifest(out)
    assert loaded.slide_width_emu == manifest.slide_width_emu
    assert len(loaded.slides) == len(manifest.slides)
    for a, b in zip(manifest.slides, loaded.slides):
        assert len(a.shapes) == len(b.shapes)
        for s1, s2 in zip(a.shapes, b.shapes):
            assert s1.name == s2.name
            assert s1.left_emu == s2.left_emu
            assert s1.top_emu == s2.top_emu
