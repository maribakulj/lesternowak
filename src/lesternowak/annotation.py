"""Feuille d'annotation (CSV) et import vers un gold versionné (identifiants + étiquettes)."""

from __future__ import annotations

import csv
import hashlib
import io
import random
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from lesternowak.export import read_jsonl
from lesternowak.models import (
    GOLD_FUNCTIONS,
    ArtworkRef,
    Link,
    Relation,
    SourceAsset,
    Span,
)

FIXED_COLS = ["span_id", "section", "paragraph_index", "group", "source_url", "candidates", "text"]
TAIL_COLS = ["function", "note"]
NOT_CANDIDATE = "-"


class GoldRecord(BaseModel):
    """Une étiquette de référence : aucun texte, seulement des identifiants."""

    span_id: str
    artwork_id: str
    relation: Relation
    function: str
    annotator: str
    annotated_at: str
    note: str
    sheet_sha256: str


class SliceData(BaseModel):
    spans: list[Span]
    artworks: list[ArtworkRef]
    links: list[Link]
    assets: list[SourceAsset]


def load_slice(path: Path) -> SliceData:
    return SliceData(
        spans=read_jsonl(path / "spans.jsonl", Span),
        artworks=read_jsonl(path / "artworks.jsonl", ArtworkRef),
        links=read_jsonl(path / "links.jsonl", Link),
        assets=read_jsonl(path / "assets.jsonl", SourceAsset),
    )


def cat_number(art: ArtworkRef) -> int:
    m = re.search(r"(\d+)", art.catalogue_number)
    if not m:
        raise ValueError(f"numéro de catalogue illisible : {art.catalogue_number!r}")
    return int(m.group(1))


def _ordered_artworks(sl: SliceData) -> list[ArtworkRef]:
    return sorted(sl.artworks, key=cat_number)


def build_sheet_rows(
    sl: SliceData, sample: int | None = None, seed: int = 0
) -> tuple[list[str], list[list[str]]]:
    arts = _ordered_artworks(sl)
    rel_cols = [f"relation_cat{cat_number(a)}" for a in arts]
    header = [*FIXED_COLS, *rel_cols, *TAIL_COLS]
    cands: dict[str, set[str]] = {}
    for lk in sl.links:
        cands.setdefault(lk.span_id, set()).add(lk.artwork_id)
    assets = {a.id: a for a in sl.assets}
    spans = [s for s in sl.spans if s.id in cands]
    if sample is not None:
        rng = random.Random(seed)
        chosen = set(rng.sample(sorted(s.id for s in spans), min(sample, len(spans))))
        spans = [s for s in spans if s.id in chosen]
    rows = []
    for s in spans:
        c = cands[s.id]
        cell = [("" if a.id in c else NOT_CANDIDATE) for a in arts]
        labels = ", ".join(a.catalogue_number for a in arts if a.id in c)
        rows.append(
            [
                s.id,
                s.section_label,
                str(s.paragraph_index),
                s.group_title or "",
                assets[s.asset_id].url,
                labels,
                s.text,
                *cell,
                "",
                "",
            ]
        )
    return header, rows


def write_sheet(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class ImportError_(ValueError):
    pass


def import_sheet(sheet: Path, sl: SliceData, annotator: str, now: datetime | None = None):
    """Retourne (records, rapport). Lève ImportError_ à la première invalidité."""
    raw = sheet.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    now = now or datetime.now(UTC)
    arts = {f"relation_cat{cat_number(a)}": a for a in sl.artworks}
    spans = {s.id: s for s in sl.spans}
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    missing = [c for c in [*FIXED_COLS, *TAIL_COLS, *arts] if c not in (reader.fieldnames or [])]
    if missing:
        raise ImportError_(f"colonnes absentes : {missing}")
    valid_rel = {r.value for r in Relation}
    valid_fn = {f.value for f in GOLD_FUNCTIONS}
    records: list[GoldRecord] = []
    rep = {"rows": 0, "rows_ignored": 0, "pairs": 0, "pairs_skipped": 0}
    seen: set[str] = set()
    for n, row in enumerate(reader, start=2):
        rep["rows"] += 1
        sid = (row["span_id"] or "").strip()
        if sid not in spans:
            raise ImportError_(f"ligne {n} : span_id inconnu {sid!r}")
        if sid in seen:
            raise ImportError_(f"ligne {n} : span_id en double {sid!r}")
        seen.add(sid)
        short = [c for c in [*FIXED_COLS, *TAIL_COLS, *arts] if row.get(c) is None]
        if short:
            raise ImportError_(f"ligne {n} : ligne tronquée (cellules absentes : {short})")
        if row["text"] != spans[sid].text:
            raise ImportError_(f"ligne {n} : texte différent du span {sid} (modifié ?)")
        fn = (row["function"] or "").strip()
        rels = {}
        for col, art in arts.items():
            v = (row[col] or "").strip()
            if v in ("", NOT_CANDIDATE):
                continue
            if v not in valid_rel:
                raise ImportError_(f"ligne {n}, {col} : relation invalide {v!r}")
            rels[art.id] = v
        if fn and fn not in valid_fn:
            raise ImportError_(f"ligne {n} : fonction invalide {fn!r}")
        if not rels and not fn:
            rep["rows_ignored"] += 1
            continue
        if fn and not rels:
            raise ImportError_(f"ligne {n} : fonction renseignée sans aucune relation")
        if rels and not fn:
            raise ImportError_(f"ligne {n} : relations renseignées sans fonction")
        for art_id, v in rels.items():
            records.append(
                GoldRecord(
                    span_id=sid,
                    artwork_id=art_id,
                    relation=Relation(v),
                    function=fn,
                    annotator=annotator,
                    annotated_at=now.isoformat(),
                    note=(row["note"] or "").strip(),
                    sheet_sha256=sha,
                )
            )
            rep["pairs"] += 1
    # couples candidats laissés vides dans une ligne partiellement remplie
    done = {(r.span_id, r.artwork_id) for r in records}
    touched = {r.span_id for r in records}
    rep["pairs_skipped"] = sum(
        1 for lk in sl.links if lk.span_id in touched and (lk.span_id, lk.artwork_id) not in done
    )
    return records, rep
