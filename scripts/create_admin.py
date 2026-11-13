"""Create the first local administrator without exposing a password in argv."""
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import models  # noqa: E402
from auth import hash_password  # noqa: E402
from database import SessionLocal  # noqa: E402
from schemas import UserRegister  # noqa: E402


def main() -> None:
    email = input("Admin email: ").strip()
    full_name = input("Admin full name: ").strip()
    password = getpass.getpass("Admin password (12+ characters): ")
    confirmation = getpass.getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords did not match.")

    try:
        account = UserRegister(email=email, full_name=full_name, password=password)
    except Exception:
        # Validation exceptions may include rejected field values; never display them.
        raise SystemExit("Admin details are invalid. Check the email, name, and 12+ character password requirements.") from None

    with SessionLocal() as db:
        if db.query(models.User).filter(models.User.role == models.RoleEnum.admin).count():
            raise SystemExit("An administrator already exists; refusing to create another through bootstrap.")
        if db.query(models.User).filter(models.User.email == account.email).first():
            raise SystemExit("That email is already registered.")
        user = models.User(
            email=account.email,
            full_name=account.full_name,
            hashed_password=hash_password(account.password),
            role=models.RoleEnum.admin,
        )
        db.add(user)
        db.flush()
        db.add(models.AuditLog(user_id=user.id, action="admin_bootstrapped"))
        db.commit()
    print("Administrator created. Sign in through the application.")


if __name__ == "__main__":
    main()
