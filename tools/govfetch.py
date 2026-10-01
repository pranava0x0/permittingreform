#!/usr/bin/env python3
"""govfetch: reusable fetch/cache/validate primitives for government and
public-agency data sources — the working code behind the government-data
skill's prose.

Stdlib-only by design (this repo runs with zero installs); every function
here is a small, independently-testable primitive rather than a framework —
compose them into your own fetch loop instead of inheriting from one.

The donors, anonymized, by what each contributed:

  Project A's connectors/base.py           IPv4-preference DNS monkeypatch
                                            (IPv6-blackhole timeout fix)
  Project A's connectors/epa_echo.py       embedded-error-in-200 detection,
                                            type-code-over-label filtering
  Project B's utils/http_client.py         rate-limited fetch shape, the
                                            encoding-mangle fix it needed
  Project C's scripts/lib/source-cache.mjs content-addressed cache, the
                                            wall-page marker list, the
                                            >50%-failed circuit breaker
  Project D's tools/validate-comments.py   scanned-PDF text-threshold check
  Project D's tools/organize-comment-files a Content-Disposition filename
             .py                           truncation fix
  Project E's scripts/freshness.py         HEAD-vs-manifest freshness probe
  Project E's scripts/portal_api.py        namespace-stripping for
                                            undocumented gov XML
  Project F's connectors/extract.py        publication-date extraction chain
  Project G's source-cache.mjs (claim      claim-term extraction + fuzzy
             verification helpers)         matching for citation checks
  Project G's federal-register workaround  known-per-host API escape hatches

Every one of these was reimplemented from the pattern, not copy-pasted —
the originals are project-coupled (specific field names, specific directory
layouts); what's here is the reusable core.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse

LOG = logging.getLogger("govfetch")

DEFAULT_USER_AGENT = (
    "govfetch/1.0 (personal research tool; set a project-specific "
    "User-Agent via the `headers` argument before real use)"
)

# ---------------------------------------------------------------------------
# 1. IPv4-preference DNS (IPv6-blackhole workaround)
# ---------------------------------------------------------------------------
# Many .gov / ArcGIS / Census hosts resolve AAAA-first. On a network where the
# IPv6 path silently blackholes (no RST, just a stall), a naive client burns
# its *entire* timeout on the v6 attempt before falling back to v4 — measured
# elsewhere at 60s per call instead of 0.6s, turning a 20-minute job into a
# multi-hour one. This patch is process-wide and idempotent (safe to call
# more than once, and to call with enabled=False to restore stock behavior).

_original_getaddrinfo = socket.getaddrinfo


def prefer_ipv4(enabled: bool = True) -> None:
    """Pin DNS resolution to IPv4-only (or restore default resolution)."""
    if enabled:
        if getattr(socket.getaddrinfo, "_ipv4_pinned", False):
            return

        def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
            return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

        _ipv4_only._ipv4_pinned = True  # type: ignore[attr-defined]
        socket.getaddrinfo = _ipv4_only
    else:
        socket.getaddrinfo = _original_getaddrinfo


# ---------------------------------------------------------------------------
# 2. Response classification: dead / blocked / ok
# ---------------------------------------------------------------------------
# Conflating these either raises false "the government took this down" alarms
# (a live-but-bot-walled host reported as dead) or lets a real dead link pass
# as fine (a permanent 404 retried into a false "still there").

DEAD_STATUSES = {404, 410}
BLOCKED_STATUSES = {401, 402, 403, 406, 409, 429, 451, 500, 503}


def classify_status(status: int) -> str:
    """Return "ok", "dead", or "blocked" for an HTTP status code."""
    if 200 <= status < 300:
        return "ok"
    if status in DEAD_STATUSES:
        return "dead"
    if status in BLOCKED_STATUSES:
        return "blocked"
    return "dead"  # an unrecognized 4xx is rarely a bot-wall; default dead


class GovFetchError(Exception):
    """Base class for govfetch's own raised errors."""


class HostNotAllowedError(GovFetchError):
    pass


class NetworkHealthError(GovFetchError):
    """Raised by check_failure_rate when too much of a batch failed to trust
    the results — re-run rather than believing a mostly-failed pass."""


# ---------------------------------------------------------------------------
# 3. Wall / interstitial detection, and success-shaped failures
# ---------------------------------------------------------------------------
# A bot-wall or a soft rate-limit frequently arrives as a normal 200 — an
# interstitial page, or a JSON body whose *content* (not its status code) is
# the actual error. Status-code-based retry logic never sees either as a
# failure.

WALL_MARKERS = (
    "request access",
    "due to aggressive automated scraping",
    "just a moment",
    "attention required",
    "verify you are human",
    "checking your browser",
    "robotic or programmed query",
    "robotic query",
)


def looks_like_wall(text: str, min_chars: int = 800) -> bool:
    """True if `text` reads like an interstitial/bot-wall page rather than
    real content: a known marker phrase, or suspiciously little text for
    what was supposed to be a real document (a client-rendered SPA shell
    fetched without a browser lands here too)."""
    if not text or len(text.strip()) < min_chars:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in WALL_MARKERS)


def find_embedded_error(payload, marker_words: Iterable[str] = ("robotic", "blocked", "denied")) -> Optional[str]:
    """Walk a parsed JSON payload (dict/list/str, arbitrarily nested) for a
    string value containing one of `marker_words` — the shape of an API that
    soft-blocks with a normal 200 and an error message buried at an
    unpredictable depth (sometimes top-level, sometimes under a results key).
    Returns the offending string, or None."""
    stack = [payload]
    lowered_markers = [m.lower() for m in marker_words]
    while stack:
        node = stack.pop()
        if isinstance(node, str):
            low = node.lower()
            if any(m in low for m in lowered_markers):
                return node
        elif isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


# ---------------------------------------------------------------------------
# 4. Backoff scheduling and per-host rate limiting
# ---------------------------------------------------------------------------

def backoff_delay(attempt: int, *, blocked: bool = False, base: float = 2.0) -> float:
    """Seconds to wait before retry `attempt` (1-indexed). A `blocked`
    response (429 and friends) gets steeper, multiplicative backoff than a
    generic transient failure."""
    if attempt < 1:
        attempt = 1
    if blocked:
        return min(10.0 * (3 ** (attempt - 1)), 480.0)  # 10s, 30s, 90s, ... capped
    return base * (2 ** (attempt - 1))  # 2s, 4s, 8s, ...


@dataclass
class HostRateLimiter:
    """Track last-request time per host and sleep the remainder of a fixed
    interval before the next call to that host — so parallel work against a
    *different* host isn't slowed by one slow one."""

    min_interval: float = 2.0
    jitter: float = 1.0
    _last_call: dict = field(default_factory=dict)
    _sleep_fn: Callable[[float], None] = time.sleep
    _clock: Callable[[], float] = time.monotonic

    def wait(self, host: str) -> float:
        """Sleep if needed; returns the actual seconds slept (0.0 if none),
        useful for tests that want to assert without truly sleeping."""
        now = self._clock()
        last = self._last_call.get(host)
        delay = 0.0
        if last is not None:
            elapsed = now - last
            target = self.min_interval + (self.jitter * 0.5)
            if elapsed < target:
                delay = target - elapsed
                self._sleep_fn(delay)
        self._last_call[host] = self._clock()
        return delay


def check_failure_rate(attempted: int, failed: int, threshold: float = 0.5) -> None:
    """Raise NetworkHealthError if more than `threshold` of a batch failed —
    the signal is usually "the network (or the host) is down right now," not
    "every one of these records is actually broken." Silently writing that
    result as if it were real data (a wave of dead links, an empty dataset)
    is worse than aborting loudly and re-running later."""
    if attempted <= 0:
        return
    if failed / attempted > threshold:
        raise NetworkHealthError(
            f"{failed}/{attempted} fetches failed ({failed / attempted:.0%}) — "
            "network looks down; re-run rather than trusting this pass"
        )


# ---------------------------------------------------------------------------
# 5. Safe text decoding
# ---------------------------------------------------------------------------

def decode_text(raw: bytes, content_type: Optional[str]) -> str:
    """Decode response bytes using the charset the server actually declared;
    fall back to UTF-8 with replacement rather than a fixed legacy codepage
    that silently mangles non-ASCII text (an em-dash rendered as garbage
    bytes reads as "fine" until someone spots it in the output)."""
    charset = "utf-8"
    if content_type:
        match = re.search(r"charset=([\w-]+)", content_type, re.I)
        if match:
            charset = match.group(1)
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 6. Content-addressed cache with a manifest, and a freshness probe
# ---------------------------------------------------------------------------

@dataclass
class CacheEntry:
    url: str
    fetched_at: str
    sha256: str
    content_type: Optional[str]
    byte_size: int
    final_url: str


class SourceCache:
    """Content-addressed cache: raw bytes on disk keyed by a hash of the
    request URL, plus a sorted manifest (clean diffs) recording provenance
    for every entry. A later re-verification checks the exact bytes
    originally captured even if the live page has since changed or died."""

    def __init__(self, cache_dir: Path, manifest_path: Optional[Path] = None):
        self.cache_dir = Path(cache_dir)
        self.manifest_path = manifest_path or (self.cache_dir / "index.json")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key_for(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def path_for(self, url: str) -> Path:
        return self.cache_dir / self.key_for(url)

    def has(self, url: str) -> bool:
        return self.path_for(url).exists()

    def get(self, url: str) -> Optional[bytes]:
        path = self.path_for(url)
        return path.read_bytes() if path.exists() else None

    def put(self, url: str, content: bytes, *, content_type: Optional[str] = None,
            final_url: Optional[str] = None, fetched_at: Optional[str] = None) -> CacheEntry:
        self.path_for(url).write_bytes(content)
        entry = CacheEntry(
            url=url,
            fetched_at=fetched_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            sha256=hashlib.sha256(content).hexdigest(),
            content_type=content_type,
            byte_size=len(content),
            final_url=final_url or url,
        )
        manifest = self.load_manifest()
        manifest[url] = entry.__dict__
        self.save_manifest(manifest)
        return entry

    def load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def save_manifest(self, manifest: dict) -> None:
        # Sorted keys → clean diffs when the manifest is committed to git.
        # Local change (Permitting Reform Tracker): write to a temp file and rename, so a
        # reader in another thread or process never sees a half-written manifest.
        tmp = self.manifest_path.with_name(f"{self.manifest_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.manifest_path)

    def is_stale(self, url: str, live_content_length: Optional[int]) -> bool:
        """True if a cheap live probe's Content-Length disagrees with the
        byte size recorded at capture time. Caller supplies the live length
        (e.g. from a HEAD request) — this function stays network-free and
        testable. `None` (server didn't report a length) is treated as
        "can't tell, assume fresh" rather than a false-positive staleness."""
        manifest = self.load_manifest()
        entry = manifest.get(url)
        if entry is None:
            return True
        if live_content_length is None:
            return False
        return live_content_length != entry.get("byte_size")


# ---------------------------------------------------------------------------
# 7. Downloaded-file validation and filename healing
# ---------------------------------------------------------------------------

MAGIC_BYTES = {
    b"%PDF-": ".pdf",
    b"PK\x03\x04": ".xlsx",  # also matches .docx/.zip; good enough as a hint
}


def validate_pdf_bytes(content: bytes) -> bool:
    """A server returning 200 with an HTML error page saved under a .pdf
    extension is a more dangerous failure than a clean error code — nothing
    downstream flags it automatically unless this is checked."""
    return content[:5] == b"%PDF-"


def pdf_is_text_extractable(extracted_text: str, min_chars: int = 200) -> bool:
    """A PDF can be a technically-valid file (passes validate_pdf_bytes) and
    still be a scanned image with no real text layer. Pass in whatever your
    PDF library extracted; this just applies the length threshold — distinct
    from the magic-byte check above, which only proves the file isn't a
    disguised HTML error page."""
    stripped = re.sub(r"\s+", "", extracted_text or "")
    return len(stripped) >= min_chars


def heal_filename(raw_filename: str, content: bytes) -> str:
    """Fix two real-world download-naming failures: Chrome's ' (1)' dedupe
    suffix, and a Content-Disposition header truncated at a semicolon that
    strips the real extension entirely. Sniffs magic bytes to restore the
    correct extension when one is missing."""
    name = re.sub(r" \(\d+\)(?=\.[^.]+$|$)", "", raw_filename).strip()
    if "." in Path(name).name:
        return name
    for magic, ext in MAGIC_BYTES.items():
        if content[: len(magic)] == magic:
            return name + ext
    return name


# ---------------------------------------------------------------------------
# 8. Publication-date extraction (JSON-LD -> OpenGraph -> <time> tag)
# ---------------------------------------------------------------------------

_JSONLD_BLOCK = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_OG_DATE_NAMES = (
    "article:published_time",
    "og:published_time",
    "datePublished",
    "parsely-pub-date",
    "publish-date",
    "date",
    "DC.date.issued",
)
_DATE_LIKE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _walk_for_date_keys(node, keys=("datePublished", "dateCreated", "uploadDate")):
    if isinstance(node, dict):
        for key in keys:
            value = node.get(key)
            if isinstance(value, str) and _DATE_LIKE.search(value):
                return value
        for value in node.values():
            found = _walk_for_date_keys(value, keys)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _walk_for_date_keys(item, keys)
            if found:
                return found
    return None


def extract_publication_date(html: str) -> Optional[str]:
    """Try JSON-LD first (most reliable when present), then an OpenGraph/
    meta-name variant list, then a bare <time datetime> tag. Returns the raw
    matched string (caller normalizes/validates), or None rather than
    guessing."""
    for block in _JSONLD_BLOCK.findall(html or ""):
        try:
            data = json.loads(block.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        found = _walk_for_date_keys(data)
        if found:
            return found

    for name in _OG_DATE_NAMES:
        pattern = re.compile(
            rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            re.I,
        )
        match = pattern.search(html or "")
        if match:
            return match.group(1)

    time_match = re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', html or "", re.I)
    if time_match:
        return time_match.group(1)

    return None


# ---------------------------------------------------------------------------
# 9. Namespace-stripping for undocumented government XML/SOAP feeds
# ---------------------------------------------------------------------------

def strip_xml_namespaces(xml_text: str) -> str:
    """Regex-strip xmlns declarations and element/attribute prefixes so
    ElementTree can parse a namespaced, undocumented government XML feed
    without fighting its namespace API (`{uri}tag` lookups everywhere)."""
    text = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", xml_text)
    text = re.sub(r"<(/?)\w+:", r"<\1", text)  # element prefixes
    text = re.sub(r'(\s)\w+:(\w+=")', r"\1\2", text)  # attribute prefixes
    return text


# ---------------------------------------------------------------------------
# 10. Claim-term extraction and fuzzy matching (citation verification)
# ---------------------------------------------------------------------------

_UNIT_NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s?[A-Za-z]{1,4}\b")
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_CAP_PHRASE = re.compile(r"\b[A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*)+\b")


def extract_claim_terms(label: str) -> list:
    """Pull checkable terms out of a claim label for citation verification:
    unit-bearing numbers ("345 MWe"), ISO-ish dates, and capitalized
    multi-word names. Deliberately skips the label's first word — it's
    capitalized regardless of content (sentence case), which produces
    reliable false positives like "Secured" or "Selected" read as a proper
    noun."""
    rest = label.split(" ", 1)[1] if " " in label else ""
    terms = set(_UNIT_NUMBER.findall(label))
    terms.update(_ISO_DATE.findall(label))
    terms.update(_CAP_PHRASE.findall(rest))
    return sorted(terms)


def _normalize_unit_term(term: str) -> str:
    """345 MWe <-> 345-MW style normalization: strip spaces/hyphens, drop a
    trailing lowercase qualifier letter after the unit (e/th/etc.)."""
    collapsed = re.sub(r"[\s-]+", "", term)
    return re.sub(r"([A-Z]+)[a-z]+$", r"\1", collapsed)


def fuzzy_contains(haystack: str, term: str) -> bool:
    """True if `term` (or a unit/hyphen-normalized variant of it) appears in
    `haystack`. A single fixed-format match against real-world prose misses
    the same value written several equally-valid ways."""
    if term in haystack:
        return True
    normalized_term = _normalize_unit_term(term)
    normalized_haystack = re.sub(r"[\s-]+", "", haystack)
    return normalized_term in normalized_haystack


# ---------------------------------------------------------------------------
# 11. Known per-host API escape hatches
# ---------------------------------------------------------------------------
# Some .gov hosts block scripted page fetches entirely but expose an
# undocumented-to-casual-users JSON API for the same content, keyed off
# something in the page URL. This registry makes that pattern extensible
# instead of a one-off `if "federalregister.gov" in url` scattered in caller
# code.

_ApiEscapeResolver = Callable[[str], Optional[str]]
_API_ESCAPES: dict = {}


def register_api_escape(host_fragment: str, resolver: _ApiEscapeResolver) -> None:
    _API_ESCAPES[host_fragment] = resolver


def resolve_api_escape(url: str) -> Optional[str]:
    """Return an alternate API URL for a known host, or None."""
    host = urlparse(url).netloc.lower()
    for fragment, resolver in _API_ESCAPES.items():
        if fragment in host:
            alt = resolver(url)
            if alt:
                return alt
    return None


def _federal_register_escape(url: str) -> Optional[str]:
    match = re.match(
        r"^https://(?:www\.)?federalregister\.gov/documents/\d{4}/\d{2}/\d{2}/([^/]+)/",
        url,
    )
    if match:
        return f"https://www.federalregister.gov/api/v1/documents/{match.group(1)}.json"
    return None


register_api_escape("federalregister.gov", _federal_register_escape)


# ---------------------------------------------------------------------------
# 12. Login-wall and SPA-shell heuristics
# ---------------------------------------------------------------------------

_LOGIN_URL_MARKERS = ("login", "signin", "sign-in", "auth", "sso")
_PASSWORD_FIELD = re.compile(r'type=["\']password["\']', re.I)


def looks_like_login_wall(final_url: str, html: str) -> bool:
    """True if a fetch that "succeeded" actually landed on a login page —
    checked by URL shape *and* the presence of a password field, so a page
    that merely mentions "login" in a nav link doesn't false-positive."""
    host_path = urlparse(final_url).path.lower()
    url_says_login = any(marker in host_path for marker in _LOGIN_URL_MARKERS)
    has_password_field = bool(_PASSWORD_FIELD.search(html or ""))
    return url_says_login and has_password_field


def looks_like_spa_shell(text: str, min_chars: int = 600) -> bool:
    """A 200 response with real-looking headers but under `min_chars` of
    actual text is very likely a client-rendered app shell fetched without a
    browser to run its JS — distinct from a wall page (which usually has
    marker text); this one just has almost nothing at all."""
    return len((text or "").strip()) < min_chars


# ---------------------------------------------------------------------------
# 13. Host allowlisting
# ---------------------------------------------------------------------------

def enforce_host_allowlist(url: str, allowed_hosts: Iterable[str]) -> None:
    """Raise HostNotAllowedError unless `url`'s host is in (or a subdomain
    of) an allowed host. Call this before writing any downloaded file to
    disk — it stops a redirect chain, a typo'd source URL, or a compromised
    mirror from silently substituting a non-authoritative document into a
    dataset that's supposed to be official."""
    host = urlparse(url).netloc.lower()
    for allowed in allowed_hosts:
        allowed = allowed.lower()
        if host == allowed or host.endswith("." + allowed):
            return
    raise HostNotAllowedError(f"{host!r} is not in the allowlist {sorted(allowed_hosts)!r}")


# ---------------------------------------------------------------------------
# 14. macOS textutil: zero-dependency DOC/DOCX-to-text extraction
# ---------------------------------------------------------------------------

def extract_text_via_textutil(path: Path) -> str:
    """Extract plain text from a .doc/.docx (or .rtf) file using macOS's
    built-in `textutil` — no library dependency, but macOS-only."""
    if sys.platform != "darwin":
        raise GovFetchError("extract_text_via_textutil requires macOS (textutil)")
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout
