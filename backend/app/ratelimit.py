"""Limiteur de débit en mémoire (fenêtre glissante), par IP et par périmètre.

Limite assumée : l'état est local au processus. Avec plusieurs réplicas (projets 3 et 5),
la limite effective est multipliée par le nombre de pods ; la vraie solution est de la
déplacer à l'Ingress/Gateway ou dans Redis.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings

_hits: dict[str, deque[float]] = defaultdict(deque)
WINDOW_SECONDS = 60


def reset() -> None:
    _hits.clear()


def rate_limited(scope: str, setting_name: str):
    def dependency(request: Request) -> None:
        limit = getattr(get_settings(), setting_name)
        ip = request.client.host if request.client else "unknown"
        key = f"{scope}:{ip}"
        now = time.monotonic()
        window = _hits[key]
        while window and now - window[0] > WINDOW_SECONDS:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Trop de tentatives. Réessaie dans une minute.",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
        window.append(now)

    return dependency


auth_rate_limit = rate_limited("auth", "auth_rate_limit_per_minute")
pickup_rate_limit = rate_limited("pickup", "pickup_rate_limit_per_minute")
