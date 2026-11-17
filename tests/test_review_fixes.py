"""Régressions de la revue indépendante du lot C3-C5 (voir le commit correspondant)."""

import copy
import itertools
from pathlib import Path

import pytest
import yaml

from lesternowak import catalogue as cat
from lesternowak import export
from lesternowak import gallica as g
from lesternowak.alto import parse_alto
from lesternowak.models import Figure, Link, Span
from test_catalogue import CFG, PAGES, alto_xml, run_build, server


@pytest.fixture
def env(tmp_path):
    (tmp_path / "sheet.yaml").write_text(
        yaml.safe_dump([{"id": "fake-vol", "pd_status": True, "pd_basis": "x", "url": "http://x"}])
    )
    cfgp = tmp_path / "fake.yaml"
    cfgp.write_text(yaml.safe_dump(CFG))
    return tmp_path, cfgp


@pytest.fixture
def pages():
    saved = copy.deepcopy(PAGES)
    yield PAGES
    PAGES.clear()
    PAGES.update(saved)


def build(env, **kw):
    opener, calls = server()
    rep, out, _ = run_build(env, opener, **kw)
    return rep, out, calls


def spans_of(out):
    return export.read_jsonl(out / "spans.jsonl", Span)


# 1. source_bbox -------------------------------------------------------------------------------


def test_span_source_bbox_is_xyxy_and_roundtrips(env):
    _, out, _ = build(env)
    n = 0
    for sp in spans_of(out):
        ref = sp.page_refs[0]
        x0, y0, x1, y1 = ref.source_bbox
        assert x1 > x0 and y1 > y0  # (x0, y0, x1, y1), pas (HPOS, VPOS, W, H)
        assert ref.source_coordinate_system == "alto:pixel:1000x2000"
        nx0, ny0, nx1, ny1 = ref.bbox
        assert (nx0 * 1000, ny0 * 2000, nx1 * 1000, ny1 * 2000) == pytest.approx(
            (x0, y0, x1, y1), abs=1.0
        )
        n += 1
    assert n > 5


# 2. segmentation : confusions OCR et trous ----------------------------------------------------


def alto_page(lines):
    return parse_alto(alto_xml([[x] for x in lines]))


def make_seg():
    import re

    sg = CFG["segmentation"]
    tok = r"(?P<number>\d{1,4})"
    return cat.Segmentation(
        notice_start=re.compile(sg["notice_start"]),
        loose=re.compile(sg["notice_start"].replace(tok, r"(?P<number>[0-9SsIl|OoB]{1,4})")),
        skip_lines=[re.compile(x) for x in sg["skip_lines"]],
    )


def test_ocr_digit_confusions_accepted_only_when_expected():
    pg = alto_page(["1. un", "2. deux", "3. trois", "4. quatre", "S. cinq", "6. six", "l1. onze"])
    notices = cat.segment([pg], make_seg())
    assert [n.number for n in notices] == [1, 2, 3, 4, 5, 6]  # « S. » lu 5 car 5 est attendu
    assert [n.ocr_digit_fix for n in notices] == [False] * 4 + [True, False]
    # « S. » n'est pas accepté quand 2 est attendu (S -> 5 ne correspond pas)
    pg2 = alto_page(["1. un", "S. bruit", "2. deux"])
    assert [n.number for n in cat.segment([pg2], make_seg())] == [1, 2]
    pg4 = alto_page(["1. un", "2. deux", "S. trois", "4. quatre", "S. cinq"])  # S = 3 puis 5
    assert [n.number for n in cat.segment([pg4], make_seg())] == [1, 2, 3, 4, 5]
    pg3 = alto_page(["1. un", "2. deux", "I3. trois", "O. zéro", "4. quatre"])
    assert [n.number for n in cat.segment([pg3], make_seg())] == [1, 2, 4]  # « I3 » = 13, refusé


def test_gap_marks_previous_notice_uncertain_and_links_unresolved(env, pages):
    pages[4] = [
        ["Texte sans numéro de notice", "suite du texte."]
    ]  # la notice 3 n'est pas reconnue
    rep, out, _ = build(env)
    arts = {a.catalogue_number: a for a in export.read_jsonl(out / "artworks.jsonl", cat.Artwork)}
    assert "3" not in arts and "segmentation_uncertain" in arts["2"].flags
    assert "segmentation_uncertain" not in arts["4"].flags
    links = export.read_jsonl(out / "links.jsonl", Link)
    by_art = {}
    for lk in links:
        by_art.setdefault(lk.artwork_id, set()).add(lk.status.value)
    assert by_art[arts["2"].id] == {"unresolved"}
    assert by_art[arts["4"].id] == {"machine_proposed"}
    lk2 = next(lk for lk in links if lk.artwork_id == arts["2"].id)
    assert (
        "segmentation_uncertain" in lk2.evidence[0].explanation
        and "3" in lk2.evidence[0].explanation
    )
    assert rep["uncertain_notices"] == 1 and rep["missing_numbers"] == 1
    assert rep["gap_rate"] == pytest.approx(1 / 6, abs=1e-3)


def test_range_lot_does_not_create_a_gap():
    import re

    seg = cat.Segmentation(
        notice_start=re.compile(r"^(?P<number>\d{1,4})(?:-(?P<number_end>\d{1,4}))?\s+—\s"),
    )
    pg = alto_page(["1 — a", "2-3 — b", "4 — c"])
    notices = cat.segment([pg], seg)
    assert [(n.number, n.end_number, n.flags) for n in notices] == [
        (1, None, []),
        (2, 3, []),
        (4, None, []),
    ]


# 3. bruit : en-têtes, qualité OCR --------------------------------------------------------------


def test_folio_header_lines_are_not_notice_text(env, pages):
    pages[3] = [["12 DUPONT"], *pages[3]]
    cfg = copy.deepcopy(CFG)
    cfg["segmentation"]["skip_lines"].append(r"^\s*\d{1,3}\s+[A-Z][A-Z' .()-]{3,}\s*$")
    env[1].write_text(yaml.safe_dump(cfg))
    _, out, _ = build(env)
    texts = [s.text for s in spans_of(out)]
    assert not any("12 DUPONT" in t for t in texts)
    assert any(t.startswith("2. Tableau numéro 2") for t in texts)
    env[1].write_text(yaml.safe_dump(CFG))  # sans la règle, l'en-tête serait absorbé
    _, out2, _ = build(env)
    assert any("12 DUPONT" in s.text for s in spans_of(out2))


def test_low_quality_span_kept_with_flag_but_not_linked(env, pages):
    pages[6] = [["5. ~'^K &«-F|M: 1 2 3 ~~ ;; ##", "«&#% 12 ~ '' ^^ |"]]
    rep, out, _ = build(env)
    bad = [s for s in spans_of(out) if s.quality_flag == "low_letter_share"]
    assert len(bad) == 1 and bad[0].text.startswith("5. ~'^K")
    linked = {lk.span_id for lk in export.read_jsonl(out / "links.jsonl", Link)}
    assert bad[0].id not in linked and rep["low_quality_spans"] == 1


def test_quality_flag_letters_and_wc():
    assert cat.quality_flag("Portrait de femme", 0.9, 0.6, 0.5) is None
    assert cat.quality_flag("~'<K &«-F<M: 12", None, 0.6, None) == "low_letter_share"
    assert cat.quality_flag("Portrait de femme", 0.3, 0.6, 0.5) == "low_wc"
    assert cat.quality_flag("Portrait de femme", None, 0.6, 0.5) is None  # WC absent : pas de seuil


def test_wc_read_from_alto():
    xml = (
        b'<alto xmlns="http://www.loc.gov/standards/alto/ns-v2#"><Layout><Page WIDTH="100" '
        b'HEIGHT="100"><PrintSpace><TextBlock><TextLine HPOS="1" VPOS="1" WIDTH="9" HEIGHT="9">'
        b'<String CONTENT="a" WC="0.2"/><String CONTENT="b" WC="0.4"/></TextLine></TextBlock>'
        b"</PrintSpace></Page></Layout></alto>"
    )
    assert parse_alto(xml).blocks[0].lines[0].wc == pytest.approx(0.3)


# 4. mojibake token par token --------------------------------------------------------------------


def test_mojibake_repaired_per_token_with_raw_text_and_normalizations(env, pages):
    pages[3] = [["3. Notre JÃ©sus et Jésus ici", "Ã\xa0 la fin."]]
    _, out, _ = build(env)
    sp = next(s for s in spans_of(out) if "Jésus" in s.text)
    assert sp.text.startswith("3. Notre Jésus et Jésus ici")  # seul le jeton fautif est réparé
    assert sp.raw_text.startswith("3. Notre JÃ©sus et Jésus ici")
    assert sp.normalizations == ["mojibake_utf8_latin1"] and sp.text_fidelity == "ocr_raw"
    clean = next(s for s in spans_of(out) if s.text.startswith("4. "))
    assert clean.raw_text is None and clean.normalizations == []


# 5. figures ---------------------------------------------------------------------------------------


def _fig_page(ills, caps):
    return parse_alto(alto_xml([[c] for c in caps], ills))


def test_dedupe_near_identical_illustrations():
    pg = _fig_page([(100, 400, 600, 500), (102, 401, 600, 500), (100, 1200, 600, 400)], [])
    assert len(cat.dedupe_illustrations(pg.illustrations)) == 2


def test_caption_goes_to_one_figure_only():
    import re

    seg = cat.Segmentation(
        notice_start=re.compile(r"(?P<number>\d+)"),
        caption_number=re.compile(r"No (?P<number>\d+)"),
    )
    # deux figures voisines, une seule légende : la plus proche la reçoit, l'autre reste libre
    pg = _fig_page([(100, 330, 700, 400), (100, 800, 700, 400)], ["No 7"])
    ills = pg.illustrations
    got = cat.assign_captions(pg, ills, seg, min_area=0.02)
    assert list(got) == [0] and got[0][0] == 7
    pg2 = _fig_page([(100, 330, 700, 400)], ["No 7", "No 8"])
    assert (
        len(cat.assign_captions(pg2, pg2.illustrations, seg, 0.02)) == 1
    )  # une figure, une légende


def test_small_figure_never_linked():
    import re

    seg = cat.Segmentation(
        notice_start=re.compile(r"(?P<number>\d+)"),
        caption_number=re.compile(r"No (?P<number>\d+)"),
    )
    pg = _fig_page([(100, 330, 100, 100)], ["No 7"])  # 1 % de la page environ
    assert cat.assign_captions(pg, pg.illustrations, seg, min_area=0.02) == {}
    assert len(cat.assign_captions(pg, pg.illustrations, seg, min_area=0.001)) == 1


def test_pipeline_links_caption_to_single_figure(env):
    _, out, _ = build(env)
    figs = export.read_jsonl(out / "figures.jsonl", Figure)
    caps = [f.caption_span_id for f in figs if f.caption_span_id]
    assert len(caps) == len(set(caps)) == 1


# 6. limiteur --------------------------------------------------------------------------------------


class Clock:
    def __init__(self):
        self.t = 5000.0

    def now(self):
        return self.t

    def sleep(self, dt):
        self.t += dt


def test_margin_20_percent_and_shared_alto_quota():
    c = Clock()
    lim = g.Limiter(c.now, c.sleep)
    times = []
    for svc in itertools.islice(itertools.cycle(["alto", "alto_rde"]), 8):
        lim.acquire(svc)
        times.append(c.t)
    gaps = [b - a for a, b in itertools.pairwise(times)]
    assert min(gaps) >= 60 / 5 * 1.2 - 1e-9  # 14,4 s, v3 et RDE confondus


def test_limiter_state_persists_between_processes(tmp_path):
    c = Clock()
    st = tmp_path / "_limiter.json"
    g.Limiter(c.now, c.sleep, st).acquire("alto")
    t0 = c.t
    assert st.exists()
    lim2 = g.Limiter(c.now, c.sleep, st)  # nouveau « processus »
    lim2.acquire("alto_rde")
    assert c.t - t0 >= 14.4 - 1e-9


def test_first_403_is_persisted_and_counts_in_next_process(tmp_path):
    c = Clock()
    seq = [(403, {}, b"cf"), (200, {}, b"ok")]
    calls = []

    def opener(url, h):
        calls.append(url)
        return seq[len(calls) - 1]

    def mk(op):
        return g.GallicaClient(
            cache_root=tmp_path,
            limiter=g.Limiter(c.now, c.sleep, tmp_path / "_limiter.json"),
            opener=op,
        )

    mk(opener).oai("bpt6k1")  # un 403 puis succès
    state = (tmp_path / "_limiter.json").read_text()
    assert '"forbidden"' in state and "403" in state
    c2 = mk(lambda u, h: (403, {}, b"cf"))
    assert c2.stops == 1
    with pytest.raises(g.GallicaStop):
        c2.pagination("bpt6k1")  # le second 403 (tous processus confondus) arrête


# 7. droits ----------------------------------------------------------------------------------------


def refused(env, sheet):
    tmp, cfgp = env
    (tmp / "sheet.yaml").write_text(yaml.safe_dump([{"id": "fake-vol", **sheet}]))
    calls = []

    def opener(url, h):
        calls.append(url)
        return 200, {}, b""

    client = g.GallicaClient(
        cache_root=tmp / "raw", limiter=g.Limiter(lambda: 0.0, lambda d: None), opener=opener
    )
    with pytest.raises(cat.RightsRefused):
        cat.build_volume(cat.load_config(cfgp), client, tmp / "out", root=tmp)
    return calls


def test_unknown_rights_refused_before_any_download(env):
    assert refused(env, {"pd_status": "unknown", "pd_basis": "?"}) == []
    assert refused(env, {"pd_status": False}) == []


def test_excluded_volume_refused_before_any_download(env):
    assert refused(env, {"pd_status": True, "excluded_reason": "décision"}) == []


def test_repo_ribes_config_is_refused_without_network():
    cfg = cat.load_config(Path("config/catalogues/vente-ribes-christofle-1928.yaml"))

    def no_net(url, h):
        raise AssertionError(url)

    client = g.GallicaClient(cache_root=Path("/nonexistent-cache"), opener=no_net)
    with pytest.raises(cat.RightsRefused, match="exclu"):
        cat.build_volume(cfg, client, Path("/nonexistent-out"))
    sheet = yaml.safe_load(Path("docs/sources/inventory/gallica.yaml").read_text("utf-8"))
    assert next(r for r in sheet if r["id"] == cfg.id)["excluded_reason"]


def test_title_page_flag_needs_named_people():
    role_only = ["CATALOGUE\n\nCOMMISSAIRES-PRISEURS\n\nEXPERTS\n\nEXPOSITION le 9 décembre"]
    assert cat.title_page_flag(role_only) is None
    named = [
        "COMMISSAIRES-PRISEURS |M e F. LAIR DUBREUIL |Me HENRI BAUDOIN |EXPERTS |M. JULES FÉRAL"
    ]
    assert "nommé" in cat.title_page_flag(named)


def test_named_experts_stop_before_alto(env, monkeypatch):
    opener, calls = server()
    monkeypatch.setattr(cat, "title_page_flag", lambda pages: "page de titre : expert nommé")
    _tmp, cfgp = env
    cfg = yaml.safe_load(cfgp.read_text())
    cfg["type"] = "sale_catalogue"
    cfgp.write_text(yaml.safe_dump(cfg))
    with pytest.raises(cat.RightsRefused):
        run_build(env, opener)
    assert not any("alto" in u for u in calls)
