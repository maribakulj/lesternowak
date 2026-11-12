"""Tranche verticale Getty Quire : Ancient Terracottas (Ferruzza, 2016, CC BY 4.0).

Règle E1 (structure de notice) : la section Description / Discussion d'une page d'entrée
`catalogue/<n>/` concerne l'objet de cette entrée, identifié par les données de l'éditeur.
Aucun texte n'est produit par un modèle : chaque passage est une sous-chaîne exacte du
texte canonique extrait, vérifiée à la construction.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from lxml import html as lxml_html

from lesternowak import __version__
from lesternowak.models import (
    AnnotationEvent,
    ArtworkRef,
    Decision,
    Evidence,
    Link,
    LinkStatus,
    Occurrence,
    PassageRole,
    RightsDecision,
    Run,
    SourceAsset,
    Span,
    Surrogate,
)

BASE = "https://www.getty.edu/publications/terracottas/"
DATA_URL = BASE + "assets/downloads/AncientTerracottas_Ferruzza_Data.json"
ABOUT_URL = BASE + "about/"
USER_AGENT = "lesternowak-research/0.0.1 (open-access catalogue study; rate-limited, cached)"
MIN_DELAY_S = 1.0

# Règle de fonction : intitulé de section -> rôle. Seules ces sections font l'objet de liens.
SECTION_ROLES: dict[str, PassageRole] = {
    "Description": PassageRole.visual_description,
    "Discussion": PassageRole.interpretive_discussion,
    "Group Discussion": PassageRole.interpretive_discussion,
}

TEXT_ACTIONS = ("tdm", "publish_text", "redistribute_text", "remote_llm", "training")
IMAGE_ACTIONS = ("publish_image", "redistribute_image", "tdm", "remote_llm", "training")

_last_request = 0.0


class FetchStatusError(RuntimeError):
    """Statut HTTP non réussi (un 403 est un statut, pas un obstacle à contourner)."""


def _http_get(url: str) -> bytes:
    global _last_request
    for attempt in range(3):
        wait = MIN_DELAY_S - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(min(int(e.headers.get("Retry-After", "5")), 120))
                continue
            raise FetchStatusError(f"{url} -> HTTP {e.code}") from e
    raise FetchStatusError(f"{url}: trop de tentatives")


def fetch_cached(url: str, cache_dir: Path, media_type: str) -> tuple[bytes, SourceAsset]:
    """Télécharge `url` (ou relit le cache) ; sidecar JSON avec sha256 et date de capture."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.removeprefix("https://"))
    path, sidecar = cache_dir / name, cache_dir / (name + ".meta.json")
    if path.exists() and sidecar.exists():
        meta = json.loads(sidecar.read_text())
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != meta["sha256"]:
            raise RuntimeError(f"cache corrompu : {path}")
    else:
        data = _http_get(url)
        meta = {
            "url": url,
            "sha256": hashlib.sha256(data).hexdigest(),
            "captured_at": datetime.now(UTC).isoformat(),
            "media_type": media_type,
        }
        path.write_bytes(data)
        sidecar.write_text(json.dumps(meta, indent=2))
    asset = SourceAsset(
        id=meta["sha256"][:12],
        url=url,
        sha256=meta["sha256"],
        captured_at=meta["captured_at"],
        media_type=meta["media_type"],
        local_path=str(path),
    )
    return data, asset


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _para_text(el) -> str:
    """Texte d'un bloc sans marques d'appel de note (<sup>)."""
    import copy

    el = copy.deepcopy(el)
    for sup in el.xpath(".//sup"):
        sup.drop_tree()
    return _clean(el.text_content())


class ParsedEntry:
    def __init__(self, number, title, inventory, canonical, sections, discussion_group):
        self.number = number
        self.title = title
        self.inventory = inventory
        self.canonical_text = canonical
        # [(label, start, end)] : bornes du corps de chaque section dans canonical_text
        self.sections = sections
        self.discussion_group = discussion_group  # (titre du groupe, note) ou None


def parse_entry(page: bytes) -> ParsedEntry:
    root = lxml_html.fromstring(page)
    number = _clean(root.xpath('//h2[contains(@class,"object-meta")]')[0].text_content())
    title = _clean(root.xpath('//h1[@class="object-title"]')[0].text_content())
    inventory = None
    for row in root.xpath('//table[@class="object-info"]//tr'):
        cells = [_clean(c.text_content()) for c in row]
        if cells and cells[0] == "Inventory Number":
            inventory = cells[1]
    canonical, sections, group = "", [], None
    for sec in root.xpath(
        '//div[@class="object-content"]/div[contains(@class,"object-content-section")]'
    ):
        label = _clean(sec.xpath(".//h3")[0].text_content())
        if label == "Object Details":
            continue
        content = sec.xpath('./div[contains(@class,"expander-content")]')[0]
        paras = [_para_text(p) for p in content.xpath("./p")]
        paras = [p for p in paras if p]
        if label in SECTION_ROLES and label.endswith("Discussion"):
            h4 = content.xpath("./h4")
            h6 = content.xpath('./h6[@class="discussion-note"]')
            group = (
                _clean(h4[0].text_content()) if h4 else None,
                _clean(h6[0].text_content()) if h6 else None,
            )
        canonical += label + "\n"
        start = len(canonical)
        canonical += "\n\n".join(paras)
        sections.append((label, start, len(canonical)))
        canonical += "\n\n"
    return ParsedEntry(number, title, inventory, canonical, sections, group)


def artwork_for(entry_no: int, data: list[dict]) -> ArtworkRef:
    rows = [r for r in data if r["Catalogue/Guide Number"] == f"cat. {entry_no}"]
    if len(rows) != 1:
        raise ValueError(f"cat. {entry_no}: {len(rows)} correspondances dans les données")
    r = rows[0]
    return ArtworkRef(
        id=f"getty-{r['DOR ID']}",
        getty_dor_id=r["DOR ID"],
        inventory_number=r["Inventory Number"],
        catalogue_number=r["Catalogue/Guide Number"],
        collection_url=r["Collection Page URL"],
        title=r["Title"],
    )


def rights_decisions(checked_at: datetime) -> list[RightsDecision]:
    out = [
        RightsDecision(
            asset="text",
            action=a,
            decision=Decision.allow,
            basis="CC BY 4.0, attribution required",
            evidence_url=ABOUT_URL,
            checked_at=checked_at,
        )
        for a in TEXT_ACTIONS
    ]
    out += [
        RightsDecision(
            asset="images",
            action=a,
            decision=Decision.unknown,
            basis="crédits par figure non contrôlés (« except where otherwise noted »)",
            evidence_url=ABOUT_URL,
            checked_at=checked_at,
        )
        for a in IMAGE_ACTIONS
    ]
    return out


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def git_version() -> str:
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        rev = "unknown"
    return f"{__version__}+{rev}"


def build_records(
    entries: dict[int, tuple[bytes, SourceAsset]],
    data: list[dict],
    run: Run,
    checked_at: datetime,
) -> dict:
    """Construit artworks, spans, links ; vérifie chaque offset (échec bruyant)."""
    artworks: dict[str, ArtworkRef] = {}
    spans: dict[str, Span] = {}
    links: list[Link] = []
    for no, (page, asset) in entries.items():
        entry = parse_entry(page)
        art = artwork_for(no, data)
        # contrôles de cohérence page <-> données de l'éditeur
        if entry.number != str(no):
            raise ValueError(f"cat. {no}: page annonce l'entrée {entry.number!r}")
        if entry.inventory != art.inventory_number:
            raise ValueError(
                f"cat. {no}: inventaire {entry.inventory!r} != {art.inventory_number!r}"
            )
        if entry.title != art.title:
            raise ValueError(f"cat. {no}: titre {entry.title!r} != {art.title!r}")
        artworks[art.id] = art
        for label, start, end in entry.sections:
            role = SECTION_ROLES.get(label)
            if role is None or end <= start:
                continue
            text = entry.canonical_text[start:end]
            assert entry.canonical_text[start:end] == text and text, "offset invalide"
            sid = "spn_" + _sha(text)[:12]
            if sid in spans:
                if spans[sid].text != text:
                    raise AssertionError(f"collision de hachage {sid}")
                spans[sid].also_in.append(
                    Occurrence(asset_id=asset.id, char_start=start, char_end=end)
                )
            else:
                spans[sid] = Span(
                    id=sid,
                    asset_id=asset.id,
                    section_label=label,
                    char_start=start,
                    char_end=end,
                    text=text,
                    group_title=entry.discussion_group[0]
                    if label.endswith("Discussion") and entry.discussion_group
                    else None,
                )
            shared = ""
            if label.endswith("Discussion") and entry.discussion_group:
                shared = (
                    f" Discussion de groupe « {entry.discussion_group[0]} » ; "
                    f"note de l'éditeur : « {entry.discussion_group[1]} »"
                )
            links.append(
                Link(
                    id="lnk_" + _sha(f"{art.id}|{sid}|{role}")[:12],
                    artwork_id=art.id,
                    span_id=sid,
                    role=role,
                    evidence=[
                        Evidence(
                            mechanism="editorial_entry_structure",
                            quoted_heading=label,
                            explanation=(
                                f"E1 : la page catalogue/{no}/ est l'entrée de l'objet "
                                f"« {art.title} » ({art.catalogue_number}, inv. "
                                f"{art.inventory_number}, DOR {art.getty_dor_id}), appariée aux "
                                "données de l'éditeur par numéro de catalogue, inventaire et "
                                f"titre concordants ; la section « {label} » de cette entrée "
                                f"est rattachée à cet objet.{shared}"
                            ),
                        )
                    ],
                    status=LinkStatus.machine_proposed,
                    rights=rights_decisions(checked_at),
                    run_id=run.id,
                )
            )
    # vérification finale des offsets, y compris occurrences partagées
    canon = {a.id: parse_entry(p).canonical_text for p, a in entries.values()}
    for sp in spans.values():
        assert canon[sp.asset_id][sp.char_start : sp.char_end] == sp.text, sp.id
        for oc in sp.also_in:
            assert canon[oc.asset_id][oc.char_start : oc.char_end] == sp.text, sp.id
    return {"artworks": list(artworks.values()), "spans": list(spans.values()), "links": links}


def fetch_entries(nos: list[int], cache_dir: Path):
    data_bytes, data_asset = fetch_cached(DATA_URL, cache_dir, "application/json")
    pages = {n: fetch_cached(f"{BASE}catalogue/{n}/", cache_dir, "text/html") for n in nos}
    return json.loads(data_bytes), data_asset, pages


SURROGATE = dict(
    publication_url=BASE,
    title="Ancient Terracottas from South Italy and Sicily in the J. Paul Getty Museum",
    author="Maria Lucia Ferruzza",
    publisher="J. Paul Getty Museum",
    year=2016,
    license_url="https://creativecommons.org/licenses/by/4.0/",
)


def current_statuses(links: list[Link], events: list[AnnotationEvent]) -> dict[str, LinkStatus]:
    status = {link.id: link.status for link in links}
    for ev in sorted(events, key=lambda e: e.timestamp):
        if ev.link_id in status:
            status[ev.link_id] = ev.after
    return status


def make_run(nos: list[int]) -> Run:
    now = datetime.now(UTC)
    return Run(
        id="run_" + now.strftime("%Y%m%dT%H%M%S"),
        code_version=git_version(),
        params={"source": "getty-terracottas", "entries": nos, "rule": "E1"},
        started_at=now,
    )


__all__ = [
    "SURROGATE",
    "Surrogate",
    "build_records",
    "current_statuses",
    "fetch_entries",
    "make_run",
    "parse_entry",
]
