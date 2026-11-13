$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Missing venv Python. Run .\scripts\setup.ps1 first.' }
Push-Location $ProjectRoot
try {
  $rawCsv = Join-Path $ProjectRoot 'data\raw\bitext\Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv'
  if (-not (Test-Path $rawCsv)) {
    & $Python .\ml\download_dataset.py
    if ($LASTEXITCODE -ne 0) { throw 'Dataset download failed.' }
  } else {
    Write-Host 'Using the existing pinned Bitext raw CSV; it will not be overwritten.' -ForegroundColor Cyan
  }
  & $Python .\ml\preprocess.py
  if ($LASTEXITCODE -ne 0) { throw 'Dataset preprocessing failed.' }
  & $Python .\ml\train_models.py
  if ($LASTEXITCODE -ne 0) { throw 'Model training failed.' }
} finally { Pop-Location }
Write-Host 'Model training completed. Review docs\data_quality_report.md and docs\evaluation_report.md.' -ForegroundColor Green
