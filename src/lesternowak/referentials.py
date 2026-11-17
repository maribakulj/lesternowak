"""Référentiels d'œuvres locaux (lot C2) et résolveur E0 / E2 composite (ADR 0003).

Les fiches de collection sont mises en cache sous `data/ref/<source>.jsonl` (ignoré par Git) et
servent de liste fermée de candidats. Le résolveur ne conclut jamais sur le titre ou l'artiste
seuls ; en cas de doute il retourne `unresolved` avec la raison et les candidats en lice.
"""

# ruff: noqa: RUF001, RUF002
from __future__ import annotations

import json
import math
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

MET_API = "https://collectionapi.metmuseum.org/public/collection/v1"
USER_AGENT = "lesternowak/0.0.1 (recherche; référentiel local)"
DIM_TOLERANCE_CM = 2.0
CREDIT_THRESHOLD = 0.9
ARTIST_THRESHOLD = 0.85
IN_TO_CM = 2.54

ImageLicense = Literal["cc0", "public_domain", "restricted", "unknown"]


class OtherNumber(BaseModel):
    scheme: str  # ex. "Villot", "Both de Tauzia", "inv_ancien"
    value: str
    source: str  # provenance de l'attribut (URL ou champ de la source)


class ReferenceArtwork(BaseModel):
    ref_id: str  # "<source>:<external_id>"
    source: str
    external_id: str
    accession_number: str = ""
    title: str = ""
    artist: str = ""
    artist_dates: str = ""
    date: str = ""
    medium: str = ""
    dimensions_raw: str = ""
    dimensions_cm: tuple[float, float] | None = None  # (hauteur, largeur)
    credit_line: str = ""
    accession_year: int | None = None
    department: str = ""
    collection_url: str = ""
    image_url: str = ""
    image_license: ImageLicense = "unknown"
    is_public_domain: bool = False
    other_numbers: list[OtherNumber] = Field(default_factory=list)
    retrieved_at: str = ""
    source_url: str = ""


# --- dimensions -----------------------------------------------------------------------------

_FRACS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅓": " 1/3", "⅔": " 2/3", "⅛": " 1/8"}
_NUM = r"(\d+(?:[.,]\d+)?(?:\s+\d+/\d+)?|\d+/\d+)"


def _to_float(s: str) -> float:
    s = s.strip().replace(",", ".")
    total = 0.0
    for part in s.split():
        if "/" in part:
            a, b = part.split("/")
            total += int(a) / int(b)
        else:
            total += float(part)
    return total


def parse_dimensions(raw: str) -> tuple[float, float] | None:
    """(hauteur, largeur) en cm, ou None. Priorité à la valeur en cm ; sinon pouces convertis.

    Formes : « 28 13/16 × 36 3/4 in. (73.2 × 93.4 cm) », « H. 28 1/2 in.; W. 36 in. »,
    « 73 × 93 cm ». Les mesures à trois dimensions ou sans unité ne sont pas interprétées.
    """
    if not raw:
        return None
    for k, v in _FRACS.items():
        raw = raw.replace(k, v)
    raw = raw.replace("x", "×").replace("X", "×")
    m = re.search(rf"{_NUM}\s*×\s*{_NUM}\s*cm", raw)
    if m and "×" not in raw[m.end() : m.end() + 6]:
        return (_to_float(m.group(1)), _to_float(m.group(2)))
    m = re.search(rf"{_NUM}\s*×\s*{_NUM}\s*(?:in\b|inches|po\b)", raw)
    if m:
        return (_to_float(m.group(1)) * IN_TO_CM, _to_float(m.group(2)) * IN_TO_CM)
    m = re.search(rf"H\w*\.?\s*{_NUM}\s*(in|cm)?[^W]*?W\w*\.?\s*{_NUM}\s*(in|cm)?", raw)
    if m:
        unit = m.group(4) or m.group(2) or "in"
        k = IN_TO_CM if unit == "in" else 1.0
        return (_to_float(m.group(1)) * k, _to_float(m.group(3)) * k)
    return None


# --- cache JSONL ----------------------------------------------------------------------------


def cache_path(source: str, root: Path = Path("data/ref")) -> Path:
    return root / f"{source}.jsonl"


def load_cache(path: Path) -> list[ReferenceArtwork]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(ReferenceArtwork.model_validate_json(line))
    return out


def append_cache(path: Path, ref: ReferenceArtwork) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(ref.model_dump_json() + "\n")


# --- HTTP poli ------------------------------------------------------------------------------


class PoliteClient:
    """GET JSON limité en débit, avec backoff sur 429/5xx et respect de `Retry-After`."""

    def __init__(self, max_per_sec: float, max_retries: int = 6, sleep=time.sleep):
        self.min_interval = 1.0 / max_per_sec
        self.max_retries = max_retries
        self._last = 0.0
        self._sleep = sleep

    def get_json(self, url: str) -> dict | None:
        """None si 404 (statut consigné par l'appelant) ; lève sur échec persistant."""
        for attempt in range(self.max_retries):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                self._sleep(wait)
            self._last = time.monotonic()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code == 403:
                    raise RuntimeError(f"403 sur {url} : arrêt (statut, pas un obstacle)") from e
                if e.code in (429, 500, 502, 503, 504):
                    ra = e.headers.get("Retry-After")
                    delay = float(ra) if ra and ra.isdigit() else min(2.0**attempt, 60.0)
                    self._sleep(delay)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                self._sleep(min(2.0**attempt, 60.0))
        raise RuntimeError(f"échec persistant sur {url}")


# --- Met ------------------------------------------------------------------------------------


def met_to_ref(obj: dict, retrieved_at: str) -> ReferenceArtwork:
    oid = str(obj["objectID"])
    pd = bool(obj.get("isPublicDomain"))
    img = obj.get("primaryImage") or ""
    year = obj.get("accessionYear") or ""
    dims = obj.get("dimensions") or ""
    parsed = parse_dimensions(dims)
    if parsed is None:  # repli sur les mesures structurées (cm), élément « Overall » sinon premier
        for el in obj.get("measurements") or []:
            mm = el.get("elementMeasurements") or {}
            if mm.get("Height") and mm.get("Width"):
                parsed = (float(mm["Height"]), float(mm["Width"]))
                if el.get("elementName") == "Overall":
                    break
    return ReferenceArtwork(
        ref_id=f"met:{oid}",
        source="met",
        external_id=oid,
        accession_number=obj.get("accessionNumber") or "",
        title=obj.get("title") or "",
        artist=obj.get("artistDisplayName") or "",
        artist_dates=obj.get("artistDisplayBio") or "",
        date=obj.get("objectDate") or "",
        medium=obj.get("medium") or "",
        dimensions_raw=dims,
        dimensions_cm=parsed,
        credit_line=obj.get("creditLine") or "",
        accession_year=int(year) if year.isdigit() else None,
        department=obj.get("department") or "",
        collection_url=obj.get("objectURL") or "",
        image_url=img if (pd and img) else "",
        image_license="cc0" if (pd and img) else ("restricted" if img else "unknown"),
        is_public_domain=pd,
        other_numbers=[],
        retrieved_at=retrieved_at,
        source_url=f"{MET_API}/objects/{oid}",
    )


def build_met(
    department: str,
    cache_dir: Path = Path("data/ref"),
    client: PoliteClient | None = None,
    log: Callable[[str], None] = print,
) -> dict:
    client = client or PoliteClient(max_per_sec=2.5)
    deps = client.get_json(f"{MET_API}/departments") or {}
    ids = [
        d["departmentId"]
        for d in deps.get("departments", [])
        if d["displayName"].lower() == department.lower()
    ]
    if not ids:
        raise ValueError(f"département Met inconnu : {department!r}")
    listing = client.get_json(f"{MET_API}/objects?departmentIds={ids[0]}") or {}
    object_ids = listing.get("objectIDs") or []
    path = cache_path("met", cache_dir)
    done = {r.external_id for r in load_cache(path)}
    todo = [i for i in object_ids if str(i) not in done]
    log(f"met/{department} : {len(object_ids)} ids, {len(done)} en cache, {len(todo)} à récupérer")
    t0 = time.monotonic()
    missing = 0
    for n, oid in enumerate(todo, 1):
        obj = client.get_json(f"{MET_API}/objects/{oid}")
        if obj is None:
            missing += 1
            continue
        append_cache(path, met_to_ref(obj, datetime.now(UTC).isoformat(timespec="seconds")))
        if n % 200 == 0:
            log(f"  {n}/{len(todo)} ({time.monotonic() - t0:.0f} s)")
    return {
        "listed": len(object_ids),
        "fetched": len(todo) - missing,
        "missing_404": missing,
        "seconds": round(time.monotonic() - t0, 1),
    }


# --- Louvre via Joconde (open data, Licence Ouverte 2.0) -----------------------------------

JOCONDE_CSV = "https://ministere-culture.s3.sbg.io.cloud.ovh.net/POP/joconde.csv"
JOCONDE_PAGE = "https://www.data.gouv.fr/datasets/5b448216a3a729752eb11d6f/"
_LOUVRE_REF = re.compile(
    r"\b(Villot\s+[IVX]+\s+\d+|Suppl\.?\s*Tauzia\s+\d+|Reiset\s+\d+|Cornu\s+\d+)"
)
_INV_PREFIX = re.compile(r"^([A-Za-z]+)\s*(.+)$")


def _joconde_dims(raw: str) -> tuple[float, float] | None:
    """« 41 H ; 52 L » (cm) -> (41, 52)."""
    h = re.search(r"(\d+(?:[.,]\d+)?)\s*H\b", raw)
    w = re.search(r"(\d+(?:[.,]\d+)?)\s*L\b", raw)
    return (_to_float(h.group(1)), _to_float(w.group(1))) if h and w else None


def joconde_to_ref(row: dict[str, str], retrieved_at: str) -> ReferenceArtwork:
    """Fiche Joconde -> référence. Anciens numéros : uniquement ceux écrits tels quels dans
    `Numero_inventaire` (numéros multiples) et les renvois `Villot II 365`, `Suppl. Tauzia 809`
    de `Bibliographie` ; rien n'est inféré."""
    ref = row["Reference"]
    invs = [x.strip() for x in row.get("Numero_inventaire", "").split(";") if x.strip()]
    others = []
    src_inv = f"joconde:{ref}:Numero_inventaire"
    for x in invs[1:]:
        m = _INV_PREFIX.match(x)
        others.append(
            OtherNumber(scheme=m.group(1).upper() if m else "inv", value=x, source=src_inv)
        )
    for m in _LOUVRE_REF.finditer(row.get("Bibliographie", "")):
        label, _, num = m.group(1).rpartition(" ")
        scheme = re.sub(r"[^A-Za-z]", "", label.split()[0] if "Suppl" not in label else "Tauzia")
        others.append(
            OtherNumber(
                scheme=scheme.capitalize(),
                value=num,
                source=f"joconde:{ref}:Bibliographie",
            )
        )
    acq = re.search(r"\d{4}", row.get("Date_d_acquisition", ""))
    return ReferenceArtwork(
        ref_id=f"louvre-joconde:{ref}",
        source="louvre",
        external_id=ref,
        accession_number=invs[0] if invs else "",
        title=row.get("Titre", ""),
        artist=row.get("Auteur", ""),
        date=row.get("Epoque", "") or row.get("Date_creation", ""),
        medium=row.get("Materiaux_techniques", ""),
        dimensions_raw=row.get("Mesures", ""),
        dimensions_cm=_joconde_dims(row.get("Mesures", "")),
        credit_line=row.get("Ancienne_appartenance", ""),  # provenance, pas une « credit line »
        accession_year=int(acq.group(0)) if acq else None,
        department="Département des Peintures",
        collection_url=f"https://pop.culture.gouv.fr/notice/joconde/{ref}",
        image_url="",
        image_license="unknown",  # Joconde ne donne pas d'URL d'image ni de licence d'image
        is_public_domain=False,
        other_numbers=others,
        retrieved_at=retrieved_at,
        source_url=JOCONDE_PAGE,
    )


def build_louvre(
    limit: int = 500, cache_dir: Path = Path("data/ref"), log: Callable[[str], None] = print
) -> dict:
    """Échantillon de peintures du Louvre : lecture en flux du CSV Joconde (une seule requête
    HTTP), arrêt dès `limit` fiches ; le fichier n'est pas conservé."""
    import csv
    import io

    csv.field_size_limit(10**9)
    path = cache_path("louvre", cache_dir)
    done = {r.external_id for r in load_cache(path)}
    req = urllib.request.Request(JOCONDE_CSV, headers={"User-Agent": USER_AGENT})
    n_read = n_new = 0
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=120) as resp:
        text = io.TextIOWrapper(resp, encoding="utf-8", errors="replace", newline="")
        rd = csv.reader(text, delimiter="|")
        header = next(rd)
        for row in rd:
            n_read += 1
            if len(row) != len(header):
                continue
            d = dict(zip(header, row, strict=True))
            if d["Nom_officiel_musee"] != "musée du Louvre" or "peinture" not in d["Domaine"]:
                continue
            if d["Reference"] in done:
                continue
            append_cache(path, joconde_to_ref(d, datetime.now(UTC).isoformat(timespec="seconds")))
            done.add(d["Reference"])
            n_new += 1
            if len(done) >= limit:
                break
    log(f"louvre : {n_new} nouvelles fiches ({len(done)} au total)")
    return {
        "rows_read": n_read,
        "new": n_new,
        "total": len(done),
        "seconds": round(time.monotonic() - t0, 1),
    }


# --- résolveur ------------------------------------------------------------------------------


class LocalAttrs(BaseModel):
    """Attributs lus dans une notice locale (aucun n'est inventé : absent = None)."""

    accession_number: str | None = None
    credit_line: str | None = None
    accession_year: int | None = None
    dimensions_cm: tuple[float, float] | None = None
    # OCR dégradé : parties entières possibles (pouces) par axe, quand la fraction est illisible
    dimension_inch_options: tuple[tuple[int, ...], tuple[int, ...]] | None = None
    dimensions_raw: str | None = None  # converti en cm (pouces compris) si dimensions_cm absent
    other_numbers: list[OtherNumber] = Field(default_factory=list)
    artist: str | None = None


class CandidateSignals(BaseModel):
    ref_id: str
    accession_number: bool = False
    credit_line: float | None = None  # score si >= seuil
    accession_year: bool = False
    dimensions: bool = False
    other_number: bool = False
    artist: float | None = None  # score si >= seuil (appui, jamais signal indépendant)

    def independent(self) -> list[str]:
        # crédit et année d'accession ne sont pas indépendants (la ligne de crédit porte l'année
        # d'entrée) : ils comptent ensemble pour un seul signal.
        out = []
        if self.credit_line is not None or self.accession_year:
            out.append("credit_or_year")
        if self.dimensions:
            out.append("dimensions")
        if self.other_number:
            out.append("other_number")
        return out


class ResolutionResult(BaseModel):
    status: Literal["resolved", "unresolved"]
    evidence: Literal["E0", "E2", "none"] = "none"
    ref_id: str | None = None
    reason: str
    signals: list[CandidateSignals] = Field(default_factory=list)  # candidats en lice
    candidates: list[str] = Field(default_factory=list)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


def _norm_acc(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _dims_match(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= DIM_TOLERANCE_CM and abs(a[1] - b[1]) <= DIM_TOLERANCE_CM


def _signals(local: LocalAttrs, ref: ReferenceArtwork) -> CandidateSignals:
    s = CandidateSignals(ref_id=ref.ref_id)
    if local.accession_number and ref.accession_number:
        s.accession_number = _norm_acc(local.accession_number) == _norm_acc(ref.accession_number)
    if local.credit_line and ref.credit_line:
        sc = fuzz.ratio(_norm(local.credit_line), _norm(ref.credit_line)) / 100
        s.credit_line = round(sc, 3) if sc >= CREDIT_THRESHOLD else None
    if local.accession_year and ref.accession_year:
        s.accession_year = local.accession_year == ref.accession_year
    ldims = local.dimensions_cm or (
        parse_dimensions(local.dimensions_raw) if local.dimensions_raw else None
    )
    if ldims and ref.dimensions_cm:
        s.dimensions = _dims_match(ldims, ref.dimensions_cm)
    elif local.dimension_inch_options and ref.dimensions_cm:
        # partie entière en pouces de la fiche (à 0,03 in près) parmi celles lues sur chaque axe
        ho, wo = local.dimension_inch_options
        h, w = (math.floor(v / IN_TO_CM + 0.03) for v in ref.dimensions_cm)
        s.dimensions = h in ho and w in wo
    for n in local.other_numbers:
        if any(
            o.scheme.lower() == n.scheme.lower() and _norm_acc(o.value) == _norm_acc(n.value)
            for o in ref.other_numbers
        ):
            s.other_number = True
    if local.artist and ref.artist:
        sc = fuzz.token_sort_ratio(_norm(local.artist), _norm(ref.artist)) / 100
        s.artist = round(sc, 3) if sc >= ARTIST_THRESHOLD else None
    return s


def resolve(local: LocalAttrs, refs: list[ReferenceArtwork]) -> ResolutionResult:
    """E0 si le numéro d'accession cité est trouvé ; sinon E2 composite ; sinon `unresolved`."""
    sigs = [_signals(local, r) for r in refs]
    # E0
    e0 = [s for s in sigs if s.accession_number]
    if len(e0) == 1:
        return ResolutionResult(
            status="resolved",
            evidence="E0",
            ref_id=e0[0].ref_id,
            reason="numéro d'accession cité et trouvé (candidat unique)",
            signals=e0,
            candidates=[e0[0].ref_id],
        )
    if len(e0) > 1:
        return ResolutionResult(
            status="unresolved",
            reason="numéro d'accession présent dans plusieurs fiches",
            signals=e0,
            candidates=[s.ref_id for s in e0],
        )
    # E2 composite
    multi = [s for s in sigs if len(s.independent()) >= 2]
    if not multi:
        near = [s for s in sigs if s.independent()]
        return ResolutionResult(
            status="unresolved",
            reason="moins de 2 attributs indépendants concordants "
            "(titre et artiste seuls ne suffisent jamais)",
            signals=near,
            candidates=[s.ref_id for s in near],
        )
    if local.artist:
        supported = [s for s in multi if s.artist is not None]
        if not supported:
            return ResolutionResult(
                status="unresolved",
                reason="attributs concordants mais artiste non concordant",
                signals=multi,
                candidates=[s.ref_id for s in multi],
            )
        multi = supported
    else:
        return ResolutionResult(
            status="unresolved",
            reason="aucun artiste local en appui",
            signals=multi,
            candidates=[s.ref_id for s in multi],
        )
    if len(multi) > 1:
        return ResolutionResult(
            status="unresolved",
            reason=f"{len(multi)} candidats restants (unicité requise)",
            signals=multi,
            candidates=[s.ref_id for s in multi],
        )
    return ResolutionResult(
        status="resolved",
        evidence="E2",
        ref_id=multi[0].ref_id,
        reason="E2 composite : " + ", ".join(multi[0].independent()) + " + artiste",
        signals=multi,
        candidates=[multi[0].ref_id],
    )


def iter_cache(source: str, root: Path = Path("data/ref")) -> Iterator[ReferenceArtwork]:
    yield from load_cache(cache_path(source, root))
