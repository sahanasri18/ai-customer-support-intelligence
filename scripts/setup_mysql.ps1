$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvFile = Join-Path $ProjectRoot '.env'
$SchemaFile = Join-Path $ProjectRoot 'database\schema.sql'
$Python = Join-Path $ProjectRoot 'venv\Scripts\python.exe'

if (-not (Test-Path $EnvFile)) { throw 'Missing .env. Run .\scripts\setup.ps1 first.' }
if (-not (Test-Path $Python)) { throw 'Missing working venv. Run .\scripts\setup.ps1 first.' }
if (-not (Test-Path $SchemaFile)) { throw 'Missing database\schema.sql.' }

$envLines = [IO.File]::ReadAllLines($EnvFile)
function Read-EnvValue([string]$Name, [string]$Default) {
  foreach ($line in $envLines) {
    if ($line -match ('^\s*' + [regex]::Escape($Name) + '\s*=\s*(.*)$')) {
      return $Matches[1].Trim().Trim('"').Trim("'")
    }
  }
  return $Default
}

$DbUser = Read-EnvValue 'DB_USER' 'root'
$DbHost = Read-EnvValue 'DB_HOST' 'localhost'
$DbPort = Read-EnvValue 'DB_PORT' '3306'
$DbName = Read-EnvValue 'DB_NAME' 'customer_support_db'
$DatabaseUrl = Read-EnvValue 'DATABASE_URL' ''
if ($DatabaseUrl) { throw 'DATABASE_URL is set. This setup helper only configures the project DB_HOST/DB_PORT/DB_NAME/DB_USER settings.' }

Write-Host "Enter the MySQL password for $DbUser at the hidden prompt. It will not be displayed or written to logs." -ForegroundColor Yellow
$SecurePassword = Read-Host 'MySQL password' -AsSecureString
$PasswordPointer = [IntPtr]::Zero
$PasswordText = $null
Push-Location $ProjectRoot
try {
  $PasswordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
  $PasswordText = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($PasswordPointer)
  $env:DB_PASSWORD = $PasswordText
  $env:DB_USER = $DbUser
  $env:DB_HOST = $DbHost
  $env:DB_PORT = $DbPort
  $env:DB_NAME = $DbName
  $env:DATABASE_URL = ''

  @'
import re
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
sys.path.insert(0, str(Path.cwd() / "backend"))
from config import settings

def stop(message):
    print(message)
    raise SystemExit(1)

if settings.DATABASE_URL:
    stop("DATABASE_URL is set; refusing to apply schema to a different target.")
if not re.fullmatch(r"[A-Za-z0-9_]+", settings.DB_NAME):
    stop("Configured database name contains unsupported characters; no schema changes were made.")

server_url = URL.create(
    "mysql+pymysql", username=settings.DB_USER, password=settings.DB_PASSWORD,
    host=settings.DB_HOST, port=settings.DB_PORT,
)
server_engine = create_engine(server_url, pool_pre_ping=True)
try:
    with server_engine.connect() as connection:
        version = connection.execute(text("SELECT VERSION()")).scalar_one()
        authenticated_as = connection.execute(text("SELECT CURRENT_USER()")).scalar_one()
        print(f"MySQL connection: OK ({version}; authenticated as {authenticated_as})")

        sql = Path("database/schema.sql").read_text(encoding="utf-8-sig")
        sql = re.sub(r"(?m)^\s*--.*?$", "", sql)
        statements = [part.strip() for part in sql.split(";") if part.strip()]
        if not statements:
            stop("Schema file contains no SQL statements.")
        selected_database = None
        for statement in statements:
            create_db = re.fullmatch(
                r"CREATE\s+DATABASE\s+IF\s+NOT\s+EXISTS\s+`?([A-Za-z0-9_]+)`?.*",
                statement, re.IGNORECASE | re.DOTALL,
            )
            use_db = re.fullmatch(r"USE\s+`?([A-Za-z0-9_]+)`?", statement, re.IGNORECASE)
            create_table = re.match(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\b", statement, re.IGNORECASE)
            if create_db:
                if create_db.group(1) != settings.DB_NAME:
                    stop("Schema database name differs from .env DB_NAME; no schema changes were made.")
                connection.exec_driver_sql(statement)
            elif use_db:
                if use_db.group(1) != settings.DB_NAME:
                    stop("Schema USE target differs from .env DB_NAME; no table changes were made.")
                connection.exec_driver_sql(statement)
                selected_database = use_db.group(1)
            elif create_table and selected_database == settings.DB_NAME:
                connection.exec_driver_sql(statement)
            else:
                stop("Schema contains a non-idempotent or unexpected statement; refusing to execute it.")
        print("Existing schema applied with CREATE DATABASE/TABLE IF NOT EXISTS; no DROP or overwrite statements were run.")
finally:
    server_engine.dispose()

from database import engine
with engine.connect() as connection:
    assert connection.execute(text("SELECT 1")).scalar_one() == 1
    print("SQLAlchemy application connection: OK")

inspector = inspect(engine)
required = {"users", "tickets", "ticket_predictions", "ticket_status_history", "audit_logs"}
tables = set(inspector.get_table_names())
if not required.issubset(tables):
    stop("One or more expected project tables are missing.")
if inspector.get_pk_constraint("tickets").get("constrained_columns") != ["id"]:
    stop("tickets primary key does not match the project schema.")
expected_foreign_keys = {
    "tickets": {"users"}, "ticket_predictions": {"tickets"},
    "ticket_status_history": {"tickets", "users"}, "audit_logs": {"users", "tickets"},
}
expected_indexes = {
    "users": {"ix_users_email"},
    "tickets": {"ix_tickets_status", "ix_tickets_priority", "ix_tickets_created_at", "ix_tickets_ticket_number"},
    "ticket_predictions": {"ix_ticket_predictions_ticket_id"},
    "ticket_status_history": {"ix_ticket_status_history_ticket_id"},
    "audit_logs": {"ix_audit_logs_created_at", "ix_audit_logs_user_id", "ix_audit_logs_ticket_id"},
}
for table in sorted(required):
    if inspector.get_pk_constraint(table).get("constrained_columns") != ["id"]:
        stop(f"{table} primary key does not match the project schema.")
    actual_indexes = {index.get("name") for index in inspector.get_indexes(table)}
    if not expected_indexes.get(table, set()).issubset(actual_indexes):
        stop(f"One or more expected indexes are missing from {table}.")
    actual_fks = {fk.get("referred_table") for fk in inspector.get_foreign_keys(table)}
    if not expected_foreign_keys.get(table, set()).issubset(actual_fks):
        stop(f"One or more expected foreign keys are missing from {table}.")
print("Schema verification: all expected tables, primary keys, foreign keys and indexes are present.")
'@ | & $Python -
  if ($LASTEXITCODE -ne 0) { throw 'MySQL connection/schema verification failed. .env was not changed.' }

  # Persist the credential only after authentication and schema checks pass.
  # .env is excluded by the project's ignore rules. Single quotes and
  # backslashes are escaped for python-dotenv's quoted-value syntax.
  $escapedPassword = $PasswordText.Replace('\', '\\').Replace("'", "\'")
  $envText = [IO.File]::ReadAllText($EnvFile)
  $replacement = "DB_PASSWORD='$escapedPassword'"
  if ($envText -match '(?m)^\s*DB_PASSWORD\s*=') {
    $envText = [regex]::Replace($envText, '(?m)^\s*DB_PASSWORD\s*=.*$', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement })
  } else {
    $envText = $envText.TrimEnd() + "`r`n$replacement`r`n"
  }
  [IO.File]::WriteAllText($EnvFile, $envText, [Text.UTF8Encoding]::new($false))
  Remove-Variable escapedPassword,envText,replacement

  Write-Host 'Running the full backend suite, including opt-in real-MySQL integration tests...' -ForegroundColor Yellow
  $env:RUN_MYSQL_INTEGRATION = '1'
  Push-Location $ProjectRoot
  try {
    & $Python -m pytest tests -v
    if ($LASTEXITCODE -ne 0) { throw "Backend or MySQL integration tests failed with exit code $LASTEXITCODE." }
  } finally { Pop-Location }
  Write-Host 'Backend and MySQL integration tests passed.' -ForegroundColor Green
} finally {
  Remove-Item Env:\DB_PASSWORD, Env:\DB_USER, Env:\DB_HOST, Env:\DB_PORT, Env:\DB_NAME, Env:\DATABASE_URL, Env:\RUN_MYSQL_INTEGRATION -ErrorAction SilentlyContinue
  if ($PasswordPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($PasswordPointer) }
  $PasswordText = $null
  if ($SecurePassword) { $SecurePassword.Dispose() }
  Remove-Variable PasswordText,SecurePassword,PasswordPointer -ErrorAction SilentlyContinue
  Pop-Location
}
