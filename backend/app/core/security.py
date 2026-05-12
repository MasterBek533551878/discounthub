from typing import Annotated

from fastapi import Header, HTTPException, Query, status

from app.core.config import Settings, get_settings

DEFAULT_DEV_ADMIN_TOKEN = "dev-local-admin-token"


def require_admin_token(
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    token: Annotated[str | None, Query(description="Local admin token for Swagger testing.")] = None,
) -> None:
    settings = get_settings()
    expected_token = settings.admin_api_token.strip()
    provided_token = (x_admin_token or token or "").strip()

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_API_TOKEN is not configured.",
        )

    if provided_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token.",
        )


def validate_production_safety(settings: Settings | None = None) -> None:
    """Fail fast when production runs with unsafe local defaults."""
    settings = settings or get_settings()

    if not settings.enforce_production_safety:
        return

    if not settings.is_production:
        return

    errors: list[str] = []

    admin_token = settings.admin_api_token.strip()
    if not admin_token:
        errors.append("ADMIN_API_TOKEN must be configured in production.")
    elif admin_token == DEFAULT_DEV_ADMIN_TOKEN:
        errors.append("ADMIN_API_TOKEN still uses the local development token.")
    elif len(admin_token) < 32:
        errors.append("ADMIN_API_TOKEN should be at least 32 characters in production.")

    if settings.cors_origins.strip() == "*":
        errors.append("CORS_ORIGINS must not be '*' in production. Use your app/web domains.")

    if settings.admin_panel_enabled:
        errors.append("ADMIN_PANEL_ENABLED should be false in production.")

    if settings.docs_enabled or settings.openapi_enabled:
        errors.append("DOCS_ENABLED and OPENAPI_ENABLED should be false in production.")

    if errors:
        formatted_errors = "\n- ".join(errors)
        raise RuntimeError(
            "Unsafe DiscountHub production configuration:\n"
            f"- {formatted_errors}\n"
            "Fix .env before starting the production backend."
        )


def get_security_status() -> dict[str, object]:
    settings = get_settings()
    admin_token = settings.admin_api_token.strip()

    warnings: list[str] = []
    if settings.cors_origins.strip() == "*":
        warnings.append("CORS is open to all origins.")
    if admin_token == DEFAULT_DEV_ADMIN_TOKEN:
        warnings.append("Admin token is the local development token.")
    if settings.is_production and settings.admin_panel_enabled:
        warnings.append("Admin panel is enabled in production.")
    if settings.is_production and (settings.docs_enabled or settings.openapi_enabled):
        warnings.append("API docs or OpenAPI are enabled in production.")

    return {
        "environment": settings.environment,
        "production": settings.is_production,
        "enforceProductionSafety": settings.enforce_production_safety,
        "adminTokenConfigured": bool(admin_token),
        "adminTokenIsDevDefault": admin_token == DEFAULT_DEV_ADMIN_TOKEN,
        "adminPanelEnabled": settings.admin_panel_enabled,
        "docsEnabled": settings.docs_enabled,
        "openapiEnabled": settings.openapi_enabled,
        "corsOrigins": settings.cors_origin_list,
        "warnings": warnings,
        "status": "warning" if warnings else "ok",
    }
