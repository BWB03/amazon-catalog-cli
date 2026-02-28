# Changelog

All notable changes to Catalog CLI Light will be documented in this file.

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
