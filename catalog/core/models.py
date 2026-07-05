"""
Pydantic request/response models for Catalog CLI.
These serve triple duty: CLI validation, MCP type contracts, and auto-generated schemas.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from .validation import validate_asin, validate_file_path, validate_query_name, validate_sku


class ScanRequest(BaseModel):
    """Request model for scanning a CLR file with all/selected queries."""
    file: str = Field(..., description="Path to CLR file (.xlsx or .xlsm)")
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
    file: str = Field(..., description="Path to CLR file (.xlsx or .xlsm)")
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


class SellerListingFetchRequest(BaseModel):
    """Request model for fetching Seller Central listing JSON by ASIN."""
    asin: str = Field(..., description="ASIN to look up in Seller Central")
    cookie: str | None = Field(None, description="Seller Central Cookie header value")
    cookie_file: str | None = Field(None, description="Path to a file containing the Cookie header value")
    timeout: float = Field(20.0, gt=0, le=120, description="HTTP timeout in seconds")
    format: Literal["json", "terminal"] = Field("json", description="Output format")

    @field_validator("asin")
    @classmethod
    def validate_request_asin(cls, v: str) -> str:
        return validate_asin(v)

    @field_validator("cookie_file")
    @classmethod
    def validate_cookie_file(cls, v: str | None) -> str | None:
        return validate_file_path(v) if v else v


class SellerListingFetchResponse(BaseModel):
    """Response from Seller Central listing JSON fetch."""
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    asin: str
    endpoint: str
    status: Literal["success", "auth_required", "http_error", "parse_error", "request_error"]
    status_code: int | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
    display_fields: dict[str, Any] = Field(default_factory=dict)
    parsed_imsv3: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class SellerListingDiffRequest(SellerListingFetchRequest):
    """Request model for comparing Seller Central listing JSON with a CLR row."""
    file: str = Field(..., description="Path to CLR file (.xlsx or .xlsm)")
    sku: str | None = Field(None, description="Optional SKU to match in the CLR")

    @field_validator("file")
    @classmethod
    def validate_file(cls, v: str) -> str:
        return validate_file_path(v)

    @field_validator("sku")
    @classmethod
    def validate_optional_sku(cls, v: str | None) -> str | None:
        return validate_sku(v) if v else v


class SellerListingDiffResponse(BaseModel):
    """Response from comparing Seller Central listing JSON with a CLR row."""
    asin: str
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: Literal["success", "auth_required", "http_error", "parse_error", "request_error", "no_clr_match"]
    fetch: SellerListingFetchResponse
    clr_match: dict[str, Any] | None = None
    amazon_only: dict[str, Any] = Field(default_factory=dict)
    clr_only: dict[str, Any] = Field(default_factory=dict)
    value_mismatches: list[dict[str, Any]] = Field(default_factory=list)
    missing_on_amazon: list[str] = Field(default_factory=list)
    missing_in_clr: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class QueryInfo(BaseModel):
    """Metadata about an available query."""
    name: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    severity_levels: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
    example_usage: str = ""


class SchemaResponse(BaseModel):
    """Response from schema introspection."""
    queries: list[QueryInfo] = Field(default_factory=list)
    request_schema: dict[str, Any] = Field(default_factory=dict)
    response_schema: dict[str, Any] = Field(default_factory=dict)
