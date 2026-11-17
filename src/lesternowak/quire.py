"""Lecteur Getty Quire générique, piloté par `config/catalogues/<id>.yaml` (lot C8).

Deux types de pages, déclarés par la configuration :
- `essays` : spans par paragraphe, figures (image + légende), appels « fig. N » ;
- `catalogue_entries` : page d'entrée d'un objet (règle E1), sections analytiques listées.

Preuves : un paragraphe qui contient un appel de figure (ancre `#fig…`) est relié à l'objet de la
figure (E0 vers la figure) ; un paragraphe sans appel n'est pas relié (abstention) mais reste un
span. L'objet local d'une figure est lu dans sa légende (musée, numéro d'inventaire tel
qu'imprimé). Résolution externe : E0 sur numéro d'accession seulement si le musée cité est le Met
et que l'accession est trouvée, de façon unique, dans `data/ref/met.jsonl` ; sinon `unresolved`.
Aucun texte n'est produit par un modèle ; chaque offset est vérifié à la construction.
"""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import yaml
from lxml import html as lxml_html

from lesternowak.getty_quire import (
    IMAGE_ACTIONS,
    TEXT_ACTIONS,
    fetch_cached,
    git_version,
)
from lesternowak.models import (
    ArtworkRef,
    Decision,
    Evidence,
    FigureCall,
    Link,
    LinkStatus,
    Occurrence,
    PassageFunction,
    QuireFigure,
    Resolution,
    RightsDecision,
    Run,
    SourceAsset,
    Span,
)

_RANK = {Decision.deny: 0, Decision.unknown: 1, Decision.conditional: 2, Decision.allow: 3}
_ROLES = {r.value: r for r in PassageFunction}


@dataclass
class QuireConfig:
    id: str
    root_url: str
    title: str
    type: str  # essays | catalogue_entries (type par défaut des pages)
    include: list[str]
    exclude: list[str] = field(default_factory=list)
    entry_pages: str | None = None  # motif des pages d'entrée (sinon `type` s'applique)
    sections: dict[str, PassageFunction] = field(default_factory=dict)
    text_license: str = ""
    text_flags: list[str] = field(default_factory=list)
    rights_url: str = ""
    figures_mode: str = "unknown"  # unknown | listed_licensed | listed_excluded
    figures_listed: list[str] = field(default_factory=list)
    figures_license: str = ""
    referential: str | None = None
    cache: str = "data/raw/quire"


def load_config(path: Path) -> QuireConfig:
    d = yaml.safe_load(path.read_text("utf-8"))
    pg, rt, fg = d["pages"], d["rights"], d["rights"].get("figures", {})
    return QuireConfig(
        id=d["id"],
        root_url=d["root_url"],
        title=d["title"],
        type=d["type"],
        include=pg["include"],
        exclude=pg.get("exclude", []),
        entry_pages=pg.get("entry_pages"),
        sections={k: _ROLES[v] for k, v in (d.get("sections") or {}).items()},
        text_license=rt["text"]["license"],
        text_flags=rt["text"].get("flags", []),
        rights_url=rt["url"],
        figures_mode=fg.get("mode", "unknown"),
        figures_listed=[str(k) for k in fg.get("listed", [])],
        figures_license=fg.get("license", ""),
        referential=d.get("referential"),
    )


def toc_pages(root_html: bytes, cfg: QuireConfig) -> list[str]:
    """Pages de la table des matières (liens `./…/` de la page racine), filtrées par la config."""
    seen: list[str] = []
    for a in lxml_html.fromstring(root_html).xpath("//a[@href]"):
        href = a.get("href")
        if not href.startswith("./") or not href.endswith("/"):
            continue
        path = href[2:]
        if path in seen or not any(re.search(p, path) for p in cfg.include):
            continue
        if any(re.search(p, path) for p in cfg.exclude):
            continue
        seen.append(path)
    return seen


# --- extraction ---------------------------------------------------------------------------------


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def fig_key(s: str) -> str:
    """« fig_1_5 » / « fig-1-5 » / « 17.4a » -> « 1.5 » / « 17.4a »."""
    return ".".join(re.findall(r"\d+[a-z]?", re.sub(r"[_-]([a-z])$", r"\1", s)))


def _drop_hidden(el) -> None:
    for n in el.xpath(
        './/*[contains(@class,"quire-citation__content") or contains(@class,"visually-hidden")]'
    ):
        n.drop_tree()


def paragraph(el, figure_ids: set[str]) -> tuple[str, list[int], list[FigureCall]]:
    """Texte exact d'un <p> : notes -> « [n] », contenu masqué (glossaire) ignoré, appels de
    figure repérés par leurs ancres (offsets relatifs au texte retourné)."""
    el = copy.deepcopy(el)
    _drop_hidden(el)
    notes: list[int] = []
    for sup in el.xpath(".//sup"):
        label = _clean(sup.text_content())
        if label.isdigit():
            notes.append(int(label))
            for child in list(sup):
                sup.remove(child)
            sup.text = f"[{label}]"
        else:
            sup.drop_tree()
    targets = []
    for a in el.xpath('.//a[starts-with(@href,"#fig")]'):
        targets.append(a.get("href")[1:])
        label = a.text_content()
        for child in list(a):
            a.remove(child)
        a.text = f"\ue000{label}\ue001"
    raw = _clean(el.text_content())
    out, starts, calls = [], [], []
    pos = 0
    for ch in raw:
        if ch == "\ue000":
            starts.append(pos)
        elif ch == "\ue001":
            s = starts.pop()
            txt = "".join(out)
            calls.append((txt[s:pos], s, pos))
        else:
            out.append(ch)
            pos += 1
    text = "".join(out)
    result = []
    for (label, s, e), fid in zip(calls, targets, strict=True):
        if fid in figure_ids and label.strip():
            result.append(FigureCall(label=label, char_start=s, char_end=e, figure_id=fid))
    return text, notes, result


class RawFigure:
    def __init__(self, img_id, label, image_url, caption):
        self.img_id, self.label, self.image_url, self.caption = img_id, label, image_url, caption
        self.key = fig_key(img_id)


_DIMS = re.compile(
    r"(?:\b[HWLD]\w{0,5}\.?:?\s*)?\d+(?:\.\d+)?(?:\s*[x×]\s*\d+(?:\.\d+)?)*\s*cm",
    re.IGNORECASE,
)
_INV = re.compile(
    r"^(?:(?:inv|no|acc)\.?\s*)?(?:[A-Z\u00c6]{1,5}[ .]?)?\d[\w.\-/,]*(?: and [\w.\-/]+)?$",
    re.IGNORECASE,
)
# fin de la phrase « lieu de conservation » : avant un crédit (©, Image:, Photo:) ou une majuscule
_SENTENCE = re.compile(
    r"(?:(?<!Mrs)(?<!Mr)(?<!Dr)(?<!St)(?<!Jr)(?<!Inc)(?<!ca)(?<=[a-z0-9)])\. (?=[A-Z\u00a9])"
    r"|\s(?=\u00a9|Image:|Photo:))"
)
_LICENSE = re.compile(r"\b(CC0|CC BY(?:-NC)?(?: \d\.\d)?|public domain)\b", re.IGNORECASE)
_DERIVED = re.compile(
    r"^[^.]{0,60}\b(?:detail|view|close-up|section|photograph)\b[^.]{0,30}"
    r"\bfig(?:ure)?s?\.?\s*(\d+[.\-]\d+[a-z]?)",
    re.IGNORECASE,
)


def _content(root):
    return root.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " content ")]')[0]


def parse_figures(root, page_url: str) -> list[RawFigure]:
    out = []
    content = _content(root)
    for img in content.xpath('.//img[contains(@class,"quire-figure__image")]'):
        if not img.get("id"):
            continue
        fig = img.xpath("ancestor::figure[.//figcaption][1]")
        caption = ""
        if fig:
            cap = copy.deepcopy(fig[0].xpath(".//figcaption")[0])
            _drop_hidden(cap)
            caption = _clean(cap.text_content())
        label = img.xpath('../span/span[contains(@class,"quire-figure__label")]')
        lab = _clean(label[0].text_content()) if label else ""
        out.append(RawFigure(img.get("id"), lab, urljoin(page_url, img.get("src", "")), caption))
    return out


@dataclass
class CaptionObject:
    label: str  # première phrase de la légende, telle qu'imprimée
    museum: str | None
    inventory: str | None  # tel qu'imprimé


def caption_object(caption: str) -> CaptionObject | None:
    """Objet d'une légende descriptive (dimensions « NN x NN cm » présentes) ; sinon None."""
    ms = list(_DIMS.finditer(caption))
    if not ms:
        return None
    m, last = ms[0], ms[-1]
    head = caption[: m.start()]
    label = (head.rsplit(". ", 1)[0] if ". " in head else head).strip().rstrip(".")
    rest = re.sub(r"^\s*\([^)]*\)\s*\.?\s*", "", caption[last.end() :])
    rest = re.sub(r"\s*www\.[^\s,]+", "", rest.replace("\u200b", ""))
    loc = _SENTENCE.split(rest)[0].strip().rstrip(".")
    parts = [p.strip() for p in loc.split(", ") if p.strip() and not _LICENSE.fullmatch(p.strip())]
    if len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[-2]) and re.match(r"\d{4}", parts[-1]):
        parts[-2:] = [f"{parts[-2]},{parts[-1]}"]  # numéro à virgule (1994,0521.15)
    if len(parts) >= 2 and _INV.match(parts[-1]):
        return CaptionObject(label, ", ".join(parts[:-1]), parts[-1])
    return None  # sans musée ni inventaire imprimés : pas d'objet local (abstention)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# --- droits -------------------------------------------------------------------------------------


def text_rights(cfg: QuireConfig, checked_at: datetime) -> list[RightsDecision]:
    nc = "NC" in cfg.text_flags
    basis = f"{cfg.text_license}, attribution requise" + (
        " ; [NC] usage non commercial seulement" if nc else ""
    )
    return [
        RightsDecision(
            asset="text",
            action=a,
            decision=Decision.conditional if nc else Decision.allow,
            basis=basis,
            evidence_url=cfg.rights_url,
            checked_at=checked_at,
        )
        for a in TEXT_ACTIONS
    ]


def figure_rights(
    cfg: QuireConfig, fig: RawFigure, explicit: str | None, checked_at: datetime
) -> list[RightsDecision]:
    """`unknown` ne devient jamais `allow` : une figure n'est autorisée que si elle figure dans la
    liste des figures sous licence, n'est pas exclue, ou porte une licence ouverte explicite."""
    nc = "NC" in cfg.text_flags
    listed = fig.key in cfg.figures_listed
    if cfg.figures_mode == "listed_licensed" and listed:
        dec, basis = Decision.allow, f"figure listée sous {cfg.figures_license} (page copyright)"
    elif cfg.figures_mode == "listed_licensed":
        dec, basis = Decision.deny, "image exclue de la licence (page copyright) : droits réservés"
    elif cfg.figures_mode == "listed_excluded" and listed:
        dec, basis = Decision.deny, "figure exclue de la licence (page copyright) : droits réservés"
    elif cfg.figures_mode == "listed_excluded":
        dec, basis = Decision.allow, f"hors liste d'exclusions : {cfg.figures_license}"
    elif explicit and explicit.upper().startswith("CC BY"):
        dec, basis = Decision.allow, f"licence explicite dans la légende : {explicit}"
        nc = nc or "NC" in explicit.upper()
    else:
        dec, basis = Decision.unknown, "« except where otherwise noted » : figure non vérifiée"
    if dec == Decision.allow and nc:
        basis += " [NC] usage non commercial seulement"
    out = [
        RightsDecision(
            asset="images",
            action="display_pilot",
            decision=dec,
            basis=basis,
            evidence_url=cfg.rights_url,
            checked_at=checked_at,
        )
    ]
    reuse = Decision.conditional if (dec == Decision.allow and nc) else dec
    out += [
        RightsDecision(
            asset="images",
            action=a,
            decision=reuse,
            basis=basis,
            evidence_url=cfg.rights_url,
            checked_at=checked_at,
        )
        for a in IMAGE_ACTIONS
    ]
    return out


def _min_rights(groups: list[list[RightsDecision]]) -> list[RightsDecision]:
    best: dict[str, RightsDecision] = {}
    for g in groups:
        for r in g:
            if r.action not in best or _RANK[r.decision] < _RANK[best[r.action].decision]:
                best[r.action] = r
    return list(best.values())


# --- pages ----------------------------------------------------------------------------------------


@dataclass
class ParsedPage:
    path: str
    kind: str
    title: str
    canonical: str
    # (section, index, start, end, text, notes, calls)
    paragraphs: list[tuple]
    figures: list[RawFigure]


def parse_page(page: bytes, path: str, url: str, kind: str, cfg: QuireConfig) -> ParsedPage:
    root = lxml_html.fromstring(page)
    h1 = root.xpath('//h1[contains(@class,"quire-page__header__title")]')
    title = _clean(h1[0].text_content()) if h1 else path
    figs = parse_figures(root, url)
    fids = {f.img_id for f in figs}
    content = _content(root)
    canonical, paras = "", []
    section, idx, opened = "Body", 0, False
    for child in content:
        if child.tag == "h2":
            section, idx, opened = _clean(child.text_content()), 0, False
            continue
        if child.tag != "p":
            continue
        analytic = kind == "essays" or section in cfg.sections
        text, notes, calls = paragraph(child, fids)
        if not text or not analytic:
            continue
        if not opened:
            canonical += section + "\n"
            opened = True
        else:
            canonical += "\n\n"
        start = len(canonical)
        canonical += text
        paras.append((section, idx, start, len(canonical), text, notes, calls))
        idx += 1
    return ParsedPage(path, kind, title, canonical, paras, figs)


def page_kind(path: str, cfg: QuireConfig) -> str:
    if cfg.type == "catalogue_entries" or (cfg.entry_pages and re.search(cfg.entry_pages, path)):
        return "catalogue_entries"
    return "essays"


# --- résolution externe (E0, Met) -----------------------------------------------------------------


def met_index(root: Path = Path("data/ref")) -> dict[str, list]:
    from lesternowak.referentials import iter_cache

    idx: dict[str, list] = {}
    try:
        for r in iter_cache("met", root):
            if r.accession_number:
                idx.setdefault(_norm(r.accession_number), []).append(r)
    except FileNotFoundError:
        pass
    return idx


def resolve_object(co: CaptionObject | None, idx: dict[str, list]) -> tuple[Resolution, list]:
    if co is None or not co.inventory:
        return Resolution(status="unresolved", reason="légende sans numéro d'inventaire"), []
    if not co.museum or "metropolitan museum" not in co.museum.lower():
        return Resolution(
            status="unresolved", reason=f"objet hors Met ({co.museum}) : pas de référentiel"
        ), []
    hits = idx.get(_norm(co.inventory), [])
    if len(hits) != 1:
        why = "absent de data/ref/met.jsonl" if not hits else "plusieurs fiches"
        return Resolution(
            status="unresolved",
            reason=f"Met, accession {co.inventory} : {why}",
            candidates=[h.ref_id for h in hits],
        ), []
    h = hits[0]
    return Resolution(
        status="resolved",
        mechanism="E0",
        candidates=[h.ref_id],
        signals=[{"accession_number": co.inventory, "ref_id": h.ref_id}],
        reason="numéro d'accession imprimé dans la légende, trouvé (candidat unique)",
    ), hits


# --- construction ---------------------------------------------------------------------------


def fetch_pages(cfg: QuireConfig, cache: Path):
    root_html, root_asset = fetch_cached(cfg.root_url, cache, "text/html")
    paths = toc_pages(root_html, cfg)
    pages = {p: fetch_cached(urljoin(cfg.root_url, p), cache, "text/html") for p in paths}
    # page de droits : preuve consignée (non analysée ici, les listes sont dans la config)
    return paths, pages, root_asset


def build_records(
    cfg: QuireConfig,
    pages: dict[str, tuple[bytes, SourceAsset]],
    run: Run,
    checked_at: datetime,
    met: dict[str, list] | None = None,
) -> dict:
    met = met if met is not None else {}
    trights = text_rights(cfg, checked_at)
    artworks: dict[str, ArtworkRef] = {}
    figures: dict[str, QuireFigure] = {}
    spans: dict[str, Span] = {}
    links: list[Link] = []
    canon: dict[str, str] = {}
    stats = {"pages": 0, "calls": 0, "calls_unlinked": 0, "paragraphs": 0}
    for path, (page, asset) in pages.items():
        url = asset.url
        pp = parse_page(page, path, url, page_kind(path, cfg), cfg)
        canon[asset.id] = pp.canonical
        stats["pages"] += 1
        # --- objets locaux et figures de la page
        entry_art = None
        if pp.kind == "catalogue_entries":
            aid = f"{cfg.id}:{path.strip('/').replace('/', '-')}"
            entry_art = ArtworkRef(
                id=aid,
                title=pp.title,
                artwork_local_id=aid,
                local_label=pp.title,
                catalogue_number=pp.title.split(".")[0] if pp.title[:1].isdigit() else "",
                collection_url=url,
                resolution=Resolution(
                    status="unresolved", reason="entrée sans identifiant externe cité"
                ),
            )
            artworks[aid] = entry_art
        by_key = {f.key: f for f in pp.figures}
        objs: dict[str, tuple[CaptionObject | None, str, str]] = {}
        for f in pp.figures:
            if entry_art:
                objs[f.img_id] = (None, entry_art.id, "figure placée dans la page de l'entrée (E1)")
                continue
            co = caption_object(f.caption)
            if co:
                key = (
                    f"{cfg.id}:obj:{_sha(_norm(co.museum or '') + _norm(co.inventory))[:10]}"
                    if co.inventory
                    else f"{cfg.id}:fig:{f.key}"
                )
                objs[f.img_id] = (co, key, "légende descriptive : objet, musée et inventaire")
        for f in pp.figures:  # figures dérivées (« Detail of fig. 1.1 »)
            if f.img_id in objs:
                continue
            m = _DERIVED.match(f.caption)
            tgt = by_key.get(fig_key(m.group(1))) if m else None
            if tgt and tgt.img_id in objs and tgt is not f:
                objs[f.img_id] = (
                    None,
                    objs[tgt.img_id][1],
                    f"légende : « {f.caption[: m.end()]} » cite la figure {tgt.key}",
                )
        for f in pp.figures:
            lic = _LICENSE.search(f.caption)
            explicit = lic.group(1) if lic else None
            art_id = objs[f.img_id][1] if f.img_id in objs else None
            if art_id and art_id not in artworks:
                co = objs[f.img_id][0]
                res, hits = resolve_object(co, met)
                artworks[art_id] = ArtworkRef(
                    id=art_id,
                    title=co.label if co else f.caption,
                    inventory_number=co.inventory or "" if co else "",
                    artwork_local_id=art_id,
                    local_label=co.label if co else None,
                    collection_url=hits[0].collection_url if hits else "",
                    external_ids=[{"ref_id": h.ref_id} for h in hits],
                    resolution=res,
                )
            figures[f"{cfg.id}:{f.img_id}"] = QuireFigure(
                id=f"{cfg.id}:{f.img_id}",
                asset_id=asset.id,
                key=f.key,
                label=f.label,
                image_url=f.image_url,
                caption=f.caption,
                explicit_license=explicit,
                artwork_id=art_id,
                object_evidence=objs[f.img_id][2] if f.img_id in objs else "",
                image_rights=figure_rights(cfg, f, explicit, checked_at),
            )
        # --- spans et liens
        for section, idx, start, end, text, notes, calls in pp.paragraphs:
            stats["paragraphs"] += 1
            assert pp.canonical[start:end] == text and text, "offset invalide"
            for c in calls:
                assert text[c.char_start : c.char_end] == c.label, "offset d'appel invalide"
            sid = "spn_" + _sha(text)[:12]
            calls = [c.model_copy(update={"figure_id": f"{cfg.id}:{c.figure_id}"}) for c in calls]
            if sid in spans:
                if spans[sid].text != text:
                    raise AssertionError(f"collision de hachage {sid}")
                if spans[sid].asset_id != asset.id and not any(
                    o.asset_id == asset.id for o in spans[sid].also_in
                ):
                    spans[sid].also_in.append(
                        Occurrence(asset_id=asset.id, char_start=start, char_end=end)
                    )
            else:
                spans[sid] = Span(
                    id=sid,
                    asset_id=asset.id,
                    section_label=section,
                    paragraph_index=idx,
                    char_start=start,
                    char_end=end,
                    text=text,
                    notes=notes,
                    figure_calls=calls,
                )
            stats["calls"] += len(calls)
            by_art: dict[str, list] = {}
            for c in calls:
                fg = figures[c.figure_id]
                if fg.artwork_id is None:
                    stats["calls_unlinked"] += 1
                else:
                    by_art.setdefault(fg.artwork_id, []).append((c, fg))
            if entry_art and section in cfg.sections:
                role = cfg.sections[section]
                e1_figs = sorted({c.figure_id for c in calls if c.figure_id in figures})
                lid = "lnk_" + _sha(f"{entry_art.id}|{sid}|E1")[:12]
                links.append(
                    Link(
                        id=lid,
                        artwork_id=entry_art.id,
                        span_id=sid,
                        role=role,
                        evidence=[
                            Evidence(
                                mechanism="editorial_entry_structure",
                                quoted_heading=section,
                                explanation=(
                                    f"E1 : la page {path} est l'entrée « {pp.title} » ; le "
                                    f"paragraphe {idx + 1} de la section « {section} » est "
                                    "rattaché à cet objet."
                                ),
                            )
                        ],
                        status=LinkStatus.machine_proposed,
                        rights=trights + _min_rights([figures[i].image_rights for i in e1_figs]),
                        run_id=run.id,
                        figure_ids=e1_figs,
                    )
                )
            if entry_art and section in cfg.sections:
                by_art.pop(entry_art.id, None)  # déjà couvert par le lien E1 (mêmes figures)
            for art_id, cs in by_art.items():
                fids = sorted({fg.id for _, fg in cs})
                links.append(
                    Link(
                        id="lnk_" + _sha(f"{art_id}|{sid}|figure_call")[:12],
                        artwork_id=art_id,
                        span_id=sid,
                        role=PassageFunction.unclassified,
                        evidence=[
                            Evidence(
                                mechanism="figure_call",
                                quoted_heading=cs[0][0].label,
                                explanation=(
                                    "E0 vers la figure : le paragraphe appelle "
                                    + ", ".join(f"« {c.label} »" for c, _ in cs)
                                    + " (ancre vers la figure) ; l'objet de la figure est lu "
                                    f"dans sa légende ({cs[0][1].object_evidence}). Le lien "
                                    "paragraphe-figure est direct ; que le paragraphe analyse "
                                    "l'objet reste à vérifier."
                                ),
                            )
                        ],
                        status=LinkStatus.machine_proposed,
                        rights=trights + _min_rights([figures[i].image_rights for i in fids]),
                        run_id=run.id,
                        figure_ids=fids,
                    )
                )
    for sp in spans.values():
        assert canon[sp.asset_id][sp.char_start : sp.char_end] == sp.text, sp.id
        for oc in sp.also_in:
            assert canon[oc.asset_id][oc.char_start : oc.char_end] == sp.text, sp.id
    ids = [lk.id for lk in links]
    assert len(ids) == len(set(ids)), "identifiants de lien en double"
    return {
        "artworks": list(artworks.values()),
        "spans": list(spans.values()),
        "links": links,
        "figures": list(figures.values()),
        "stats": stats,
    }


def metrics(rec: dict) -> dict:
    figs, arts = rec["figures"], rec["artworks"]
    reusable = [
        f
        for f in figs
        if any(
            r.action == "redistribute_image" and r.decision == Decision.allow
            for r in f.image_rights
        )
    ]
    shown = [
        f
        for f in figs
        if any(r.action == "display_pilot" and r.decision == Decision.allow for r in f.image_rights)
    ]
    return {
        **rec["stats"],
        "spans": len(rec["spans"]),
        "figures": len(figs),
        "figures_with_object": sum(f.artwork_id is not None for f in figs),
        "figures_reusable": len(reusable),
        "figures_displayable_pilot": len(shown),
        "links": len(rec["links"]),
        "links_figure_call": sum(lk.evidence[0].mechanism == "figure_call" for lk in rec["links"]),
        "links_entry_E1": sum(
            lk.evidence[0].mechanism == "editorial_entry_structure" for lk in rec["links"]
        ),
        "links_with_figures": sum(bool(lk.figure_ids) for lk in rec["links"]),
        "artworks": len(arts),
        "met_resolved": sum(
            a.resolution is not None and a.resolution.status == "resolved" for a in arts
        ),
    }


def make_run(cfg: QuireConfig, paths: list[str]) -> Run:
    now = datetime.now(UTC)
    return Run(
        id="run_" + now.strftime("%Y%m%dT%H%M%S"),
        code_version=git_version(),
        params={"source": "quire", "catalogue": cfg.id, "pages": paths, "rules": ["E1", "E0"]},
        started_at=now,
    )


def run_build(config: Path, out: Path, cache: Path) -> dict:
    """Config -> pages (cache) -> slice sur disque ; retourne les mesures."""
    from lesternowak import export

    cfg = load_config(config)
    paths, pages, root_asset = fetch_pages(cfg, cache)
    run = make_run(cfg, paths)
    rec = build_records(cfg, pages, run, run.started_at, met_index() if cfg.referential else {})
    out.mkdir(parents=True, exist_ok=True)
    export.write_jsonl(out / "links.jsonl", rec["links"])
    export.write_jsonl(out / "spans.jsonl", rec["spans"])
    export.write_jsonl(out / "artworks.jsonl", rec["artworks"])
    export.write_jsonl(out / "figures.jsonl", rec["figures"])
    export.write_jsonl(out / "assets.jsonl", [a for _, a in pages.values()] + [root_asset])
    export.write_jsonl(out / "runs.jsonl", [run])
    m = metrics(rec)
    export.dump_json(out / "metrics.json", m)
    return m
