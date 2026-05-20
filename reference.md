# web-api-docs — reference

`scripts/mdn.py` fetches MDN docs straight from `github.com/mdn/content`
(raw Markdown on the `main` branch), with a shipped slug→path index, a
shipped redirect map, and on-disk caching. Stdlib only.

## Subcommands

| Command | Purpose |
|---|---|
| `find <query>` | Semantic search via `developer.mozilla.org/api/v1/search`; auto-reads the top hit. |
| `get <slug \| URL \| repo-path>` | Read one doc (light KumaScript cleanup). |
| `search <query>` | Fuzzy-find a doc in the shipped local index (slug-only; offline-capable). |
| `browse <slug-prefix>` | List immediate children of a slug. |
| `refresh` | Rebuild `index/web-docs.tsv` and `index/redirects.tsv` from GitHub. |

If the first argument is not one of the verbs above, all arguments are
joined and treated as a `find` query
(`mdn.py css grid` ≡ `mdn.py find css grid`).

### `find`
```
mdn.py find <query...> [--limit N] [--top N] [--no-read]
                       [--no-cache] [--ttl SECONDS]
```
Calls MDN's own search API and prints ranked candidates as
`slug · title · summary` lines. By default also fetches the top hit
via `get` and prints its full Markdown — one shell call, no further
turns. `--no-read` skips the auto-fetch; `--top N` reads the top N
instead of just the first. Responses are cached at
`.cache/find/<sha256(query)>.json` with TTL `MDN_FIND_TTL` (default 1
day).

`find` may return slugs outside the shipped index scope (e.g. `Learn`
docs). `get` still works on those — the index only constrains local
`search` / `browse`, not `get`.

### `get`
```
mdn.py get <target> [--raw] [--no-cache] [--json] [--ttl SECONDS]
```
`<target>` can be:
- a slug: `Web/CSS/:hover`, `Glossary/CORS`
- a full MDN URL: `https://developer.mozilla.org/en-US/docs/Web/API/fetch`
- a repo path: `files/en-us/web/api/fetch/index.md`

Redirects from `index/redirects.tsv` are followed for slug/URL inputs (up
to 5 hops, cycle-safe). `--raw` skips macro cleanup. `--json` emits a
structured object: `title`, `slug`, `url`, `page_type`, `repo_path`,
`status`, `markdown`.

### `search`
Scores entries by token presence in the slug. Last path segment hits
score higher; an exact-segment match wins outright. The index is
slug-only, so queries that name a concept not in the slug (e.g.
"flexbox" for `web/css/css_flexible_box_layout`) will miss — fall back
to `browse` or a known MDN URL.

### `browse`
Lists direct children of a slug prefix. Slug encoding is applied to the
prefix before the lookup.

### `refresh`
Calls the GitHub git-tree API once (recursive). On truncation, walks
per-section subtrees. Then fetches `files/en-us/_redirects.txt` and
writes the in-scope subset to `index/redirects.tsv`.

## Slug → folder encoding

Mirrors `mdn/yari` `libs/slug-utils/index.js` `slugToFolder`. **Order
matters** — `::` must be replaced before `:`.

| Char | Replacement |
|---|---|
| `*` | `_star_` |
| `::` | `_doublecolon_` |
| `:` (remaining) | `_colon_` |
| `?` | `_question_` |

Then the slug is lowercased and each `/`-segment is run through the npm
`sanitize-filename` rules:

- strip `/?<>\:*|"` (already replaced above for the special four)
- strip control chars `\x00-\x1f` and `\x80-\x9f`
- replace pure-dots segments (`.`, `..`) with empty
- strip Windows reserved names (`con`, `prn`, `aux`, `nul`, `com[0-9]`, `lpt[0-9]`, with any extension)
- strip trailing `.` and spaces
- truncate each segment to 255 bytes (UTF-8)

Examples:
- `Web/CSS/:hover` → `web/css/_colon_hover`
- `Web/CSS/::before` → `web/css/_doublecolon_before`
- `Web/JavaScript/Reference/Global_Objects/Array/map` → `web/javascript/reference/global_objects/array/map`
- `Glossary/CORS` → `glossary/cors`

The final repo path is `files/en-us/<folder>/index.md`.

## Redirects

`index/redirects.tsv` is `lower(from_slug)\t<to_slug>`. Only
doc→doc redirects whose source is under `web/` or `glossary/` are
kept (keeps the file lean). `resolve_slug()` follows up to 5 hops and
breaks on cycles or self-references.

When a `get` 404s, the slug is either wrong or moved without a redirect
entry — fall back to `mdn.py search '<terms>'`.

## KumaScript cleanup

The raw Markdown contains `{{Macro(args)}}` tokens. `--raw` keeps them;
default rendering substitutes:

| Macro family | Substitution |
|---|---|
| `Deprecated_inline`, `Experimental_inline`, `Non-standard_inline`, `Optional_inline`, `ReadOnlyInline`, `SecureContext_Inline` | inline italic badge, e.g. `*(deprecated)*` |
| `Deprecated_Header`, `Non-standard_Header`, `SeeCompatTable`, `SecureContext_Header`, `AvailableInWorkers` | one-line blockquote banner |
| `Compat`, `Specifications`, `EmbedLiveSample`, `EmbedGHLiveSample`, `LiveSampleLink`, `EmbedInteractiveExample`, `InteractiveExample`, `EmbedYouTube` | `> _(... omitted — see MDN.)_` placeholder |
| `jsxref`, `domxref`, `cssxref`, `HTMLElement`, `SVGElement`, `SVGAttr`, `HTTPHeader`, `HTTPStatus`, `HTTPMethod`, `Glossary`, `RFC`, `WebExtAPIRef`, `ARIARole`, `ariaattr` | `` `label` `` (most-human arg as inline code) |
| `note`, `warning`, `callout` | `> **Note:** ...` / `> **Warning:** ...` |
| `*Sidebar`, `JSRef`, `CSSRef`, `APIRef`, `HTMLRef`, `PreviousNext`, `Previous`, `Next`, `ListSubpages`, `Page`, etc. | dropped |
| anything else | last/first non-empty arg as inline code, else dropped |

This is lossy on purpose — sidebar/navigation macros are dropped and
compat/sample macros become single-line placeholders. Note that only
the *macros* are touched; a standalone fenced code block following an
`InteractiveExample` macro (e.g. ``` ```css interactive-example ```)
is left intact as readable example code. Use `--raw` if you need the
original tokens.

## Cache

`.cache/content/<sha256(repo_path)>.{md,meta}` — one file pair per doc.
`meta` stores `etag`, `last_modified`, and `fetched_at`. Inside the TTL
window the cache is returned without a network call; outside, a
conditional GET (`If-None-Match` / `If-Modified-Since`) revalidates and
refreshes only on actual change.

`.cache/trees/<sha>[_r].json` caches GitHub git-tree responses by SHA
so retries after a rate-limit are cheap.

## Environment variables

| Var | Effect |
|---|---|
| `GITHUB_TOKEN` or `GH_TOKEN` | Bearer auth for the GitHub API. Required for `refresh` unless you're under the 60 req/hr unauth limit. `gh auth token` prints a working token if `gh` is logged in. |
| `MDN_CACHE_TTL` | Per-doc cache TTL in seconds (default `604800` = 7 days). |

## Build step

`index/web-docs.tsv` and `index/redirects.tsv` are committed to the
repo. Regenerate before shipping changes that affect the encoder or
scope:

```bash
export GH_TOKEN="$(gh auth token)"   # or set GITHUB_TOKEN
python3 scripts/mdn.py refresh
```
