# install.ps1 — thin PowerShell wrapper around scripts/install.py.
# All flags are forwarded; see `.\install.ps1 --help` for full usage.

$ErrorActionPreference = "Stop"

$SkillDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $Python) {
    Write-Error "python3 (or python) not found on PATH. Install Python 3.8+ and rerun."
    exit 1
}

& $Python.Source (Join-Path $SkillDir "scripts/install.py") @args
exit $LASTEXITCODE
