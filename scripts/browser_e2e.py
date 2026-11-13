"""Run a real Playwright workflow against the local Vite, FastAPI, and MySQL app.

Requires Playwright plus its Chromium browser. The script refuses to start if
the MySQL users table is nonempty, creates only unique QA records, and removes
only records identified by its generated user/ticket IDs.
"""
import csv
import io
import secrets
import sys
import uuid
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from auth import verify_password  # noqa: E402
from config import settings  # noqa: E402
from database import SessionLocal, engine  # noqa: E402
import models  # noqa: E402


BASE_URL = "http://localhost:5173"
SCREENSHOT_DIR = ROOT / "docs" / "screenshots"


def main() -> None:
    if engine.dialect.name != "mysql":
        raise SystemExit("Refusing browser QA: configured SQLAlchemy engine is not MySQL.")
    if not settings.ALLOW_FIRST_USER_ADMIN:
        raise SystemExit("Refusing browser QA: start the isolated empty test database with ALLOW_FIRST_USER_ADMIN=true.")
    with SessionLocal() as db:
        if db.query(models.User).count() != 0:
            raise SystemExit("Refusing to seed browser QA into a nonempty users table.")

    marker = uuid.uuid4().hex[:12]
    admin_email = f"browser-admin-{marker}@example.com"
    agent_email = f"browser-agent-{marker}@example.com"
    admin_password = f"QA!{secrets.token_urlsafe(24)}a9"
    agent_password = f"QA!{secrets.token_urlsafe(24)}b8"
    subject = f"=1+1 browser-qa-{marker}"
    description = (
        "Urgent: my monthly subscription renewal was charged twice. "
        "Please help me get a refund for the duplicate charge."
    )
    admin_id = agent_id = ticket_id = None
    browser = None
    checks = []
    page_errors = []
    server_errors = []
    download_path = Path(__import__("tempfile").gettempdir()) / f"browser-qa-{marker}.csv"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu",
                    "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                ],
            )
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("response", lambda response: server_errors.append(f"{response.status} {response.url}") if response.status >= 500 else None)

            page.goto(f"{BASE_URL}/login", wait_until="networkidle")
            expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
            page.screenshot(path=SCREENSHOT_DIR / "login.png", full_page=True)
            checks.append("login rendered in Playwright Chromium")

            page.goto(f"{BASE_URL}/register", wait_until="networkidle")
            page.locator('input[type="text"]').fill(f"Browser QA Admin {marker}")
            page.locator('input[type="email"]').fill(admin_email)
            page.locator('input[type="password"]').fill(admin_password)
            page.get_by_role("button", name="Create account").click()
            expect(page).to_have_url(f"{BASE_URL}/login")
            with SessionLocal() as db:
                admin = db.query(models.User).filter_by(email=admin_email).one()
                admin_id = admin.id
                assert admin.role == models.RoleEnum.admin
                assert admin.hashed_password != admin_password
                assert verify_password(admin_password, admin.hashed_password)
            checks.append("registration created an Admin with a verified password hash in MySQL")

            page.locator('input[type="email"]').fill(admin_email)
            page.locator('input[type="password"]').fill("invalid-browser-qa-password")
            with page.expect_response(lambda response: response.url.endswith("/api/auth/login") and response.status == 401):
                page.get_by_role("button", name="Sign in").click()
            expect(page.get_by_text("Invalid credentials")).to_be_visible()
            checks.append("invalid login was rejected and displayed an error")

            page.locator('input[type="email"]').fill(admin_email)
            page.locator('input[type="password"]').fill(admin_password)
            with page.expect_response(lambda response: response.url.endswith("/api/auth/login") and response.status == 200):
                page.get_by_role("button", name="Sign in").click()
            expect(page).to_have_url(f"{BASE_URL}/dashboard")
            expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
            auth = page.evaluate("""async () => {
              const token = localStorage.getItem('access_token');
              const me = await fetch('http://localhost:8000/api/auth/me', {headers:{Authorization:`Bearer ${token}`}});
              const anonymous = await fetch('http://localhost:8000/api/analytics/dashboard');
              return {meStatus:me.status, role:(await me.json()).role, anonymousStatus:anonymous.status};
            }""")
            assert auth == {"meStatus": 200, "role": "admin", "anonymousStatus": 401}, auth
            expect(page.get_by_role("link", name="Users")).to_be_visible()
            checks.append("login, authenticated navigation, Admin navigation, and anonymous API denial verified")

            page.get_by_role("link", name="Users").click()
            expect(page).to_have_url(f"{BASE_URL}/users")
            expect(page.get_by_role("heading", name="User Management")).to_be_visible()

            page.get_by_role("link", name="New Ticket").click()
            expect(page).to_have_url(f"{BASE_URL}/tickets/new")
            page.locator('input[placeholder="Brief description of the issue"]').fill(subject)
            page.locator("textarea").fill(description)
            page.get_by_role("button", name="Create Ticket").click()
            expect(page).to_have_url(__import__("re").compile(r".*/tickets/\d+$"))
            ticket_id = int(page.url.rstrip("/").split("/")[-1])
            expect(page.get_by_role("heading", name="ML Predictions")).to_be_visible()
            expect(page.get_by_text("Category is a suggestion.")).to_be_visible()
            ticket_api = page.evaluate("""async (id) => {
              const token=localStorage.getItem('access_token');
              const response=await fetch(`http://localhost:8000/api/tickets/${id}`,{headers:{Authorization:`Bearer ${token}`}});
              return {status:response.status,ticket:await response.json()};
            }""", ticket_id)
            assert ticket_api["status"] == 200
            predicted_category = ticket_api["ticket"]["predictions"]["predicted_category"]
            model_version = ticket_api["ticket"]["predictions"]["model_version"]
            assert predicted_category and model_version
            expect(page.get_by_text("Predicted category")).to_be_visible()
            expect(page.get_by_text(predicted_category, exact=True)).to_be_visible()
            expect(page.get_by_text("Priority model: unavailable")).to_be_visible()
            expect(page.get_by_text("Sentiment model: unavailable")).to_be_visible()
            expect(page.get_by_text("Urgency detection: keyword rules, not a learned probability.")).to_be_visible()
            with SessionLocal() as db:
                ticket = db.query(models.Ticket).filter_by(id=ticket_id).one()
                prediction = db.query(models.TicketPrediction).filter_by(ticket_id=ticket_id).one()
                assert ticket.created_by == admin_id
                assert prediction.predicted_category == predicted_category
                assert prediction.model_version == model_version
                assert prediction.predicted_priority is None and prediction.predicted_sentiment is None
                assert verify_password(admin_password, db.query(models.User).filter_by(id=admin_id).one().hashed_password)
            page.screenshot(path=SCREENSHOT_DIR / "ticket-details.png", full_page=True)
            checks.append(f"ticket {ticket_id} rendered category {predicted_category}; matching prediction/version persisted in MySQL")

            page.locator("select").select_option("in_progress")
            page.get_by_placeholder("Add a note about this status change").fill(f"Browser workflow {marker}")
            page.get_by_role("button", name="Save").click()
            expect(page.get_by_text(f"Browser workflow {marker}")).to_be_visible()
            with SessionLocal() as db:
                history = db.query(models.TicketStatusHistory).filter_by(ticket_id=ticket_id).all()
                assert any(row.new_status == models.TicketStatusEnum.in_progress for row in history)
                assert db.query(models.AuditLog).filter_by(ticket_id=ticket_id, action="ticket_updated").count() == 1
            checks.append("status history and audit event verified in MySQL")

            page.get_by_role("link", name="Tickets").click()
            expect(page).to_have_url(f"{BASE_URL}/tickets")
            page.locator('input[placeholder^="Search tickets"]').fill(marker)
            page.locator("select").nth(0).select_option("in_progress")
            expect(page.locator("tbody")).to_contain_text(marker)
            expect(page.locator("tbody")).to_contain_text("in progress")
            page.screenshot(path=SCREENSHOT_DIR / "ticket-list.png", full_page=True)
            checks.append("ticket list search and status filter showed the created record")

            page.get_by_role("link", name="Dashboard").click()
            expect(page.get_by_text(subject, exact=True)).to_be_visible()
            stats = page.evaluate("""async () => {
              const token=localStorage.getItem('access_token');
              const r=await fetch('http://localhost:8000/api/analytics/dashboard',{headers:{Authorization:`Bearer ${token}`}});
              return {status:r.status,data:await r.json()};
            }""")
            assert stats["status"] == 200
            assert any(item["id"] == ticket_id for item in stats["data"]["recent_tickets"])
            page.screenshot(path=SCREENSHOT_DIR / "dashboard.png", full_page=True)
            checks.append("dashboard rendered the actual MySQL-backed ticket and analytics response")

            page.get_by_role("link", name="Analytics").click()
            expect(page.get_by_text("All charts use live data from your database")).to_be_visible()
            expect(page.get_by_text("Sentiment unavailable: the selected dataset has no sentiment labels.")).to_be_visible()
            page.screenshot(path=SCREENSHOT_DIR / "analytics.png", full_page=True)
            checks.append("analytics rendered live ticket data and the valid sentiment-unavailable state")

            page.get_by_role("link", name="Reports").click()
            with page.expect_download() as download_info:
                page.get_by_role("button", name="Download CSV").click()
            download = download_info.value
            download.save_as(download_path)
            with download_path.open(encoding="utf-8-sig", newline="") as exported:
                exported_rows = list(csv.DictReader(exported))
            exported_row = next(row for row in exported_rows if row["ticket_number"] == ticket_api["ticket"]["ticket_number"])
            assert exported_row["subject"].startswith("'="), exported_row["subject"]
            checks.append("Reports page downloaded actual CSV with formula-leading subject escaped")

            # Check horizontal overflow on the principal desktop/mobile pages.
            responsive = {}
            page.set_viewport_size({"width": 390, "height": 844})
            for route in ("/dashboard", "/tickets", f"/tickets/{ticket_id}", "/analytics"):
                page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
                page.locator("main").wait_for()
                responsive[route] = page.evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth})")
            assert all(dimensions["document"] <= dimensions["viewport"] for dimensions in responsive.values()), responsive
            checks.append("dashboard, tickets, details, and analytics fit a 390px viewport without horizontal overflow")

            page.set_viewport_size({"width": 1440, "height": 1000})
            page.get_by_role("button", name="Sign out").click()
            expect(page).to_have_url(f"{BASE_URL}/login")
            assert page.evaluate("localStorage.getItem('access_token')") is None
            page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
            expect(page).to_have_url(f"{BASE_URL}/login")
            checks.append("logout removed the browser token and a protected-page visit redirected to login")

            page.get_by_role("link", name="Register").click()
            page.locator('input[type="text"]').fill(f"Browser QA Agent {marker}")
            page.locator('input[type="email"]').fill(agent_email)
            page.locator('input[type="password"]').fill(agent_password)
            page.get_by_role("button", name="Create account").click()
            expect(page).to_have_url(f"{BASE_URL}/login")
            with SessionLocal() as db:
                agent = db.query(models.User).filter_by(email=agent_email).one()
                agent_id = agent.id
                assert agent.role == models.RoleEnum.agent
                assert verify_password(agent_password, agent.hashed_password)
            page.locator('input[type="email"]').fill(agent_email)
            page.locator('input[type="password"]').fill(agent_password)
            page.get_by_role("button", name="Sign in").click()
            expect(page).to_have_url(f"{BASE_URL}/dashboard")
            expect(page.get_by_role("link", name="Users")).to_have_count(0)
            agent_permissions = page.evaluate("""async (id) => {
              const token=localStorage.getItem('access_token');
              const h={Authorization:`Bearer ${token}`};
              const [users,del,csv]=await Promise.all([
                fetch('http://localhost:8000/api/users/',{headers:h}),
                fetch(`http://localhost:8000/api/tickets/${id}`,{method:'DELETE',headers:h}),
                fetch('http://localhost:8000/api/tickets/export/csv',{headers:h})
              ]);
              return {users:users.status,delete:del.status,csv:csv.status};
            }""", ticket_id)
            assert agent_permissions == {"users": 403, "delete": 403, "csv": 200}, agent_permissions
            page.goto(f"{BASE_URL}/users", wait_until="networkidle")
            expect(page).to_have_url(f"{BASE_URL}/dashboard")
            checks.append("Support Agent role was denied admin UI/API and ticket deletion while CSV export remained allowed")
            page.get_by_role("button", name="Sign out").click()
            expect(page).to_have_url(f"{BASE_URL}/login")
            if page_errors:
                raise AssertionError(f"Browser page errors: {page_errors}")
            if server_errors:
                raise AssertionError(f"Unexpected server errors: {server_errors}")

            print({
                "result": "passed",
                "browser": f"Playwright Chromium {browser.version}",
                "checks": checks,
                "created_user_count": 2,
                "created_ticket_id": ticket_id,
                "predicted_category": predicted_category,
                "model_version": model_version,
                "responsive_dimensions": responsive,
                "screenshots": [
                    "docs/screenshots/login.png",
                    "docs/screenshots/dashboard.png",
                    "docs/screenshots/ticket-list.png",
                    "docs/screenshots/ticket-details.png",
                    "docs/screenshots/analytics.png",
                ],
            })
            context.close()
    finally:
        if download_path.exists():
            download_path.unlink()
        with SessionLocal() as db:
            # Resolve by unique generated emails as well as captured IDs so a
            # failure immediately after registration cannot strand QA accounts.
            owned_users = db.query(models.User).filter(
                models.User.email.in_([admin_email, agent_email])
            ).all()
            owned_user_ids = {user.id for user in owned_users}
            owned_user_ids.update(user_id for user_id in (admin_id, agent_id) if user_id is not None)
            owned_ticket_ids = {
                ticket.id for ticket in db.query(models.Ticket).filter(
                    models.Ticket.created_by.in_(owned_user_ids or {-1})
                ).all()
            }
            if ticket_id is not None:
                owned_ticket_ids.add(ticket_id)
            db.query(models.AuditLog).filter(
                (models.AuditLog.user_id.in_(owned_user_ids or {-1}))
                | (models.AuditLog.ticket_id.in_(owned_ticket_ids or {-1}))
            ).delete(synchronize_session=False)
            if owned_ticket_ids:
                db.query(models.TicketStatusHistory).filter(models.TicketStatusHistory.ticket_id.in_(owned_ticket_ids)).delete(synchronize_session=False)
                db.query(models.TicketPrediction).filter(models.TicketPrediction.ticket_id.in_(owned_ticket_ids)).delete(synchronize_session=False)
                db.query(models.Ticket).filter(models.Ticket.id.in_(owned_ticket_ids)).delete(synchronize_session=False)
            if owned_user_ids:
                db.query(models.User).filter(models.User.id.in_(owned_user_ids)).delete(synchronize_session=False)
            db.commit()
        with SessionLocal() as db:
            remaining_users = db.query(models.User).filter(
                models.User.email.in_([admin_email, agent_email])
            ).count()
            remaining_tickets = db.query(models.Ticket).filter(
                models.Ticket.created_by.in_([user_id for user_id in (admin_id, agent_id) if user_id is not None] or [-1])
            ).count()
            if ticket_id is not None:
                remaining_tickets += db.query(models.Ticket).filter_by(id=ticket_id).count()
        if remaining_users or remaining_tickets:
            raise RuntimeError("Browser QA cleanup did not remove its own test records.")
        print("Cleanup verified: browser QA users and ticket removed.")


if __name__ == "__main__":
    main()
