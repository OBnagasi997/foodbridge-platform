import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.deps import DB, require_roles
from app.models import Claim, ClaimStatus, Listing, User, UserRole
from app.ratelimit import pickup_rate_limit
from app.schemas import ClaimOut, PickupIn
from app.services import claims as claim_service

router = APIRouter(prefix="/claims", tags=["claims"])

Provider = Annotated[User, Depends(require_roles(UserRole.PROVIDER))]
Beneficiary = Annotated[User, Depends(require_roles(UserRole.BENEFICIARY))]
Actor = Annotated[
    User, Depends(require_roles(UserRole.BENEFICIARY, UserRole.PROVIDER, UserRole.ADMIN))
]


def _for_beneficiary(claim: Claim) -> ClaimOut:
    """Le code de retrait n'est révélé qu'au bénéficiaire, et seulement tant qu'il sert."""
    out = ClaimOut.model_validate(claim)
    active = claim.status == ClaimStatus.CONFIRMED
    return out.model_copy(
        update={
            "pickup_code": claim.pickup_code if active else None,
            "contact_phone": claim.listing.provider.phone if active else None,
        }
    )


def _for_provider(claim: Claim) -> ClaimOut:
    phone = claim.beneficiary.phone if claim.status == ClaimStatus.CONFIRMED else None
    return ClaimOut.model_validate(claim).model_copy(
        update={"pickup_code": None, "contact_phone": phone}
    )


def _loaded(stmt):
    return stmt.options(
        joinedload(Claim.listing).joinedload(Listing.provider), joinedload(Claim.beneficiary)
    )


@router.get("/me", response_model=list[ClaimOut])
def my_claims(db: DB, user: Beneficiary) -> list[ClaimOut]:
    stmt = _loaded(select(Claim)).where(Claim.beneficiary_id == user.id)
    rows = db.scalars(stmt.order_by(Claim.claimed_at.desc()).limit(100))
    return [_for_beneficiary(c) for c in rows]


@router.get("/received", response_model=list[ClaimOut])
def received_claims(
    db: DB,
    provider: Provider,
    status: ClaimStatus | None = None,
    listing_id: uuid.UUID | None = None,
) -> list[ClaimOut]:
    stmt = _loaded(select(Claim)).join(Listing, Claim.listing_id == Listing.id)
    stmt = stmt.where(Listing.provider_id == provider.id)
    if status:
        stmt = stmt.where(Claim.status == status)
    if listing_id:
        stmt = stmt.where(Claim.listing_id == listing_id)
    rows = db.scalars(stmt.order_by(Claim.claimed_at.desc()).limit(200).execution_options())
    return [_for_provider(c) for c in rows.unique()]


@router.post(
    "/{claim_id}/pickup", response_model=ClaimOut, dependencies=[Depends(pickup_rate_limit)]
)
def pickup(claim_id: uuid.UUID, payload: PickupIn, db: DB, provider: Provider) -> ClaimOut:
    return _for_provider(claim_service.pickup_claim(db, claim_id, provider, payload.code))


@router.post("/{claim_id}/cancel", response_model=ClaimOut)
def cancel(claim_id: uuid.UUID, db: DB, actor: Actor) -> ClaimOut:
    claim = claim_service.cancel_claim(db, claim_id, actor)
    return _for_beneficiary(claim) if claim.beneficiary_id == actor.id else _for_provider(claim)


@router.post("/{claim_id}/no-show", response_model=ClaimOut)
def no_show(claim_id: uuid.UUID, db: DB, provider: Provider) -> ClaimOut:
    return _for_provider(claim_service.mark_no_show(db, claim_id, provider))
