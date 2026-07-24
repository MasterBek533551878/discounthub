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
    availability_countries TEXT NOT NULL DEFAULT '[]',
    is_global INTEGER NOT NULL DEFAULT 0,
    delivery_regions TEXT NOT NULL DEFAULT '[]',
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
    "CREATE INDEX IF NOT EXISTS idx_deals_availability_countries ON deals(availability_countries);",
    "CREATE INDEX IF NOT EXISTS idx_deals_is_global ON deals(is_global);",
    "CREATE INDEX IF NOT EXISTS idx_deals_delivery_regions ON deals(delivery_regions);",
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


CREATE_PROMOTIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS promotions (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL DEFAULT 'sale',
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    store TEXT NOT NULL,
    discount_text TEXT NOT NULL DEFAULT '',
    code TEXT,
    landing_url TEXT NOT NULL,
    affiliate_url TEXT,
    image_url TEXT,
    provider_id TEXT,
    monetization_mode TEXT NOT NULL DEFAULT 'affiliate',
    availability_countries TEXT NOT NULL DEFAULT '[]',
    is_global INTEGER NOT NULL DEFAULT 0,
    valid_from TEXT,
    valid_until TEXT,
    featured INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    search_text TEXT NOT NULL DEFAULT ''
);
"""

CREATE_PROMOTIONS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_promotions_type ON promotions(type);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_store ON promotions(store);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_provider_id ON promotions(provider_id);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_monetization_mode ON promotions(monetization_mode);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_availability_countries ON promotions(availability_countries);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_is_global ON promotions(is_global);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_valid_until ON promotions(valid_until);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_featured ON promotions(featured);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_updated_at ON promotions(updated_at);",
    "CREATE INDEX IF NOT EXISTS idx_promotions_search_text ON promotions(search_text);",
]


CREATE_PROMOTION_CLICK_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS promotion_click_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    promotion_id TEXT NOT NULL,
    store TEXT NOT NULL,
    type TEXT NOT NULL,
    provider_id TEXT,
    monetization_mode TEXT NOT NULL DEFAULT 'affiliate',
    target_url TEXT NOT NULL,
    referrer TEXT,
    user_agent TEXT,
    ip_address TEXT,
    clicked_at TEXT NOT NULL
);
"""

CREATE_PROMOTION_CLICK_EVENTS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_promotion_click_events_promotion_id ON promotion_click_events(promotion_id);",
    "CREATE INDEX IF NOT EXISTS idx_promotion_click_events_store ON promotion_click_events(store);",
    "CREATE INDEX IF NOT EXISTS idx_promotion_click_events_type ON promotion_click_events(type);",
    "CREATE INDEX IF NOT EXISTS idx_promotion_click_events_provider_id ON promotion_click_events(provider_id);",
    "CREATE INDEX IF NOT EXISTS idx_promotion_click_events_clicked_at ON promotion_click_events(clicked_at);",
]



CREATE_PARTNER_OFFERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS partner_offers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    partner_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'other',
    tags TEXT NOT NULL DEFAULT '[]',
    offer_text TEXT NOT NULL DEFAULT '',
    original_price_text TEXT NOT NULL DEFAULT '',
    current_price_text TEXT NOT NULL DEFAULT '',
    code TEXT,
    landing_url TEXT NOT NULL,
    checkout_url TEXT,
    image_url TEXT,
    logo_url TEXT,
    countries TEXT NOT NULL DEFAULT 'Global',
    monetization_mode TEXT NOT NULL DEFAULT 'direct',
    valid_from TEXT,
    valid_until TEXT,
    featured INTEGER NOT NULL DEFAULT 0,
    verified INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    search_text TEXT NOT NULL DEFAULT ''
);
"""

CREATE_PARTNER_OFFERS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_partner_offers_partner_name ON partner_offers(partner_name);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offers_category ON partner_offers(category);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offers_monetization_mode ON partner_offers(monetization_mode);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offers_valid_until ON partner_offers(valid_until);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offers_featured ON partner_offers(featured);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offers_verified ON partner_offers(verified);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offers_updated_at ON partner_offers(updated_at);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offers_search_text ON partner_offers(search_text);",
]


CREATE_PARTNER_OFFER_CLICK_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS partner_offer_click_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    partner_name TEXT NOT NULL,
    category TEXT NOT NULL,
    monetization_mode TEXT NOT NULL DEFAULT 'direct',
    target_url TEXT NOT NULL,
    referrer TEXT,
    user_agent TEXT,
    ip_address TEXT,
    clicked_at TEXT NOT NULL
);
"""

CREATE_PARTNER_OFFER_CLICK_EVENTS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_partner_offer_click_events_offer_id ON partner_offer_click_events(offer_id);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offer_click_events_partner_name ON partner_offer_click_events(partner_name);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offer_click_events_category ON partner_offer_click_events(category);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offer_click_events_monetization_mode ON partner_offer_click_events(monetization_mode);",
    "CREATE INDEX IF NOT EXISTS idx_partner_offer_click_events_clicked_at ON partner_offer_click_events(clicked_at);",
]
