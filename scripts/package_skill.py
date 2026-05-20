#!/usr/bin/env python3
"""package_skill.py — produce a zip archive of this skill for upload.

The archive contains the skill directory at its root
(e.g. ``web-api-docs/SKILL.md``), with cache/build/git noise excluded.
Suitable for uploading to Claude Code on the web.

Run via ``package-skill.sh`` / ``package-skill.ps1`` or directly:

    python3 scripts/package_skill.py [-o OUTPUT.zip] [--include-cache]
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_NAME = SKILL_DIR.name

# Directory and file names to skip (matched against any path component).
# .claude/ holds dev-time settings for the source repo and is not part of the
# distributable skill. .cache/ is gated by --include-cache.
SKIP_DIR_NAMES_ALWAYS = {"__pycache__", ".git", ".claude"}
SKIP_DIR_NAMES_CACHE = {".cache"}
SKIP_FILE_NAMES = {".DS_Store"}
SKIP_FILE_SUFFIXES = {".pyc"}


def should_skip(rel: Path, include_cache: bool) -> bool:
    parts = set(rel.parts)
    if parts & SKIP_DIR_NAMES_ALWAYS:
        return True
    if not include_cache and parts & SKIP_DIR_NAMES_CACHE:
        return True
    if rel.name in SKIP_FILE_NAMES:
        return True
    if rel.suffix in SKIP_FILE_SUFFIXES:
        return True
    return False


def collect_files(include_cache: bool) -> list[Path]:
    files = []
    for path in SKILL_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(SKILL_DIR)
        if should_skip(rel, include_cache):
            continue
        files.append(path)
    return sorted(files)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="package_skill.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-o", "--output", default=None,
                   help=f"output zip path (default: ./{SKILL_NAME}.zip)")
    p.add_argument("--include-cache", action="store_true",
                   help="include .cache/ in the archive (default: excluded)")
    p.add_argument("--name", default=SKILL_NAME,
                   help=f"override the archive root directory name (default: {SKILL_NAME})")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="list files that would be archived, then exit")
    args = p.parse_args(argv)

    out = Path(args.output).resolve() if args.output else Path.cwd() / f"{args.name}.zip"
    files = collect_files(args.include_cache)
    if not files:
        print("error: no files matched", file=sys.stderr)
        return 1

    if args.dry_run:
        for f in files:
            print(f.relative_to(SKILL_DIR))
        print(f"\n{len(files)} files would be archived into {out}", file=sys.stderr)
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            rel = f.relative_to(SKILL_DIR)
            arcname = Path(args.name) / rel
            zf.write(f, arcname.as_posix())
            total_bytes += f.stat().st_size

    size_kb = out.stat().st_size / 1024
    print(f"wrote {out} ({len(files)} files, {size_kb:.1f} KB compressed, "
          f"{total_bytes / 1024:.1f} KB uncompressed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
