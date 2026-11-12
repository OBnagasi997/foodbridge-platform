import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: Any,
    actor_id: uuid.UUID | None = None,
    **details: Any,
) -> None:
    """Ajoute une ligne d'audit à la transaction en cours (le commit appartient à l'appelant)."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details,
        )
    )
