from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.cli import create_admin
from app.jobs.expire_listings import run as run_expiry
from app.models import (
    Category,
    DateType,
    Listing,
    ListingStatus,
    StorageCondition,
    Unit,
    User,
    UserRole,
)
from tests.helpers import listing_payload


@pytest.fixture
def admin(client, db):
    create_admin(db, "root@example.org", "correct-horse-battery")
    r = client.post(
        "/api/auth/login", json={"email": "root@example.org", "password": "correct-horse-battery"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_admin_rules(db):
    user = create_admin(db, "Boss@Example.org", "correct-horse-battery")
    assert user.role == UserRole.ADMIN and user.is_verified and user.email == "boss@example.org"
    with pytest.raises(ValueError, match="existe déjà"):
        create_admin(db, "boss@example.org", "correct-horse-battery")
    with pytest.raises(ValueError, match="10 caractères"):
        create_admin(db, "x@example.org", "court")


def test_admin_verifies_organizations(client, actor, admin):
    b = actor("beneficiary", "asso@example.org")
    p = actor("provider", "shop@example.org")

    assert client.get("/api/admin/users", headers=b.h).status_code == 403
    assert client.get("/api/admin/users", headers=p.h).status_code == 403

    pending = client.get("/api/admin/users?role=beneficiary&verified=false", headers=admin).json()
    assert [u["email"] for u in pending] == ["asso@example.org"]

    r = client.patch(f"/api/admin/users/{b.id}/verify", json={"is_verified": True}, headers=admin)
    assert r.status_code == 200 and r.json()["is_verified"] is True

    lid = client.post("/api/listings", json=listing_payload(), headers=p.h).json()["id"]
    client.post(f"/api/listings/{lid}/claim", json={"quantity": "1"}, headers=b.h)
    received = client.get("/api/claims/received", headers=p.h).json()[0]
    assert received["beneficiary_verified"] is True  # le commerçant voit le badge

    unknown = "00000000-0000-0000-0000-000000000000"
    assert (
        client.patch(
            f"/api/admin/users/{unknown}/verify", json={"is_verified": True}, headers=admin
        ).status_code
        == 404
    )


def _db_listing(db, provider_id, end_delta_hours, status=ListingStatus.AVAILABLE, title="Lot"):
    now = datetime.now().astimezone()
    listing = Listing(
        provider_id=provider_id,
        title=title,
        category=Category.AUTRE,
        quantity=Decimal("5"),
        unit=Unit.KG,
        date_type=DateType.DDM,
        storage_condition=StorageCondition.AMBIENT,
        allergens=[],
        pickup_start=now + timedelta(hours=end_delta_hours - 2),
        pickup_end=now + timedelta(hours=end_delta_hours),
        expiry_at=now + timedelta(days=3),
        location_text="Rue test",
        status=status,
    )
    db.add(listing)
    return listing


def test_expiry_job_is_correct_and_idempotent(db):
    provider = User(
        email="p@example.org", hashed_password="x", full_name="P", role=UserRole.PROVIDER
    )
    db.add(provider)
    db.flush()
    stale = _db_listing(db, provider.id, -1, title="Périmée")
    stale_partial = _db_listing(db, provider.id, -2, ListingStatus.PARTIALLY_CLAIMED, "Partielle")
    sold = _db_listing(db, provider.id, -1, ListingStatus.FULLY_CLAIMED, "Conclue")
    fresh = _db_listing(db, provider.id, 3, title="Fraîche")
    db.commit()
    ids = {
        k: v.id for k, v in dict(stale=stale, partial=stale_partial, sold=sold, fresh=fresh).items()
    }

    assert run_expiry() == 2
    assert run_expiry() == 0  # idempotent

    db.expire_all()
    status = {k: db.get(Listing, i).status for k, i in ids.items()}
    assert status == {
        "stale": ListingStatus.EXPIRED,
        "partial": ListingStatus.EXPIRED,
        "sold": ListingStatus.FULLY_CLAIMED,  # un don conclu reste conclu
        "fresh": ListingStatus.AVAILABLE,
    }
