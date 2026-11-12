from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import audit
from app.deps import DB, CurrentUser
from app.metrics import USERS_REGISTERED
from app.models import User, UserRole
from app.ratelimit import auth_rate_limit
from app.schemas import LoginIn, ProfileUpdate, RefreshIn, RegisterIn, TokenOut, UserOut
from app.security import create_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user: User) -> TokenOut:
    access, expires_in = create_token(user.id, "access")
    refresh, _ = create_token(user.id, "refresh")
    return TokenOut(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
def register(payload: RegisterIn, db: DB) -> User:
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole(payload.role),
        organization_name=payload.organization_name,
        phone=payload.phone,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # email déjà pris (y compris en cas de course)
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet email"
        ) from exc
    audit.record(
        db,
        action="user.registered",
        entity_type="user",
        entity_id=user.id,
        actor_id=user.id,
        role=user.role.value,
    )
    db.commit()
    USERS_REGISTERED.labels(role=user.role.value).inc()
    return user


@router.post("/login", response_model=TokenOut, dependencies=[Depends(auth_rate_limit)])
def login(payload: LoginIn, db: DB) -> TokenOut:
    user = db.scalar(select(User).where(User.email == payload.email))
    ok = verify_password(payload.password, user.hashed_password if user else None)
    if not ok or user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect")
    return _tokens(user)


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(auth_rate_limit)])
def refresh(payload: RefreshIn, db: DB) -> TokenOut:
    user_id = decode_token(payload.refresh_token, "refresh")
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expirée")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileUpdate, db: DB, user: CurrentUser) -> User:
    """Complète le profil (ex. compte créé avant l'ajout du téléphone obligatoire)."""
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(user, field, value)
    audit.record(
        db,
        action="user.profile_updated",
        entity_type="user",
        entity_id=user.id,
        actor_id=user.id,
        fields=sorted(changes),
    )
    db.commit()
    return user
