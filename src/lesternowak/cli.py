"""Interface en ligne de commande.

Étape 2 : `slice getty-terracottas` produit les liens et la page d'inspection ;
`validate` ajoute un événement d'annotation humain (append-only).
"""

from __future__ import annotations

import argparse
import json
import sys
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
    rb = sub.add_parser(
        "ref-build", help="construire un référentiel local (data/ref/<source>.jsonl)"
    )
    rb.add_argument("source", choices=["met", "louvre"])
    rb.add_argument("--department", default="European Paintings")
    rb.add_argument("--limit", type=int, default=500)
    rb.add_argument("--out", type=Path, default=Path("data/ref"))
    ev = sub.add_parser("eval", help="mesurer des liens prédits contre un gold")
    ev.add_argument("--gold", type=Path, required=True)
    ev.add_argument("--pred", type=Path, default=Path("data/slice/links.jsonl"))
    ev.add_argument("--spans", type=Path, default=Path("data/slice/spans.jsonl"))
    ev.add_argument("--name", required=True)
    ev.add_argument("--out", type=Path, required=True)
    bd = sub.add_parser("build", help="volume -> slice (config de catalogue, voie Gallica ALTO)")
    bd.add_argument("--catalogue", type=Path, required=True)
    bd.add_argument("--out", type=Path, required=True)
    bd.add_argument("--cache", type=Path, default=Path("data/raw/gallica"))
    qb = sub.add_parser("quire", help="publication Getty Quire -> slice (config de catalogue)")
    qb.add_argument("--catalogue", type=Path, required=True)
    qb.add_argument("--out", type=Path, required=True)
    qb.add_argument("--cache", type=Path, default=Path("data/raw/quire"))
    ib = sub.add_parser("ia-build", help="volume Internet Archive (djvu.xml) -> slice")
    ib.add_argument("--catalogue", type=Path, required=True)
    ib.add_argument("--out", type=Path, required=True)
    ib.add_argument("--cache", type=Path, default=Path("data/raw/ia"))
    ib.add_argument("--ref-dir", type=Path, default=Path("data/ref"))
    rq = sub.add_parser("review-queue", help="file de vérification (pilote C6)")
    rq.add_argument("--slice", type=Path, default=Path("data/slice"))
    rq.add_argument("--adapter", default="getty-terracottas")
    rq.add_argument(
        "--extra",
        action="append",
        default=[],
        metavar="ADAPTER=DIR",
        help="slice supplémentaire (file combinée), répétable",
    )
    rq.add_argument("--out", type=Path, default=Path("data/review/queue.jsonl"))
    rq.add_argument("--blind-rate", type=float, default=0.15)
    rq.add_argument("--seed", type=int, default=7)
    db = sub.add_parser(
        "dashboard", help="tableau de bord qualité par volume (lot C7, lecture seule)"
    )
    db.add_argument("--slices", type=Path, nargs="+", required=True)
    db.add_argument("--events", type=Path, default=Path("data/review/events.jsonl"))
    db.add_argument("--queue", type=Path, default=Path("data/review/queue-all.jsonl"))
    db.add_argument("--out", type=Path, default=None)
    rs = sub.add_parser("review-serve", help="serveur local de vérification (127.0.0.1)")
    rs.add_argument("--queue", type=Path, default=Path("data/review/queue.jsonl"))
    rs.add_argument("--events", type=Path, default=Path("data/review/events.jsonl"))
    rs.add_argument("--port", type=int, default=8765)
    rs.add_argument("--host", default="127.0.0.1")
    rs.add_argument("--allow-remote", action="store_true", help="autoriser un hôte non local")
    rs.add_argument("--annotator", required=True)
    rx = sub.add_parser("review-export", help="gold (sans texte) depuis les décisions")
    rx.add_argument("--queue", type=Path, required=True)
    rx.add_argument("--events", type=Path, required=True)
    rx.add_argument("--out", type=Path, required=True)
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


def cmd_review_queue(args) -> int:
    from lesternowak import review

    specs = [(args.adapter, args.slice)]
    for x in args.extra:
        name, _, d = x.partition("=")
        specs.append((name, Path(d)))
    items = review.make_combined_queue(specs, args.blind_rate, args.seed)
    review.write_queue(args.out, items)
    nb = sum(i.blind for i in items)
    print(f"{len(items)} éléments dont {nb} à l'aveugle -> {args.out}")
    return 0


def cmd_dashboard(args) -> int:
    from datetime import date

    from lesternowak import dashboard

    out = args.out or Path("reports/corpus") / f"{date.today().isoformat()}.md"
    rep = dashboard.build_report(args.slices, args.events, args.queue, out, date.today())
    print(json.dumps(rep, ensure_ascii=False))
    return 0


def cmd_review_serve(args) -> int:
    from lesternowak import review

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(
            f"ATTENTION : {args.host} expose le serveur au réseau, sans authentification.",
            file=sys.stderr,
        )
        if not args.allow_remote:
            print("refusé : ajouter --allow-remote pour l'accepter", file=sys.stderr)
            return 2
    srv = review.make_server(args.queue, args.events, args.annotator, args.host, args.port)
    print(f"http://{args.host}:{srv.server_address[1]}/ (Ctrl+C pour arrêter)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


def cmd_review_export(args) -> int:
    from lesternowak import review

    n = review.export_gold(args.queue, args.events, args.out)
    print(f"{n} enregistrements gold -> {args.out}")
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


def cmd_build(args) -> int:
    from lesternowak import catalogue as cat
    from lesternowak.gallica import GallicaClient, GallicaStop
    from lesternowak.referentials import iter_cache

    cfg = cat.load_config(args.catalogue)
    refs = list(iter_cache(cfg.referential)) if cfg.referential else None
    client = GallicaClient(cache_root=args.cache)
    try:
        report = cat.build_volume(cfg, client, args.out, ref_index=refs or None)
    except GallicaStop as e:
        print(f"ARRÊT Gallica : {e}", file=sys.stderr)
        return 3
    print(json.dumps(report, ensure_ascii=False))
    return 0


def cmd_ia_build(args) -> int:
    from lesternowak import ia_djvu
    from lesternowak.referentials import iter_cache

    cfg = ia_djvu.load_ia_config(args.catalogue)
    refs = list(iter_cache(cfg.referential, args.ref_dir)) if cfg.referential else None
    client = ia_djvu.IAClient(cache_root=args.cache)
    try:
        report = ia_djvu.build_ia_volume(cfg, client, args.out, refs=refs or None)
    except ia_djvu.IAStop as e:
        print(f"ARRÊT Internet Archive : {e}", file=sys.stderr)
        return 3
    print(json.dumps(report, ensure_ascii=False))
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


def cmd_ref_build(args: argparse.Namespace) -> int:
    from lesternowak import referentials

    if args.source == "met":
        stats = referentials.build_met(args.department, cache_dir=args.out)
    else:
        stats = referentials.build_louvre(limit=args.limit, cache_dir=args.out)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "slice":
        return cmd_slice(args)
    if args.command == "build":
        return cmd_build(args)
    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "quire":
        from lesternowak import quire

        print(json.dumps(quire.run_build(args.catalogue, args.out, args.cache), ensure_ascii=False))
        return 0
    if args.command == "ia-build":
        return cmd_ia_build(args)
    handlers = {
        "annotation-sheet": cmd_annotation_sheet,
        "annotation-import": cmd_annotation_import,
        "eval": cmd_eval,
        "agreement": cmd_agreement,
        "review-queue": cmd_review_queue,
        "review-serve": cmd_review_serve,
        "dashboard": cmd_dashboard,
        "review-export": cmd_review_export,
        "ref-build": cmd_ref_build,
    }
    if args.command in handlers:
        return handlers[args.command](args)
    parser.print_help()
    return 0
