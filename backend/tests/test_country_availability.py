import sqlite3
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.db.database import (
    _backfill_deal_availability,
    _backfill_promotion_availability,
)
from app.db.schema import CREATE_DEALS_TABLE_SQL, CREATE_PROMOTIONS_TABLE_SQL
from app.models.deal import Deal
from app.models.promotion import Promotion
from app.repositories.deals_repository import DealsRepository
from app.repositories.promotions_repository import PromotionsRepository
from app.services.awin_offers_service import AwinOffersService
from app.services.country_availability import (
    infer_availability,
    normalize_availability,
    resolve_deal_availability,
)
from app.services.feed_adapters import FeedAdapterService


class CountryAvailabilityTests(unittest.TestCase):
    def test_common_awin_region_values_are_normalized(self) -> None:
        countries, is_global = normalize_availability(
            ["United States of America", "United Kingdom", "Brazil USD"]
        )
        self.assertEqual(countries, ["BR", "GB", "US"])
        self.assertFalse(is_global)

        europe, is_global = normalize_availability("Europe")
        self.assertIn("DE", europe)
        self.assertIn("GB", europe)
        self.assertFalse(is_global)

        countries, is_global = normalize_availability("Worldwide")
        self.assertEqual(countries, [])
        self.assertTrue(is_global)

    def test_market_specific_aliexpress_is_not_marked_global(self) -> None:
        countries, is_global = infer_availability(
            "AliExpress FR",
            "awin_feed_list",
            "https://www.aliexpress.com/item/123.html",
        )
        self.assertEqual(countries, ["FR"])
        self.assertFalse(is_global)

        countries, is_global = infer_availability(
            "AliExpress UK",
            "awin_feed_list",
        )
        self.assertEqual(countries, ["GB"])
        self.assertFalse(is_global)

        countries, is_global = infer_availability(
            "AliExpress",
            "awin_feed_list",
        )
        self.assertEqual(countries, [])
        self.assertTrue(is_global)

        countries, is_global = infer_availability("eBay IT")
        self.assertEqual(countries, ["IT"])
        self.assertFalse(is_global)

        countries, is_global = infer_availability("eBay ES")
        self.assertEqual(countries, ["ES"])
        self.assertFalse(is_global)

    def test_market_country_takes_precedence_over_legacy_shipping_list(self) -> None:
        countries, is_global = resolve_deal_availability(
            market_values=(
                "Aliexpress FR",
                "awin_feed_list",
                "https://www.aliexpress.com/item/123.html",
            ),
            shipping_values=["FR", "GB", "US", "PL", "DE"],
            delivery_region_values=["global", "europe", "usa"],
        )

        self.assertEqual(countries, ["FR"])
        self.assertFalse(is_global)

        countries, is_global = resolve_deal_availability(
            market_values=("eBay US", "ebay_us_v1"),
            shipping_values=["CA", "GB", "US"],
        )

        self.assertEqual(countries, ["US"])
        self.assertFalse(is_global)

    def test_platform_market_precedes_conflicting_provider_and_url_hints(self) -> None:
        countries, is_global = resolve_deal_availability(
            market_values=(
                "eBay GB",
                "ebay_us_legacy",
                "https://www.ebay.com/itm/123",
            ),
            shipping_values=["GB", "US"],
        )

        self.assertEqual(countries, ["GB"])
        self.assertFalse(is_global)

    def test_awin_product_feed_region_is_not_written_as_shipping_country(self) -> None:
        normalized = FeedAdapterService()._normalize_awin(
            {
                "aw_product_id": "sku-1",
                "product_name": "Test product",
                "description": "Test product description",
                "merchant_name": "Test Store",
                "merchant_product_url": "https://example.com/product",
                "aw_deep_link": "https://www.awin1.com/cread.php?ued=https%3A%2F%2Fexample.com%2Fproduct",
                "merchant_image_url": "https://example.com/image.jpg",
                "product_price": "100 USD",
                "sale_price": "80 USD",
                "_awin_feed_region": "United States of America",
            }
        )

        self.assertEqual(normalized["shipsTo"], [])
        self.assertEqual(normalized["availabilityCountries"], ["US"])
        self.assertFalse(normalized["isGlobal"])

    def test_deal_backfill_repairs_conflicting_market_mapping(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(CREATE_DEALS_TABLE_SQL)
        connection.execute(
            """
            INSERT INTO deals (
                id, title, description, image_url, platform, category,
                old_price, current_price, currency, product_url,
                affiliate_url, provider_id, availability_countries,
                is_global, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ebay-gb-conflict",
                "Deal",
                "Deal description",
                "https://example.test/image.jpg",
                "eBay GB",
                "Other",
                100.0,
                80.0,
                "GBP",
                "https://www.ebay.com/itm/123",
                "https://www.ebay.com/itm/123",
                "ebay_us_legacy",
                '["GB", "US"]',
                0,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        try:
            _backfill_deal_availability(connection)
            row = connection.execute(
                """
                SELECT availability_countries, is_global
                FROM deals
                WHERE id = 'ebay-gb-conflict'
                """
            ).fetchone()
        finally:
            connection.close()

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["availability_countries"], '["GB"]')
        self.assertEqual(row["is_global"], 0)

    def test_promotion_availability_backfill_runs_during_database_migration(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(CREATE_PROMOTIONS_TABLE_SQL)
        connection.execute(
            """
            INSERT INTO promotions (
                id, title, description, store, landing_url, provider_id, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "promotion-uk",
                "20% off",
                "United Kingdom offer",
                "Example UK",
                "https://example.co.uk/sale",
                "awin_offers_1",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        try:
            _backfill_promotion_availability(connection)
            row = connection.execute(
                """
                SELECT availability_countries, is_global
                FROM promotions
                WHERE id = 'promotion-uk'
                """
            ).fetchone()
        finally:
            connection.close()

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["availability_countries"], '["GB"]')
        self.assertEqual(row["is_global"], 0)

    def test_awin_promotion_region_codes_are_preserved(self) -> None:
        promotion = AwinOffersService()._item_to_promotion(
            {
                "promotionId": 123,
                "type": "voucher",
                "title": "20% off",
                "description": "Save 20% today",
                "url": "https://example.co.uk/sale",
                "urlTracking": "https://tracking.example/click",
                "regionCodes": ["GB"],
                "voucher": {"code": "SAVE20"},
                "advertiser": {"id": 456, "name": "Example UK"},
            }
        )

        self.assertIsNotNone(promotion)
        assert promotion is not None
        self.assertEqual(promotion.availability_countries, ["GB"])
        self.assertFalse(promotion.is_global)


class CountryRepositoryFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(CREATE_DEALS_TABLE_SQL)
        self.connection.execute(CREATE_PROMOTIONS_TABLE_SQL)

    def tearDown(self) -> None:
        self.connection.close()

    def _deal(self, deal_id: str, countries: list[str], *, is_global: bool = False) -> Deal:
        return Deal(
            id=deal_id,
            title=f"Deal {deal_id}",
            description="A real discounted product",
            image_url="https://example.test/image.jpg",
            platform="Store",
            category="Other",
            old_price=20,
            current_price=10,
            currency="USD",
            product_url=f"https://example.test/{deal_id}",
            affiliate_url=f"https://example.test/click/{deal_id}",
            provider_id="provider",
            monetization_mode="affiliate",
            rating=0,
            review_count=0,
            free_shipping=False,
            verified=True,
            ships_to=[],
            availability_countries=countries,
            is_global=is_global,
            delivery_regions=[],
            hot_deal=False,
            lowest_price=False,
            deal_score=50,
            updated_at=datetime.now(timezone.utc),
        )

    def _promotion(self, promotion_id: str, countries: list[str], *, is_global: bool = False) -> Promotion:
        return Promotion(
            id=promotion_id,
            type="coupon",
            title=f"Promotion {promotion_id}",
            description="Save 20%",
            store="Store",
            discount_text="20% off",
            code="SAVE20",
            landing_url=f"https://example.test/{promotion_id}",
            affiliate_url=f"https://example.test/click/{promotion_id}",
            provider_id="awin_offers_1",
            monetization_mode="affiliate",
            availability_countries=countries,
            is_global=is_global,
            updated_at=datetime.now(timezone.utc),
        )

    def test_deal_country_filter_includes_global_rows(self) -> None:
        repository = DealsRepository()
        with patch("app.repositories.deals_repository.get_connection", return_value=self.connection):
            repository.upsert_many(
                [
                    self._deal("us", ["US"]),
                    self._deal("gb", ["GB"]),
                    self._deal("global", [], is_global=True),
                ]
            )
            rows, total = repository.query_deals(country="US", page_size=20)
            facets = repository.get_facets()

        self.assertEqual(total, 2)
        self.assertEqual({row.id for row in rows}, {"us", "global"})
        counts = {item["id"]: item["count"] for item in facets["countries"]}
        self.assertEqual(counts["US"], 2)
        self.assertEqual(counts["GB"], 2)

    def test_promotion_country_filter_includes_global_rows(self) -> None:
        repository = PromotionsRepository()
        with patch("app.repositories.promotions_repository.get_connection", return_value=self.connection):
            repository.upsert_many(
                [
                    self._promotion("us", ["US"]),
                    self._promotion("gb", ["GB"]),
                    self._promotion("global", [], is_global=True),
                ]
            )
            rows, total = repository.query_promotions(country="GB", page_size=20)
            facets, global_count = repository.get_country_facets()

        self.assertEqual(total, 2)
        self.assertEqual({row.id for row in rows}, {"gb", "global"})
        self.assertEqual(global_count, 1)
        counts = {item["id"]: item["count"] for item in facets}
        self.assertEqual(counts["GB"], 2)
        self.assertEqual(counts["US"], 2)


if __name__ == "__main__":
    unittest.main()
