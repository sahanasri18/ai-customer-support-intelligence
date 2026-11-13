param([switch]$Setup)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
$Node = (Get-Command node -ErrorAction Stop).Source
$LogDir = Join-Path $ProjectRoot 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (-not (Test-Path (Join-Path $ProjectRoot '.env'))) {
  throw 'Missing .env. Run .\scripts\setup.ps1 first.'
}
if (-not (Test-Path $Python)) { throw 'Project Python environment is missing. Run .\scripts\setup.ps1.' }
try { & $Python -c 'import fastapi, uvicorn' } catch {
  throw 'The project Python executable could not start or dependencies are missing. Run .\scripts\setup.ps1 and check Python 3.11.'
}
if (-not (Test-Path (Join-Path $ProjectRoot 'frontend\node_modules\vite\bin\vite.js'))) {
  throw 'Frontend packages are missing. Run .\scripts\setup.ps1 first.'
}
Push-Location (Join-Path $ProjectRoot 'frontend')
try {
  & $Node scripts/build-css.mjs
  if ($LASTEXITCODE -ne 0) { throw 'Tailwind CSS generation failed.' }
} finally { Pop-Location }

$backend = Start-Process -PassThru -WindowStyle Hidden -FilePath $Python `
  -ArgumentList @('-m','uvicorn','main:app','--host','127.0.0.1','--port','8000') `
  -WorkingDirectory (Join-Path $ProjectRoot 'backend') `
  -RedirectStandardOutput (Join-Path $LogDir 'backend.log') `
  -RedirectStandardError (Join-Path $LogDir 'backend_err.log')
$backend.Id | Set-Content -LiteralPath (Join-Path $ProjectRoot '.backend.pid')

$frontend = Start-Process -PassThru -WindowStyle Hidden -FilePath $Node `
  -ArgumentList @('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173') `
  -WorkingDirectory (Join-Path $ProjectRoot 'frontend') `
  -RedirectStandardOutput (Join-Path $LogDir 'frontend.log') `
  -RedirectStandardError (Join-Path $LogDir 'frontend_err.log')
$frontend.Id | Set-Content -LiteralPath (Join-Path $ProjectRoot '.frontend.pid')

Start-Sleep -Seconds 4
try {
  $null = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 5
  Write-Host 'Backend:  http://127.0.0.1:8000  [ready]' -ForegroundColor Green
} catch {
  Write-Warning "Backend did not become ready. See $LogDir\backend_err.log"
}
Write-Host 'Frontend: http://127.0.0.1:5173' -ForegroundColor Cyan
Write-Host 'API docs: http://127.0.0.1:8000/docs'
Write-Host 'Stop with: .\scripts\stop.ps1'
