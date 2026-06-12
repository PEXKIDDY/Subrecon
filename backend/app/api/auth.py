"""Authentication & user management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import AuditLog, User, UserRole
from app.schemas import Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _audit(db: Session, user_id: int | None, action: str, detail: str, request: Request) -> None:
    db.add(AuditLog(
        user_id=user_id, action=action, detail=detail,
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter((User.email == payload.email) | (User.username == payload.username)).first():
        raise HTTPException(status_code=409, detail="Email or username already registered")
    # First user becomes admin automatically.
    role = UserRole.ADMIN if db.query(User).count() == 0 else payload.role
    user = User(
        email=payload.email, username=payload.username,
        hashed_password=hash_password(payload.password), role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _audit(db, user.id, "user.register", f"username={user.username}", request)
    return user


@router.post("/login", response_model=Token)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == form.username) | (User.email == form.username)).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token(user.id, user.role.value)
    _audit(db, user.id, "user.login", f"username={user.username}", request)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.ADMIN))):
    return db.query(User).order_by(User.id).all()
