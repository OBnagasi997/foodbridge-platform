.PHONY: create-admin expire init dev-up dev-down logs test test-backend test-frontend lint migrate revision

init:            ## Crée .env à partir de .env.example
	@test -f .env || cp .env.example .env && echo ".env prêt"

dev-up:          ## Lance db + migrations + backend + frontend
	docker compose up --build -d
	@echo "Frontend : http://localhost:8080  |  API docs : http://localhost:8000/api/docs"

dev-down:        ## Arrête tout (garde les données). Ajouter -v pour effacer la base.
	docker compose down

logs:
	docker compose logs -f --tail=100

test-backend:    ## Tests sur un vrai Postgres (db doit tourner)
	-docker compose up -d db
	-docker compose exec -T db createdb -U foodbridge foodbridge_test
	cd backend && pytest -q

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run typecheck

migrate:         ## Applique les migrations sur la base locale
	cd backend && alembic upgrade head

revision:        ## Nouvelle migration : make revision m="ajoute X"
	cd backend && alembic revision --autogenerate -m "$(m)"

create-admin:    ## Crée un compte admin : make create-admin email=moi@exemple.org
	cd backend && python -m app.cli create-admin --email "$(email)"

expire:          ## Lance le job d'expiration des annonces (futur CronJob K8s)
	cd backend && python -m app.jobs.expire_listings
