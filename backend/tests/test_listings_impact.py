from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Category,
    DateType,
    Listing,
    ListingStatus,
    StorageCondition,
    Unit,
    User,
)


def _listing(provider_id, **over):
    from datetime import datetime

    now = datetime.now().astimezone()
    data = dict(
        provider_id=provider_id,
        title="Invendus du soir",
        category=Category.BOULANGERIE,
        quantity=Decimal("10"),
        unit=Unit.KG,
        date_type=DateType.DLC,
        storage_condition=StorageCondition.AMBIENT,
        allergens=["gluten"],
        pickup_start=now + timedelta(hours=1),
        pickup_end=now + timedelta(hours=3),
        expiry_at=now + timedelta(hours=6),
        location_text="12 rue Test",
    )
    data.update(over)
    return Listing(**data)


def test_listings_requires_auth(client):
    assert client.get("/api/listings").status_code == 401


def test_listings_empty_then_returns_open_only(client, auth_headers, db):
    headers = auth_headers("beneficiary")
    assert client.get("/api/listings", headers=headers).json() == {"items": [], "next_cursor": None}

    provider = User(
        email="p@example.org",
        hashed_password="x",
        full_name="P",
        role="provider",
        organization_name="Maison Test",
    )
    db.add(provider)
    db.flush()
    db.add_all(
        [
            _listing(provider.id, title="ouverte"),
            _listing(provider.id, title="annulée", status=ListingStatus.CANCELLED),
        ]
    )
    db.commit()

    items = client.get("/api/listings", headers=headers).json()["items"]
    assert [i["title"] for i in items] == ["ouverte"]
    assert items[0]["provider_name"] == "Maison Test"
    assert Decimal(items[0]["quantity_remaining"]) == Decimal("10")


def test_db_rejects_overclaimed_listing(db):
    provider = User(email="p2@example.org", hashed_password="x", full_name="P", role="provider")
    db.add(provider)
    db.flush()
    db.add(_listing(provider.id, quantity_claimed=Decimal("11")))
    with pytest.raises(IntegrityError):
        db.commit()


def test_db_rejects_invalid_pickup_window(db):
    provider = User(email="p3@example.org", hashed_password="x", full_name="P", role="provider")
    db.add(provider)
    db.flush()
    now = _listing(provider.id).pickup_start
    db.add(_listing(provider.id, pickup_start=now, pickup_end=now - timedelta(minutes=1)))
    with pytest.raises(IntegrityError):
        db.commit()


def test_impact_summary_public_and_zero_at_start(client):
    r = client.get("/api/impact/summary")
    assert r.status_code == 200
    assert r.json() == {
        "kg_rescued": 0,
        "meals_estimated": 0,
        "co2e_avoided_kg": 0,
        "listings_published": 0,
        "pickups_completed": 0,
    }
