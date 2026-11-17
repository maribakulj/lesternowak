"""Lecture d'ALTO (v2 à v4) : blocs, lignes, mots, illustrations, coordonnées normalisées.

Texte canonique d'une page : lignes d'un bloc séparées par « \\n », blocs par « \\n\\n »
(`AltoPage.text`) ; les offsets des lignes et des blocs s'y rapportent. Le texte vient du
CONTENT des `String` (rien n'est corrigé : `ocr_raw`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree

BBox = tuple[float, float, float, float]


@dataclass
class Word:
    text: str
    bbox: BBox  # normalisée


@dataclass
class Line:
    text: str
    bbox: BBox
    src_bbox: BBox
    start: int = 0
    end: int = 0
    words: list[Word] = field(default_factory=list)


@dataclass
class Block:
    id: str
    bbox: BBox
    lines: list[Line]
    start: int = 0
    end: int = 0


@dataclass
class Illustration:
    id: str
    bbox: BBox
    src_bbox: BBox
    kind: str  # Illustration | GraphicalElement | ComposedBlock


@dataclass
class AltoPage:
    width: float
    height: float
    unit: str
    blocks: list[Block]
    illustrations: list[Illustration]
    text: str

    @property
    def coordinate_system(self) -> str:
        return f"alto:{self.unit}:{self.width:g}x{self.height:g}"


def fix_mojibake(s: str) -> str:
    """Double encodage UTF-8 -> Latin-1 observé sur RequestDigitalElement (« JÃ©sus ») :
    réparation réversible, seulement si tout le texte se relit en UTF-8 ; sinon inchangé."""
    if "Ã" not in s and "Â" not in s:
        return s
    for enc in ("latin-1", "cp1252"):
        try:
            return s.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s


def _ln(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def normalize_bbox(
    hpos: float, vpos: float, w: float, h: float, page_w: float, page_h: float
) -> BBox:
    """Coordonnées ALTO (unités de la page) -> bbox normalisée 0-1, bornée."""
    clamp = lambda v: min(1.0, max(0.0, v))  # noqa: E731
    return (
        round(clamp(hpos / page_w), 6),
        round(clamp(vpos / page_h), 6),
        round(clamp((hpos + w) / page_w), 6),
        round(clamp((vpos + h) / page_h), 6),
    )


def denormalize_bbox(bbox: BBox, page_w: float, page_h: float) -> tuple[float, float, float, float]:
    """bbox normalisée -> (HPOS, VPOS, WIDTH, HEIGHT) dans les unités de la page."""
    x0, y0, x1, y1 = bbox
    return (x0 * page_w, y0 * page_h, (x1 - x0) * page_w, (y1 - y0) * page_h)


def union(boxes: list[BBox]) -> BBox:
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def _geo(el) -> tuple[float, float, float, float] | None:
    try:
        return (
            float(el.get("HPOS")),
            float(el.get("VPOS")),
            float(el.get("WIDTH")),
            float(el.get("HEIGHT")),
        )
    except (TypeError, ValueError):
        return None


def parse_alto(data: bytes) -> AltoPage:
    root = etree.fromstring(data, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    unit = "pixel"
    for el in root.iter():
        if _ln(el) == "MeasurementUnit" and el.text:
            unit = el.text.strip()
            break
    page = next((e for e in root.iter() if _ln(e) == "Page"), None)
    if page is None:
        raise ValueError("ALTO sans élément Page")
    pw, ph = float(page.get("WIDTH")), float(page.get("HEIGHT"))
    if pw <= 0 or ph <= 0:
        raise ValueError("dimensions de page ALTO invalides")

    blocks: list[Block] = []
    illus: list[Illustration] = []

    def handle(el) -> None:
        name = _ln(el)
        if name == "TextBlock":
            lines = []
            for tl in el:
                if _ln(tl) != "TextLine":
                    continue
                parts, words = [], []
                for st in tl:
                    k = _ln(st)
                    g = _geo(st)
                    if k == "String" and st.get("CONTENT"):
                        content = fix_mojibake(st.get("CONTENT"))
                        parts.append(content)
                        if g:
                            words.append(Word(content, normalize_bbox(*g, pw, ph)))
                    elif k == "HYP" and st.get("CONTENT") and parts:
                        parts[-1] += fix_mojibake(st.get("CONTENT"))
                text = " ".join(parts).strip()
                lg = _geo(tl)
                if text and lg:
                    lines.append(Line(text, normalize_bbox(*lg, pw, ph), lg, words=words))
            if lines:
                bg = _geo(el)
                bb = normalize_bbox(*bg, pw, ph) if bg else union([ln.bbox for ln in lines])
                blocks.append(Block(el.get("ID", ""), bb, lines))
        elif name in ("Illustration", "GraphicalElement"):
            g = _geo(el)
            # filets et traits : un GraphicalElement doit mesurer au moins 4 % de la page par côté
            thin = name == "GraphicalElement" and g and min(g[2] / pw, g[3] / ph) < 0.04
            if g and not thin:
                illus.append(Illustration(el.get("ID", ""), normalize_bbox(*g, pw, ph), g, name))
        elif name == "ComposedBlock":
            if (el.get("TYPE") or "").lower() == "illustration":
                g = _geo(el)
                if g:
                    illus.append(
                        Illustration(el.get("ID", ""), normalize_bbox(*g, pw, ph), g, name)
                    )
                    return
            for ch in el:
                handle(ch)

    for ps in page.iter():
        if _ln(ps) == "PrintSpace":
            for ch in ps:
                handle(ch)
            break
    else:
        for ch in page:
            handle(ch)

    out: list[str] = []
    pos = 0
    for bi, b in enumerate(blocks):
        if bi:
            out.append("\n\n")
            pos += 2
        b.start = pos
        for li, ln in enumerate(b.lines):
            if li:
                out.append("\n")
                pos += 1
            ln.start = pos
            out.append(ln.text)
            pos += len(ln.text)
            ln.end = pos
        b.end = pos
    return AltoPage(pw, ph, unit, blocks, illus, "".join(out))
