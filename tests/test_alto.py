from pathlib import Path

import pytest

from lesternowak import alto

FIX = Path(__file__).parent / "fixtures" / "alto_page.xml"


def test_parse_blocks_lines_text_offsets():
    pg = alto.parse_alto(FIX.read_bytes())
    assert (pg.width, pg.height, pg.unit) == (2000, 3000, "mm10")
    assert pg.coordinate_system == "alto:mm10:2000x3000"
    assert [len(b.lines) for b in pg.blocks] == [1, 2, 1]
    assert pg.blocks[1].lines[0].text == "1. Portrait de femme--"  # HYP ajouté au dernier mot
    for b in pg.blocks:
        for ln in b.lines:
            assert pg.text[ln.start : ln.end] == ln.text
        assert pg.text[b.start : b.end] == "\n".join(x.text for x in b.lines)


def test_illustration_kept_rule_dropped():
    pg = alto.parse_alto(FIX.read_bytes())
    assert [i.id for i in pg.illustrations] == ["I1"]  # le filet (hauteur 4) est écarté
    assert pg.illustrations[0].bbox == pytest.approx((0.2, 800 / 3000, 0.7, 2000 / 3000), abs=1e-6)


def test_bbox_roundtrip_source_xyxy():
    """source_bbox = (x0, y0, x1, y1) et non (HPOS, VPOS, WIDTH, HEIGHT) ; aller-retour exact."""
    pg = alto.parse_alto(FIX.read_bytes())
    ln = pg.blocks[1].lines[0]  # HPOS=200 VPOS=300 WIDTH=1600 HEIGHT=60
    assert ln.src_bbox == (200, 300, 1800, 360)
    for b in pg.blocks:
        for line in b.lines:
            x0, y0, x1, y1 = alto.denormalize_bbox(line.bbox, pg.width, pg.height)
            assert x1 > x0 and y1 > y0
            assert (x0, y0, x1, y1) == pytest.approx(line.src_bbox, abs=2e-3 * pg.width)
    assert pg.illustrations[0].src_bbox == (400, 800, 1400, 2000)
    u = alto.union([pg.blocks[1].lines[0].src_bbox, pg.blocks[1].lines[1].src_bbox])
    assert u == (200, 300, 1800, 440)
    bb = alto.normalize_bbox(250, 300, 500, 600, 1000, 2000)
    assert bb == (0.25, 0.15, 0.75, 0.45)
    assert alto.denormalize_bbox(bb, 1000, 2000) == pytest.approx((250, 300, 750, 900))


def test_bbox_clamped_and_words():
    assert alto.normalize_bbox(-10, 0, 5000, 10, 1000, 1000) == (0.0, 0.0, 1.0, 0.01)
    pg = alto.parse_alto(FIX.read_bytes())
    assert [w.text for w in pg.blocks[0].lines[0].words] == ["12", "MUSÉE"]


def test_mojibake_repair_is_conservative():
    assert alto.fix_mojibake("JÃ©sus Ã\xa0 la") == "Jésus à la"
    assert alto.fix_mojibake("Jésus") == "Jésus"
    assert alto.fix_mojibake("Ãx incohérent ☃") == "Ãx incohérent ☃"
