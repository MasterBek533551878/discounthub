import unittest

from app.services.awin_feed_list_service import AwinFeedListOptions, AwinFeedListService


class AwinFeedSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AwinFeedListService()

    @staticmethod
    def row(advertiser_id: str, advertiser_name: str, feed_name: str, suffix: str) -> dict[str, str]:
        return {
            "advertiser_id": advertiser_id,
            "advertiser_name": advertiser_name,
            "feed_name": feed_name,
            "download_url": f"https://example.test/{suffix}.csv",
            "status": "joined",
        }

    def options(self, **overrides: object) -> AwinFeedListOptions:
        values = {
            "max_feeds": 5,
            "max_feeds_per_advertiser": 5,
            "max_items_per_feed": 500,
            "max_scan_rows_per_feed": 25000,
            "min_discount_percent": 1,
            "joined_only": True,
            "advertiser_id": "",
            "advertiser_name": "",
            "excluded_advertiser_ids": (),
        }
        values.update(overrides)
        return AwinFeedListOptions(**values)

    def test_general_provider_covers_each_advertiser_before_duplicates(self) -> None:
        rows = [
            self.row("1", "Large Store", "A-1", "a1"),
            self.row("1", "Large Store", "A-2", "a2"),
            self.row("1", "Large Store", "A-3", "a3"),
            self.row("2", "Store B", "B-1", "b1"),
            self.row("3", "Store C", "C-1", "c1"),
            self.row("4", "Store D", "D-1", "d1"),
        ]

        selected = self.service._select_feed_rows(rows, options=self.options())

        self.assertEqual(
            [(feed.advertiser_id, feed.feed_name) for feed in selected],
            [("1", "A-1"), ("2", "B-1"), ("3", "C-1"), ("4", "D-1"), ("1", "A-2")],
        )


    def test_general_provider_round_robins_second_feeds(self) -> None:
        rows = [
            self.row("1", "Store A", "A-1", "a1"),
            self.row("1", "Store A", "A-2", "a2"),
            self.row("1", "Store A", "A-3", "a3"),
            self.row("2", "Store B", "B-1", "b1"),
            self.row("2", "Store B", "B-2", "b2"),
            self.row("3", "Store C", "C-1", "c1"),
            self.row("3", "Store C", "C-2", "c2"),
        ]

        selected = self.service._select_feed_rows(
            rows,
            options=self.options(max_feeds=6, max_feeds_per_advertiser=2),
        )

        self.assertEqual(
            [(feed.advertiser_id, feed.feed_name) for feed in selected],
            [("1", "A-1"), ("2", "B-1"), ("3", "C-1"), ("1", "A-2"), ("2", "B-2"), ("3", "C-2")],
        )

    def test_general_provider_can_exclude_targeted_advertiser(self) -> None:
        rows = [
            self.row("28737", "TTfone", "TTfone", "ttfone"),
            self.row("2", "Store B", "B-1", "b1"),
        ]

        selected = self.service._select_feed_rows(
            rows,
            options=self.options(excluded_advertiser_ids=("28737",)),
        )

        self.assertEqual([(feed.advertiser_id, feed.feed_name) for feed in selected], [("2", "B-1")])

    def test_targeted_provider_preserves_multiple_feeds_for_one_advertiser(self) -> None:
        rows = [
            self.row("1", "Store A", "A-1", "a1"),
            self.row("2", "Store B", "B-1", "b1"),
            self.row("1", "Store A", "A-2", "a2"),
            self.row("1", "Store A", "A-3", "a3"),
        ]

        selected = self.service._select_feed_rows(
            rows,
            options=self.options(max_feeds=2, advertiser_id="1"),
        )

        self.assertEqual([feed.feed_name for feed in selected], ["A-1", "A-2"])

    def test_duplicate_urls_are_not_selected_twice(self) -> None:
        duplicate = self.row("1", "Store A", "A-1 duplicate", "same")
        rows = [
            self.row("1", "Store A", "A-1", "same"),
            duplicate,
            self.row("2", "Store B", "B-1", "b1"),
        ]

        selected = self.service._select_feed_rows(rows, options=self.options(max_feeds=5))

        self.assertEqual(len(selected), 2)
        self.assertEqual({feed.advertiser_id for feed in selected}, {"1", "2"})


if __name__ == "__main__":
    unittest.main()
