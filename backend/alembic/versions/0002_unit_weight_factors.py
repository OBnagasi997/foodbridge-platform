"""facteurs de poids par unité

Convertit pièces, portions, barquettes et litres en kg pour le calcul d'impact.
Ordres de grandeur volontairement prudents, modifiables en base sans redéploiement.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE = "Hypothese de travail a affiner avec les associations partenaires"
FACTORS = {
    "kg_per_piece": (0.3, "kg par piece"),
    "kg_per_portion": (0.4, "kg par portion"),
    "kg_per_barquette": (0.5, "kg par barquette"),
    "kg_per_litre": (1.0, "kg par litre"),
}


def upgrade() -> None:
    table = sa.table(
        "impact_factors",
        sa.column("key", sa.String),
        sa.column("value", sa.Numeric),
        sa.column("unit", sa.String),
        sa.column("source", sa.String),
    )
    op.bulk_insert(
        table,
        [{"key": k, "value": v, "unit": u, "source": SOURCE} for k, (v, u) in FACTORS.items()],
    )


def downgrade() -> None:
    keys = ", ".join(f"'{k}'" for k in FACTORS)
    op.execute(f"DELETE FROM impact_factors WHERE key IN ({keys})")
