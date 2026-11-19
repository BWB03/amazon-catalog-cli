"""Regression tests for listing copy monitoring and coverage reporting."""

import json

from click.testing import CliRunner
from openpyxl import Workbook

from catalog.core.listing_monitor import monitor_seller_listings
from catalog.core.models import SellerListingFetchResponse
from catalog.surfaces.cli import cli


def _write_workbook(path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Template"
    sheet.append(["Country:US"])
    sheet.append([])
    sheet.append([])
    sheet.append([
        "Status", "Title", "SKU", "Product Type", "Parentage", "Product Id Type",
        "Product Id", "Item Name", "Bullet Point", "Bullet Point", "Product Description", "Brand Name",
    ])
    sheet.append([
        None, "::title", None, None, None, None, None, "item_name[language_tag=en_US]#1.value",
        "bullet_point[language_tag=en_US]#1.value", "bullet_point[language_tag=en_US]#2.value",
        "product_description#1.value", "brand#1.value",
    ])
    sheet.append([])
    for sku, identifier_type, identifier in (
        ("SKU-FBA", "ASIN", "B000TEST01"),
        ("SKU-FBM", "ASIN", "B000TEST01"),
        ("SKU-2", "ASIN", "B000TEST02"),
        ("UPC-SKU", "UPC", "012345678901"),
    ):
        sheet.append([
            "Active", "Amazon's title column", sku, "TEST_PRODUCT", None, identifier_type,
            identifier, "Submitted title", "First bullet", "Old second bullet", "Description",
        ])
    workbook.save(path)


def _fetch(asin, status="success", **kwargs):
    return SellerListingFetchResponse(
        asin=asin, endpoint="https://sellercentral.amazon.com", status=status, **kwargs,
    )


def test_monitor_preserves_bullet_slots_and_reports_missing_coverage(tmp_path, monkeypatch):
    path = tmp_path / "catalog.xlsx"
    _write_workbook(path)
    monkeypatch.setenv("CATALOG_SELLER_CENTRAL_COOKIE", "test-session")
    calls = []

    def fake_fetch(request):
        calls.append(request.asin)
        return _fetch(
            request.asin,
            display_fields={
                "item_name#1.value": {"value": "Submitted title"},
                "bullet_point#1.value": {"displayLabel": "Bullet Point", "value": "First  bullet"},
                "bullet_point#2.value": {"displayLabel": "Bullet Point", "value": "New second bullet"},
            },
            parsed_imsv3={"brand": [{"value": "Live Brand"}]},
        )

    monkeypatch.setattr("catalog.core.listing_monitor.fetch_seller_listing", fake_fetch)
    report = monitor_seller_listings(
        str(path), baseline=path.name, asins=("B000TEST01", "B000TEST03"),
    )

    assert calls == ["B000TEST01"]
    assert report.status == "partial"
    assert report.unmatched_asins == ["B000TEST03"]
    assert report.rows_without_asin == ["UPC-SKU"]
    assert [row.sku for row in report.results] == ["SKU-FBA", "SKU-FBM"]
    for row in report.results:
        assert row.unavailable_fields == ["Product Description"]
        assert row.compared_fields == 4
        assert [entry.model_dump() for entry in row.discrepancies] == [
            {"field": "Bullet Point 2", "clr_value": "Old second bullet", "amazon_value": "New second bullet"},
            {"field": "Brand", "clr_value": None, "amazon_value": "Live Brand"},
        ]


def test_monitor_stops_on_expired_session(tmp_path, monkeypatch):
    path = tmp_path / "catalog.xlsx"
    _write_workbook(path)
    monkeypatch.setenv("CATALOG_SELLER_CENTRAL_COOKIE", "test-session")
    calls = []

    def expired(request):
        calls.append(request.asin)
        return _fetch(request.asin, "auth_required", error="Session expired.")

    monkeypatch.setattr("catalog.core.listing_monitor.fetch_seller_listing", expired)
    report = monitor_seller_listings(str(path), baseline=path.name)

    assert calls == ["B000TEST01"]
    assert report.status == "failed"
    assert report.error == "Session expired."
    assert report.unchecked_asins == {"B000TEST01": "auth_required", "B000TEST02": "auth_required"}
    assert report.results == []


def test_monitor_cli_uses_hosted_baseline_and_writes_json(tmp_path, monkeypatch):
    file = tmp_path / "catalog.xlsx"
    _write_workbook(file)
    output = tmp_path / "checks.json"
    catalog_id = "5194de18-8c73-4709-a799-a205ad2a86c1"
    monkeypatch.setenv("CATALOG_API_KEY", "test-api-key")
    monkeypatch.setenv("CATALOG_SELLER_CENTRAL_COOKIE", "test-session")

    def download(catalog, key):
        assert str(catalog) == catalog_id
        assert key == "test-api-key"
        return "original.xlsm", file.read_bytes()

    monkeypatch.setattr("catalog.surfaces.cli.download_catalog_source", download)
    monkeypatch.setattr(
        "catalog.core.listing_monitor.fetch_seller_listing",
        lambda request: _fetch(request.asin, display_fields={"item_name": "Different title"}),
    )
    result = CliRunner().invoke(cli, [
        "listing", "monitor", "--catalog-id", catalog_id, "--asin", "b000test01", "--output", str(output),
    ])

    assert result.exit_code == 0, result.output
    report = json.loads(output.read_text())
    assert report["catalog_id"] == catalog_id
    assert report["baseline"] == "original.xlsm"
    assert report["results"][0]["discrepancies"][0]["amazon_value"] == "Different title"
    assert "test-session" not in output.read_text()
