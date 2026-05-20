# Changelog

## 2026-05-20

### Changed
- **Broadened trigger conditions.** Dropped the implicit "MDN must be
  mentioned" requirement. SKILL.md now triggers on any specific web-
  platform technology mention (CSS properties / selectors / at-rules /
  functions; JS built-ins; DOM/Web APIs; HTML elements/attributes;
  HTTP headers/status codes; SVG; ARIA; glossary terms) and when the
  user is working with front-end source files
  (`.html`, `.css`, `.js`, `.jsx`, `.ts`, `.tsx`, `.svg`, etc.).
  `description` and `when_to_use` expanded with concrete examples
  per category.

### Added
- **Two-stage execution for implicit triggers.** Bare `mdn.py` (no
  args) now prints implicit-trigger guidance instead of the argparse
  help: it tells Claude to extract 1-3 queries from the recent
  conversation, run `find` per query (in parallel), and use the
  returned Markdown. Includes 20 curated example queries
  demonstrating good query shapes and a per-section topic table built
  live from the shipped TSV (`web/api: 7989 docs · DOM, fetch, …` etc).
- SKILL.md restructured around a "Two-stage execution" section so the
  model knows whether the `!`-injected block is a result (explicit
  args) or a guidance block (implicit). The heavy guidance is only in
  context when no args were passed — explicit slash commands stay
  lean.

## 2026-05-19 (last)

### Added
- `mdn.py find <query>` — semantic search backed by MDN's own search
  API (`developer.mozilla.org/api/v1/search`). Returns ranked
  candidates with `slug · title · summary` lines and by default
  auto-reads the top hit via `get`, so one shell call yields both the
  candidate list and the full top doc. Flags: `--no-read`, `--top N`,
  `--limit`, `--no-cache`, `--ttl`. Responses cached at
  `.cache/find/<sha256(query)>.json` (TTL `MDN_FIND_TTL`, default 1d).
- Bare-invocation handling: `mdn.py` with no args prints help; if the
  first arg is not a known verb (`find`/`get`/`search`/`browse`/
  `refresh`), all args are routed to `find`.
- SKILL.md frontmatter: `argument-hint: "[find|get|search|browse|
  refresh] [query...]"` and a `!`-injection block that runs
  `mdn.py $ARGUMENTS` so a `/web-api-docs find ...` invocation lands
  the result directly in the model's context. Body restructured around
  the verb table.

### Rationale
- Embeddings / local BM25 over per-doc summaries were considered and
  rejected: torch/onnx are too heavy for the Claude-Code-web sandbox
  and arbitrary user dirs; building summaries upfront would need ~12k
  authed GitHub fetches. MDN already ships a high-quality search API,
  so retrieval is outsourced and content fetch stays local.

## 2026-05-19 (later still)

### Added
- `README.md` for GitHub — what / how / install (local + web) / usage /
  requirements / scope caveats / license & attribution.
- `splash.svg` — banner-aspect hybrid splash: `</>` mark + wordmark on
  the left, terminal mockup of a real `mdn.py get :hover` invocation
  on the right. Pure SVG; scales to any width.

## 2026-05-19 (later)

### Added
- `scripts/install.py` — cross-platform installer (copy by default,
  `--symlink` for symlink). Destination resolution: `--project DIR` >
  `--home DIR` > `--user USER` > current `$HOME`. Supports `--force`,
  `--dry-run`, `--uninstall`, `--name`, post-install verification, and
  prints a Windows-specific hint when `os.symlink()` fails.
- `scripts/package_skill.py` — builds `<name>.zip` for upload to Claude
  Code on the web. Archive has the skill folder at its root; excludes
  `.cache/`, `__pycache__/`, `.git/`, `.claude/`. Pure stdlib (works on
  Windows without 7-zip/WinZip).
- `install.sh` / `install.ps1` and `package-skill.sh` /
  `package-skill.ps1` — thin wrappers that locate `python3` and forward
  all flags. The Python scripts can also be invoked directly.
- `setup.ps1` — PowerShell counterpart to `setup.sh` so Windows-native
  users without Git Bash can still bootstrap.

### Security
- Reject `--name` values containing path separators or `.`/`..` so an
  install can never escape the resolved `skills/` directory (matters
  when combined with `--home` or root-run `--user`).

### Changed
- Install/package both drop the source repo's `.claude/` directory.
  It holds dev-time settings (e.g. `settings.local.json`) and has no
  runtime role inside an installed skill.

### Verified
- Project-local install (copy + symlink) and uninstall.
- Round-trip: install to a temp project, run `mdn.py search` from the
  installed copy, uninstall cleanly.
- `package-skill.sh` archive: SKILL.md present, `.cache/`, `.claude/`,
  `__pycache__/` excluded; `web-api-docs/` is the archive root.

## 2026-05-19

### Added
- `SKILL.md` with frontmatter, trigger phrases, and step-by-step usage.
- `reference.md` documenting slug→folder encoding, redirect handling,
  KumaScript macro substitution table, cache layout, and environment
  variables.
- `DESIGN.md` capturing scope, constraints, and key decisions.
- `setup.sh` — verifies `python3` is on PATH and the shipped index is
  present; suggests `gh auth token` for the `refresh` rate-limit.
- `.gitignore` (ignores `.cache/`, `__pycache__/`).
- Regenerated `index/web-docs.tsv` and added `index/redirects.tsv`
  (9004 entries) so `:hover` and other moved pages resolve through the
  shipped redirect map.

### Installed
- Symlinked `~/.claude/skills/web-api-docs` →
  `/home/owner/Projects/skills/web-api-docs` so the skill is
  discoverable to Claude Code.

### Verified
- `get` works for slug, full MDN URL, and repo-path inputs.
- Pseudo-class / pseudo-element encoding (`:hover`, `::before`).
- Redirect following (`Web/CSS/:hover` → `Web/CSS/Reference/Selectors/:hover`).
- `search` and `browse` against the shipped index.
- Glossary lookups (`Glossary/CORS`).

## 2026-05-17

### Added
- Initial `scripts/mdn.py` with `get` / `search` / `browse` / `refresh`
  subcommands, on-disk caching with conditional GET, and the yari
  `slugToFolder` + `sanitize-filename` encoder.
- Initial `index/web-docs.tsv` (12680 rows: 12056 web + 624 glossary).
