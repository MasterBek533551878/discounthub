from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.core.config import get_settings
from app.models.feed_provider import FeedProviderUpsertRequest
from app.services.feed_providers_service import feed_providers_service


class DefaultFeedProvidersError(Exception):
    pass


class DefaultFeedProvidersService:
    """Registers configured feed providers automatically on backend startup.

    Production flow:
      official/affiliate feed URLs -> saved provider registry -> scheduler -> database -> app.

    Manual admin product creation is intentionally not part of the normal flow.
    It is only a local/testing/emergency tool.
    """

    def ensure_configured_providers(self) -> dict[str, object]:
        settings = get_settings()
        if not settings.auto_register_feed_providers:
            return {
                "status": "disabled",
                "message": "AUTO_REGISTER_FEED_PROVIDERS is disabled.",
                "registeredCount": 0,
            }

        providers = self._load_configured_providers()
        if not providers:
            return {
                "status": "skipped",
                "message": "No configured feed providers found.",
                "registeredCount": 0,
            }

        registered_count = 0
        errors: list[str] = []

        for raw_provider in providers:
            try:
                payload = FeedProviderUpsertRequest.model_validate(raw_provider)
                feed_providers_service.upsert_provider(payload)
                registered_count += 1
            except (ValidationError, ValueError, TypeError) as exc:
                provider_id = raw_provider.get("id", "unknown") if isinstance(raw_provider, dict) else "unknown"
                errors.append(f"{provider_id}: {exc}")

        if errors:
            return {
                "status": "partial",
                "message": "Some feed providers could not be registered: " + "; ".join(errors[:3]),
                "registeredCount": registered_count,
            }

        return {
            "status": "ok",
            "message": f"Registered/updated {registered_count} configured feed provider(s).",
            "registeredCount": registered_count,
        }

    def _load_configured_providers(self) -> list[dict[str, Any]]:
        settings = get_settings()

        if settings.default_feed_providers_json.strip():
            loaded = self._load_json(settings.default_feed_providers_json)
            return self._extract_provider_list(loaded)

        config_path = settings.resolved_default_feed_providers_path
        if not config_path.exists():
            return []

        loaded = self._load_json(config_path.read_text(encoding="utf-8-sig"))
        return self._extract_provider_list(loaded)

    def _load_json(self, raw_json: str) -> Any:
        # PowerShell 5.1 Set-Content -Encoding UTF8 writes a UTF-8 BOM.
        # json.loads() does not accept BOM, so strip it before parsing.
        return json.loads(raw_json.lstrip("\ufeff"))

    def _extract_provider_list(self, loaded: Any) -> list[dict[str, Any]]:
        """Extract provider objects from current and legacy config shapes.

        The intended config shape is a flat array of provider objects:
          [{"id": "demo_feed", ...}, {"id": "ebay_browse_headphones", ...}]

        Some earlier PowerShell/script flows could leave a legacy mixed shape:
          [{"providers": [{...}]}, {"id": "ebay_browse_headphones", ...}]

        Accept both so startup never breaks because of an older local config.
        """
        if isinstance(loaded, list):
            candidates = loaded
        elif isinstance(loaded, dict):
            providers = loaded.get("providers")
            if not isinstance(providers, list):
                raise DefaultFeedProvidersError("Feed provider config providers must be an array.")
            candidates = providers
        else:
            raise DefaultFeedProvidersError("Feed provider config must be a JSON array or an object with providers array.")

        result: list[dict[str, Any]] = []
        for item in candidates:
            if not isinstance(item, dict):
                raise DefaultFeedProvidersError("Every feed provider must be a JSON object.")

            nested_providers = item.get("providers")
            if "id" not in item and isinstance(nested_providers, list):
                for nested_item in nested_providers:
                    if not isinstance(nested_item, dict):
                        raise DefaultFeedProvidersError("Every nested feed provider must be a JSON object.")
                    result.append(nested_item)
                continue

            result.append(item)

        return result


default_feed_providers_service = DefaultFeedProvidersService()
