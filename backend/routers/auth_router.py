"""Auth router: register, login, logout."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas import UserRegister, Token, UserResponse
from auth import hash_password, verify_password, create_access_token, get_current_user
from datetime import timedelta
from config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Public registration never grants administrator privileges by default.
    # Local QA may explicitly opt in for an isolated empty test database.
    is_first = settings.ALLOW_FIRST_USER_ADMIN and db.query(models.User).count() == 0
    user = models.User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=models.RoleEnum.admin if is_first else models.RoleEnum.agent,
    )
    db.add(user)
    db.flush()
    db.add(models.AuditLog(user_id=user.id, action="user_registered"))
    db.commit()
    db.refresh(user)
    logger.info("New user registered (role=%s)", user.role.value)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if len(form_data.username) > 255 or len(form_data.password) > 128:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    db.add(models.AuditLog(user_id=user.id, action="user_login"))
    db.commit()

    token = create_access_token(
        {"sub": str(user.id), "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return Token(
        access_token=token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Access tokens are stateless; the client ends its session by discarding the token.
    db.add(models.AuditLog(user_id=current_user.id, action="user_logout"))
    db.commit()
    return {"message": "Logged out. Discard the access token on the client."}
