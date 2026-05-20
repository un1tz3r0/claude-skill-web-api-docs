---
name: web-api-docs
description: Look up MDN web-platform documentation (HTML, CSS, JavaScript, Web APIs, HTTP, SVG, glossary) straight from the `mdn/content` GitHub repo — no browser, no scraping, no API key. Use when the user needs the canonical MDN reference for a property, method, element, header, status code, pseudo-class/element, or web-platform term; when checking syntax, parameters, return values, or behavior of a JS built-in or DOM API; or when verifying browser-platform semantics before writing front-end / web-API code. Supports an optional `[verb] [query]` argument for one-shot lookups (e.g. `/web-api-docs find css grid layout`).
when_to_use: |
  Trigger phrases / symptoms:
    - "MDN says ..." / "look up X on MDN" / "what does MDN say about X"
    - Questions about JavaScript built-ins: `Array.map`, `Promise.allSettled`, `Object.fromEntries`, ...
    - Questions about Web APIs: `fetch`, `IntersectionObserver`, `WebSocket`, `URL`, ...
    - Questions about CSS properties / selectors / at-rules: `:hover`, `::before`, `@container`, `flex-basis`, ...
    - Questions about HTML elements / attributes / HTTP headers / status codes
    - Verifying browser-platform behavior before writing front-end code
    - "What's the difference between X and Y on the web platform"
  Skip when:
    - The user wants Node/Deno/Bun runtime docs (MDN covers the web platform, not server runtimes)
    - Live browser-compat data is required (`Compat` tables are stripped — link to MDN instead)
    - Live samples / interactive examples are needed (also stripped)
argument-hint: "[find|get|search|browse|refresh] [query...]"
allowed-tools: Bash(bash *) Bash(python3 *mdn.py *) Bash(python3 *mdn.py) Bash(./setup.sh) Bash(test *) Bash(ls *) Bash(cat *)
---

## Overview

This skill turns the `mdn/content` GitHub repo into a stdlib-only CLI
lookup. There is no browser, no scraping, no MDN API key. Subcommands:

| Verb | What it does |
|---|---|
| `find <query>` | **Recommended starting point.** Hits MDN's `/api/v1/search` for ranked candidates, then auto-reads the top hit. Online; great for natural-language topics. |
| `get <slug \| URL \| repo-path>` | Direct fetch of a specific doc by slug, full MDN URL, or repo path. Local redirect map handles moved pages. |
| `search <query>` | Local slug-only fuzzy search against the shipped index. Offline-capable; weaker quality than `find`. |
| `browse <slug-prefix>` | List immediate children of a slug. |
| `refresh` | Rebuild the local index from GitHub. Rarely needed. |

If the first argument isn't a known verb, it's treated as a `find` query
(so `mdn.py css grid` ≡ `mdn.py find css grid`).

## Invoked with arguments

If the user passes `[verb] [query...]` via `/web-api-docs`, the result
of that command runs *now* and lands directly in context below:

```
!`python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py $ARGUMENTS`
```

When `$ARGUMENTS` is empty, the block above prints the CLI's help.
Use the manual workflow in that case.

## Manual workflow (no arguments, or follow-ups)

### Finding the right doc

Prefer `find` when the user's question doesn't already name a slug:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py find "css grid layout"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py find "intersection observer threshold"
```

`find` prints ranked candidates *and* the full top hit. Pass `--no-read`
for candidates only, `--top N` to auto-read N hits.

When the slug is already obvious from the conversation, skip `find`:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "Web/CSS/:hover"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "Glossary/CORS"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "https://developer.mozilla.org/en-US/docs/Web/API/fetch"
```

`get` accepts slugs, full MDN URLs, or repo paths. `--raw` skips macro
cleanup; `--json` emits a structured object with `title`, `slug`,
`url`, `page_type`, `repo_path`, `status`, `markdown`.

### Offline fallback

If MDN's search API is unreachable (rare; sandbox network limits), use
the local slug-only search:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py search "fetch"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py browse "Web/API/Fetch_API"
```

### Reference doc

`${CLAUDE_SKILL_DIR}/reference.md` has the slug→folder encoding,
redirect handling, the full KumaScript macro substitution table, cache
layout, and environment variables. Read it before guessing at flags or
encoding rules.

## Important notes for the model

- **Browser-compat tables, live samples, and interactive-example
  *macros* are replaced** with `> _(... omitted — see MDN.)_`
  placeholders. Standalone fenced code blocks (often labeled
  ``` ```css interactive-example ```) remain in the output as useful
  example code. Don't fabricate compatibility data — link the MDN URL.
- The `src:` line under each `get` header tells you whether the body
  came from cache, a 304 revalidation, or a network fetch — pass that
  along when freshness matters.
- For "what's the canonical URL of this doc" use the `MDN:` line in
  the header, or `--json` and read `.url`.
- 404 from `get` means the slug is wrong or moved without a redirect —
  fall back to `find`.
- `find` results may include out-of-scope areas (e.g. `Learn`) that
  aren't in our shipped index. `get` still works on those slugs as
  long as the file exists in `mdn/content`.
