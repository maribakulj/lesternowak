"""Banc d'évaluation : métriques de rattachement et de fonction, accord inter-annotateurs."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from lesternowak.models import GOLD_FUNCTIONS, Link, LinkStatus, PassageFunction, Relation

ABSTAIN = "abstention"
EXCERPT = 120


def read_gold(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text("utf-8").splitlines() if x]


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _ratio(k: int, n: int) -> dict:
    ci = wilson(k, n)
    return {
        "value": round(k / n, 4) if n else None,
        "k": k,
        "n": n,
        "wilson95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
    }


def _attach(pairs: list[tuple[str, bool]], positives: set[str]) -> dict:
    """pairs : (relation gold, prédit ?)."""
    tp = sum(1 for g, p in pairs if g in positives and p)
    fp = sum(1 for g, p in pairs if g not in positives and p)
    fn = sum(1 for g, p in pairs if g in positives and not p)
    pred = tp + fp
    prec = tp / pred if pred else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec == 0 or rec == 0 else None)
    return {
        "positives": sorted(positives),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": _ratio(tp, pred),
        "recall": _ratio(tp, tp + fn),
        "f1": None if f1 is None else round(f1, 4),
        "coverage": _ratio(pred, len(pairs)),
        "abstentions": len(pairs) - pred,
    }


def evaluate(gold: list[dict], links: list[Link], spans: dict, name: str) -> dict:
    pred_pairs = {
        (lk.span_id, lk.artwork_id): lk for lk in links if lk.status != LinkStatus.unresolved
    }
    pairs, unsure, errors = [], 0, []
    matrix: dict[str, Counter] = {}
    for g in gold:
        if g["relation"] == Relation.unsure:
            unsure += 1
            continue
        key = (g["span_id"], g["artwork_id"])
        pred = key in pred_pairs
        pairs.append((g["relation"], pred))
        matrix.setdefault(g["relation"], Counter())["about" if pred else ABSTAIN] += 1
        if (g["relation"] == "about") != pred:
            sp = spans.get(g["span_id"])
            errors.append(
                {
                    "span_id": g["span_id"],
                    "artwork_id": g["artwork_id"],
                    "gold": g["relation"],
                    "pred": "about" if pred else ABSTAIN,
                    "excerpt": (sp.text[:EXCERPT] if sp else ""),
                }
            )
    # fonction : une valeur par span
    gfn: dict[str, str] = {}
    for g in gold:
        known = g["relation"] != Relation.unsure and g.get("function")
        if known and gfn.setdefault(g["span_id"], g["function"]) != g["function"]:
            raise ValueError(f"fonctions gold contradictoires pour {g['span_id']}")
    pfn: dict[str, str] = {}
    for lk in links:
        pfn.setdefault(lk.span_id, str(lk.role))
    conf: dict[str, Counter] = {}
    fn_err = []
    for sid, gf in gfn.items():
        pf = pfn.get(sid, PassageFunction.unclassified)
        conf.setdefault(gf, Counter())[pf] += 1
        if pf != gf:
            sp = spans.get(sid)
            fn_err.append(
                {"span_id": sid, "gold": gf, "pred": pf, "excerpt": sp.text[:EXCERPT] if sp else ""}
            )
    n = len(gfn)
    abst = sum(1 for sid in gfn if pfn.get(sid, "unclassified") == "unclassified")
    correct = sum(1 for sid, gf in gfn.items() if pfn.get(sid) == gf)
    per_class = {}
    for c in GOLD_FUNCTIONS:
        tp = conf.get(c, Counter())[c]
        n_gold = sum(conf.get(c, Counter()).values())
        n_pred = sum(conf[g][c] for g in conf)
        p = tp / n_pred if n_pred else None
        r = tp / n_gold if n_gold else None
        f = 2 * p * r / (p + r) if p and r else (0.0 if n_gold and n_pred else None)
        per_class[c.value] = {
            "support": n_gold,
            "predicted": n_pred,
            "precision": None if p is None else round(p, 4),
            "recall": None if r is None else round(r, 4),
            "f1": None if f is None else round(f, 4),
        }
    return {
        "name": name,
        "pairs_evaluated": len(pairs),
        "pairs_unsure_excluded": unsure,
        "attachment_strict": _attach(pairs, {"about"}),
        "attachment_tolerant": _attach(pairs, {"about", "group"}),
        "relation_matrix": {k: dict(v) for k, v in matrix.items()},
        "function": {
            "spans": n,
            "abstentions": abst,
            "accuracy_all": _ratio(correct, n),
            "accuracy_answered": _ratio(correct, n - abst),
            "per_class": per_class,
            "confusion": {k: dict(v) for k, v in conf.items()},
        },
        "errors": errors,
        "function_errors": fn_err,
    }


def _fmt(r: dict) -> str:
    if r["value"] is None:
        return "n/a"
    ci = r["wilson95"]
    return f"{r['value']:.3f} ({r['k']}/{r['n']}) IC95 [{ci[0]:.3f}, {ci[1]:.3f}]"


def _table(m: dict[str, dict], cols: list[str]) -> list[str]:
    out = ["| gold \\ prédit | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for g, row in sorted(m.items()):
        out.append(f"| {g} | " + " | ".join(str(row.get(c, 0)) for c in cols) + " |")
    return out


def render_report(m: dict) -> str:
    o = [f"# Rapport d'évaluation : {m['name']}", ""]
    o.append(
        f"Couples (span, œuvre) évalués : {m['pairs_evaluated']} ; "
        f"`unsure` exclus : {m['pairs_unsure_excluded']}."
    )
    for key, title in (
        ("attachment_strict", "strict (about)"),
        ("attachment_tolerant", "tolérant (about + group)"),
    ):
        a = m[key]
        o += [
            "",
            f"## Rattachement {title}",
            "",
            f"- précision : {_fmt(a['precision'])}",
            f"- rappel : {_fmt(a['recall'])}",
            f"- F1 : {a['f1']}",
            f"- couverture : {_fmt(a['coverage'])} ; abstentions : {a['abstentions']}",
            f"- TP {a['tp']} · FP {a['fp']} · FN {a['fn']}",
        ]
    o += ["", "## Matrice relation gold / prédit", ""]
    o += _table(m["relation_matrix"], ["about", ABSTAIN])
    f = m["function"]
    o += [
        "",
        "## Fonction (par span)",
        "",
        f"- spans : {f['spans']} ; abstentions (`unclassified`) : {f['abstentions']}",
        f"- exactitude (abstentions comptées fausses) : {_fmt(f['accuracy_all'])}",
        f"- exactitude sur les spans classés : {_fmt(f['accuracy_answered'])}",
        "",
        "| classe | support | prédits | précision | rappel | F1 |",
        "|---|---|---|---|---|---|",
    ]
    for c, v in f["per_class"].items():
        o.append(
            f"| {c} | {v['support']} | {v['predicted']} | {v['precision']} | "
            f"{v['recall']} | {v['f1']} |"
        )
    o += ["", "### Matrice de confusion", ""]
    cols = [x.value for x in PassageFunction]
    o += _table(f["confusion"], cols)
    o += ["", "## Erreurs de rattachement (strict)", ""]
    o += ["| span | œuvre | gold | prédit | extrait (≤120 car.) |", "|---|---|---|---|---|"]
    for e in m["errors"]:
        ex = e["excerpt"].replace("|", "/").replace("\n", " ")
        o.append(f"| {e['span_id']} | {e['artwork_id']} | {e['gold']} | {e['pred']} | {ex} |")
    return "\n".join(o) + "\n"


def cohen_kappa(a: list[str], b: list[str]) -> dict:
    n = len(a)
    if n == 0:
        return {"n": 0, "agreement": None, "kappa": None}
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in ca) / (n * n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else (1.0 if po == 1 else 0.0)
    return {"n": n, "agreement": round(po, 4), "kappa": round(kappa, 4)}


def agreement(gold_a: list[dict], gold_b: list[dict]) -> dict:
    ra = {(g["span_id"], g["artwork_id"]): g for g in gold_a}
    rb = {(g["span_id"], g["artwork_id"]): g for g in gold_b}
    common = sorted(ra.keys() & rb.keys())
    rel = cohen_kappa([ra[k]["relation"] for k in common], [rb[k]["relation"] for k in common])
    fa = {g["span_id"]: g["function"] for g in gold_a}
    fb = {g["span_id"]: g["function"] for g in gold_b}
    spans = sorted(fa.keys() & fb.keys())
    fn = cohen_kappa([fa[s] for s in spans], [fb[s] for s in spans])
    return {"common_pairs": len(common), "relations": rel, "functions": fn}
