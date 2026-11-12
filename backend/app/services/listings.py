from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Listing, ListingStatus

OPEN_STATUSES = (ListingStatus.AVAILABLE, ListingStatus.PARTIALLY_CLAIMED)


def lock_listing(db: Session, listing_id) -> Listing:
    """Verrou d'écriture sur la ligne : sérialise toutes les modifications concurrentes du stock.

    Pas de joinedload ici : PostgreSQL refuse FOR UPDATE sur le côté nullable
    d'une jointure externe.
    """
    listing = db.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if listing is None or listing.deleted_at is not None:
        raise DomainError(404, "Annonce introuvable")
    return listing


def refresh_status(listing: Listing) -> None:
    """Recalcule le statut à partir du stock réservé. Ne ressuscite jamais une annonce close."""
    if listing.status in (ListingStatus.EXPIRED, ListingStatus.CANCELLED):
        return
    if listing.quantity_claimed <= 0:
        listing.status = ListingStatus.AVAILABLE
    elif listing.quantity_claimed >= listing.quantity:
        listing.status = ListingStatus.FULLY_CLAIMED
    else:
        listing.status = ListingStatus.PARTIALLY_CLAIMED


def expire_listings(db: Session, now: datetime) -> int:
    """Passe en `expired` les annonces ouvertes dont le créneau est terminé.

    Les annonces entièrement réservées restent `fully_claimed` : le don est conclu.
    Idempotent : peut être lancé aussi souvent qu'on veut (CronJob Kubernetes, projet 3).
    """
    result = db.execute(
        update(Listing)
        .where(
            Listing.status.in_(OPEN_STATUSES),
            Listing.pickup_end <= now,
            Listing.deleted_at.is_(None),
        )
        .values(status=ListingStatus.EXPIRED)
    )
    db.commit()
    return result.rowcount
