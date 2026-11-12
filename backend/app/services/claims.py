import secrets
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import audit
from app.config import get_settings
from app.errors import DomainError
from app.metrics import CLAIMS, KG_RESCUED
from app.models import (
    Claim,
    ClaimStatus,
    ImpactEvent,
    ImpactFactor,
    ListingStatus,
    Unit,
    User,
    UserRole,
)
from app.services.listings import OPEN_STATUSES, lock_listing, refresh_status

UNIT_FACTOR_KEY = {
    Unit.PIECES: "kg_per_piece",
    Unit.PORTIONS: "kg_per_portion",
    Unit.BARQUETTES: "kg_per_barquette",
    Unit.LITRES: "kg_per_litre",
}


def _now() -> datetime:
    return datetime.now().astimezone()


def _new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _lock_claim(db: Session, claim_id) -> Claim:
    claim = db.scalar(
        select(Claim)
        .where(Claim.id == claim_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if claim is None:
        raise DomainError(404, "Réservation introuvable")
    return claim


def _lock_listing_then_claim(db: Session, claim_id) -> Claim:
    """Ordre de verrouillage unique pour éviter les interblocages : annonce, puis réservation."""
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise DomainError(404, "Réservation introuvable")
    lock_listing(db, claim.listing_id)
    return _lock_claim(db, claim_id)


def claim_listing(
    db: Session, listing_id, user: User, quantity: Decimal, notes: str | None
) -> Claim:
    """Réserve `quantity` sur une annonce. Ordre des verrous : bénéficiaire, puis annonce."""
    if user.role != UserRole.BENEFICIARY:
        raise DomainError(403, "Seuls les bénéficiaires peuvent réserver")
    s = get_settings()

    # Verrou sur le bénéficiaire : ses réservations simultanées sont traitées l'une après l'autre,
    # ce qui rend fiables la limite de réservations actives et l'anti-doublon.
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    db.refresh(user)

    if s.require_verified_claimants and not user.is_verified:
        raise DomainError(403, "Ton organisation doit être vérifiée avant de pouvoir réserver")
    if user.no_show_count >= s.max_no_shows:
        raise DomainError(403, "Réservations suspendues : trop de retraits non honorés")

    listing = lock_listing(db, listing_id)
    if listing.status not in OPEN_STATUSES or listing.pickup_end <= _now():
        raise DomainError(409, "Cette annonce n'est plus disponible")
    if quantity > listing.quantity_remaining:
        raise DomainError(
            409, f"Il ne reste que {listing.quantity_remaining.normalize():f} disponible"
        )

    active = db.scalar(
        select(func.count(Claim.id)).where(
            Claim.beneficiary_id == user.id, Claim.status == ClaimStatus.CONFIRMED
        )
    )
    if active >= s.max_active_claims:
        raise DomainError(409, f"Limite de {s.max_active_claims} réservations en cours atteinte")
    already = db.scalar(
        select(func.count(Claim.id)).where(
            Claim.listing_id == listing.id,
            Claim.beneficiary_id == user.id,
            Claim.status == ClaimStatus.CONFIRMED,
        )
    )
    if already:
        raise DomainError(409, "Tu as déjà une réservation en cours sur cette annonce")

    claim = Claim(
        listing_id=listing.id,
        beneficiary_id=user.id,
        quantity_claimed=quantity,
        status=ClaimStatus.CONFIRMED,
        pickup_code=_new_code(),
        notes=notes,
    )
    db.add(claim)
    listing.quantity_claimed += quantity
    refresh_status(listing)
    db.flush()
    audit.record(
        db,
        action="claim.created",
        entity_type="claim",
        entity_id=claim.id,
        actor_id=user.id,
        listing_id=str(listing.id),
        quantity=str(quantity),
    )
    db.commit()
    CLAIMS.labels(status="confirmed").inc()
    return claim


def cancel_claim(db: Session, claim_id, actor: User) -> Claim:
    claim = _lock_listing_then_claim(db, claim_id)
    listing = claim.listing
    is_beneficiary = claim.beneficiary_id == actor.id
    is_provider = listing.provider_id == actor.id
    if not (is_beneficiary or is_provider or actor.role == UserRole.ADMIN):
        raise DomainError(404, "Réservation introuvable")
    if claim.status != ClaimStatus.CONFIRMED:
        raise DomainError(409, "Seule une réservation en cours peut être annulée")

    claim.status = ClaimStatus.CANCELLED
    listing.quantity_claimed -= claim.quantity_claimed
    refresh_status(listing)
    audit.record(
        db, action="claim.cancelled", entity_type="claim", entity_id=claim.id, actor_id=actor.id
    )
    db.commit()
    CLAIMS.labels(status="cancelled").inc()
    return claim


def _kg_for(quantity: Decimal, unit: Unit, factors: dict[str, Decimal]) -> Decimal:
    if unit == Unit.KG:
        return quantity
    return quantity * factors[UNIT_FACTOR_KEY[unit]]


def pickup_claim(db: Session, claim_id, provider: User, code: str) -> Claim:
    """Valide le retrait avec le code. C'est ici, et seulement ici, que l'impact est créé."""
    claim = _lock_listing_then_claim(db, claim_id)
    listing = claim.listing
    if listing.provider_id != provider.id:
        raise DomainError(404, "Réservation introuvable")
    if claim.status != ClaimStatus.CONFIRMED:
        raise DomainError(409, "Cette réservation n'est plus en attente de retrait")
    if not secrets.compare_digest(code, claim.pickup_code):
        raise DomainError(400, "Code incorrect")

    factors = {f.key: f.value for f in db.scalars(select(ImpactFactor))}
    kg = _kg_for(claim.quantity_claimed, listing.unit, factors)
    meals = kg / factors["kg_per_meal"]
    co2e = kg * factors["co2e_kg_per_kg_food"]

    claim.status = ClaimStatus.PICKED_UP
    claim.picked_up_at = _now()
    db.add(
        ImpactEvent(
            claim_id=claim.id,
            provider_id=provider.id,
            kg_rescued=kg.quantize(Decimal("0.001"), ROUND_HALF_UP),
            meals_estimated=meals.quantize(Decimal("0.1"), ROUND_HALF_UP),
            co2e_avoided_kg=co2e.quantize(Decimal("0.01"), ROUND_HALF_UP),
        )
    )
    audit.record(
        db,
        action="claim.picked_up",
        entity_type="claim",
        entity_id=claim.id,
        actor_id=provider.id,
        kg=str(kg),
    )
    db.commit()
    CLAIMS.labels(status="picked_up").inc()
    KG_RESCUED.inc(float(kg))
    return claim


def mark_no_show(db: Session, claim_id, provider: User) -> Claim:
    claim = _lock_listing_then_claim(db, claim_id)
    listing = claim.listing
    if listing.provider_id != provider.id:
        raise DomainError(404, "Réservation introuvable")
    if claim.status != ClaimStatus.CONFIRMED:
        raise DomainError(409, "Cette réservation n'est plus en attente de retrait")
    if listing.pickup_end > _now():
        raise DomainError(409, "Le créneau de retrait n'est pas encore terminé")

    claim.status = ClaimStatus.NO_SHOW
    db.execute(
        update(User)
        .where(User.id == claim.beneficiary_id)
        .values(no_show_count=User.no_show_count + 1)
    )
    audit.record(
        db, action="claim.no_show", entity_type="claim", entity_id=claim.id, actor_id=provider.id
    )
    db.commit()
    CLAIMS.labels(status="no_show").inc()
    return claim


def cancel_listing(db: Session, listing_id, provider: User) -> None:
    """Retire une annonce (suppression logique) et annule les réservations encore en cours."""
    listing = lock_listing(db, listing_id)
    if listing.provider_id != provider.id and provider.role != UserRole.ADMIN:
        raise DomainError(404, "Annonce introuvable")
    active = db.scalars(
        select(Claim)
        .where(Claim.listing_id == listing.id, Claim.status == ClaimStatus.CONFIRMED)
        .with_for_update()
    ).all()
    for claim in active:
        claim.status = ClaimStatus.CANCELLED
        CLAIMS.labels(status="cancelled").inc()
    listing.quantity_claimed = sum(
        (
            c.quantity_claimed
            for c in db.scalars(
                select(Claim).where(
                    Claim.listing_id == listing.id, Claim.status == ClaimStatus.PICKED_UP
                )
            )
        ),
        Decimal("0"),
    )
    listing.status = ListingStatus.CANCELLED
    listing.deleted_at = _now()
    audit.record(
        db,
        action="listing.cancelled",
        entity_type="listing",
        entity_id=listing.id,
        actor_id=provider.id,
        claims_cancelled=len(active),
    )
    db.commit()
