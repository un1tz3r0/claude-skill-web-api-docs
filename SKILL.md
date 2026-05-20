---
name: web-api-docs
description: Canonical web-platform reference — HTML, CSS, JavaScript, DOM/Web APIs, HTTP, SVG, MathML, ARIA, WebAssembly, glossary — fetched from github.com/mdn/content. Auto-activates whenever a specific web feature is named — CSS properties/selectors/at-rules (:has, ::before, @container, color-mix, ...); JS built-ins (Array.flatMap, Promise.allSettled, structuredClone, ...); DOM/Web APIs (fetch, IntersectionObserver, ResizeObserver, IndexedDB, WebSocket, Service Worker, ...); HTML elements/attributes (dialog, details, popover, inert, ...); HTTP headers/status (Cache-Control, CSP, CORS, ...); SVG/ARIA/glossary terms — or when editing front-end source (.html/.css/.js/.jsx/.ts/.tsx/.svg/...). Explicit usage — `/web-api-docs [find|get|search|browse|refresh] [query...]`. No browser, no scraping, no API key.
when_to_use: |
  Trigger on any specific web-platform feature name in conversation;
  no "MDN" mention required. When invoked without args, the skill
  prints implicit-trigger guidance — follow it to extract 1-3
  queries from the recent conversation and run `find` per topic
  (in parallel for distinct topics).

  Skip when:
    - The user explicitly wants Node / Deno / Bun runtime docs.
    - The topic is purely framework-specific (React / Vue / Angular /
      Svelte component APIs) and not a wrapped web primitive.
    - Live browser-compat data is required — `Compat` tables are
      stripped; link to MDN instead.
    - Live interactive samples are needed (also stripped).
argument-hint: "[find|get|search|browse|refresh] [query...]"
allowed-tools: Bash(bash *) Bash(python3 *mdn.py *) Bash(python3 *mdn.py) Bash(./setup.sh) Bash(test *) Bash(ls *) Bash(cat *)
---

## Two-stage execution

This is a knowledge-base skill: 12k+ MDN docs are accessible via
on-demand fetch, but only the ones relevant to the current
conversation belong in your context.

How this invocation goes depends on whether arguments were passed:

- **With arguments** — explicit `/web-api-docs <verb> [query]`. The
  block below is the result of that command. Use it directly; no
  further extraction step needed.
- **Without arguments** — implicit auto-activation, or a bare
  `/web-api-docs`. The block below is *guidance*: instructions for
  you to scan the recent conversation, pick a query, and run
  `find` yourself. Follow it.

```
!`python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py $ARGUMENTS`
```

## Subcommand cheatsheet

| Verb | When to use |
|---|---|
| `find <query>` | **Default.** Ranked search via MDN's `/api/v1/search`; auto-reads the top hit. Natural-language topics, when the slug isn't obvious. |
| `get <slug \| URL \| repo-path>` | Direct fetch when you already know the slug or have an MDN URL. Local redirect map handles moved pages. |
| `search <query>` | Local slug-only fuzzy search. Offline-capable; weaker quality than `find`. |
| `browse <slug-prefix>` | List immediate children of a slug. |
| `refresh` | Rebuild the local index from GitHub. Rarely needed. |

If the first argument isn't a known verb, all args route to `find`
(so `mdn.py css grid` ≡ `mdn.py find css grid`).

## Examples (after the initial guidance/result above)

Re-invoke this skill via its slash command — do **not** call the
underlying script directly. On this install the command is
`/web-api-docs` (it matches the directory holding this `SKILL.md`,
so a renamed install would use that name instead).

```
/web-api-docs find intersection observer threshold
/web-api-docs find Array.flatMap
/web-api-docs get Web/CSS/:hover
/web-api-docs get https://developer.mozilla.org/en-US/docs/Web/API/fetch
/web-api-docs browse Web/API/Fetch_API
```

Issue multiple `find` invocations in parallel when the conversation
touches multiple distinct topics — each is independent and cached
separately.

## Important notes

- **Browser-compat tables, live samples, and interactive-example
  *macros* are replaced** with `> _(... omitted — see MDN.)_`
  placeholders. Standalone fenced code blocks (often labeled
  ``` ```css interactive-example ```) remain in the output as useful
  example code. Don't fabricate compatibility data — link the MDN URL.
- The `src:` line under each `get` header tells you whether the body
  came from cache, a 304 revalidation, or a network fetch — surface
  that when freshness matters.
- For "what's the canonical URL of this doc" use the `MDN:` line in
  the header, or `--json` and read `.url`.
- 404 from `get` means the slug is wrong or moved without a redirect
  — fall back to `find`.
- `find` can return out-of-scope slugs (e.g. `Learn/...`) that aren't
  in our shipped index. `get` still works on those.
- For slug-encoding rules, macro substitution table, cache layout,
  and environment variables, see `${CLAUDE_SKILL_DIR}/reference.md`.
