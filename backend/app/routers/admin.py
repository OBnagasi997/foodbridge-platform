import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app import audit
from app.deps import DB, require_roles
from app.errors import DomainError
from app.models import User, UserRole
from app.schemas import AdminUserOut, VerifyIn

router = APIRouter(prefix="/admin", tags=["admin"])
Admin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: DB,
    _admin: Admin,
    role: UserRole | None = None,
    verified: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    if role:
        stmt = stmt.where(User.role == role)
    if verified is not None:
        stmt = stmt.where(User.is_verified == verified)
    return list(db.scalars(stmt))


@router.patch("/users/{user_id}/verify", response_model=AdminUserOut)
def verify_user(user_id: uuid.UUID, payload: VerifyIn, db: DB, admin: Admin) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise DomainError(404, "Utilisateur introuvable")
    user.is_verified = payload.is_verified
    audit.record(
        db,
        action="user.verification_changed",
        entity_type="user",
        entity_id=user.id,
        actor_id=admin.id,
        is_verified=payload.is_verified,
    )
    db.commit()
    return user
