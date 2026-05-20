<p align="center">
  <img src="splash.svg" alt="web-api-docs — a Claude Code skill that automatically enriches contexts with relevant pages from MDN's library of web frontend development docs." width="100%">
</p>

# web-api-docs

> A [Claude Code](https://claude.com/claude-code) skill that
> **automatically enriches contexts with relevant pages from MDN's
> library of web frontend development docs**.

## What this looks like in practice

You're editing a stylesheet and ask "why isn't my `:has()` selector
matching here?" — or you paste a snippet using `IntersectionObserver`
and ask Claude to fix the threshold logic — or you wonder out loud why
your `fetch` isn't sending cookies. In each case, the skill spots the
web-platform feature in play, pulls the canonical MDN page into the
conversation, and Claude answers from the spec instead of from
memory.

You don't have to remember the skill exists. It activates whenever a
specific web feature is named (CSS properties / selectors / at-rules,
JS built-ins, DOM / Web APIs, HTML elements / attributes, HTTP
headers and statuses, SVG, ARIA, glossary terms) or whenever Claude
is touching front-end source (`.html`, `.css`, `.js`, `.jsx`, `.ts`,
`.tsx`, `.svg`, …).

## Asking for a specific page

When you do want a particular page on hand, invoke the skill
explicitly:

```text
> /web-api-docs get Web/CSS/:hover
> /web-api-docs find IntersectionObserver
> /web-api-docs search "cache control"
> /web-api-docs browse Web/API/Fetch_API
```

The verbs:

| Verb       | What it does |
| ---------- | ------------ |
| `find`     | Search MDN, return the top results' summaries. The quickest "what's at this name?" probe. |
| `get`      | Render a specific page. Accepts a slug (`Web/CSS/:hover`), a full MDN URL, or a repo path. |
| `search`   | List matching slugs from the shipped index without fetching content. |
| `browse`   | Show the immediate children of a slug — useful for walking the MDN tree. |
| `refresh`  | Rebuild the local slug index from MDN's GitHub repo. |

Every rendered page leads with the canonical MDN URL, so a click
takes you to the live page for interactive examples and
browser-compat tables.

## Install

### Into your local Claude Code

Clone the repo and run the installer. By default it **copies** the
skill into `~/.claude/skills/web-api-docs/`.

```bash
git clone https://github.com/un1tz3r0/claude-skill-web-api-docs.git web-api-docs
cd web-api-docs
./install.sh                  # copy into ~/.claude/skills/
./install.sh --symlink        # symlink instead (edits track the checkout)
```

Other destinations are mutually exclusive:

```bash
./install.sh --project /path/to/proj    # → proj/.claude/skills/web-api-docs
./install.sh --home    /path/to/home    # → home/.claude/skills/web-api-docs
./install.sh --user    alice            # look up alice's home automatically
```

Useful flags: `--force` to overwrite an existing install, `--dry-run`
to preview, `--uninstall` to remove, `--name OTHER` to install under a
different folder name.

Windows-native users: run `install.ps1` instead. Symlink mode needs
Developer Mode or an elevated shell; copy mode works as-is.

### Into Claude Code on the web

Grab the latest `web-api-docs.zip` from the
[Releases page](https://github.com/un1tz3r0/claude-skill-web-api-docs/releases)
and upload it via the web UI's skill upload.

Or build one yourself:

```bash
./package-skill.sh                       # writes ./web-api-docs.zip
./package-skill.sh -o /tmp/out.zip       # custom output path
./package-skill.sh --dry-run             # list what would be packed
```

## Scope and limits

The skill covers everything under `web/` and `glossary/` on MDN —
HTML, CSS, JavaScript, Web APIs, HTTP, SVG, MathML, WebAssembly,
Accessibility, Web Extensions, and the Glossary.

A few things it deliberately doesn't do:

- **No live browser-compat tables or interactive examples.** Those
  parts of the page are replaced with placeholders; follow the MDN
  URL at the top of every response for the live versions.
- **No full-text search.** The shipped index is slug-only, so
  concepts not named in the slug (e.g. "flexbox" →
  `css_flexible_box_layout`) may need a `/web-api-docs browse`
  from a known parent.
- **No server-runtime docs.** This is the web platform only — for
  Node / Deno / Bun, use those projects' own references.

## Requirements

- Python 3.8+. Stdlib only — no `pip install` step.
- For `refresh`: network access and a GitHub token
  (`GITHUB_TOKEN` / `GH_TOKEN`); `gh auth token` works.
- For symlink installs on Windows: Developer Mode or an admin shell.

## License & attribution

This skill is tooling. The MDN content it fetches at runtime is
© Mozilla Contributors and licensed under
[CC BY-SA 2.5](https://developer.mozilla.org/en-US/docs/MDN/About#copyrights_and_licenses).

For implementation details — slug → folder encoding rules, the macro
substitution table, cache layout, environment variables — see
[`reference.md`](reference.md).
