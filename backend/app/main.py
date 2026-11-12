import logging

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings
from app.errors import DomainError
from app.routers import admin, auth, claims, health, impact, listings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()

app = FastAPI(
    title="FoodBridge API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


# Endpoints d'exploitation à la racine (sondes K8s, scrape Prometheus).
app.include_router(health.router)

# API métier sous /api : l'Ingress route /api vers le backend sans réécriture d'URL.
api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(listings.router)
api.include_router(claims.router)
api.include_router(admin.router)
api.include_router(impact.router)
app.include_router(api)

Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)
