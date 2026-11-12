"""Métriques métier Prometheus.

Les métriques HTTP (http_requests_total, http_request_duration_seconds) sont fournies par
prometheus-fastapi-instrumentator. Celles-ci décrivent ce que fait le *produit*.
Elles sont déclarées dès la Phase 0 pour figer le nom des séries ; les compteurs de
réservation et de kg sauvés seront incrémentés en V1.
"""

from prometheus_client import Counter

USERS_REGISTERED = Counter("foodbridge_users_registered_total", "Comptes créés", ["role"])
LISTINGS_CREATED = Counter("foodbridge_listings_created_total", "Annonces publiées", ["category"])
CLAIMS = Counter("foodbridge_claims_total", "Réservations par statut", ["status"])
KG_RESCUED = Counter(
    "foodbridge_kg_rescued_total", "Kilogrammes sauvés (retraits confirmés uniquement)"
)
