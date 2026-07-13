import sqlite3
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.db.schema import CREATE_DEALS_TABLE_SQL
from app.models.deal import Deal
from app.repositories.deals_repository import DealsRepository


class FacetsNarrowTempTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(CREATE_DEALS_TABLE_SQL)
        self.repository = DealsRepository()

    def tearDown(self) -> None:
        self.connection.close()

    def deal(self, deal_id: str, *, title: str, score: int) -> Deal:
        return Deal(
            id=deal_id,
            title=title,
            description="x" * 100_000,
            image_url="https://example.test/" + ("image" * 1000),
            platform="Store",
            category="Other",
            old_price=20.0,
            current_price=10.0,
            currency="USD",
            product_url=f"https://example.test/{deal_id}",
            affiliate_url=f"https://example.test/click/{deal_id}",
            provider_id="provider-a",
            monetization_mode="affiliate",
            rating=0,
            review_count=0,
            free_shipping=False,
            verified=False,
            ships_to=["US"],
            delivery_regions=["global"],
            hot_deal=False,
            lowest_price=False,
            deal_score=score,
            updated_at=datetime.now(timezone.utc),
            expires_at=None,
        )

    def test_facets_keep_dedupe_semantics_without_copying_large_columns(self) -> None:
        deals = [
            self.deal("duplicate-low", title="Same product", score=10),
            self.deal("duplicate-high", title="Same product", score=90),
            self.deal("unique", title="Different product", score=60),
        ]

        with patch(
            "app.repositories.deals_repository.get_connection",
            return_value=self.connection,
        ):
            self.repository.upsert_many(deals)
            facets = self.repository.get_facets()

        columns = {
            str(row[1])
            for row in self.connection.execute(
                "PRAGMA table_info(temp_facet_deals)"
            ).fetchall()
        }

        self.assertEqual(facets["total"], 2)
        self.assertEqual(facets["marketplaces"][0]["count"], 2)
        self.assertIn("current_price_usd", columns)
        self.assertIn("delivery_regions", columns)
        self.assertNotIn("description", columns)
        self.assertNotIn("image_url", columns)
        self.assertNotIn("affiliate_url", columns)


if __name__ == "__main__":
    unittest.main()
