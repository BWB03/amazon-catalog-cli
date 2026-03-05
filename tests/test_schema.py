"""Tests for schema introspection."""

from catalog.core.engine import get_schema, list_queries


class TestSchema:
    def test_get_schema_returns_all_queries(self):
        response = get_schema()
        assert len(response.queries) == 12

    def test_get_schema_has_request_schemas(self):
        response = get_schema()
        assert "scan" in response.request_schema
        assert "check" in response.request_schema
        assert "properties" in response.request_schema["scan"]
        assert "file" in response.request_schema["scan"]["properties"]

    def test_get_schema_has_response_schemas(self):
        response = get_schema()
        assert "scan" in response.response_schema
        assert "check" in response.response_schema

    def test_get_schema_single_query(self):
        response = get_schema("missing-attributes")
        assert len(response.queries) == 1
        assert response.queries[0].name == "missing-attributes"

    def test_get_schema_unknown_query_returns_empty(self):
        response = get_schema("nonexistent-query")
        assert len(response.queries) == 0


class TestListQueries:
    def test_list_all(self):
        queries = list_queries()
        assert len(queries) == 12
        names = [q.name for q in queries]
        assert "missing-attributes" in names
        assert "rufus-bullets" in names
        assert "bullet-awareness" in names

    def test_query_has_description(self):
        queries = list_queries()
        for q in queries:
            assert q.name
            assert q.description
