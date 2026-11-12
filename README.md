# FoodBridge

Plateforme de **dons alimentaires traçables** entre commerçants et associations.
Un surplus encore consommable est publié, réservé (y compris en partie), puis retiré avec un code à 6 chiffres.
Seuls les retraits confirmés comptent dans l'impact (kg sauvés, repas, CO₂e évité).

> Projet fil rouge d'un parcours DevOps : une seule application, cinq projets (CI/CD, Terraform AWS,
> Kubernetes, monitoring, architecture de production haute disponibilité).

**Statut : V1 + Projet 1.** Annonces, réservation sans surréservation (verrous PostgreSQL), retrait par code,
impact réel, contact téléphonique protégé, et pipeline CI/CD ([`docs/ci-cd.md`](docs/ci-cd.md)).

## Architecture

```
 Navigateur ──▶ Frontend (React, nginx-unprivileged :8080)
                    │  /api/*  (même origine, proxy)
                    ▼
               Backend (FastAPI :8000) ──▶ PostgreSQL 16
                 ├─ /health        liveness  (ne touche jamais la base)
                 ├─ /health/ready  readiness (vérifie la base)
                 └─ /metrics       Prometheus (HTTP + métriques métier)

               Job d'expiration : python -m app.jobs.expire_listings   (futur CronJob Kubernetes)
```

| Couche | Choix | Pourquoi |
|---|---|---|
| API | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, psycopg 3 | Typage de bout en bout, migrations versionnées |
| Auth | JWT courts (15 min) + refresh (7 j), argon2 | Pas de session serveur, hash résistant au GPU |
| Concurrence | `SELECT ... FOR UPDATE`, ordre de verrous unique | Aucune surréservation, prouvée par test de mutation |
| Front | React, TypeScript, Vite, Tailwind 4, Framer Motion, TanStack Query | Mobile-first, états de chargement soignés |
| Tests | pytest sur **vrai Postgres** (62), Vitest (28) | Enums, JSONB, CHECK et verrous ne se testent pas sur SQLite |
| Images | Backend multi-étapes non-root, front `nginx-unprivileged` | Prépare Trivy et les `securityContext` K8s |

## Démarrage rapide

```bash
make init        # crée .env
make dev-up      # db + migrations + backend + frontend   (ou : docker compose up --build -d)
```

Application : http://localhost:8080 · Swagger : http://localhost:8000/api/docs · Métriques : http://localhost:8000/metrics

### Sans Docker pour le code

```bash
docker compose up -d db                       # ou un Postgres local
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://foodbridge:foodbridge@localhost:5433/foodbridge
alembic upgrade head && uvicorn app.main:app --reload
# autre terminal
cd frontend && npm ci && npm run dev          # http://localhost:5173, /api proxifié vers :8000
```

> Le port hôte de la base est **5433** par défaut (`POSTGRES_HOST_PORT`), car 5432 est souvent réservé sous Windows.

### Administration

```bash
ADMIN_PASSWORD='un-mot-de-passe-long' python -m app.cli create-admin --email moi@exemple.org
```

L'admin se connecte via Swagger (`/api/docs`, bouton *Authorize*) pour lister les comptes
(`GET /api/admin/users?verified=false`) et vérifier une organisation (`PATCH /api/admin/users/{id}/verify`).
Un badge « Vérifié » apparaît alors partout. Avec `REQUIRE_VERIFIED_CLAIMANTS=true`, seules les organisations
vérifiées peuvent réserver.

## Tests

```bash
make test         # backend (Postgres réel) + frontend
make lint         # ruff + tsc
```

La base `foodbridge_test` est créée par `make test-backend` (surchargeable via `TEST_DATABASE_URL`).
Le schéma y est créé par les migrations : tester l'application teste aussi les migrations.

## API

| Méthode | Route | Accès |
|---|---|---|
| GET | `/health`, `/health/ready`, `/metrics` | Public (racine, hors `/api`) |
| POST | `/api/auth/register`, `/login`, `/refresh` | Public, 10 req/min/IP |
| GET/PATCH | `/api/auth/me` | Authentifié (PATCH : compléter son profil, ex. téléphone) |
| GET | `/api/listings` | Authentifié ; filtres `category`, `q` ; pagination par curseur |
| POST/PATCH/DELETE | `/api/listings`, `/api/listings/{id}` | Commerçant propriétaire (DELETE = suppression logique) |
| GET | `/api/listings/mine`, `/api/listings/{id}` | Commerçant / authentifié |
| POST | `/api/listings/{id}/claim` | Bénéficiaire |
| GET | `/api/claims/me`, `/api/claims/received` | Bénéficiaire / commerçant |
| POST | `/api/claims/{id}/pickup` | Commerçant propriétaire, **code requis**, 20 req/min/IP |
| POST | `/api/claims/{id}/cancel`, `/no-show` | Bénéficiaire ou commerçant / commerçant |
| GET | `/api/impact/summary` (public), `/api/impact/me` | Public / authentifié |
| GET/PATCH | `/api/admin/users`, `/api/admin/users/{id}/verify` | Admin |

Les actions de statut sont des routes explicites (`/pickup`, `/cancel`, `/no-show`) plutôt qu'un `PATCH` générique :
chacune a ses propres règles d'autorisation et d'état.

## Règles métier

- **DLC** : le retrait doit se terminer avant la date limite. **DDM** : informative.
- Créneau de retrait dans le futur, au plus 7 jours (`MAX_LISTING_HORIZON_DAYS`).
- Réservation partielle ; quantité réservée jamais supérieure au stock ; une réservation en cours par annonce et par bénéficiaire.
- Anti-abus : 3 réservations en cours maximum, suspension après 3 absences (réglable).
- **Téléphone** obligatoire (normalisé E.164, pays par défaut `DEFAULT_PHONE_REGION`). Transmis uniquement à l'autre partie d'une réservation en cours, jamais dans les annonces.
- Le **code de retrait** n'est visible que du bénéficiaire, tant que la réservation est en cours.
- L'**impact** est créé uniquement au retrait validé, avec des facteurs stockés en base (`impact_factors`).

## Métriques

HTTP : `http_requests_total`, `http_request_duration_seconds`.
Métier : `foodbridge_users_registered_total{role}`, `foodbridge_listings_created_total{category}`,
`foodbridge_claims_total{status}`, `foodbridge_kg_rescued_total`.

## CI/CD

`.github/workflows/ci.yml` : lint, migrations (`alembic check`), tests sur Postgres réel, build, contrôle de taille et
non-root, scan Trivy, puis publication sur GHCR depuis `main`. Moindre privilège et action tierce épinglée par SHA,
suite à l'incident Trivy de mars 2026. Détails, mise en route et pannes : [`docs/ci-cd.md`](docs/ci-cd.md).

## Sécurité

Argon2 · tokens typés (un refresh ne sert jamais d'access) · réponse identique pour email inconnu et mauvais mot de passe ·
inscription publique impossible en `admin` · refus de démarrer en production avec la clé par défaut ·
code de retrait masqué au commerçant, limité en débit · mot de passe admin jamais en argument de commande ·
conteneurs non-root · secrets hors dépôt.

## Limites connues

- Rate limiting **en mémoire par processus** : avec N réplicas, la limite effective est N fois plus large (à déplacer à l'Ingress ou Redis).
- Jetons en `localStorage` (exposés en cas de XSS) ; évolution : refresh token en cookie `httpOnly`.
- Pas de révocation de refresh token, ni de suppression de compte RGPD (V2).
- Le code de retrait est en clair en base (usage éphémère, 6 chiffres, limité en débit) ; un hash n'apporterait que peu pour 10⁶ combinaisons.
- Facteurs d'impact : ordres de grandeur à sourcer (ADEME, WRAP) avant toute communication de chiffres.
- Le numéro de téléphone est **saisi, pas vérifié** : rien ne prouve que son propriétaire en est le titulaire (vérification par SMS prévue en V2).
- Pas encore d'interface d'administration (Swagger suffit), ni de photos, géolocalisation, notifications.
- ESLint côté front : ajouté avec le pipeline du projet 1.

## Feuille de route

| Palier | Contenu |
|---|---|
| V0 | Fondations, auth, schéma, sondes, métriques |
| **V1 (ici)** | Annonces, réservation avec verrous, retrait par code, impact, expiration, admin minimal |
| Projet 1 | Pipeline CI/CD (ici) |
| V2 | Vérification du téléphone (OTP) et de l'e-mail, profil d'organisation (adresse, numéro d'enregistrement), notifications (e-mail, WhatsApp), messagerie, photos (MinIO), géolocalisation, graphiques d'impact, interface d'administration |

Documentation : [`docs/data-model.md`](docs/data-model.md) · [`docs/troubleshooting.md`](docs/troubleshooting.md)

## Checklist de fin de V1

- [ ] `make dev-up` : 4 services sains (`docker compose ps`)
- [ ] `make test` vert (62 backend, 28 frontend) ; `make lint` propre
- [ ] `alembic upgrade head` / `downgrade base` / `upgrade head` sans erreur, `alembic check` sans dérive
- [ ] Parcours manuel : commerçant publie, association réserve, commerçant valide avec le code, l'impact augmente
- [ ] `pytest tests/test_concurrency.py` vert ; mutation (retirer `with_for_update`) fait échouer ces tests
- [ ] `python -m app.jobs.expire_listings` s'exécute et est idempotent
- [ ] Aucun secret dans le dépôt
