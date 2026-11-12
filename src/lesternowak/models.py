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


class PassageRole(StrEnum):
    visual_description = "visual_description"
    technical_material = "technical_material"
    provenance = "provenance"
    interpretive_discussion = "interpretive_discussion"
    bibliographic = "bibliographic"
    unclassified = "unclassified"


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


class Span(BaseModel):
    """Passage : `canonical_text[char_start:char_end] == text` pour la page `asset_id`."""

    id: str  # empreinte du texte : un même passage partagé n'a qu'un Span
    asset_id: str
    section_label: str
    paragraph_index: int  # rang du paragraphe dans la section (depuis 0)
    char_start: int
    char_end: int
    text: str
    text_fidelity: Literal["born_digital"] = "born_digital"
    notes: list[int] = Field(default_factory=list)  # appels de note, visibles « [n] » dans text
    group_title: str | None = None
    # autres pages où le même texte est reproduit (discussion partagée)
    also_in: list[Occurrence] = Field(default_factory=list)


class Occurrence(BaseModel):
    asset_id: str
    char_start: int
    char_end: int


Span.model_rebuild()


class ArtworkRef(BaseModel):
    """Identifiants externes fournis par l'éditeur ; le titre est celui de l'éditeur."""

    id: str
    getty_dor_id: int
    inventory_number: str
    catalogue_number: str
    collection_url: str
    title: str


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


class Link(BaseModel):
    id: str
    artwork_id: str
    span_id: str
    role: PassageRole
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
    link_id: str
    before: LinkStatus
    after: LinkStatus
    annotator: str
    note: str
    timestamp: datetime
