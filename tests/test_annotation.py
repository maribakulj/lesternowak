import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lesternowak import annotation as an
from lesternowak import evaluation as ev
from lesternowak.cli import main
from lesternowak.models import (
    ArtworkRef,
    Link,
    LinkStatus,
    PassageFunction,
    SourceAsset,
    Span,
)

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _span(i, text, group=None):
    return Span(
        id=i,
        asset_id="as1",
        section_label="Description",
        paragraph_index=0,
        char_start=0,
        char_end=len(text),
        text=text,
        group_title=group,
    )


def _art(i, n):
    return ArtworkRef(
        id=i,
        getty_dor_id=n,
        inventory_number=f"i{n}",
        catalogue_number=f"cat. {n}",
        collection_url="u",
        title=f"T{n}",
    )


def _link(i, a, s, role=PassageFunction.visual_description, status=LinkStatus.machine_proposed):
    return Link(
        id=i, artwork_id=a, span_id=s, role=role, evidence=[], status=status, rights=[], run_id="r"
    )


@pytest.fixture
def sl():
    return an.SliceData(
        spans=[
            _span("s1", "Texte un."),
            _span("s2", "Texte « deux »\nligne.", "Groupe 1-2"),
            _span("s3", "Trois."),
            _span("s4", "Quatre."),
        ],
        artworks=[_art("a1", 1), _art("a2", 2)],
        links=[
            _link("l1", "a1", "s1"),
            _link("l2", "a1", "s2", PassageFunction.unclassified),
            _link("l3", "a2", "s2", PassageFunction.unclassified),
            _link("l4", "a2", "s3"),
        ],
        assets=[
            SourceAsset(
                id="as1",
                url="https://x/1",
                sha256="h",
                captured_at=NOW,
                media_type="text/html",
                local_path="p",
            )
        ],
    )


def _write_slice(sl, d: Path):
    d.mkdir(parents=True, exist_ok=True)
    for name, items in (
        ("spans", sl.spans),
        ("artworks", sl.artworks),
        ("links", sl.links),
        ("assets", sl.assets),
    ):
        (d / f"{name}.jsonl").write_text(
            "".join(i.model_dump_json() + "\n" for i in items), encoding="utf-8"
        )


def _fill(path: Path, edits: dict[str, dict[str, str]]):
    rows = list(csv.reader(path.read_text("utf-8-sig").splitlines(keepends=True)))
    # relit proprement (champs multilignes)
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    h = rows[0]
    for r in rows[1:]:
        for col, v in edits.get(r[0], {}).items():
            r[h.index(col)] = v
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)


def test_sheet_roundtrip(sl, tmp_path):
    header, rows = an.build_sheet_rows(sl)
    assert header[:7] == an.FIXED_COLS and header[7:9] == ["relation_cat1", "relation_cat2"]
    sheet = tmp_path / "s.csv"
    an.write_sheet(sheet, header, rows)
    assert sheet.read_bytes().startswith(b"\xef\xbb\xbf")
    by = {r[0]: r for r in rows}
    assert by["s1"][7:9] == ["", "-"] and by["s1"][5] == "cat. 1" and by["s2"][3] == "Groupe 1-2"
    _fill(
        sheet,
        {
            "s1": {"relation_cat1": "about", "function": "visual_description"},
            "s2": {
                "relation_cat1": "group",
                "relation_cat2": "group",
                "function": "comparison",
                "note": "n",
            },
        },
    )
    recs, rep = an.import_sheet(sheet, sl, "moi", NOW)
    assert rep["rows"] == 3 and rep["rows_ignored"] == 1 and rep["pairs"] == 3
    assert {(r.span_id, r.artwork_id, r.relation) for r in recs} == {
        ("s1", "a1", "about"),
        ("s2", "a1", "group"),
        ("s2", "a2", "group"),
    }
    assert "text" not in json.loads(recs[0].model_dump_json())
    assert recs[0].sheet_sha256 and recs[0].annotator == "moi"


@pytest.mark.parametrize(
    "edit,msg",
    [
        ({"s1": {"relation_cat1": "oui", "function": "other"}}, "relation invalide"),
        ({"s1": {"relation_cat1": "about", "function": "unclassified"}}, "fonction invalide"),
        (
            {"s1": {"relation_cat1": "about", "function": "other", "text": "Texte modifié."}},
            "texte",
        ),
        ({"s1": {"span_id": "spn_zzz"}}, "inconnu"),
        ({"s1": {"function": "other"}}, "sans aucune relation"),
    ],
)
def test_import_rejects(sl, tmp_path, edit, msg):
    header, rows = an.build_sheet_rows(sl)
    sheet = tmp_path / "s.csv"
    an.write_sheet(sheet, header, rows)
    _fill(sheet, edit)
    with pytest.raises(an.ImportError_, match=msg):
        an.import_sheet(sheet, sl, "moi", NOW)


def test_sample_is_deterministic_and_blank(sl):
    _h, r1 = an.build_sheet_rows(sl, 2, 7)
    _, r2 = an.build_sheet_rows(sl, 2, 7)
    assert r1 == r2 and len(r1) == 2
    assert all(r[-2] == "" and r[-1] == "" for r in r1)


def test_cli_import_refuses_overwrite(sl, tmp_path, capsys):
    _write_slice(sl, tmp_path / "sl")
    sheet, out = tmp_path / "s.csv", tmp_path / "g" / "gold.jsonl"
    assert main(["annotation-sheet", "--slice", str(tmp_path / "sl"), "--out", str(sheet)]) == 0
    _fill(sheet, {"s1": {"relation_cat1": "about", "function": "other"}})
    args = [
        "annotation-import",
        "--slice",
        str(tmp_path / "sl"),
        "--sheet",
        str(sheet),
        "--annotator",
        "moi",
        "--out",
        str(out),
    ]
    assert main(args) == 0 and out.exists()
    assert main(args) == 2
    assert main([*args, "--force"]) == 0


def test_wilson_known():
    lo, hi = ev.wilson(8, 10)
    assert (round(lo, 3), round(hi, 3)) == (0.490, 0.943)
    assert ev.wilson(0, 0) is None


def test_kappa_known():
    k = ev.cohen_kappa(["a", "a", "b", "b"], ["a", "b", "b", "b"])
    assert k["agreement"] == 0.75 and k["kappa"] == 0.5
    assert ev.cohen_kappa(["a", "a"], ["a", "a"])["kappa"] == 1.0


def test_eval_mini_gold(sl):
    gold = ev.read_gold(FIX / "gold_mini.jsonl")
    spans = {s.id: s for s in sl.spans}
    m = ev.evaluate(gold, sl.links, spans, "T")
    assert m["pairs_evaluated"] == 5 and m["pairs_unsure_excluded"] == 1
    st = m["attachment_strict"]
    # prédits sur les couples gold : (s1,a1) about ; (s2,a1), (s2,a2) group ; (s3,a2) about
    assert (st["tp"], st["fp"], st["fn"]) == (2, 2, 0)
    assert st["abstentions"] == 1 and st["coverage"]["k"] == 4
    to = m["attachment_tolerant"]
    assert (to["tp"], to["fp"], to["fn"]) == (4, 0, 0)
    assert len(m["errors"]) == 2
    f = m["function"]
    assert f["spans"] == 3 and f["abstentions"] == 1  # s2 non classé ; s3 prédit visual
    assert f["accuracy_all"]["k"] == 1  # seul s1 juste
    assert "Rapport" in ev.render_report(m)


def test_agreement():
    a = ev.read_gold(FIX / "gold_mini.jsonl")
    b = [dict(g) for g in a]
    b[0]["relation"] = "mentions"
    r = ev.agreement(a, b)
    assert r["common_pairs"] == 6 and r["relations"]["agreement"] == round(5 / 6, 4)


def test_link_ids_independent_of_function():
    from lesternowak import getty_quire as gq

    # clés figées : l'identifiant ne dépend que de (œuvre, span, clé de section historique)
    assert gq._ID_KEYS["Description"] == "visual_description"
    assert gq._ID_KEYS["Group Discussion"] == gq._ID_KEYS["Discussion"] == "interpretive_discussion"
    assert gq.SECTION_ROLES["Group Discussion"] == PassageFunction.unclassified
