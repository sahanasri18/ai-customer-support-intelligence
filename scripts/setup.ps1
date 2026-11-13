$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
$StandardPython311 = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
$Npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
$Mysql = Get-Command mysql -ErrorAction SilentlyContinue

if (-not (Test-Path $StandardPython311) -and -not $PythonLauncher) { throw 'Python 3.11 was not found. Install the standard Windows Python 3.11 release from python.org.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not $Npm) { throw 'Node.js and npm.cmd are required.' }
if (-not $Mysql) { Write-Warning 'mysql.exe is not on PATH. Run database/schema.sql manually before starting the API.' }

$venvPython = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
  if (Test-Path $StandardPython311) {
    & $StandardPython311 -m venv $venvPython.Substring(0, $venvPython.LastIndexOf('\Scripts\'))
  } else {
    & $PythonLauncher.Source -3.11 -m venv $venvPython.Substring(0, $venvPython.LastIndexOf('\Scripts\'))
  }
  if ($LASTEXITCODE -ne 0) { throw 'Could not create venv. Check that Python 3.11 can start from the terminal.' }
}
try {
  & $venvPython -c 'import sys; print(sys.version)'
  if ($LASTEXITCODE -ne 0) { throw 'Interpreter returned a failure code.' }
} catch {
  throw "The existing project virtual environment cannot start ($venvPython). It references an unavailable Windows Store Python install. Install Python 3.11 from python.org, then recreate this environment before continuing."
}

Write-Host 'Installing backend dependencies...' -ForegroundColor Yellow
& $venvPython -m pip install -r (Join-Path $ProjectRoot 'backend\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }

Write-Host 'Installing frontend dependencies...' -ForegroundColor Yellow
Push-Location (Join-Path $ProjectRoot 'frontend')
try {
  & $Npm.Source install --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'npm dependency installation failed.' }
} finally { Pop-Location }

$envPath = Join-Path $ProjectRoot '.env'
if (-not (Test-Path $envPath)) {
  $bytes = New-Object byte[] 48
  $rng = New-Object Security.Cryptography.RNGCryptoServiceProvider
  $rng.GetBytes($bytes)
  $secret = [Convert]::ToBase64String($bytes)
  $examplePath = Join-Path $ProjectRoot '.env.example'
  $envContent = (Get-Content -LiteralPath $examplePath -Raw).Replace('Generate-a-local-random-secret-with-scripts/setup.ps1', $secret)
  [IO.File]::WriteAllText($envPath, $envContent, [Text.UTF8Encoding]::new($false))
  $rng.Dispose(); [Array]::Clear($bytes, 0, $bytes.Length)
  Remove-Variable secret,envContent,bytes,rng
  Write-Host 'Created .env with a random local secret. Database password is blank until configured.' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Setup dependencies are ready.' -ForegroundColor Green
Write-Host 'If MySQL database/tables are not initialized, run in a local terminal:'
Write-Host '  cmd.exe /c "mysql -u root -p < database\schema.sql"'
Write-Host 'Set DB_PASSWORD in .env using a local editor; never paste it into chat.'
Write-Host 'Start with: .\scripts\start.ps1'
