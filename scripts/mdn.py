#!/usr/bin/env python3
"""
mdn.py — retrieve MDN front-end web docs straight from the mdn/content GitHub
repo (raw Markdown), with a shipped slug->path index and on-disk caching.

Stdlib only. Subcommands:

  find <query>                       semantic search via developer.mozilla.org
                                     /api/v1/search; auto-reads the top hit
  get <slug | MDN-url | repo-path>   read a doc (light KumaScript cleanup)
  search <query>                     fuzzy-find a doc in the local index
                                     (slug-only; offline-capable)
  browse <slug-prefix>               list immediate children of a slug
  refresh                            rebuild index/web-docs.tsv from GitHub

If the first argument is not one of the known verbs, all arguments are
treated as a `find` query (so `mdn.py css grid layout` == `mdn.py find css
grid layout`). See reference.md for slug rules, macro table, cache layout
and environment variables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths / constants
# --------------------------------------------------------------------------- #

SKILL_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = SKILL_DIR / "index" / "web-docs.tsv"
REDIRECTS_FILE = SKILL_DIR / "index" / "redirects.tsv"
REDIRECTS_RAW = "files/en-us/_redirects.txt"
CACHE_DIR = SKILL_DIR / ".cache"
CONTENT_CACHE = CACHE_DIR / "content"
TREE_CACHE = CACHE_DIR / "trees"
FIND_CACHE = CACHE_DIR / "find"

REPO = "mdn/content"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
API_BASE = f"https://api.github.com/repos/{REPO}/git/trees/"
MDN_BASE = "https://developer.mozilla.org/en-US/docs/"
MDN_SEARCH_API = "https://developer.mozilla.org/api/v1/search"
FIND_TTL = int(os.environ.get("MDN_FIND_TTL", str(24 * 3600)))  # 1 day

# Scope: which top-level files/en-us/ areas the index covers.
SCOPE_PREFIXES = ("files/en-us/web/", "files/en-us/glossary/")

DEFAULT_TTL = int(os.environ.get("MDN_CACHE_TTL", str(7 * 24 * 3600)))
HTTP_TIMEOUT = 30
USER_AGENT = "web-api-docs-skill (+https://github.com/mdn/content reader)"


# --------------------------------------------------------------------------- #
# slug -> folder  (verbatim mirror of mdn/yari libs/slug-utils slugToFolder
# plus the npm `sanitize-filename` package it applies per path segment)
# --------------------------------------------------------------------------- #

_ILLEGAL_RE = re.compile(r'[/?<>\\:*|"]')
_CONTROL_RE = re.compile(r"[\x00-\x1f\x80-\x9f]")
_RESERVED_RE = re.compile(r"^\.+$")
_WIN_RESERVED_RE = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", re.I)
_WIN_TRAILING_RE = re.compile(r"[. ]+$")


def _sanitize_filename(seg: str, replacement: str = "") -> str:
    s = _ILLEGAL_RE.sub(replacement, seg)
    s = _CONTROL_RE.sub(replacement, s)
    s = _RESERVED_RE.sub(replacement, s)
    s = _WIN_RESERVED_RE.sub(replacement, s)
    s = _WIN_TRAILING_RE.sub(replacement, s)
    return s.encode("utf-8")[:255].decode("utf-8", "ignore")


def slug_to_folder(slug: str) -> str:
    """Mirror of yari slugToFolder: order matters (:: before :)."""
    s = slug.replace("*", "_star_")
    s = s.replace("::", "_doublecolon_")
    s = s.replace(":", "_colon_")
    s = s.replace("?", "_question_")
    s = s.lower()
    return "/".join(_sanitize_filename(p) for p in s.split("/"))


def folder_to_slug(folder: str) -> str:
    """Best-effort inverse for display/search (casing cannot be restored)."""
    s = folder.replace("_doublecolon_", "::")
    s = s.replace("_colon_", ":")
    s = s.replace("_star_", "*")
    s = s.replace("_question_", "?")
    return s


def slug_from_repo_path(repo_path: str) -> str:
    inner = repo_path[len("files/en-us/"):]
    if inner.endswith("/index.md"):
        inner = inner[: -len("/index.md")]
    return folder_to_slug(inner)


def section_from_repo_path(repo_path: str) -> str:
    inner = repo_path[len("files/en-us/"):]
    parts = inner.split("/")
    if parts and parts[0] == "web" and len(parts) > 1:
        return "web/" + parts[1]
    return parts[0] if parts else ""


def input_to_slug(arg: str):
    """Classify an input as ('path', repo_path) or ('slug', slug)."""
    a = arg.strip()
    if a.startswith("http://") or a.startswith("https://"):
        a = a.split("#", 1)[0].split("?", 1)[0]
        m = re.search(r"/docs/(.+)$", a)
        if not m:
            raise ValueError(f"could not extract a slug from URL: {arg!r}")
        a = m.group(1)
    if a.startswith("files/en-us/") and a.endswith("index.md"):
        return "path", a
    return "slug", a.strip("/")


def repo_path_from_input(arg: str) -> str:
    """Pure encoder (no redirect resolution): input -> repo_path."""
    kind, val = input_to_slug(arg)
    if kind == "path":
        return val
    return "files/en-us/" + slug_to_folder(val) + "/index.md"


_DOCS_PREFIX = "/en-us/docs/"


def _strip_docs_prefix(s: str) -> str:
    s = s.split("#", 1)[0].split("?", 1)[0]
    low = s.lower()
    i = low.find(_DOCS_PREFIX)
    if i != -1:
        return s[i + len(_DOCS_PREFIX):]
    return s


_REDIRECTS = None


def load_redirects() -> dict:
    """Lazy-load the shipped redirect map: lower(from_slug) -> to_slug."""
    global _REDIRECTS
    if _REDIRECTS is not None:
        return _REDIRECTS
    _REDIRECTS = {}
    if REDIRECTS_FILE.exists():
        for line in REDIRECTS_FILE.read_text().splitlines():
            if not line or "\t" not in line:
                continue
            k, v = line.split("\t", 1)
            _REDIRECTS[k] = v
    return _REDIRECTS


def resolve_slug(slug: str) -> str:
    """Follow MDN redirects (depth-capped, cycle-safe). Misses fall through."""
    red = load_redirects()
    if not red:
        return slug
    cur = slug
    for _ in range(5):
        key = cur.strip("/").lower()
        nxt = red.get(key)
        if nxt is None or nxt.strip("/").lower() == key:
            break
        cur = nxt
    return cur


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


def _http(url: str, headers: dict | None = None):
    """GET with retries. Returns (status, body_bytes, resp_headers)."""
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    last_err = None
    for attempt in range(3):
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return 304, b"", dict(e.headers or {})
            if e.code in (429,) or 500 <= e.code < 600:
                last_err = e
            else:
                return e.code, e.read() if hasattr(e, "read") else b"", dict(e.headers or {})
        except urllib.error.URLError as e:
            last_err = e
        time.sleep((2 ** attempt) + 0.3)
    raise RuntimeError(f"request failed after retries: {url} ({last_err})")


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


# --------------------------------------------------------------------------- #
# KumaScript light cleanup
# --------------------------------------------------------------------------- #

_MACRO_RE = re.compile(r"\\?\{\{\s*([A-Za-z0-9_.\-]+)\s*(?:\(([^}]*)\))?\s*\}\}")

# name (lowercase) -> short inline badge
_BADGE = {
    "deprecated_inline": " *(deprecated)*",
    "experimental_inline": " *(experimental)*",
    "non-standard_inline": " *(non-standard)*",
    "optional_inline": " *(optional)*",
    "readonlyinline": " *(read-only)*",
    "securecontext_inline": " *(secure context)*",
}
# name -> fixed block note
_BANNER = {
    "deprecated_header": "> **Deprecated.** This feature is no longer recommended.",
    "non-standard_header": "> **Non-standard.** Check cross-browser support before use.",
    "seecompattable": "> **Experimental.** Check browser compatibility before use.",
    "securecontext_header": "> **Secure context.** Available only in secure contexts (HTTPS).",
    "availableinworkers": "> **Available in Workers.**",
}
# name -> block omission marker
_OMIT = {
    "compat": "> _(Browser compatibility table omitted — see MDN.)_",
    "specifications": "> _(Specifications table omitted — see MDN.)_",
    "embedlivesample": "> _(Live sample omitted — see MDN.)_",
    "embedghlivesample": "> _(Live sample omitted — see MDN.)_",
    "livesamplelink": "> _(Live sample link omitted — see MDN.)_",
    "embedinteractiveexample": "> _(Interactive example omitted — see MDN.)_",
    "interactiveexample": "> _(Interactive example omitted — see MDN.)_",
    "embedyoutube": "> _(Video omitted — see MDN.)_",
}
# link/term macros: render the most human arg as inline code
_LINK = {
    "jsxref", "domxref", "cssxref", "htmlelement", "svgelement", "svgattr",
    "httpheader", "httpstatus", "httpmethod", "glossary", "rfc",
    "webextapiref", "ariarole", "ariaattr",
}
# pure navigation / sidebar -> drop
_STRIP_EXACT = {
    "jsref", "cssref", "apiref", "htmlref", "httpsidebar", "jssidebar",
    "csssidebar", "htmlsidebar", "defaultapisidebar", "quicklinkswithsubpages",
    "previousnext", "previous", "next", "previousmenunext", "listsubpages",
    "page", "addonsidebar", "mdnsidebar", "glossarysidebar", "landingpagelistsubpages",
}


def _split_args(raw: str) -> list[str]:
    if raw is None:
        return []
    args, buf, quote = [], [], None
    i = 0
    while i < len(raw):
        c = raw[i]
        if quote:
            if c == "\\" and i + 1 < len(raw):
                buf.append(raw[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            else:
                buf.append(c)
        elif c in ('"', "'"):
            quote = c
        elif c == ",":
            args.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf or args:
        args.append("".join(buf).strip())
    return [a for a in (x.strip().strip("\"'") for x in args)]


def _macro_sub(m: re.Match) -> str:
    name = m.group(1).lower()
    args = _split_args(m.group(2)) if m.group(2) is not None else []

    if name in _STRIP_EXACT or name.endswith("sidebar"):
        return ""
    if name in _BADGE:
        return _BADGE[name]
    if name in _BANNER:
        return _BANNER[name]
    if name in _OMIT:
        return _OMIT[name]
    if name == "rfc":
        n = args[0] if args else ""
        return f"RFC {n}" if n else "RFC"
    if name in _LINK:
        label = args[1] if len(args) > 1 and args[1] else (args[0] if args else "")
        return f"`{label}`" if label else ""
    if name in ("note", "warning", "callout"):
        txt = args[0] if args else ""
        tag = "Warning" if name == "warning" else "Note"
        return f"> **{tag}:** {txt}" if txt else ""
    # Unknown macro: fail-safe — surface a label if one exists, else drop.
    if args:
        return f"`{args[-1] or args[0]}`" if (args[-1] or args[0]) else ""
    return ""


def clean_markdown(md: str) -> str:
    return _MACRO_RE.sub(_macro_sub, md)


# --------------------------------------------------------------------------- #
# Frontmatter
# --------------------------------------------------------------------------- #


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end]
    body = text[end + 4:].lstrip("\n")
    meta = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", line)
        if m:
            meta[m.group(1).strip()] = m.group(2).strip().strip("\"'")
    return meta, body


# --------------------------------------------------------------------------- #
# Content cache
# --------------------------------------------------------------------------- #


def _cache_key(repo_path: str) -> str:
    return hashlib.sha256(repo_path.encode()).hexdigest()


def fetch_doc(repo_path: str, ttl: int, no_cache: bool) -> tuple[str, str]:
    """Return (markdown, status_note). Uses cache + conditional GET."""
    CONTENT_CACHE.mkdir(parents=True, exist_ok=True)
    key = _cache_key(repo_path)
    md_path = CONTENT_CACHE / f"{key}.md"
    meta_path = CONTENT_CACHE / f"{key}.meta"

    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}

    if not no_cache and md_path.exists() and meta:
        age = time.time() - meta.get("fetched_at", 0)
        if age < ttl:
            mins = int(age // 60)
            return md_path.read_text(), f"cache hit (age {mins}m, ttl {ttl // 3600}h)"

    cond = {}
    if not no_cache and md_path.exists():
        if meta.get("etag"):
            cond["If-None-Match"] = meta["etag"]
        elif meta.get("last_modified"):
            cond["If-Modified-Since"] = meta["last_modified"]

    url = RAW_BASE + repo_path
    status, body, headers = _http(url, cond)

    if status == 304 and md_path.exists():
        meta["fetched_at"] = time.time()
        meta_path.write_text(json.dumps(meta))
        return md_path.read_text(), "revalidated (304, content unchanged)"
    if status == 404:
        raise FileNotFoundError(
            f"not found on {REPO}@{BRANCH}: {repo_path}\n"
            f"  the slug may be wrong or moved — try: mdn.py search '<terms>'"
        )
    if status != 200:
        raise RuntimeError(f"HTTP {status} fetching {url}")

    text = body.decode("utf-8", "replace")
    md_path.write_text(text)
    meta = {
        "repo_path": repo_path,
        "fetched_at": time.time(),
        "etag": headers.get("ETag", ""),
        "last_modified": headers.get("Last-Modified", ""),
    }
    meta_path.write_text(json.dumps(meta))
    return text, "fetched (network)"


# --------------------------------------------------------------------------- #
# Index (shipped TSV)
# --------------------------------------------------------------------------- #


def load_index() -> list[tuple[str, str, str]]:
    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            f"index not found: {INDEX_FILE}\n  run: mdn.py refresh"
        )
    rows = []
    for line in INDEX_FILE.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def cmd_search(args):
    rows = load_index()
    q = [t for t in re.split(r"[^a-z0-9]+", args.query.lower()) if t]
    if not q:
        print("empty query", file=sys.stderr)
        return 2
    qjoin = "".join(q)
    scored = []
    for repo_path, section, slug in rows:
        hay = slug.lower()
        last = hay.rsplit("/", 1)[-1]
        score = sum(2 for t in q if t in hay)
        score += sum(3 for t in q if t in last)
        if qjoin and qjoin in hay.replace("/", "").replace("_", ""):
            score += 5
        if last == qjoin:
            score += 10
        if score:
            scored.append((score, slug, section, repo_path))
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    if not scored:
        print("no matches")
        return 0
    for _, slug, section, repo_path in scored[: args.limit]:
        print(f"{slug}\t[{section}]\t{repo_path}")
    print(f"\n# {min(len(scored), args.limit)} of {len(scored)} hits — "
          f"read one with: mdn.py get '<slug>'", file=sys.stderr)
    return 0


def cmd_browse(args):
    rows = load_index()
    folder = slug_to_folder(args.prefix.strip("/"))
    base = "files/en-us/" + folder + "/"
    depth = base.count("/")
    kids = set()
    for repo_path, _section, slug in rows:
        if repo_path.startswith(base) and repo_path != base + "index.md":
            rest = repo_path[len(base):]
            child = rest.split("/", 1)[0]
            kids.add(child)
    if not kids:
        print(f"no children under: {args.prefix}")
        return 0
    for k in sorted(kids):
        print(f"{args.prefix.strip('/')}/{folder_to_slug(k)}")
    return 0


# --------------------------------------------------------------------------- #
# refresh — rebuild index from the GitHub git-tree API
# --------------------------------------------------------------------------- #


def _get_tree(sha: str, recursive: bool):
    """Return (entries, truncated). Caches raw JSON by sha+mode."""
    TREE_CACHE.mkdir(parents=True, exist_ok=True)
    tag = f"{sha}{'_r' if recursive else ''}"
    cached = TREE_CACHE / f"{tag}.json"
    if cached.exists():
        data = json.loads(cached.read_text())
    else:
        url = API_BASE + sha + ("?recursive=1" if recursive else "")
        status, body, _ = _http(url, _gh_headers())
        if status == 403:
            raise RuntimeError(
                "GitHub API 403 (rate limited?). Set GITHUB_TOKEN/GH_TOKEN "
                "and retry; cached subtrees make retries cheap."
            )
        if status != 200:
            raise RuntimeError(f"GitHub API HTTP {status} for tree {sha}")
        data = json.loads(body)
        cached.write_text(json.dumps(data))
    return data.get("tree", []), bool(data.get("truncated"))


def _find(entries, name, etype):
    for e in entries:
        if e.get("path") == name and e.get("type") == etype:
            return e.get("sha")
    return None


def cmd_refresh(args):
    print("fetching git tree (recursive, single call)…", file=sys.stderr)
    entries, truncated = _get_tree(BRANCH, recursive=True)
    note = "single recursive call"

    if truncated:
        note = "truncated — walked per-section subtrees"
        print("  tree truncated; walking subtrees…", file=sys.stderr)
        root, _ = _get_tree(BRANCH, recursive=False)
        files_sha = _find(root, "files", "tree")
        files_t, _ = _get_tree(files_sha, recursive=False)
        enus_sha = _find(files_t, "en-us", "tree")
        enus_t, _ = _get_tree(enus_sha, recursive=False)

        entries = []
        for area in ("web", "glossary"):
            area_sha = _find(enus_t, area, "tree")
            if not area_sha:
                continue
            if area == "glossary":
                sub, _ = _get_tree(area_sha, recursive=True)
                for e in sub:
                    e["path"] = f"files/en-us/glossary/{e['path']}"
                entries += sub
            else:
                web_t, _ = _get_tree(area_sha, recursive=False)
                for sec in web_t:
                    if sec.get("type") != "tree":
                        continue
                    secname = sec["path"]
                    sub, _ = _get_tree(sec["sha"], recursive=True)
                    for e in sub:
                        e["path"] = f"files/en-us/web/{secname}/{e['path']}"
                    entries += sub
                    print(f"    web/{secname}: {len(sub)} entries",
                          file=sys.stderr)

    seen = set()
    out = []
    for e in entries:
        p = e.get("path", "")
        if e.get("type") != "blob" or not p.endswith("/index.md"):
            continue
        if not any(p.startswith(pre) for pre in SCOPE_PREFIXES):
            continue
        if p in seen:
            continue
        seen.add(p)
        out.append((p, section_from_repo_path(p), slug_from_repo_path(p)))

    out.sort(key=lambda r: r[0])
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_FILE.open("w") as f:
        for repo_path, section, slug in out:
            f.write(f"{repo_path}\t{section}\t{slug}\n")

    web_n = sum(1 for r in out if r[0].startswith("files/en-us/web/"))
    glo_n = sum(1 for r in out if r[0].startswith("files/en-us/glossary/"))
    print(f"wrote {len(out)} rows to {INDEX_FILE} "
          f"(web={web_n}, glossary={glo_n}) [{note}]")

    rcount = _refresh_redirects()
    print(f"wrote {rcount} redirects to {REDIRECTS_FILE}")
    return 0


def _refresh_redirects() -> int:
    """Fetch files/en-us/_redirects.txt and write index/redirects.tsv.

    Stored as lower(from_slug)\\t<canonical to_slug>; only doc->doc
    redirects whose key is in scope are kept (keeps the file lean).
    """
    print("fetching _redirects.txt…", file=sys.stderr)
    status, body, _ = _http(RAW_BASE + REDIRECTS_RAW)
    if status != 200:
        raise RuntimeError(f"HTTP {status} fetching _redirects.txt")
    rows = []
    for line in body.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "\t" not in line:
            continue
        src, dst = line.split("\t", 1)
        if "/docs/" not in src.lower() or "/docs/" not in dst.lower():
            continue
        k = _strip_docs_prefix(src).strip("/")
        v = _strip_docs_prefix(dst).strip("/")
        if not k or not v:
            continue
        top = k.split("/", 1)[0].lower()
        if top not in ("web", "glossary"):
            continue
        rows.append((k.lower(), v))
    rows.sort()
    REDIRECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with REDIRECTS_FILE.open("w") as f:
        for k, v in rows:
            f.write(f"{k}\t{v}\n")
    return len(rows)


# --------------------------------------------------------------------------- #
# find — MDN search API (high-quality ranked retrieval, no local index)
# --------------------------------------------------------------------------- #


def _mdn_search(query: str, ttl: int, no_cache: bool) -> dict:
    """Hit developer.mozilla.org/api/v1/search with a small TTL cache."""
    FIND_CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"v1::{query}".encode()).hexdigest()
    cached = FIND_CACHE / f"{key}.json"

    if not no_cache and cached.exists():
        age = time.time() - cached.stat().st_mtime
        if age < ttl:
            try:
                return json.loads(cached.read_text())
            except Exception:
                pass  # fall through and refetch

    import urllib.parse
    qs = urllib.parse.urlencode({"q": query, "locale": "en-US"})
    url = f"{MDN_SEARCH_API}?{qs}"
    status, body, _ = _http(url)
    if status != 200:
        raise RuntimeError(f"HTTP {status} from MDN search API for query {query!r}")
    data = json.loads(body)
    cached.write_text(json.dumps(data))
    return data


def cmd_find(args):
    """MDN-backed semantic search. By default also reads the top hit."""
    data = _mdn_search(args.query, args.ttl or FIND_TTL, args.no_cache)
    docs = data.get("documents", [])
    if not docs:
        print(f"no MDN search hits for: {args.query}")
        sugg = data.get("suggestions") or []
        if sugg:
            print("suggestions:", ", ".join(s.get("text", "") for s in sugg[:5]),
                  file=sys.stderr)
        return 0

    limit = max(1, args.limit)
    candidates = docs[:limit]

    print(f"# Search: {args.query!r}")
    print(f"# {len(candidates)} of {len(docs)} hits from developer.mozilla.org/api/v1/search\n")
    for i, d in enumerate(candidates, 1):
        slug = d.get("slug", "")
        title = d.get("title", "")
        summary = (d.get("summary") or "").strip().replace("\n", " ")
        if len(summary) > 220:
            summary = summary[:217] + "..."
        score = d.get("score", 0)
        pop = d.get("popularity", 0)
        print(f"  {i}. {slug}")
        print(f"     {title}  [score {score:.2f} · popularity {pop:.2f}]")
        if summary:
            print(f"     {summary}")
        print()

    if args.no_read or args.top < 1:
        print(f"# read one with: mdn.py get '<slug>'", file=sys.stderr)
        return 0

    # Auto-read the top N hits.
    n = min(args.top, len(candidates))
    for i in range(n):
        d = candidates[i]
        slug = d.get("slug", "")
        if not slug:
            continue
        sep = "=" * 72
        print(sep)
        print(f"=  Top result #{i + 1}: {slug}")
        print(sep)
        print()
        ga = argparse.Namespace(
            target=slug, raw=False, no_cache=False, json=False, ttl=None,
        )
        try:
            cmd_get(ga)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"(could not fetch {slug}: {e})", file=sys.stderr)
        if i < n - 1:
            print()
    return 0


# --------------------------------------------------------------------------- #
# get
# --------------------------------------------------------------------------- #


def cmd_get(args):
    kind, val = input_to_slug(args.target)
    if kind == "path":
        repo_path = val
        disp_slug = slug_from_repo_path(val)
    else:
        canonical = resolve_slug(val)
        disp_slug = canonical
        repo_path = "files/en-us/" + slug_to_folder(canonical) + "/index.md"
    ttl = args.ttl if args.ttl is not None else DEFAULT_TTL
    text, status_note = fetch_doc(repo_path, ttl, args.no_cache)
    meta, body = split_frontmatter(text)

    slug = meta.get("slug", disp_slug)
    title = meta.get("title", slug.rsplit("/", 1)[-1])
    page_type = meta.get("page-type", "")
    mdn_url = MDN_BASE + slug

    if not args.raw:
        body = clean_markdown(body)

    if args.json:
        print(json.dumps({
            "title": title, "slug": slug, "url": mdn_url,
            "page_type": page_type, "repo_path": repo_path,
            "status": status_note, "markdown": body,
        }, indent=2))
        return 0

    hdr = [f"# {title}", f"MDN:  {mdn_url}"]
    if page_type:
        hdr.append(f"type: {page_type}")
    hdr.append(f"src:  {REPO}@{BRANCH}/{repo_path}  [{status_note}]")
    print("\n".join(hdr))
    print("\n" + "-" * 72 + "\n")
    print(body)
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


KNOWN_VERBS = {"find", "get", "search", "browse", "refresh"}


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="mdn.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd")

    f = sub.add_parser(
        "find",
        help="semantic search via MDN's search API; auto-reads top hit",
    )
    f.add_argument("query", nargs="+",
                   help="search terms (joined with spaces)")
    f.add_argument("--limit", type=int, default=8,
                   help="number of candidates to list (default: 8)")
    f.add_argument("--top", type=int, default=1,
                   help="number of top hits to auto-read (default: 1)")
    f.add_argument("--no-read", action="store_true",
                   help="list candidates only; do not fetch any doc")
    f.add_argument("--no-cache", action="store_true",
                   help="bypass the search-result cache")
    f.add_argument("--ttl", type=int, default=None,
                   help="cache TTL seconds (default: 86400)")
    f.set_defaults(func=cmd_find)

    g = sub.add_parser("get", help="read a doc")
    g.add_argument("target", help="MDN slug, full MDN URL, or repo path")
    g.add_argument("--raw", action="store_true", help="skip macro cleanup")
    g.add_argument("--no-cache", action="store_true", help="force refetch")
    g.add_argument("--json", action="store_true", help="structured JSON output")
    g.add_argument("--ttl", type=int, default=None, help="cache TTL seconds")
    g.set_defaults(func=cmd_get)

    s = sub.add_parser("search",
                       help="local slug-only fuzzy search (offline-capable)")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(func=cmd_search)

    b = sub.add_parser("browse", help="list immediate children of a slug")
    b.add_argument("prefix")
    b.set_defaults(func=cmd_browse)

    r = sub.add_parser("refresh", help="rebuild index/web-docs.tsv")
    r.set_defaults(func=cmd_refresh)

    # Normalize argv: with no args, show help. If the first arg isn't a known
    # verb, treat the whole input as a `find` query — so `mdn.py css grid`
    # is equivalent to `mdn.py find css grid`.
    raw = sys.argv[1:] if argv is None else list(argv)
    if not raw:
        p.print_help(sys.stderr)
        return 0
    if raw[0] not in KNOWN_VERBS and raw[0] not in ("-h", "--help"):
        raw = ["find", *raw]

    args = p.parse_args(raw)
    # Normalize multi-token query to a single string.
    if getattr(args, "cmd", None) == "find":
        args.query = " ".join(args.query) if isinstance(args.query, list) else args.query
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
