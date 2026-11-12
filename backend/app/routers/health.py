from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.deps import DB

router = APIRouter(tags=["system"])


@router.get("/health")
def liveness() -> dict[str, str]:
    """Liveness : le processus répond. Ne touche jamais la base (sinon une panne DB
    ferait redémarrer tous les pods en boucle)."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(db: DB) -> dict[str, str]:
    """Readiness : le service peut recevoir du trafic (base joignable)."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable") from exc
    return {"status": "ready"}
