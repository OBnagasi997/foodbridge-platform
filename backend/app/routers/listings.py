import base64
import json
import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select, tuple_
from sqlalchemy.orm import joinedload

from app import audit
from app.config import get_settings
from app.deps import DB, CurrentUser, require_roles
from app.errors import DomainError
from app.metrics import LISTINGS_CREATED
from app.models import Category, Listing, User, UserRole
from app.schemas import (
    ClaimCreate,
    ClaimOut,
    ListingCreate,
    ListingOut,
    ListingPage,
    ListingUpdate,
    _check_window,
)
from app.services import claims as claim_service
from app.services import listings as listing_service

router = APIRouter(prefix="/listings", tags=["listings"])

Provider = Annotated[User, Depends(require_roles(UserRole.PROVIDER))]
Beneficiary = Annotated[User, Depends(require_roles(UserRole.BENEFICIARY))]


def _now() -> datetime:
    return datetime.now().astimezone()


def _encode_cursor(listing: Listing) -> str:
    raw = json.dumps([listing.pickup_end.isoformat(), str(listing.id)])
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        end, ident = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(end), uuid.UUID(ident)
    except (ValueError, TypeError) as exc:
        raise DomainError(400, "Curseur de pagination invalide") from exc


def _validate_horizon(pickup_end: datetime) -> None:
    now = _now()
    if pickup_end <= now:
        raise DomainError(422, "Le créneau de retrait doit se terminer dans le futur")
    if pickup_end > now + timedelta(days=get_settings().max_listing_horizon_days):
        raise DomainError(
            422,
            f"Le créneau doit se terminer dans les {get_settings().max_listing_horizon_days} jours",
        )


@router.get("", response_model=ListingPage)
def list_listings(
    db: DB,
    _user: CurrentUser,
    category: Category | None = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ListingPage:
    """Annonces réservables, les plus urgentes d'abord. Pagination par curseur (keyset) :
    stable même si des annonces apparaissent ou disparaissent pendant la lecture."""
    stmt = (
        select(Listing)
        .options(joinedload(Listing.provider))
        .where(
            Listing.deleted_at.is_(None),
            Listing.status.in_(listing_service.OPEN_STATUSES),
            Listing.pickup_end > _now(),
        )
        .order_by(Listing.pickup_end.asc(), Listing.id.asc())
        .limit(limit + 1)
    )
    if category:
        stmt = stmt.where(Listing.category == category)
    if q:
        stmt = stmt.where(Listing.title.ilike(f"%{q.strip()}%"))
    if cursor:
        end, ident = _decode_cursor(cursor)
        stmt = stmt.where(tuple_(Listing.pickup_end, Listing.id) > tuple_(end, ident))
    rows = list(db.scalars(stmt))
    page, has_more = rows[:limit], len(rows) > limit
    return ListingPage(
        items=[ListingOut.model_validate(r) for r in page],
        next_cursor=_encode_cursor(page[-1]) if has_more else None,
    )


@router.get("/mine", response_model=list[ListingOut])
def my_listings(db: DB, provider: Provider) -> list[ListingOut]:
    stmt = (
        select(Listing)
        .options(joinedload(Listing.provider))
        .where(Listing.provider_id == provider.id)
        .order_by(Listing.created_at.desc())
        .limit(100)
    )
    return [ListingOut.model_validate(r) for r in db.scalars(stmt)]


@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreate, db: DB, provider: Provider) -> ListingOut:
    _validate_horizon(payload.pickup_end)
    listing = Listing(provider_id=provider.id, **payload.model_dump())
    db.add(listing)
    db.flush()
    audit.record(
        db,
        action="listing.created",
        entity_type="listing",
        entity_id=listing.id,
        actor_id=provider.id,
    )
    db.commit()
    LISTINGS_CREATED.labels(category=listing.category.value).inc()
    return ListingOut.model_validate(listing)


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: uuid.UUID, db: DB, _user: CurrentUser) -> ListingOut:
    listing = db.scalar(
        select(Listing).options(joinedload(Listing.provider)).where(Listing.id == listing_id)
    )
    if listing is None or listing.deleted_at is not None:
        raise DomainError(404, "Annonce introuvable")
    return ListingOut.model_validate(listing)


@router.patch("/{listing_id}", response_model=ListingOut)
def update_listing(listing_id: uuid.UUID, payload: ListingUpdate, db: DB, provider: Provider):
    listing = listing_service.lock_listing(db, listing_id)
    if listing.provider_id != provider.id:
        raise DomainError(404, "Annonce introuvable")
    if listing.status not in listing_service.OPEN_STATUSES:
        raise DomainError(409, "Cette annonce n'est plus modifiable")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None and field not in ("description",):
            raise DomainError(422, f"Le champ {field} ne peut pas être vide")
        setattr(listing, field, value)

    try:
        _check_window(
            listing.pickup_start, listing.pickup_end, listing.expiry_at, listing.date_type
        )
    except ValueError as exc:
        raise DomainError(422, str(exc)) from exc
    if "pickup_end" in changes:
        _validate_horizon(listing.pickup_end)
    if listing.quantity < listing.quantity_claimed:
        reserved = listing.quantity_claimed.normalize()
        raise DomainError(409, f"{reserved:f} déjà réservés : quantité minimale atteinte")

    listing_service.refresh_status(listing)
    audit.record(
        db,
        action="listing.updated",
        entity_type="listing",
        entity_id=listing.id,
        actor_id=provider.id,
        fields=sorted(changes),
    )
    db.commit()
    db.refresh(listing)
    return ListingOut.model_validate(listing)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: uuid.UUID, db: DB, provider: Provider) -> Response:
    claim_service.cancel_listing(db, listing_id, provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{listing_id}/claim", response_model=ClaimOut, status_code=status.HTTP_201_CREATED)
def claim(listing_id: uuid.UUID, payload: ClaimCreate, db: DB, user: Beneficiary) -> ClaimOut:
    created = claim_service.claim_listing(db, listing_id, user, payload.quantity, payload.notes)
    out = ClaimOut.model_validate(created)
    return out.model_copy(
        update={
            "pickup_code": created.pickup_code,
            "contact_phone": created.listing.provider.phone,
        }
    )
