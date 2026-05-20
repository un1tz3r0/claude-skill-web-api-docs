# Changelog

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
