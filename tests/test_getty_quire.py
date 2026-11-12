from datetime import UTC, datetime
from pathlib import Path

import pytest

from lesternowak import export
from lesternowak import getty_quire as gq
from lesternowak.cli import main
from lesternowak.models import AnnotationEvent, Decision, Link, LinkStatus, SourceAsset

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 12, tzinfo=UTC)


def _asset(n: int, page: bytes) -> SourceAsset:
    return SourceAsset(
        id=f"a{n}",
        url=f"u{n}",
        sha256="0" * 64,
        captured_at=NOW,
        media_type="text/html",
        local_path="x",
    )


@pytest.fixture
def data():
    import json

    return json.loads((FIX / "data_first3.json").read_text())


@pytest.fixture
def page1() -> bytes:
    return (FIX / "catalogue_1.html").read_bytes()


def _pages(page1: bytes, data) -> dict:
    """cat. 2 et 3 : la fixture de cat. 1 avec identité de l'objet substituée."""
    pages = {1: (page1, _asset(1, page1))}
    for n in (2, 3):
        r = data[n - 1]
        txt = page1.decode()
        txt = txt.replace(data[0]["Title"], r["Title"]).replace(
            data[0]["Inventory Number"], r["Inventory Number"]
        )
        txt = txt.replace('object-meta mt2">1<', f'object-meta mt2">{n}<')
        txt = txt.replace("The male figure", f"Variant {n} of the figure")  # description propre
        b = txt.encode()
        pages[n] = (b, _asset(n, b))
    return pages


def test_parse_offsets_roundtrip(page1):
    e = gq.parse_entry(page1)
    assert e.number == "1" and e.inventory == "76.AD.11.1"
    labels = [s[0] for s in e.sections]
    assert "Description" in labels and "Group Discussion" in labels
    for _label, a, b in e.sections:
        assert e.canonical_text[a:b].strip() == e.canonical_text[a:b]
    assert "<" not in e.canonical_text


def test_shared_discussion_dedupe(page1, data):
    run = gq.make_run([1, 2, 3])
    rec = gq.build_records(_pages(page1, data), data, run, NOW)
    disc = [lk for lk in rec["links"] if lk.role == "interpretive_discussion"]
    assert len(disc) == 3 and len({lk.span_id for lk in disc}) == 1
    assert len({lk.artwork_id for lk in disc}) == 3
    span = next(s for s in rec["spans"] if s.id == disc[0].span_id)
    assert len(span.also_in) == 2
    assert len(rec["spans"]) == 4  # 3 descriptions + 1 discussion partagée
    assert all(lk.status == LinkStatus.machine_proposed for lk in rec["links"])


def test_rights_images_unknown_text_allow(page1, data):
    rec = gq.build_records(_pages(page1, data), data, gq.make_run([1]), NOW)
    for lk in rec["links"]:
        assert {r.decision for r in lk.rights if r.asset == "images"} == {Decision.unknown}
        assert {r.decision for r in lk.rights if r.asset == "text"} == {Decision.allow}


def test_mismatch_fails_loudly(page1, data):
    data[0]["Inventory Number"] = "00.XX.0.0"
    with pytest.raises(ValueError):
        gq.build_records({1: (page1, _asset(1, page1))}, data, gq.make_run([1]), NOW)


def test_validate_appends_event_without_mutating_links(page1, data, tmp_path):
    rec = gq.build_records({1: (page1, _asset(1, page1))}, data, gq.make_run([1]), NOW)
    export.write_jsonl(tmp_path / "links.jsonl", rec["links"])
    before = (tmp_path / "links.jsonl").read_bytes()
    ev = tmp_path / "events.jsonl"
    lid = rec["links"][0].id
    argv = [
        "validate",
        lid,
        "--status",
        "validated",
        "--note",
        "ok",
        "--annotator",
        "t",
        "--events",
        str(ev),
    ]
    assert main(argv) == 0
    assert (
        main(
            [
                "validate",
                lid,
                "--status",
                "rejected",
                "--note",
                "non",
                "--annotator",
                "t",
                "--events",
                str(ev),
            ]
        )
        == 0
    )
    assert (tmp_path / "links.jsonl").read_bytes() == before
    events = export.read_jsonl(ev, AnnotationEvent)
    assert [(e.before, e.after) for e in events] == [
        (LinkStatus.machine_proposed, LinkStatus.validated),
        (LinkStatus.validated, LinkStatus.rejected),
    ]
    links = export.read_jsonl(tmp_path / "links.jsonl", Link)
    assert gq.current_statuses(links, events)[lid] == LinkStatus.rejected
    assert (
        main(
            [
                "validate",
                "nope",
                "--status",
                "validated",
                "--note",
                "x",
                "--annotator",
                "t",
                "--events",
                str(ev),
            ]
        )
        == 2
    )


@pytest.mark.live
def test_live_entry_1(tmp_path):
    data, _, pages = gq.fetch_entries([1], tmp_path)
    page, asset = pages[1]
    rec = gq.build_records({1: (page, asset)}, data, gq.make_run([1]), NOW)
    assert any(lk.role == "interpretive_discussion" for lk in rec["links"])
