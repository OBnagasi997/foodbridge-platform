"""Modèle de données FoodBridge (cf. docs/data-model.md)."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def _enum(py_enum: type[enum.Enum], name: str) -> SAEnum:
    return SAEnum(py_enum, name=name, values_callable=lambda e: [m.value for m in e])


class UserRole(enum.StrEnum):
    PROVIDER = "provider"
    BENEFICIARY = "beneficiary"
    ADMIN = "admin"


class Category(enum.StrEnum):
    BOULANGERIE = "boulangerie"
    TRAITEUR = "traiteur"
    FRUITS_LEGUMES = "fruits_legumes"
    PRODUITS_LAITIERS = "produits_laitiers"
    EPICERIE = "epicerie"
    AUTRE = "autre"


class Unit(enum.StrEnum):
    KG = "kg"
    PIECES = "pieces"
    PORTIONS = "portions"
    BARQUETTES = "barquettes"
    LITRES = "litres"


class DateType(enum.StrEnum):
    DLC = "dlc"  # date limite de consommation : à ne jamais dépasser
    DDM = "ddm"  # date de durabilité minimale : qualité, pas sécurité


class StorageCondition(enum.StrEnum):
    AMBIENT = "ambient"
    CHILLED = "chilled"
    FROZEN = "frozen"


class ListingStatus(enum.StrEnum):
    AVAILABLE = "available"
    PARTIALLY_CLAIMED = "partially_claimed"
    FULLY_CLAIMED = "fully_claimed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ClaimStatus(enum.StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PICKED_UP = "picked_up"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole, "user_role"))
    organization_name: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    # Une organisation n'est visible comme "vérifiée" qu'après validation par un admin.
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    no_show_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listings: Mapped[list["Listing"]] = relationship(back_populates="provider")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_listings_quantity_positive"),
        CheckConstraint(
            "quantity_claimed >= 0 AND quantity_claimed <= quantity",
            name="ck_listings_claimed_within_quantity",
        ),
        CheckConstraint("pickup_end > pickup_start", name="ck_listings_pickup_window"),
        Index("ix_listings_status_pickup_end", "status", "pickup_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[Category] = mapped_column(_enum(Category, "listing_category"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity_claimed: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), server_default=text("0")
    )
    unit: Mapped[Unit] = mapped_column(_enum(Unit, "listing_unit"))
    date_type: Mapped[DateType] = mapped_column(_enum(DateType, "listing_date_type"))
    storage_condition: Mapped[StorageCondition] = mapped_column(
        _enum(StorageCondition, "listing_storage_condition")
    )
    allergens: Mapped[list[str]] = mapped_column(
        JSONType, default=list, server_default=text("'[]'")
    )
    pickup_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pickup_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expiry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ListingStatus] = mapped_column(
        _enum(ListingStatus, "listing_status"),
        default=ListingStatus.AVAILABLE,
        server_default=ListingStatus.AVAILABLE.value,
    )
    location_text: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    image_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # soft delete

    provider: Mapped[User] = relationship(back_populates="listings")

    @property
    def quantity_remaining(self) -> Decimal:
        return self.quantity - self.quantity_claimed

    @property
    def provider_name(self) -> str:
        return self.provider.organization_name or self.provider.full_name

    @property
    def provider_verified(self) -> bool:
        return self.provider.is_verified


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint("quantity_claimed > 0", name="ck_claims_quantity_positive"),
        Index("ix_claims_beneficiary_status", "beneficiary_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    quantity_claimed: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[ClaimStatus] = mapped_column(
        _enum(ClaimStatus, "claim_status"),
        default=ClaimStatus.CONFIRMED,
        server_default=ClaimStatus.CONFIRMED.value,
    )
    pickup_code: Mapped[str] = mapped_column(String(6))  # saisi par le commerçant au retrait
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    listing: Mapped[Listing] = relationship()
    beneficiary: Mapped[User] = relationship()

    @property
    def listing_title(self) -> str:
        return self.listing.title

    @property
    def unit(self) -> Unit:
        return self.listing.unit

    @property
    def provider_name(self) -> str:
        return self.listing.provider_name

    @property
    def location_text(self) -> str:
        return self.listing.location_text

    @property
    def pickup_start(self) -> datetime:
        return self.listing.pickup_start

    @property
    def pickup_end(self) -> datetime:
        return self.listing.pickup_end

    @property
    def beneficiary_name(self) -> str:
        return self.beneficiary.organization_name or self.beneficiary.full_name

    @property
    def beneficiary_verified(self) -> bool:
        return self.beneficiary.is_verified


class ImpactFactor(Base):
    """Hypothèses de conversion, modifiables sans redéploiement et citables dans le README."""

    __tablename__ = "impact_factors"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    unit: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ImpactEvent(Base):
    """Un événement par retrait confirmé. Seule source des chiffres d'impact."""

    __tablename__ = "impact_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), unique=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    kg_rescued: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    meals_estimated: Mapped[Decimal] = mapped_column(Numeric(10, 1))
    co2e_avoided_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSONType, default=dict, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
