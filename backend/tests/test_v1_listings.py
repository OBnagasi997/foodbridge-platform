from tests.helpers import iso, listing_payload


def test_provider_creates_listing(client, actor):
    p = actor("provider", "p@example.org")
    r = client.post("/api/listings", json=listing_payload(), headers=p.h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "available"
    assert body["provider_name"] == "Org p@example.org"
    assert float(body["quantity_remaining"]) == 10


def test_beneficiary_cannot_create_listing(client, actor):
    b = actor("beneficiary", "b@example.org")
    assert client.post("/api/listings", json=listing_payload(), headers=b.h).status_code == 403


def test_dlc_forbids_pickup_after_expiry_but_ddm_allows_it(client, actor):
    p = actor("provider", "p@example.org")
    late = {"pickup_end": iso(5), "expiry_at": iso(4)}
    dlc = client.post("/api/listings", json=listing_payload(date_type="dlc", **late), headers=p.h)
    assert dlc.status_code == 422
    ddm = client.post("/api/listings", json=listing_payload(date_type="ddm", **late), headers=p.h)
    assert ddm.status_code == 201


def test_window_validation(client, actor):
    p = actor("provider", "p@example.org")
    inverted = listing_payload(pickup_start=iso(3), pickup_end=iso(1))
    assert client.post("/api/listings", json=inverted, headers=p.h).status_code == 422
    past = listing_payload(pickup_start=iso(-3), pickup_end=iso(-1), expiry_at=iso(2))
    assert client.post("/api/listings", json=past, headers=p.h).status_code == 422
    far = listing_payload(pickup_end=iso(24 * 10), expiry_at=iso(24 * 11))
    assert client.post("/api/listings", json=far, headers=p.h).status_code == 422


def test_input_validation(client, actor):
    p = actor("provider", "p@example.org")
    assert (
        client.post("/api/listings", json=listing_payload(quantity="0"), headers=p.h).status_code
        == 422
    )
    bad = listing_payload(allergens=["gluten", "pas-un-allergene"])
    assert client.post("/api/listings", json=bad, headers=p.h).status_code == 422
    naive = listing_payload(pickup_end="2030-01-01T10:00:00")  # sans fuseau horaire
    assert client.post("/api/listings", json=naive, headers=p.h).status_code == 422


def test_cursor_pagination_is_complete_and_ordered(client, actor):
    p = actor("provider", "p@example.org")
    b = actor("beneficiary", "b@example.org")
    for i in range(5):
        r = client.post(
            "/api/listings",
            json=listing_payload(title=f"Lot {i}", pickup_end=iso(2 + i), expiry_at=iso(12)),
            headers=p.h,
        )
        assert r.status_code == 201

    seen, cursor, pages = [], None, 0
    while True:
        url = "/api/listings?limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = client.get(url, headers=b.h).json()
        seen += [i["title"] for i in page["items"]]
        pages += 1
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert pages == 3
    assert seen == [f"Lot {i}" for i in range(5)]  # aucun doublon, ordre d'urgence
    assert client.get("/api/listings?cursor=garbage", headers=b.h).status_code == 400


def test_search_and_category_filters(client, actor):
    p = actor("provider", "p@example.org")
    b = actor("beneficiary", "b@example.org")
    client.post("/api/listings", json=listing_payload(title="Baguettes"), headers=p.h)
    client.post(
        "/api/listings",
        json=listing_payload(title="Salade de fruits", category="fruits_legumes"),
        headers=p.h,
    )
    by_cat = client.get("/api/listings?category=fruits_legumes", headers=b.h).json()["items"]
    assert [i["title"] for i in by_cat] == ["Salade de fruits"]
    by_q = client.get("/api/listings?q=bagu", headers=b.h).json()["items"]
    assert [i["title"] for i in by_q] == ["Baguettes"]


def test_mine_lists_only_own(client, actor):
    p1, p2 = actor("provider", "p1@example.org"), actor("provider", "p2@example.org")
    client.post("/api/listings", json=listing_payload(title="Lot A"), headers=p1.h)
    client.post("/api/listings", json=listing_payload(title="Lot B"), headers=p2.h)
    mine = client.get("/api/listings/mine", headers=p1.h).json()
    assert [i["title"] for i in mine] == ["Lot A"]


def test_update_rules(client, actor):
    p, other = actor("provider", "p@example.org"), actor("provider", "o@example.org")
    b = actor("beneficiary", "b@example.org")
    lid = client.post("/api/listings", json=listing_payload(), headers=p.h).json()["id"]
    client.post(f"/api/listings/{lid}/claim", json={"quantity": "3"}, headers=b.h)

    assert (
        client.patch(f"/api/listings/{lid}", json={"title": "Intrus"}, headers=other.h).status_code
        == 404
    )
    empty = client.patch(f"/api/listings/{lid}", json={"title": None}, headers=p.h)
    assert empty.status_code == 422
    floor = client.patch(f"/api/listings/{lid}", json={"quantity": "2"}, headers=p.h)
    assert floor.status_code == 409  # 3 déjà réservés
    ok = client.patch(
        f"/api/listings/{lid}", json={"quantity": "5", "title": "Nouveau titre"}, headers=p.h
    )
    assert ok.status_code == 200 and float(ok.json()["quantity_remaining"]) == 2
    full = client.patch(f"/api/listings/{lid}", json={"quantity": "3"}, headers=p.h)
    assert full.json()["status"] == "fully_claimed"


def test_delete_cancels_listing_and_active_claims(client, actor):
    p, b = actor("provider", "p@example.org"), actor("beneficiary", "b@example.org")
    lid = client.post("/api/listings", json=listing_payload(), headers=p.h).json()["id"]
    client.post(f"/api/listings/{lid}/claim", json={"quantity": "2"}, headers=b.h)

    assert client.delete(f"/api/listings/{lid}", headers=p.h).status_code == 204
    assert client.get(f"/api/listings/{lid}", headers=b.h).status_code == 404
    assert client.get("/api/listings", headers=b.h).json()["items"] == []
    mine = client.get("/api/claims/me", headers=b.h).json()
    assert mine[0]["status"] == "cancelled" and mine[0]["pickup_code"] is None
