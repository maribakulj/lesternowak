"""Tableau de bord C7 : mini-fixture hors ligne, lecture seule, aucun texte de document."""

import json
from datetime import date
from pathlib import Path

from lesternowak import dashboard as db

SECRET = "PHRASE_DE_DOCUMENT_UNIQUE"


def _w(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _slice(root: Path) -> Path:
    d = root / "fixture-volume"
    _w(
        d / "runs.jsonl",
        [
            {
                "id": "r",
                "code_version": "t",
                "params": {"catalogue": "fixture-vol"},
                "started_at": "2026-01-01T00:00:00Z",
            }
        ],
    )
    _w(
        d / "spans.jsonl",
        [
            {"id": "s1", "text": SECRET, "quality_flag": None},
            {"id": "s2", "text": SECRET, "quality_flag": "low_letter_share"},
        ],
    )
    _w(
        d / "artworks.jsonl",
        [
            {"id": "a1", "resolution": {"status": "resolved", "mechanism": "E2_composite"}},
            {"id": "a2", "resolution": {"status": "unresolved", "mechanism": None}},
        ],
    )
    _w(d / "resolutions.jsonl", [{"artwork_id": "a1", "image_license": "cc0"}])
    _w(
        d / "links.jsonl",
        [
            {
                "id": "l1",
                "status": "machine_proposed",
                "evidence": [{"mechanism": "notice_structure"}],
                "rights": [{"asset": "text", "decision": "allow"}],
            },
            {
                "id": "l2",
                "status": "unresolved",
                "evidence": [{"mechanism": "notice_structure"}, {"mechanism": "e0"}],
                "rights": [{"asset": "text", "decision": "allow"}],
            },
        ],
    )
    _w(
        d / "figures.jsonl",
        [
            {
                "id": "f1",
                "image_rights": [
                    {"action": "publish_image", "decision": "allow"},
                    {"action": "redistribute_image", "decision": "allow"},
                ],
            },
            {
                "id": "f2",
                "image_rights": [
                    {"action": "publish_image", "decision": "deny"},
                    {"action": "redistribute_image", "decision": "deny"},
                ],
            },
        ],
    )
    _w(
        d / "rights.jsonl",
        [
            {"asset": "text", "action": "tdm", "decision": "allow"},
            {"asset": "images", "action": "tdm", "decision": "unknown"},
        ],
    )
    return d


def _queue(root: Path) -> Path:
    q = root / "queue.jsonl"
    _w(
        q,
        [
            {"item_id": "i1", "corpus": "fixture-vol", "blind": False},
            {"item_id": "i2", "corpus": "fixture-vol", "blind": True},
            {"item_id": "i3", "corpus": "fixture-vol", "blind": True},
            {"item_id": "i4", "corpus": "autre", "blind": False},
        ],
    )
    return q


def _events(root: Path) -> Path:
    e = root / "events.jsonl"
    _w(
        e,
        [
            {
                "item_id": "i1",
                "before": "machine_proposed",
                "after": "validated",
                "annotator": "x",
                "note": "",
                "timestamp": "2026-11-17T10:00:00Z",
                "relation": "about",
                "blind": False,
                "elapsed_ms": 4000,
            },
            {
                "item_id": "i2",
                "before": "machine_proposed",
                "after": "validated",
                "annotator": "x",
                "note": "",
                "timestamp": "2026-11-17T10:01:00Z",
                "relation": "about",
                "blind": True,
                "elapsed_ms": 6000,
            },
            {
                "item_id": "i3",
                "before": "machine_proposed",
                "after": "rejected",
                "annotator": "x",
                "note": "",
                "timestamp": "2026-11-17T10:02:00Z",
                "relation": "not_about",
                "blind": True,
                "elapsed_ms": 2000,
            },
        ],
    )
    return e


def test_row_counts_without_events(tmp_path):
    sl = _slice(tmp_path)
    row = db.volume_row(sl, db._read(_queue(tmp_path)), None)
    assert row["volume"] == "fixture-vol"
    assert row["spans"] == 2 and row["spans_faible_qualite"] == 1
    assert row["notices"] == 2 and row["resolues"] == 1 and row["resolues_cc0"] == 1
    assert row["status"]["machine_proposed"] == 1 and row["status"]["unresolved"] == 1
    assert row["mecanismes"]["notice_structure"] == 2
    assert row["figures"] == 2 and row["figures_reutilisables"] == 1
    assert row["droits_texte"] == "allow"
    assert row["file"] == 3 and row["file_aveugles"] == 2
    assert row["verifies"] == db.NOT_MEASURED and row["precision"] == db.NOT_MEASURED


def test_report_with_events_and_no_document_text(tmp_path):
    sl = _slice(tmp_path)
    out = tmp_path / "out" / "rapport.md"
    rep = db.build_report([sl], _events(tmp_path), _queue(tmp_path), out, date(2026, 11, 17))
    assert rep == {"volumes": 1, "events": True, "out": str(out)}
    text = out.read_text(encoding="utf-8")
    assert SECRET not in text
    # précision : 2 aveugles décidés, 1 confirmé (about) -> 0.500
    assert "0.500 (n=2)" in text
    assert "| fixture-vol | 3 | 2 | 3 |" in text
    assert "Temps moyen (s)" in text


def test_missing_events_is_not_measured(tmp_path):
    sl = _slice(tmp_path)
    out = tmp_path / "rapport.md"
    db.build_report([sl], tmp_path / "absent.jsonl", _queue(tmp_path), out, date(2026, 11, 17))
    text = out.read_text(encoding="utf-8")
    assert "non mesuré" in text
    assert SECRET not in text
