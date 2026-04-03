# Catalog CLI Pro

Agent-native Amazon catalog auditing tool. Analyzes Category Listing Reports (CLR files) for quality issues across 13 checks.

## Architecture

Three-layer design:

- **Core** (`catalog/core/`) — engine, parser, models, validation, query engine, schema
- **Surfaces** (`catalog/surfaces/`) — CLI (`cli.py`) and MCP server (`mcp.py`)
- **Queries** (`catalog/queries/`) — 13 query plugins, each implements `QueryPlugin.execute(listings, clr_parser)`
- **API** (`api/`) — FastAPI hosted service (local only, NOT pushed to public GitHub)

## Key Patterns

- Pydantic models for all request/response shapes (`core/models.py`)
- Query plugins are auto-discovered from `catalog/queries/`
- CLI uses Click, MCP uses FastMCP (stdio transport)
- Output formats: terminal (Rich), JSON, CSV, NDJSON
- Field masking and pagination supported across all surfaces

## Commands

```bash
catalog scan my-catalog.xlsx           # Full audit
catalog check rufus-bullets file.xlsx  # Single query
catalog list-queries                   # Available queries
catalog schema                         # Schema introspection
catalog mcp                            # Start MCP server
catalog setup-claude                   # Configure Claude Code integration
```

## Development

```bash
pip install -e ".[api]"    # Install with API dependencies
pytest                      # Run tests
```

## Important

- `api/` directory contains the hosted API service — this is NOT pushed to the public GitHub repo
- `site/` directory contains the landing page for catalogcli.com
- The package on PyPI is `amazon-catalog-cli`
