"""Client Gallica : limiteur (horloge simulée), Retry-After, arrêt sur 403/429, cache."""

import itertools
import json
from datetime import UTC, datetime

import pytest

from lesternowak import gallica as g


class FakeClock:
    def __init__(self):
        self.t = 1000.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, dt):
        self.sleeps.append(dt)
        self.t += dt


def make_client(tmp_path, responses, clock=None):
    clock = clock or FakeClock()
    calls = []

    def opener(url, headers):
        calls.append((clock.t, url, headers))
        r = responses(url, len(calls)) if callable(responses) else responses
        return r

    c = g.GallicaClient(
        cache_root=tmp_path,
        limiter=g.Limiter(clock.now, clock.sleep),
        opener=opener,
        now=lambda: datetime(2026, 11, 17, tzinfo=UTC),
    )
    return c, clock, calls


def test_per_service_spacing_alto(tmp_path):
    c, _clock, calls = make_client(tmp_path, (200, {}, b"<x/>"))
    for n in range(1, 7):
        c.alto("bpt6k1", n)
    times = [t for t, _, _ in calls]
    gaps = [b - a for a, b in itertools.pairwise(times)]
    assert min(gaps) >= 60 / 5  # 5 req/min
    assert all(h["User-Agent"] == g.USER_AGENT for _, _, h in calls)


def test_global_cap_sliding_window(tmp_path):
    c, _clock, calls = make_client(tmp_path, (200, {}, b"x"))
    for n in range(1, 160):  # medres : 50 / min par service, 70 / min global
        c.fetch("medres", "bpt6k1", f"m/{n}", n=n)
        c.fetch("oai", "bpt6k1", f"o/{n}")
    times = [t for t, _, _ in calls]
    for i, t0 in enumerate(times):
        assert sum(1 for t in times[i:] if t - t0 < 60.0) <= g.GLOBAL_PER_MIN


def test_iiif_bytes_per_minute(tmp_path):
    big = b"x" * 3_000_000
    c, _clock, calls = make_client(tmp_path, (200, {}, big))
    for n in range(8):
        c.fetch("iiif_image", "bpt6k1", f"i/{n}", region=(0, 0, 1, 1), n=n)
    times = [t for t, _, _ in calls]
    for i, t0 in enumerate(times):
        window = [t for t in times[i:] if t - t0 < 60.0]
        assert len(window) * 3_000_000 <= g.IIIF_BYTES_PER_MIN + 3_000_000


def test_retry_after_respected_then_ok(tmp_path):
    seq = [(429, {"Retry-After": "40"}, b""), (200, {}, b"ok")]
    c, _clock, calls = make_client(tmp_path, lambda url, n: seq[n - 1])
    f = c.oai("bpt6k1")
    assert f.body == b"ok" and c.stops == 1
    assert calls[1][0] - calls[0][0] >= 40


def test_stop_after_two_403_and_stop_file(tmp_path):
    c, _clock, calls = make_client(tmp_path, (403, {}, b"cf"))
    with pytest.raises(g.GallicaStop):
        c.oai("bpt6k1")
    assert len(calls) == 2  # pas de troisième tentative
    assert (tmp_path / "_stop.json").exists()
    c2, _, calls2 = make_client(tmp_path, (200, {}, b"x"))
    with pytest.raises(g.GallicaStop):
        c2.oai("bpt6k2")
    assert calls2 == []  # aucune requête tant que l'arrêt n'est pas levé à la main


def test_cache_permanent_with_sha_and_404(tmp_path):
    c, _, calls = make_client(tmp_path, (200, {}, b"data"))
    f1 = c.pagination("ark:/12148/bpt6k1")
    f2 = c.pagination("bpt6k1")
    assert len(calls) == 1 and f2.from_cache and f1.sha256 == f2.sha256
    meta = json.loads((tmp_path / "bpt6k1" / "pagination.xml.meta.json").read_text())
    assert meta["sha256"] == f1.sha256 and meta["captured_at"].startswith("2026-11-17")
    c404, _, calls404 = make_client(tmp_path, (404, {}, b"{}"))
    assert c404.alto("bpt6k1", 3).status == 404
    n = len(calls404)
    c404.alto("bpt6k1", 3)  # 404 en cache : pas de nouvelle requête
    assert len(calls404) == n


def test_transient_error_retried_once(tmp_path):
    seq = [(500, {}, b""), (200, {}, b"ok")]
    c, _, calls = make_client(tmp_path, lambda url, n: seq[n - 1])
    assert c.oai("bpt6k1").body == b"ok" and len(calls) == 2
    c2, _, calls2 = make_client(tmp_path / "b", (500, {}, b""))
    with pytest.raises(g.GallicaHTTPError):
        c2.oai("bpt6k1")
    assert len(calls2) == 2


def test_urls_and_iiif_width_cap():
    assert g.GallicaClient.url("alto", "bpt6k1", n=7).endswith(
        "/presentation/v3/ark:/12148/bpt6k1/f7/alto.xml"
    )
    assert g.GallicaClient.url("textebrut_doc", "bpt6k1").endswith("/ark:/12148/bpt6k1.texteBrut")
    u = g.iiif_region_url("bpt6k1", 3, (0.1, 0.2, 0.6, 0.7), width=5000)
    assert "/pct:10.00,20.00,50.00,50.00/800,/0/" in u


def test_split_textebrut():
    pages = g.split_textebrut(b"a<br/>b</BR>c <br/><br/>d")
    assert pages == ["a\nb", "c \n\nd"]


def test_alto_falls_back_to_rde_then_prefers_it(tmp_path):
    def resp(url, n):
        if "RequestDigitalElement" in url:
            return 200, {}, b"<alto/>"
        return 404, {}, b"{}"

    c, _clock, calls = make_client(tmp_path, resp)
    for n in range(1, 6):
        assert c.alto("bpt6k1", n).body == b"<alto/>"
    urls = [u for _, u, _ in calls]
    assert sum("alto.xml" in u for u in urls) == 3  # trois 404 v3, puis RDE directement
    assert sum("RequestDigitalElement" in u for u in urls) == 5
    assert "O=bpt6k1&E=ALTO&Deb=4" in urls[-2]
