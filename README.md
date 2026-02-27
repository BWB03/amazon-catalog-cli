# Catalog CLI Light

[![PyPI version](https://badge.fury.io/py/amazon-catalog-cli.svg)](https://badge.fury.io/py/amazon-catalog-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Free CLI for Amazon catalog auditing**

The first AI-agent-friendly Amazon catalog analysis tool. Query your CLRs with natural language, automate catalog audits, and integrate with AI workflows.

> 💡 **Want more?** Check out [Catalog Audit Pro](https://catalogauditpro.com) for web-based audits, unlimited reports, and client-ready PDFs.

## Features

- 🤖 **Agent-Native** - CLI/JSON output designed for AI agent integration
- ⚡ **Fast** - Query 1000+ SKU catalogs in seconds
- 🔌 **Extensible** - Plugin system for custom queries
- 📊 **Comprehensive** - 9 built-in catalog health checks
- 🎯 **RUFUS Optimized** - Amazon AI shopping assistant bullet scoring

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

```bash
# Run all catalog checks
catalog scan my-catalog.xlsx

# Run specific check
catalog check missing-attributes my-catalog.xlsx

# Export results as JSON (for agents)
catalog scan my-catalog.xlsx --format json --output results.json

# List available queries
catalog list-queries my-catalog.xlsx
```

## Available Queries

### Attribute Audits
- **missing-attributes** - Find mandatory attributes missing from listings
- **missing-any-attributes** - Find all missing attributes (required + conditional)
- **new-attributes** - Find unused template fields that might add value

### Content Quality
- **rufus-bullets** - Score bullet points against Amazon's RUFUS AI framework
- **long-titles** - Find titles exceeding 200 characters
- **title-prohibited-chars** - Find titles with prohibited characters
- **prohibited-chars** - Find prohibited characters in any field

### Catalog Structure
- **product-type-mismatch** - Find mismatched product types and item keywords
- **missing-variations** - Find products that should be variations but aren't

## Usage Examples

### For Humans

```bash
# Quick scan with summary
catalog scan my-catalog.xlsx

# Detailed results
catalog scan my-catalog.xlsx --show-details

# Check specific issue
catalog check rufus-bullets my-catalog.xlsx
```

### For AI Agents

```bash
# JSON output for agent parsing
catalog scan my-catalog.xlsx --format json

# CSV export for spreadsheet analysis
catalog scan my-catalog.xlsx --format csv --output audit.csv

# Single query with structured output
catalog check missing-attributes my-catalog.xlsx --format json
```

### Example JSON Output

```json
{
  "timestamp": "2026-02-21T10:30:00Z",
  "total_queries": 9,
  "total_issues": 47,
  "total_affected_skus": 23,
  "queries": [
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
          "product_type": "HAIR_STYLING_AGENT"
        }
      ]
    }
  ]
}
```

## CLI Commands

### `catalog scan`
Run all queries on a CLR file.

```bash
catalog scan <clr-file> [OPTIONS]

Options:
  --format [terminal|json|csv]  Output format (default: terminal)
  --output PATH                 Output file path
  --show-details / --no-details Show detailed results
```

### `catalog check`
Run a specific query.

```bash
catalog check <query-name> <clr-file> [OPTIONS]

Options:
  --format [terminal|json|csv]  Output format (default: terminal)
  --output PATH                 Output file path
  --show-details / --no-details Show detailed results
```

### `catalog list-queries`
List available queries.

```bash
catalog list-queries <clr-file>
```

## Agent Integration

This tool is designed for AI agent workflows:

```python
import subprocess
import json

# Run scan and parse results
result = subprocess.run(
    ['catalog', 'scan', 'my-catalog.xlsx', '--format', 'json'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)

# Agent can now process catalog issues
for query in data['queries']:
    if query['total_issues'] > 0:
        print(f"Found {query['total_issues']} issues in {query['query_name']}")
```

## RUFUS Bullet Optimization

The `rufus-bullets` query evaluates bullet points against Amazon's RUFUS AI framework:

- **Bullet 1**: Should lead with Hero Benefit (why buy this?)
- **Bullet 2**: Should state who it's for (target audience)
- **Bullet 3**: Should differentiate (why this vs. competitors?)
- **All bullets**: Checked for specifics, length, vague marketing, ALL CAPS

Scores 1-5 with actionable suggestions.

## Extending with Custom Queries

Create a new query plugin:

```python
from catalog.query_engine import QueryPlugin

class MyCustomQuery(QueryPlugin):
    name = "my-custom-check"
    description = "My custom catalog check"
    
    def execute(self, listings, clr_parser):
        issues = []
        
        for listing in listings:
            # Your logic here
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

Register in `cli.py` and it's instantly available.

## Requirements

- Python 3.7+
- openpyxl
- click
- rich

## How to Get Your CLR

1. Go to **Amazon Seller Central** → **Catalog** → **Category Listing Report**
2. Click **Generate Report**
3. Download the `.xlsm` or `.xlsx` file
4. Run catalog CLI on it

## Contributing

This is an open-source project. Contributions welcome!

- Add new query plugins
- Improve parsing logic
- Enhance output formats
- Build integrations

## Roadmap

### v1.1
- Excel export (formatted like CLR Auditor)
- Natural language query parsing
- Query result caching

### v2.0
- Query composition ("missing attributes AND rufus score <3")
- Saved query templates
- Diff mode (compare two CLRs)
- Watch mode (monitor CLR file for changes)

## License

MIT License - Free to use, modify, and distribute.

## Author

Built by Brett Bohannon ([@BWB03](https://github.com/BWB03))

Amazon consulting veteran, AI automation enthusiast, open-source believer.

## Related Projects

- [clr-auditor](https://github.com/BWB03/clr-auditor) - Original CLR auditing tool
- [amazon-tool](https://github.com/BWB03/amazon-tool) - Amazon variation creator

---

**First AI-agent-friendly Amazon catalog tool.** Built for the future of catalog management.
