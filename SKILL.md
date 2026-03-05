# Catalog CLI - Agent Guidance

## What this tool does
Catalog CLI audits Amazon Category Listing Reports (CLR files, .xlsx) for listing quality issues. It runs 12 query plugins covering missing attributes, title validation, bullet point optimization, product type checks, and more.

## Quick patterns

### Health check (fastest)
```bash
catalog scan report.xlsx --format json --queries missing-attributes,long-titles --fields sku,severity,details --limit 10
```

### Full audit
```bash
catalog scan report.xlsx --format json
```

### Single query
```bash
catalog check rufus-bullets report.xlsx --format json --limit 20
```

### JSON input (structured)
```bash
catalog scan --json '{"file": "report.xlsx", "queries": ["missing-attributes"], "fields": ["sku", "severity"], "limit": 10}'
```

### Piped input
```bash
echo '{"file": "report.xlsx"}' | catalog scan --stdin
```

### Schema discovery
```bash
catalog schema --format json
catalog schema missing-attributes --format json
```

## Rules for agents

1. **Always use `--format json`** for machine-readable output
2. **Use field masks** (`--fields sku,severity,details`) to reduce output size
3. **Use `--limit`** to cap results and avoid overwhelming context
4. **Check schema first** for unknown queries: `catalog schema --format json`
5. **Use NDJSON** (`--format ndjson`) for streaming large results line-by-line

## Available queries

| Query | Description |
|-------|-------------|
| `missing-attributes` | Find mandatory attributes missing from listings |
| `missing-any-attributes` | Find all missing attributes (required + conditional) |
| `long-titles` | Find titles exceeding 200 characters |
| `title-prohibited-chars` | Find titles with prohibited characters |
| `rufus-bullets` | Evaluate bullets against Amazon's RUFUS AI framework |
| `prohibited-chars` | Find prohibited characters in title/brand |
| `bullet-prohibited-content` | Find prohibited content in bullet points |
| `bullet-formatting` | Check bullet formatting (caps, length, punctuation) |
| `bullet-awareness` | Soft violations in bullets (excessive caps, etc.) |
| `product-type-mismatch` | Product type / item type keyword mismatches |
| `missing-variations` | Products that might be missing variation relationships |
| `new-attributes` | Template attributes not being used |

## MCP server

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

MCP tools: `catalog_scan`, `catalog_check`, `catalog_list_queries`, `catalog_schema`

## Environment variables

- `CATALOG_CLI_DEFAULT_FORMAT` - Default output format (default: `terminal`, set to `json` for headless/CI)
- `CATALOG_CLI_CONFIG` - Config file path (reserved for future use)
