import sqlite3
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.db.schema import CREATE_DEALS_TABLE_SQL
from app.models.deal import Deal
from app.repositories.deals_repository import DealsRepository


class DealsSinglePassQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(CREATE_DEALS_TABLE_SQL)
        self.repository = DealsRepository()

    def tearDown(self) -> None:
        self.connection.close()

    def deal(self, deal_id: str, *, title: str, score: int, price: float = 10.0) -> Deal:
        return Deal(
            id=deal_id,
            title=title,
            description="Good product",
            image_url="https://example.test/image.jpg",
            platform="Store",
            category="Other",
            old_price=20.0,
            current_price=price,
            currency="USD",
            product_url=f"https://example.test/{deal_id}",
            affiliate_url=f"https://example.test/click/{deal_id}",
            provider_id="provider-a",
            monetization_mode="affiliate",
            rating=0,
            review_count=0,
            free_shipping=False,
            verified=False,
            ships_to=[],
            delivery_regions=[],
            hot_deal=False,
            lowest_price=False,
            deal_score=score,
            updated_at=datetime.now(timezone.utc),
            expires_at=None,
        )

    def test_total_and_page_are_returned_from_one_query_result(self) -> None:
        deals = [
            self.deal("duplicate-low", title="Same product", score=10),
            self.deal("duplicate-high", title="Same product", score=80),
            self.deal("unique", title="Different product", score=60, price=9.0),
        ]

        with patch(
            "app.repositories.deals_repository.get_connection",
            return_value=self.connection,
        ):
            self.repository.upsert_many(deals)
            rows, total = self.repository.query_deals(page=1, page_size=1)

        self.assertEqual(total, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].id, "duplicate-high")

    def test_page_beyond_end_keeps_total(self) -> None:
        deals = [self.deal("only", title="Only product", score=50)]

        with patch(
            "app.repositories.deals_repository.get_connection",
            return_value=self.connection,
        ):
            self.repository.upsert_many(deals)
            rows, total = self.repository.query_deals(page=2, page_size=20)

        self.assertEqual(rows, [])
        self.assertEqual(total, 1)


if __name__ == "__main__":
    unittest.main()
