CREATE_DEALS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    image_url TEXT NOT NULL,
    platform TEXT NOT NULL,
    category TEXT NOT NULL,
    old_price REAL NOT NULL,
    current_price REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    product_url TEXT NOT NULL,
    affiliate_url TEXT,
    provider_id TEXT,
    monetization_mode TEXT NOT NULL DEFAULT 'direct',
    rating REAL NOT NULL DEFAULT 0,
    review_count INTEGER NOT NULL DEFAULT 0,
    free_shipping INTEGER NOT NULL DEFAULT 0,
    verified INTEGER NOT NULL DEFAULT 0,
    ships_to TEXT NOT NULL DEFAULT '[]',
    hot_deal INTEGER NOT NULL DEFAULT 0,
    lowest_price INTEGER NOT NULL DEFAULT 0,
    deal_score INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    expires_at TEXT,
    public_platform TEXT NOT NULL DEFAULT '',
    discount_percent REAL NOT NULL DEFAULT 0,
    current_price_usd REAL NOT NULL DEFAULT 0,
    search_text TEXT NOT NULL DEFAULT ''
);
"""

CREATE_DEALS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_deals_platform ON deals(platform);",
    "CREATE INDEX IF NOT EXISTS idx_deals_category ON deals(category);",
    "CREATE INDEX IF NOT EXISTS idx_deals_currency ON deals(currency);",
    "CREATE INDEX IF NOT EXISTS idx_deals_provider_id ON deals(provider_id);",
    "CREATE INDEX IF NOT EXISTS idx_deals_monetization_mode ON deals(monetization_mode);",
    "CREATE INDEX IF NOT EXISTS idx_deals_discount ON deals(old_price, current_price);",
    "CREATE INDEX IF NOT EXISTS idx_deals_rating ON deals(rating);",
    "CREATE INDEX IF NOT EXISTS idx_deals_score ON deals(deal_score);",
    "CREATE INDEX IF NOT EXISTS idx_deals_updated_at ON deals(updated_at);",
    "CREATE INDEX IF NOT EXISTS idx_deals_public_platform ON deals(public_platform);",
    "CREATE INDEX IF NOT EXISTS idx_deals_public_platform_score ON deals(public_platform, deal_score DESC, updated_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_deals_category_score ON deals(category, deal_score DESC, updated_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_deals_discount_percent ON deals(discount_percent);",
    "CREATE INDEX IF NOT EXISTS idx_deals_current_price_usd ON deals(current_price_usd);",
    "CREATE INDEX IF NOT EXISTS idx_deals_search_text ON deals(search_text);",
]


CREATE_FEED_PROVIDERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS feed_providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    adapter TEXT NOT NULL DEFAULT 'auto',
    enabled INTEGER NOT NULL DEFAULT 1,
    replace_on_sync INTEGER NOT NULL DEFAULT 0,
    monetization_mode TEXT NOT NULL DEFAULT 'direct',
    last_sync_at TEXT,
    last_status TEXT,
    last_message TEXT,
    last_imported_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

CREATE_FEED_PROVIDERS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_feed_providers_enabled ON feed_providers(enabled);",
    "CREATE INDEX IF NOT EXISTS idx_feed_providers_adapter ON feed_providers(adapter);",
    "CREATE INDEX IF NOT EXISTS idx_feed_providers_monetization_mode ON feed_providers(monetization_mode);",
    "CREATE INDEX IF NOT EXISTS idx_feed_providers_updated_at ON feed_providers(updated_at);",
]


CREATE_FEED_SYNC_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS feed_sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT NOT NULL,
    provider_name TEXT,
    url TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    imported_count INTEGER NOT NULL DEFAULT 0,
    deal_count INTEGER,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""

CREATE_FEED_SYNC_RUNS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_feed_sync_runs_provider_id ON feed_sync_runs(provider_id);",
    "CREATE INDEX IF NOT EXISTS idx_feed_sync_runs_status ON feed_sync_runs(status);",
    "CREATE INDEX IF NOT EXISTS idx_feed_sync_runs_started_at ON feed_sync_runs(started_at);",
]


CREATE_CLICK_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS click_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    category TEXT NOT NULL,
    provider_id TEXT,
    monetization_mode TEXT NOT NULL DEFAULT 'direct',
    target_url TEXT NOT NULL,
    referrer TEXT,
    user_agent TEXT,
    ip_address TEXT,
    clicked_at TEXT NOT NULL
);
"""

CREATE_CLICK_EVENTS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_click_events_deal_id ON click_events(deal_id);",
    "CREATE INDEX IF NOT EXISTS idx_click_events_platform ON click_events(platform);",
    "CREATE INDEX IF NOT EXISTS idx_click_events_category ON click_events(category);",
    "CREATE INDEX IF NOT EXISTS idx_click_events_provider_id ON click_events(provider_id);",
    "CREATE INDEX IF NOT EXISTS idx_click_events_monetization_mode ON click_events(monetization_mode);",
    "CREATE INDEX IF NOT EXISTS idx_click_events_clicked_at ON click_events(clicked_at);",
]
