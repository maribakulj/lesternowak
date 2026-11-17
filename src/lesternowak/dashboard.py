"""Tableau de bord qualité du corpus (lot C7) : une ligne par volume.

Lecture seule : slices (JSONL), file de revue et événements de décision (JSONL), configuration de
catalogue (YAML) pour le type et la langue. Le rapport ne contient que des identifiants, des comptes
et des statuts : aucun texte de document, aucun titre d'œuvre.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path

import yaml

CONFIG_DIR = Path("config/catalogues")
LINK_STATUSES = ("machine_proposed", "unresolved", "validated", "rejected")
PRECISION_RELATIONS = {"about", "group"}
NOT_MEASURED = "non mesuré"


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _config(volume: str) -> dict:
    p = CONFIG_DIR / f"{volume}.yaml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _corpus_key(slice_dir: Path, runs: list[dict]) -> str:
    params = runs[0].get("params", {}) if runs else {}
    return params.get("catalogue") or params.get("source") or slice_dir.name


def _text_decision(rights: list[dict], links: list[dict]) -> str:
    rows = [r for r in rights if r.get("asset") == "text"]
    if not rows:
        rows = [r for lk in links for r in lk.get("rights", []) if r.get("asset") == "text"]
    decisions = sorted({r["decision"] for r in rows})
    return "/".join(decisions) if decisions else "non décidé"


def _reusable(fig: dict) -> bool:
    dec = {r["action"]: r["decision"] for r in fig.get("image_rights", [])}
    return dec.get("publish_image") == "allow" and dec.get("redistribute_image") == "allow"


def _fmt_counter(c: Counter) -> str:
    return "; ".join(f"{k} {v}" for k, v in sorted(c.items())) or "—"


def volume_row(slice_dir: Path, queue: list[dict], events: list[dict] | None) -> dict:
    """Mesures d'un volume. `events` None : fichier d'événements absent (non mesuré)."""
    runs = _read(slice_dir / "runs.jsonl")
    key = _corpus_key(slice_dir, runs)
    cfg = _config(key)
    links = _read(slice_dir / "links.jsonl")
    spans = _read(slice_dir / "spans.jsonl")
    artworks = _read(slice_dir / "artworks.jsonl")
    figures = _read(slice_dir / "figures.jsonl")
    rights = _read(slice_dir / "rights.jsonl")

    mech: Counter = Counter()
    for lk in links:
        mech.update({e["mechanism"] for e in lk.get("evidence", [])})
    status = Counter(lk["status"] for lk in links)

    resolved = [a for a in artworks if (a.get("resolution") or {}).get("status") == "resolved"]
    res_mech = Counter(a["resolution"].get("mechanism") for a in resolved)
    cc0_ids = {
        r.get("artwork_id")
        for r in _read(slice_dir / "resolutions.jsonl")
        if r.get("image_license") == "cc0"
    }
    cc0 = sum(1 for a in resolved if a["id"] in cc0_ids)

    items = [i for i in queue if i.get("corpus") == key]
    blind_items = [i for i in items if i.get("blind")]
    row = {
        "volume": key,
        "type": cfg.get("type", "non déclaré"),
        "langue": cfg.get("language", "non déclarée"),
        "droits_texte": _text_decision(rights, links),
        "notices": len(artworks),
        "spans": len(spans),
        "status": {s: status.get(s, 0) for s in LINK_STATUSES},
        "status_autres": sum(v for k, v in status.items() if k not in LINK_STATUSES),
        "mecanismes": mech,
        "spans_faible_qualite": sum(1 for s in spans if s.get("quality_flag")),
        "figures": len(figures),
        "figures_reutilisables": sum(1 for f in figures if _reusable(f)),
        "resolues": len(resolved),
        "resolues_mecanisme": res_mech,
        "resolues_cc0": cc0,
        "file": len(items),
        "file_aveugles": len(blind_items),
        "verifies": NOT_MEASURED,
        "precision": NOT_MEASURED,
        "temps_moyen_s": NOT_MEASURED,
    }
    if events is not None:
        last: dict[str, dict] = {}
        for ev in sorted(events, key=lambda e: e["timestamp"]):
            if ev.get("item_id"):
                last[ev["item_id"]] = ev
        ids = {i["item_id"] for i in items}
        done = [e for k, e in last.items() if k in ids]
        blind_done = [e for e in done if e.get("blind")]
        row["verifies"] = len(done)
        if blind_done:
            ok = sum(1 for e in blind_done if e.get("relation") in PRECISION_RELATIONS)
            row["precision"] = f"{ok / len(blind_done):.3f} (n={len(blind_done)})"
        times = [e["elapsed_ms"] for e in done if e.get("elapsed_ms") is not None]
        if times:
            row["temps_moyen_s"] = f"{sum(times) / len(times) / 1000:.1f}"
    return row


def render(rows: list[dict], report_date: date, sources: Iterable[str]) -> str:
    lines = [
        f"# Tableau de bord du corpus, {report_date.isoformat()}",
        "",
        "Lot C7 (`docs/PLAN_CORPUS.md`). Comptes et statuts seulement : aucun texte de document.",
        "« non mesuré » : aucun événement de décision enregistré pour la mesure concernée.",
        "",
        "Sources : " + ", ".join(sources),
        "",
        "## Identification et structure",
        "",
        "| Volume | Type | Langue | Droits texte | Notices / œuvres | Spans "
        "| Spans faible qualité |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['volume']} | {r['type']} | {r['langue']} | {r['droits_texte']} | "
            f"{r['notices']} | {r['spans']} | {r['spans_faible_qualite']} |"
        )
    tot_notices = sum(r["notices"] for r in rows)
    tot_spans = sum(r["spans"] for r in rows)
    tot_low = sum(r["spans_faible_qualite"] for r in rows)
    lines.append(f"| **Total** | | | | {tot_notices} | {tot_spans} | {tot_low} |")

    lines += [
        "",
        "## Liens, figures, résolutions et revue",
        "",
        "| Volume | machine_proposed | unresolved | validated | rejected "
        "| autres statuts | Mécanismes de preuve | Figures (réutilisables) | Résolues E0/E2 "
        "| Part CC0 |",
        "|---|---:|---:|---:|---:|---:|---|---:|---|---|",
    ]
    for r in rows:
        st = r["status"]
        share = f"{r['resolues_cc0'] / r['resolues']:.0%}" if r["resolues"] else "—"
        lines.append(
            f"| {r['volume']} | {st['machine_proposed']} | {st['unresolved']} | "
            f"{st['validated']} | {st['rejected']} | {r['status_autres']} | "
            f"{_fmt_counter(r['mecanismes'])} | {r['figures']} ({r['figures_reutilisables']}) | "
            f"{_fmt_counter(r['resolues_mecanisme'])} ({r['resolues']}) | {share} |"
        )
    tot = {k: sum(r["status"][k] for r in rows) for k in LINK_STATUSES}
    tot_res = sum(r["resolues"] for r in rows)
    tot_cc0 = sum(r["resolues_cc0"] for r in rows)
    tot_share = f"{tot_cc0 / tot_res:.0%}" if tot_res else "—"
    tot_fig = sum(r["figures"] for r in rows)
    tot_reu = sum(r["figures_reutilisables"] for r in rows)
    tot_autres = sum(r["status_autres"] for r in rows)
    lines.append(
        f"| **Total** | {tot['machine_proposed']} | {tot['unresolved']} | {tot['validated']} | "
        f"{tot['rejected']} | {tot_autres} | | {tot_fig} ({tot_reu}) | {tot_res} | {tot_share} |"
    )

    lines += [
        "",
        "## Revue et précision",
        "",
        "| Volume | Éléments de revue | Dont aveugles | Éléments vérifiés | Précision "
        "(aveugles) | Temps moyen (s) |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['volume']} | {r['file']} | {r['file_aveugles']} | {r['verifies']} | "
            f"{r['precision']} | {r['temps_moyen_s']} |"
        )
    tot_file = sum(r["file"] for r in rows)
    tot_blind = sum(r["file_aveugles"] for r in rows)
    lines.append(f"| **Total** | {tot_file} | {tot_blind} | | | |")
    lines += [
        "",
        "Précision (aveugles) : part des éléments aveugles décidés dont la relation humaine "
        "confirme la proposition machine (`about` ou `group`).",
        "",
    ]
    return "\n".join(lines)


def build_report(
    slices: list[Path],
    events_path: Path,
    queue_path: Path,
    out: Path,
    report_date: date,
) -> dict:
    queue = _read(queue_path)
    events = _read(events_path) if events_path.exists() else None
    rows = [volume_row(s, queue, events) for s in slices]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rows, report_date, [str(s) for s in slices]), encoding="utf-8")
    return {"volumes": len(rows), "events": events is not None, "out": str(out)}
