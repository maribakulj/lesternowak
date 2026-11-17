"""Pipeline volume -> slice, hors ligne : serveur Gallica simulé, volume fictif de 7 vues."""

import re
from pathlib import Path

import pytest
import yaml

from lesternowak import catalogue as cat
from lesternowak import export, review
from lesternowak import gallica as g
from lesternowak.alto import parse_alto
from lesternowak.models import Figure, Link, Span
from lesternowak.referentials import ReferenceArtwork

ARK = "bpt6kfake"
CFG = {
    "id": "fake-vol",
    "source": "gallica",
    "ark": ARK,
    "route": "gallica_alto",
    "type": "museum_catalogue",
    "language": "fre",
    "rights_sheet": "sheet.yaml",
    "referential": "louvre",
    "pages": {"mode": "auto", "max_pages": 50},
    "segmentation": {
        "notice_start": r"^\s*(?P<number>\d{1,4})\s*\.\s+(?=\S)",
        "max_gap": 5,
        "first_max": 5,
        "artist_heading": r"^[A-Z][A-Z' -]{3,}\s*(?:\([^)]*\))?\s*\.?\s*$",
        "skip_lines": [r"^\s*\d{1,3}\s*$"],
        "caption_number": r"(?i)\bn[o°]\s*(?P<number>\d{1,4})\b",
    },
}
# vue k (2..7) : notice k-1 ; la vue 4 porte l'illustration et sa légende « No 3 »
PAGES = {
    1: [["CATALOGUE FICTIF"]],
    **{
        v: [[f"{v - 1}. Tableau numéro {v - 1}", f"Description du tableau {v - 1}."]]
        for v in range(2, 8)
    },
}
PAGES[2] = [["DUPONT (Jean)."], *PAGES[2], ["H. 0, 50. - L. 0, 65."]]
PAGES[5] = [["Suite de la notice précédente."], *PAGES[5]]


def alto_xml(blocks, illus=()):
    out = [
        '<alto xmlns="http://www.loc.gov/standards/alto/ns-v2#"><Description>'
        "<MeasurementUnit>pixel</MeasurementUnit></Description><Layout>"
        '<Page WIDTH="1000" HEIGHT="2000"><PrintSpace>'
    ]
    y = 100
    for b, lines in enumerate(blocks):
        out.append(
            f'<TextBlock ID="b{b}" HPOS="100" VPOS="{y}" WIDTH="800" HEIGHT="{50 * len(lines)}">'
        )
        for ln in lines:
            out.append(f'<TextLine HPOS="100" VPOS="{y}" WIDTH="800" HEIGHT="40">')
            for i, w in enumerate(ln.split()):
                out.append(
                    f'<String CONTENT="{w}" HPOS="{100 + 60 * i}" VPOS="{y}" '
                    'WIDTH="50" HEIGHT="40"/>'
                )
            out.append("</TextLine>")
            y += 50
        out.append("</TextBlock>")
        y += 60
    for h, v, w, hh in illus:
        out.append(f'<Illustration ID="i" HPOS="{h}" VPOS="{v}" WIDTH="{w}" HEIGHT="{hh}"/>')
    out.append("</PrintSpace></Page></Layout></alto>")
    return "".join(out).replace("&", "&amp;").encode()


def server(alto_status=200, status403=False):
    calls = []

    def opener(url, headers):
        calls.append(url)
        if "OAIRecord" in url:
            return (
                200,
                {},
                (
                    b"<r xmlns:dc='http://purl.org/dc/elements/1.1/'><dc:title>Fictif</dc:title>"
                    b"<dc:creator>Auteur</dc:creator></r>"
                ),
            )
        if "Pagination" in url:
            pg = "".join(
                f"<page><numero>{'NP' if v == 1 else v - 1}</numero><ordre>{v}</ordre></page>"
                for v in range(1, 8)
            )
            return (
                200,
                {},
                f"<livre><structure><hasToc>false</hasToc></structure><pages>{pg}</pages></livre>".encode(),
            )
        if "manifest.json" in url:
            return 200, {}, b"{}"
        if url.endswith(".texteBrut"):
            pages = ["\n\n".join("\n".join(b) for b in PAGES[v]) for v in range(1, 8)]
            return 200, {}, "</BR>".join(p.replace("\n", "<br/>") for p in pages).encode()
        m = re.search(r"/f(\d+)/alto.xml", url)
        if m:
            if status403:
                return 403, {}, b"cf"
            if alto_status != 200:
                return alto_status, {}, b"{}"
            v = int(m.group(1))
            illus = [(200, 330, 600, 400)] if v == 4 else []
            blocks = PAGES[v] + ([["No 3"]] if v == 4 else [])
            return 200, {}, alto_xml(blocks, illus)
        return 404, {}, b""

    return opener, calls


@pytest.fixture
def env(tmp_path):
    (tmp_path / "sheet.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "fake-vol",
                    "pd_status": True,
                    "pd_basis": "anonyme avant 1956",
                    "url": "http://x",
                }
            ]
        )
    )
    cfgp = tmp_path / "fake.yaml"
    cfgp.write_text(yaml.safe_dump(CFG))
    return tmp_path, cfgp


def run_build(env, opener, ref_index=None, sheet_status=None):
    tmp, cfgp = env
    if sheet_status is not None:
        (tmp / "sheet.yaml").write_text(
            yaml.safe_dump(
                [{"id": "fake-vol", "pd_status": sheet_status, "pd_basis": "x", "url": "http://x"}]
            )
        )
    client = g.GallicaClient(
        cache_root=tmp / "raw", limiter=g.Limiter(lambda: 0.0, lambda dt: None), opener=opener
    )
    cfg = cat.load_config(cfgp)
    rep = cat.build_volume(
        cfg, client, tmp / "out", root=tmp, ref_index=ref_index, log=lambda *_: None
    )
    return rep, tmp / "out", client


def test_build_notices_spans_links_figures(env):
    opener, _ = server()
    rep, out, _ = run_build(env, opener)
    assert rep["notices"] == 6 and rep["pages_alto"] == 6 and rep["alto_404"] == 0
    spans = export.read_jsonl(out / "spans.jsonl", Span)
    links = export.read_jsonl(out / "links.jsonl", Link)
    assert len(links) == len(spans) - 1 and all(s.text_fidelity == "ocr_raw" for s in spans)
    # offsets : text[start:end] == span.text sur la page canonique de l'ALTO mis en cache
    pages = {}
    for p in export.read_jsonl(out / "assets.jsonl", cat.SourceAsset):
        pages[p.id] = parse_alto(Path(p.local_path).read_bytes()).text
    for s in spans:
        assert pages[s.asset_id][s.char_start : s.char_end] == s.text
        ref = s.page_refs[0]
        assert ref.alignment == "verified" and ref.bbox and all(0 <= x <= 1 for x in ref.bbox)
    assert {lk.evidence[0].mechanism for lk in links} == {"notice_structure"}
    assert {lk.status for lk in links} == {"machine_proposed"}
    # la continuation de la vue 5 revient à la notice 3 ; l'intitulé d'artiste clôt la notice
    n3 = [s for s in spans if s.section_label == "notice 3"]
    assert any(s.text.startswith("Suite de la notice") for s in n3)
    arts = {a.catalogue_number: a for a in export.read_jsonl(out / "artworks.jsonl", cat.Artwork)}
    assert arts["1"].artist_heading == "DUPONT (Jean)." and arts["1"].local_label.startswith("1. ")
    assert arts["1"].artwork_local_id == "fake-vol#1"
    assert arts["1"].resolution.status == "unresolved"
    # figure de la vue 4 rattachée à la notice 3 par « No 3 » seulement
    figs = export.read_jsonl(out / "figures.jsonl", Figure)
    assert len(figs) == 1 and figs[0].linked_artwork_local_id == "fake-vol#3"
    assert figs[0].link_evidence[0].mechanism == "caption_number"
    assert "/800,/0/" in figs[0].image_url and figs[0].caption_span_id in {s.id for s in spans}
    # le texte de la légende n'est pas du texte de notice
    assert not any("No 3" in s.text for s in n3)


def test_rebuild_is_deterministic_and_cached(env):
    opener, calls = server()
    _, out, _ = run_build(env, opener)
    ids1 = [lk.id for lk in export.read_jsonl(out / "links.jsonl", Link)]
    n = len(calls)
    _, out, _ = run_build(env, opener)
    assert [lk.id for lk in export.read_jsonl(out / "links.jsonl", Link)] == ids1
    assert len(calls) == n  # tout vient du cache permanent


def test_rights_unknown_never_allow_and_gallica_images(env):
    opener, _ = server()
    _, out, _ = run_build(env, opener, sheet_status="unknown")
    rights = export.read_jsonl(out / "rights.jsonl", cat.RightsDecision)
    assert {r.decision.value for r in rights if r.asset == "text"} == {"unknown"}
    img = {r.action: r.decision.value for r in rights if r.asset == "images"}
    assert img["display_pilot"] == "allow" and img["publish_image"] == "conditional"
    _, out, _ = run_build(env, opener, sheet_status=True)
    rights = export.read_jsonl(out / "rights.jsonl", cat.RightsDecision)
    assert {r.decision.value for r in rights if r.asset == "text"} == {"allow"}


def test_alto_404_falls_back_to_text_without_geometry(env):
    opener, _ = server(alto_status=404)
    rep, out, _ = run_build(env, opener)
    assert rep["alto_404"] == 3 and any("repli texteBrut" in n for n in rep["notes"])
    spans = export.read_jsonl(out / "spans.jsonl", Span)
    assert spans and all(s.page_refs[0].bbox is None for s in spans)
    assert all(s.page_refs[0].alignment == "estimated" for s in spans)
    assert rep["notices"] >= 5 and rep["figures"] == 0


def test_stop_on_403_keeps_partial_slice(env):
    opener, calls = server(status403=True)
    rep, _out, _client = run_build(env, opener)
    assert any(n.startswith("ARRÊT") for n in rep["notes"]) and rep["spans"] == 0
    assert (env[0] / "raw" / "_stop.json").exists()
    assert sum("alto.xml" in u for u in calls) == 2  # deux 403 puis arrêt


def test_resolver_not_forced_on_dims_and_artist_only(env):
    opener, _ = server()
    ref = ReferenceArtwork(
        ref_id="louvre:1",
        source="louvre",
        external_id="1",
        artist="DUPONT Jean",
        dimensions_cm=(50.0, 65.0),
    )
    _, out, _ = run_build(env, opener, ref_index=[ref])
    a1 = next(
        a
        for a in export.read_jsonl(out / "artworks.jsonl", cat.Artwork)
        if a.catalogue_number == "1"
    )
    assert a1.resolution.status == "unresolved" and not a1.external_ids
    assert a1.resolution.candidates == ["louvre:1"] and "indépendants" in a1.resolution.reason


def test_local_dimensions_and_segmentation_noise():
    assert cat.local_dimensions_cm("H. 0, 96. - L. 0, 76. — B.") == (96.0, 76.0)
    assert cat.local_dimensions_cm("sans mesures") is None
    c = [(0, 0, 0, 1), (0, 0, 1, 2), (0, 0, 2, 900), (0, 0, 3, 3), (1, 0, 0, 4)]
    assert [x[3] for x in cat.accepted_starts(c, 5, 5)] == [1, 2, 3, 4]
    late = [(0, 0, 0, 40), (0, 0, 1, 41)]  # première série trop haute et incohérente
    assert cat.accepted_starts(late, 5, 5) == []


def test_review_adapter_on_gallica_slice(env):
    opener, _ = server()
    _, out, _ = run_build(env, opener)
    items = review.gallica_items(out)
    spans = {s.id: s for s in export.read_jsonl(out / "spans.jsonl", Span)}
    assert len(items) == len(export.read_jsonl(out / "links.jsonl", Link))
    for it in items:
        assert it.passage.text == spans[it.passage.span_id].text
        assert it.source.url.startswith("https://gallica.bnf.fr/ark:/12148/")
        assert it.source.page_image_url.endswith(".medres")
        for h in it.highlights:
            assert it.passage.text[h.start : h.end].strip()[0].isdigit()
    first = next(i for i in items if i.artwork.catalogue_number == "1")
    assert first.highlights and first.proposal.evidence_mechanism == "notice_structure"
    with3 = next(i for i in items if i.artwork.catalogue_number == "3")
    assert with3.artwork.image_url and with3.artwork.image_display_allowed
    q = review.make_combined_queue([("gallica-notices", out)], 0.15, 7)
    assert len(q) == len(items) and any(i.blind for i in q)


def test_toc_article_pages():
    toc = (
        b"<TEI><row><cell><seg>Paul Durrieu</seg></cell><cell><seg>QUELQUES PORTRAITS X</seg>"
        b"</cell>"
        b"<cell><xref>461</xref></cell></row><row><cell><seg>Autre</seg></cell><cell><seg>T</seg></cell>"
        b"<cell><xref>464</xref></cell></row></TEI>"
    )
    labels = [("", 1), ("461", 10), ("462", 11), ("463", 12), ("464", 13)]
    art = {"author": "Paul Durrieu", "title_match": "QUELQUES PORTRAITS"}
    assert cat.toc_article_pages(toc, art, labels) == [10, 11, 12]


def test_config_rejects_unknown_route(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump({**CFG, "route": "pdf"}))
    with pytest.raises(ValueError):
        cat.load_config(p)


def test_all_repo_configs_load():
    for p in sorted(Path("config/catalogues").glob("*.yaml")):
        cfg = cat.load_config(p)
        assert cfg.id == p.stem and cfg.ark


def test_match_text_index_prefers_exact_and_nearest():
    pages = [
        "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi",
        "Tout autre texte sans rapport avec la page precedente du tout du tout",
        "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi",
    ]
    assert cat.match_text_index(pages[0], pages, center=3) == 3  # à égalité, la plus proche
    assert cat.match_text_index("rien de commun ici", pages, center=2) is None


def test_estimate_offsets_uses_folio_anchors():
    labels = [("", 1), ("", 2), ("1", 3), ("2", 4), ("3", 5), ("4", 6)]
    pages = ["1 Titre courant\ntexte", "2 Titre courant\ntexte", "3 Titre courant\nx", "4 T\ny"]
    assert cat.estimate_offsets(pages, labels) == [2, 2, 2, 2]
    assert cat.estimate_offsets(["sans folio"], labels) == [0]


def test_alto_http_error_skips_page_without_crash(env):
    base, _ = server()

    def opener(url, headers):
        if "/f4/alto.xml" in url:
            return 500, {}, b"boom"
        return base(url, headers)

    rep, _out, _ = run_build(env, opener)
    assert rep["alto_errors"] == 1 and any("vue 4" in n for n in rep["notes"])
    assert rep["pages_alto"] == 5 and rep["notices"] >= 4
