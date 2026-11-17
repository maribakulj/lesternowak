"""Adaptateur pilote des slices Quire : un élément par lien (E1 d'entrée ou appel de figure).

L'image de la figure n'est proposée que si ses droits autorisent l'affichage pilote ; sinon le
lecteur ne reçoit que le lien vers la page source. L'appel « fig. N » est surligné dans le passage.
"""

from __future__ import annotations

from pathlib import Path

from lesternowak.export import read_jsonl
from lesternowak.models import (
    ArtworkRef,
    Link,
    QuireFigure,
    Relation,
    ReviewArtwork,
    ReviewHighlight,
    ReviewItem,
    ReviewPassage,
    ReviewProposal,
    ReviewSource,
    Run,
    SourceAsset,
    Span,
)


def _display_allowed(fig: QuireFigure) -> bool:
    return any(
        r.action == "display_pilot" and r.decision.value == "allow" for r in fig.image_rights
    )


def quire_items(slice_dir: Path) -> list[ReviewItem]:
    from lesternowak.review import _rights_summary, item_id_for

    spans = {s.id: s for s in read_jsonl(slice_dir / "spans.jsonl", Span)}
    arts = {a.id: a for a in read_jsonl(slice_dir / "artworks.jsonl", ArtworkRef)}
    figs = {f.id: f for f in read_jsonl(slice_dir / "figures.jsonl", QuireFigure)}
    assets = {a.id: a for a in read_jsonl(slice_dir / "assets.jsonl", SourceAsset)}
    corpus = read_jsonl(slice_dir / "runs.jsonl", Run)[0].params["catalogue"]
    items = []
    for lk in read_jsonl(slice_dir / "links.jsonl", Link):
        sp, art = spans[lk.span_id], arts[lk.artwork_id]
        called = [figs[i] for i in lk.figure_ids]
        shown = next((f for f in called if f.artwork_id == art.id and _display_allowed(f)), None)
        hl = [
            ReviewHighlight(start=c.char_start, end=c.char_end, label="figure_call")
            for c in sp.figure_calls
            if c.figure_id in lk.figure_ids
        ]
        src = assets[sp.asset_id].url + ("#" + called[0].id.split(":", 1)[1] if called else "")
        ev = lk.evidence[0]
        res = art.resolution
        items.append(
            ReviewItem(
                item_id=item_id_for(corpus, lk.id, sp.id, art.id),
                corpus=corpus,
                link_id=lk.id,
                artwork=ReviewArtwork(
                    id=art.id,
                    title=art.local_label or art.title,
                    catalogue_number=art.catalogue_number or None,
                    accession_number=art.inventory_number or None,
                    other_ids={
                        "artwork_local_id": art.artwork_local_id or "",
                        "resolution": res.status if res else "unresolved",
                    },
                    collection_url=art.collection_url or None,
                    image_url=shown.image_url if shown else None,
                    image_display_allowed=shown is not None,
                ),
                passage=ReviewPassage(
                    span_id=sp.id,
                    text=sp.text,
                    section=sp.section_label,
                    char_start=sp.char_start,
                    char_end=sp.char_end,
                ),
                highlights=sorted(hl, key=lambda h: (h.start, h.end)),
                source=ReviewSource(url=src),
                proposal=ReviewProposal(
                    relation=Relation.about,
                    function=None if lk.role.value == "unclassified" else lk.role,
                    evidence_mechanism=ev.mechanism,
                    explanation=ev.explanation,
                ),
                rights_summary=_rights_summary(lk),
            )
        )
    return items
