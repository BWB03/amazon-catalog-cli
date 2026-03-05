"""
MCP Server Surface for Amazon Catalog CLI.
Exposes catalog_scan, catalog_check, catalog_schema, catalog_list_queries as MCP tools.
Launch with: catalog mcp
"""

from __future__ import annotations
import json

from mcp.server.fastmcp import FastMCP

from catalog.core.engine import execute_scan, execute_check, list_queries, get_schema
from catalog.core.models import ScanRequest, CheckRequest


mcp = FastMCP(
    "Catalog CLI",
    instructions="Amazon catalog auditing tool - scan CLR files for listing issues",
)


@mcp.tool()
def catalog_scan(
    file: str,
    queries: list[str] | None = None,
    fields: list[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
    exclude_fbm: bool = True,
) -> str:
    """Scan a CLR file with all or selected queries.

    Args:
        file: Path to CLR file (.xlsx)
        queries: Query names to run (omit for all queries)
        fields: Field mask - only return these fields in issues (e.g. ["sku", "severity", "details"])
        limit: Max issues to return per query
        offset: Skip first N issues per query
        exclude_fbm: Exclude FBM/MFN duplicates, keep FBA (default: true)

    Returns:
        JSON string with scan results including issues grouped by query
    """
    request = ScanRequest(
        file=file,
        queries=queries,
        fields=fields,
        limit=limit,
        offset=offset,
        exclude_fbm=exclude_fbm,
        format="json",
    )
    response = execute_scan(request)
    return json.dumps(response.model_dump(), indent=2)


@mcp.tool()
def catalog_check(
    query: str,
    file: str,
    fields: list[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
    exclude_fbm: bool = True,
) -> str:
    """Run a specific query on a CLR file.

    Args:
        query: Query name (e.g. "missing-attributes", "rufus-bullets")
        file: Path to CLR file (.xlsx)
        fields: Field mask - only return these fields in issues
        limit: Max issues to return
        offset: Skip first N issues
        exclude_fbm: Exclude FBM/MFN duplicates (default: true)

    Returns:
        JSON string with query results
    """
    request = CheckRequest(
        query=query,
        file=file,
        fields=fields,
        limit=limit,
        offset=offset,
        exclude_fbm=exclude_fbm,
        format="json",
    )
    response = execute_check(request)
    return json.dumps(response.model_dump(), indent=2)


@mcp.tool()
def catalog_list_queries() -> str:
    """List all available audit queries.

    Returns:
        JSON array of query objects with name and description
    """
    queries = list_queries()
    return json.dumps([q.model_dump() for q in queries], indent=2)


@mcp.tool()
def catalog_schema(query_name: str | None = None) -> str:
    """Get schema for queries, request params, and response shapes.

    Args:
        query_name: Optional specific query to get schema for (omit for all)

    Returns:
        JSON schema describing available queries, request formats, and response structures
    """
    response = get_schema(query_name)
    return json.dumps(response.model_dump(), indent=2)


def run_mcp_server():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")
