"""Smoke tests for CLI commands."""

from click.testing import CliRunner
from catalog.surfaces.cli import cli
from catalog.core.models import SellerListingDiffResponse, SellerListingFetchResponse
import json


runner = CliRunner()


class TestCLIBasics:
    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "2.2" in result.output

    def test_help(self):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "scan" in result.output
        assert "check" in result.output
        assert "listing" in result.output
        assert "schema" in result.output
        assert "mcp" in result.output

    def test_scan_help(self):
        result = runner.invoke(cli, ["scan", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--stdin" in result.output
        assert "--fields" in result.output
        assert "--limit" in result.output
        assert "ndjson" in result.output

    def test_listing_fetch_json(self, monkeypatch):
        def fake_fetch(request):
            return SellerListingFetchResponse(
                asin=request.asin,
                endpoint="https://sellercentral.amazon.com/abis/ajax/reconciledDetailsV2?asin=B000TEST01",
                status="success",
                status_code=200,
                raw_response={"ok": True},
                display_fields={"brand#1.value": {"displayLabel": "Brand Name", "value": "Brand"}},
                parsed_imsv3={"brand": [{"value": "Brand"}]},
            )

        monkeypatch.setattr("catalog.surfaces.cli.fetch_seller_listing", fake_fetch)

        result = runner.invoke(
            cli,
            ["listing", "fetch", "B000TEST01", "--cookie", "session-cookie", "--format", "json"],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["asin"] == "B000TEST01"
        assert data["status"] == "success"
        assert data["parsed_imsv3"]["brand"][0]["value"] == "Brand"

    def test_listing_diff_json(self, monkeypatch):
        fetch = SellerListingFetchResponse(
            asin="B000TEST01",
            endpoint="https://sellercentral.amazon.com/abis/ajax/reconciledDetailsV2?asin=B000TEST01",
            status="success",
            status_code=200,
        )

        def fake_diff(request):
            return SellerListingDiffResponse(
                asin=request.asin,
                status="success",
                fetch=fetch,
                clr_match={"row": 7, "sku": request.sku, "product_type": "TEST_PRODUCT"},
                value_mismatches=[
                    {
                        "field": "Brand Name",
                        "amazon_field": "Brand Name",
                        "clr_value": "CLR",
                        "amazon_value": "Amazon",
                    }
                ],
            )

        monkeypatch.setattr("catalog.surfaces.cli.diff_seller_listing", fake_diff)

        with runner.isolated_filesystem():
            open("catalog.xlsx", "w").close()
            result = runner.invoke(
                cli,
                [
                    "listing",
                    "diff",
                    "B000TEST01",
                    "catalog.xlsx",
                    "--sku",
                    "SKU-1",
                    "--cookie",
                    "session-cookie",
                    "--format",
                    "json",
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["clr_match"]["sku"] == "SKU-1"
        assert data["value_mismatches"][0]["clr_value"] == "CLR"


class TestListQueries:
    def test_terminal(self):
        result = runner.invoke(cli, ["list-queries"])
        assert result.exit_code == 0
        assert "missing-attributes" in result.output
        assert "intent-bullets" in result.output

    def test_json(self):
        result = runner.invoke(cli, ["list-queries", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 14
        assert data[0]["name"]
        assert data[0]["description"]


class TestSchema:
    def test_terminal(self):
        result = runner.invoke(cli, ["schema"])
        assert result.exit_code == 0
        assert "missing-attributes" in result.output

    def test_json(self):
        result = runner.invoke(cli, ["schema", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "queries" in data
        assert "request_schema" in data
        assert "response_schema" in data

    def test_single_query(self):
        result = runner.invoke(cli, ["schema", "intent-bullets", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["queries"]) == 1
        assert data["queries"][0]["name"] == "intent-bullets"
        assert "rufus-bullets" in data["queries"][0]["aliases"]

    def test_single_query_legacy_alias(self):
        result = runner.invoke(cli, ["schema", "rufus-bullets", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["queries"]) == 1
        assert data["queries"][0]["name"] == "intent-bullets"


class TestValidationErrors:
    def test_scan_path_traversal(self):
        result = runner.invoke(cli, ["scan", "--json", '{"file": "../../../etc/passwd"}', "--format", "json"])
        assert result.exit_code != 0

    def test_check_bad_query_name(self):
        result = runner.invoke(cli, ["check", "--json", '{"query": "rm -rf /", "file": "test.xlsx"}', "--format", "json"])
        assert result.exit_code != 0

    def test_scan_missing_file_arg(self):
        result = runner.invoke(cli, ["scan"])
        assert result.exit_code != 0
