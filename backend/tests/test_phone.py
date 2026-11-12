import pytest

from app.models import User, UserRole
from app.security import hash_password
from tests.helpers import listing_payload

PROVIDER_PHONE = "+33611111111"
BENEFICIARY_PHONE = "+33622222222"


def _register(client, phone, **over):
    body = {
        "email": "n@example.org",
        "password": "correct-horse-battery",
        "full_name": "Nom Test",
        "role": "beneficiary",
        "phone": phone,
    }
    body.update(over)
    return client.post("/api/auth/register", json=body)


def test_national_number_is_normalized_to_e164(client):
    r = _register(client, "06 12 34 56 78")
    assert r.status_code == 201 and r.json()["phone"] == "+33612345678"


def test_international_number_is_accepted(client):
    r = _register(client, "+221 77 123 45 67")
    assert r.status_code == 201 and r.json()["phone"] == "+221771234567"


def test_default_region_is_configurable(client, settings_env):
    settings_env(DEFAULT_PHONE_REGION="SN")
    r = _register(client, "77 123 45 67")
    assert r.status_code == 201 and r.json()["phone"] == "+221771234567"


@pytest.mark.parametrize("bad", ["0612", "abcdefgh", "+33 1 23", "000000000000"])
def test_invalid_numbers_are_rejected(client, bad):
    assert _register(client, bad).status_code == 422


def test_phone_is_required_at_registration(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "n@example.org",
            "password": "correct-horse-battery",
            "full_name": "Nom Test",
            "role": "beneficiary",
        },
    )
    assert r.status_code == 422 and "phone" in r.text


def test_profile_update_normalizes_and_ignores_privileged_fields(client, actor):
    b = actor("beneficiary", "b@example.org")
    r = client.patch(
        "/api/auth/me",
        json={"phone": "06 98 76 54 32", "role": "admin", "is_verified": True},
        headers=b.h,
    )
    assert r.status_code == 200
    assert r.json()["phone"] == "+33698765432"
    assert r.json()["role"] == "beneficiary" and r.json()["is_verified"] is False
    assert client.patch("/api/auth/me", json={"phone": "123"}, headers=b.h).status_code == 422


def test_legacy_account_without_phone_can_complete_profile(client, db):
    db.add(
        User(
            email="old@example.org",
            hashed_password=hash_password("correct-horse-battery"),
            full_name="Ancien Compte",
            role=UserRole.BENEFICIARY,
        )
    )
    db.commit()
    login = client.post(
        "/api/auth/login", json={"email": "old@example.org", "password": "correct-horse-battery"}
    )
    assert login.status_code == 200  # un compte ancien reste utilisable
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=h).json()["phone"] is None
    done = client.patch("/api/auth/me", json={"phone": "0612345678"}, headers=h)
    assert done.json()["phone"] == "+33612345678"


def test_contact_is_shared_only_between_the_two_parties_of_an_active_claim(client, actor):
    p = actor("provider", "p@example.org")
    b = actor("beneficiary", "b@example.org")
    other = actor("beneficiary", "other@example.org", phone="+33633333333")
    lid = client.post("/api/listings", json=listing_payload(), headers=p.h).json()["id"]

    # Jamais dans les annonces, quel que soit le lecteur
    for headers in (p.h, b.h, other.h):
        assert PROVIDER_PHONE.lstrip("+") not in client.get("/api/listings", headers=headers).text
        assert (
            PROVIDER_PHONE.lstrip("+")
            not in client.get(f"/api/listings/{lid}", headers=headers).text
        )

    created = client.post(f"/api/listings/{lid}/claim", json={"quantity": "2"}, headers=b.h).json()
    assert created["contact_phone"] == PROVIDER_PHONE
    cid = created["id"]

    assert client.get("/api/claims/me", headers=b.h).json()[0]["contact_phone"] == PROVIDER_PHONE
    received = client.get("/api/claims/received", headers=p.h).json()[0]
    assert received["contact_phone"] == BENEFICIARY_PHONE
    assert client.get("/api/claims/me", headers=other.h).json() == []  # un tiers ne voit rien

    # Dès que la réservation n'est plus en cours, les numéros ne sont plus transmis
    code = created["pickup_code"]
    client.post(f"/api/claims/{cid}/pickup", json={"code": code}, headers=p.h)
    assert client.get("/api/claims/me", headers=b.h).json()[0]["contact_phone"] is None
    assert client.get("/api/claims/received", headers=p.h).json()[0]["contact_phone"] is None


def test_contact_is_hidden_after_cancellation(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = client.post("/api/listings", json=listing_payload(), headers=p.h).json()["id"]
    cid = client.post(f"/api/listings/{lid}/claim", json={"quantity": "1"}, headers=b.h).json()[
        "id"
    ]
    done = client.post(f"/api/claims/{cid}/cancel", headers=b.h).json()
    assert done["contact_phone"] is None
    assert client.get("/api/claims/received", headers=p.h).json()[0]["contact_phone"] is None
