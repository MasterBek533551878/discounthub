import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError

from app.core.ai_config import AiSettings
from app.models.ai_assistant import AiChatHistoryItem
from app.services.ai_assistant_service import AiAssistantService, SearchIntent


class ShoppingContextTests(unittest.TestCase):
    def setUp(self):
        self.service = AiAssistantService()
        self.settings = AiSettings(_env_file=None, gemini_api_key="")
        self.settings_patch = patch("app.services.ai_assistant_service.get_ai_settings", return_value=self.settings)
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def history(self, *texts):
        return [AiChatHistoryItem(role="user", content=text) for text in texts]

    def test_product_request_searches_without_optional_questions(self):
        for message in ("I need notebook for job", "I need a noutbook for work", "ноутбуки", "ноутки"):
            with self.subTest(message=message), patch.object(self.service, "_deals", return_value=[]) as search:
                _, clarify, _, _, provider = self.service.find_offers(message=message, history=[])
                self.assertFalse(clarify)
                self.assertEqual(provider, "local_fallback")
                intent, query = search.call_args.args
                self.assertEqual(query, "laptop")
                self.assertEqual((intent.max_price, intent.min_discount, intent.country), (0, 1, ""))

    def test_budget_and_cheaper_followups_preserve_subject(self):
        history = self.history("ноутбуки до 700", "до 500")
        history.append(AiChatHistoryItem(role="assistant", content="Нужна скидка 50%? Только США?"))
        intent = self.service._fallback_intent("дешевле", history)
        self.assertEqual((intent.query, intent.max_price, intent.sort), ("laptop", 500, "price_asc"))
        self.assertEqual((intent.country, intent.min_discount), ("", 1))
        self.assertFalse(intent.needs_clarification)

    def test_new_product_drops_previous_product_filters(self):
        intent = self.service._fallback_intent("наушники", self.history("ноутбуки до 700 от 30% на ebay us"))
        self.assertEqual((intent.query, intent.platform, intent.max_price, intent.min_discount), ("headphones", "", 0, 1))

    def test_filter_can_be_removed_without_losing_subject(self):
        intent = self.service._fallback_intent("любой бюджет", self.history("ноутбуки до 700"))
        self.assertEqual((intent.query, intent.max_price), ("laptop", 0))
        self.assertFalse(intent.needs_clarification)

    def test_example_chip_extracts_budget_and_sort(self):
        intent = self.service._fallback_intent("Find wireless headphones under $50 with the biggest discount")
        self.assertEqual((intent.query, intent.max_price, intent.sort), ("wireless headphones", 50, "discount_desc"))

    def test_broad_promos_keep_empty_query(self):
        with patch.object(self.service, "_promotions", return_value=[]) as promos, patch.object(self.service, "_deals") as deals:
            _, clarify, *_ = self.service.find_offers(message="Show me useful promo codes for online shopping", history=[])
        self.assertFalse(clarify)
        self.assertEqual(promos.call_args.args[1], "")
        deals.assert_not_called()

    def test_model_cannot_block_a_product_on_optional_preferences(self):
        model = SearchIntent(needs_clarification=True, clarifying_question="What minimum discount?")
        with patch.object(self.service, "_extract_intent", return_value=(model, "gemini")), patch.object(self.service, "_deals", return_value=[]) as search:
            _, clarify, *_ = self.service.find_offers(message="ноутки", history=[])
        self.assertFalse(clarify)
        self.assertEqual(search.call_args.args[1], "laptop")

    def test_greeting_still_asks_for_subject_only(self):
        with patch.object(self.service, "_deals") as search:
            reply, clarify, *_ = self.service.find_offers(message="привет", history=[])
        self.assertTrue(clarify)
        self.assertEqual(reply, "Какой товар или промокод найти?")
        search.assert_not_called()

    def test_provider_failure_retains_user_history(self):
        self.settings.gemini_api_key = "test-only"
        with patch("app.services.ai_assistant_service.urllib_request.urlopen", side_effect=URLError("offline")):
            intent, provider = self.service._extract_intent("under $500", self.history("laptops"))
        self.assertEqual(provider, "local_fallback")
        self.assertEqual((intent.query, intent.max_price), ("laptop", 500))

    def test_model_response_empty_query_is_not_replaced_by_sentence(self):
        model = SearchIntent(query="", platform="AliExpress PL", include_deals=False, include_partner_offers=False)
        with patch.object(self.service, "_extract_intent", return_value=(model, "gemini")), patch.object(self.service, "_promotions", return_value=[]) as promos:
            self.service.find_offers(message="promo codes for AliExpress PL", history=[])
        self.assertEqual(promos.call_args.args[1], "")

    def test_normal_provider_response_and_history_contract(self):
        self.settings.gemini_api_key = "test-only"
        body = {"candidates": [{"content": {"parts": [{"text": json.dumps(SearchIntent(query="laptop", max_price=500).model_dump())}]}}]}
        with patch("app.services.ai_assistant_service.urllib_request.urlopen") as request:
            request.return_value.__enter__.return_value.read.return_value = json.dumps(body).encode()
            intent, provider = self.service._extract_intent("under $500", self.history("laptops"))
            prompt = json.loads(request.call_args.args[0].data)["contents"][0]["parts"][0]["text"]
        self.assertEqual(provider, "gemini")
        self.assertEqual((intent.query, intent.max_price), ("laptop", 500))
        self.assertIn("user: laptops", prompt)

    def test_catalogue_calls_use_country_and_keep_discount_floor(self):
        with patch("app.services.ai_assistant_service.deals_service.list_deals", return_value=([], 0)) as deals:
            self.service._deals(SearchIntent(country="US"), "headphones")
        self.assertEqual(deals.call_args.kwargs["country"], "US")
        self.assertIsNone(deals.call_args.kwargs["ships_to"])
        self.assertEqual(deals.call_args.kwargs["min_discount"], 1)
        with patch("app.services.ai_assistant_service.promotions_service.list_promotions", return_value=([], 0)) as promos:
            self.service._promotions(SearchIntent(country="PL"), "")
        self.assertEqual(promos.call_args.kwargs["country"], "PL")
        self.assertIsNone(promos.call_args.kwargs["q"])

    def offer(self, title, price):
        return SimpleNamespace(id=title, title=title, platform="Store", description="", discount_percent=20,
                               current_price=price, old_price=price * 1.25, currency="USD", image_url="")

    def test_cheaper_laptops_exclude_peripherals_without_price_floor(self):
        rows = [self.offer("2 in 1 USB Card Reader for PC Laptop", 2),
                self.offer("16 inch Portable Monitor for Laptop PC", 80),
                self.offer("HP Probook Laptop 8GB RAM Intel i5 Windows", 101),
                self.offer("Windows 7 Laptop Notebook PC Dual core 4GB RAM", 104),
                self.offer("Lenovo 300e Chromebook 4GB 32GB", 105)]
        with patch("app.services.ai_assistant_service.deals_service.list_deals", return_value=(rows, len(rows))) as search:
            cards = self.service._deals(SearchIntent(sort="price_asc", max_price=500), "laptop")
        self.assertEqual([x.current_price for x in cards], [101, 104, 105])
        self.assertEqual(search.call_args.kwargs["category"], "Computers")
        self.assertEqual(search.call_args.kwargs["max_price"], 500)
        self.assertEqual(search.call_args.kwargs["sort"], "price_asc")

    def test_laptop_search_continues_past_accessory_only_page(self):
        accessory = self.offer("Laptop Stand Adjustable Holder", 5)
        laptop = self.offer("Dell Latitude Laptop 16GB RAM 512GB SSD", 110)
        with patch("app.services.ai_assistant_service.deals_service.list_deals", side_effect=[([accessory] * 24, 25), ([laptop], 25)]) as search:
            cards = self.service._deals(SearchIntent(sort="price_asc"), "laptop")
        self.assertEqual([x.title for x in cards], [laptop.title])
        self.assertEqual([x.kwargs["page"] for x in search.call_args_list], [1, 2])

    def test_explicit_laptop_accessories_still_search_normally(self):
        accessory = self.offer("USB C Charger for Laptop", 9)
        with patch("app.services.ai_assistant_service.deals_service.list_deals", return_value=([accessory], 1)) as search:
            cards = self.service._deals(SearchIntent(sort="price_asc"), "laptop charger")
        self.assertEqual([x.title for x in cards], [accessory.title])
        self.assertIsNone(search.call_args.kwargs["category"])
        self.assertTrue(self.service._wants_laptop("laptop 16GB RAM"))
        self.assertTrue(self.service._is_laptop_title("Dell Latitude Laptop 16GB RAM 512GB SSD for work"))


if __name__ == "__main__":
    unittest.main()
