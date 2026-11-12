import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import get_settings

_hasher = PasswordHasher()
# Hash factice : on vérifie toujours un hash, même si l'email n'existe pas,
# pour ne pas révéler l'existence d'un compte par le temps de réponse.
_DUMMY_HASH = _hasher.hash("not-a-real-password")

TokenType = Literal["access", "refresh"]
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        return _hasher.verify(hashed or _DUMMY_HASH, password) and hashed is not None
    except (VerificationError, InvalidHashError):
        return False


def create_token(user_id: uuid.UUID, token_type: TokenType) -> tuple[str, int]:
    s = get_settings()
    ttl = (
        timedelta(minutes=s.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=s.refresh_token_expire_days)
    )
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, s.secret_key, algorithm=ALGORITHM), int(ttl.total_seconds())


def decode_token(token: str, expected_type: TokenType) -> uuid.UUID | None:
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        if payload.get("type") != expected_type:
            return None
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
