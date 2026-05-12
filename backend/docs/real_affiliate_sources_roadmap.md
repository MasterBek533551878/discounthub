# DiscountHub — real affiliate/source roadmap

This document describes the practical next step after local demo feeds: apply to official affiliate networks and marketplace APIs, receive official product feed/API URLs or credentials, map each source to a DiscountHub adapter, then let the backend scheduler import deals automatically.

## Important rule

Do not scrape marketplace websites. Use official APIs, affiliate product feeds, CSV/XML/JSON exports, or product catalog access from an approved partner account.

## Priority order

### 1. eBay Partner Network + eBay Browse API

Good first real integration because the Browse API can search items by keyword, category and item IDs. eBay Deal API exists but may require production access approval, so start with Browse API and affiliate links.

Recommended adapter path:

- New adapter: `ebay_browse_api`
- Data source type: API
- Required credentials: OAuth client credentials / access token setup
- Key mapping: title, image, price, original price if available, seller/rating if available, item URL, affiliate tracking URL

### 2. Awin product feeds

Good for many merchants because Awin provides product data feeds via downloaded CSV or Create-a-Feed.

Recommended adapter path:

- Existing adapter: `awin_products`
- Data source type: feed URL / CSV / JSON if converted
- Required credentials: Awin account and advertiser feed access

### 3. Rakuten Advertising Product Search API

Useful because Rakuten Advertising has an affiliate Product Search API that searches advertiser product feed data.

Recommended adapter path:

- New adapter: `rakuten_product_search`
- Data source type: API
- Required credentials: Rakuten Advertising API credentials

### 4. CJ Affiliate Product Feed API

CJ has a GraphQL Product Feed API for product information. This can be integrated after basic feed import is stable.

Recommended adapter path:

- New adapter: `cj_product_feed`
- Data source type: GraphQL API
- Required credentials: CJ API key / account access

### 5. Impact product catalogs

Impact supports product catalogs and product catalog downloads/API access for partners.

Recommended adapter path:

- New adapter: `impact_product_catalog`
- Data source type: API / catalog export
- Required credentials: Impact partner API access

### 6. Amazon Creators API

Amazon is important but should not be first. Product Advertising API documentation warns about migration to Creators API. Add after the product, legal text and affiliate compliance are stable.

Recommended adapter path:

- New adapter: `amazon_creators_api`
- Data source type: API
- Required credentials: Amazon affiliate/Creators API access

### 7. AliExpress affiliate/Open Platform

Useful for global low-cost shopping. Access and documentation vary by regional portal, so connect only through official partner/API access.

Recommended adapter path:

- New adapter: `aliexpress_affiliate_api`
- Data source type: API
- Required credentials: app key, app secret, tracking ID / affiliate params

## Application checklist

For every provider, collect:

- Provider name
- Official sign-up URL
- API/product feed docs URL
- Account email
- Approval status
- Feed/API URL
- Required auth method
- Allowed regions/countries
- Terms for displaying prices/images
- Affiliate tracking parameters
- Rate limits
- Data refresh interval
- Required disclosure text

## Production note

The current admin panel is only for control and debugging. Final data flow must remain automatic:

Official provider feed/API -> adapter -> scheduler -> SQLite/PostgreSQL -> mobile app.
