"""Interface en ligne de commande.

Étape 2 : `slice getty-terracottas` produit les liens et la page d'inspection ;
`validate` ajoute un événement d'annotation humain (append-only).
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from lesternowak import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lesternowak",
        description=(
            "Extrait de publications d'histoire de l'art numérisées des liaisons "
            "œuvre ↔ passage analytique authentique, avec preuve et droits par usage."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    sl = sub.add_parser("slice", help="tranche verticale sur un catalogue")
    sl.add_argument("source", choices=["getty-terracottas"])
    sl.add_argument("--entries", type=int, nargs="+", required=True)
    sl.add_argument("--out", type=Path, default=Path("data/slice"))
    sl.add_argument("--cache", type=Path, default=Path("data/raw"))
    va = sub.add_parser("validate", help="enregistrer une décision humaine (append-only)")
    va.add_argument("link_id")
    va.add_argument("--status", required=True, choices=["validated", "rejected", "unresolved"])
    va.add_argument("--note", required=True)
    va.add_argument("--annotator", required=True)
    va.add_argument("--events", type=Path, default=Path("data/slice/events.jsonl"))
    return parser


def cmd_slice(args) -> int:
    from lesternowak import export
    from lesternowak import getty_quire as gq

    data, data_asset, pages = gq.fetch_entries(args.entries, args.cache)
    run = gq.make_run(args.entries)
    entries = {n: (page, asset) for n, (page, asset) in pages.items()}
    rec = gq.build_records(entries, data, run, run.started_at)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    assets = [a for _, a in pages.values()] + [data_asset]
    surrogate = gq.Surrogate(captured_at=run.started_at, **gq.SURROGATE)
    export.write_jsonl(out / "links.jsonl", rec["links"])
    export.write_jsonl(out / "spans.jsonl", rec["spans"])
    export.write_jsonl(out / "artworks.jsonl", rec["artworks"])
    export.write_jsonl(out / "assets.jsonl", assets)
    export.write_jsonl(out / "runs.jsonl", [run])
    export.dump_json(out / "surrogate.json", surrogate.model_dump())
    rights = [r for lk in rec["links"] for r in lk.rights]
    export.write_jsonl(
        out / "rights.jsonl", list({r.model_dump_json(): r for r in rights}.values())
    )
    events = export.read_jsonl(out / "events.jsonl", gq.AnnotationEvent)
    statuses = gq.current_statuses(rec["links"], events)
    page = export.render_inspect(
        rec["links"],
        {s.id: s for s in rec["spans"]},
        {a.id: a for a in rec["artworks"]},
        {a.id: a for a in assets},
        statuses,
        events,
        surrogate.model_dump(mode="json"),
    )
    (out / "inspect.html").write_text(page, encoding="utf-8")
    print(f"{len(rec['links'])} liens, {len(rec['spans'])} passages -> {out}/inspect.html")
    return 0


def cmd_validate(args) -> int:
    from lesternowak import export
    from lesternowak.getty_quire import current_statuses
    from lesternowak.models import AnnotationEvent, Link, LinkStatus

    links = export.read_jsonl(args.events.parent / "links.jsonl", Link)
    events = export.read_jsonl(args.events, AnnotationEvent)
    current = current_statuses(links, events)
    if args.link_id not in current:
        print(f"lien inconnu : {args.link_id}")
        return 2
    ev = AnnotationEvent(
        link_id=args.link_id,
        before=current[args.link_id],
        after=LinkStatus(args.status),
        annotator=args.annotator,
        note=args.note,
        timestamp=datetime.now(UTC),
    )
    export.append_event(args.events, ev)
    print(json.dumps({"link_id": ev.link_id, "before": ev.before, "after": ev.after}))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "slice":
        return cmd_slice(args)
    if args.command == "validate":
        return cmd_validate(args)
    parser.print_help()
    return 0
