"""Tests for title validation query plugins."""

from catalog.core.parser import Listing
from catalog.queries.title_checks import MobileTitleReadinessQuery


def make_listing(title, all_fields=None, product_type="BACKPACK", item_type="daypack"):
    return Listing(
        row_number=7,
        sku="SKU-123",
        product_type=product_type,
        item_type=item_type,
        title=title,
        brand="Acme",
        parentage="",
        parent_sku="",
        status="Active",
        bullet_points=[],
        all_fields=all_fields or {},
    )


class TestMobileTitleReadinessQuery:
    def test_title_exactly_75_characters_is_not_flagged(self):
        listing = make_listing("A" * 75)

        issues = MobileTitleReadinessQuery().execute([listing], None)

        assert issues == []

    def test_title_over_75_characters_includes_rewrite_segments(self):
        title = (
            "Acme Waterproof Hiking Backpack Lightweight Travel Daypack "
            "with Laptop Sleeve and Bottle Pockets"
        )
        listing = make_listing(title)

        issues = MobileTitleReadinessQuery().execute([listing], None)

        assert len(issues) == 1
        issue = issues[0]
        assert issue["title_char_count"] == len(title)
        assert issue["max_title_chars"] == 75
        assert issue["over_by"] == len(title) - 75
        assert issue["mobile_visible_title"] == title[:75]
        assert issue["overflow_title"] == title[75:].strip()
        assert issue["field"] == "Title"
        assert issue["severity"] == "warning"
        assert issue["original_title"] == title
        assert issue["brand"] == "Acme"
        assert issue["title_limit_applicability"] == "standard_limit"

    def test_term_extraction_separates_visible_and_overflow_terms(self):
        title = (
            "Acme Stainless Steel Water Bottle Insulated Leakproof Travel "
            "Bottle for Gym Cycling Camping"
        )
        listing = make_listing(title)

        issue = MobileTitleReadinessQuery().execute([listing], None)[0]

        assert "acme" in issue["priority_zone_terms"]
        assert "stainless" in issue["priority_zone_terms"]
        assert "for" not in issue["all_significant_terms"]
        assert issue["all_significant_terms"].index("acme") < issue["all_significant_terms"].index("bottle")
        assert issue["overflow_terms"]
        assert set(issue["overflow_terms"]).isdisjoint({"for", "and", "with"})

    def test_item_highlights_detected_when_present(self):
        listing = make_listing(
            "Acme Stainless Steel Water Bottle Insulated Leakproof Travel Bottle for Gym Cycling Camping",
            {
                "Item Highlight 1": "Keeps drinks cold for travel.",
                "other field": "ignored",
            },
        )

        issue = MobileTitleReadinessQuery().execute([listing], None)[0]

        assert issue["item_highlights_present"] is True
        assert issue["item_highlights_char_count"] == len("Keeps drinks cold for travel.")
        assert issue["item_highlights_max_chars"] == 125
        assert issue["item_highlights_remaining_chars"] == 125 - len("Keeps drinks cold for travel.")
        assert issue["item_highlights_over_limit"] is False

    def test_item_highlights_use_one_aggregate_125_character_budget(self):
        listing = make_listing(
            "Acme Stainless Steel Water Bottle Insulated Leakproof Travel Bottle for Gym Cycling Camping",
            {
                "Item Highlight 1": "A" * 70,
                "Item Highlight 2": "B" * 70,
            },
        )

        issue = MobileTitleReadinessQuery().execute([listing], None)[0]

        assert issue["item_highlights_char_count"] == 141
        assert issue["item_highlights_remaining_chars"] == 0
        assert issue["item_highlights_over_limit"] is True

    def test_missing_item_highlights_are_safe(self):
        listing = make_listing(
            "Acme Stainless Steel Water Bottle Insulated Leakproof Travel Bottle for Gym Cycling Camping"
        )

        issue = MobileTitleReadinessQuery().execute([listing], None)[0]

        assert issue["item_highlights_present"] is False
        assert issue["item_highlights_char_count"] == 0

    def test_likely_media_listing_requires_exemption_review(self):
        listing = make_listing(
            "A" * 76,
            product_type="BOOKS_1973_AND_LATER",
            item_type="books",
        )

        issue = MobileTitleReadinessQuery().execute([listing], None)[0]

        assert issue["severity"] == "info"
        assert issue["title_limit_applicability"] == "likely_media_exempt"
        assert "verify the exemption" in issue["details"]

    def test_missing_category_data_requires_confirmation(self):
        listing = make_listing("A" * 76, product_type="", item_type="")

        issue = MobileTitleReadinessQuery().execute([listing], None)[0]

        assert issue["severity"] == "warning"
        assert issue["title_limit_applicability"] == "category_unverified"
        assert "confirm the listing is not media" in issue["details"]
