"""Cached, rate-limited page reads for the link and quote checkers.

One entry point, read(url), which returns what a checker needs: a class
(ok / blocked / dead / error), the HTTP status, and the page's readable text.

Platforms that serve nothing useful to a plain GET are read through their
public, keyless endpoints instead:
  X posts        publish.twitter.com/oembed      (post text and author)
  Bluesky posts  public.api.bsky.app             (post text and author)
  YouTube        youtube.com/oembed              (title and channel only)
  Federal Register documents                     (their JSON API)

Raw responses are cached under data/cache/pages/ so a re-run reads the same
bytes; pass refresh=True to fetch again. Built on tools/govfetch.py.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

import govfetch

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data/cache/pages"
STATUS_PATH = ROOT / "data/cache/fetch_status.json"
USER_AGENT = "Mozilla/5.0 (compatible; PermittingReformTracker/1.0; +https://github.com/pranava0x0/permittingreform)"
TIMEOUT = 25
MAX_BYTES = 4_000_000

BLOCKED = {401, 402, 403, 405, 406, 429, 451, 999}
DEAD = {404, 410}

_cache = govfetch.SourceCache(CACHE_DIR)
_limiter = govfetch.HostRateLimiter(min_interval=1.5, jitter=0.6)
_host_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_status_guard = threading.Lock()
_cache_guard = threading.Lock()  # the cache manifest is one file: read-modify-write must not interleave


def _cache_put(target: str, content: bytes, ctype, final_url: str) -> None:
    with _cache_guard:
        _cache.put(target, content, content_type=ctype, final_url=final_url)


def _cache_get(target: str):
    """Cached bytes (or None) and the content type recorded with them."""
    with _cache_guard:
        return _cache.get(target), (_cache.load_manifest().get(target) or {}).get("content_type")


@dataclass
class Page:
    url: str
    cls: str            # ok | blocked | dead | error
    status: int | None
    kind: str           # page | pdf | x | bluesky | youtube | federal_register
    text: str
    note: str
    checked: str
    final_url: str = ""


def route(url: str) -> tuple[str, str]:
    """Return (kind, url_to_request). Platform posts go to their public endpoints."""
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.").removeprefix("mobile.")
    if host in ("x.com", "twitter.com") and "/status/" in parts.path:
        return "x", "https://publish.twitter.com/oembed?omit_script=1&dnt=1&url=" + quote(url, safe="")
    m = re.match(r"^/profile/([^/]+)/post/([^/?#]+)", parts.path)
    if host == "bsky.app" and m:
        uri = f"at://{m.group(1)}/app.bsky.feed.post/{m.group(2)}"
        return "bluesky", "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?depth=0&uri=" + quote(uri, safe="")
    if host in ("youtube.com", "m.youtube.com", "youtu.be"):
        return "youtube", "https://www.youtube.com/oembed?format=json&url=" + quote(url, safe="")
    escape = govfetch.resolve_api_escape(url)
    if escape:
        return "federal_register", escape
    return "page", url


# Inline elements add no space when a browser lays out the text, so their tags are
# removed without one: "inter<span>regional</span>" reads "interregional".
INLINE_TAGS = "a|abbr|b|bdi|bdo|cite|code|data|del|dfn|em|font|i|ins|kbd|mark|q|s|samp|small|span|strong|sub|sup|time|u|var|wbr"


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg|template)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|tr|blockquote|section|article)>", "\n", raw)
    raw = re.sub(rf"(?is)</?(?:{INLINE_TAGS})\b[^>]*>", "", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"[ \t\r\f\v]+", " ", raw)


def pdf_to_text(content: bytes, max_pages: int = 40) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:max_pages])
    except Exception as exc:  # a malformed PDF is a finding, not a crash
        return f"[pdf text could not be extracted: {exc}]"


def _json_strings(node, keys: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if k in keys and isinstance(v, str):
                    out.append(v)
                else:
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
    return out


def extract_text(kind: str, content: bytes, content_type: str | None) -> str:
    if kind == "pdf" or content[:5] == b"%PDF-":
        return pdf_to_text(content)
    decoded = govfetch.decode_text(content, content_type)
    if kind in ("x", "youtube", "bluesky", "federal_register"):
        try:
            payload = json.loads(decoded)
        except ValueError:
            return html_to_text(decoded)
        if kind == "x":
            return html_to_text(payload.get("html", "")) + "\n" + payload.get("author_name", "")
        if kind == "youtube":
            return payload.get("title", "") + "\n" + payload.get("author_name", "")
        if kind == "bluesky":
            return "\n".join(_json_strings(payload, ("text", "displayName", "handle", "title", "description")))
        return "\n".join(html_to_text(s) for s in _json_strings(payload, ("title", "abstract", "body_html_url", "action", "dates", "type")))
    return html_to_text(decoded)


def _curl_into(page: "Page", target: str) -> bool:
    """Last resort for hosts whose TLS setup this Python cannot talk to. True if curl got an answer."""
    try:
        out = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", str(TIMEOUT), "-A", USER_AGENT, "-o", "-", "-w", "\n%{http_code} %{content_type}", target],
            capture_output=True, timeout=TIMEOUT + 5, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    body, _, tail = out.stdout.rpartition(b"\n")
    parts = tail.decode("ascii", "replace").split(" ", 1)
    if out.returncode != 0 or not parts[0].isdigit():
        return False
    status = int(parts[0])
    ctype = parts[1] if len(parts) > 1 else None
    page.status, page.final_url = status, target
    if 200 <= status < 300:
        page.cls, page.note = "ok", "read with curl"
        page.text = extract_text(page.kind, body[:MAX_BYTES], ctype)
        _cache_put(target, body[:MAX_BYTES], ctype, target)
    elif status in DEAD:
        page.cls, page.note = "dead", f"HTTP {status}"
    elif status in BLOCKED:
        page.cls, page.note = "blocked", f"HTTP {status}"
    else:
        page.cls, page.note = "error", f"HTTP {status}"
    return True


def _host_lock(host: str) -> threading.Lock:
    with _locks_guard:
        return _host_locks.setdefault(host, threading.Lock())


def _load_status() -> dict:
    if STATUS_PATH.exists():
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    return {}


def _save_status(url: str, page: Page) -> None:
    with _status_guard:
        data = _load_status()
        row = asdict(page)
        row.pop("text")
        data[url] = row
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATUS_PATH.with_name(f"{STATUS_PATH.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, STATUS_PATH)  # readers in other threads never see a half-written file


def read(url: str, *, refresh: bool = False) -> Page:
    """Fetch (or read from cache) one URL and classify the result."""
    kind, target = route(url)
    now = time.strftime("%Y-%m-%d", time.gmtime())
    if not refresh:
        prior = _load_status().get(url)
        if prior and prior["cls"] != "error":
            cached, ctype = _cache_get(target) if prior["cls"] == "ok" else (b"", None)
            if cached is not None:
                text = extract_text(prior["kind"], cached, ctype) if cached else ""
                return Page(url=url, text=text, **{k: prior[k] for k in ("cls", "status", "kind", "note", "checked", "final_url")})

    host = urlsplit(target).netloc.lower()
    page = Page(url=url, cls="error", status=None, kind=kind, text="", note="", checked=now)
    for attempt in (1, 2):
        with _host_lock(host):
            _limiter.wait(host)
            req = urllib.request.Request(target, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/json,application/pdf;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            })
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    content = resp.read(MAX_BYTES)
                    ctype = resp.headers.get("Content-Type")
                    page.status = resp.status
                    page.final_url = resp.geturl()
                    if "pdf" in (ctype or "").lower() or content[:5] == b"%PDF-":
                        page.kind = "pdf" if kind == "page" else kind
                    page.text = extract_text(page.kind, content, ctype)
                    page.cls = "ok"
                    if page.kind == "page":
                        if govfetch.looks_like_login_wall(page.final_url, govfetch.decode_text(content, ctype)):
                            page.cls, page.note = "blocked", "login wall"
                        elif any(mark in page.text.lower() for mark in govfetch.WALL_MARKERS) and len(page.text) < 4000:
                            page.cls, page.note = "blocked", "interstitial page"
                        elif govfetch.looks_like_spa_shell(page.text, 300):
                            page.note = "little readable text (script-rendered page)"
                    if page.cls == "ok":
                        _cache_put(target, content, ctype, page.final_url)
                break
            except urllib.error.HTTPError as exc:
                location = exc.headers.get("Location") if exc.code in (307, 308) else None
                if location and attempt == 1:
                    target = urljoin(target, location)  # older urllib does not follow a 308
                    host = urlsplit(target).netloc.lower()
                    continue
                page.status = exc.code
                page.final_url = exc.geturl() or target
                if exc.code in DEAD:
                    page.cls, page.note = "dead", f"HTTP {exc.code}"
                elif exc.code in BLOCKED:
                    page.cls, page.note = "blocked", f"HTTP {exc.code}"
                else:
                    page.cls, page.note = "error", f"HTTP {exc.code}"
                if exc.code < 500:
                    break  # a wall or a missing page will not change on retry
            except Exception as exc:  # timeouts, DNS, TLS, resets
                page.cls, page.note = "error", f"{type(exc).__name__}: {exc}"[:160]
                if attempt == 2 and _curl_into(page, target):
                    break
        if attempt == 1 and page.cls == "error":
            time.sleep(govfetch.backoff_delay(1))
    _save_status(url, page)
    return page
