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
    sh = sub.add_parser("annotation-sheet", help="feuille d'annotation CSV (UTF-8 avec BOM)")
    sh.add_argument("--slice", type=Path, default=Path("data/slice"))
    sh.add_argument("--out", type=Path, required=True)
    sh.add_argument("--sample", type=int, default=None, help="tirage de N spans (à l'aveugle)")
    sh.add_argument("--seed", type=int, default=0)
    im = sub.add_parser("annotation-import", help="importer une feuille remplie en gold JSONL")
    im.add_argument("--sheet", type=Path, required=True)
    im.add_argument("--annotator", required=True)
    im.add_argument("--out", type=Path, required=True)
    im.add_argument("--slice", type=Path, default=Path("data/slice"))
    im.add_argument("--force", action="store_true")
    ev = sub.add_parser("eval", help="mesurer des liens prédits contre un gold")
    ev.add_argument("--gold", type=Path, required=True)
    ev.add_argument("--pred", type=Path, default=Path("data/slice/links.jsonl"))
    ev.add_argument("--spans", type=Path, default=Path("data/slice/spans.jsonl"))
    ev.add_argument("--name", required=True)
    ev.add_argument("--out", type=Path, required=True)
    ag = sub.add_parser("agreement", help="accord brut et kappa entre deux gold")
    ag.add_argument("--a", type=Path, required=True)
    ag.add_argument("--b", type=Path, required=True)
    return parser


def cmd_annotation_sheet(args) -> int:
    from lesternowak import annotation as an

    sl = an.load_slice(args.slice)
    header, rows = an.build_sheet_rows(sl, args.sample, args.seed)
    an.write_sheet(args.out, header, rows)
    print(f"{len(rows)} lignes -> {args.out}")
    return 0


def cmd_annotation_import(args) -> int:
    from lesternowak import annotation as an

    if args.out.exists() and not args.force:
        print(f"{args.out} existe déjà : --force pour écraser")
        return 2
    sl = an.load_slice(args.slice)
    try:
        records, rep = an.import_sheet(args.sheet, sl, args.annotator)
    except an.ImportError_ as e:
        print(f"import refusé : {e}")
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(r.model_dump_json() + "\n" for r in records), encoding="utf-8")
    print(json.dumps(rep) + f" -> {args.out}")
    return 0


def cmd_eval(args) -> int:
    from lesternowak import evaluation as evl
    from lesternowak.export import dump_json, read_jsonl
    from lesternowak.models import Link, Span

    spans = {s.id: s for s in read_jsonl(args.spans, Span)}
    m = evl.evaluate(evl.read_gold(args.gold), read_jsonl(args.pred, Link), spans, args.name)
    args.out.mkdir(parents=True, exist_ok=True)
    dump_json(args.out / "metrics.json", m)
    (args.out / "report.md").write_text(evl.render_report(m), encoding="utf-8")
    print(f"rapport -> {args.out}")
    return 0


def cmd_agreement(args) -> int:
    from lesternowak import evaluation as evl

    r = evl.agreement(evl.read_gold(args.a), evl.read_gold(args.b))
    print(json.dumps(r, indent=2))
    return 0


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
    handlers = {
        "annotation-sheet": cmd_annotation_sheet,
        "annotation-import": cmd_annotation_import,
        "eval": cmd_eval,
        "agreement": cmd_agreement,
    }
    if args.command in handlers:
        return handlers[args.command](args)
    parser.print_help()
    return 0
