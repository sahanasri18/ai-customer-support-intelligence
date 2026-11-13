$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
$LogDir = Join-Path $ProjectRoot 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
if (-not (Test-Path $Python)) { throw 'Missing venv Python. Run .\scripts\setup.ps1 first.' }

Push-Location $ProjectRoot
try {
  & $Python -m pytest tests -v 2>&1 | Tee-Object -FilePath (Join-Path $LogDir 'test_results.log')
  if ($LASTEXITCODE -ne 0) { throw "Pytest failed with exit code $LASTEXITCODE. Review logs\test_results.log." }
} finally { Pop-Location }
Write-Host 'Backend tests passed.' -ForegroundColor Green
