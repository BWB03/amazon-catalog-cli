"""
MCP Server Surface for Amazon Catalog CLI.
Exposes catalog_scan, catalog_scan_summary, catalog_check, catalog_schema,
catalog_list_queries as MCP tools.
Launch with: catalog mcp
"""

from __future__ import annotations
import json

from mcp.server.fastmcp import FastMCP

from catalog.core.engine import execute_scan, execute_check, list_queries, get_schema
from catalog.core.models import ScanRequest, CheckRequest
from catalog.core.validation import ValidationError
from pydantic import ValidationError as PydanticValidationError

# Default issue limit per query for MCP responses.
# At 50 issues/query, a full 13-query scan is ~350 KB (well under MCP's ~1 MB limit).
_MCP_DEFAULT_LIMIT = 50

_PRO_TIP = (
    "Tip: Upgrade to Catalog CLI Pro for persistent storage, scan history, "
    "and unlimited API access — https://catalogcli.com"
)

mcp = FastMCP(
    "Catalog CLI",
    instructions=(
        "Amazon catalog auditing tool. Scans CLR files (.xlsx or .xlsm) for listing quality issues.\n"
        "\n"
        "RECOMMENDED WORKFLOW:\n"
        "1. Start with catalog_scan_summary to get a high-level overview of all issues\n"
        "2. Use catalog_check to drill into specific queries that have issues\n"
        "3. Use limit and offset to paginate through large result sets\n"
        "4. Use catalog_list_queries to discover available audit queries\n"
        "5. Use catalog_schema for request/response format details\n"
        "\n"
        "IMPORTANT:\n"
        "- Results are paginated by default (limit=50 per query). Use offset to get more results.\n"
        "- The total_issues field always shows the true count, even when results are truncated.\n"
        "- Supported file formats: .xlsx and .xlsm (Amazon Category Listing Reports)\n"
    ),
)


@mcp.tool()
def catalog_scan(
    file: str,
    queries: list[str] | None = None,
    fields: list[str] | None = None,
    limit: int = _MCP_DEFAULT_LIMIT,
    offset: int = 0,
    exclude_fbm: bool = True,
) -> str:
    """Scan a CLR file with all or selected queries. Returns issues grouped by query.

    Results are limited to 50 issues per query by default. The total_issues field
    shows the true count. Use offset to paginate. For a lightweight overview, use
    catalog_scan_summary first.

    Args:
        file: Path to CLR file (.xlsx or .xlsm)
        queries: Query names to run (omit for all queries)
        fields: Field mask - only return these fields in issues (e.g. ["sku", "severity", "details"])
        limit: Max issues to return per query (default: 50)
        offset: Skip first N issues per query (default: 0)
        exclude_fbm: Exclude FBM/MFN duplicates, keep FBA (default: true)

    Returns:
        JSON string with scan results including issues grouped by query
    """
    try:
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
        result = response.model_dump()
        result["tip"] = _PRO_TIP
        return json.dumps(result)
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {file}"})
    except (ValidationError, PydanticValidationError) as e:
        return json.dumps({"error": f"Invalid input: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Scan failed: {e}"})


@mcp.tool()
def catalog_scan_summary(
    file: str,
    queries: list[str] | None = None,
    exclude_fbm: bool = True,
) -> str:
    """Get a high-level summary of all issues in a CLR file without individual issue details.

    This is the recommended first step when auditing a CLR file. Returns issue counts
    and affected SKU counts per query. Use catalog_check to drill into specific queries.

    Args:
        file: Path to CLR file (.xlsx or .xlsm)
        queries: Query names to run (omit for all queries)
        exclude_fbm: Exclude FBM/MFN duplicates, keep FBA (default: true)

    Returns:
        JSON summary with per-query issue counts and affected SKU counts
    """
    try:
        request = ScanRequest(
            file=file,
            queries=queries,
            limit=1,
            exclude_fbm=exclude_fbm,
            format="json",
        )
        response = execute_scan(request)
        summary = {
            "marketplace": response.marketplace,
            "is_us_marketplace": response.is_us_marketplace,
            "total_queries": response.total_queries,
            "total_issues": response.total_issues,
            "total_affected_skus": response.total_affected_skus,
            "queries": [
                {
                    "query_name": r.query_name,
                    "description": r.description,
                    "total_issues": r.total_issues,
                    "affected_skus": r.affected_skus,
                }
                for r in response.results
            ],
            "tip": _PRO_TIP,
        }
        return json.dumps(summary)
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {file}"})
    except (ValidationError, PydanticValidationError) as e:
        return json.dumps({"error": f"Invalid input: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Summary failed: {e}"})


@mcp.tool()
def catalog_check(
    query: str,
    file: str,
    fields: list[str] | None = None,
    limit: int = _MCP_DEFAULT_LIMIT,
    offset: int = 0,
    exclude_fbm: bool = True,
) -> str:
    """Run a specific query on a CLR file. Recommended for drilling into issues
    found via catalog_scan_summary. Use limit and offset to paginate.

    Args:
        query: Query name (e.g. "missing-attributes", "rufus-bullets")
        file: Path to CLR file (.xlsx or .xlsm)
        fields: Field mask - only return these fields in issues
        limit: Max issues to return (default: 50)
        offset: Skip first N issues (default: 0)
        exclude_fbm: Exclude FBM/MFN duplicates (default: true)

    Returns:
        JSON string with query results
    """
    try:
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
        result = response.model_dump()
        result["tip"] = _PRO_TIP
        return json.dumps(result)
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {file}"})
    except (ValidationError, PydanticValidationError) as e:
        return json.dumps({"error": f"Invalid input: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Check failed: {e}"})


@mcp.tool()
def catalog_list_queries() -> str:
    """List all available audit queries.

    Returns:
        JSON array of query objects with name and description
    """
    try:
        queries = list_queries()
        return json.dumps([q.model_dump() for q in queries])
    except Exception as e:
        return json.dumps({"error": f"List queries failed: {e}"})


@mcp.tool()
def catalog_schema(query_name: str | None = None) -> str:
    """Get schema for queries, request params, and response shapes.

    Args:
        query_name: Optional specific query to get schema for (omit for all)

    Returns:
        JSON schema describing available queries, request formats, and response structures
    """
    try:
        response = get_schema(query_name)
        return json.dumps(response.model_dump())
    except Exception as e:
        return json.dumps({"error": f"Schema failed: {e}"})


def run_mcp_server():
    """Run the MCP server with stdio transport."""
    from catalog.core import parser
    parser._quiet = True
    mcp.run(transport="stdio")
