import io
import unittest

from app.services.awin_feed_list_service import AwinFeedListService
from app.services.feed_adapters import FeedAdapterService


class AwinFeedScanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AwinFeedListService()

    @staticmethod
    def csv_row(index: int, *, discounted: bool) -> str:
        current = "50.00" if discounted else "100.00"
        old = "100.00"
        return (
            f'{index},"Product {index}",https://example.test/p/{index},'
            f'https://example.test/i/{index}.jpg,{current},{old},in stock\n'
        )

    def test_streaming_scan_can_find_discount_after_first_500_rows(self) -> None:
        header = "aw_product_id,product_name,merchant_product_url,merchant_image_url,product_price,product_price_old,availability\n"
        rows = [self.csv_row(index, discounted=index == 650) for index in range(1, 701)]
        filtered, stats = self.service._extract_filtered_delimited_stream(
            io.StringIO(header + "".join(rows)),
            feed_url="https://example.test/products.csv",
            content_type="text/csv",
            max_items=500,
            max_scan_rows=700,
            min_discount_percent=1,
        )

        self.assertEqual(stats["rows"], 700)
        self.assertEqual(stats["passed"], 1)
        self.assertEqual(filtered[0]["aw_product_id"], "650")

    def test_price_parser_supports_common_us_and_eu_formats(self) -> None:
        self.assertEqual(self.service._parse_number_text("£1,299.99"), 1299.99)
        self.assertEqual(self.service._parse_number_text("1.299,99 €"), 1299.99)
        self.assertEqual(self.service._parse_number_text("1 299,99 PLN"), 1299.99)

    def test_additional_awin_price_aliases_form_discount_pair(self) -> None:
        current, old = self.service._awin_price_pair(
            {
                "special_price": "79,99 EUR",
                "recommended_retail_price": "99,99 EUR",
            }
        )
        self.assertAlmostEqual(current or 0, 79.99)
        self.assertAlmostEqual(old or 0, 99.99)

    def test_awin_normalizer_uses_same_price_aliases_and_currency(self) -> None:
        adapter = FeedAdapterService()
        normalized = adapter.normalize_items(
            adapter="awin_products",
            raw_items=[
                {
                    "aw_product_id": "abc",
                    "product_name": "Alias product",
                    "merchant_product_url": "https://example.test/product",
                    "aw_deep_link": "https://example.test/click",
                    "merchant_image_url": "https://example.test/image.jpg",
                    "special_price": "79,99 EUR",
                    "recommended_retail_price": "99,99 EUR",
                    "_awin_advertiser_id": "123",
                    "_awin_advertiser_name": "Store",
                }
            ],
        )[0]

        self.assertEqual(normalized["currentPrice"], 79.99)
        self.assertEqual(normalized["oldPrice"], 99.99)
        self.assertEqual(normalized["currency"], "EUR")

    def test_ttfone_resale_products_are_allowed_but_known_404_is_blocked(self) -> None:
        for title in (
            "Returned Resale - TTfone TT240",
            "Return Resale - TTfone TT150",
            "TTfone TT240 Brand New",
        ):
            self.assertFalse(
                self.service._is_blocked_awin_product(
                    {
                        "_awin_advertiser_id": "28737",
                        "aw_product_id": "valid-live-product",
                        "product_name": title,
                    }
                )
            )

        self.assertTrue(
            self.service._is_blocked_awin_product(
                {
                    "_awin_advertiser_id": "28737",
                    "aw_product_id": "42338245511",
                    "product_name": "Confirmed broken TTfone product",
                }
            )
        )

    def test_ttfone_currency_fallback_respects_eu_feed(self) -> None:
        adapter = FeedAdapterService()
        base = {
            "aw_product_id": "abc",
            "product_name": "TTfone product",
            "merchant_product_url": "https://www.ttfone.com/product",
            "aw_deep_link": "https://example.test/click",
            "merchant_image_url": "https://example.test/image.jpg",
            "search_price": "19.99",
            "rrp_price": "39.99",
            "_awin_advertiser_id": "28737",
            "_awin_advertiser_name": "TTfone",
        }
        uk = adapter.normalize_items(adapter="awin_products", raw_items=[dict(base, _awin_feed_name="Shopify")])[0]
        eu = adapter.normalize_items(adapter="awin_products", raw_items=[dict(base, _awin_feed_name="Shopify EU")])[0]

        self.assertEqual(uk["currency"], "GBP")
        self.assertEqual(eu["currency"], "EUR")

    def test_zero_quantity_is_out_of_stock(self) -> None:
        self.assertTrue(self.service._is_out_of_stock({"stock_quantity": "0"}))
        self.assertFalse(self.service._is_out_of_stock({"stock_quantity": "12", "availability": "in stock"}))


if __name__ == "__main__":
    unittest.main()
