import sys
import types
import unittest
from datetime import datetime, timezone

# The sanitized production export intentionally omitted runtime data directories,
# including app/data/mock_deals.py. Stub only that development fixture so the
# production service module can be imported for this isolated unit test.
app_data = types.ModuleType("app.data")
mock_deals = types.ModuleType("app.data.mock_deals")
mock_deals.MOCK_DEALS = []
sys.modules.setdefault("app.data", app_data)
sys.modules.setdefault("app.data.mock_deals", mock_deals)

from app.models.deal import DealUpsertRequest
from app.services.deals_service import DealsService


class FakeDealsRepository:
    def __init__(self) -> None:
        self.deleted_provider_ids: list[str] = []
        self.delete_all_calls = 0
        self.upserted = []

    def delete_provider_deals(self, *, provider_id: str) -> int:
        self.deleted_provider_ids.append(provider_id)
        return 2

    def delete_all(self) -> int:
        self.delete_all_calls += 1
        return 99

    def upsert_many(self, deals) -> None:
        self.upserted.extend(list(deals))


class ProviderScopedReplaceTests(unittest.TestCase):
    def payload(self) -> DealUpsertRequest:
        return DealUpsertRequest(
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
            updated_at=datetime.now(timezone.utc),
        )

    def test_provider_replace_never_deletes_full_catalogue(self) -> None:
        repository = FakeDealsRepository()
        service = DealsService(repository=repository)

        imported = service.import_provider_deals(
            [self.payload()],
            provider_id="provider-a",
            replace=True,
        )

        self.assertEqual(imported, 1)
        self.assertEqual(repository.deleted_provider_ids, ["provider-a"])
        self.assertEqual(repository.delete_all_calls, 0)
        self.assertEqual(len(repository.upserted), 1)


if __name__ == "__main__":
    unittest.main()
