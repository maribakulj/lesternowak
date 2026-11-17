"""Client Gallica via la passerelle `openapi.bnf.fr` (lot C3) : quotas, cache permanent, arrêt.

Quotas : `docs/sources/gallica-acces.md`. Le limiteur applique un espacement minimal par service
(60 / quota), un plafond global glissant sur 60 s et un plafond d'octets par minute pour IIIF
Image. `Retry-After` est respecté. Après deux réponses 403 ou 429 au total, le client s'arrête
(`GallicaStop`) : un 403 est un statut, jamais un obstacle à contourner. Le User-Agent est fixe.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

BASE = "https://openapi.bnf.fr"
USER_AGENT = "lesternowak/0.0.1 (recherche; client Gallica)"
GLOBAL_PER_MIN = 75
GLOBAL_MARGIN = 70  # marge sous le plafond de 75
IIIF_BYTES_PER_MIN = 9_000_000  # quota 10 Mo/min (à confirmer), marge
IIIF_BYTES_ESTIMATE = 400_000  # réservation avant réponse
MAX_STOPS = 2

# requêtes par minute ; « aucun spécifique » -> espacement prudent de 20 / min
RATES: dict[str, float] = {
    "oai": 20,
    "pagination": 20,
    "toc": 20,
    "manifest": 5,
    "textebrut_doc": 6,
    "textebrut_page": 20,
    "alto": 5,
    "alto_rde": 6,
    "medres": 50,
    "iiif_image": 10,
}
SPACING_MARGIN = 1.05


class GallicaStop(RuntimeError):
    """Arrêt volontaire : 403/429 répétés."""


class GallicaHTTPError(RuntimeError):
    def __init__(self, status: int, url: str):
        super().__init__(f"HTTP {status} sur {url}")
        self.status = status
        self.url = url


class Limiter:
    """Limiteur à horloge injectable (tests)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, sleep=time.sleep):
        self.clock = clock
        self.sleep = sleep
        self.last: dict[str, float] = {}
        self.window: deque[float] = deque()
        self.bytes_window: deque[tuple[float, int]] = deque()
        self.blocked_until = 0.0
        self.waited = 0.0

    def _wait(self, dt: float) -> None:
        if dt > 0:
            self.waited += dt
            self.sleep(dt)

    def block(self, seconds: float) -> None:
        """Retry-After : plus aucune requête avant `seconds`."""
        self.blocked_until = max(self.blocked_until, self.clock() + seconds)

    def acquire(self, service: str) -> None:
        self._wait(self.blocked_until - self.clock())
        rate = RATES[service]
        if service in self.last:
            self._wait(self.last[service] + SPACING_MARGIN * 60.0 / rate - self.clock())
        while True:
            now = self.clock()
            while self.window and now - self.window[0] >= 60.0:
                self.window.popleft()
            if len(self.window) < GLOBAL_MARGIN:
                break
            self._wait(60.0 - (now - self.window[0]) + 0.01)
        if service == "iiif_image":
            while True:
                now = self.clock()
                while self.bytes_window and now - self.bytes_window[0][0] >= 60.0:
                    self.bytes_window.popleft()
                used = sum(n for _, n in self.bytes_window)
                if used + IIIF_BYTES_ESTIMATE <= IIIF_BYTES_PER_MIN or not self.bytes_window:
                    break
                self._wait(60.0 - (now - self.bytes_window[0][0]) + 0.01)
        now = self.clock()
        self.last[service] = now
        self.window.append(now)

    def record_bytes(self, service: str, n: int) -> None:
        if service == "iiif_image":
            self.bytes_window.append((self.clock(), n))


Opener = Callable[[str, dict[str, str]], tuple[int, dict[str, str], bytes]]


def urllib_opener(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read() or b""


@dataclass
class Fetched:
    url: str
    status: int
    body: bytes | None
    sha256: str
    captured_at: str
    path: Path
    from_cache: bool = False


@dataclass
class Stats:
    requests: dict[str, int] = field(default_factory=dict)
    errors: dict[str, dict[int, int]] = field(default_factory=dict)
    cache_hits: int = 0
    transient_retries: int = 0
    started: float = field(default_factory=time.time)

    def count(self, service: str) -> None:
        self.requests[service] = self.requests.get(service, 0) + 1

    def error(self, service: str, code: int) -> None:
        d = self.errors.setdefault(service, {})
        d[code] = d.get(code, 0) + 1

    def as_dict(self) -> dict:
        return {
            "requests": dict(sorted(self.requests.items())),
            "total": sum(self.requests.values()),
            "errors": {k: {str(c): n for c, n in v.items()} for k, v in self.errors.items()},
            "cache_hits": self.cache_hits,
            "transient_retries": self.transient_retries,
            "seconds": round(time.time() - self.started, 1),
        }


def bare_ark(ark: str) -> str:
    """`ark:/12148/bpt6k73772x` ou `bpt6k73772x` -> `bpt6k73772x`."""
    return ark.rsplit("/", 1)[-1]


class GallicaClient:
    def __init__(
        self,
        cache_root: Path = Path("data/raw/gallica"),
        limiter: Limiter | None = None,
        opener: Opener = urllib_opener,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        max_stops: int = MAX_STOPS,
    ):
        self.cache_root = cache_root
        self.limiter = limiter or Limiter()
        self.opener = opener
        self.now = now
        self.max_stops = max_stops
        self.stops = 0
        self.rde_first = False
        self.v3_404_streak = 0
        self.stats = Stats()
        self.stop_file = cache_root / "_stop.json"

    # -- URL des services ----------------------------------------------------------------
    @staticmethod
    def url(service: str, ark: str, **kw) -> str:
        a = bare_ark(ark)
        n = kw.get("n")
        if service == "oai":
            return f"{BASE}/document/oaidc/gallica/1.0.0/OAIRecord?ark={a}"
        if service == "pagination":
            return f"{BASE}/document/pagination/gallica/1.0.0/Pagination?ark={a}"
        if service == "toc":
            return f"{BASE}/document/tdm/gallica/1.0.0/Toc?ark={a}"
        if service == "manifest":
            return f"{BASE}/presentation/iiifv2/gallica/1.0.0/ark:/12148/{a}/manifest.json"
        if service == "textebrut_doc":
            return f"{BASE}/texte/brut/gallica/1.0.0/ark:/12148/{a}.texteBrut"
        if service == "textebrut_page":
            return f"{BASE}/texte/brut/gallica/1.0.0/ark:/12148/{a}/f{n}.texteBrut"
        if service == "alto":
            v3 = f"{BASE}/presentation/iiif/gallica/1.0.0/presentation/v3"
            return f"{v3}/ark:/12148/{a}/f{n}/alto.xml"
        if service == "alto_rde":
            return f"{BASE}/texte/ocr/gallica/1.0.0/RequestDigitalElement?O={a}&E=ALTO&Deb={n}"
        if service == "medres":
            return f"{BASE}/image/gallica/1.0.0/ark:/12148/{a}/f{n}.medres"
        if service == "iiif_image":
            return iiif_region_url(a, n, kw["region"], kw.get("width", 800))
        raise KeyError(service)

    # -- cache -----------------------------------------------------------------------------
    def cache_path(self, ark: str, relpath: str) -> Path:
        return self.cache_root / bare_ark(ark) / relpath

    def _read_cache(self, p: Path) -> Fetched | None:
        meta_p = p.with_name(p.name + ".meta.json")
        if not meta_p.exists():
            return None
        meta = json.loads(meta_p.read_text("utf-8"))
        body = None
        if meta["status"] == 200:
            if not p.exists():
                return None
            body = p.read_bytes()
            if hashlib.sha256(body).hexdigest() != meta["sha256"]:
                raise RuntimeError(f"cache corrompu : {p}")
        return Fetched(
            meta["url"], meta["status"], body, meta["sha256"], meta["captured_at"], p, True
        )

    def _write_cache(self, p: Path, url: str, status: int, body: bytes | None) -> Fetched:
        p.parent.mkdir(parents=True, exist_ok=True)
        sha = hashlib.sha256(body).hexdigest() if body is not None else ""
        captured = self.now().isoformat(timespec="seconds")
        if body is not None:
            p.write_bytes(body)
        meta = {"url": url, "status": status, "sha256": sha, "captured_at": captured}
        p.with_name(p.name + ".meta.json").write_text(json.dumps(meta), "utf-8")
        return Fetched(url, status, body, sha, captured, p)

    # -- requête -----------------------------------------------------------------------------
    def fetch(
        self,
        service: str,
        ark: str,
        relpath: str,
        *,
        allow_404: bool | tuple[int, ...] = False,
        **kw,
    ) -> Fetched:
        """Cache d'abord ; sinon une requête limitée. 404 mis en cache si `allow_404`."""
        p = self.cache_path(ark, relpath)
        hit = self._read_cache(p)
        if hit is not None:
            self.stats.cache_hits += 1
            return hit
        if self.stop_file.exists():
            raise GallicaStop(f"{self.stop_file} présent : arrêt précédent après 403/429")
        url = self.url(service, ark, **kw)
        attempts = 0
        while True:
            attempts += 1
            self.limiter.acquire(service)
            self.stats.count(service)
            try:
                status, headers, body = self.opener(
                    url, {"User-Agent": USER_AGENT, "Accept": "*/*"}
                )
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                status, headers, body = 0, {}, str(e).encode()[:200]
            self.limiter.record_bytes(service, len(body))
            if status == 200:
                return self._write_cache(p, url, 200, body)
            self.stats.error(service, status)
            if status in (403, 429):
                self.stops += 1
                ra = {k.lower(): v for k, v in headers.items()}.get("retry-after", "")
                if self.stops >= self.max_stops:
                    self.cache_root.mkdir(parents=True, exist_ok=True)
                    self.stop_file.write_text(
                        json.dumps({"status": status, "url": url, "at": self.now().isoformat()}),
                        "utf-8",
                    )
                    raise GallicaStop(f"{status} sur {url} (arrêt après {self.stops})")
                self.limiter.block(float(ra) if ra.isdigit() else 60.0)
                continue
            if allow_404 and status in ((404,) if allow_404 is True else allow_404):
                return self._write_cache(p, url, 404, None)
            if (status == 0 or status >= 500) and attempts < 2:
                self.stats.transient_retries += 1
                self.limiter.block(10.0)
                continue
            raise GallicaHTTPError(status, url)

    # -- services nommés --------------------------------------------------------------------
    def oai(self, ark: str) -> Fetched:
        return self.fetch("oai", ark, "oai.xml")

    def pagination(self, ark: str) -> Fetched:
        return self.fetch("pagination", ark, "pagination.xml")

    def toc(self, ark: str) -> Fetched:
        return self.fetch("toc", ark, "toc.xml", allow_404=(400, 404))

    def manifest(self, ark: str) -> Fetched:
        return self.fetch("manifest", ark, "manifest.json")

    def texte_brut(self, ark: str) -> Fetched:
        return self.fetch("textebrut_doc", ark, "texteBrut.txt")

    def alto(self, ark: str, n: int) -> Fetched:
        """ALTO de la vue n : IIIF v3, puis repli RequestDigitalElement si le v3 répond 404.
        Après trois 404 v3 suivis d'un succès RDE, RDE est essayé en premier (moitié moins de
        requêtes) ; chaque réponse, 404 compris, est mise en cache."""
        order = ["alto_rde", "alto"] if self.rde_first else ["alto", "alto_rde"]
        last = None
        for svc in order:
            rel = f"alto/f{n}.xml" if svc == "alto" else f"alto_rde/f{n}.xml"
            f = self.fetch(svc, ark, rel, allow_404=True, n=n)
            last = last or f
            if f.status == 200:
                if svc == "alto_rde" and not self.rde_first and self.v3_404_streak >= 3:
                    self.rde_first = True
                self.v3_404_streak = self.v3_404_streak if svc == "alto_rde" else 0
                return f
            if svc == "alto":
                self.v3_404_streak += 1
        return last

    def medres(self, ark: str, n: int) -> Fetched:
        return self.fetch("medres", ark, f"medres/f{n}.jpg", n=n)


def iiif_region_url(ark: str, n: int, region: tuple[float, float, float, float], width: int = 800):
    """IIIF Image v2, région en pourcentages (bbox normalisée x0,y0,x1,y1), largeur <= 800."""
    a = bare_ark(ark)
    x0, y0, x1, y1 = region
    w = min(int(width), 800)
    pct = f"pct:{x0 * 100:.2f},{y0 * 100:.2f},{(x1 - x0) * 100:.2f},{(y1 - y0) * 100:.2f}"
    return f"{BASE}/image/iiifv2/gallica/1.0.0/ark:/12148/{a}/f{n}/{pct}/{w},/0/default.jpg"


def split_textebrut(raw: bytes) -> list[str]:
    """Pages du texte brut document entier (séparateur `</BR>`), `<br/>` -> saut de ligne."""
    text = raw.decode("utf-8", errors="replace")
    pages = re.split(r"</BR>", text, flags=re.IGNORECASE)
    out = []
    for p in pages:
        p = re.sub(r"<br\s*/?>", "\n", p, flags=re.IGNORECASE)
        p = re.sub(r"<[^>]+>", "", p)
        out.append(p.strip("\n"))
    return out
