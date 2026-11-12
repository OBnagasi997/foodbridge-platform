from datetime import datetime, timedelta

from sqlalchemy import text

from app.database import engine
from app.models import User
from tests.helpers import listing_payload


def _listing(client, provider, **over):
    r = client.post("/api/listings", json=listing_payload(**over), headers=provider.h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _claim(client, who, lid, qty="1"):
    return client.post(f"/api/listings/{lid}/claim", json={"quantity": qty}, headers=who.h)


def _end_window(lid):
    """Simule l'écoulement du temps : le créneau est désormais terminé."""
    past = datetime.now().astimezone() - timedelta(hours=1)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE listings SET pickup_start=:s, pickup_end=:e WHERE id=:i"),
            {"s": past - timedelta(hours=2), "e": past, "i": lid},
        )


def test_partial_claims_then_sold_out(client, actor):
    p = actor("provider", "p@example.org")
    b1, b2, b3 = (actor("beneficiary", f"b{i}@example.org") for i in range(3))
    lid = _listing(client, p)

    r1 = _claim(client, b1, lid, "4")
    assert r1.status_code == 201
    assert len(r1.json()["pickup_code"]) == 6 and r1.json()["pickup_code"].isdigit()
    assert client.get(f"/api/listings/{lid}", headers=b1.h).json()["status"] == "partially_claimed"

    assert _claim(client, b2, lid, "6").status_code == 201
    assert client.get(f"/api/listings/{lid}", headers=b1.h).json()["status"] == "fully_claimed"

    over = _claim(client, b3, lid, "1")
    assert over.status_code == 409
    assert client.get("/api/listings", headers=b3.h).json()["items"] == []


def test_cannot_claim_more_than_remaining(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p, quantity="5")
    r = _claim(client, b, lid, "5.01")
    assert r.status_code == 409 and "5" in r.json()["detail"]


def test_roles_and_duplicates(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p)
    assert _claim(client, p, lid).status_code == 403  # un commerçant ne réserve pas
    assert _claim(client, b, lid).status_code == 201
    dup = _claim(client, b, lid)
    assert dup.status_code == 409 and "déjà" in dup.json()["detail"]
    assert _claim(client, b, "00000000-0000-0000-0000-000000000000").status_code == 404


def test_pickup_code_is_secret_from_provider(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p)
    code = _claim(client, b, lid).json()["pickup_code"]

    mine = client.get("/api/claims/me", headers=b.h).json()[0]
    assert mine["pickup_code"] == code
    received = client.get("/api/claims/received", headers=p.h).json()[0]
    assert received["pickup_code"] is None
    assert received["beneficiary_name"] == "beneficiary b@example.org"
    assert received["beneficiary_verified"] is False


def test_pickup_creates_impact_only_with_right_code(client, actor):
    p, other = actor("provider", "p@example.org"), actor("provider", "o@example.org")
    b = actor("beneficiary", "b@example.org")
    lid = _listing(client, p)
    claim = _claim(client, b, lid, "4").json()
    cid, code = claim["id"], claim["pickup_code"]
    wrong = "000000" if code != "000000" else "111111"

    assert client.get("/api/impact/summary").json()["pickups_completed"] == 0
    assert (
        client.post(f"/api/claims/{cid}/pickup", json={"code": wrong}, headers=p.h).status_code
        == 400
    )
    assert (
        client.post(f"/api/claims/{cid}/pickup", json={"code": "12"}, headers=p.h).status_code
        == 422
    )
    assert (
        client.post(f"/api/claims/{cid}/pickup", json={"code": code}, headers=other.h).status_code
        == 404
    )
    assert (
        client.post(f"/api/claims/{cid}/pickup", json={"code": code}, headers=b.h).status_code
        == 403
    )
    assert client.get("/api/impact/summary").json()["pickups_completed"] == 0  # rien n'a compté

    ok = client.post(f"/api/claims/{cid}/pickup", json={"code": code}, headers=p.h)
    assert ok.status_code == 200 and ok.json()["status"] == "picked_up"
    assert (
        client.post(f"/api/claims/{cid}/pickup", json={"code": code}, headers=p.h).status_code
        == 409
    )

    s = client.get("/api/impact/summary").json()
    assert s["kg_rescued"] == 4.0
    assert s["meals_estimated"] == 10.0  # 4 kg / 0,4 kg par repas
    assert s["co2e_avoided_kg"] == 10.0  # 4 kg x 2,5
    assert s["pickups_completed"] == 1
    assert client.get("/api/impact/me", headers=p.h).json()["kg_rescued"] == 4.0
    assert client.get("/api/impact/me", headers=b.h).json()["kg_rescued"] == 4.0
    assert client.get("/api/impact/me", headers=other.h).json()["kg_rescued"] == 0.0


def test_unit_conversion_uses_configurable_factors(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p, unit="pieces", quantity="10")
    claim = _claim(client, b, lid, "10").json()
    client.post(
        f"/api/claims/{claim['id']}/pickup", json={"code": claim["pickup_code"]}, headers=p.h
    )
    s = client.get("/api/impact/summary").json()
    assert s["kg_rescued"] == 3.0  # 10 pièces x 0,3 kg
    assert s["meals_estimated"] == 7.5


def test_cancel_restores_stock(client, actor):
    p = actor("provider", "p@example.org")
    b, intruder = actor("beneficiary", "b@example.org"), actor("beneficiary", "i@example.org")
    lid = _listing(client, p, quantity="5")
    cid = _claim(client, b, lid, "5").json()["id"]
    assert client.get(f"/api/listings/{lid}", headers=b.h).json()["status"] == "fully_claimed"

    assert client.post(f"/api/claims/{cid}/cancel", headers=intruder.h).status_code == 404
    done = client.post(f"/api/claims/{cid}/cancel", headers=b.h)
    assert done.status_code == 200 and done.json()["status"] == "cancelled"
    assert done.json()["pickup_code"] is None

    page = client.get("/api/listings", headers=b.h).json()["items"]
    assert float(page[0]["quantity_remaining"]) == 5 and page[0]["status"] == "available"
    assert client.post(f"/api/claims/{cid}/cancel", headers=b.h).status_code == 409


def test_provider_can_cancel_a_claim(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p)
    cid = _claim(client, b, lid, "2").json()["id"]
    assert client.post(f"/api/claims/{cid}/cancel", headers=p.h).status_code == 200


def test_active_claims_limit(client, actor, settings_env):
    settings_env(MAX_ACTIVE_CLAIMS=2)
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    ids = [_listing(client, p, title=f"Lot numéro {i}") for i in range(3)]
    assert _claim(client, b, ids[0]).status_code == 201
    assert _claim(client, b, ids[1]).status_code == 201
    blocked = _claim(client, b, ids[2])
    assert blocked.status_code == 409 and "Limite" in blocked.json()["detail"]


def test_verified_claimants_required_when_enabled(client, actor, settings_env, db):
    settings_env(REQUIRE_VERIFIED_CLAIMANTS="true")
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p)
    assert _claim(client, b, lid).status_code == 403
    user = db.get(User, b.id)
    user.is_verified = True
    db.commit()
    assert _claim(client, b, lid).status_code == 201


def test_cannot_claim_after_window_ended(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p)
    _end_window(lid)
    assert _claim(client, b, lid).status_code == 409


def test_no_show_flow_and_suspension(client, actor, settings_env, db):
    settings_env(MAX_NO_SHOWS=1)
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p)
    cid = _claim(client, b, lid).json()["id"]

    early = client.post(f"/api/claims/{cid}/no-show", headers=p.h)
    assert early.status_code == 409  # créneau pas terminé

    _end_window(lid)
    ok = client.post(f"/api/claims/{cid}/no-show", headers=p.h)
    assert ok.status_code == 200 and ok.json()["status"] == "no_show"
    db.expire_all()
    assert db.get(User, b.id).no_show_count == 1

    lid2 = _listing(client, p, title="Un autre lot")
    suspended = _claim(client, b, lid2)
    assert suspended.status_code == 403 and "suspendues" in suspended.json()["detail"]


def test_pickup_is_rate_limited(client, actor, settings_env):
    settings_env(PICKUP_RATE_LIMIT_PER_MINUTE=3)
    from app import ratelimit

    ratelimit.reset()
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    cid = _claim(client, b, _listing(client, p)).json()["id"]
    codes = [
        client.post(f"/api/claims/{cid}/pickup", json={"code": "000000"}, headers=p.h).status_code
        for _ in range(5)
    ]
    assert codes[3:] == [429, 429]


def test_business_metrics_are_exposed(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = _listing(client, p)
    claim = _claim(client, b, lid, "2").json()
    client.post(
        f"/api/claims/{claim['id']}/pickup", json={"code": claim["pickup_code"]}, headers=p.h
    )
    body = client.get("/metrics").text
    assert 'foodbridge_listings_created_total{category="boulangerie"}' in body
    assert 'foodbridge_claims_total{status="confirmed"}' in body
    assert 'foodbridge_claims_total{status="picked_up"}' in body
    kg = [line for line in body.splitlines() if line.startswith("foodbridge_kg_rescued_total ")]
    assert kg and float(kg[0].split()[1]) >= 2.0
