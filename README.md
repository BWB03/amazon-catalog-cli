# Catalog CLI

[![PyPI version](https://badge.fury.io/py/amazon-catalog-cli.svg)](https://badge.fury.io/py/amazon-catalog-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Agent-native Amazon catalog auditing tool**

The first AI-agent-friendly Amazon catalog analysis tool. Query your CLRs with structured input, integrate via MCP server, and automate catalog audits.

> **Hosted API available** at [api.catalogcli.com](https://api.catalogcli.com/docs) — persistent storage, unlimited scans, and API access for $9.99/mo. [Learn more](https://catalogcli.com)

## What's New in v2.0

- **Shared core architecture** - Business logic separated into `catalog/core/`, powering both CLI and MCP
- **MCP server** - `catalog mcp` launches a stdio MCP server with 4 tools, ready for Claude Desktop and any MCP client
- **JSON input** - `--json` and `--stdin` flags for structured agent input
- **Schema introspection** - `catalog schema --format json` returns full request/response schemas
- **Field masks** - `--fields sku,severity,details` to reduce output size
- **Pagination** - `--limit` and `--offset` for controlling result size
- **NDJSON streaming** - `--format ndjson` for line-by-line streaming of large results
- **Input hardening** - Pydantic validation rejects path traversal, injection, and malformed input
- **Environment variables** - `CATALOG_CLI_DEFAULT_FORMAT=json` for headless/CI use
- **Backward compatible** - All v1.x commands work unchanged

## Features

- **Agent-Native** - CLI + MCP server as equal citizens, JSON/NDJSON output, schema introspection
- **Fast** - Query 1000+ SKU catalogs in seconds
- **Extensible** - Plugin system for custom queries
- **Comprehensive** - 13 built-in catalog health checks
- **Intent Optimized** - COSMO-inspired shopper intent coverage for bullets

## Installation

```bash
pip install amazon-catalog-cli
```

Or install from source:

```bash
git clone https://github.com/BWB03/amazon-catalog-cli.git
cd amazon-catalog-cli
pip install -e .
```

## Quick Start

### For Humans

```bash
# Run all catalog checks
catalog scan my-catalog.xlsx

# Detailed results
catalog scan my-catalog.xlsx --show-details

# Run specific check
catalog check intent-bullets my-catalog.xlsx

# List available queries
catalog list-queries
```

### For AI Agents

```bash
# JSON output with field mask and limit
catalog scan my-catalog.xlsx --format json --fields sku,severity,details --limit 20

# Structured JSON input
catalog scan --json '{"file": "my-catalog.xlsx", "queries": ["missing-attributes"], "limit": 10}'

# Piped input
echo '{"file": "my-catalog.xlsx"}' | catalog scan --stdin --format json

# NDJSON streaming for large results
catalog scan my-catalog.xlsx --format ndjson

# Schema introspection (discover queries, params, response shapes)
catalog schema --format json

# Fetch live Seller Central listing JSON for an ASIN
CATALOG_SELLER_CENTRAL_COOKIE='session-id=...' catalog listing fetch B000TEST01 --format json

# Compare live Seller Central JSON with a CLR row
catalog listing diff B000TEST01 my-catalog.xlsx --sku SKU-123 --format json
```

### MCP Server (for Claude Desktop, CLR Pro, etc.)

```bash
# Start MCP server
catalog mcp
```

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "catalog": {
      "command": "catalog",
      "args": ["mcp"]
    }
  }
}
```

MCP tools: `catalog_scan`, `catalog_scan_summary`, `catalog_check`, `catalog_seller_listing_fetch`, `catalog_seller_listing_diff`, `catalog_list_queries`, `catalog_schema`

## Available Queries

### Attribute Audits
- **missing-attributes** - Find mandatory attributes missing from listings
- **missing-any-attributes** - Find all missing attributes (required + conditional)
- **new-attributes** - Find unused template fields that might add value

### Content Quality
- **intent-bullets** - Score bullet points against shopper intent coverage
- **bullet-prohibited-content** - Find bullet points with prohibited chars, emojis, claims, or placeholders
- **bullet-formatting** - Check bullet formatting (capitalization, length, punctuation)
- **bullet-awareness** - Soft violations in bullets (excessive caps, problematic chars)
- **long-titles** - Find titles exceeding 200 characters
- **title-prohibited-chars** - Find titles with prohibited characters
- **prohibited-chars** - Find prohibited characters in title/brand

### Catalog Structure
- **product-type-mismatch** - Find mismatched product types and item keywords
- **missing-variations** - Find products that should be variations but aren't

## CLI Commands

### `catalog scan`
Run all queries on a CLR file.

```bash
catalog scan <clr-file> [OPTIONS]

Options:
  --format [terminal|json|csv|ndjson]  Output format (default: terminal)
  --output PATH                        Output file path
  --show-details / --no-details        Show detailed results
  --include-fbm-duplicates             Include FBM/MFN duplicates
  --json TEXT                          JSON request body
  --stdin                              Read JSON request from stdin
  --queries TEXT                       Comma-separated query names
  --fields TEXT                        Comma-separated field mask
  --limit INTEGER                      Max issues to return
  --offset INTEGER                     Skip first N issues
```

### `catalog check`
Run a specific query.

```bash
catalog check <query-name> <clr-file> [OPTIONS]

Options:
  --format [terminal|json|csv|ndjson]  Output format (default: terminal)
  --output PATH                        Output file path
  --show-details / --no-details        Show detailed results
  --json TEXT                          JSON request body
  --stdin                              Read JSON request from stdin
  --fields TEXT                        Comma-separated field mask
  --limit INTEGER                      Max issues to return
  --offset INTEGER                     Skip first N issues
```

### `catalog listing fetch`
Fetch Amazon's live Seller Central listing JSON for an ASIN.

Requires a logged-in Seller Central cookie from your own browser session. Pass it with `--cookie`, `--cookie-file`, or the `CATALOG_SELLER_CENTRAL_COOKIE` environment variable.

```bash
catalog listing fetch <asin> [OPTIONS]

Options:
  --format [terminal|json]  Output format (default: terminal)
  --output PATH             Output file path
  --cookie TEXT             Seller Central Cookie header value
  --cookie-file PATH        File containing the Cookie header value
  --timeout FLOAT           HTTP timeout in seconds
  --json TEXT               JSON request body
  --stdin                   Read JSON request from stdin
```

### `catalog listing diff`
Compare Amazon's live Seller Central listing JSON with a matching CLR row.

Rows match by `--sku` when provided. Otherwise Catalog CLI looks for `Product Id Type = ASIN` and `Product Id = <asin>` in the CLR.

```bash
catalog listing diff <asin> <clr-file> [OPTIONS]

Options:
  --sku TEXT                Optional SKU to match in the CLR
  --format [terminal|json]  Output format (default: terminal)
  --output PATH             Output file path
  --cookie TEXT             Seller Central Cookie header value
  --cookie-file PATH        File containing the Cookie header value
  --timeout FLOAT           HTTP timeout in seconds
  --json TEXT               JSON request body
  --stdin                   Read JSON request from stdin
```

### `catalog schema`
Show schema for queries, params, and response shapes.

```bash
catalog schema [query-name] [OPTIONS]

Options:
  --format [terminal|json]  Output format
```

### `catalog list-queries`
List available queries.

```bash
catalog list-queries [OPTIONS]

Options:
  --format [terminal|json]  Output format
```

### `catalog mcp`
Start the MCP server (stdio transport).

```bash
catalog mcp
```

### `catalog setup-claude`
Configure Claude Code to use Catalog CLI as an MCP tool server.

```bash
# Free (local) — data stays on your machine
catalog setup-claude

# Pro (hosted API) — persistent storage, unlimited scans
catalog setup-claude --pro --api-key YOUR_KEY

# Per-project instead of global
catalog setup-claude --project
```

After setup, restart Claude Code and try: *"Scan my-catalog.xlsx and tell me the biggest issues"*

## Example JSON Output

```json
{
  "timestamp": "2026-03-05T10:30:00Z",
  "marketplace": "US",
  "is_us_marketplace": true,
  "total_queries": 13,
  "total_issues": 47,
  "total_affected_skus": 23,
  "results": [
    {
      "query_name": "missing-attributes",
      "description": "Find mandatory attributes missing from listings",
      "total_issues": 12,
      "affected_skus": 8,
      "issues": [
        {
          "row": 7,
          "sku": "ABC-123",
          "field": "brand",
          "severity": "required",
          "details": "Missing required field: brand",
          "product_type": "HAIR_STYLING_AGENT",
          "extra": {}
        }
      ]
    }
  ]
}
```

## Agent Integration

### Via CLI (subprocess)

```python
import subprocess, json

result = subprocess.run(
    ['catalog', 'scan', 'my-catalog.xlsx', '--format', 'json',
     '--fields', 'sku,severity,details', '--limit', '20'],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
```

### Via Python (direct import)

```python
from catalog.core import execute_scan, ScanRequest

request = ScanRequest(
    file="my-catalog.xlsx",
    queries=["missing-attributes", "intent-bullets"],
    fields=["sku", "severity", "details"],
    limit=20,
)
response = execute_scan(request)
```

### Via MCP

Add the MCP server to any MCP client (Claude Desktop, CLR Pro, etc.) and call `catalog_scan`, `catalog_check`, `catalog_seller_listing_fetch`, `catalog_seller_listing_diff`, `catalog_list_queries`, or `catalog_schema`.

## Intent-Based Bullet Optimization

The `intent-bullets` query evaluates bullet points against COSMO-inspired shopper intent coverage:

- **Audience / need fit**: Who it is for, preferences, or problem state
- **Function / use case**: The job, activity, event, or use flow
- **Context / compatibility**: Where, when, or what it works with
- **Decision evidence**: Specs, attributes, trust signals, or differentiators
- **All bullets**: Checked for intent coverage, length, vague marketing, ALL CAPS

Scores 1-5 with actionable suggestions. The old `rufus-bullets` query name still works as a deprecated compatibility alias.

## Extending with Custom Queries

```python
from catalog.query_engine import QueryPlugin

class MyCustomQuery(QueryPlugin):
    name = "my-custom-check"
    description = "My custom catalog check"

    def execute(self, listings, clr_parser):
        issues = []
        for listing in listings:
            if some_condition:
                issues.append({
                    'row': listing.row_number,
                    'sku': listing.sku,
                    'field': 'FieldName',
                    'severity': 'warning',
                    'details': 'Issue description',
                    'product_type': listing.product_type
                })
        return issues
```

## Requirements

- Python 3.10+
- openpyxl
- click
- rich
- pydantic
- mcp

## How to Get Your CLR

1. Go to **Amazon Seller Central** > **Catalog** > **Category Listing Report**
2. Click **Generate Report**
3. Download the `.xlsm` or `.xlsx` file
4. Run catalog CLI on it

## Free vs Pro

| | Open Source CLI | Free API | Pro API ($9.99/mo) |
|---|---|---|---|
| 13 quality audits | Yes | Yes | Yes |
| Scans | Unlimited (local) | 2 lifetime | Unlimited |
| Catalogs stored | — | 1 | Unlimited |
| Results persistence | — | 7 days | Permanent |
| API access | — | Yes | Yes |
| Rate limit | — | 10 req/min | 100 req/min |
| Claude Code integration | Local MCP | — | Hosted MCP |
| Variation Creator | — | — | Coming soon |

**[Get started at catalogcli.com](https://catalogcli.com)** | **[API Docs](https://api.catalogcli.com/docs)**

## Contributing

This is an open-source project. Contributions welcome!

- Add new query plugins
- Improve parsing logic
- Enhance output formats
- Build integrations

## License

MIT License - Free to use, modify, and distribute.

## Author

Built by Brett Bohannon ([@BWB03](https://github.com/BWB03))

## Related Projects

- [amazon-catalog-auditor-skill](https://github.com/BWB03/amazon-catalog-auditor-skill) - OpenClaw skill for agent workflows
- [clr-auditor](https://github.com/BWB03/clr-auditor) - Original CLR auditing tool
- [amazon-tool](https://github.com/BWB03/amazon-tool) - Amazon variation creator

---

**Agent-native Amazon catalog tool.** Built for the future of catalog management.
