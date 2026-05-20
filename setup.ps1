# setup.ps1 — verification-only setup for the web-api-docs skill.
# Confirms python3 (or python) is available and the shipped index is
# present. Does not install anything.

$ErrorActionPreference = "Stop"
$SkillDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

$Python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $Python) {
    Write-Error "python3 (or python) not found on PATH. Install Python 3.8+ and rerun."
    exit 1
}
$Version = & $Python.Source -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
Write-Host "python $Version found at $($Python.Source)" -ForegroundColor Green

$Index = Join-Path $SkillDir "index\web-docs.tsv"
if (-not (Test-Path $Index)) {
    Write-Warning "index/web-docs.tsv missing."
    Write-Host "  Run: $($Python.Source) `"$(Join-Path $SkillDir 'scripts\mdn.py')`" refresh"
    Write-Host "  (set GITHUB_TOKEN or GH_TOKEN first to avoid rate limits)"
}

if (-not $env:GITHUB_TOKEN -and -not $env:GH_TOKEN) {
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        Write-Host "tip: set `$env:GH_TOKEN = (gh auth token) before running 'refresh'"
    }
}

Write-Host "web-api-docs setup ok"
