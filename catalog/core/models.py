"""
Pydantic request/response models for Catalog CLI.
These serve triple duty: CLI validation, MCP type contracts, and auto-generated schemas.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from .validation import validate_file_path, validate_query_name, validate_sku


class ScanRequest(BaseModel):
    """Request model for scanning a CLR file with all/selected queries."""
    file: str = Field(..., description="Path to CLR file (.xlsx)")
    queries: list[str] | None = Field(None, description="Query names to run (None = all)")
    fields: list[str] | None = Field(None, description="Field mask - only return these fields in issues")
    limit: int | None = Field(None, ge=1, description="Max issues to return")
    offset: int | None = Field(None, ge=0, description="Skip first N issues")
    exclude_fbm: bool = Field(True, description="Exclude FBM/MFN duplicates (keep FBA)")
    format: Literal["json", "csv", "terminal", "ndjson"] = Field("json", description="Output format")

    @field_validator("file")
    @classmethod
    def validate_file(cls, v: str) -> str:
        return validate_file_path(v)

    @field_validator("queries")
    @classmethod
    def validate_queries(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            return [validate_query_name(q) for q in v]
        return v


class CheckRequest(BaseModel):
    """Request model for running a single query on a CLR file."""
    query: str = Field(..., description="Query name to run")
    file: str = Field(..., description="Path to CLR file (.xlsx)")
    fields: list[str] | None = Field(None, description="Field mask - only return these fields in issues")
    limit: int | None = Field(None, ge=1, description="Max issues to return")
    offset: int | None = Field(None, ge=0, description="Skip first N issues")
    exclude_fbm: bool = Field(True, description="Exclude FBM/MFN duplicates (keep FBA)")
    format: Literal["json", "csv", "terminal", "ndjson"] = Field("json", description="Output format")

    @field_validator("file")
    @classmethod
    def validate_file(cls, v: str) -> str:
        return validate_file_path(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return validate_query_name(v)


class QueryResultItem(BaseModel):
    """A single issue found by a query."""
    row: int = 0
    sku: str = ""
    field: str = ""
    severity: str = ""
    details: str = ""
    product_type: str = ""
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional query-specific data")


class QueryResultBlock(BaseModel):
    """Results from a single query execution."""
    query_name: str
    description: str
    total_issues: int
    affected_skus: int
    issues: list[QueryResultItem]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScanResponse(BaseModel):
    """Response from a scan operation."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    marketplace: str = "US"
    is_us_marketplace: bool = True
    total_queries: int = 0
    total_issues: int = 0
    total_affected_skus: int = 0
    results: list[QueryResultBlock] = Field(default_factory=list)


class CheckResponse(BaseModel):
    """Response from a check (single query) operation."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    marketplace: str = "US"
    is_us_marketplace: bool = True
    query_name: str = ""
    description: str = ""
    total_issues: int = 0
    affected_skus: int = 0
    issues: list[QueryResultItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryInfo(BaseModel):
    """Metadata about an available query."""
    name: str
    description: str
    severity_levels: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
    example_usage: str = ""


class SchemaResponse(BaseModel):
    """Response from schema introspection."""
    queries: list[QueryInfo] = Field(default_factory=list)
    request_schema: dict[str, Any] = Field(default_factory=dict)
    response_schema: dict[str, Any] = Field(default_factory=dict)
