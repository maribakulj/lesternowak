"""Rétrocompatibilité Terracottas : les identifiants de liens existants ne changent pas."""

import hashlib
import json

from test_getty_quire import FIX, NOW, _pages, gq


def test_terracottas_link_ids_unchanged_by_generic_models():
    page1 = (FIX / "catalogue_1.html").read_bytes()
    data = json.loads((FIX / "data_first3.json").read_text())
    rec = gq.build_records(_pages(page1, data), data, gq.make_run([1, 2, 3]), NOW)
    ids = [lk.id for lk in rec["links"]]
    assert ids[:3] == ["lnk_755aeeb486fd", "lnk_d3485f94041d", "lnk_ce24be59957e"]
    assert hashlib.sha256("".join(ids).encode()).hexdigest() == (
        "457fc79f5ed6f08ef601e129f40a3cd03dcf879494b8cb001fe297219f021b30"
    )
    assert sorted(a.id for a in rec["artworks"]) == ["getty-13144", "getty-13145", "getty-13146"]
    sp = rec["spans"][0]
    assert sp.text_fidelity == "born_digital" and sp.page_refs == []
    art = rec["artworks"][0]
    assert art.getty_dor_id == 13144 and art.artwork_local_id is None and art.resolution is None
