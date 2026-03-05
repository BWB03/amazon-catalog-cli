"""Tests for input validation."""

import pytest
from catalog.core.validation import (
    validate_file_path,
    validate_query_name,
    validate_sku,
    ValidationError,
)


class TestValidateFilePath:
    def test_valid_relative_path(self):
        assert validate_file_path("report.xlsx") == "report.xlsx"

    def test_valid_subdirectory(self):
        assert validate_file_path("data/report.xlsx") == "data/report.xlsx"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_file_path("")

    def test_rejects_path_traversal(self):
        with pytest.raises(ValidationError, match="Path traversal"):
            validate_file_path("../../../etc/passwd")

    def test_rejects_path_traversal_middle(self):
        with pytest.raises(ValidationError, match="Path traversal"):
            validate_file_path("data/../../../etc/passwd")

    def test_allows_absolute_path(self):
        assert validate_file_path("/Users/someone/report.xlsx") == "/Users/someone/report.xlsx"

    def test_expands_home_directory(self):
        import os
        result = validate_file_path("~/report.xlsx")
        assert result == os.path.expanduser("~/report.xlsx")

    def test_rejects_null_bytes(self):
        with pytest.raises(ValidationError, match="null bytes"):
            validate_file_path("report\x00.xlsx")

    def test_rejects_control_characters(self):
        with pytest.raises(ValidationError, match="control characters"):
            validate_file_path("report\x01.xlsx")


class TestValidateQueryName:
    def test_valid_name(self):
        assert validate_query_name("missing-attributes") == "missing-attributes"

    def test_valid_with_underscores(self):
        assert validate_query_name("my_custom_query") == "my_custom_query"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_query_name("")

    def test_rejects_spaces(self):
        with pytest.raises(ValidationError, match="Invalid query name"):
            validate_query_name("missing attributes")

    def test_rejects_shell_injection(self):
        with pytest.raises(ValidationError, match="Invalid query name"):
            validate_query_name("rm -rf /")

    def test_rejects_special_chars(self):
        with pytest.raises(ValidationError, match="Invalid query name"):
            validate_query_name("query;drop table")


class TestValidateSku:
    def test_valid_sku(self):
        assert validate_sku("ABC-123") == "ABC-123"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_sku("")

    def test_rejects_question_mark(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_sku("ABC?123")

    def test_rejects_hash(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_sku("ABC#123")

    def test_rejects_percent(self):
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_sku("ABC%123")

    def test_rejects_control_chars(self):
        with pytest.raises(ValidationError, match="control characters"):
            validate_sku("ABC\x00123")
