# ruff: noqa: RUF001
"""Tests hors ligne du référentiel d'œuvres et du résolveur E0 / E2 (lot C2)."""

import json
from pathlib import Path

import pytest

from lesternowak.referentials import (
    LocalAttrs,
    OtherNumber,
    ReferenceArtwork,
    append_cache,
    joconde_to_ref,
    load_cache,
    met_to_ref,
    parse_dimensions,
    resolve,
)

FIX = Path(__file__).parent / "fixtures" / "met_objects.json"


@pytest.fixture
def refs() -> list[ReferenceArtwork]:
    return [met_to_ref(o, "2026-11-17T00:00:00+00:00") for o in json.loads(FIX.read_text())]


def test_parse_dimensions_cm_and_inches():
    assert parse_dimensions("28 13/16 × 36 3/4 in. (73.2 × 93.4 cm)") == (73.2, 93.4)
    h, w = parse_dimensions("H. 28 1/2 in.; W. 36 in.")
    assert (round(h, 1), round(w, 1)) == (72.4, 91.4)
    h, w = parse_dimensions("29 x 37 in.")
    assert (round(h, 1), round(w, 1)) == (73.7, 94.0)
    assert parse_dimensions("Diameter 114 in.") is None
    assert parse_dimensions("") is None


def test_met_mapping_image_only_if_public_domain(refs):
    r = refs[0]
    assert r.ref_id == "met:436535" and r.accession_year == 1993
    assert r.image_license == "cc0" and r.image_url.endswith("DP-42549-001.jpg")
    obj = json.loads(FIX.read_text())[0] | {"isPublicDomain": False}
    r2 = met_to_ref(obj, "x")
    assert r2.image_url == "" and r2.image_license == "restricted"


def test_cache_incremental(tmp_path, refs):
    p = tmp_path / "ref" / "met.jsonl"
    append_cache(p, refs[0])
    append_cache(p, refs[1])
    assert [r.ref_id for r in load_cache(p)] == ["met:436535", "met:437793"]


def test_e0_accession_number(refs):
    res = resolve(LocalAttrs(accession_number="1993.132"), refs)
    assert (res.status, res.evidence, res.ref_id) == ("resolved", "E0", "met:436535")
    assert resolve(LocalAttrs(accession_number="99.99"), refs).status == "unresolved"


def test_e2_composite_unique(refs):
    local = LocalAttrs(
        credit_line="Purchase, Annenberg Foundation Gift, 1993",
        dimensions_raw="H. 28 3/4 in.; W. 36 3/4 in.",
        artist="Vincent van Gogh",
    )
    res = resolve(local, refs)
    assert (res.status, res.evidence, res.ref_id) == ("resolved", "E2", "met:436535")
    assert set(res.signals[0].independent()) >= {"credit_line", "dimensions"}


def test_e2_refused_with_two_candidates(refs):
    local = LocalAttrs(
        credit_line="Bequest of Grace Rainey Rogers, 1943",
        accession_year=1943,
        dimensions_cm=(370.8, 147.0),
        artist="Giovanni Battista Tiepolo",
    )
    res = resolve(local, refs)
    assert res.status == "unresolved"
    assert sorted(res.candidates) == ["met:437793", "met:437797"]
    assert "2 candidats" in res.reason


def test_refused_on_title_or_artist_alone(refs):
    res = resolve(LocalAttrs(artist="Vincent van Gogh"), refs)
    assert res.status == "unresolved"
    res = resolve(LocalAttrs(artist="Vincent van Gogh", accession_year=1993), refs)
    assert res.status == "unresolved"  # un seul attribut indépendant


def test_old_number_counts_as_independent_signal(refs):
    refs[0].other_numbers = [OtherNumber(scheme="Villot", value="365", source="test")]
    local = LocalAttrs(
        other_numbers=[OtherNumber(scheme="Villot", value="365", source="notice")],
        accession_year=1993,
        artist="Vincent van Gogh",
    )
    assert resolve(local, refs).ref_id == "met:436535"


def test_joconde_mapping():
    row = {
        "Reference": "000PE000050",
        "Numero_inventaire": "MV 3678 ; INV 3229 ; MR 1576",
        "Titre": "Le dessert",
        "Auteur": "BAUGIN Lubin",
        "Mesures": "41 H ; 52 L",
        "Date_d_acquisition": "1954",
        "Bibliographie": "Cat. ; Villot II 365 ; Suppl. Tauzia 809",
    }
    r = joconde_to_ref(row, "x")
    assert r.accession_number == "MV 3678" and r.dimensions_cm == (41.0, 52.0)
    assert {(o.scheme, o.value) for o in r.other_numbers} >= {
        ("INV", "INV 3229"),
        ("MR", "MR 1576"),
        ("Villot", "365"),
        ("Tauzia", "809"),
    }
