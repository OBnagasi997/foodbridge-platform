"""Validation et normalisation des numéros de téléphone au format E.164 (+33612345678)."""

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

from app.config import get_settings


def normalize_phone(raw: str) -> str:
    """Accepte un numéro national (région par défaut) ou international (+...). Lève ValueError."""
    try:
        number = phonenumbers.parse(raw.strip(), get_settings().default_phone_region)
    except NumberParseException as exc:
        raise ValueError("Numéro de téléphone invalide") from exc
    if not phonenumbers.is_valid_number(number):
        raise ValueError("Numéro de téléphone invalide pour ce pays")
    return phonenumbers.format_number(number, PhoneNumberFormat.E164)
