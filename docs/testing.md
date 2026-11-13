# Testing and quality verification

Verified on 2026-11-10 against the local Python 3.11.9 environment and MySQL 8.4.7.

## Publication-readiness rerun

After the dependency remediation and removal of confirmed-unused Vite starter files, the following commands were run against the current workspace:

- Full backend suite, including real MySQL integration: **33 passed, 0 failed**. MySQL integration tests used the configured MySQL 8.4.7 database, not SQLite or mocks; the browser and pytest fixtures cleaned up only their uniquely generated records.
- Playwright: **13 browser checks passed** against the live frontend, FastAPI API, and MySQL database. The script covered registration/login, roles, ticket create and prediction persistence, ticket updates/history/audit, filtering, analytics, CSV formula escaping, logout/protected pages, and responsive checks.
- Frontend production build: **passed** (TypeScript and Vite). Four upstream `use client` warnings remain.
- `pip check`: **no broken requirements**.
- `npm audit --omit=dev --audit-level=moderate`: **0 vulnerabilities**.
- Full-resolver `pip-audit -r backend/requirements.txt` (without `--no-deps`): **53 distributions audited, 0 vulnerable distributions, 0 known vulnerabilities**. Successful machine-readable report retained at [`python-dependency-audit.json`](python-dependency-audit.json). The first remediation candidate, cryptography 49.0.0, still had a finding; final pin is 50.0.0 and the final audit is clean.
- Final local Git review: **78 staged files, 0 unstaged tracked changes, 0 untracked files**. `git diff --cached --check` passed. `detect-secrets` scanned tracked files and returned 9 unverified candidates (source SHA-256 literals and test-only dummy credential fixtures); manual review found no real credentials. The staged path check found no `.env`, local database, raw/processed dataset, model artifact, or virtual environment paths. The fresh repository has no commit history.

Python dependency changes: FastAPI 0.111.0 → 0.162.2, Starlette 0.37.2 → 1.10.0 (now explicitly pinned), Pydantic 2.7.0 → 2.9.2 to meet the FastAPI constraint, cryptography 42.0.8 → 50.0.0, python-multipart 0.0.9 → 0.0.31, pytest 8.2.0 → 9.0.3, and python-dotenv 1.0.1 → 1.2.2. Removed Pillow 10.3.0 after confirming no application code uses it; removed pytest-asyncio 0.23.6 because async pytest usage was absent and that pin conflicts with pytest 9. Other direct requirement pins were left unchanged.

The historical audit notes below describe the pre-remediation state and are superseded by this section and the retained final report.

## Automated test commands and results

SQLite, dataset/model invariants, and live MySQL integration tests together:

```powershell
$env:RUN_MYSQL_INTEGRATION = '1'
.\venv\Scripts\python.exe -m pytest tests -q
Remove-Item Env:\RUN_MYSQL_INTEGRATION
```

Actual result at the prior security audit: **33 passed, 0 failed, 1 warning**. The latest post-remediation rerun above passed 33 tests with no failure. This includes six MySQL integration tests against the real configured MySQL SQLAlchemy engine; the fixture asserts the dialect is MySQL and performs a live `SELECT 1`. It uses unique disposable test users and removes only its own tickets and users.

Grouped evaluation can be reproduced independently with `.\venv\Scripts\python.exe .\ml\evaluate_intent_heldout.py` after preprocessing/training data is present.

Coverage includes authentication/registration, invalid login and invalid payloads, password hash verification, Admin and Support Agent authorization, health and schema metadata, ticket create/read/update/delete, prediction availability and persistence, status history, audit events, search/filter/pagination, database-backed dashboard values, CSV export and formula escaping, source checksums, class/split checks, the saved classifier, and intent-group isolation.

Earlier runs showed a Starlette TestClient deprecation caused by importing AnyIO's deprecated `anyio.abc.BlockingPortal` alias. The latest post-upgrade run reported no pytest warnings. Four Pydantic class-based config warnings and the `model_version` protected-name warning were eliminated with `ConfigDict`.

## Frontend production build

```powershell
Push-Location frontend
npm run build
Pop-Location
```

Verified: TypeScript check and Vite production build passed. Route-level lazy loading reduced the entry JavaScript chunk from 773.15 KB to 331.42 KB (gzip 108.19 KB). Recharts is a separate 403.36 KB chunk (gzip 113.68 KB), loaded for chart pages. Vite still reports four upstream `use client` module directive warnings from React Router and lucide-react. The previous >500 KB per-chunk warning is gone.

## Real browser end-to-end verification

The installed Chrome `157.0.8103.50` and Edge `157.0.4341.42` executables both crashed in headless rendering with GPU process status `-1073741790`. A search of recent Windows Application Error/WER events found no matching browser crash record. Playwright Python `1.65.0` and its compatible Chromium `158.0.8127.18` were installed in the existing local venv/user browser cache; the matched browser launched with SwiftShader software rendering and a clean temporary profile. No system browser was reinstalled or system graphics setting changed.

`python .\\scripts\\browser_e2e.py` completed successfully against the running frontend, FastAPI server, and actual local MySQL database. It used real UI interactions and unmocked API/database calls. It registered unique Admin and Support Agent accounts, exercised invalid and valid login, authenticated navigation, protected API/page behavior, ticket creation and category prediction, status changes, history and audit persistence, search/filter, dashboard and analytics, CSV download/formula escaping, role restrictions, and logout. The script verified ticket/prediction/history/audit rows directly in MySQL and removed only its uniquely created records. It also checked for page JavaScript exceptions and 5xx responses.

Responsive checks at 390 CSS pixels passed for dashboard, ticket list, ticket detail, and analytics (no horizontal overflow). The latest run passed all 13 workflow checks. Browser QA records were cleaned up. This workflow is reproducible locally:

```powershell
& .\\venv\\Scripts\\python.exe -m pip install playwright
& .\\venv\\Scripts\\python.exe -m playwright install chromium
$env:ALLOW_FIRST_USER_ADMIN = 'true' # isolated E2E only; database must be empty
& .\\scripts\\start.ps1
& .\\venv\\Scripts\\python.exe .\\scripts\\browser_e2e.py
& .\\scripts\\stop.ps1
Remove-Item Env:ALLOW_FIRST_USER_ADMIN
```

The optional Playwright dependency is local-only and is not part of backend requirements. The browser workflow explicitly requires the temporary `ALLOW_FIRST_USER_ADMIN=true` override because it tests the first UI registration as admin; the default is false. The script refuses to run when the MySQL `users` table is nonempty. Its cleanup recovers records using unique generated emails even if an earlier assertion interrupts the flow. Genuine rendered screenshots are checked in locally under [`screenshots`](screenshots/): [login](screenshots/login.png), [dashboard](screenshots/dashboard.png), [ticket list](screenshots/ticket-list.png), [ticket detail with prediction](screenshots/ticket-details.png), and [analytics](screenshots/analytics.png). Dashboard distribution panels can be empty for categories/statuses absent from the underlying records; no synthetic chart values are injected.

## Environment and security checks

- `pip check`: no broken Python requirements.
- `.gitignore` contains rules for `.env`, `/data/raw/`, `/data/processed/`, `/ml/models/`, and `/frontend/dist/`.
- `.gitignore` excludes `.env.*` while explicitly allowing the safe `.env.example`; data, model artifacts, runtime logs, caches, virtual environments, and frontend build output are excluded. A new local Git repository has staged publication candidates for review; there is no commit history and nothing has been committed or pushed.
- Fixed public self-service registration so it always creates Support Agent users by default. Initial Admin creation is an explicit local `scripts/create_admin.py` action using a hidden password prompt; an admin already present blocks the command. `ALLOW_FIRST_USER_ADMIN` defaults to false and is used only as an explicit isolated browser-test override.
- New and changed passwords require 12–128 characters; existing database password hashes/data were not modified. SQL access uses SQLAlchemy ORM/bound parameters; request text is length/type validated. CSV formula-leading cells are escaped before writing.
- High: fresh public sign-up previously made the first visitor an Admin. Fixed: sign-up now grants Support Agent by default; `ALLOW_FIRST_USER_ADMIN=false` is the default, and `scripts/create_admin.py` provides local one-time admin bootstrap with a hidden password prompt. Browser E2E uses an explicit temporary opt-in only with an empty test database.
- Medium: password minimum was six characters. Fixed: new registrations and password changes require 12–128 characters, login rejects oversized credentials before hashing, and ticket description updates now enforce the same 20,000-character bound as ticket creation.
- Medium: pinned `python-jose==3.3.0` was outdated and falls within a published algorithm-confusion advisory range. Replaced it with PyJWT 2.15.1, allow-listed HS256 in verification, removed the unused old package from the local venv, and added an unsigned-token rejection test. PyJWT release/advisory references: [PyJWT 2.15.1 on PyPI](https://pypi.org/project/PyJWT/2.15.1/), [python-jose CVE-2024-33663](https://github.com/advisories/GHSA-6c5p-j8vq-pqhj), and [PyJWT maintainer advisories](https://github.com/jpadilla/pyjwt/security/advisories).
- Dependency audit: see the publication-readiness rerun at the top for the final full-resolver Python result.
- Historical note: the pre-remediation audit flagged six distributions (cryptography, python-multipart, pytest, python-dotenv, Pillow, and Starlette). The latest complete resolver audit and current versions are recorded at the top of this document; that result supersedes the previous findings and failed early audit attempts.
- Publish hygiene: `.gitignore` excludes `.env`, `.env.*` (except safe `.env.example`), local SQLite files, runtime logs, virtual environments, raw/processed datasets, model artifacts, and frontend build output. Bitext attribution/license notes are in `dataset_review.md`; raw data and model artifacts are Git-ignored, screenshots show generated QA data. The root MIT `LICENSE` applies to project code only; dataset terms remain separate.
- Remaining limitations: bearer tokens in `localStorage` are exposed if an XSS bug is introduced; logout cannot revoke a copied stateless token before expiry; login has no rate limit/lockout; deployment still needs HTTPS, a least-privilege DB account, operational secret management, monitoring, and a production security review.
- Test output contains no database passwords or secret keys.
- Final frontend production build passed TypeScript and Vite. It generated CSS for 463 source tokens; CSS is 23.08 KB, entry JS 331.42 KB (gzip 108.19 KB), and Recharts chunk 403.36 KB (gzip 113.68 KB). Four upstream `use client` module-directive warnings remain; no chunk-size warning was emitted.
- Final `scripts/start.ps1`/`scripts/stop.ps1` workflow and browser run used the local API and frontend. The E2E script cleaned its records. The explicit test-runner shutdown stopped project API/frontend processes; MySQL was left running.
- `.gitignore` contains rules for `.env`, `/data/raw/`, `/data/processed/`, `/ml/models/`, and `/frontend/dist/`.
- No GitHub push, deployment, or publication was performed.
