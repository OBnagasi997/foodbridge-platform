"""Tests de concurrence : le coeur de la V1.

Chaque thread utilise sa propre session/connexion, comme des requêtes simultanées réelles.
Une barrière aligne les départs pour maximiser les collisions.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.database import SessionLocal
from app.errors import DomainError
from app.models import (
    Category,
    Claim,
    ClaimStatus,
    DateType,
    Listing,
    ListingStatus,
    StorageCondition,
    Unit,
    User,
    UserRole,
)
from app.services.claims import claim_listing


def _provider(db) -> User:
    p = User(email="prov@example.org", hashed_password="x", full_name="P", role=UserRole.PROVIDER)
    db.add(p)
    db.flush()
    return p


def _listing(db, provider, quantity="5", title="Lot") -> Listing:
    now = datetime.now().astimezone()
    listing = Listing(
        provider_id=provider.id,
        title=title,
        category=Category.BOULANGERIE,
        quantity=Decimal(quantity),
        unit=Unit.KG,
        date_type=DateType.DLC,
        storage_condition=StorageCondition.AMBIENT,
        allergens=[],
        pickup_start=now,
        pickup_end=now + timedelta(hours=2),
        expiry_at=now + timedelta(hours=5),
        location_text="Rue test",
    )
    db.add(listing)
    db.flush()
    return listing


def _beneficiaries(db, n) -> list:
    users = [
        User(
            email=f"b{i}@example.org",
            hashed_password="x",
            full_name=f"B{i}",
            role=UserRole.BENEFICIARY,
        )
        for i in range(n)
    ]
    db.add_all(users)
    db.flush()
    return [u.id for u in users]


def _run_parallel(jobs):
    barrier = threading.Barrier(len(jobs))

    def wrap(job):
        barrier.wait()
        try:
            job()
            return "ok"
        except DomainError as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return list(pool.map(wrap, jobs))


def _claim_job(user_id, listing_id, qty="1"):
    def job():
        with SessionLocal() as db:
            user = db.get(User, user_id)
            claim_listing(db, listing_id, user, Decimal(qty), None)

    return job


def test_no_overbooking_under_concurrency():
    """15 bénéficiaires se disputent 5 unités : exactement 5 réussissent, jamais plus."""
    with SessionLocal() as db:
        listing = _listing(db, _provider(db), quantity="5")
        user_ids = _beneficiaries(db, 15)
        listing_id = listing.id
        db.commit()

    results = _run_parallel([_claim_job(uid, listing_id) for uid in user_ids])

    assert results.count("ok") == 5
    assert results.count(409) == 10
    with SessionLocal() as db:
        listing = db.get(Listing, listing_id)
        assert listing.quantity_claimed == Decimal("5")
        assert listing.status == ListingStatus.FULLY_CLAIMED
        confirmed = db.scalar(
            select(func.count(Claim.id)).where(
                Claim.listing_id == listing_id, Claim.status == ClaimStatus.CONFIRMED
            )
        )
        assert confirmed == 5


def test_same_beneficiary_double_click_creates_one_claim():
    """Deux clics simultanés du même bénéficiaire sur la même annonce : une seule réservation."""
    with SessionLocal() as db:
        listing = _listing(db, _provider(db), quantity="10")
        (uid,) = _beneficiaries(db, 1)
        listing_id = listing.id
        db.commit()

    results = _run_parallel([_claim_job(uid, listing_id, "2") for _ in range(2)])

    assert sorted(map(str, results)) == ["409", "ok"]
    with SessionLocal() as db:
        assert db.get(Listing, listing_id).quantity_claimed == Decimal("2")


def test_active_claims_limit_holds_across_listings(settings_env):
    """6 annonces différentes, même bénéficiaire, limite de 3 : jamais plus de 3 réservations."""
    settings_env(MAX_ACTIVE_CLAIMS=3)
    with SessionLocal() as db:
        provider = _provider(db)
        listing_ids = [_listing(db, provider, title=f"Lot {i}").id for i in range(6)]
        (uid,) = _beneficiaries(db, 1)
        db.commit()

    results = _run_parallel([_claim_job(uid, lid) for lid in listing_ids])

    assert results.count("ok") == 3
    with SessionLocal() as db:
        active = db.scalar(
            select(func.count(Claim.id)).where(
                Claim.beneficiary_id == uid, Claim.status == ClaimStatus.CONFIRMED
            )
        )
        assert active == 3
