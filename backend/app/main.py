from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin,
    admin_panel,
    deals,
    feed_providers,
    partner_offers,
    promotions,
    health,
    security_status,
    settings as settings_routes,
    storage,
)
from app.core.config import get_settings
from app.core.security import validate_production_safety
from app.db.database import initialize_database
from app.services.default_feed_providers import default_feed_providers_service
from app.services.feed_sync_scheduler import feed_sync_scheduler
from app.services.promotion_cleanup_service import promotion_cleanup_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    validate_production_safety(settings)
    initialize_database()
    promotion_cleanup_service.cleanup_promotions()
    default_feed_providers_service.ensure_configured_providers()
    if settings.feed_sync_scheduler_enabled:
        await feed_sync_scheduler.start()
    yield
    await feed_sync_scheduler.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DiscountHub MVP API. Shows global marketplace deals and discount filters.",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.openapi_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(deals.router)
app.include_router(promotions.router)
app.include_router(partner_offers.router)
app.include_router(settings_routes.router)
app.include_router(storage.router)
app.include_router(security_status.router)
app.include_router(admin.router)
app.include_router(feed_providers.router)
app.include_router(admin_panel.router)


@app.get("/")
def root() -> dict[str, str | None]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.docs_enabled else None,
    }
