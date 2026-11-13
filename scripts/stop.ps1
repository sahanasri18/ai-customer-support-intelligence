$ErrorActionPreference = 'Continue'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

foreach ($name in @('.backend.pid', '.frontend.pid')) {
  $pidFile = Join-Path $ProjectRoot $name
  if (-not (Test-Path -LiteralPath $pidFile)) { continue }
  $processId = 0
  $value = Get-Content -LiteralPath $pidFile -Raw
  if ([int]::TryParse($value.Trim(), [ref]$processId)) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    $executablePath = $process.ExecutablePath
    $processStartTime = $null
    if (-not $executablePath) {
      # CIM/WMI access can be restricted on managed Windows machines. The PID
      # file is created only by start.ps1; Get-Process provides a safe fallback.
      $localProcess = Get-Process -Id $processId -ErrorAction SilentlyContinue
      if ($localProcess) {
        $executablePath = $localProcess.Path
        $processStartTime = $localProcess.StartTime
      }
    }
    if ($executablePath) {
      $resolvedExe = [IO.Path]::GetFullPath($executablePath)
      $isProjectPython = $resolvedExe.Equals((Join-Path $ProjectRoot 'venv\Scripts\python.exe'), [StringComparison]::OrdinalIgnoreCase)
      $isNode = [IO.Path]::GetFileName($resolvedExe).Equals('node.exe', [StringComparison]::OrdinalIgnoreCase)
      if (-not $processStartTime) {
        try { $processStartTime = (Get-Process -Id $processId -ErrorAction Stop).StartTime } catch { $processStartTime = $null }
      }
      $pidFileTime = (Get-Item -LiteralPath $pidFile).LastWriteTime
      $createdForThisRun = $processStartTime -and ([Math]::Abs(($processStartTime - $pidFileTime).TotalSeconds) -lt 120)
      if (($isProjectPython -or $isNode) -and $createdForThisRun) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped project process $processId" -ForegroundColor Green
      } else {
        Write-Warning "PID $processId no longer belongs to a recognized project process; left it running."
      }
    }
  }
  Remove-Item -LiteralPath $pidFile -Force
}
Write-Host 'Project processes stopped.'
