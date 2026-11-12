# Pannes rencontrées et réparations

Journal vivant : chaque panne réelle, avec symptôme, cause et correction. Ne documenter que ce qui
s'est réellement produit, c'est la partie la plus lue en entretien.

| # | Phase | Symptôme | Cause | Réparation |
|---|---|---|---|---|
| 1 | P0 | `alembic upgrade` échoue après un `downgrade` : le type existe déjà | `alembic downgrade` supprime les tables mais **pas les types ENUM PostgreSQL** créés par la migration | Ajout de `DROP TYPE IF EXISTS` pour les 7 enums dans `downgrade()`. Vérifié par le cycle upgrade, downgrade, upgrade, puis `alembic check` (aucune dérive) |
| 2 | P0 | Ruff classe `alembic` comme module local et réordonne les imports | Le dossier `backend/alembic/` masque la bibliothèque du même nom | `known-third-party = ["alembic"]` dans `pyproject.toml` |
| 3 | P0 | Échec de connexion à Postgres pendant un test local, alors que la migration est correcte | Le serveur PostgreSQL local s'était arrêté | Toujours contrôler `pg_isready` avant d'accuser le code. En compose, c'est le rôle du healthcheck de `db` |
| 5 | V1 | *Démonstration volontaire* : sans `FOR UPDATE`, 15 réservations acceptées sur un stock de 5 | Lecture puis écriture non atomiques : chaque transaction lit `quantity_claimed = 0` et écrit `1` (*lost update*). Le `CHECK` ne se déclenche pas | Verrou de ligne `SELECT ... FOR UPDATE` avant toute lecture du stock, ordre de verrouillage unique. Reproductible : retirer les verrous et lancer `pytest tests/test_concurrency.py` |
| 6 | P1 | Estimation de l'image backend : ~290 Mo, au-dessus de l'objectif de 200 Mo | `phonenumbers` embarque 46 Mo de données de géolocalisation et d'opérateurs inutiles ici ; `uvicorn[standard]` ajoute ~25 Mo ; `pip` et les `.pyc` restent dans l'image | `phonenumberslite` (même API), `uvicorn` simple, `pip install --no-compile` puis retrait de `pip`. Mesure : `du -sm` sur le venv avant et après. À confirmer par `docker images` |

<!-- Ajouter les pannes des projets 1 à 5 ici -->

| 4 | P0 | `docker compose up -d db` : `ports are not available ... bind: An attempt was made to access a socket in a way forbidden by its access permissions` | Sous Windows, le port hôte 5432 est dans une plage réservée (Hyper-V/WSL) ou pris par un Postgres local. Le conteneur n'y est pour rien | Port hôte rendu configurable : `POSTGRES_HOST_PORT` (défaut 5433), le port interne reste 5432. Diagnostic : `netsh interface ipv4 show excludedportrange protocol=tcp` |
