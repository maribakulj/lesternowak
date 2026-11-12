"""Interface en ligne de commande.

Étape 0 : seules --help et --version existent. Les sous-commandes arriveront
avec la tranche verticale (voir docs/PLAN.md), pas avant.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
