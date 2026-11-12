"""Tests d'intégration sur un vrai PostgreSQL (pas de SQLite : enums, JSONB, contraintes CHECK).

Base utilisée : TEST_DATABASE_URL (par défaut foodbridge_test sur localhost).
Le schéma est créé via les migrations Alembic, ce qui teste aussi les migrations.
"""

import os
from pathlib import Path

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://foodbridge:foodbridge@localhost:5433/foodbridge_test",
)
# Doit être posé AVANT l'import de l'application.
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["PICKUP_RATE_LIMIT_PER_MINUTE"] = "1000"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import ratelimit  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _schema():
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean():
    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE audit_log, impact_events, claims, listings, users "
                "RESTART IDENTITY CASCADE"
            )
        )
    ratelimit.reset()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def make_user(client):
    def _make(role="beneficiary", email="user@example.org", password="correct-horse-battery"):
        body = {
            "email": email,
            "password": password,
            "full_name": "Test User",
            "phone": "+33611111111",
            "role": role,
            "organization_name": "Boulangerie Test" if role == "provider" else None,
        }
        r = client.post("/api/auth/register", json=body)
        assert r.status_code == 201, r.text
        return body

    return _make


@pytest.fixture
def auth_headers(client, make_user):
    def _headers(role="beneficiary", email="user@example.org"):
        body = make_user(role=role, email=email)
        r = client.post("/api/auth/login", json={"email": email, "password": body["password"]})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _headers


@pytest.fixture
def settings_env(monkeypatch):
    """Surcharge temporaire de réglages : settings_env(MAX_ACTIVE_CLAIMS=2)."""
    from app.config import get_settings

    def _set(**values):
        for key, value in values.items():
            monkeypatch.setenv(key.upper(), str(value))
        get_settings.cache_clear()

    yield _set
    monkeypatch.undo()
    get_settings.cache_clear()


PHONES = {"provider": "+33611111111", "beneficiary": "+33622222222"}


@pytest.fixture
def actor(client):
    """Crée et connecte un utilisateur : actor('provider', 'p@x.org') -> .h (en-têtes), .id."""
    from types import SimpleNamespace

    def _make(role, email, org=None, phone=None):
        r = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "correct-horse-battery",
                "full_name": f"{role} {email}",
                "phone": phone or PHONES[role],
                "role": role,
                "organization_name": org or (f"Org {email}" if role == "provider" else None),
            },
        )
        assert r.status_code == 201, r.text
        login = client.post(
            "/api/auth/login", json={"email": email, "password": "correct-horse-battery"}
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        return SimpleNamespace(h=headers, id=r.json()["id"], email=email)

    return _make
