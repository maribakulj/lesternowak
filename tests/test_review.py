import json
import threading
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lesternowak import evaluation as ev
from lesternowak import review as rv
from lesternowak.cli import main
from lesternowak.export import read_jsonl, write_jsonl
from lesternowak.models import (
    ArtworkRef,
    Evidence,
    Link,
    LinkStatus,
    PassageFunction,
    SourceAsset,
    Span,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TXT = "The seated figure <b>x</b> (cat. 1, inv. 76.AD.11.1) wears a cloak."


def make_slice(d: Path, n_spans: int = 20) -> Path:
    arts = [
        ArtworkRef(
            id=f"a{i}",
            getty_dor_id=i,
            inventory_number=f"76.AD.11.{i}",
            catalogue_number=f"cat. {i}",
            collection_url=f"http://example.org/{i}",
            title=f"Statue {i}",
        )
        for i in (1, 2)
    ]
    asset = SourceAsset(
        id="as1",
        url="https://example.org/p/1/",
        sha256="0",
        captured_at=NOW,
        media_type="text/html",
        local_path="x",
    )
    spans, links = [], []
    for k in range(n_spans):
        t = TXT + f" {k}"
        sec = "Description" if k % 2 else "Group Discussion"
        spans.append(
            Span(
                id=f"s{k}",
                asset_id="as1",
                section_label=sec,
                paragraph_index=k,
                char_start=0,
                char_end=len(t),
                text=t,
            )
        )
        for a in arts:
            links.append(
                Link(
                    id=f"l{k}{a.id}",
                    artwork_id=a.id,
                    span_id=f"s{k}",
                    role=PassageFunction.unclassified,
                    evidence=[
                        Evidence(
                            mechanism="editorial_entry_structure",
                            quoted_heading=sec,
                            explanation="e",
                        )
                    ],
                    status=LinkStatus.machine_proposed,
                    rights=[],
                    run_id="r",
                )
            )
    d.mkdir(parents=True)
    write_jsonl(d / "spans.jsonl", spans)
    write_jsonl(d / "artworks.jsonl", arts)
    write_jsonl(d / "links.jsonl", links)
    write_jsonl(d / "assets.jsonl", [asset])
    return d


@pytest.fixture
def queue(tmp_path):
    sl = make_slice(tmp_path / "slice")
    items = rv.make_queue("getty-terracottas", sl, 0.25, 7)
    q = tmp_path / "q.jsonl"
    rv.write_queue(q, items)
    return q, items


def test_queue_deterministic_and_blind_rate(tmp_path):
    sl = make_slice(tmp_path / "slice")
    a = rv.make_queue("getty-terracottas", sl, 0.25, 7)
    b = rv.make_queue("getty-terracottas", sl, 0.25, 7)
    assert [i.model_dump() for i in a] == [i.model_dump() for i in b]
    assert len(a) == 40
    blind = [i for i in a if i.blind]
    assert len(blind) == 10 and all(i.proposal is None for i in blind)
    assert all(i.proposal is not None for i in a if not i.blind)
    c = rv.make_queue("getty-terracottas", sl, 0.25, 8)
    assert {i.item_id for i in c if i.blind} != {i.item_id for i in blind}
    assert len({i.item_id for i in a}) == 40
    # diversité : les deux premiers éléments diffèrent par la section
    assert a[0].passage.section != a[1].passage.section


def test_text_assert_and_highlights(queue):
    _, items = queue
    for it in items:
        assert it.passage.text.startswith("The seated")
        labels = {h.label for h in it.highlights}
        assert "catalogue" in labels
        for h in it.highlights:
            assert 0 <= h.start < h.end <= len(it.passage.text)
    bad = items[0].model_copy(update={"passage": items[0].passage.model_copy(update={"text": "x"})})
    spans = {
        "s0": Span(
            id="s0",
            asset_id="a",
            section_label="d",
            paragraph_index=0,
            char_start=0,
            char_end=3,
            text="abc",
        )
    }
    with pytest.raises(AssertionError):
        rv.check_texts(
            [bad.model_copy(update={"passage": bad.passage.model_copy(update={"span_id": "s0"})})],
            spans,
        )


def _req(url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(url, data=data, headers=h)
    return urllib.request.urlopen(r, timeout=5)


def run_server(q, events):
    srv = rv.make_server(q, events, "tester", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_server_get_post_resume_export(queue, tmp_path):
    q, _items = queue
    events = tmp_path / "ev.jsonl"
    srv, base = run_server(q, events)
    try:
        page = _req(base + "/").read().decode()
        assert "<script>" in page
        st = json.loads(_req(base + "/api/state").read())
        assert st["stats"]["total"] == 40 and st["stats"]["decided"] == 0
        blind = next(i for i in st["items"] if i["blind"])
        assert blind["proposal"] is None
        norm = next(i for i in st["items"] if not i["blind"])
        # validation sans fonction refusée
        with pytest.raises(urllib.error.HTTPError) as e:
            _req(
                base + "/api/decision",
                {"item_id": norm["item_id"], "decision": "validated", "relation": "about"},
            )
        assert e.value.code == 400
        assert not events.exists()
        r = json.loads(
            _req(
                base + "/api/decision",
                {
                    "item_id": norm["item_id"],
                    "decision": "validated",
                    "relation": "about",
                    "function": "visual_description",
                    "note": "ok",
                    "elapsed_ms": 1234,
                },
            ).read()
        )
        assert r["stats"]["decided"] == 1 and r["stats"]["mean_ms"] == 1234
        # item aveugle : relation + fonction seulement
        _req(
            base + "/api/decision",
            {
                "item_id": blind["item_id"],
                "relation": "group",
                "function": "other",
                "elapsed_ms": 10,
            },
        )
        # hôte non local refusé
        with pytest.raises(urllib.error.HTTPError) as e:
            _req(base + "/api/state", headers={"Host": "evil.example"})
        assert e.value.code == 403
    finally:
        srv.shutdown()
        srv.server_close()
    lines = events.read_text().splitlines()
    assert len(lines) == 2
    evs = read_jsonl(events, rv.AnnotationEvent)
    assert evs[0].after == LinkStatus.validated and evs[0].blind is False
    assert evs[1].blind is True and evs[1].relation == "group"
    # reprise : un nouveau serveur voit les 2 éléments décidés, rien n'est réécrit
    srv, base = run_server(q, events)
    try:
        st = json.loads(_req(base + "/api/state").read())
        assert st["stats"]["decided"] == 2 and len(st["events"]) == 2
    finally:
        srv.shutdown()
        srv.server_close()
    assert events.read_text().splitlines()[:2] == lines


def test_image_hidden_when_not_allowed(queue, tmp_path):
    _q, items = queue
    it = items[0].model_copy(
        update={"artwork": items[0].artwork.model_copy(update={"image_url": "https://x/i.jpg"})}
    )
    q2 = tmp_path / "q2.jsonl"
    rv.write_queue(q2, [it])
    srv, base = run_server(q2, tmp_path / "e.jsonl")
    try:
        st = json.loads(_req(base + "/api/state").read())
        assert st["items"][0]["artwork"]["image_url"] is None
    finally:
        srv.shutdown()
        srv.server_close()


def test_html_escaping_in_page_and_csp(queue):
    q, items = queue
    assert any("<b>x</b>" in i.passage.text for i in items)  # texte hostile conservé tel quel
    from lesternowak.review_ui import PAGE

    assert "innerHTML" not in PAGE and "document.write" not in PAGE
    srv, base = run_server(q, q.parent / "e.jsonl")
    try:
        resp = _req(base + "/")
        assert "default-src 'none'" in resp.headers["Content-Security-Policy"]
        assert "<b>x</b>" not in resp.read().decode()  # données jamais dans le HTML servi
    finally:
        srv.shutdown()
        srv.server_close()


def test_export_gold_compatible_with_eval(queue, tmp_path):
    q, items = queue
    events = tmp_path / "ev.jsonl"
    srv, base = run_server(q, events)
    try:
        for n, it in enumerate(items[:4]):
            body = {
                "item_id": it.item_id,
                "elapsed_ms": 5,
                "function": "other",
                "relation": "about" if n % 2 else "not_about",
                "decision": "validated" if n % 2 else "rejected",
            }
            _req(base + "/api/decision", body)
        _req(
            base + "/api/decision",
            {"item_id": items[4].item_id, "decision": "unresolved", "relation": "unsure"},
        )
    finally:
        srv.shutdown()
        srv.server_close()
    out = tmp_path / "gold" / "c" / "review-v1.jsonl"
    assert (
        main(["review-export", "--queue", str(q), "--events", str(events), "--out", str(out)]) == 0
    )
    gold = ev.read_gold(out)
    assert len(gold) == 5
    assert all("text" not in g for g in gold)
    assert gold[-1]["relation"] == "unsure"
    spans = {s.id: s for s in read_jsonl(tmp_path / "slice" / "spans.jsonl", Span)}
    links = read_jsonl(tmp_path / "slice" / "links.jsonl", Link)
    m = ev.evaluate(gold, links, spans, "t")
    assert m["relation_matrix"]


def test_cli_review_queue(tmp_path, capsys):
    sl = make_slice(tmp_path / "slice")
    out = tmp_path / "r" / "queue.jsonl"
    assert (
        main(
            [
                "review-queue",
                "--slice",
                str(sl),
                "--out",
                str(out),
                "--blind-rate",
                "0.15",
                "--seed",
                "7",
            ]
        )
        == 0
    )
    assert "6 à l'aveugle" in capsys.readouterr().out
    assert len(rv.read_queue(out)) == 40


def _post_status(base, item, **kw):
    return json.loads(_req(base + "/api/decision", {"item_id": item["item_id"], **kw}).read())


def test_status_derived_from_relation_and_function_rules(queue, tmp_path):
    q, _ = queue
    events = tmp_path / "ev.jsonl"
    srv, base = run_server(q, events)
    try:
        st = json.loads(_req(base + "/api/state").read())
        its = st["items"]
        expected = {
            "about": "validated",
            "group": "validated",
            "context": "rejected",
            "mentions": "rejected",
            "not_about": "rejected",
            "unsure": "unresolved",
        }
        for it, rel in zip(its, expected, strict=False):
            kw = {"function": "other"} if rel in ("about", "group") else {}
            _post_status(base, it, relation=rel, **kw)  # fonction facultative sinon
        got = [e.after.value for e in read_jsonl(events, rv.AnnotationEvent)]
        assert got == list(expected.values())
        # POST incohérent refusé ; fonction obligatoire pour about/group
        for kw in ({"relation": "about", "function": "other", "decision": "rejected"},
                   {"relation": "not_about", "decision": "validated"},
                   {"relation": "group"}, {}):  # fmt: skip
            with pytest.raises(urllib.error.HTTPError) as e:
                _post_status(base, its[7], **kw)
            assert e.value.code == 400
        assert len(events.read_text().splitlines()) == 6
    finally:
        srv.shutdown()
        srv.server_close()


def test_blind_link_id_not_exposed(queue, tmp_path):
    q, _ = queue
    events = tmp_path / "ev.jsonl"
    srv, base = run_server(q, events)
    try:
        st = json.loads(_req(base + "/api/state").read())
        blind = next(i for i in st["items"] if i["blind"])
        _post_status(base, blind, relation="not_about")
        st = json.loads(_req(base + "/api/state").read())
        blind_ids = [i["link_id"] for i in st["items"] if i["blind"]]
        assert set(blind_ids) == {None}
        assert st["events"][blind["item_id"]]["link_id"] is None
        assert any(i["link_id"] for i in st["items"] if not i["blind"])
    finally:
        srv.shutdown()
        srv.server_close()
    assert read_jsonl(events, rv.AnnotationEvent)[0].link_id  # conservé côté serveur


def test_remote_host_requires_flag(queue, capsys):
    q, _ = queue
    rc = main(["review-serve", "--queue", str(q), "--annotator", "t", "--host", "0.0.0.0"])
    err = capsys.readouterr().err
    assert rc == 2 and "ATTENTION" in err and "--allow-remote" in err
