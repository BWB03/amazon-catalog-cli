# Changelog

All notable changes to Catalog CLI will be documented in this file.

## [2.1.0] - 2026-03-25

### Added
- **Hijacking detection** - New `hijacking-detection` query catches malicious content injection
  - Detects adult/sexual content terms injected by hijackers
  - Flags abusive/offensive language planted to trigger suppression
  - Identifies sabotage phrases ("do not buy", "scam", "counterfeit", etc.)
  - Scans titles, bullets, description, and search terms
  - `critical` severity - immediate action required

### Changed
- **RUFUS scoring rewrite** - Now evaluates bullets against the 3 core RUFUS questions, not just formatting
  - "Is this right for me?" — detects target user, lifestyle, and problem state signals
  - "What is the difference?" — detects differentiators, certifications, unique claims
  - "How do I use it?" — detects usage instructions, what's in the box, compatibility
  - New SKU-level coverage check reports which RUFUS questions are unanswered across all bullets
  - New FAQ-style check flags comma-separated feature dumps ("Stainless steel, BPA-free, 32oz")
  - Replaces old position-locked checks (bullet 1 = benefit, bullet 2 = audience, bullet 3 = differentiator)
  - All 5 bullets now get content-quality checks, not just bullets 1-3

### Fixed
- **RUFUS scoring bug** - Empty bullet points now return score 1 (minimum) instead of 0, keeping all scores in the documented 1-5 range

### Technical
- Total queries: 12 → 13
- Added `catalog/queries/hijacking_detection.py`
- Rewrote `catalog/queries/rufus_bullets.py`

---

## [2.0.0] - 2026-03-05

### Added
- **Shared core architecture** - Business logic in `catalog/core/`, powering both CLI and MCP surfaces
  - `core/engine.py` - Shared entry point (`execute_scan`, `execute_check`, `list_queries`, `get_schema`)
  - `core/models.py` - Pydantic request/response models (typed contracts for CLI, MCP, and schema generation)
  - `core/validation.py` - Input hardening (path traversal, control chars, SKU validation)
  - `core/schema.py` - Schema introspection auto-generated from Pydantic models
- **MCP server** - `catalog mcp` launches stdio MCP server with 4 tools
  - `catalog_scan`, `catalog_check`, `catalog_list_queries`, `catalog_schema`
  - Ready for Claude Desktop, CLR Pro, or any MCP client
- **JSON input** - `--json` flag and `--stdin` for structured agent input
  - `catalog scan --json '{"file": "report.xlsx", "queries": ["missing-attributes"], "limit": 10}'`
  - `echo '{"file": "report.xlsx"}' | catalog scan --stdin --format json`
- **Schema introspection** - `catalog schema [query_name] --format json`
  - Returns full request/response JSON schemas, query metadata, and example usage
- **Field masks** - `--fields sku,severity,details` to reduce output size for agents
- **Pagination** - `--limit` and `--offset` for controlling result size
- **NDJSON streaming** - `--format ndjson` for line-by-line JSON output
- **Environment variables** - `CATALOG_CLI_DEFAULT_FORMAT` for headless/CI use
- **SKILL.md** - Agent guidance file shipped with the package

### Changed
- Restructured into `catalog/core/` + `catalog/surfaces/` architecture
- Entry point moved to `catalog.surfaces.cli:cli` (old `catalog.cli:cli` still works via re-export)
- Parser and query engine moved to `catalog/core/` (old imports still work via re-export shims)
- FBM duplicate filter message now goes to stderr (clean stdout for JSON piping)
- Python minimum version bumped from 3.7 to 3.10
- Rebranded from "Catalog CLI Light" to "Catalog CLI"

### Added Dependencies
- `pydantic>=2.0.0` - Request/response models, validation, schema generation
- `mcp>=1.0.0` - MCP server framework

### Backward Compatibility
- All v1.x commands work unchanged
- `catalog scan file.xlsx`, `catalog check query file.xlsx`, `catalog list-queries` all preserved
- Old import paths (`catalog.parser`, `catalog.query_engine`, `catalog.cli`) re-export from new locations
- Query plugins unchanged

---

## [1.3.1] - 2026-03-03

### Fixed
- **SyntaxError on import** - Curly quote characters (\u201c \u201d) in `BulletAwarenessQuery.PROBLEMATIC_CHARS` were stored as ASCII double quotes, causing a `SyntaxError: invalid character` on Python 3.14. Fixed by using Unicode escape sequences.
- **Version sync** - `__init__.py` version now matches `setup.py` and CLI version

---

## [1.3.0] - 2026-03-03

### Added
- **Marketplace detection** - Auto-detects marketplace from CLR (US, CA, UK, DE, etc.)
  - `marketplace` field in JSON output
  - `is_us_marketplace` boolean flag
  - Useful for multi-marketplace workflows
- **Bullet awareness checks** - New `bullet-awareness` query for soft violations
  - Detects all caps at beginning (3+ consecutive words)
  - Flags excessive capitalization (>30% of text)
  - Identifies problematic special characters (unusual quotes, math symbols, arrows)
  - New `awareness` severity level - not critical, but worth reviewing
  
### Changed
- JSON output now includes marketplace metadata at top level
- Query results include marketplace in metadata

### Technical
- Total queries: 11 → 12
- Added `CLRParser.get_marketplace()` and `CLRParser.is_us_marketplace()` methods
- Added `BulletAwarenessQuery` to `catalog/queries/bullet_validation.py`

---

## [1.2.0] - 2026-02-27

### Added
- **Comprehensive bullet point validation** (2 new queries)
  - `bullet-prohibited-content` - Detects prohibited characters, emojis, placeholder text, banned claims, and guarantee language per Amazon requirements
  - `bullet-formatting` - Validates capitalization, length (10-255 chars), punctuation rules, and minimum bullet count
- **Pro upsell callout** in README - Links to Catalog Audit Pro web app
- **Rebranded as "Catalog CLI Light"** - Positions as free tier tool

### Changed
- **Fixed critical bug:** `prohibited-chars` query was incorrectly checking Product Description and applying bullet point rules
- `prohibited-chars` now only checks Title, Brand, and Item Name (basic validation)
- Bullet points now have dedicated, comprehensive validation separate from general fields
- Updated CLI description to "Catalog CLI Light - Free CLI for Amazon catalog auditing"

### Fixed
- **Corrected author name:** Brett Wilson → Brett Bohannon
- **Version display bug:** CLI now correctly shows v1.2.0 (previously showed 1.0.0 even when 1.1.0 was installed)

### Technical
- Total queries: 9 → 11
- Added `catalog/queries/bullet_validation.py` with two query classes
- Updated query registration in `cli.py`
- Removed Product Description from prohibited character checks (has different content rules)

---

## [1.1.0] - 2026-02-26

### Added
- **RUFUS tier scoring** - Each SKU gets Good/Fair/Weak/Critical rating (4-5/3-4/2-3/<2)
- **Catalog-wide summary** - Overall score + distribution stats ("12 Good, 8 Fair, 5 Weak, 2 Critical")
- **FBM duplicate filtering** - Auto-skips FBM/MFN versions, keeps FBA (default ON)
  - `--include-fbm-duplicates` flag to disable filtering
  - Smart detection by item name similarity (not just "_FBM_" suffix)

### Impact
- Cleaner reports (e.g., 5,904 → 2,952 issues by filtering duplicates)
- Better prioritization with tier-based scoring
- Faster audits by skipping redundant SKUs

---

## [1.0.0] - 2026-02-21

### Initial Release
- 9 built-in catalog health checks
- CLI and JSON output formats
- Agent-native design for AI workflow integration
- Fast query engine for 1000+ SKU catalogs
- Extensible plugin system

### Available Queries
1. missing-attributes
2. missing-any-attributes
3. long-titles
4. title-prohibited-chars
5. rufus-bullets
6. prohibited-chars
7. product-type-mismatch
8. missing-variations
9. new-attributes
