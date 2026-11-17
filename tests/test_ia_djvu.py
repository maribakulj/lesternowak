"""Voie ia_djvu, hors ligne : fixture djvu.xml d'une page réduite (domaine public)."""

import json
from pathlib import Path

import pytest

from lesternowak import export, review
from lesternowak import ia_djvu as ia
from lesternowak.models import ArtworkRef, Link, LinkStatus, Span
from lesternowak.referentials import ReferenceArtwork

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config/catalogues/met-catalogue-paintings-1926-8ed.yaml"
FIXTURE = (ROOT / "tests/fixtures/ia/mini_djvu.xml").read_bytes()
META = {"metadata": {"title": "Catalogue of paintings", "date": "1926", "collection": ["getty"]}}


def cfg() -> ia.IaConfig:
    c = ia.load_ia_config(CFG_PATH)
    c.first_page, c.last_page = 1, 1
    return c


def ref(n: str, dims: tuple[float, float], credit="Purchase, 1871", year=1871) -> ReferenceArtwork:
    return ReferenceArtwork(
        ref_id=f"met:{n}",
        source="met",
        external_id=n,
        accession_number=f"71.{n}",
        title=f"Titre {n}",
        artist="Jan Bruegel the Elder",
        dimensions_cm=dims,
        credit_line=credit,
        accession_year=year,
        collection_url=f"https://example.org/{n}",
        image_url=f"https://example.org/{n}.jpg",
        image_license="cc0",
        is_public_domain=True,
    )


# --- dimensions en pouces ----------------------------------------------------------------------


def test_inch_tokens_ocr_degrades():
    assert ia.inch_token("383") == ([38], None)  # « 38 3/8 » écrasé : entier + chiffre de fraction
    assert ia.inch_token("10%") == ([10, 1], None)
    assert ia.inch_token("7z") == ([7], None)
    assert ia.inch_token("g4oh") == ([], None)  # jeton sans chiffre initial : rien d'inventé
    assert 52 in ia.inch_token("52745")[0]
    assert ia.inch_token("28 3/4") == ([28], 28.75)


def test_parse_dims_line_inches_to_cm_only_when_exact():
    d = ia.parse_dims_line("H. 28 3/4 in. W. 36 1/2 in. Canvas.")
    assert d["h_cm"] == pytest.approx(73.0, abs=0.1) and d["w_cm"] == pytest.approx(92.7, abs=0.1)
    d = ia.parse_dims_line("H. 1587 in. W.2253 in. Canvas. Signed: X.")
    assert d["h_cm"] is None and 15 in d["h_in_options"] and 22 in d["w_in_options"]
    d = ia.parse_dims_line("H.313in. W.4531n. Canvas.")  # « in » lu « 1n »
    assert 31 in d["h_in_options"] and 45 in d["w_in_options"]
    assert ia.parse_dims_line("Signed: Corot. Canvas.") is None
    assert ia.parse_dims_line("H. gin. W. 18in. Wood.") is None


# --- lecture et segmentation -------------------------------------------------------------------


def test_parse_djvu_normalized_coordinates():
    (page,) = ia.parse_djvu(FIXTURE)
    assert (page.width, page.height) == (2547, 3978)
    words = [w for b in page.blocks for ln in b.lines for w in ln.words]
    assert words and all(0 <= v <= 1 for w in words for v in w.bbox)
    assert all(w.bbox[0] < w.bbox[2] and w.bbox[1] < w.bbox[3] for w in words)  # y haut < y bas
    assert page.text.splitlines()[0] == "BRUEGEL— BRUSH"


def test_segmentation_notices_artist_and_attributes():
    c = cfg()
    pages = ia.parse_djvu(FIXTURE)
    ns = ia.segment_ia(pages, c.segmentation, 1, 1)
    assert len(ns) == 2
    assert ns[0].artist and ns[0].artist.name == "BRUEGEL, JAN, THE ELDER"
    assert ns[0].lines[0][2].text.startswith("THE HILL.")
    assert ns[0].credit and ns[0].credit[0][2].text == "Purchase, 1871."
    attrs = ia.extract_attrs(ns[1], {0: "pg"}, c.segmentation)
    kinds = {a["kind"]: a for a in attrs}
    assert kinds["title"]["text"] == "THE WINDMILL"
    assert kinds["credit"]["value"] == {"credit_line": "Purchase, 1871.", "year": 1871}
    assert kinds["dimensions"]["value"]["h_in_options"] == [73, 7]
    for a in attrs:  # offsets exacts sur le texte de la page
        assert pages[0].text[a["char_start"] : a["char_end"]] == a["text"]
    # notice 1 : repérage (« B83-1 / Gallery / 28 ») et titre courant exclus de la notice
    assert not any("Gallery" in ln.text for _, _, ln in ns[0].lines)


def test_artist_value():
    h = ia.Heading("ZORN, ANnperRs. Swedish; born 1860", "ZORN, ANnperRs", 0, 0, 14)
    assert ia.artist_value(h) == "ANnperRs ZORN"


# --- résolution : candidat unique / ambigu -----------------------------------------------------
# « THE HILL » : entiers lus H 7, W 10 ou 1 ; « THE WINDMILL » : H 73 ou 7, W 102 ou 10.

SMALL_A = (19.7, 26.7)  # 7 3/4 x 10 1/2 in. : compatible avec les deux notices
SMALL_B = (19.1, 26.0)  # 7 1/2 x 10 1/4 in. : idem
BIG = (186.0, 260.0)  # 73 x 102 in. : compatible avec la seule notice « THE WINDMILL »


def _build(tmp_path, refs):
    def opener(url, headers):
        body = FIXTURE if url.endswith("_djvu.xml") else json.dumps(META).encode()
        return 200, {}, body

    client = ia.IAClient(tmp_path / "cache", opener=opener, sleep=lambda s: None)
    out = tmp_path / "slice"
    return ia.build_ia_volume(cfg(), client, out, root=ROOT, refs=refs), out


def test_resolution_ambiguous(tmp_path):
    rep, _ = _build(tmp_path, [ref("1", SMALL_A), ref("2", SMALL_B)])
    assert rep["notices"] == 2 and rep["resolved"] == 0
    assert rep["unresolved_by_reason"] == {"candidats multiples": 2}
    assert rep["ambiguous_notices_ge2_candidates"] == 2


def test_resolution_collision_one_object_two_notices(tmp_path):
    rep, out = _build(tmp_path, [ref("1", SMALL_A)])  # candidat unique pour chacune des deux
    assert rep["resolved"] == 0 and rep["met_objects_claimed_by_several_notices"] == 1
    assert rep["unresolved_by_reason"] == {"fiche revendiquée par plusieurs notices": 2}
    arts = export.read_jsonl(out / "artworks.jsonl", ArtworkRef)
    assert all(not a.external_ids for a in arts)


def test_resolution_unique_e2_slice_and_review(tmp_path):
    rep, out = _build(tmp_path, [ref("1", BIG)])
    assert rep["resolved"] == rep["resolved_E2"] == 1 and rep["resolved_with_cc0_image"] == 1
    assert rep["unresolved_by_reason"] == {"moins de 2 attributs concordants": 1}
    spans = {s.id: s for s in export.read_jsonl(out / "spans.jsonl", Span)}
    links = export.read_jsonl(out / "links.jsonl", Link)
    arts = {a.id: a for a in export.read_jsonl(out / "artworks.jsonl", ArtworkRef)}
    assert rep["spans"] == len(spans) == len(links) == 2
    assert all(lk.status == LinkStatus.machine_proposed for lk in links)  # jamais validated
    assert all(sp.text_fidelity == "ocr_raw" for sp in spans.values())
    resolved = [a for a in arts.values() if a.resolution.status == "resolved"]
    assert len(resolved) == 1 and resolved[0].external_ids == [{"scheme": "met", "ref_id": "met:1"}]
    assert resolved[0].artwork_local_id.endswith("#2")
    # droits : texte selon la fiche, mention IA absente consignée ; image CC0 si résolue
    lk = next(k for k in links if k.artwork_id == resolved[0].id)
    assert any("aucune mention de licence" in r.basis for r in lk.rights if r.asset == "text")
    assert any(r.asset == "images" and r.decision.value == "allow" for r in lk.rights)
    other = next(k for k in links if k.artwork_id != resolved[0].id)
    assert not any(r.asset == "images" for r in other.rights)
    # adaptateur de revue : 2 éléments passage-œuvre + 1 élément identity distinct
    items = review.ia_notices_items(out)
    assert sorted(i.kind for i in items) == ["identity", "passage_link", "passage_link"]
    review.check_texts(items, spans)
    ident = next(i for i in items if i.kind == "identity")
    assert ident.artwork.image_display_allowed and ident.artwork.image_url.endswith("1.jpg")
    assert ident.proposal and ident.proposal.evidence_mechanism == "identity_E2_composite"
    assert {h.label.split(" ")[0] for h in ident.highlights} >= {"dimensions", "credit"}
    shown = next(i for i in items if i.kind == "passage_link" and i.artwork.id == resolved[0].id)
    assert shown.artwork.image_display_allowed and shown.artwork.accession_number == "71.1"
    plain = next(i for i in items if i.kind == "passage_link" and i.artwork.id != resolved[0].id)
    assert plain.artwork.image_url is None and not plain.artwork.image_display_allowed


# --- client ------------------------------------------------------------------------------------


def test_client_cache_rate_and_stop(tmp_path):
    calls, t = [], [0.0]
    sleeps = []

    def opener(url, headers):
        calls.append((url, headers["User-Agent"]))
        return 200, {}, b"<x/>"

    def sleep(s):
        sleeps.append(s)
        t[0] += s

    c = ia.IAClient(tmp_path, opener=opener, clock=lambda: t[0], sleep=sleep)
    a = c.djvu("ident")
    c.metadata("ident")
    assert sleeps and sleeps[0] == pytest.approx(1.0)  # au plus 1 requête par seconde
    assert a.sha256 and not a.from_cache
    assert c.djvu("ident").from_cache and len(calls) == 2  # cache
    assert calls[0][1] == ia.USER_AGENT

    def refuse(url, headers):
        return 403, {}, b""

    c2 = ia.IAClient(tmp_path / "b", opener=refuse, sleep=lambda s: None)
    with pytest.raises(ia.IAStop):
        c2.djvu("ident")
    with pytest.raises(ia.IAStop):  # arrêt consigné : aucune nouvelle requête
        c2.metadata("ident")
