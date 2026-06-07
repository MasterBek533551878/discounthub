from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "DiscountHub API"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: str = "*"
    database_path: str = "data/discounthub.sqlite3"
    admin_api_token: str = "dev-local-admin-token"

    # Production safety controls.
    # In production, keep admin panel and API docs disabled unless you explicitly need them.
    enforce_production_safety: bool = True
    admin_panel_enabled: bool = True
    docs_enabled: bool = True
    openapi_enabled: bool = True

    # Feed providers are the normal production source of deals.
    # Admin manual deal editing exists only for local testing and emergency corrections.
    auto_register_feed_providers: bool = True
    default_feed_providers_path: str = "config/feed_providers.json"
    default_feed_providers_json: str = ""

    # Enabled by default so the backend can refresh feeds automatically.
    feed_sync_scheduler_enabled: bool = True
    feed_sync_interval_seconds: int = 3600
    feed_sync_timeout_seconds: int = 20
    feed_sync_run_on_startup: bool = True

    # eBay Browse API adapter. Keep providers disabled until these values are configured.
    # The adapter uses OAuth client credentials to request an application access token.
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_scope: str = "https://api.ebay.com/oauth/api_scope"
    ebay_oauth_url: str = "https://api.ebay.com/identity/v1/oauth2/token"
    ebay_api_base_url: str = "https://api.ebay.com"
    ebay_default_marketplace_id: str = "EBAY_US"
    ebay_campaign_id: str = ""
    ebay_reference_id: str = "discounthub"

    # Awin product-feed integration. These values must stay server-side in backend/.env.
    # The feed-list provider imports products from joined advertisers and stores
    # advertiser names as normal marketplaces, so the mobile app filters update
    # automatically after every successful sync.
    awin_publisher_id: str = ""
    awin_datafeed_api_key: str = ""
    awin_feed_list_url: str = ""
    awin_feed_list_endpoint_template: str = "https://productdata.awin.com/datafeed/list/apikey/{api_key}"
    awin_feed_max_feeds: int = 20
    awin_feed_max_items_per_feed: int = 80
    awin_feed_min_discount_percent: int = 10

    # Awin Offers API / My Offers. This is separate from product feeds:
    # it imports store-level promotions and voucher codes into /promotions.
    # If AWIN_API_ACCESS_TOKEN is empty, the backend falls back to
    # AWIN_DATAFEED_API_KEY because some publisher accounts use the same
    # Toolbox token for API calls.
    awin_api_base_url: str = "https://api.awin.com"
    awin_api_access_token: str = ""

    # Mercado Libre direct marketplace adapter. Public search endpoints may be
    # blocked or require OAuth depending on site/account/app policy. Keep these
    # values empty until an official Mercado Libre developer app is configured.
    mercadolibre_access_token: str = ""

    # Admitad publisher API. These values must stay server-side in backend/.env.
    # Never put them into Flutter builds, APK/AAB/IPA, or public repository files.
    admitad_client_id: str = ""
    admitad_client_secret: str = ""
    admitad_website_id: str = ""
    admitad_api_base_url: str = "https://api.admitad.com"

    model_config = SettingsConfigDict(
        # Use the backend/.env file regardless of the shell working directory.
        # Windows PowerShell 5.1 can write UTF-8 files with BOM, so read with utf-8-sig.
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    @property
    def environment_key(self) -> str:
        return self.environment.strip().lower()

    @property
    def is_production(self) -> bool:
        return self.environment_key in {"production", "prod"}

    @property
    def is_production_like(self) -> bool:
        return self.environment_key in {"production", "prod", "staging", "stage"}

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def backend_root(self) -> Path:
        return BACKEND_ROOT

    @property
    def resolved_database_path(self) -> Path:
        path = Path(self.database_path)
        if path.is_absolute():
            return path
        return self.backend_root / path

    @property
    def resolved_default_feed_providers_path(self) -> Path:
        path = Path(self.default_feed_providers_path)
        if path.is_absolute():
            return path
        return self.backend_root / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
