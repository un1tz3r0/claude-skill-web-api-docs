#!/usr/bin/env bash
# Verification-only setup for the web-api-docs skill. Does NOT install
# anything; just confirms python3 is on PATH and that the shipped index
# exists. Optionally exports GH_TOKEN from `gh auth token` so `refresh`
# avoids the 60 req/hr unauth rate limit.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found on PATH." >&2
    echo "Install Python 3.8+ and rerun this script." >&2
    exit 1
fi
echo "python3 $(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))') found at $(command -v python3)" >&2

if [ ! -f "${SKILL_DIR}/index/web-docs.tsv" ]; then
    echo "WARNING: index/web-docs.tsv missing." >&2
    echo "  Run: python3 ${SKILL_DIR}/scripts/mdn.py refresh" >&2
    echo "  (set GITHUB_TOKEN or GH_TOKEN first to avoid rate limits)" >&2
fi

if [ -z "${GITHUB_TOKEN:-}" ] && [ -z "${GH_TOKEN:-}" ]; then
    if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
        echo "tip: export GH_TOKEN=\"\$(gh auth token)\" before running 'refresh'" >&2
    fi
fi

echo "web-api-docs setup ok" >&2
