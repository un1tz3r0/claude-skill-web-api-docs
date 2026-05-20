---
name: web-api-docs
description: Canonical web-platform reference — HTML, CSS, JavaScript, DOM and Web APIs, HTTP, SVG, MathML, ARIA, WebAssembly, and the web glossary — fetched on demand from `mdn/content`. Auto-activates whenever the user or assistant names a specific web technology (a CSS property/selector/at-rule, a JS built-in or method, a DOM/Web API, an HTML element/attribute, an HTTP header/status, an SVG element, an ARIA role, a web glossary term) or works with front-end source (HTML, CSS, JS, JSX, TS, TSX, SVG, etc.). Also takes an explicit `[verb] [query]` argument for one-shot lookups (e.g. `/web-api-docs find css grid layout`). No browser, no scraping, no API key.
when_to_use: |
  Trigger on any of these — explicit "MDN" mention is **not** required:
    - Specific CSS terms: properties (display, grid-template-areas,
      content-visibility, color-scheme, …); selectors (:hover, :has,
      :is, :where, ::before, ::backdrop, ::part, …); at-rules
      (@container, @layer, @media, @supports, @keyframes); functions
      (calc, clamp, min/max, var, color-mix, oklch, light-dark, …);
      units / color spaces / custom properties / cascade layers.
    - Specific JS built-ins / syntax: Array/Promise/Map/Set/Object/
      String/RegExp methods (Array.flatMap, Promise.allSettled,
      Object.fromEntries, structuredClone, …); operators (??, ?.,
      ?.()), control flow, async/await, generators, modules, regex
      features.
    - DOM / Web APIs: fetch, AbortController, IntersectionObserver,
      ResizeObserver, MutationObserver, WebSocket, EventSource,
      IndexedDB, Cache, Service Workers, Web Workers, Canvas / WebGL,
      Web Audio, WebRTC, File System Access, Streams, …
    - HTML: elements (dialog, details, picture, slot, …), global
      attributes (popover, inert, contenteditable, …), forms,
      microdata, the HTML parsing algorithm.
    - HTTP: headers (Cache-Control, Content-Security-Policy, CORS-*,
      Vary, Set-Cookie, …), methods, status codes, redirects,
      caching, conditional requests, content negotiation.
    - SVG / MathML elements and attributes.
    - Accessibility: ARIA roles / states / properties; semantic HTML;
      WCAG concepts; WAI-ARIA authoring practices.
    - Web glossary terms: CORS, CSP, REST, ES Modules, hoisting,
      semantic markup, hydration, polyfill, transpiler, …
    - The user is editing or asking about front-end source files:
      `.html`, `.htm`, `.css`, `.scss`, `.sass`, `.less`, `.js`,
      `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.svg`, `.xml`.
    - Questions of the shape: "how does X work in the browser?",
      "what's the cross-browser way to …?", "is X standard?",
      "what's the difference between X and Y on the web platform?"

  Skip when:
    - The user explicitly wants Node / Deno / Bun runtime docs.
    - The topic is purely framework-specific (React / Vue / Angular /
      Svelte component APIs) and not a wrapped web primitive.
    - Live browser-compat data is required — `Compat` tables are
      stripped; link to MDN instead.
    - Live samples / interactive examples are needed (also stripped).
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

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py find "intersection observer threshold"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py find "Array.flatMap"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "Web/CSS/:hover"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py get "https://developer.mozilla.org/en-US/docs/Web/API/fetch"
python3 ${CLAUDE_SKILL_DIR}/scripts/mdn.py browse "Web/API/Fetch_API"
```

Run multiple `find` calls in parallel when the conversation touches
multiple distinct topics — each `find` is independent and cached
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
