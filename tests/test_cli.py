"""Smoke tests for CLI commands."""

from click.testing import CliRunner
from catalog.surfaces.cli import cli
import json


runner = CliRunner()


class TestCLIBasics:
    def test_version(self):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_help(self):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "scan" in result.output
        assert "check" in result.output
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


class TestListQueries:
    def test_terminal(self):
        result = runner.invoke(cli, ["list-queries"])
        assert result.exit_code == 0
        assert "missing-attributes" in result.output
        assert "rufus-bullets" in result.output

    def test_json(self):
        result = runner.invoke(cli, ["list-queries", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 12
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
        result = runner.invoke(cli, ["schema", "rufus-bullets", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["queries"]) == 1
        assert data["queries"][0]["name"] == "rufus-bullets"


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
