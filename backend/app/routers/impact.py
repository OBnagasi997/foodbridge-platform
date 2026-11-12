from fastapi import APIRouter
from sqlalchemy import func, select

from app.deps import DB, CurrentUser
from app.models import Claim, ImpactEvent, Listing, UserRole
from app.schemas import ImpactSummary

router = APIRouter(prefix="/impact", tags=["impact"])


def _summary(db, listings_filter=None, events_filter=None, join_claims=False) -> ImpactSummary:
    stmt = select(
        func.coalesce(func.sum(ImpactEvent.kg_rescued), 0),
        func.coalesce(func.sum(ImpactEvent.meals_estimated), 0),
        func.coalesce(func.sum(ImpactEvent.co2e_avoided_kg), 0),
        func.count(ImpactEvent.id),
    )
    if join_claims:
        stmt = stmt.join(Claim, Claim.id == ImpactEvent.claim_id)
    if events_filter is not None:
        stmt = stmt.where(events_filter)
    kg, meals, co2, pickups = db.execute(stmt).one()

    listings_stmt = select(func.count(Listing.id)).where(Listing.deleted_at.is_(None))
    if listings_filter is not None:
        listings_stmt = listings_stmt.where(listings_filter)
    return ImpactSummary(
        kg_rescued=float(kg),
        meals_estimated=float(meals),
        co2e_avoided_kg=float(co2),
        listings_published=db.scalar(listings_stmt) or 0,
        pickups_completed=pickups,
    )


@router.get("/summary", response_model=ImpactSummary)
def summary(db: DB) -> ImpactSummary:
    """Chiffres publics, calculés uniquement à partir des retraits confirmés (impact_events)."""
    return _summary(db)


@router.get("/me", response_model=ImpactSummary)
def my_impact(db: DB, user: CurrentUser) -> ImpactSummary:
    """Impact personnel : dons effectués (commerçant) ou denrées récupérées (bénéficiaire)."""
    if user.role == UserRole.PROVIDER:
        return _summary(
            db,
            listings_filter=Listing.provider_id == user.id,
            events_filter=ImpactEvent.provider_id == user.id,
        )
    if user.role == UserRole.BENEFICIARY:
        return _summary(
            db,
            listings_filter=Listing.id.is_(None),
            events_filter=Claim.beneficiary_id == user.id,
            join_claims=True,
        )
    return _summary(db)
