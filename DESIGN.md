# DESIGN — web-api-docs skill

## Goal

Give the model a fast, offline-first way to read MDN web-platform docs
(HTML, CSS, JS, Web APIs, HTTP, SVG, Glossary) from inside a Claude
Code session, without a browser, without scraping rendered HTML, and
without an MDN API key.

## Approach

Read the raw Markdown straight from `github.com/mdn/content` on `main`.
MDN's renderer (`yari`) turns those files into developer.mozilla.org;
the source is plain Markdown plus KumaScript `{{Macro(args)}}` tokens.

A shipped slug→path index removes any guessing about where a doc lives.
A shipped redirect map handles moved pages. Per-doc on-disk caching
with conditional GET keeps repeat lookups effectively free.

## Constraints

- **Stdlib only.** No `requests`, no `pyyaml`, no third-party deps.
  The skill must work on a vanilla Python 3.8+ install.
- **No state in shell sessions.** Each invocation is self-contained;
  configuration is environment variables only.
- **Encoder fidelity.** Slug→folder must match `mdn/yari`
  `libs/slug-utils` `slugToFolder` byte-for-byte, including the
  `sanitize-filename` rules applied per path segment. Any drift means
  silent 404s.
- **Scope is bounded.** Only `files/en-us/web/**` and
  `files/en-us/glossary/**`. Learn, Plus, and non-`en-US` are out of
  scope; the index would balloon and the lookup ergonomics suffer.
- **Lossy is fine.** Browser-compat tables, live samples, and
  interactive-example macros are replaced with one-line placeholders.
  Fenced code blocks remain in the body. The user gets the canonical
  MDN URL in the header and can follow it for the rendered/interactive
  bits.

## Architecture

```
web-api-docs/
├── SKILL.md            # frontmatter + usage; what the model reads first
├── reference.md        # encoder rules, macro table, cache, env vars
├── DESIGN.md           # this file
├── CHANGELOG.md
├── setup.sh            # verify python3, no installs
├── .gitignore          # ignore .cache/
├── scripts/
│   └── mdn.py          # the whole CLI (get / search / browse / refresh)
├── index/
│   ├── web-docs.tsv    # repo_path \t section \t slug   (shipped)
│   └── redirects.tsv   # lower(from_slug) \t to_slug    (shipped)
└── .cache/             # gitignored
    ├── content/        # <sha256(repo_path)>.{md,meta}
    └── trees/          # <sha>[_r].json  (GitHub git-tree responses)
```

## Key decisions

1. **Slug-only fuzzy search.** A full-text index over the markdown
   bodies would be 10×+ bigger and require either a build step or a
   runtime indexer. The slug is usually enough; when it isn't, fall
   back to `browse` from a known parent.

2. **Single recursive git-tree call with subtree fallback.** GitHub
   truncates very large recursive tree responses; the script detects
   truncation and walks `files/en-us/{web/<section>, glossary}`
   subtrees instead. Trees are cached by SHA so retries after a
   rate-limit are cheap.

3. **Shipped redirects, not runtime resolution.** A miss on `get`
   could trigger an MDN HEAD redirect lookup, but that would require
   network on the bad-slug path. Shipping a `redirects.tsv` (~9k
   entries, scope-filtered) means a slug→path lookup with redirects
   stays purely local.

4. **Macro cleanup table is curated, not exhaustive.** The unknown-macro
   fail-safe surfaces the last/first arg as inline code, which covers
   the long tail without polluting the rendered doc with raw tokens.

5. **No `--all` / no recursive tree dumps.** `browse` lists one level.
   For more, follow links from the rendered output.

## Out of scope (deliberate)

- Server-runtime docs (Node, Deno, Bun) — different sources.
- Live browser-compat data (BCD) — would require a separate index
  and renderer.
- Localized content (non-`en-US`) — scope creep, search ambiguity.
- Search that ranks by content body — wrong tool; use a real index
  if that's the need.
