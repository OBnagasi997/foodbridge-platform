# Modèle de données

```mermaid
erDiagram
    users ||--o{ listings : "publie (provider)"
    users ||--o{ claims : "réserve (beneficiary)"
    listings ||--o{ claims : "reçoit"
    claims ||--o| impact_events : "génère à PICKED_UP"
    users ||--o{ audit_log : "acteur"

    users {
        uuid id PK
        string email UK
        string hashed_password "argon2"
        enum role "provider | beneficiary | admin"
        bool is_verified "validé par un admin"
        int no_show_count
    }
    listings {
        uuid id PK
        uuid provider_id FK
        numeric quantity
        numeric quantity_claimed "CHECK 0..quantity"
        enum date_type "dlc | ddm"
        enum storage_condition "ambient | chilled | frozen"
        jsonb allergens
        timestamptz pickup_start
        timestamptz pickup_end "CHECK > pickup_start"
        enum status "available | partially_claimed | fully_claimed | expired | cancelled"
        timestamptz deleted_at "soft delete"
    }
    claims {
        uuid id PK
        uuid listing_id FK
        uuid beneficiary_id FK
        numeric quantity_claimed "CHECK > 0"
        enum status "pending | confirmed | picked_up | cancelled | no_show"
        string pickup_code "6 chiffres"
    }
    impact_events {
        uuid id PK
        uuid claim_id FK,UK "un seul événement par retrait"
        numeric kg_rescued
        numeric meals_estimated
        numeric co2e_avoided_kg
    }
    impact_factors {
        string key PK "kg_per_meal, co2e_kg_per_kg_food"
        numeric value
        string source
    }
    audit_log {
        uuid id PK
        string action
        jsonb details
    }
```

## Téléphone et confidentialité

`users.phone` est stocké au format E.164 (`+33612345678`). Il est obligatoire à l'inscription mais reste
nullable en base, pour que les comptes créés avant cette règle continuent de fonctionner (bandeau d'invitation à
le compléter). Il n'apparaît **jamais** dans les annonces. L'API le transmet (`contact_phone`) uniquement à
l'autre partie d'une réservation **en cours** ; il disparaît dès le retrait, l'annulation ou l'absence.
Des tests, validés par mutation, garantissent l'absence de fuite.

## Règles portées par la base (pas seulement par le code)

| Règle | Mécanisme |
|---|---|
| On ne réserve jamais plus que le stock | `CHECK (quantity_claimed <= quantity)` |
| Un créneau de retrait a un début et une fin cohérents | `CHECK (pickup_end > pickup_start)` |
| Un retrait ne compte qu'une fois dans l'impact | `UNIQUE (impact_events.claim_id)` |
| Un email = un compte | `UNIQUE (users.email)` |

## Hypothèses d'impact

Stockées dans `impact_factors`, pas dans le code. Valeurs initiales : `kg_per_meal = 0.4`,
`co2e_kg_per_kg_food = 2.5`. Ce sont des ordres de grandeur courants : **à sourcer (ADEME, WRAP)
et à citer dans le README avant toute publication de chiffres.**

## Cycle de vie d'une réservation

```mermaid
stateDiagram-v2
    [*] --> confirmed : réservation (code à 6 chiffres généré)
    confirmed --> picked_up : le commerçant saisit le bon code
    confirmed --> cancelled : annulation (bénéficiaire ou commerçant)
    confirmed --> no_show : créneau terminé, absent
    picked_up --> [*] : crée l'impact_event (seul point d'écriture de l'impact)
```

Le statut `pending` existe dans le schéma mais n'est pas utilisé en V1 : la réservation est confirmée
immédiatement. Il servira si une validation manuelle est ajoutée.

## Concurrence (implémentée)

Toute modification du stock passe par un verrou `SELECT ... FOR UPDATE` sur la ligne de l'annonce.
Ordre de verrouillage **unique** pour éviter les interblocages : bénéficiaire (si concerné), puis annonce,
puis réservation.

| Risque | Protection | Test |
|---|---|---|
| 15 personnes, 5 unités | Verrou sur l'annonce, stock relu sous verrou | `test_no_overbooking_under_concurrency` |
| Double clic du même bénéficiaire | Verrou sur le bénéficiaire + contrôle de doublon sous verrou | `test_same_beneficiary_double_click_creates_one_claim` |
| Limite de réservations actives contournée via plusieurs annonces | Verrou sur le bénéficiaire | `test_active_claims_limit_holds_across_listings` |

**Preuve par la mutation** : en retirant les `with_for_update()`, les 15 bénéficiaires obtiennent tous une
réservation sur un stock de 5, et la contrainte `CHECK` ne le détecte pas (chaque transaction écrit « 1 » à
son tour : *lost update*). Le `CHECK` est un filet de sécurité, pas la protection.
