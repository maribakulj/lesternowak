"""Voie `ia_djvu` : volume Internet Archive (djvu.xml, coordonnées des mots) -> slice.

Tout ce qui dépend du volume vient de `config/catalogues/<id>.yaml` (expressions régulières de
segmentation, plage de pages, référentiel, fiche de droits). Les passages sont des extraits exacts
de l'OCR brut (`ocr_raw`) ; aucun texte n'est produit par un modèle. Les catalogues du Met (1922,
1926) n'ont pas de numéro de notice : une notice va de son titre à sa ligne de crédit
(« Gift of …, 1906. »), l'œuvre locale est numérotée par rang dans le volume.

Réseau : `archive.org/download/<id>/<id>_djvu.xml` et `archive.org/metadata/<id>`, cache
`data/raw/ia/`, empreinte sha256, au plus 1 requête par seconde, User-Agent fixe, `Retry-After`
respecté une fois ; un 403 est un statut (arrêt consigné), jamais un obstacle à contourner.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml
from lxml import etree

from lesternowak import export
from lesternowak.alto import AltoPage, Block, Line, Word, normalize_bbox, union
from lesternowak.gallica import Fetched, Opener, urllib_opener
from lesternowak.models import (
    ArtworkRef,
    Decision,
    Evidence,
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

IA_BASE = "https://archive.org"
USER_AGENT = "lesternowak/0.0.1 (recherche; client Internet Archive)"
MIN_INTERVAL_S = 1.0
IA_METADATA_KEYS = (
    "licenseurl",
    "possible-copyright-status",
    "rights",
    "copyright-region",
    "date",
    "publisher",
    "sponsor",
    "contributor",
    "scandate",
    "collection",
)
TEXT_ACTIONS = ("tdm", "publish_text", "redistribute_text", "remote_llm", "training")
IMAGE_REUSE_ACTIONS = ("publish_image", "redistribute_image", "tdm", "remote_llm", "training")
MET_OA = "https://www.metmuseum.org/about-the-met/policies-and-documents/open-access"


class IAStop(RuntimeError):
    """Arrêt volontaire après un 403/429 persistant."""


class IAHTTPError(RuntimeError):
    def __init__(self, status: int, url: str):
        super().__init__(f"HTTP {status} sur {url}")
        self.status = status
        self.url = url


# --- client ------------------------------------------------------------------------------------


class IAClient:
    def __init__(
        self,
        cache_root: Path = Path("data/raw/ia"),
        opener: Opener = urllib_opener,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.cache_root, self.opener, self.clock, self.sleep, self.now = (
            cache_root,
            opener,
            clock,
            sleep,
            now,
        )
        self.last = -1e9
        self.requests = 0
        self.stop_file = cache_root / "_stop.json"

    def _read_cache(self, p: Path) -> Fetched | None:
        meta_p = p.with_name(p.name + ".meta.json")
        if not meta_p.exists() or not p.exists():
            return None
        meta = json.loads(meta_p.read_text("utf-8"))
        body = p.read_bytes()
        if hashlib.sha256(body).hexdigest() != meta["sha256"]:
            raise RuntimeError(f"cache corrompu : {p}")
        return Fetched(meta["url"], 200, body, meta["sha256"], meta["captured_at"], p, True)

    def _get(self, url: str) -> tuple[int, dict[str, str], bytes]:
        wait = MIN_INTERVAL_S - (self.clock() - self.last)
        if wait > 0:
            self.sleep(wait)
        self.last = self.clock()
        self.requests += 1
        try:
            return self.opener(url, {"User-Agent": USER_AGENT, "Accept": "*/*"})
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            return 0, {}, str(e).encode()[:200]

    def fetch(self, identifier: str, relname: str, url: str) -> Fetched:
        p = self.cache_root / identifier / relname
        hit = self._read_cache(p)
        if hit is not None:
            return hit
        if self.stop_file.exists():
            raise IAStop(f"{self.stop_file} présent : arrêt précédent après 403/429")
        status, headers, body = self._get(url)
        if status in (429, 503):
            ra = {k.lower(): v for k, v in headers.items()}.get("retry-after", "")
            if ra.isdigit() and int(ra) <= 120:
                self.sleep(float(ra))
                status, headers, body = self._get(url)
        if status in (403, 429):
            self.cache_root.mkdir(parents=True, exist_ok=True)
            self.stop_file.write_text(
                json.dumps({"status": status, "url": url, "at": self.now().isoformat()}), "utf-8"
            )
            raise IAStop(f"{status} sur {url} : arrêt, non contourné")
        if status != 200:
            raise IAHTTPError(status, url)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        captured = self.now().isoformat(timespec="seconds")
        p.with_name(p.name + ".meta.json").write_text(
            json.dumps({"url": url, "status": 200, "sha256": sha, "captured_at": captured}), "utf-8"
        )
        return Fetched(url, 200, body, sha, captured, p)

    def djvu(self, identifier: str) -> Fetched:
        return self.fetch(
            identifier, "djvu.xml", f"{IA_BASE}/download/{identifier}/{identifier}_djvu.xml"
        )

    def metadata(self, identifier: str) -> Fetched:
        return self.fetch(identifier, "metadata.json", f"{IA_BASE}/metadata/{identifier}")


# --- lecture de djvu.xml -----------------------------------------------------------------------


def _layout(blocks: list[Block]) -> str:
    """Texte canonique d'une page : lignes séparées par « \\n », blocs par « \\n\\n »."""
    out: list[str] = []
    pos = 0
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
    return "".join(out)


def _coords(s: str | None) -> tuple[float, float, float, float] | None:
    """`coords="x0,y1,x1,y0"` (origine en haut à gauche) -> (HPOS, VPOS, WIDTH, HEIGHT)."""
    try:
        x0, ya, x1, yb = (float(v) for v in (s or "").split(","))
    except ValueError:
        return None
    return (min(x0, x1), min(ya, yb), abs(x1 - x0), abs(ya - yb))


def parse_djvu(data: bytes) -> list[AltoPage]:
    """Une `AltoPage` par `OBJECT` (un paragraphe = un bloc ; coordonnées normalisées 0-1)."""
    root = etree.fromstring(
        data, parser=etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True)
    )
    pages: list[AltoPage] = []
    for obj in root.iter("OBJECT"):
        pw, ph = float(obj.get("width") or 0), float(obj.get("height") or 0)
        if pw <= 0 or ph <= 0:
            raise ValueError("page djvu.xml sans dimensions")
        blocks: list[Block] = []
        for pi, para in enumerate(obj.iter("PARAGRAPH")):
            lines: list[Line] = []
            for ln in para.iter("LINE"):
                words: list[Word] = []
                for w in ln.iter("WORD"):
                    g = _coords(w.get("coords"))
                    text = (w.text or "").strip()
                    if g and text:
                        words.append(Word(text, normalize_bbox(*g, pw, ph)))
                if words:
                    bb = union([w.bbox for w in words])
                    src = (
                        bb[0] * pw,
                        bb[1] * ph,
                        (bb[2] - bb[0]) * pw,
                        (bb[3] - bb[1]) * ph,
                    )
                    lines.append(Line(" ".join(w.text for w in words), bb, src, words=words))
            if lines:
                blocks.append(Block(f"P{pi}", union([ln.bbox for ln in lines]), lines))
        pages.append(AltoPage(pw, ph, "djvu_pixel", blocks, [], _layout(blocks)))
    return pages


# --- dimensions en pouces (OCR dégradé) --------------------------------------------------------

IN_TO_CM = 2.54
_TOKEN = r"(?:\d{1,3}\s\d{1,2}/\d{1,2}|[0-9A-Za-z%$¢}{;|!,.]{1,9}?)"
DIMS_RE = re.compile(
    rf"(?P<dims>\bH\.*\s*(?P<h>{_TOKEN})\s*[i1l]n\b\.?\s*[,;]?\s*W\.*\s*(?P<w>{_TOKEN})\s*[i1l]n\b)"
)
_FRAC = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875}


def inch_token(tok: str) -> tuple[list[int], float | None]:
    """Jeton OCR d'une mesure en pouces -> (parties entières possibles, valeur exacte ou None).

    L'OCR écrase les fractions (« 38⅜ » devient « 383 », « 10½ » devient « 102 ») : le jeton peut
    donc être l'entier seul ou l'entier suivi d'un ou deux chiffres de fraction. Valeur exacte
    seulement pour un entier propre ou « N a/b » lisible ; sinon aucune valeur n'est inventée.
    """
    t = tok.strip(" .,;")
    m = re.fullmatch(r"(\d{1,3})\s+(\d{1,2})/(\d{1,2})", t)
    if m and int(m.group(3)):
        v = int(m.group(1)) + int(m.group(2)) / int(m.group(3))
        return [int(m.group(1))], v
    m = re.fullmatch(r"(\d{1,3})([½¼¾⅛⅜⅝⅞])", t)
    if m:
        return [int(m.group(1))], int(m.group(1)) + _FRAC[m.group(2)]
    m = re.match(r"\d+", t)
    if not m:
        return [], None
    digits = m.group(0)
    opts: list[int] = []
    for k, min_len in ((0, 1), (1, 2), (2, 4), (3, 5)):
        whole = int(digits[: len(digits) - k]) if len(digits) >= min_len else 0
        if 1 <= whole <= 200 and whole not in opts:
            opts.append(whole)
    return opts, None


def parse_dims_line(text: str) -> dict | None:
    """« H. 38⅜ in. W. 12 in. » -> options de pouces par axe ; cm seulement si non ambigu."""
    m = DIMS_RE.search(text)
    if not m:
        return None
    ho, hv = inch_token(m.group("h"))
    wo, wv = inch_token(m.group("w"))
    if not ho or not wo:
        return None
    return {
        "h_in_options": ho,
        "w_in_options": wo,
        "h_cm": round(hv * IN_TO_CM, 1) if hv is not None else None,
        "w_cm": round(wv * IN_TO_CM, 1) if wv is not None else None,
        "span": (m.start("dims"), m.end("dims")),
    }


# --- configuration -----------------------------------------------------------------------------


@dataclass
class IaSegmentation:
    skip_lines: list[re.Pattern]
    artist_header: re.Pattern
    artist_confirm: re.Pattern
    artist_end: re.Pattern
    title: re.Pattern
    credit_start: re.Pattern
    credit_year: re.Pattern
    credit_max_lines: int = 3
    bio_max_blocks: int = 2
    min_chars: int = 25


@dataclass
class IaConfig:
    id: str
    identifier: str
    type: str
    language: str
    rights_sheet: str
    rights_id: str
    referential: str | None
    first_page: int
    last_page: int
    segmentation: IaSegmentation
    raw: dict


def load_ia_config(path: Path) -> IaConfig:
    d = yaml.safe_load(path.read_text("utf-8"))
    if d.get("source") != "internet_archive" or d.get("route") != "ia_djvu":
        raise ValueError(f"{path} : seule la voie ia_djvu est gérée ici")
    sg = d["segmentation"]
    rx = lambda k: re.compile(sg[k])  # noqa: E731
    seg = IaSegmentation(
        skip_lines=[re.compile(x) for x in sg.get("skip_lines", [])],
        artist_header=rx("artist_header"),
        artist_confirm=rx("artist_confirm"),
        artist_end=rx("artist_end"),
        title=rx("title"),
        credit_start=rx("credit_start"),
        credit_year=rx("credit_year"),
        credit_max_lines=int(sg.get("credit_max_lines", 3)),
        bio_max_blocks=int(sg.get("bio_max_blocks", 2)),
        min_chars=int(sg.get("min_chars", 25)),
    )
    if "title" not in seg.title.groupindex:
        raise ValueError(f"{path} : segmentation.title doit définir le groupe « title »")
    pg = d.get("pages") or {}
    return IaConfig(
        id=d["id"],
        identifier=d["identifier"],
        type=d["type"],
        language=d.get("language", ""),
        rights_sheet=d["rights_sheet"],
        rights_id=d.get("rights_id", d["id"]),
        referential=d.get("referential"),
        first_page=int(pg.get("first", 1)),
        last_page=int(pg.get("last", 10**6)),
        segmentation=seg,
        raw=d,
    )


# --- segmentation en notices -------------------------------------------------------------------


@dataclass
class Heading:
    text: str  # ligne d'en-tête, extrait exact
    name: str  # partie nom (avant la nationalité), extrait exact
    page: int
    start: int
    end: int


@dataclass
class IaNotice:
    ordinal: int
    artist: Heading | None
    lines: list[tuple[int, int, Line]] = field(default_factory=list)  # page, bloc, ligne
    credit: list[tuple[int, int, Line]] = field(default_factory=list)
    credit_open: bool = False

    def chars(self) -> int:
        return sum(len(ln.text) for _, _, ln in self.lines)


def _skip(seg: IaSegmentation, text: str) -> bool:
    return any(p.search(text) for p in seg.skip_lines)


def segment_ia(pages: list[AltoPage], seg: IaSegmentation, first: int, last: int) -> list[IaNotice]:
    out: list[IaNotice] = []
    cur: IaNotice | None = None
    artist: Heading | None = None
    mode, bio_n = "between", 0

    def close() -> None:
        nonlocal cur
        if cur is not None:
            cur.credit_open = False
            if cur.chars() >= seg.min_chars:
                out.append(cur)
        cur = None

    for pi in range(first - 1, min(last, len(pages))):
        for bi, blk in enumerate(pages[pi].blocks):
            if cur is not None:
                cur.credit_open = False  # un crédit tient dans un seul paragraphe
            lines = blk.lines
            if all(_skip(seg, ln.text) for ln in lines):
                continue
            head = lines[0].text
            two = " ".join(ln.text for ln in lines[:2])
            if seg.artist_header.match(head) and seg.artist_confirm.search(two):
                close()
                cut = seg.artist_end.search(head)
                name_end = cut.start() if cut else len(head)
                artist = Heading(
                    head, head[:name_end], pi, lines[0].start, lines[0].start + name_end
                )
                mode, bio_n = "bio", 0
                continue
            if mode == "bio":
                if seg.title.match(head) or bio_n >= seg.bio_max_blocks:
                    mode = "between"
                else:
                    bio_n += 1
                    continue
            for ln in lines:
                if _skip(seg, ln.text):
                    if cur is not None:
                        cur.lines.append((pi, bi, ln))
                    continue
                if cur is None:
                    if seg.credit_start.match(ln.text) and out and out[-1].credit:
                        continue  # second crédit orphelin : non rattaché
                    cur = IaNotice(len(out) + 1, artist)
                cur.lines.append((pi, bi, ln))
                if cur.credit_open:
                    cur.credit.append((pi, bi, ln))
                    if seg.credit_year.search(ln.text) or len(cur.credit) >= seg.credit_max_lines:
                        close()
                elif seg.credit_start.match(ln.text):
                    cur.credit = [(pi, bi, ln)]
                    if seg.credit_year.search(ln.text):
                        close()
                    else:
                        cur.credit_open = True
    close()
    for i, n in enumerate(out, 1):
        n.ordinal = i
    return out


# --- attributs locaux, avec offsets ------------------------------------------------------------


def clean_join(lines: list[str]) -> str:
    """Recolle les coupures de fin de ligne (« Hearn- » + « Fund ») ; texte sinon inchangé."""
    s = ""
    for t in lines:
        s = s[:-1] + t if s.endswith("-") and t[:1].islower() else (s + " " + t if s else t)
    return s.strip()


def artist_value(heading: Heading) -> str | None:
    """« ZORN, ANnperRs » -> « ANnperRs ZORN » (comparaison insensible à la casse)."""
    if "," not in heading.name:
        return None
    sur, _, given = heading.name.partition(",")
    given = re.sub(r"[.;,]\s*$", "", given.strip()).strip()
    return f"{given} {sur.strip()}".strip() if given else sur.strip()


def extract_attrs(n: IaNotice, assets: dict[int, str], seg: IaSegmentation) -> list[dict]:
    """Attributs lus dans la notice ; `text == page.text[char_start:char_end]` (offsets de page)."""
    attrs: list[dict] = []

    def add(kind: str, pi: int, a: int, b: int, text: str, value) -> None:
        attrs.append(
            {
                "kind": kind,
                "asset_id": assets[pi],
                "char_start": a,
                "char_end": b,
                "text": text,
                "value": value,
            }
        )

    if n.artist is not None and n.artist.page in assets:
        h = n.artist
        add("artist", h.page, h.start, h.end, h.name, artist_value(h))
    if n.lines:
        pi, _, ln = n.lines[0]
        m = seg.title.match(ln.text)
        if m and len(m["title"]) >= 4:
            add(
                "title",
                pi,
                ln.start + m.start("title"),
                ln.start + m.end("title"),
                m["title"],
                m["title"],
            )
    for pi, _, ln in n.lines:
        d = parse_dims_line(ln.text)
        if d:
            a, b = d.pop("span")
            add("dimensions", pi, ln.start + a, ln.start + b, ln.text[a:b], d)
            break
    if n.credit:
        pi0 = n.credit[0][0]
        same = [ln for pi, _, ln in n.credit if pi == pi0]
        a, b = same[0].start, same[-1].end
        text = clean_join([ln.text for ln in same])
        ym = seg.credit_year.search(text)
        year = None
        if ym:
            y = re.search(r"\d{4}", ym.group(0))
            year = int(y.group(0)) if y else None
        add(
            "credit",
            pi0,
            a,
            b,
            "\n".join(ln.text for ln in same),
            {"credit_line": text, "year": year},
        )
    return attrs


# --- droits ------------------------------------------------------------------------------------


def _sheet(cfg: IaConfig, root: Path) -> dict:
    data = yaml.safe_load((root / cfg.rights_sheet).read_text("utf-8"))
    for r in data["volumes"] if isinstance(data, dict) else data:
        if r.get("id") == cfg.rights_id:
            return r
    raise KeyError(f"fiche de droits introuvable : {cfg.rights_id}")


def text_rights(cfg: IaConfig, sheet: dict, ia_meta: dict, at: datetime) -> list[RightsDecision]:
    """Texte : selon `pd_status` de la fiche ; `unknown` ne devient jamais `allow`. La mention IA
    (licenseurl, possible-copyright-status) est consignée dans la base de la décision."""
    status = str(sheet.get("pd_status")).lower()
    decision = Decision.allow if status in ("true", "yes") else Decision.unknown
    ia = {k: ia_meta.get(k) for k in ("licenseurl", "possible-copyright-status", "rights")}
    ia_note = (
        "métadonnées Internet Archive : "
        + (
            ", ".join(f"{k}={v}" for k, v in ia.items() if v)
            or "aucune mention de licence ni de statut"
        )
        + " (la décision vient de la fiche d'inventaire, non de l'IA)"
    )
    return [
        RightsDecision(
            asset="text",
            action=a,
            decision=decision,
            basis=f"{sheet.get('pd_basis', '')} ; {ia_note}",
            evidence_url=sheet.get("evidence_url") or f"{IA_BASE}/metadata/{cfg.identifier}",
            checked_at=at,
        )
        for a in TEXT_ACTIONS
    ]


def met_image_rights(ref: dict, at: datetime) -> list[RightsDecision]:
    """Image du référentiel Met : seulement si `image_license == cc0` (sinon rien d'autorisé)."""
    if ref.get("image_license") != "cc0":
        return [
            RightsDecision(
                asset="images",
                action="display_pilot",
                decision=Decision.unknown,
                basis="licence d'image du référentiel non cc0",
                evidence_url=ref.get("collection_url", ""),
                checked_at=at,
            )
        ]
    return [
        RightsDecision(
            asset="images",
            action=a,
            decision=Decision.allow,
            basis="Met Open Access, CC0 (champ image_license du référentiel local)",
            evidence_url=MET_OA,
            checked_at=at,
        )
        for a in ("display_pilot", *IMAGE_REUSE_ACTIONS)
    ]


# --- résolution --------------------------------------------------------------------------------


def _reason_category(reason: str) -> str:
    if "candidats restants" in reason:
        return "candidats multiples"
    if "artiste non concordant" in reason:
        return "artiste non concordant"
    if "aucun artiste local" in reason:
        return "artiste local absent"
    if "moins de 2" in reason:
        return "moins de 2 attributs concordants"
    return reason.split(" (")[0]


def resolve_notice(attrs: list[dict], refs) -> tuple[Resolution, str | None]:
    """E2 composite via `referentials.resolve` ; renvoie (résolution, catégorie de refus)."""
    from lesternowak.referentials import LocalAttrs, resolve

    by = {a["kind"]: a for a in attrs}
    dims = (by.get("dimensions") or {}).get("value")
    cred = (by.get("credit") or {}).get("value")
    if dims is None:
        return Resolution(
            status="unresolved", reason="[dimensions non lues] pas de ligne H./W. lisible"
        ), "dimensions non lues"
    if cred is None:
        return Resolution(
            status="unresolved", reason="[crédit non lu] pas de ligne de crédit"
        ), "crédit non lu"
    cm = (dims["h_cm"], dims["w_cm"]) if dims["h_cm"] and dims["w_cm"] else None
    local = LocalAttrs(
        artist=(by.get("artist") or {}).get("value"),
        credit_line=cred["credit_line"],
        accession_year=cred["year"],
        dimensions_cm=cm,
        dimension_inch_options=(tuple(dims["h_in_options"]), tuple(dims["w_in_options"])),
    )
    res = resolve(local, refs)
    cat = None if res.status == "resolved" else _reason_category(res.reason)
    return (
        Resolution(
            status=res.status,
            mechanism={"E0": "E0", "E2": "E2_composite"}.get(res.evidence),
            signals=[s.model_dump() for s in res.signals[:5]],
            candidates=res.candidates[:10],
            reason=res.reason if res.status == "resolved" else f"[{cat}] {res.reason}",
        ),
        cat,
    )


# --- assemblage --------------------------------------------------------------------------------


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def build_ia_volume(
    cfg: IaConfig,
    client: IAClient,
    out: Path,
    root: Path = Path("."),
    refs: list | None = None,
    log=print,
) -> dict:
    from lesternowak.getty_quire import git_version

    t0 = datetime.now(UTC)
    meta_f = client.metadata(cfg.identifier)
    djvu = client.djvu(cfg.identifier)
    assert djvu.body is not None and meta_f.body is not None
    ia_meta = json.loads(meta_f.body).get("metadata", {})
    pages = parse_djvu(djvu.body)
    seg = cfg.segmentation
    notices = segment_ia(pages, seg, cfg.first_page, cfg.last_page)
    sheet = _sheet(cfg, root)
    rights_text = text_rights(cfg, sheet, ia_meta, t0)
    run = Run(
        id="run_" + t0.strftime("%Y%m%dT%H%M%S"),
        code_version=git_version(),
        params={
            "catalogue": cfg.id,
            "source": "internet_archive",
            "route": "ia_djvu",
            "identifier": cfg.identifier,
            "djvu_sha256": djvu.sha256,
            "rule": "E1 notice_structure",
            "text_fidelity": "ocr_raw",
            "referential": cfg.referential,
        },
        started_at=t0,
    )

    used_pages = sorted(
        {pi for n in notices for pi, _, _ in n.lines} | {n.artist.page for n in notices if n.artist}
    )
    assets: dict[int, SourceAsset] = {}
    for pi in used_pages:
        txt = pages[pi].text
        assets[pi] = SourceAsset(
            id="ia_" + _sha(f"{cfg.identifier}|{pi + 1}|{txt}")[:12],
            url=f"{IA_BASE}/details/{cfg.identifier}/page/n{pi}/mode/1up",
            sha256=_sha(txt),
            captured_at=datetime.fromisoformat(djvu.captured_at),
            media_type="text/plain; charset=utf-8; source=djvu.xml (texte canonique de la page)",
            local_path=str(djvu.path),
        )
    asset_id = {pi: a.id for pi, a in assets.items()}
    ref_by_id = {r.ref_id: r for r in refs or []}

    spans: dict[str, Span] = {}
    artworks: list[ArtworkRef] = []
    links: list[Link] = []
    resolutions: list[dict] = []
    reasons: Counter[str] = Counter()
    notice_spans: dict[str, list[str]] = {}
    for n in notices:
        local_id = f"{cfg.id}#{n.ordinal}"
        attrs = extract_attrs(n, asset_id, seg)
        title = next((a["text"] for a in attrs if a["kind"] == "title"), None)
        art = ArtworkRef(
            id="loc_" + _sha(local_id)[:12],
            artwork_local_id=local_id,
            local_label=title or n.lines[0][2].text,
            artist_heading=n.artist.text if n.artist else None,
            title=title or n.lines[0][2].text,
            local_attributes=attrs,
        )
        if refs is None or not cfg.referential:
            art.resolution = Resolution(
                status="unresolved", reason="[sans référentiel] aucun référentiel chargé"
            )
            reasons["sans référentiel"] += 1
        else:
            art.resolution, cat = resolve_notice(attrs, refs)
            if cat:
                reasons[cat] += 1
        artworks.append(art)
        # un span par page (extrait contigu exact, sans paragraphes de repérage en tête ou en queue)
        by_page: dict[int, list[Line]] = {}
        for pi, _, ln in n.lines:
            by_page.setdefault(pi, []).append(ln)
        ids = []
        for para, (pi, lns) in enumerate(sorted(by_page.items())):
            lns = [ln for ln in lns if not any(p.search(ln.text) for p in seg.skip_lines)]
            if not lns:
                continue
            start, end = lns[0].start, lns[-1].end
            text = pages[pi].text[start:end]
            sid = "spn_" + _sha(f"{asset_id[pi]}|{start}|{end}|{text}")[:12]
            spans[sid] = Span(
                id=sid,
                asset_id=asset_id[pi],
                section_label=f"notice {n.ordinal}",
                paragraph_index=para,
                char_start=start,
                char_end=end,
                text=text,
                text_fidelity="ocr_raw",
                page_refs=[
                    PageRef(
                        view=pi + 1,
                        page_label=None,
                        bbox=union([ln.bbox for ln in lns]),
                        source_bbox=union([ln.src_bbox for ln in lns]),
                        source_coordinate_system=f"djvu_xml:pixel:{pages[pi].width:g}x{pages[pi].height:g}",
                    )
                ],
            )
            ids.append(sid)
        notice_spans[art.id] = ids

    # collisions : une même fiche de référentiel ne peut pas désigner deux notices
    claimed: dict[str, list[ArtworkRef]] = {}
    for a in artworks:
        if a.resolution and a.resolution.status == "resolved":
            claimed.setdefault(a.resolution.candidates[0], []).append(a)
    collisions = 0
    for ref_id, arts in claimed.items():
        if len(arts) > 1:
            collisions += 1
            for a in arts:
                a.resolution = Resolution(
                    status="unresolved",
                    candidates=[ref_id],
                    signals=a.resolution.signals if a.resolution else [],
                    reason=f"[fiche revendiquée par {len(arts)} notices] {ref_id}",
                )
                reasons["fiche revendiquée par plusieurs notices"] += 1
    for a in artworks:
        r = a.resolution
        if r and r.status == "resolved":
            ref = ref_by_id[r.candidates[0]]
            a.external_ids = [{"scheme": cfg.referential, "ref_id": ref.ref_id}]
            resolutions.append(
                {
                    "artwork_id": a.id,
                    "ref_id": ref.ref_id,
                    "mechanism": r.mechanism,
                    "signals": r.signals,
                    "title": ref.title,
                    "artist": ref.artist,
                    "accession_number": ref.accession_number,
                    "credit_line": ref.credit_line,
                    "collection_url": ref.collection_url,
                    "image_url": ref.image_url,
                    "image_license": ref.image_license,
                }
            )
    res_by_art = {r["artwork_id"]: r for r in resolutions}
    for a in artworks:
        rights = list(rights_text)
        if a.id in res_by_art:
            rights += met_image_rights(res_by_art[a.id], t0)
        for sid in notice_spans[a.id]:
            sp = spans[sid]
            first = a.local_label or ""
            links.append(
                Link(
                    id="lnk_" + _sha(f"{a.id}|{sid}|notice_structure")[:12],
                    artwork_id=a.id,
                    span_id=sid,
                    role=PassageFunction.unclassified,
                    evidence=[
                        Evidence(
                            mechanism="notice_structure",
                            quoted_heading=first,
                            explanation=(
                                f"E1 : passage de la notice n° {a.artwork_local_id.split('#')[-1]} "
                                f"(rang dans le volume ; « {first} »), entre le début de la "
                                "notice et sa ligne de crédit ; rattachement par la structure de "
                                "notice, non validé."
                            ),
                        )
                    ],
                    status=LinkStatus.machine_proposed,
                    rights=rights,
                    run_id=run.id,
                )
            )
    for sp in spans.values():
        pg = next(p for p, a in assets.items() if a.id == sp.asset_id)
        assert pages[pg].text[sp.char_start : sp.char_end] == sp.text, sp.id
    for a in artworks:
        for at in a.local_attributes:
            pg = next(p for p, x in assets.items() if x.id == at["asset_id"])
            assert pages[pg].text[at["char_start"] : at["char_end"]] == at["text"], at

    out.mkdir(parents=True, exist_ok=True)
    export.write_jsonl(out / "artworks.jsonl", artworks)
    export.write_jsonl(out / "spans.jsonl", list(spans.values()))
    export.write_jsonl(out / "links.jsonl", links)
    export.write_jsonl(out / "assets.jsonl", list(assets.values()))
    export.write_jsonl(out / "runs.jsonl", [run])
    export.write_jsonl(out / "rights.jsonl", rights_text)
    (out / "resolutions.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in resolutions), "utf-8"
    )
    ia_subset = {k: ia_meta.get(k) for k in IA_METADATA_KEYS}
    export.dump_json(
        out / "surrogate.json",
        {
            "publication_url": f"{IA_BASE}/details/{cfg.identifier}",
            "title": ia_meta.get("title", ""),
            "author": str(ia_meta.get("creator", "")),
            "publisher": str(ia_meta.get("publisher", "")),
            "date": ia_meta.get("date", ""),
            "license_url": ia_meta.get("licenseurl") or "",
            "ia_metadata": ia_subset,
            "metadata_sha256": meta_f.sha256,
            "djvu_sha256": djvu.sha256,
            "captured_at": djvu.captured_at,
        },
    )
    n_res = sum(1 for a in artworks if a.resolution and a.resolution.status == "resolved")
    cc0 = sum(1 for r in resolutions if r["image_license"] == "cc0" and r["image_url"])
    amb = sum(
        1
        for a in artworks
        if a.resolution
        and a.resolution.status == "unresolved"
        and a.resolution.reason.startswith("[candidats multiples]")
    )
    kinds = Counter(at["kind"] for a in artworks for at in a.local_attributes)
    report = {
        "catalogue": cfg.id,
        "identifier": cfg.identifier,
        "pages_in_djvu": len(pages),
        "pages_range": [cfg.first_page, cfg.last_page],
        "notices": len(artworks),
        "spans": len(spans),
        "links": len(links),
        "attributes": dict(kinds),
        "resolved": n_res,
        "resolved_E2": sum(
            1
            for a in artworks
            if a.resolution
            and a.resolution.mechanism == "E2_composite"
            and a.resolution.status == "resolved"
        ),
        "unresolved": len(artworks) - n_res,
        "unresolved_by_reason": dict(reasons.most_common()),
        "ambiguous_notices_ge2_candidates": amb,
        "met_objects_claimed_by_several_notices": collisions,
        "resolved_with_cc0_image": cc0,
        "ia_metadata": ia_subset,
        "djvu_sha256": djvu.sha256,
        "client_requests": client.requests,
        "seconds": round((datetime.now(UTC) - t0).total_seconds(), 1),
    }
    export.dump_json(out / "report.json", report)
    return report
