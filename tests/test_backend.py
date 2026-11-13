"""
Backend tests for auth, tickets, and analytics endpoints.
Uses FastAPI TestClient with an in-memory SQLite override.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys, os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import Base, get_db
from main import app

# Use in-memory SQLite for tests (no MySQL needed)
TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ---- Helpers ----
def register_and_login(email="test@example.com", password="testpassword123", name="Test User"):
    client.post("/api/auth/register", json={"email": email, "full_name": name, "password": password})
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


# ---- Tests ----
class TestAuth:
    def test_register_success(self):
        r = client.post("/api/auth/register", json={
            "email": "new@example.com", "full_name": "New User", "password": "password12345"
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "new@example.com"
        assert "hashed_password" not in data
        assert data["role"] == "agent"

    def test_register_duplicate_email(self):
        client.post("/api/auth/register", json={
            "email": "dup@example.com", "full_name": "Dup", "password": "password12345"
        })
        r = client.post("/api/auth/register", json={
            "email": "dup@example.com", "full_name": "Dup2", "password": "password12345"
        })
        assert r.status_code == 400

    def test_login_success(self):
        client.post("/api/auth/register", json={
            "email": "login@example.com", "full_name": "Login User", "password": "loginpass1234"
        })
        r = client.post("/api/auth/login", data={"username": "login@example.com", "password": "loginpass1234"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self):
        client.post("/api/auth/register", json={
            "email": "wrong@example.com", "full_name": "Wrong", "password": "correct-password"
        })
        r = client.post("/api/auth/login", data={"username": "wrong@example.com", "password": "incorrect"})
        assert r.status_code == 401

    def test_unsigned_jwt_is_rejected(self):
        token = jwt.encode(
            {"sub": "1", "exp": datetime.utcnow() + timedelta(minutes=1)},
            "",
            algorithm="none",
        )
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_registration_rejects_short_password(self):
        response = client.post("/api/auth/register", json={
            "email": "short-password@example.com", "full_name": "Short Password", "password": "shortpw"
        })
        assert response.status_code == 422

    def test_login_rejects_oversized_password_before_hash_verification(self):
        response = client.post("/api/auth/login", data={
            "username": "unknown@example.com", "password": "x" * 129
        })
        assert response.status_code == 401

    def test_me_endpoint(self):
        token = register_and_login("me@example.com", "mepassword123", "Me User")
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["email"] == "me@example.com"


class TestTickets:
    def setup_method(self):
        self.token = register_and_login(f"agent_{id(self)}@example.com", "agentpassword123", "Agent")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_create_ticket(self):
        r = client.post("/api/tickets/", json={
            "subject": "Cannot login to account",
            "description": "I am unable to login to my account since yesterday. Please help urgently.",
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
        }, headers=self.headers)
        assert r.status_code == 201
        data = r.json()
        assert data["subject"] == "Cannot login to account"
        assert data["ticket_number"].startswith("TKT-")
        assert isinstance(data["is_urgent"], bool)

    def test_list_tickets(self):
        r = client.get("/api/tickets/", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    def test_get_ticket(self):
        c = client.post("/api/tickets/", json={
            "subject": "Test get ticket", "description": "Some description for testing get endpoint."
        }, headers=self.headers)
        tid = c.json()["id"]
        r = client.get(f"/api/tickets/{tid}", headers=self.headers)
        assert r.status_code == 200
        assert r.json()["id"] == tid

    def test_update_ticket_status(self):
        c = client.post("/api/tickets/", json={
            "subject": "Status update test", "description": "Testing status update flow correctly."
        }, headers=self.headers)
        tid = c.json()["id"]
        r = client.patch(f"/api/tickets/{tid}", json={"status": "in_progress", "comment": "Working on it"},
                         headers=self.headers)
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_ticket_not_found(self):
        r = client.get("/api/tickets/99999", headers=self.headers)
        assert r.status_code == 404

    def test_ticket_update_rejects_oversized_description(self):
        created = client.post("/api/tickets/", json={
            "subject": "Bounded update input", "description": "A valid ticket description for this test."
        }, headers=self.headers)
        response = client.patch(
            f"/api/tickets/{created.json()['id']}",
            json={"description": "x" * 20001},
            headers=self.headers,
        )
        assert response.status_code == 422

    def test_search_tickets(self):
        client.post("/api/tickets/", json={
            "subject": "Payment issue SearchTest", "description": "Customer cannot process payment."
        }, headers=self.headers)
        r = client.get("/api/tickets/?search=SearchTest", headers=self.headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1


class TestAnalytics:
    def setup_method(self):
        self.token = register_and_login(f"analyst_{id(self)}@example.com", "analyticpassword", "Analyst")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_dashboard(self):
        r = client.get("/api/analytics/dashboard", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        for key in ["total_tickets", "open_tickets", "category_distribution", "tickets_last_7_days"]:
            assert key in data

    def test_unauthenticated_access(self):
        r = client.get("/api/analytics/dashboard")
        assert r.status_code == 401

    def test_agent_cannot_manage_users(self):
        r = client.get("/api/users/", headers=self.headers)
        assert r.status_code == 403

    def test_csv_export_requires_authentication(self):
        r = client.get("/api/tickets/export/csv")
        assert r.status_code == 401


class TestPredictions:
    def setup_method(self):
        self.token = register_and_login(f"predict_{id(self)}@example.com", "predictpassword", "Predict User")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_model_status_and_task_responses_match_installed_models(self):
        status = client.get("/api/predictions/status", headers=self.headers)
        assert status.status_code == 200
        models = status.json()["models"]

        payload = {
            "subject": "Question about cancelling an order",
            "description": "I need help cancelling this order and understanding the next steps.",
        }
        category = client.post("/api/predictions/category", json=payload, headers=self.headers)
        priority = client.post("/api/predictions/priority", json=payload, headers=self.headers)
        sentiment = client.post("/api/predictions/sentiment", json=payload, headers=self.headers)
        assert category.status_code == priority.status_code == sentiment.status_code == 200

        if models["category"]["available"]:
            assert category.json()["status"] == "available"
            assert isinstance(category.json()["prediction"], str)
            assert category.json()["model_version"] == status.json()["model_version"]
        else:
            assert category.json()["status"] == "unavailable"
            assert category.json()["prediction"] is None
            assert category.json()["confidence"] is None

        assert (priority.json()["status"] == "available") is models["priority"]["available"]
        assert (sentiment.json()["status"] == "available") is models["sentiment"]["available"]
        if not models["priority"]["available"]:
            assert priority.json()["prediction"] is None and priority.json()["confidence"] is None
        if not models["sentiment"]["available"]:
            assert sentiment.json()["prediction"] is None and sentiment.json()["confidence"] is None

    def test_model_status_requires_authentication(self):
        assert client.get("/api/predictions/status").status_code == 401


class TestHealth:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_database_health_uses_test_database(self):
        r = client.get("/health/database")
        assert r.status_code == 200
        assert r.json()["database"] == "reachable"
