"""Pilote de vérification (C6) : file d'éléments, serveur local, export gold.

Indépendant de la source : un adaptateur transforme un jeu de données en `ReviewItem`.
Adaptateurs : Terracottas et slices Gallica (`gallica-notices`) ; en ajouter un = une fonction
dans `ADAPTERS`.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lesternowak.annotation import GoldRecord, load_slice
from lesternowak.export import append_event, read_jsonl, write_jsonl
from lesternowak.models import (
    GOLD_FUNCTIONS,
    AnnotationEvent,
    ArtworkRef,
    Link,
    LinkStatus,
    PassageFunction,
    Relation,
    ReviewArtwork,
    ReviewHighlight,
    ReviewItem,
    ReviewPassage,
    ReviewProposal,
    ReviewSource,
    Run,
    Span,
)


def item_id_for(corpus: str, link_id: str | None, span_id: str, artwork_id: str) -> str:
    key = f"{corpus}|{link_id or ''}|{span_id}|{artwork_id}"
    return "rev_" + hashlib.sha256(key.encode()).hexdigest()[:12]


# --- adaptateur Terracottas -------------------------------------------------------------------


def _highlights(text: str, art: ArtworkRef) -> list[ReviewHighlight]:
    """Identifiants et titre de l'œuvre présents dans le passage (indices, pas preuve)."""
    pats = [
        ("inventory", re.escape(art.inventory_number)),
        ("catalogue", r"\bcats?\.\s*\d+(?:\s*[\u2013-]\s*\d+)?"),
        ("title", re.escape(art.title)),
    ]
    out: list[ReviewHighlight] = []
    for label, pat in pats:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            out.append(ReviewHighlight(start=m.start(), end=m.end(), label=label))
    return sorted(out, key=lambda h: (h.start, h.end))


def _rights_summary(link: Link) -> str:
    by: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for r in link.rights:
        by[(r.asset, r.decision.value, r.basis)].append(r.action)
    return " ; ".join(
        f"{asset} {dec} ({', '.join(acts)}) : {basis}"
        for (asset, dec, basis), acts in sorted(by.items())
    )


def terracottas_items(slice_dir: Path) -> list[ReviewItem]:
    sl = load_slice(slice_dir)
    spans = {s.id: s for s in sl.spans}
    arts = {a.id: a for a in sl.artworks}
    assets = {a.id: a for a in sl.assets}
    corpus = "getty-terracottas"
    items = []
    for lk in sl.links:
        sp, art = spans[lk.span_id], arts[lk.artwork_id]
        ev = lk.evidence[0]
        fn = None if lk.role == PassageFunction.unclassified else lk.role
        items.append(
            ReviewItem(
                item_id=item_id_for(corpus, lk.id, sp.id, art.id),
                corpus=corpus,
                link_id=lk.id,
                artwork=ReviewArtwork(
                    id=art.id,
                    title=art.title,
                    catalogue_number=art.catalogue_number,
                    accession_number=art.inventory_number,
                    other_ids={"getty_dor_id": str(art.getty_dor_id)},
                    collection_url=art.collection_url,
                    image_url=None,
                    image_display_allowed=False,  # droits d'image inconnus : lien seulement
                ),
                passage=ReviewPassage(
                    span_id=sp.id,
                    text=sp.text,
                    section=sp.section_label,
                    char_start=sp.char_start,
                    char_end=sp.char_end,
                ),
                highlights=_highlights(sp.text, art),
                source=ReviewSource(url=assets[sp.asset_id].url),
                proposal=ReviewProposal(
                    relation=Relation.about,
                    function=fn,
                    evidence_mechanism=ev.mechanism,
                    explanation=ev.explanation,
                ),
                rights_summary=_rights_summary(lk),
            )
        )
    return items


# --- adaptateur slices Gallica (volume -> slice, `catalogue.py`) ------------------------------

_NUMBER_START = re.compile(r"^\s*\d{1,4}(?:\s*[-\u2013]\s*\d{1,4})?")


def gallica_items(slice_dir: Path) -> list[ReviewItem]:
    """Un élément par lien E1 notice -> œuvre locale : passage, numéro de notice surligné, image
    de la page (précalculée `medres`) et figure liée par numéro de légende si elle existe."""
    from lesternowak.gallica import GallicaClient
    from lesternowak.models import Figure, RightsDecision

    spans = {s.id: s for s in read_jsonl(slice_dir / "spans.jsonl", Span)}
    arts = {a.id: a for a in read_jsonl(slice_dir / "artworks.jsonl", ArtworkRef)}
    links = read_jsonl(slice_dir / "links.jsonl", Link)
    figs = read_jsonl(slice_dir / "figures.jsonl", Figure)
    params = read_jsonl(slice_dir / "runs.jsonl", Run)[0].params
    corpus, ark = params["catalogue"], params["ark"]
    fig_of = {f.linked_artwork_local_id: f for f in figs if f.linked_artwork_local_id}
    items = []
    for lk in links:
        sp, art = spans[lk.span_id], arts[lk.artwork_id]
        ref = sp.page_refs[0]
        fig = fig_of.get(art.artwork_local_id)
        shown = False
        if fig:
            shown = any(
                r.action == "display_pilot" and r.decision.value == "allow"
                for r in fig.image_rights
                if isinstance(r, RightsDecision)
            )
        hl = []
        m = _NUMBER_START.match(sp.text)
        if m and art.local_label and sp.text.startswith(art.local_label):
            hl.append(ReviewHighlight(start=m.start(), end=m.end(), label="notice_number"))
        ev = lk.evidence[0]
        items.append(
            ReviewItem(
                item_id=item_id_for(corpus, lk.id, sp.id, art.id),
                corpus=corpus,
                link_id=lk.id,
                artwork=ReviewArtwork(
                    id=art.id,
                    title=art.local_label or "",
                    catalogue_number=art.catalogue_number or None,
                    other_ids={"artwork_local_id": art.artwork_local_id or ""},
                    image_url=fig.image_url if fig else None,
                    image_display_allowed=shown,
                ),
                passage=ReviewPassage(
                    span_id=sp.id,
                    text=sp.text,
                    section=corpus,
                    char_start=sp.char_start,
                    char_end=sp.char_end,
                ),
                highlights=hl,
                source=ReviewSource(
                    url=f"https://gallica.bnf.fr/ark:/12148/{ark}/f{ref.view}",
                    page_label=ref.page_label,
                    page_image_url=GallicaClient.url("medres", ark, n=ref.view),
                ),
                proposal=ReviewProposal(
                    relation=Relation.about,
                    function=None,
                    evidence_mechanism=ev.mechanism,
                    explanation=ev.explanation,
                ),
                rights_summary=_rights_summary(lk),
            )
        )
    return items


ADAPTERS: dict[str, Callable[[Path], list[ReviewItem]]] = {
    "getty-terracottas": terracottas_items,
    "gallica-notices": gallica_items,
}


# --- file priorisée ----------------------------------------------------------------------------


def _round_robin(groups: list[list]) -> list:
    out, i = [], 0
    while any(groups):
        for g in groups:
            if i < len(g):
                out.append(g[i])
        i += 1
        groups = [g for g in groups if i < len(g)] or [[]]
    return out


def diversity_order(items: list[ReviewItem], seed: int) -> list[ReviewItem]:
    """Alterne section, type de preuve, puis œuvre ; ordre interne tiré de façon déterministe."""

    def h(it: ReviewItem) -> str:
        return hashlib.sha256(f"{seed}|{it.item_id}".encode()).hexdigest()

    def mech(it: ReviewItem) -> str:
        return it.proposal.evidence_mechanism if it.proposal else ""

    buckets: dict[tuple, dict[str, list[ReviewItem]]] = defaultdict(lambda: defaultdict(list))
    for it in sorted(items, key=h):
        buckets[(it.passage.section, mech(it))][it.artwork.id].append(it)
    groups = [
        _round_robin([v for _, v in sorted(by_art.items())])
        for _, by_art in sorted(buckets.items())
    ]
    return _round_robin(groups)


def build_queue(items: list[ReviewItem], blind_rate: float, seed: int) -> list[ReviewItem]:
    if not 0 <= blind_rate <= 1:
        raise ValueError("blind_rate hors de [0, 1]")
    n_blind = round(blind_rate * len(items))
    drawn = sorted(
        items, key=lambda it: hashlib.sha256(f"blind|{seed}|{it.item_id}".encode()).hexdigest()
    )
    blind_ids = {it.item_id for it in drawn[:n_blind]}
    out = []
    for it in diversity_order(items, seed):
        if it.item_id in blind_ids:
            it = it.model_copy(update={"blind": True, "proposal": None})
        out.append(it)
    return out


def check_texts(items: list[ReviewItem], spans: dict[str, Span]) -> None:
    for it in items:
        sp = spans[it.passage.span_id]
        assert it.passage.text == sp.text, f"texte différent du span {sp.id}"
        for h in it.highlights:
            assert 0 <= h.start < h.end <= len(sp.text), f"surlignage hors passage {sp.id}"


def make_queue(adapter: str, slice_dir: Path, blind_rate: float, seed: int) -> list[ReviewItem]:
    items = ADAPTERS[adapter](slice_dir)
    if adapter == "getty-terracottas":
        check_texts(items, {s.id: s for s in load_slice(slice_dir).spans})
    return build_queue(items, blind_rate, seed)


def make_combined_queue(
    specs: list[tuple[str, Path]], blind_rate: float, seed: int
) -> list[ReviewItem]:
    """File unique sur plusieurs slices ((adaptateur, dossier)) ; diversité entre corpus."""
    items: list[ReviewItem] = []
    for adapter, d in specs:
        part = ADAPTERS[adapter](d)
        if adapter == "getty-terracottas":
            check_texts(part, {s.id: s for s in load_slice(d).spans})
        items += part
    ids = [i.item_id for i in items]
    if len(set(ids)) != len(ids):
        raise ValueError("item_id en double dans la file combinée")
    return build_queue(items, blind_rate, seed)


def write_queue(path: Path, items: list[ReviewItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(path, items)


def read_queue(path: Path) -> list[ReviewItem]:
    return read_jsonl(path, ReviewItem)


# --- événements --------------------------------------------------------------------------------


def last_events(events: list[AnnotationEvent]) -> dict[str, AnnotationEvent]:
    """Dernière décision par élément (une re-décision s'ajoute, rien n'est réécrit)."""
    out: dict[str, AnnotationEvent] = {}
    for ev in sorted(events, key=lambda e: e.timestamp):
        if ev.item_id:
            out[ev.item_id] = ev
    return out


class ReviewError(ValueError):
    pass


STATUS_OF_RELATION = {
    Relation.about: LinkStatus.validated,
    Relation.group: LinkStatus.validated,
    Relation.context: LinkStatus.rejected,
    Relation.mentions: LinkStatus.rejected,
    Relation.not_about: LinkStatus.rejected,
    Relation.unsure: LinkStatus.unresolved,
}
STATUS_NAME = {v.value: v for v in STATUS_OF_RELATION.values()}
NEEDS_FUNCTION = {Relation.about, Relation.group}


def make_event(item: ReviewItem, body: dict, annotator: str, now: datetime) -> AnnotationEvent:
    """Le statut est dérivé de la relation ; une `decision` fournie doit lui être cohérente."""
    try:
        relation = Relation(body.get("relation"))
        function = PassageFunction(body["function"]) if body.get("function") else None
    except ValueError as e:
        raise ReviewError(f"valeur invalide : {e}") from e
    if function == PassageFunction.unclassified:
        raise ReviewError("fonction invalide")
    status = STATUS_OF_RELATION[relation]
    given = body.get("decision")
    if given is not None and STATUS_NAME.get(given) != status:
        raise ReviewError(f"décision {given!r} incohérente avec la relation {relation.value}")
    if relation in NEEDS_FUNCTION and function is None:
        raise ReviewError("relation about/group : fonction obligatoire")
    elapsed = body.get("elapsed_ms")
    if elapsed is not None and (not isinstance(elapsed, int) or elapsed < 0):
        raise ReviewError("elapsed_ms invalide")
    note = body.get("note", "")
    if not isinstance(note, str) or len(note) > 5000:
        raise ReviewError("note invalide")
    return AnnotationEvent(
        link_id=item.link_id,
        before=LinkStatus.machine_proposed,
        after=status,
        annotator=annotator,
        note=note,
        timestamp=now,
        item_id=item.item_id,
        span_id=item.passage.span_id,
        artwork_id=item.artwork.id,
        relation=relation,
        function=function,
        blind=item.blind,
        elapsed_ms=elapsed,
    )


def stats(items: list[ReviewItem], events: list[AnnotationEvent]) -> dict:
    last = last_events(events)
    done = [e for k, e in last.items() if k in {i.item_id for i in items}]
    times = [e.elapsed_ms for e in done if e.elapsed_ms is not None]
    return {
        "total": len(items),
        "decided": len(done),
        "mean_ms": round(sum(times) / len(times)) if times else None,
    }


# --- export gold -------------------------------------------------------------------------------


def export_gold(queue: Path, events_path: Path, out: Path) -> int:
    items = {i.item_id: i for i in read_queue(queue)}
    events = read_jsonl(events_path, AnnotationEvent)
    sha = hashlib.sha256(events_path.read_bytes()).hexdigest() if events_path.exists() else ""
    records = []
    for iid, ev in last_events(events).items():
        it = items.get(iid)
        if it is None:
            continue
        if ev.relation is not None:
            rel = ev.relation
        elif ev.after == LinkStatus.unresolved:
            rel = Relation.unsure
        elif ev.after == LinkStatus.rejected:
            rel = Relation.not_about
        else:
            rel = it.proposal.relation if it.proposal else Relation.unsure
        if ev.after == LinkStatus.unresolved:
            rel = Relation.unsure
        fn = ev.function or (it.proposal.function if it.proposal else None)
        if fn is not None and fn not in GOLD_FUNCTIONS:
            fn = None
        records.append(
            GoldRecord(
                span_id=it.passage.span_id,
                artwork_id=it.artwork.id,
                relation=rel,
                function=fn.value if fn else "",
                annotator=ev.annotator,
                annotated_at=ev.timestamp.isoformat(),
                note=ev.note,
                sheet_sha256=sha,
            )
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out, records)
    return len(records)


# --- serveur -----------------------------------------------------------------------------------

CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "img-src https: http:; connect-src 'self'; base-uri 'none'; form-action 'none'"
)
MAX_BODY = 64 * 1024


def _public_event(ev: AnnotationEvent, item: ReviewItem) -> dict:
    d = ev.model_dump(mode="json")
    if item.blind:
        d["link_id"] = None
    return d


def make_server(
    queue: Path, events: Path, annotator: str, host: str = "127.0.0.1", port: int = 8765
) -> ThreadingHTTPServer:
    from lesternowak.review_ui import PAGE

    items = read_queue(queue)
    by_id = {i.item_id: i for i in items}
    lock = threading.Lock()
    allowed_hosts = {"127.0.0.1", "localhost", "[::1]", host}

    def state() -> dict:
        evs = read_jsonl(events, AnnotationEvent)
        last = last_events(evs)
        shown = []
        for it in items:
            d = it.model_dump(mode="json")
            a = d["artwork"]
            if not a["image_display_allowed"]:
                a["image_url"] = None  # affichage interdit : jamais transmis à la page
            if it.blind:
                d["link_id"] = None  # correspondance item_id -> link_id côté serveur seulement
            shown.append(d)
        return {
            "annotator": annotator,
            "items": shown,
            "events": {k: _public_event(v, by_id[k]) for k, v in last.items() if k in by_id},
            "stats": stats(items, evs),
        }

    class Handler(BaseHTTPRequestHandler):
        server_version = "lesternowak-review"

        def log_message(self, *a):  # silence
            pass

        def _host_ok(self) -> bool:
            return self.headers.get("Host", "").rsplit(":", 1)[0] in allowed_hosts

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj).encode(), "application/json; charset=utf-8")

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"error": "hôte refusé"})
            if self.path == "/":
                return self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            if self.path == "/api/state":
                with lock:
                    return self._json(200, state())
            self._json(404, {"error": "inconnu"})

        def do_POST(self):
            if not self._host_ok():
                return self._json(403, {"error": "hôte refusé"})
            if self.path != "/api/decision":
                return self._json(404, {"error": "inconnu"})
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._json(415, {"error": "JSON attendu"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n <= 0 or n > MAX_BODY:
                    raise ValueError
                body = json.loads(self.rfile.read(n))
                if not isinstance(body, dict):
                    raise ValueError
                it = by_id[body["item_id"]]
                ev = make_event(it, body, annotator, datetime.now(UTC))
            except (ValueError, KeyError, TypeError, ReviewError) as e:
                return self._json(400, {"error": str(e) or "requête invalide"})
            with lock:
                append_event(events, ev)
                return self._json(
                    200, {"ok": True, "stats": stats(items, read_jsonl(events, AnnotationEvent))}
                )

    return ThreadingHTTPServer((host, port), Handler)
