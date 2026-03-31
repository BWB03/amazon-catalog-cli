"""Tests for MCP server tool registration."""

from catalog.surfaces.mcp import mcp


class TestMCPTools:
    def test_tools_registered(self):
        tools = mcp._tool_manager.list_tools()
        names = [t.name for t in tools]
        assert "catalog_scan" in names
        assert "catalog_scan_summary" in names
        assert "catalog_check" in names
        assert "catalog_list_queries" in names
        assert "catalog_schema" in names

    def test_tool_count(self):
        tools = mcp._tool_manager.list_tools()
        assert len(tools) == 5
