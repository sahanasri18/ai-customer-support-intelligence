"""Opt-in tests against the configured, real MySQL database.

Run with RUN_MYSQL_INTEGRATION=1 after applying database/schema.sql. These
tests create uniquely named disposable rows and remove only those rows.
"""
import csv
import io
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from auth import verify_password
from database import Base, SessionLocal, engine, get_db
import models
from main import app

REQUIRED_TABLES = {
    "users", "tickets", "ticket_predictions", "ticket_status_history", "audit_logs"
}

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_MYSQL_INTEGRATION") != "1",
    reason="Set RUN_MYSQL_INTEGRATION=1 to run against the configured local MySQL database",
)


@pytest.fixture
def mysql_client():
    """Use the real configured engine; never create tables or replace the DB."""
    assert engine.dialect.name == "mysql", "Integration tests must use MySQL, not SQLite"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1

    assert REQUIRED_TABLES.issubset(set(inspect(engine).get_table_names()))

    marker = uuid.uuid4().hex
    admin_email = f"mysql-admin-{marker}@example.com"
    agent_email = f"mysql-agent-{marker}@example.com"
    admin_password = f"MySQLAdmin-{marker}!"
    agent_password = f"MySQLAgent-{marker}!"
    client = TestClient(app)
    previous_db_override = app.dependency_overrides.pop(get_db, None)
    created_user_ids = []
    try:
        admin_registration = client.post("/api/auth/register", json={
            "email": admin_email, "full_name": "MySQL Integration Admin", "password": admin_password
        })
        assert admin_registration.status_code == 201, admin_registration.text
        admin_id = admin_registration.json()["id"]
        created_user_ids.append(admin_id)

        agent_registration = client.post("/api/auth/register", json={
            "email": agent_email, "full_name": "MySQL Integration Agent", "password": agent_password
        })
        assert agent_registration.status_code == 201, agent_registration.text
        agent_id = agent_registration.json()["id"]
        created_user_ids.append(agent_id)

        # The app promotes only the first registered account. Promote this isolated
        # test account explicitly so the role checks do not depend on DB contents.
        with SessionLocal() as db:
            admin = db.query(models.User).filter(models.User.id == admin_id).one()
            admin.role = models.RoleEnum.admin
            db.commit()
            assert verify_password(admin_password, admin.hashed_password)

        admin_login = client.post("/api/auth/login", data={
            "username": admin_email, "password": admin_password
        })
        agent_login = client.post("/api/auth/login", data={
            "username": agent_email, "password": agent_password
        })
        assert admin_login.status_code == agent_login.status_code == 200
        client.admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        client.agent_headers = {"Authorization": f"Bearer {agent_login.json()['access_token']}"}
        client.integration_marker = marker
        client.integration_user_ids = (admin_id, agent_id)
        client.integration_passwords = (admin_password, agent_password)
        yield client
    finally:
        try:
            # Clean only rows created by this fixture, preserving all preexisting data.
            if created_user_ids:
                with SessionLocal() as db:
                    tickets = db.query(models.Ticket).filter(
                        models.Ticket.created_by.in_(created_user_ids)
                    ).all()
                    ticket_ids = [ticket.id for ticket in tickets]
                    db.query(models.AuditLog).filter(
                        (models.AuditLog.user_id.in_(created_user_ids)) |
                        (models.AuditLog.ticket_id.in_(ticket_ids if ticket_ids else [-1]))
                    ).delete(synchronize_session=False)
                    if ticket_ids:
                        db.query(models.TicketStatusHistory).filter(
                            models.TicketStatusHistory.ticket_id.in_(ticket_ids)
                        ).delete(synchronize_session=False)
                        db.query(models.TicketPrediction).filter(
                            models.TicketPrediction.ticket_id.in_(ticket_ids)
                        ).delete(synchronize_session=False)
                        db.query(models.Ticket).filter(models.Ticket.id.in_(ticket_ids)).delete(
                            synchronize_session=False
                        )
                    db.query(models.User).filter(
                        models.User.id.in_(created_user_ids)
                    ).delete(synchronize_session=False)
                    db.commit()
        finally:
            if previous_db_override is not None:
                app.dependency_overrides[get_db] = previous_db_override


def test_mysql_connection_schema_and_health(mysql_client):
    response = mysql_client.get("/health/database")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}

    inspector = inspect(engine)
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
    for table in REQUIRED_TABLES:
        assert inspector.get_pk_constraint(table)["constrained_columns"] == ["id"]
        fk_targets = {fk["referred_table"] for fk in inspector.get_foreign_keys(table)}
        assert expected_foreign_keys.get(table, set()).issubset(fk_targets)
        index_names = {index["name"] for index in inspector.get_indexes(table)}
        assert expected_indexes.get(table, set()).issubset(index_names)


def test_mysql_auth_roles_password_hash_and_restrictions(mysql_client):
    admin_id, agent_id = mysql_client.integration_user_ids
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.id == admin_id).one()
        agent = db.query(models.User).filter(models.User.id == agent_id).one()
        assert admin.role == models.RoleEnum.admin
        assert agent.role == models.RoleEnum.agent
        assert verify_password(mysql_client.integration_passwords[0], admin.hashed_password)
        assert not verify_password("wrong-password-for-test", admin.hashed_password)

    assert mysql_client.get("/api/users/", headers=mysql_client.admin_headers).status_code == 200
    assert mysql_client.get("/api/users/", headers=mysql_client.agent_headers).status_code == 403
    assert mysql_client.get("/api/analytics/dashboard").status_code == 401


def test_mysql_auth_validation_audit_and_dashboard_security(mysql_client):
    admin_id, agent_id = mysql_client.integration_user_ids
    admin_email = f"mysql-admin-{mysql_client.integration_marker}@example.com"

    bad_login = mysql_client.post("/api/auth/login", data={
        "username": admin_email, "password": "wrong-password-for-test"
    })
    assert bad_login.status_code == 401
    assert mysql_client.get("/api/auth/me").status_code == 401
    assert mysql_client.get("/api/tickets/").status_code == 401
    assert mysql_client.get("/api/tickets/export/csv").status_code == 401

    invalid_registration = mysql_client.post("/api/auth/register", json={
        "email": "not-an-email", "full_name": "Invalid User", "password": "ValidPassword123!"
    })
    assert invalid_registration.status_code == 422
    invalid_ticket = mysql_client.post("/api/tickets/", headers=mysql_client.agent_headers, json={
        "subject": "x", "description": "short"
    })
    assert invalid_ticket.status_code == 422

    assert mysql_client.get("/api/analytics/audit-logs", headers=mysql_client.agent_headers).status_code == 403
    admin_audit = mysql_client.get("/api/analytics/audit-logs", headers=mysql_client.admin_headers)
    assert admin_audit.status_code == 200
    assert {row["action"] for row in admin_audit.json()["items"] if row["user_id"] in (admin_id, agent_id)} >= {
        "user_registered", "user_login"
    }

    created = mysql_client.post("/api/tickets/", headers=mysql_client.agent_headers, json={
        "subject": f"Live analytics {mysql_client.integration_marker}",
        "description": "A real ticket used to verify database-backed dashboard totals.",
    })
    assert created.status_code == 201
    dashboard = mysql_client.get("/api/analytics/dashboard", headers=mysql_client.agent_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_tickets"] >= 1
    assert any(row["id"] == created.json()["id"] for row in dashboard.json()["recent_tickets"])
    assert mysql_client.get("/api/users/", headers=mysql_client.agent_headers).status_code == 403


def test_mysql_ticket_crud_status_audit_search_filter_and_pagination(mysql_client):
    marker = mysql_client.integration_marker
    created = mysql_client.post("/api/tickets/", headers=mysql_client.agent_headers, json={
        "subject": f"MySQL Integration {marker}",
        "description": "Verify MySQL persistence, history, filters and paging.",
        "category": "mysql-integration",
        "priority": "high",
    })
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    read_back = mysql_client.get(f"/api/tickets/{ticket_id}", headers=mysql_client.agent_headers)
    assert read_back.status_code == 200
    assert read_back.json()["subject"].endswith(marker)

    updated = mysql_client.patch(f"/api/tickets/{ticket_id}", headers=mysql_client.agent_headers, json={
        "status": "in_progress", "comment": "MySQL integration status update"
    })
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    filtered = mysql_client.get(
        "/api/tickets/", headers=mysql_client.agent_headers,
        params={"search": marker, "category": "mysql-integration", "status": "in_progress", "page": 1, "page_size": 1},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert len(filtered.json()["items"]) == 1
    assert filtered.json()["items"][0]["id"] == ticket_id
    assert len(filtered.json()["items"][0]["status_history"]) >= 2

    with SessionLocal() as db:
        assert db.query(models.Ticket).filter_by(id=ticket_id).one().status == models.TicketStatusEnum.in_progress
        assert db.query(models.TicketStatusHistory).filter_by(ticket_id=ticket_id).count() >= 2
        assert db.query(models.AuditLog).filter_by(ticket_id=ticket_id, action="ticket_created").count() == 1
        assert db.query(models.AuditLog).filter_by(ticket_id=ticket_id, action="ticket_updated").count() == 1

    assert mysql_client.delete(f"/api/tickets/{ticket_id}", headers=mysql_client.agent_headers).status_code == 403
    assert mysql_client.delete(f"/api/tickets/{ticket_id}", headers=mysql_client.admin_headers).status_code == 204
    assert mysql_client.get(f"/api/tickets/{ticket_id}", headers=mysql_client.agent_headers).status_code == 404


def test_mysql_csv_export_escapes_formulas(mysql_client):
    marker = mysql_client.integration_marker
    created = mysql_client.post("/api/tickets/", headers=mysql_client.agent_headers, json={
        "subject": f"=HYPERLINK(\"https://example.invalid/{marker}\")",
        "description": "CSV formula escaping must persist and be safe.",
    })
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    exported = mysql_client.get("/api/tickets/export/csv", headers=mysql_client.agent_headers)
    assert exported.status_code == 200
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    row = next(item for item in rows if item["ticket_number"] == created.json()["ticket_number"])
    assert row["subject"].startswith("'=HYPERLINK(")
    assert mysql_client.get("/api/tickets/export/csv").status_code == 401

    with SessionLocal() as db:
        assert db.query(models.Ticket).filter_by(id=ticket_id).one().subject.startswith("=HYPERLINK(")


def test_mysql_prediction_api_and_ticket_prediction_persistence(mysql_client):
    status = mysql_client.get("/api/predictions/status", headers=mysql_client.agent_headers)
    assert status.status_code == 200
    model_status = status.json()
    assert model_status["models"]["category"]["available"] is True
    assert model_status["models"]["category"]["confidence_available"] is False
    assert model_status["models"]["priority"]["available"] is False
    assert model_status["models"]["sentiment"]["available"] is False

    payload = {
        "subject": "Urgent question about cancelling an order",
        "description": "Urgent: I need help cancelling this order and understanding the next steps.",
    }
    category = mysql_client.post(
        "/api/predictions/category", json=payload, headers=mysql_client.agent_headers
    )
    assert category.status_code == 200
    assert category.json()["status"] == "available"
    assert category.json()["prediction"] is not None
    assert category.json()["confidence"] is None
    assert category.json()["model_version"] == model_status["model_version"]

    priority = mysql_client.post(
        "/api/predictions/priority", json=payload, headers=mysql_client.agent_headers
    )
    sentiment = mysql_client.post(
        "/api/predictions/sentiment", json=payload, headers=mysql_client.agent_headers
    )
    assert priority.status_code == sentiment.status_code == 200
    assert priority.json()["status"] == sentiment.json()["status"] == "unavailable"
    assert priority.json()["prediction"] is sentiment.json()["prediction"] is None
    assert priority.json()["confidence"] is sentiment.json()["confidence"] is None

    ticket = mysql_client.post("/api/tickets/", json=payload, headers=mysql_client.agent_headers)
    assert ticket.status_code == 201
    ticket_id = ticket.json()["id"]
    assert ticket.json()["predictions"]["predicted_category"] == category.json()["prediction"]
    assert ticket.json()["predictions"]["predicted_priority"] is None
    assert ticket.json()["predictions"]["predicted_sentiment"] is None
    assert ticket.json()["predictions"]["category_confidence"] is None
    assert ticket.json()["predictions"]["model_version"] == model_status["model_version"]
    assert ticket.json()["is_urgent"] is True
    assert ticket.json()["predictions"]["is_urgent_rule_based"] is True

    rerun = mysql_client.post(
        f"/api/tickets/{ticket_id}/predict", headers=mysql_client.agent_headers
    )
    assert rerun.status_code == 200
    assert rerun.json()["predicted_category"] == category.json()["prediction"]
    assert rerun.json()["model_version"] == model_status["model_version"]

    with SessionLocal() as db:
        saved = db.query(models.TicketPrediction).filter_by(ticket_id=ticket_id).one()
        assert saved.predicted_category == category.json()["prediction"]
        assert saved.predicted_priority is None
        assert saved.predicted_sentiment is None
        assert saved.model_version == model_status["model_version"]
