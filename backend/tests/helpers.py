from datetime import datetime, timedelta


def iso(delta_hours: float) -> str:
    return (datetime.now().astimezone() + timedelta(hours=delta_hours)).isoformat()


def listing_payload(**over):
    data = {
        "title": "Pains et viennoiseries du soir",
        "description": "Invendus de la journée",
        "category": "boulangerie",
        "quantity": "10",
        "unit": "kg",
        "date_type": "dlc",
        "storage_condition": "ambient",
        "allergens": ["gluten"],
        "pickup_start": iso(1),
        "pickup_end": iso(3),
        "expiry_at": iso(6),
        "location_text": "12 rue du Marché",
    }
    data.update(over)
    return data
