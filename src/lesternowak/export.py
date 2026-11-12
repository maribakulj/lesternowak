"""Export JSONL et page d'inspection statique (sans image : droits d'image inconnus)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from pydantic import BaseModel

from lesternowak.models import AnnotationEvent, ArtworkRef, Link, SourceAsset, Span


def write_jsonl(path: Path, items: list[BaseModel]) -> None:
    path.write_text("".join(i.model_dump_json() + "\n" for i in items), encoding="utf-8")


def read_jsonl[T: BaseModel](path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        return []
    return [model.model_validate_json(x) for x in path.read_text("utf-8").splitlines() if x]


def append_event(path: Path, event: AnnotationEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:  # ajout seul : links.jsonl n'est jamais réécrit
        f.write(event.model_dump_json() + "\n")


CSS = """
body{font:16px/1.5 system-ui,sans-serif;max-width:60rem;margin:0 auto;padding:1rem;color:#222}
.card{border:1px solid #bbb;border-radius:8px;padding:.5rem 1rem;margin:1rem 0}
.meta{color:#555;font-size:.9rem}
blockquote{margin:.5rem 0;padding:.5rem 1rem;background:#fffbe0;border-left:4px solid #d4a800;
white-space:pre-wrap}
table{border-collapse:collapse;font-size:.85rem}td,th{border:1px solid #ccc;padding:2px 8px}
.st{font-weight:bold}.machine_proposed{color:#a60}.validated{color:#070}.rejected{color:#a00}
.unresolved{color:#555}
"""


def render_inspect(
    links: list[Link],
    spans: dict[str, Span],
    artworks: dict[str, ArtworkRef],
    assets: dict[str, SourceAsset],
    statuses: dict[str, str],
    events: list[AnnotationEvent],
    surrogate: dict,
) -> str:
    out = [
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>Inspection des liens</title><style>{CSS}</style></head><body>",
        "<h1>Liaisons œuvre ↔ passage : inspection</h1>",
        f"<p class='meta'>Source : <a href='{escape(surrogate['publication_url'])}'>"
        f"{escape(surrogate['title'])}</a>, {escape(surrogate['author'])}, "
        f"{escape(surrogate['publisher'])}, {surrogate['year']}. Texte sous "
        f"<a href='{escape(surrogate['license_url'])}'>CC BY 4.0</a> (attribution requise). "
        "Aucune image incluse : droits d'image non vérifiés. Statuts : "
        "<em>machine_proposed</em> = règle de structure, non validé.</p>",
    ]
    by_art: dict[str, list[Link]] = {}
    for link in links:
        by_art.setdefault(link.artwork_id, []).append(link)
    for art_id, alinks in by_art.items():
        art = artworks[art_id]
        out.append(
            f"<section class='art' id='{escape(art_id)}'>"
            f"<h2>{escape(art.title)} <span class='meta'>({escape(art.catalogue_number)}, "
            f"inv. {escape(art.inventory_number)})</span></h2>"
            f"<p><a href='{escape(art.collection_url)}'>Page collection Getty</a> · "
            f"{len(alinks)} paragraphe(s) liés</p>"
        )
        labels: list[str] = []
        for lk in alinks:
            lab = spans[lk.span_id].section_label
            if lab not in labels:
                labels.append(lab)
        for label in labels:
            out.append(f"<h3>{escape(label)}</h3>")
            for link in (x for x in alinks if spans[x.span_id].section_label == label):
                out.append(_render_link(link, spans, assets, statuses, events, links))
        out.append("</section>")
    out.append("</body></html>")
    return "".join(out)


def _render_link(link, spans, assets, statuses, events, links) -> str:
    sp = spans[link.span_id]
    asset = assets[sp.asset_id]
    st = statuses.get(link.id, link.status)
    out = [f"<div class='card' id='{link.id}'>"]
    out.append(
        f"<p class='meta'>§{sp.paragraph_index + 1} · lien <code>{link.id}</code> · rôle "
        f"<code>{link.role}</code> · statut <span class='st {st}'>{st}</span> · offsets "
        f"[{sp.char_start}:{sp.char_end}] ({len(sp.text)} car.) du texte canonique de "
        f"<a href='{escape(asset.url)}'>{escape(asset.url)}</a> (sha256 {asset.sha256[:12]}…)"
    )
    if sp.notes:
        out.append(
            " · appels de note : " + ", ".join(f"[{n}]" for n in sp.notes) + " (texte des notes "
            "non inclus : « [n] » marque l'appel dans le passage)"
        )
    if sp.also_in:
        out.append(
            f" · passage partagé, reproduit aussi sur {len(sp.also_in)} autre(s) page(s), "
            f"{len(links_for(links, link.span_id))} œuvres liées"
        )
    out.append("</p>")
    out.append(f"<blockquote>{escape(sp.text)}</blockquote>")
    for ev in link.evidence:
        out.append(
            f"<p><strong>Preuve ({escape(ev.mechanism)}), intitulé « "
            f"{escape(ev.quoted_heading)} » :</strong> {escape(ev.explanation)}</p>"
        )
    for e in (e for e in events if e.link_id == link.id):
        out.append(
            f"<p class='meta'>{e.timestamp:%Y-%m-%d %H:%M} · {escape(e.annotator)} : "
            f"{e.before} → {e.after} — {escape(e.note)}</p>"
        )
    out.append(
        "<p class='meta'>Valider : <code>uv run lesternowak validate "
        f'{link.id} --status validated --note "…" --annotator VOTRE_NOM</code></p>'
    )
    out.append("<details><summary>Droits par usage</summary>")
    out.append("<table><tr><th>actif</th><th>action</th><th>décision</th><th>base</th></tr>")
    for r in link.rights:
        out.append(
            f"<tr><td>{r.asset}</td><td>{escape(r.action)}</td><td>{r.decision}</td>"
            f"<td>{escape(r.basis)} (<a href='{escape(r.evidence_url)}'>preuve</a>, "
            f"{r.checked_at:%Y-%m-%d})</td></tr>"
        )
    out.append("</table></details></div>")
    return "".join(out)


def links_for(links: list[Link], span_id: str) -> list[Link]:
    return [x for x in links if x.span_id == span_id]


def dump_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), "utf-8")
