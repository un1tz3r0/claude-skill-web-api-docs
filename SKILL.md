---
name: web-api-docs
description: Look up MDN web-platform documentation (HTML, CSS, JavaScript, Web APIs, HTTP, SVG, glossary) straight from the `mdn/content` GitHub repo — no browser, no scraping, no API key. Use when the user needs the canonical MDN reference for a property, method, element, header, status code, pseudo-class/element, or web-platform term; when checking syntax, parameters, return values, or behavior of a JS built-in or DOM API; or when verifying browser-platform semantics before writing front-end / web-API code. Ships a slug→path index and a redirect map so most lookups need a single HTTP fetch.
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
allowed-tools: Bash(bash *) Bash(python3 *mdn.py *) Bash(./setup.sh) Bash(test *) Bash(ls *) Bash(cat *)
---

## Overview

This skill turns the `mdn/content` GitHub repo into a stdlib-only CLI
lookup. There is no browser, no scraping, no MDN API key. A shipped
index (`index/web-docs.tsv`) maps every in-scope slug to its repo path
without a network call; a shipped redirect map (`index/redirects.tsv`)
follows moved pages. Fetched docs are cached on disk with conditional
GET, so repeated lookups stay cheap.

Scope: `files/en-us/web/**` and `files/en-us/glossary/**`. That covers
HTML, CSS, JavaScript, Web APIs, HTTP, SVG, MathML, WebAssembly,
Accessibility, Web Extensions, and the Glossary. It does **not** cover
Learn, Plus, Mozilla-internal, or non-`en-US` content.

## Step 1 — Bootstrap (idempotent)

```bash
bash ${CLAUDE_SKILL_DIR}/setup.sh
```

Verifies `python3` is on PATH and checks that the shipped index is
present. Does not install anything.

## Step 2 — Read the reference before writing scripts

**Read `${CLAUDE_SKILL_DIR}/reference.md` first.** It documents the
slug→folder encoding, redirect handling, macro cleanup table, cache
layout, and environment variables. Don't reimplement encoding or guess
at flags — they're verified there.

## Step 3 — Look up a doc

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "Web/CSS/:hover"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "Web/JavaScript/Reference/Global_Objects/Array/map"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "Glossary/CORS"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "https://developer.mozilla.org/en-US/docs/Web/API/fetch"
```

Inputs accepted: MDN slug, full MDN URL, or repo path
(`files/en-us/.../index.md`). Pass `--json` for a structured object
(`title`, `slug`, `url`, `page_type`, `repo_path`, `status`,
`markdown`). Pass `--raw` to skip KumaScript macro cleanup.

## Step 4 — Find a slug

When you don't know the exact slug:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py search "intersectionobserver"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py browse "Web/API/Fetch_API"
```

`search` is slug-only — queries that name a concept not in the slug
(e.g. "flexbox" for `css_flexible_box_layout`) will miss. Fall back to
`browse` from a known parent slug, or guess the slug from
developer.mozilla.org and pass it directly to `get`.

## Step 5 — Refresh the index (rarely)

The shipped TSVs are good for normal use. Regenerate after changes to
the encoder, scope, or after a long gap (months):

```bash
export GH_TOKEN="$(gh auth token)"   # avoid 60 req/hr unauth limit
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py refresh
```

## Important notes for the model

- **Browser-compat tables, live samples, and interactive-example
  *macros* are replaced** with `> _(... omitted — see MDN.)_`
  placeholders. Standalone fenced code blocks (often labeled
  ``` ```css interactive-example ```) remain in the output as useful
  example code. Don't fabricate compatibility data — link the MDN URL.
- The `Status:` field at the top of `get` output tells you whether the
  body came from cache, a 304 revalidation, or a network fetch — pass
  that along when freshness matters.
- For "what's the canonical URL of this doc" use the `MDN:` line in the
  header, or `--json` and read `.url`.
- 404 from `get` means the slug is wrong or moved without a redirect —
  fall back to `search`.
