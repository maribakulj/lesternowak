"""Pipeline générique « volume -> slice » (lots C3-C5, C8) : rien de spécifique à un volume.

Tout ce qui dépend du volume vient de `config/catalogues/<id>.yaml` : ark, règle de segmentation
des notices (expressions régulières), pages concernées, droits. Les passages sont des extraits
exacts du texte OCR brut (`ocr_raw`) ; aucun texte n'est produit par un modèle.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import statistics
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import yaml
from lxml import etree
from rapidfuzz import fuzz

from lesternowak import export
from lesternowak.alto import AltoPage, Block, Illustration, Line, parse_alto, union
from lesternowak.gallica import (
    GallicaClient,
    GallicaHTTPError,
    GallicaStop,
    bare_ark,
    iiif_region_url,
    split_textebrut,
)
from lesternowak.models import ArtworkRef as Artwork
from lesternowak.models import (
    Decision,
    Evidence,
    Figure,
    Link,
    LinkStatus,
    PageRef,
    PassageFunction,
    Resolution,
    RightsDecision,
    Run,
    SourceAsset,
    Span,
)

GALLICA_CONDITIONS = (
    "https://gallica.bnf.fr/edit/und/conditions-dutilisation-des-contenus-de-gallica"
)
TEXT_ACTIONS = ("tdm", "publish_text", "redistribute_text", "remote_llm", "training")
IMAGE_REUSE_ACTIONS = ("publish_image", "redistribute_image", "tdm", "remote_llm", "training")


# --- configuration -----------------------------------------------------------------------------


@dataclass
class Segmentation:
    notice_start: re.Pattern
    max_gap: int = 5
    first_max: int = 5
    artist_heading: re.Pattern | None = None
    skip_lines: list[re.Pattern] = field(default_factory=list)
    caption_number: re.Pattern | None = None
    loose: re.Pattern | None = None  # notice_start tolérant aux confusions OCR du numéro


@dataclass
class CatalogueConfig:
    id: str
    ark: str
    route: str
    type: str
    language: str
    rights_sheet: str
    rights_id: str
    referential: str | None
    pages_mode: str
    max_pages: int
    article: dict | None
    segmentation: Segmentation | None
    raw: dict
    min_letter_share: float = 0.6  # qualité OCR : part de lettres minimale d'un passage
    min_wc: float | None = None  # confiance ALTO (WC) moyenne minimale, si disponible
    quality_exempt: list[re.Pattern] = field(default_factory=list)  # ex. lignes de dimensions
    figure_min_area: float = 0.02  # aire minimale (part de la page) d'une figure liable


def load_config(path: Path) -> CatalogueConfig:
    d = yaml.safe_load(path.read_text("utf-8"))
    if d.get("source") != "gallica" or d.get("route") != "gallica_alto":
        raise ValueError(f"{path} : seule la voie gallica_alto est gérée")
    if d["type"] not in ("museum_catalogue", "sale_catalogue", "periodical_article"):
        raise ValueError(f"{path} : type inconnu {d['type']!r}")
    pg = d.get("pages") or {}
    if pg.get("mode") not in ("auto", "toc_article"):
        raise ValueError(f"{path} : pages.mode inconnu")
    sg = d.get("segmentation")
    seg = None
    if sg:
        rx = lambda k: re.compile(sg[k]) if sg.get(k) else None  # noqa: E731
        seg = Segmentation(
            notice_start=re.compile(sg["notice_start"]),
            max_gap=int(sg.get("max_gap", 5)),
            first_max=int(sg.get("first_max", 5)),
            artist_heading=rx("artist_heading"),
            skip_lines=[re.compile(x) for x in sg.get("skip_lines", [])],
            caption_number=rx("caption_number"),
        )
        if "number" not in seg.notice_start.groupindex:
            raise ValueError(f"{path} : notice_start doit définir le groupe « number »")
        tok = r"(?P<number>\d{1,4})"
        if tok in sg["notice_start"]:
            seg.loose = re.compile(
                sg["notice_start"].replace(tok, r"(?P<number>[0-9SsIl|OoB]{1,4})")
            )
    q = d.get("quality") or {}
    return CatalogueConfig(
        id=d["id"],
        ark=bare_ark(d["ark"]),
        route=d["route"],
        type=d["type"],
        language=d.get("language", ""),
        rights_sheet=d["rights_sheet"],
        rights_id=d.get("rights_id", d["id"]),
        referential=d.get("referential"),
        pages_mode=pg["mode"],
        max_pages=int(pg.get("max_pages", 120)),
        article=pg.get("article"),
        segmentation=seg,
        raw=d,
        min_letter_share=float(q.get("min_letter_share", 0.6)),
        min_wc=float(q["min_wc"]) if q.get("min_wc") is not None else None,
        quality_exempt=[re.compile(x) for x in q.get("exempt", [])],
        figure_min_area=float((d.get("figures") or {}).get("min_area", 0.02)),
    )


# --- pages : texte brut, pagination, alignement ----------------------------------------------


def page_from_text(raw: str) -> AltoPage:
    """Page sans géométrie (repli texteBrut) : blocs séparés par une ligne vide."""
    blocks: list[Block] = []
    zero = (0.0, 0.0, 0.0, 0.0)
    for chunk in re.split(r"\n\s*\n", raw):
        lines = [Line(x.strip(), zero, zero) for x in chunk.split("\n") if x.strip()]
        if lines:
            blocks.append(Block(f"t{len(blocks)}", zero, lines))
    out, pos = [], 0
    for bi, b in enumerate(blocks):
        if bi:
            out.append("\n\n")
            pos += 2
        b.start = pos
        for li, ln in enumerate(b.lines):
            if li:
                out.append("\n")
                pos += 1
            ln.start = pos
            out.append(ln.text)
            pos += len(ln.text)
            ln.end = pos
        b.end = pos
    return AltoPage(1.0, 1.0, "none", blocks, [], "".join(out))


def parse_pagination(data: bytes) -> list[tuple[str, int]]:
    """[(numéro imprimé, vue)] ; « NP » (non paginé) -> chaîne vide."""
    root = etree.fromstring(data)
    out = []
    for p in root.iter("page"):
        num = (p.findtext("numero") or "").strip()
        out.append(("" if num == "NP" else num, int(p.findtext("ordre"))))
    return out


_FOLIO = [
    re.compile(r"^(\d{1,4})\s+\D"),
    re.compile(r"\D\s(\d{1,4})\s*$"),
    re.compile(r"^(\d{1,4})$"),
]


def estimate_offsets(
    pages: list[str], labels: list[tuple[str, int]], window: int = 15
) -> list[int]:
    """Décalage vue - indice de page du texte brut (1-based), par médiane d'ancres de folios.

    Le texte brut omet des pages (planches, blancs) : les indices ne sont pas des numéros de vue.
    Estimation seulement ; elle est vérifiée page par page contre l'ALTO."""
    lab2v: dict[str, int] = {}
    for lab, v in labels:
        if lab.isdigit():
            lab2v.setdefault(lab, v)
    anchors: dict[int, int] = {}
    for i, txt in enumerate(pages, 1):
        lines = [x.strip() for x in txt.split("\n") if x.strip()]
        for cand in lines[:2] + lines[-2:]:
            for rx in _FOLIO:
                m = rx.search(cand)
                if m and m.group(1) in lab2v:
                    anchors[i] = lab2v[m.group(1)] - i
                    break
            if i in anchors:
                break
    out = []
    for i in range(1, len(pages) + 1):
        near = [o for j, o in anchors.items() if abs(j - i) <= window]
        if len(near) < 2 and anchors:
            j = min(anchors, key=lambda k: abs(k - i))
            near = [anchors[j]]
        out.append(round(statistics.median(near)) if near else 0)
    return out


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# --- segmentation en notices ------------------------------------------------------------------


@dataclass
class Notice:
    number: int
    label: str  # ligne de début, extrait exact
    artist_heading: str | None
    start_page: int  # indice dans la liste de pages traitées
    runs: list[tuple[int, int, int, int]] = field(default_factory=list)  # page, bloc, l0, l1
    end_number: int | None = None  # « 4-5 » : lot double
    flags: list[str] = field(default_factory=list)
    missing_after: list[int] = field(default_factory=list)  # numéros introuvables ensuite
    ocr_digit_fix: bool = False  # numéro lu malgré une confusion OCR (S/5, I/1, O/0, B/8)


class Cand(NamedTuple):
    page: int
    block: int
    line: int
    number: int
    loose: bool = False  # numéro reconstitué après confusion OCR
    end: int | None = None
    alts: tuple[int, ...] = ()  # lectures possibles du jeton (confusions OCR)


# confusions OCR courantes lettre -> chiffres possibles ; « S » vaut aussi 3 et 6 (relevé sur le
# catalogue de Narbonne : « S - Consuls de l'année 1603 » pour la notice 3)
_OCR_DIGITS = {
    "S": "536",
    "s": "536",
    "I": "1",
    "l": "1",
    "|": "1",
    "O": "0",
    "o": "0",
    "B": "8",
}


def _readings(tok: str) -> tuple[int, ...]:
    opts = [_OCR_DIGITS.get(ch, ch) for ch in tok]
    if not all(all(c.isdigit() for c in o) for o in opts):
        return ()
    return tuple(sorted({int("".join(c)) for c in itertools.product(*opts)}))


def _candidates(pages: list[AltoPage], seg: Segmentation):
    for pi, pg in enumerate(pages):
        for bi, b in enumerate(pg.blocks):
            for li, ln in enumerate(b.lines):
                if any(s.search(ln.text) for s in seg.skip_lines):
                    continue
                m = seg.notice_start.match(ln.text)
                if m:
                    end = m.groupdict().get("number_end")
                    yield Cand(pi, bi, li, int(m.group("number")), False, int(end) if end else None)
                    continue
                m = seg.loose.match(ln.text) if seg.loose else None
                if m:
                    alts = _readings(m.group("number"))
                    if alts:
                        end = m.groupdict().get("number_end")
                        yield Cand(pi, bi, li, alts[0], True, int(end) if end else None, alts)


def accepted_starts(cands, max_gap: int, first_max: int) -> list[Cand]:
    """Suite croissante de numéros plausibles (bruit OCR écarté, resynchronisation sur deux
    candidats consécutifs cohérents). Un numéro reconstitué après confusion OCR n'est accepté
    que s'il est exactement le numéro attendu (suivant)."""
    cs = [Cand(*c) for c in cands]
    out: list[Cand] = []
    last = None
    for k, c in enumerate(cs):
        n = c.number
        if c.loose:  # accepté seulement si le numéro attendu fait partie des lectures possibles
            ok = last is not None and (last + 1) in c.alts
            if ok:
                c = c._replace(number=last + 1)
                n = c.number
        else:
            ok = (n <= first_max) if last is None else (last < n <= last + max_gap)
            if not ok and last is not None and n > last and k + 1 < len(cs):
                nxt = cs[k + 1].number
                ok = n < nxt <= n + max_gap
        if ok:
            out.append(c)
            last = c.end if c.end and c.end >= n else n
    return out


def segment(pages: list[AltoPage], seg: Segmentation) -> list[Notice]:
    cands = list(_candidates(pages, seg))
    starts = {
        (c.page, c.block, c.line): c for c in accepted_starts(cands, seg.max_gap, seg.first_max)
    }
    notices: list[Notice] = []
    cur: Notice | None = None
    artist: str | None = None
    for pi, pg in enumerate(pages):
        for bi, b in enumerate(pg.blocks):
            run_start = None  # première ligne de la série courante dans ce bloc
            for li, ln in enumerate(b.lines):
                key = (pi, bi, li)
                skip = any(s.search(ln.text) for s in seg.skip_lines)
                is_cap = bool(seg.caption_number and seg.caption_number.search(ln.text)) and (
                    len(ln.text) < 60
                )
                head = bool(seg.artist_heading and seg.artist_heading.match(ln.text))
                if key in starts:
                    if cur is not None and run_start is not None:
                        cur.runs.append((pi, bi, run_start, li - 1))
                    c = starts[key]
                    cur = Notice(
                        c.number, ln.text, artist, pi, end_number=c.end, ocr_digit_fix=c.loose
                    )
                    notices.append(cur)
                    run_start = li
                    continue
                breaker = skip or is_cap or head
                if breaker:
                    if cur is not None and run_start is not None:
                        cur.runs.append((pi, bi, run_start, li - 1))
                    run_start = None
                    if head:
                        artist = ln.text
                        cur = None  # un intitulé d'artiste clôt la notice précédente
                    continue
                if cur is not None and run_start is None:
                    run_start = li
            if cur is not None and run_start is not None:
                cur.runs.append((pi, bi, run_start, len(b.lines) - 1))
    mark_gaps(notices)
    return notices


def mark_gaps(notices: list[Notice]) -> None:
    """Un trou dans la suite des numéros signifie qu'une notice absente (non reconnue) a pu être
    absorbée par la précédente : celle-ci est `segmentation_uncertain`."""
    for a, b in itertools.pairwise(notices):
        top = a.end_number if a.end_number and a.end_number >= a.number else a.number
        if b.number > top + 1:
            a.flags.append("segmentation_uncertain")
            a.missing_after = list(range(top + 1, b.number))


def letter_share(text: str) -> float:
    core = [ch for ch in text if not ch.isspace()]
    return sum(ch.isalpha() for ch in core) / len(core) if core else 0.0


def quality_flag(
    text: str, wc: float | None, min_letter_share: float, min_wc: float | None
) -> str | None:
    if letter_share(text) < min_letter_share:
        return "low_letter_share"
    if min_wc is not None and wc is not None and wc < min_wc:
        return "low_wc"
    return None


_DIM_M = re.compile(
    r"\bH\w*\.?\s*(\d)\s*[,.]\s*(\d{1,3}).{0,12}?\bL\w*\.?\s*(\d)\s*[,.]\s*(\d{1,3})"
)


def local_dimensions_cm(text: str) -> tuple[float, float] | None:
    """« H. 0, 96. - L. 0, 76. » (mètres) -> (96.0, 76.0) cm ; sinon None (rien d'inventé)."""
    m = _DIM_M.search(text)
    if not m:
        return None
    f = lambda a, b: float(f"{a}.{b}") * 100  # noqa: E731
    return (round(f(m.group(1), m.group(2)), 1), round(f(m.group(3), m.group(4)), 1))


# --- droits -------------------------------------------------------------------------------------


def _sheet(cfg: CatalogueConfig, root: Path) -> dict:
    for r in yaml.safe_load((root / cfg.rights_sheet).read_text("utf-8")):
        if r.get("id") == cfg.rights_id:
            return r
    raise KeyError(f"fiche de droits introuvable : {cfg.rights_id}")


class RightsRefused(RuntimeError):
    """Volume refusé : droits du texte non établis (jamais de téléchargement dans ce cas)."""


def text_rights(cfg: CatalogueConfig, sheet: dict) -> tuple[Decision, str]:
    """Droits du texte d'après la fiche : `allow` seulement si domaine public ou licence acceptée
    est établi (`pd_status` vrai ; `partial` : article de la config en domaine public)."""
    basis = sheet.get("pd_basis", "")
    if sheet.get("excluded_reason"):
        return Decision.deny, f"volume exclu : {sheet['excluded_reason']}"
    status = str(sheet.get("pd_status")).lower()
    if status in ("true", "yes"):
        return Decision.allow, basis
    if status == "partial":
        art = cfg.article or {}
        ok = any(
            a.get("pd") in (True, "true", "yes") and art.get("author") in a.get("author", "")
            for a in sheet.get("articles", [])
        )
        if ok:
            return Decision.allow, f"article {art.get('author')} seulement : {basis}"
    return Decision.unknown, basis


def rights_for(cfg: CatalogueConfig, sheet: dict, checked_at: datetime):
    """Texte : selon la fiche (`unknown` ne devient jamais `allow`). Images de pages Gallica :
    affichage pilote `allow`, réutilisation `conditional`."""
    decision, basis = text_rights(cfg, sheet)
    ev = sheet.get("url", GALLICA_CONDITIONS)
    out = [
        RightsDecision(
            asset="text",
            action=a,
            decision=decision,
            basis=basis,
            evidence_url=ev,
            checked_at=checked_at,
        )
        for a in TEXT_ACTIONS
    ]
    out.append(
        RightsDecision(
            asset="images",
            action="display_pilot",
            decision=Decision.allow,
            basis="affichage de recherche d'images de pages Gallica (pilote)",
            evidence_url=GALLICA_CONDITIONS,
            checked_at=checked_at,
        )
    )
    out += [
        RightsDecision(
            asset="images",
            action=a,
            decision=Decision.conditional,
            basis="conditions d'utilisation de Gallica : réutilisation non commerciale, "
            "mention de la source",
            evidence_url=GALLICA_CONDITIONS,
            checked_at=checked_at,
        )
        for a in IMAGE_REUSE_ACTIONS
    ]
    return out


# --- construction -----------------------------------------------------------------------------


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


@dataclass
class PageData:
    view: int
    label: str | None
    asset: SourceAsset
    page: AltoPage
    route: str  # alto | textebrut
    text_index: int | None
    alignment: str


def _asset(f, media: str) -> SourceAsset:
    return SourceAsset(
        id=f.sha256[:12],
        url=f.url,
        sha256=f.sha256,
        captured_at=datetime.fromisoformat(f.captured_at),
        media_type=media,
        local_path=str(f.path),
    )


def toc_article_pages(toc: bytes, art: dict, labels: list[tuple[str, int]]) -> list[int]:
    """Vues de l'article (TOC) : de sa page de début à la page précédant l'entrée suivante."""
    root = etree.fromstring(toc)
    rows = []
    for row in root.iter("row"):
        segs = [(s.text or "").strip() for s in row.iter("seg")]
        xr = [(x.text or "").strip() for x in row.iter("xref")]
        if len(segs) >= 2 and xr and xr[0].isdigit():
            rows.append((segs[0], segs[1], int(xr[0])))
    mine = [r for r in rows if art["author"].lower() in r[0].lower() and art["title_match"] in r[1]]
    if len(mine) != 1:
        raise ValueError(f"article introuvable ou ambigu dans la TOC : {len(mine)} entrées")
    start = mine[0][2]
    later = sorted(p for _, _, p in rows if p > start)
    end = (later[0] - 1) if later else start
    lab2v = {int(lab): v for lab, v in labels if lab.isdigit()}
    missing = [p for p in range(start, end + 1) if p not in lab2v]
    if missing:
        raise ValueError(f"pages imprimées sans vue : {missing}")
    return [lab2v[p] for p in range(start, end + 1)]


_ROLE = re.compile(r"(?i)\b(experts?|commissaires?[- ]priseurs?)\b")
_PERSON = re.compile(r"\b(?:M\.|MM\.|Mes|Me|M e|M|Mme)\s+[A-ZÉÈ][\wÉÈ.'’-]+")  # noqa: RUF001


def title_page_flag(pages_text: list[str]) -> str | None:
    """Contrôle de la page de titre (catalogues de vente) : un expert ou commissaire-priseur
    *nommé* (titre de civilité + nom) rend les droits indéterminés ; le seul intitulé de rôle
    (« EXPERTS » sans personne) ne déclenche rien."""
    head = "\n".join(pages_text[:4])
    for m in _ROLE.finditer(head):
        p = _PERSON.search(head[m.end() : m.end() + 250])
        if p:
            return f"page de titre : {m.group(0)} nommé « {p.group(0)[:60]} » (auteur à identifier)"
    return None


def build_volume(
    cfg: CatalogueConfig,
    client: GallicaClient,
    out: Path,
    root: Path = Path("."),
    ref_index=None,
    log=print,
) -> dict:
    t0 = datetime.now(UTC)
    ark = cfg.ark
    notes: list[str] = []
    # droits d'abord : aucun téléchargement si le texte n'est pas utilisable
    sheet = _sheet(cfg, root)
    decision, why = text_rights(cfg, sheet)
    if decision != Decision.allow:
        raise RightsRefused(
            f"{cfg.id} : droits du texte {decision.value} ({why}) ; rien téléchargé"
        )
    # a. structure
    oai = client.oai(ark)
    pag = client.pagination(ark)
    labels = parse_pagination(pag.body)
    has_toc = b"<hasToc>true" in pag.body
    toc = client.toc(ark) if has_toc else None
    client.manifest(ark)
    tb = client.texte_brut(ark)
    text_pages = split_textebrut(tb.body)
    offsets = estimate_offsets(text_pages, labels)
    label_of = {v: (lab or None) for lab, v in labels}
    n_views = len(labels)
    tflag = title_page_flag(text_pages) if cfg.type == "sale_catalogue" else None
    if tflag:  # avant tout ALTO
        raise RightsRefused(f"{cfg.id} : {tflag} ; ALTO non téléchargé")

    # repérage des pages utiles
    plan: list[tuple[int, int | None]] = []  # (vue estimée, indice texte brut)
    if cfg.pages_mode == "toc_article":
        if toc is None or toc.body is None:
            raise ValueError("TOC absente : pages de l'article indéterminées")
        views = toc_article_pages(toc.body, cfg.article, labels)
        inv = {i + offsets[i - 1]: i for i in range(1, len(text_pages) + 1)}
        plan = [(v, inv.get(v)) for v in views]
    else:
        assert cfg.segmentation is not None
        tp = [page_from_text(t) for t in text_pages]
        cands = list(_candidates(tp, cfg.segmentation))
        st = accepted_starts(cands, cfg.segmentation.max_gap, cfg.segmentation.first_max)
        if st:
            lo, hi = st[0][0], st[-1][0]
            plan = [(min(max(i + 1 + offsets[i], 1), n_views), i + 1) for i in range(lo, hi + 1)]
    total_useful = len(plan)
    truncated = total_useful > cfg.max_pages
    if truncated:
        notes.append(f"{total_useful} pages utiles repérées, {cfg.max_pages} premières traitées")

    # b. ALTO des pages utiles ; la vue est vérifiée contre le texte brut (inverse : on cherche
    #    quelle page du texte brut correspond à l'ALTO reçu)
    pages, acq = _acquire(
        cfg, client, plan, text_pages, label_of, n_views, tb, auto=cfg.pages_mode == "auto"
    )
    notes += acq.pop("notes")
    alto_404, alto_ok, alto_attempts = acq["alto_404"], acq["alto_ok"], acq["alto_attempts"]
    misaligned = acq["misaligned"]
    pages.sort(key=lambda p: p.view)
    return _assemble(
        cfg,
        client,
        out,
        sheet,
        pages,
        oai.body,
        t0,
        notes,
        ref_index,
        {
            "useful_pages": total_useful,
            "alto_attempts": alto_attempts,
            "alto_ok": alto_ok,
            "alto_404": alto_404,
            "misaligned_first_try": misaligned,
            "alto_errors": acq["alto_errors"],
            "truncated": truncated,
            "text_pages": len(text_pages),
            "views": n_views,
        },
    )


MIN_VERIFY_CHARS = 30
MATCH_RATIO = 80
MAX_TRIES_PER_PAGE = 3


def match_text_index(
    alto_text: str,
    text_pages: list[str],
    center: int,
    radius: int = 4,
    min_ratio: float = MATCH_RATIO,
):
    """Indice (1-based) de la page du texte brut qui correspond à l'ALTO, proche de `center`."""
    a = _norm(alto_text)[:500]
    best = None
    for j in range(max(1, center - radius), min(len(text_pages), center + radius) + 1):
        r = fuzz.ratio(a, _norm(text_pages[j - 1])[:500])
        key = (r, -abs(j - center))
        if r >= min_ratio and (best is None or key > best[0]):
            best = (key, j)
    return best[1] if best else None


def _acquire(cfg, client, plan, text_pages, label_of, n_views, tb, auto):
    """Télécharge l'ALTO des pages utiles. Pages sans texte (planches) conservées : elles
    portent des figures ; leur vue n'est alors qu'estimée. Plafond : `max_pages` pages et
    1,5 fois ce nombre de requêtes ALTO."""
    pages: list[PageData] = []
    used: set[int] = set()
    notes: list[str] = []
    c = {"alto_attempts": 0, "alto_ok": 0, "alto_404": 0, "misaligned": 0, "alto_errors": 0}
    consecutive_errors = 0
    max_req = int(cfg.max_pages * 1.5)
    dead = False
    stopped = None
    off = None  # décalage vue - indice texte brut, appris au fil des pages
    done_upto = 0

    def add_text_page(v, ti):
        if ti and v not in used and 1 <= v <= n_views:
            used.add(v)
            pg = page_from_text(text_pages[ti - 1])
            pages.append(
                PageData(
                    v, label_of.get(v), _asset(tb, "text/plain"), pg, "textebrut", ti, "estimated"
                )
            )

    for v0, ti in plan:
        if len(pages) >= cfg.max_pages or c["alto_attempts"] >= max_req or stopped:
            break
        if auto and ti and ti <= done_upto:
            continue
        if off is None:
            off = v0 - (ti or 0)
        v = (ti + off) if (auto and ti) else v0
        tries = 0
        while tries < MAX_TRIES_PER_PAGE and 1 <= v <= n_views:
            tries += 1
            if dead:
                add_text_page(v, ti)
                break
            if v in used:
                v += 1
                continue
            if c["alto_attempts"] >= max_req or len(pages) >= cfg.max_pages:
                break
            c["alto_attempts"] += 1
            try:
                f = client.alto(cfg.ark, v)
            except GallicaStop as e:
                stopped = str(e)
                break
            except GallicaHTTPError as e:  # échec persistant après la relance unique : page sautée
                c["alto_errors"] += 1
                consecutive_errors += 1
                notes.append(f"vue {v} : {e}")
                if consecutive_errors >= 5:
                    stopped = "5 erreurs consécutives : service indisponible, arrêt"
                break
            consecutive_errors = 0
            if f.status != 200:
                c["alto_404"] += 1
                if c["alto_404"] >= 3 and c["alto_ok"] == 0:
                    dead = True
                    notes.append("ALTO indisponible (404 répétés) : repli texteBrut sans géométrie")
                add_text_page(v, ti)
                break
            pg = parse_alto(f.body)
            c["alto_ok"] += 1
            if not auto:  # article : vues données par la TOC, aucune vérification utile
                used.add(v)
                pages.append(
                    PageData(
                        v,
                        label_of.get(v),
                        _asset(f, "application/alto+xml"),
                        pg,
                        "alto",
                        ti,
                        "verified",
                    )
                )
                break
            if len(pg.text) < MIN_VERIFY_CHARS:  # planche : texte absent ou trop court
                used.add(v)
                pages.append(
                    PageData(
                        v,
                        label_of.get(v),
                        _asset(f, "application/alto+xml"),
                        pg,
                        "alto",
                        None,
                        "estimated",
                    )
                )
                v += 1  # la planche occupe une vue sans page de texte brut
                off += 1
                continue
            j = match_text_index(pg.text, text_pages, ti)
            recalibrated = False
            if j is None:  # décalage estimé faux : recherche globale (exigence plus forte)
                j = match_text_index(pg.text, text_pages, ti, len(text_pages), 90)
                recalibrated = j is not None
            if j is None:
                c["misaligned"] += 1
                v += 1
                continue
            off = v - j
            done_upto = max(done_upto, j)
            used.add(v)
            pages.append(
                PageData(
                    v, label_of.get(v), _asset(f, "application/alto+xml"), pg, "alto", j, "verified"
                )
            )
            if recalibrated and j < ti:  # page antérieure au plan : réessayer avec le bon décalage
                v = ti + off
                continue
            break
    if stopped:
        notes.append(f"ARRÊT : {stopped}")
    return pages, {**c, "notes": notes}


def _page_ref(pd: PageData, lines: list[Line]) -> PageRef:
    geo = pd.route == "alto"
    return PageRef(
        view=pd.view,
        page_label=pd.label,
        bbox=union([ln.bbox for ln in lines]) if geo else None,
        source_bbox=union([ln.src_bbox for ln in lines]) if geo else None,
        source_coordinate_system=pd.page.coordinate_system if geo else None,
        alignment=pd.alignment,  # type: ignore[arg-type]
    )


def _oai_meta(xml: bytes) -> dict:
    root = etree.fromstring(xml)
    ns = "{http://purl.org/dc/elements/1.1/}"
    g = lambda k: [e.text.strip() for e in root.iter(ns + k) if e.text]  # noqa: E731
    return {k: g(k) for k in ("title", "creator", "publisher", "date", "rights")}


def _assemble(cfg, client, out, sheet, pages, oai_xml, t0, notes, ref_index, counts) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    run = Run(
        id="run_" + t0.strftime("%Y%m%dT%H%M%S"),
        code_version=_git_version(),
        params={
            "catalogue": cfg.id,
            "ark": cfg.ark,
            "rule": "E1 notice_structure",
            "text_fidelity": "ocr_raw",
            "max_pages": cfg.max_pages,
        },
        started_at=t0,
    )
    rights = rights_for(cfg, sheet, t0)
    spans: dict[str, Span] = {}
    artworks: list[Artwork] = []
    links: list[Link] = []
    figures: list[Figure] = []
    notice_texts: dict[int, str] = {}
    art_by_number: dict[int, Artwork] = {}
    pdata = [p.page for p in pages]
    notices_all: list[Notice] = []

    def mk_span(pi: int, lines: list[Line], block_idx: int, para_idx: int, section: str) -> Span:
        pd = pages[pi]
        start, end = lines[0].start, lines[-1].end
        text = pd.page.text[start:end]
        assert text, "span vide"
        sid = "spn_" + _sha(f"{pd.asset.id}|{start}|{end}|{text}")[:12]
        raw = "\n".join(x.raw_text or x.text for x in lines)
        wcs = [x.wc for x in lines if x.wc is not None]
        wc = round(sum(wcs) / len(wcs), 3) if wcs else None
        sp = Span(
            id=sid,
            asset_id=pd.asset.id,
            section_label=section,
            paragraph_index=para_idx,
            char_start=start,
            char_end=end,
            text=text,
            text_fidelity="ocr_raw",
            page_refs=[_page_ref(pd, lines)],
            raw_text=raw if raw != text else None,
            normalizations=sorted({n for x in lines for n in x.normalizations}),
            quality_flag=(
                None
                if any(rx.search(text) for rx in cfg.quality_exempt)
                else quality_flag(text, wc, cfg.min_letter_share, cfg.min_wc)
            ),
            ocr_confidence=wc,
        )
        spans[sid] = sp
        return sp

    if cfg.segmentation is not None:
        notices = segment(pdata, cfg.segmentation)
        notices_all = notices
        for nt in notices:
            local_id = f"{cfg.id}#{nt.number}"
            art = Artwork(
                id="loc_" + _sha(local_id)[:12],
                artwork_local_id=local_id,
                local_label=nt.label,
                artist_heading=nt.artist_heading,
                catalogue_number=str(nt.number),
                title=nt.label,
                flags=[*nt.flags, *(["ocr_number_repaired"] if nt.ocr_digit_fix else [])],
            )
            if art.id in {a.id for a in artworks}:
                continue
            texts = []
            for para, (pi, bi, l0, l1) in enumerate(nt.runs):
                lines = pages[pi].page.blocks[bi].lines[l0 : l1 + 1]
                sp = mk_span(pi, lines, bi, para, f"notice {nt.number}")
                texts.append(sp.text)
                if sp.quality_flag:  # conservé, jamais lié
                    continue
                uncertain = "segmentation_uncertain" in nt.flags
                links.append(
                    Link(
                        id="lnk_" + _sha(f"{art.id}|{sp.id}|notice_structure")[:12],
                        artwork_id=art.id,
                        span_id=sp.id,
                        role=PassageFunction.unclassified,
                        evidence=[
                            Evidence(
                                mechanism="notice_structure",
                                quoted_heading=nt.label,
                                explanation=(
                                    f"E1 : paragraphe {para + 1} compris entre le début de la "
                                    f"notice n° {nt.number} (« {nt.label} », vue {pages[pi].view}) "
                                    "et le début de la suivante ; rattachement par la structure "
                                    "de notice, non validé."
                                    + (
                                        " NON RÉSOLU : numéros introuvables ensuite "
                                        f"({_fmt_missing(nt.missing_after)}), le passage peut "
                                        "contenir des notices absorbées (segmentation_uncertain)."
                                        if uncertain
                                        else ""
                                    )
                                ),
                            )
                        ],
                        status=LinkStatus.unresolved if uncertain else LinkStatus.machine_proposed,
                        rights=rights,
                        run_id=run.id,
                    )
                )
            notice_texts[nt.number] = "\n".join(texts)
            artworks.append(art)
            art_by_number[nt.number] = art
        # e. résolution externe
        _resolve_all(cfg, artworks, notice_texts, ref_index)
    else:  # article : un passage par bloc de texte, aucune notice, aucun lien (abstention)
        for pi, pd in enumerate(pages):
            for bi, b in enumerate(pd.page.blocks):
                mk_span(pi, b.lines, bi, bi, "article")

    # d. figures : doublons écartés ; une légende pour une seule figure ; aire minimale
    n_cap = 0
    for pi, pd in enumerate(pages):
        if pd.route != "alto":
            continue
        ills = dedupe_illustrations(pd.page.illustrations)
        assigned = assign_captions(pd.page, ills, cfg.segmentation, cfg.figure_min_area)
        for k, il in enumerate(ills):
            fid = "fig_" + _sha(f"{cfg.ark}|{pd.view}|{il.bbox}")[:12]
            fig = Figure(
                id=fid,
                view=pd.view,
                bbox=il.bbox,
                image_url=iiif_region_url(cfg.ark, pd.view, il.bbox, 800),
                image_rights=[r for r in rights if r.asset == "images"],
            )
            cap = assigned.get(k)
            art = art_by_number.get(cap[0]) if cap else None
            if cap and art:
                num, block = cap
                sp = mk_span(pi, block.lines, 0, 0, "légende de figure")
                fig.caption_span_id = sp.id
                fig.linked_artwork_local_id = art.artwork_local_id
                fig.link_evidence = [
                    Evidence(
                        mechanism="caption_number",
                        quoted_heading=block.lines[0].text,
                        explanation="légende voisine de la figure citant explicitement le "
                        f"numéro {num}, numéro d'une notice du volume ; non validé.",
                    )
                ]
                n_cap += 1
            figures.append(fig)

    # vérification des offsets (échec bruyant)
    for sp in spans.values():
        cands = [p for p in pages if p.asset.id == sp.asset_id]
        assert any(p.page.text[sp.char_start : sp.char_end] == sp.text for p in cands), sp.id

    assets = {p.asset.id: p.asset for p in pages}
    oai = _oai_meta(oai_xml)
    export.write_jsonl(out / "artworks.jsonl", artworks)
    export.write_jsonl(out / "spans.jsonl", list(spans.values()))
    export.write_jsonl(out / "links.jsonl", links)
    export.write_jsonl(out / "figures.jsonl", figures)
    export.write_jsonl(out / "assets.jsonl", list(assets.values()))
    export.write_jsonl(out / "runs.jsonl", [run])
    export.write_jsonl(out / "rights.jsonl", rights)
    (out / "pages.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "view": p.view,
                    "page_label": p.label,
                    "asset_id": p.asset.id,
                    "route": p.route,
                    "text_index": p.text_index,
                    "alignment": p.alignment,
                }
            )
            + "\n"
            for p in pages
        ),
        "utf-8",
    )
    export.dump_json(
        out / "surrogate.json",
        {
            "publication_url": f"https://gallica.bnf.fr/ark:/12148/{cfg.ark}",
            "title": (oai["title"] or [""])[0],
            "author": "; ".join(oai["creator"]),
            "publisher": "; ".join(oai["publisher"]),
            "date": oai["date"],
            "license_url": GALLICA_CONDITIONS,
            "captured_at": t0.isoformat(),
        },
    )
    nums = [int(a.catalogue_number) for a in artworks]
    missing = sum(len(nt.missing_after) for nt in notices_all)
    span_nums = (max(nums) - min(nums) + 1) if nums else 0
    n_res = sum(1 for a in artworks if a.resolution and a.resolution.status == "resolved")
    report = {
        "catalogue": cfg.id,
        "ark": cfg.ark,
        "pages_processed": len(pages),
        "pages_alto": sum(p.route == "alto" for p in pages),
        "notices": len(artworks),
        "spans": len(spans),
        "links": len(links),
        "figures": len(figures),
        "figures_linked": n_cap,
        "uncertain_notices": sum("segmentation_uncertain" in a.flags for a in artworks),
        "missing_numbers": missing,
        "gap_rate": round(missing / span_nums, 3) if span_nums else 0.0,
        "ocr_number_repaired": sum("ocr_number_repaired" in a.flags for a in artworks),
        "low_quality_spans": sum(1 for sp in spans.values() if sp.quality_flag),
        "spans_with_normalizations": sum(1 for sp in spans.values() if sp.normalizations),
        "resolved": n_res,
        "unresolved": len(artworks) - n_res,
        "notes": notes,
        **counts,
        "seconds": round((datetime.now(UTC) - t0).total_seconds(), 1),
        "client": client.stats.as_dict(),
    }
    export.dump_json(out / "report.json", report)
    return report


def _area(b) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _iou(a, b) -> float:
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    inter = max(0.0, iw) * max(0.0, ih)
    union_area = _area(a) + _area(b) - inter
    return inter / union_area if union_area > 0 else 0.0


def dedupe_illustrations(ills: list[Illustration], threshold: float = 0.9) -> list[Illustration]:
    """Écarte les boîtes quasi identiques (IoU >= seuil) d'une même page."""
    out: list[Illustration] = []
    for il in ills:
        if all(_iou(il.bbox, o.bbox) < threshold for o in out):
            out.append(il)
    return out


def assign_captions(
    page: AltoPage,
    ills: list[Illustration],
    seg: Segmentation | None,
    min_area: float,
    max_gap: float = 0.12,
) -> dict[int, tuple[int, Block]]:
    """Légendes (numéro explicite) -> figures, un pour un, du plus proche au plus éloigné ;
    une figure d'aire inférieure à `min_area` n'est jamais liée."""
    if seg is None or seg.caption_number is None:
        return {}
    caps = []
    for b in page.blocks:
        m = seg.caption_number.search("\n".join(x.text for x in b.lines[:2]))
        if m and len(b.lines) <= 4:
            caps.append((b, int(m.group("number"))))
    pairs = []
    for ci, (b, _) in enumerate(caps):
        for fi, il in enumerate(ills):
            if _area(il.bbox) < min_area:
                continue
            gap = max(b.bbox[1] - il.bbox[3], il.bbox[1] - b.bbox[3], 0.0)
            overlap = min(b.bbox[2], il.bbox[2]) - max(b.bbox[0], il.bbox[0])
            if gap <= max_gap and overlap > 0:
                pairs.append((gap, ci, fi))
    out: dict[int, tuple[int, Block]] = {}
    used_caps: set[int] = set()
    for _gap, ci, fi in sorted(pairs):
        if ci in used_caps or fi in out:
            continue
        used_caps.add(ci)
        out[fi] = (caps[ci][1], caps[ci][0])
    return out


def _fmt_missing(nums: list[int]) -> str:
    return ", ".join(map(str, nums[:6])) + (" …" if len(nums) > 6 else "")


def _resolve_all(cfg, artworks: list[Artwork], notice_texts: dict[int, str], ref_index) -> None:
    from lesternowak.referentials import LocalAttrs, resolve

    for art in artworks:
        if not cfg.referential or ref_index is None:
            art.resolution = Resolution(
                status="unresolved",
                reason="aucun référentiel d'œuvres configuré pour cette source",
            )
            continue
        text = notice_texts.get(int(art.catalogue_number), "")
        artist = re.sub(r"\s*\.\s*\d*\s*$", "", art.artist_heading or "") or None
        res = resolve(LocalAttrs(artist=artist, dimensions_cm=local_dimensions_cm(text)), ref_index)
        art.resolution = Resolution(
            status=res.status,
            mechanism={"E0": "E0", "E2": "E2_composite"}.get(res.evidence),
            signals=[s.model_dump() for s in res.signals[:5]],
            candidates=res.candidates[:10],
            reason=res.reason
            + (
                f" (référentiel {cfg.referential} : échantillon partiel, ancien numéro non inféré)"
                if res.status == "unresolved"
                else ""
            ),
        )
        if res.status == "resolved":
            art.external_ids = [{"scheme": cfg.referential, "ref_id": res.ref_id}]


def _git_version() -> str:
    from lesternowak.getty_quire import git_version

    return git_version()
