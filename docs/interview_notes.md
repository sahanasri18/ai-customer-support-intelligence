# Project interview notes

## 60-second explanation

This is a local customer-support ticket platform built with React/TypeScript, FastAPI, SQLAlchemy, and MySQL. It supports role-gated ticket workflows, status history, audit records, database-backed analytics, CSV export, and a scikit-learn category classifier. The category model uses synthetic Bitext customer-service data; intent-held-out results are substantially lower than the random-split benchmark, so neither result is presented as real-world performance. Priority and sentiment models are unavailable, and urgency is a transparent keyword rule.

## Architecture walkthrough

1. React routes render sign-in, dashboard, ticket, analytics, reporting, user, and settings pages.
2. The browser attaches a bearer token from `localStorage`; FastAPI verifies HS256 and loads the active user from MySQL.
3. Routers validate requests with Pydantic and persist via SQLAlchemy. Tickets, predictions, status transitions, and audit events use separate records.
4. Ticket creation invokes the saved category model when available. Missing predictions remain unavailable/null; keyword urgency is a separate rule.
5. Analytics and CSV export read persisted ticket records. Formula-leading CSV values are escaped.

## Model and data notes

- TF-IDF + Linear SVC was selected against Logistic Regression using validation macro F1.
- Random held-out synthetic test: accuracy 0.9989, macro F1 0.9990. Whole-intent holdout: accuracy 0.6542, macro F1 0.5018 across nine testable categories. The split gap signals template leakage/optimism in the random benchmark.
- Bitext is under CDLA-Sharing-1.0; raw data, processed splits, and trained artifacts remain local and Git-ignored. Tobi's CC BY-NC 4.0 dataset was not used.
- See [`dataset_review.md`](dataset_review.md), [`evaluation_report.md`](evaluation_report.md), and [`grouped_evaluation_report.md`](grouped_evaluation_report.md) for source/licence and metrics details.

## Security status

- Public signup creates Support Agent accounts by default. The first administrator is created locally with `scripts/create_admin.py`; new passwords require at least 12 characters.
- JWT verification uses PyJWT 2.15.1 and allows only HS256. The frontend still stores bearer tokens in `localStorage`; a future XSS defect could expose them. Logout clears the local token but cannot revoke a copied stateless token before expiry.
- Login rate limiting/account lockout, production TLS/secrets management, least-privilege deployment DB credentials, monitoring, and a full Python dependency audit remain outstanding.

## Honest resume wording

Built and browser-verified a local full-stack customer-support ticket prototype with role-gated FastAPI/MySQL workflows, audit/history records, analytics, CSV export, and a locally trained TF-IDF category model. Reported ML scores are synthetic benchmarks; the grouped stress test exposes substantial optimism, and priority/sentiment prediction are unavailable.
