import unittest
from datetime import datetime, timezone

from app.models.deal import Deal
from app.services.deals_service import DealsService


class FakeRepository:
    def __init__(self) -> None:
        self.query_calls = 0
        self.facets_calls = 0
        self.upserted = []

    def query_deals(self, **kwargs):
        self.query_calls += 1
        return [
            Deal(
                id="deal-1",
                title="Deal",
                description="Deal",
                image_url="https://example.test/image.jpg",
                platform="Store",
                category="Other",
                old_price=20,
                current_price=10,
                currency="USD",
                product_url="https://example.test/product",
                affiliate_url="https://example.test/click",
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
                deal_score=50,
                updated_at=datetime.now(timezone.utc),
                expires_at=None,
            )
        ], 1

    def upsert_many(self, deals):
        self.upserted.extend(list(deals))

    def get_facets(self, **kwargs):
        self.facets_calls += 1
        return {
            "total": 1,
            "marketplaces": [{"id": "Store", "name": "Store", "count": 1}],
            "categories": [{"id": "Other", "name": "Other", "count": 1}],
            "shipping_countries": [],
            "delivery_regions": [],
            "currencies": [{"id": "USD", "name": "USD", "count": 1}],
            "monetization_modes": [
                {"id": "affiliate", "name": "affiliate", "count": 1}
            ],
            "min_price_usd": 10.0,
            "max_price_usd": 20.0,
            "min_discount": 10,
            "max_discount": 50,
        }


class DealsCacheTests(unittest.TestCase):
    def test_identical_list_request_uses_cache(self) -> None:
        repository = FakeRepository()
        service = DealsService(repository=repository)

        first_items, first_total = service.list_deals(platform="Store")
        second_items, second_total = service.list_deals(platform="Store")

        self.assertEqual(repository.query_calls, 1)
        self.assertEqual(first_total, 1)
        self.assertEqual(second_total, 1)
        self.assertEqual(first_items[0].id, second_items[0].id)

    def test_different_page_has_different_cache_key(self) -> None:
        repository = FakeRepository()
        service = DealsService(repository=repository)

        service.list_deals(platform="Store", page=1)
        service.list_deals(platform="Store", page=2)

        self.assertEqual(repository.query_calls, 2)


    def test_facets_share_raw_database_result_across_currencies(self) -> None:
        repository = FakeRepository()
        service = DealsService(repository=repository)

        gbp = service.get_facets(platform="Store", currency="GBP")
        eur = service.get_facets(platform="Store", currency="EUR")

        self.assertEqual(repository.facets_calls, 1)
        self.assertEqual(gbp.price_range.currency, "GBP")
        self.assertEqual(eur.price_range.currency, "EUR")
        self.assertNotEqual(gbp.price_range.min, eur.price_range.min)


if __name__ == "__main__":
    unittest.main()
