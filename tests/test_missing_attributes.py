"""Tests for missing attribute query exceptions."""

from catalog.core.parser import CLRParser, Listing
from catalog.queries.missing_attributes import (
    MissingAnyAttributesQuery,
    MissingAttributesQuery,
)


class ParserStub(CLRParser):
    def __init__(self, required_fields, conditional_fields=None):
        self._required_fields = required_fields
        self._conditional_fields = conditional_fields or []

    def get_required_fields(self):
        return self._required_fields

    def get_conditional_fields(self):
        return self._conditional_fields

    def is_product_identifier_field(self, field):
        return CLRParser.is_product_identifier_field(field)

    def is_virtual_bundle_listing(self, listing):
        return CLRParser.is_virtual_bundle_listing(self, listing)


def _listing(all_fields):
    return Listing(
        row_number=7,
        sku="VB-BUNDLE",
        product_type="TEST_PRODUCT",
        item_type="",
        title="Bundle product",
        brand="",
        parentage="",
        parent_sku="",
        status="",
        bullet_points=[],
        all_fields=all_fields,
    )


def test_missing_attributes_skips_virtual_bundle_product_id_type():
    parser = ParserStub(["Product Id Type", "Brand"])
    listing = _listing({
        "Product Id Type": "",
        "Product Id": "",
        "Brand": "",
    })

    issues = MissingAttributesQuery().execute([listing], parser)

    assert [issue["field"] for issue in issues] == ["Brand"]


def test_missing_any_attributes_skips_virtual_bundle_product_identifier_fields():
    parser = ParserStub(
        required_fields=["Product Id Type"],
        conditional_fields=["Product Id", "Color"],
    )
    listing = _listing({
        "Product Id Type": "",
        "Product Id": "",
        "Color": "",
    })

    issues = MissingAnyAttributesQuery().execute([listing], parser)

    assert [issue["field"] for issue in issues] == ["Color"]


def test_regular_listing_missing_product_id_type_is_reported():
    parser = ParserStub(["Product Id Type"])
    listing = _listing({
        "Product Id Type": "",
        "Product Id": "B000TEST",
    })

    issues = MissingAttributesQuery().execute([listing], parser)

    assert [issue["field"] for issue in issues] == ["Product Id Type"]
