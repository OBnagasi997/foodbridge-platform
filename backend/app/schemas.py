import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models import (
    Category,
    ClaimStatus,
    DateType,
    ListingStatus,
    StorageCondition,
    Unit,
    UserRole,
)
from app.phone import normalize_phone


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    # L'inscription publique ne permet jamais de créer un admin.
    role: Literal["provider", "beneficiary"]
    organization_name: str | None = Field(default=None, max_length=160)
    # Obligatoire : permet au commerçant et à l'association de se joindre pour un retrait.
    phone: str = Field(min_length=6, max_length=32)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("full_name", "organization_name")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() or None if v else v

    @model_validator(mode="after")
    def _provider_needs_organization(self) -> "RegisterIn":
        if self.role == "provider" and not self.organization_name:
            raise ValueError("organization_name est obligatoire pour un commerçant")
        return self


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    organization_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, min_length=6, max_length=32)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    organization_name: str | None
    phone: str | None
    is_verified: bool
    created_at: datetime


ALLERGENS = (
    "gluten",
    "crustaces",
    "oeufs",
    "poisson",
    "arachides",
    "soja",
    "lait",
    "fruits_a_coque",
    "celeri",
    "moutarde",
    "sesame",
    "sulfites",
    "lupin",
    "mollusques",
)  # les 14 allergènes à déclaration obligatoire (UE)
Allergen = Literal[
    "gluten",
    "crustaces",
    "oeufs",
    "poisson",
    "arachides",
    "soja",
    "lait",
    "fruits_a_coque",
    "celeri",
    "moutarde",
    "sesame",
    "sulfites",
    "lupin",
    "mollusques",
]
Qty = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


def _check_window(start: datetime, end: datetime, expiry: datetime, date_type: DateType) -> None:
    if end <= start:
        raise ValueError("La fin du créneau de retrait doit être après son début")
    if date_type == DateType.DLC and end > expiry:
        raise ValueError("Avec une DLC, le retrait doit se terminer avant la date limite")


class ListingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: Category
    quantity: Qty
    unit: Unit
    date_type: DateType
    storage_condition: StorageCondition
    allergens: list[Allergen] = []
    pickup_start: AwareDatetime
    pickup_end: AwareDatetime
    expiry_at: AwareDatetime
    location_text: str = Field(min_length=3, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _window(self) -> "ListingCreate":
        _check_window(self.pickup_start, self.pickup_end, self.expiry_at, self.date_type)
        return self


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    quantity: Qty | None = None
    allergens: list[Allergen] | None = None
    storage_condition: StorageCondition | None = None
    pickup_start: AwareDatetime | None = None
    pickup_end: AwareDatetime | None = None
    expiry_at: AwareDatetime | None = None
    location_text: str | None = Field(default=None, min_length=3, max_length=255)


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID
    title: str
    description: str | None
    category: Category
    quantity: Decimal
    quantity_claimed: Decimal
    quantity_remaining: Decimal
    unit: Unit
    date_type: DateType
    storage_condition: StorageCondition
    allergens: list[str]
    pickup_start: datetime
    pickup_end: datetime
    expiry_at: datetime
    status: ListingStatus
    location_text: str
    image_url: str | None
    provider_name: str
    provider_verified: bool
    created_at: datetime


class ListingPage(BaseModel):
    items: list[ListingOut]
    next_cursor: str | None = None


class ClaimCreate(BaseModel):
    quantity: Qty
    notes: str | None = Field(default=None, max_length=500)


class PickupIn(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    listing_title: str
    provider_name: str
    location_text: str
    pickup_start: datetime
    pickup_end: datetime
    unit: Unit
    quantity_claimed: Decimal
    status: ClaimStatus
    claimed_at: datetime
    picked_up_at: datetime | None
    notes: str | None
    beneficiary_name: str
    beneficiary_verified: bool
    # Visible uniquement par le bénéficiaire, tant que la réservation est active.
    pickup_code: str | None = None
    # Numéro de l'autre partie, visible uniquement tant que la réservation est en cours.
    contact_phone: str | None = None


class AdminUserOut(UserOut):
    is_active: bool
    no_show_count: int


class VerifyIn(BaseModel):
    is_verified: bool


class ImpactSummary(BaseModel):
    kg_rescued: float
    meals_estimated: float
    co2e_avoided_kg: float
    listings_published: int
    pickups_completed: int
