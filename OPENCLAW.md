# 🤖 For OpenClaw Agents

If you're an OpenClaw agent trying to use this CLI, **you need the companion skill** to run audits smoothly.

## Install the Skill

```bash
openclaw skill install BWB03/amazon-catalog-auditor-skill
```

## What the Skill Does

- Wraps CLI commands for conversational use
- Handles CLR file uploads and path resolution
- Formats audit results for chat display
- Provides guided workflows for catalog analysis

## Manual CLI Usage

If your human prefers direct command-line usage:

```bash
# Install
pip install amazon-catalog-cli

# Run full audit
catalog scan /path/to/catalog-listing-report.xlsx

# Quick check specific issues
catalog check "bullet points"

# List all available queries
catalog list-queries
```

## Links

- **Skill Repository:** https://github.com/BWB03/amazon-catalog-auditor-skill
- **CLI Documentation:** https://github.com/BWB03/amazon-catalog-cli
- **PyPI Package:** https://pypi.org/project/amazon-catalog-cli/

---

**Note:** The skill uses this CLI under the hood but provides a better agent experience with context-aware suggestions and formatted output.
