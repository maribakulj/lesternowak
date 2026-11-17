"""Modèles minimaux de la tranche verticale (étape 2)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class LinkStatus(StrEnum):
    machine_proposed = "machine_proposed"  # preuve directe par règle/structure, non validée
    model_suggested = "model_suggested"  # suggestion de modèle (jamais validated sans humain)
    validated = "validated"  # uniquement via un AnnotationEvent humain
    rejected = "rejected"
    unresolved = "unresolved"


class PassageFunction(StrEnum):
    visual_description = "visual_description"
    technical_material = "technical_material"
    iconography_interpretation = "iconography_interpretation"
    comparison = "comparison"
    attribution_dating = "attribution_dating"
    provenance_context = "provenance_context"
    other = "other"
    unclassified = "unclassified"  # prédictions seulement : abstention, jamais une étiquette gold


GOLD_FUNCTIONS = tuple(f for f in PassageFunction if f != PassageFunction.unclassified)


class Relation(StrEnum):
    about = "about"  # le passage analyse cette œuvre
    mentions = "mentions"  # citée sans analyse
    group = "group"  # porte sur le groupe sans viser cette œuvre
    context = "context"  # arrière-plan sans affirmation sur l'objet
    not_about = "not_about"
    unsure = "unsure"


class Decision(StrEnum):
    allow = "allow"
    deny = "deny"
    unknown = "unknown"
    conditional = "conditional"


class Surrogate(BaseModel):
    """Publication source (le substitut numérique, pas l'œuvre)."""

    publication_url: str
    title: str
    author: str
    publisher: str
    year: int
    license_url: str
    captured_at: datetime


class SourceAsset(BaseModel):
    id: str
    url: str
    sha256: str
    captured_at: datetime
    media_type: str
    local_path: str


class PageRef(BaseModel):
    """Localisation d'un passage ou d'une figure sur une vue (page numérisée)."""

    view: int
    page_label: str | None = None
    # normalisée 0-1, origine en haut à gauche : (x0, y0, x1, y1)
    bbox: tuple[float, float, float, float] | None = None
    source_bbox: tuple[float, float, float, float] | None = None
    source_coordinate_system: str | None = None  # ex. « alto:pixel:2592x3508 »
    alignment: Literal["verified", "estimated"] = "verified"  # vue vérifiée ou estimée


class Span(BaseModel):
    """Passage : `canonical_text[char_start:char_end] == text` pour la page `asset_id`."""

    id: str  # empreinte du texte : un même passage partagé n'a qu'un Span
    asset_id: str
    section_label: str
    paragraph_index: int  # rang du paragraphe dans la section (depuis 0)
    char_start: int
    char_end: int
    text: str
    text_fidelity: Literal["born_digital", "ocr_raw", "ocr_corrected"] = "born_digital"
    page_refs: list[PageRef] = Field(default_factory=list)
    notes: list[int] = Field(default_factory=list)  # appels de note, visibles « [n] » dans text
    group_title: str | None = None
    # autres pages où le même texte est reproduit (discussion partagée)
    also_in: list[Occurrence] = Field(default_factory=list)


class Occurrence(BaseModel):
    asset_id: str
    char_start: int
    char_end: int


Span.model_rebuild()


class Resolution(BaseModel):
    """Résolution œuvre locale -> référentiel externe (ADR 0003) ; `unresolved` est valide."""

    status: Literal["resolved", "unresolved"] = "unresolved"
    mechanism: Literal["E0", "E2_composite"] | None = None
    signals: list[dict] = Field(default_factory=list)
    candidates: list[str] = Field(default_factory=list)
    reason: str = ""


class ArtworkRef(BaseModel):
    """Œuvre. Terracottas : identifiants Getty de l'éditeur. Autres sources : œuvre *locale* au
    volume (`artwork_local_id` = volume + numéro de notice), résolution externe séparée."""

    id: str
    getty_dor_id: int | None = None
    inventory_number: str = ""
    catalogue_number: str = ""
    collection_url: str = ""
    title: str = ""
    artwork_local_id: str | None = None
    local_label: str | None = None  # numéro/titre tel qu'imprimé (extrait exact du texte)
    artist_heading: str | None = None  # dernier intitulé d'artiste imprimé (extrait exact)
    external_ids: list[dict] = Field(default_factory=list)
    resolution: Resolution | None = None


class Evidence(BaseModel):
    mechanism: str  # ex. "editorial_entry_structure" (E1)
    quoted_heading: str
    explanation: str


class RightsDecision(BaseModel):
    asset: Literal["text", "images"]
    action: str
    decision: Decision
    basis: str
    evidence_url: str
    checked_at: datetime


class Figure(BaseModel):
    """Illustration repérée par la structure (ALTO) ; liée à une notice par numéro explicite."""

    id: str
    view: int
    bbox: tuple[float, float, float, float]  # normalisée 0-1, haut-gauche
    caption_span_id: str | None = None
    linked_artwork_local_id: str | None = None
    link_evidence: list[Evidence] = Field(default_factory=list)
    image_url: str  # région IIIF à taille réduite (<= 800 px), non téléchargée
    image_rights: list[RightsDecision] = Field(default_factory=list)


class Link(BaseModel):
    id: str
    artwork_id: str
    span_id: str
    role: PassageFunction
    evidence: list[Evidence]
    status: LinkStatus
    rights: list[RightsDecision]
    run_id: str


class Run(BaseModel):
    id: str
    code_version: str
    params: dict
    started_at: datetime


class AnnotationEvent(BaseModel):
    """Décision humaine append-only. Les champs optionnels viennent du pilote de vérification."""

    link_id: str | None = None
    before: LinkStatus
    after: LinkStatus
    annotator: str
    note: str
    timestamp: datetime
    item_id: str | None = None
    span_id: str | None = None
    artwork_id: str | None = None
    relation: Relation | None = None
    function: PassageFunction | None = None
    blind: bool | None = None
    elapsed_ms: int | None = None


class ReviewArtwork(BaseModel):
    id: str
    title: str
    catalogue_number: str | None = None
    accession_number: str | None = None
    other_ids: dict[str, str] = Field(default_factory=dict)
    collection_url: str | None = None
    image_url: str | None = None
    image_display_allowed: bool = False


class ReviewPassage(BaseModel):
    span_id: str
    text: str  # texte exact du span, jamais reformulé
    section: str
    char_start: int
    char_end: int


class ReviewHighlight(BaseModel):
    start: int  # offsets relatifs au passage
    end: int
    label: str


class ReviewSource(BaseModel):
    url: str
    page_label: str | None = None
    page_image_url: str | None = None


class ReviewProposal(BaseModel):
    relation: Relation
    function: PassageFunction | None = None  # None : fonction non proposée
    evidence_mechanism: str
    explanation: str


class ReviewItem(BaseModel):
    """Élément de vérification, indépendant de la source (voir `review.py`)."""

    item_id: str  # déterministe : empreinte de corpus + lien (ou span + œuvre)
    corpus: str
    link_id: str | None = None
    artwork: ReviewArtwork
    passage: ReviewPassage
    highlights: list[ReviewHighlight] = Field(default_factory=list)
    source: ReviewSource
    proposal: ReviewProposal | None = None  # None si présenté à l'aveugle
    blind: bool = False
    rights_summary: str = ""
