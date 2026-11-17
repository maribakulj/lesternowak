# ruff: noqa: RUF003
"""Lecteur Quire générique (hors ligne) : appels de figure, légende -> objet local, droits par
figure, rétrocompatibilité Terracottas."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from lesternowak import quire
from lesternowak.models import Decision, SourceAsset
from test_getty_quire import FIX, _pages, gq

NOW = datetime(2026, 11, 17, tzinfo=UTC)
CFG_DIR = Path(__file__).parent.parent / "config" / "catalogues"
URL = "https://www.getty.edu/publications/mummyportraits/part-one/1/"


def _cfg(**kw) -> quire.QuireConfig:
    cfg = quire.load_config(CFG_DIR / "getty-mummy-portraits-roman-egypt-2020.yaml")
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


def _build(cfg=None, met=None):
    cfg = cfg or _cfg()
    page = (FIX / "mummy_chapter1.html").read_bytes()
    asset = SourceAsset(
        id="a1", url=URL, sha256="0" * 64, captured_at=NOW, media_type="text/html", local_path="x"
    )
    run = quire.make_run(cfg, ["part-one/1/"])
    return quire.build_records(cfg, {"part-one/1/": (page, asset)}, run, NOW, met)


def _sp(rec, start):
    return next(s for s in rec["spans"] if s.text.startswith(start))


def test_toc_pages_follow_config():
    root = (FIX / "mummy_root.html").read_bytes()
    assert quire.toc_pages(root, _cfg()) == ["intro/", "part-one/1/", "part-one/2/"]


def test_paragraph_spans_and_hidden_glossary_removed():
    rec = _build()
    assert len(rec["spans"]) == 4  # 4 paragraphes dans l'extrait, tous conservés comme spans
    first = rec["spans"][0]
    assert first.text.startswith("Romano-Egyptian mummy portraits")
    assert "Citation" not in first.text and "Organic materials" not in first.text
    page = (FIX / "mummy_chapter1.html").read_bytes()
    pp = quire.parse_page(page, "part-one/1/", URL, "essays", _cfg())
    for _sec, _i, a, b, text, _n, _c in pp.paragraphs:
        assert pp.canonical[a:b] == text


def test_figure_calls_are_offset_verified_and_abstain_when_absent():
    rec = _build()
    sp = _sp(rec, "Acquired in 1922")
    labels = [sp.text[c.char_start : c.char_end] for c in sp.figure_calls]
    assert labels[:2] == ["figs. 1.1", "1.2"] and all(
        c.label == t for c, t in zip(sp.figure_calls, labels, strict=True)
    )
    # « figs. 1.5–1.7 » : seul 1.5 existe dans l'extrait ; 1.6 et 1.7 (absentes) ne sont pas liées
    sp = _sp(rec, "The analytical results")
    assert [c.label for c in sp.figure_calls] == ["figs. 1.5"]


def test_paragraph_without_call_has_span_but_no_link():
    rec = _build()
    sp = _sp(rec, "Speculation about the binding media")
    assert sp.figure_calls == []
    assert not [lk for lk in rec["links"] if lk.span_id == sp.id]


def test_caption_to_local_object_and_derived_figure():
    rec = _build()
    figs = {f.key: f for f in rec["figures"]}
    art = next(a for a in rec["artworks"] if a.inventory_number == "1922.4799")
    assert art.local_label.startswith("Mummy Portrait of a Man Wearing a Laurel Wreath")
    assert figs["1.1"].artwork_id == art.id
    assert figs["1.1"].caption.endswith("Art Institute of Chicago, CC0")
    # « Raking light detail of fig. 1.1 » : même objet, preuve citée
    assert figs["1.3"].artwork_id == art.id and "cite la figure 1.1" in figs["1.3"].object_evidence
    # spectre : aucune dimension ni inventaire, donc pas d'objet (abstention)
    assert figs["1.5"].artwork_id is None


def test_caption_object_formats():
    co = quire.caption_object(
        "Mummy Shroud, Romano-Egyptian, ca. AD 125. Paint on linen, 98 x 82 cm (38 5/8 x 32 in.). "
        "New York, Metropolitan Museum of Art, Gift of Mrs. S. W. Straus, 1925, 25.184.20 "
        "www.​metmuseum.org, CC0"
    )
    assert co.inventory == "25.184.20" and "Metropolitan Museum" in co.museum
    assert co.label.endswith("ca. AD 125")
    assert quire.caption_object("Infrared spectrum of a sample, 5 cm scale.") is None


def test_links_are_e0_to_figure_and_unresolved_outside_referential():
    rec = _build()
    sp = _sp(rec, "Acquired in 1922")
    lks = [lk for lk in rec["links"] if lk.span_id == sp.id]
    assert len(lks) == 2  # deux objets (1922.4799 et 1922.4798), un lien chacun
    assert all(lk.evidence[0].mechanism == "figure_call" for lk in lks)
    assert all(lk.figure_ids and lk.status.value == "machine_proposed" for lk in lks)
    arts = [a for a in rec["artworks"] if a.id in {lk.artwork_id for lk in lks}]
    assert all(
        a.resolution.status == "unresolved" for a in arts
    )  # Art Institute of Chicago : pas de référentiel


def test_met_object_resolves_only_via_accession_in_referential():
    from lesternowak.referentials import ReferenceArtwork

    ref = ReferenceArtwork(
        ref_id="met:1", source="met", external_id="1", accession_number="25.184.20"
    )
    co = quire.caption_object(
        "Shroud, ca. AD 125. Paint, 98 x 82 cm (38 in.). New York, Metropolitan Museum of Art, "
        "Gift of X, 25.184.20, CC0"
    )
    res, hits = quire.resolve_object(co, {quire._norm("25.184.20"): [ref]})
    assert res.status == "resolved" and res.mechanism == "E0" and hits == [ref]
    res, _ = quire.resolve_object(co, {quire._norm("99.9.9"): [ref]})  # accession absente
    assert res.status == "unresolved" and "absent" in res.reason
    other = quire.caption_object("X, 9 x 9 cm (1 in.). Boston, Museum of Fine Arts, 97.1100")
    assert quire.resolve_object(other, {})[0].status == "unresolved"


def _fig_decisions(rec, key):
    f = next(f for f in rec["figures"] if f.key == key)
    return {r.action: r.decision for r in f.image_rights}


def test_figure_rights_listed_licensed_excluded_and_unknown():
    # Mummy : seules les figures listées sont CC BY ; la légende « CC0 » ne suffit pas
    rec = _build(_cfg(figures_listed=["1.1"]))
    assert _fig_decisions(rec, "1.1")["display_pilot"] == Decision.allow
    assert _fig_decisions(rec, "1.1")["redistribute_image"] == Decision.allow
    assert _fig_decisions(rec, "1.2")["display_pilot"] == Decision.deny
    # sans liste (« except where otherwise noted ») : unknown, jamais allow
    rec = _build(_cfg(figures_mode="unknown"))
    assert set(_fig_decisions(rec, "1.1").values()) == {Decision.unknown}
    # Rococo : liste d'exclusions, NC -> hors liste allow mais réutilisation conditionnelle
    rec = _build(_cfg(figures_mode="listed_excluded", figures_listed=["1.2"], text_flags=["NC"]))
    assert _fig_decisions(rec, "1.2")["display_pilot"] == Decision.deny
    d = _fig_decisions(rec, "1.1")
    assert d["display_pilot"] == Decision.allow and d["redistribute_image"] == Decision.conditional
    nc_text = {r.decision for r in rec["links"][0].rights if r.asset == "text"}
    assert nc_text == {Decision.conditional}


def test_link_rights_take_the_most_restrictive_figure():
    rec = _build(
        _cfg(figures_listed=["1.1", "1.3"])
    )  # objet 4799 : 1.1 et 1.3 ; objet 4798 : 1.2, 1.4
    by_inv = {a.id: a.inventory_number for a in rec["artworks"]}
    shown = {
        by_inv[lk.artwork_id]: next(
            r.decision for r in lk.rights if r.asset == "images" and r.action == "display_pilot"
        )
        for lk in rec["links"]
        if lk.figure_ids
    }
    assert shown["1922.4799"] == Decision.allow and shown["1922.4798"] == Decision.deny


def test_terracottas_link_ids_unchanged_by_quire_models():
    page1 = (FIX / "catalogue_1.html").read_bytes()
    import json

    data = json.loads((FIX / "data_first3.json").read_text())
    rec = gq.build_records(_pages(page1, data), data, gq.make_run([1, 2, 3]), NOW)
    assert [lk.id for lk in rec["links"]][:3] == [
        "lnk_755aeeb486fd",
        "lnk_d3485f94041d",
        "lnk_ce24be59957e",
    ]
    assert all(s.figure_calls == [] for s in rec["spans"])
    assert all(lk.figure_ids == [] for lk in rec["links"])


def test_shipped_configs_load():
    for name in ("getty-mummy-portraits-roman-egypt-2020", "getty-rococo-2021"):
        cfg = quire.load_config(CFG_DIR / f"{name}.yaml")
        assert cfg.root_url.startswith("https://www.getty.edu/publications/")
    rococo = quire.load_config(CFG_DIR / "getty-rococo-2021.yaml")
    assert "NC" in rococo.text_flags and rococo.entry_pages
    assert quire.page_kind("catalogue/3/", rococo) == "catalogue_entries"
    assert quire.page_kind("intro/", rococo) == "essays"


@pytest.mark.parametrize("key", ["fig_1_5", "fig-1-5", "1.5", "fig_17_4_a", "17.4a"])
def test_fig_key_normalisation(key):
    assert quire.fig_key(key) in ("1.5", "17.4a")


def test_review_adapter_shows_image_only_when_allowed(tmp_path):
    from lesternowak import export
    from lesternowak.models import Run
    from lesternowak.review import ADAPTERS

    rec = _build(_cfg(figures_listed=["1.1", "1.3"]))
    asset = SourceAsset(
        id="a1", url=URL, sha256="0" * 64, captured_at=NOW, media_type="text/html", local_path="x"
    )
    run = Run(id="r", code_version="t", params={"catalogue": "mummy-fixture"}, started_at=NOW)
    for name, key in (
        ("links", "links"),
        ("spans", "spans"),
        ("artworks", "artworks"),
        ("figures", "figures"),
    ):
        export.write_jsonl(tmp_path / f"{name}.jsonl", rec[key])
    export.write_jsonl(tmp_path / "assets.jsonl", [asset])
    export.write_jsonl(tmp_path / "runs.jsonl", [run])
    items = ADAPTERS["quire-figures"](tmp_path)
    by_inv = {i.artwork.accession_number: i for i in items}
    ok, closed = by_inv["1922.4799"], by_inv["1922.4798"]
    assert ok.artwork.image_display_allowed and ok.artwork.image_url.endswith("fig_1_1.jpg")
    assert not closed.artwork.image_display_allowed and closed.artwork.image_url is None
    for it in items:
        assert it.highlights and all(
            it.passage.text[h.start : h.end].lower().lstrip("figs. ")[:1].isdigit()
            or "fig" in it.passage.text[h.start : h.end]
            for h in it.highlights
        )
        assert it.source.url.startswith(URL + "#fig_")
