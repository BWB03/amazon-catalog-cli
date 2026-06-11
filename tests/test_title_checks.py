"""Tests for title validation query plugins."""

from catalog.core.parser import Listing
from catalog.queries.title_checks import MobileTitleReadinessQuery


def make_listing(title, all_fields=None):
    return Listing(
        row_number=7,
        sku="SKU-123",
        product_type="BACKPACK",
        item_type="daypack",
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

    def test_missing_item_highlights_are_safe(self):
        listing = make_listing(
            "Acme Stainless Steel Water Bottle Insulated Leakproof Travel Bottle for Gym Cycling Camping"
        )

        issue = MobileTitleReadinessQuery().execute([listing], None)[0]

        assert issue["item_highlights_present"] is False
        assert issue["item_highlights_char_count"] == 0
