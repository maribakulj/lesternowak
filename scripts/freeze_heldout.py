"""Tirage reproductible des volumes tenus à l'écart (lot C0, PLAN_CORPUS).

Pour chaque type de `docs/sources/inventory/selection.yaml` ayant au moins deux volumes retenus
(`selected: true`), un volume est tiré avec `random.Random(SEED)` parmi les identifiants triés,
dans l'ordre des types du fichier. Les autres volumes retenus sont le développement.
Le résultat est écrit dans `gold/heldout-volumes.yaml` avec le sha256 de la liste des tenus à
l'écart. `--check` recalcule et compare sans écrire.

Usage : uv run python scripts/freeze_heldout.py [--check]
"""

import argparse
import hashlib
import json
import random
import sys
from datetime import date
from pathlib import Path

import yaml

SEED = 20261117
ROOT = Path(__file__).resolve().parent.parent
SELECTION = ROOT / "docs" / "sources" / "inventory" / "selection.yaml"
OUTPUT = ROOT / "gold" / "heldout-volumes.yaml"
MIN_VOLUMES = 2


def draw(selection: dict) -> tuple[list[dict], list[dict], list[str]]:
    rng = random.Random(SEED)
    heldout: list[dict] = []
    dev: list[dict] = []
    undrawn: list[str] = []
    for typ in selection["types"]:
        ids = sorted(v["id"] for v in typ["volumes"] if v["selected"])
        if len(ids) < MIN_VOLUMES:
            undrawn.append(typ["type"])
            dev.extend({"type": typ["type"], "id": i} for i in ids)
            continue
        picked = rng.choice(ids)
        heldout.append({"type": typ["type"], "id": picked})
        dev.extend({"type": typ["type"], "id": i} for i in ids if i != picked)
    return heldout, dev, undrawn


def digest(heldout: list[dict]) -> str:
    canonical = json.dumps(
        sorted(heldout, key=lambda h: (h["type"], h["id"])),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="vérifier sans écrire")
    args = parser.parse_args()

    selection = yaml.safe_load(SELECTION.read_text(encoding="utf-8"))
    heldout, dev, undrawn = draw(selection)
    sha = digest(heldout)

    if args.check:
        frozen = yaml.safe_load(OUTPUT.read_text(encoding="utf-8"))
        ok = frozen["heldout"] == heldout and frozen["sha256"] == sha
        print("conforme" if ok else "DIFFÉRENT", sha)
        return 0 if ok else 1

    frozen = {
        "seed": SEED,
        "frozen_at": date.today().isoformat(),
        "algorithm": (
            "random.Random(seed).choice(sorted ids retenus), un tirage par type ayant au moins "
            "2 volumes retenus, types pris dans l'ordre de selection.yaml"
        ),
        "selection_file": "docs/sources/inventory/selection.yaml",
        "sha256_of": "JSON canonique de la liste heldout triée par (type, id)",
        "sha256": sha,
        "heldout": heldout,
        "dev": dev,
        "types_without_draw": undrawn,
        "rule": "les volumes tenus à l'écart ne servent jamais au réglage",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    header = "# Gel des volumes tenus à l'écart (généré par scripts/freeze_heldout.py).\n"
    body = yaml.safe_dump(frozen, allow_unicode=True, sort_keys=False, width=100)
    OUTPUT.write_text(header + body, encoding="utf-8")
    print(sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
