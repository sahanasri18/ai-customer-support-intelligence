"""Users router: list, update, deactivate users (admin only)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
from schemas import UserResponse, UserUpdate, PasswordChange, RoleEnum
from auth import get_current_user, require_admin, hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    return db.query(models.User).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.RoleEnum.admin and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.id == user_id and (
        payload.is_active is False or payload.role == RoleEnum.agent
    ):
        raise HTTPException(status_code=400, detail="You cannot disable or demote your own account")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(user, field, val)
    db.add(models.AuditLog(
        user_id=current_user.id,
        action="user_updated",
        details=f"target_user_id={user.id}",
    ))
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/change-password")
def change_password(payload: PasswordChange, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.add(models.AuditLog(user_id=current_user.id, action="password_changed"))
    db.commit()
    return {"message": "Password changed successfully"}
