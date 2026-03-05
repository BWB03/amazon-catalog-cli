"""
Input validation and hardening for Catalog CLI.
Rejects path traversal, control characters, and malformed inputs.
"""

import re
import os


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def validate_file_path(path: str) -> str:
    """Validate a file path for safety.

    Rejects:
    - Path traversal (.. components)
    - Absolute paths (starting with /)
    - Home directory expansion (~)
    - Control characters
    - Null bytes
    """
    if not path:
        raise ValidationError("File path cannot be empty")

    # Reject null bytes
    if "\x00" in path:
        raise ValidationError("File path contains null bytes")

    # Reject control characters
    if re.search(r"[\x01-\x1f\x7f]", path):
        raise ValidationError("File path contains control characters")

    # Reject path traversal
    normalized = os.path.normpath(path)
    if ".." in normalized.split(os.sep):
        raise ValidationError("Path traversal (..) is not allowed")

    # Reject absolute paths
    if os.path.isabs(path):
        raise ValidationError("Absolute paths are not allowed")

    # Reject home directory expansion
    if path.startswith("~"):
        raise ValidationError("Home directory expansion (~) is not allowed")

    return path


def validate_query_name(name: str) -> str:
    """Validate a query name.

    Only allows alphanumeric characters, hyphens, and underscores.
    """
    if not name:
        raise ValidationError("Query name cannot be empty")

    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValidationError(
            f"Invalid query name '{name}': only alphanumeric, hyphens, and underscores allowed"
        )

    return name


def validate_sku(sku: str) -> str:
    """Validate a SKU format.

    Rejects:
    - Control characters
    - URL-unsafe characters (?, #, %)
    """
    if not sku:
        raise ValidationError("SKU cannot be empty")

    if re.search(r"[\x00-\x1f\x7f]", sku):
        raise ValidationError("SKU contains control characters")

    bad_chars = set(sku) & set("?#%")
    if bad_chars:
        raise ValidationError(
            f"SKU contains invalid characters: {', '.join(bad_chars)}"
        )

    return sku
