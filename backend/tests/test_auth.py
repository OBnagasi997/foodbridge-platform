from app import ratelimit
from app.config import get_settings
from app.models import AuditLog, User
from app.security import create_token

PASSWORD = "correct-horse-battery"


def test_register_login_me(client, db):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "Chef@Example.org",
            "password": PASSWORD,
            "phone": "+33611111111",
            "full_name": "Chef Test",
            "role": "provider",
            "organization_name": "Maison Test",
        },
    )
    assert r.status_code == 201
    assert r.json()["email"] == "chef@example.org"  # normalisé
    assert "password" not in r.text and "hashed_password" not in r.text
    assert r.json()["is_verified"] is False

    user = db.query(User).one()
    assert user.hashed_password.startswith("$argon2")
    assert db.query(AuditLog).filter_by(action="user.registered").count() == 1

    login = client.post("/api/auth/login", json={"email": "chef@example.org", "password": PASSWORD})
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer" and tokens["expires_in"] == 15 * 60

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["organization_name"] == "Maison Test"


def test_duplicate_email_conflict(client, make_user):
    make_user(email="dup@example.org")
    r = client.post(
        "/api/auth/register",
        json={
            "email": "DUP@example.org",
            "password": PASSWORD,
            "phone": "+33611111111",
            "full_name": "Autre",
            "role": "beneficiary",
        },
    )
    assert r.status_code == 409


def test_cannot_self_register_as_admin(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "a@example.org",
            "password": PASSWORD,
            "phone": "+33611111111",
            "full_name": "Eve",
            "role": "admin",
        },
    )
    assert r.status_code == 422


def test_provider_requires_organization(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "p@example.org",
            "password": PASSWORD,
            "phone": "+33611111111",
            "full_name": "Paul",
            "role": "provider",
        },
    )
    assert r.status_code == 422


def test_weak_password_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "w@example.org",
            "password": "short",
            "phone": "+33611111111",
            "full_name": "Wil",
            "role": "beneficiary",
        },
    )
    assert r.status_code == 422


def test_wrong_password_and_unknown_user_same_error(client, make_user):
    make_user(email="known@example.org")
    wrong = client.post(
        "/api/auth/login", json={"email": "known@example.org", "password": "x" * 12}
    )
    unknown = client.post(
        "/api/auth/login", json={"email": "nobody@example.org", "password": "x" * 12}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_valid_access_token(client, make_user, db):
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    )

    make_user(email="t@example.org")
    user = db.query(User).one()
    refresh, _ = create_token(user.id, "refresh")
    # un refresh token ne doit jamais servir d'access token
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401


def test_refresh_flow(client, make_user):
    body = make_user(email="r@example.org")
    tokens = client.post(
        "/api/auth/login", json={"email": "r@example.org", "password": body["password"]}
    ).json()
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    # un access token n'est pas accepté comme refresh token
    bad = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401


def test_inactive_user_cannot_login(client, make_user, db):
    body = make_user(email="off@example.org")
    user = db.query(User).one()
    user.is_active = False
    db.commit()
    r = client.post(
        "/api/auth/login", json={"email": "off@example.org", "password": body["password"]}
    )
    assert r.status_code == 401


def test_auth_rate_limit(client, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MINUTE", "3")
    get_settings.cache_clear()
    ratelimit.reset()
    try:
        codes = [
            client.post(
                "/api/auth/login", json={"email": "x@example.org", "password": "y" * 12}
            ).status_code
            for _ in range(5)
        ]
        assert codes == [401, 401, 401, 429, 429]
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
