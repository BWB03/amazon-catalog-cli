"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError
from catalog.core.models import ScanRequest, CheckRequest, ScanResponse, CheckResponse, QueryInfo


class TestScanRequest:
    def test_minimal(self):
        req = ScanRequest(file="report.xlsx")
        assert req.file == "report.xlsx"
        assert req.queries is None
        assert req.fields is None
        assert req.limit is None
        assert req.exclude_fbm is True
        assert req.format == "json"

    def test_full(self):
        req = ScanRequest(
            file="report.xlsx",
            queries=["missing-attributes", "long-titles"],
            fields=["sku", "severity"],
            limit=10,
            offset=5,
            exclude_fbm=False,
            format="ndjson",
        )
        assert req.queries == ["missing-attributes", "long-titles"]
        assert req.fields == ["sku", "severity"]
        assert req.limit == 10
        assert req.offset == 5

    def test_rejects_path_traversal(self):
        with pytest.raises(ValidationError):
            ScanRequest(file="../../../etc/passwd")

    def test_rejects_absolute_path(self):
        with pytest.raises(ValidationError):
            ScanRequest(file="/etc/passwd")

    def test_rejects_bad_query_name(self):
        with pytest.raises(ValidationError):
            ScanRequest(file="report.xlsx", queries=["rm -rf /"])

    def test_rejects_negative_limit(self):
        with pytest.raises(ValidationError):
            ScanRequest(file="report.xlsx", limit=-1)

    def test_rejects_invalid_format(self):
        with pytest.raises(ValidationError):
            ScanRequest(file="report.xlsx", format="xml")


class TestCheckRequest:
    def test_minimal(self):
        req = CheckRequest(query="missing-attributes", file="report.xlsx")
        assert req.query == "missing-attributes"
        assert req.file == "report.xlsx"

    def test_rejects_bad_query(self):
        with pytest.raises(ValidationError):
            CheckRequest(query="drop table;", file="report.xlsx")


class TestScanResponse:
    def test_defaults(self):
        resp = ScanResponse()
        assert resp.marketplace == "US"
        assert resp.is_us_marketplace is True
        assert resp.total_queries == 0
        assert resp.total_issues == 0
        assert resp.results == []
        assert resp.timestamp  # auto-generated


class TestCheckResponse:
    def test_defaults(self):
        resp = CheckResponse()
        assert resp.query_name == ""
        assert resp.issues == []


class TestQueryInfo:
    def test_basic(self):
        info = QueryInfo(name="test", description="A test query")
        assert info.name == "test"
        assert info.severity_levels == []
