"""
Core engine - shared entry point for all surfaces (CLI, MCP).
Both CLI and MCP call these functions.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .parser import CLRParser
from .query_engine import QueryEngine
from .models import (
    ScanRequest, ScanResponse, CheckRequest, CheckResponse,
    QueryInfo, QueryResultBlock, QueryResultItem, SchemaResponse,
)
from .schema import build_schema_response

if TYPE_CHECKING:
    from .query_engine import QueryResult


# All available query classes
def _get_all_query_classes():
    from catalog.queries import (
        MissingAttributesQuery,
        MissingAnyAttributesQuery,
        LongTitlesQuery,
        TitleProhibitedCharsQuery,
        RufusBulletsQuery,
        ProhibitedCharsQuery,
        ProductTypeMismatchQuery,
        MissingVariationsQuery,
        NewAttributesQuery,
        BulletProhibitedContentQuery,
        BulletFormattingQuery,
        BulletAwarenessQuery,
        HijackingDetectionQuery,
    )
    return [
        MissingAttributesQuery,
        MissingAnyAttributesQuery,
        LongTitlesQuery,
        TitleProhibitedCharsQuery,
        RufusBulletsQuery,
        ProhibitedCharsQuery,
        BulletProhibitedContentQuery,
        BulletFormattingQuery,
        BulletAwarenessQuery,
        ProductTypeMismatchQuery,
        MissingVariationsQuery,
        NewAttributesQuery,
        HijackingDetectionQuery,
    ]


def _build_engine(file: str, exclude_fbm: bool = True) -> QueryEngine:
    """Build a QueryEngine with all queries registered."""
    parser = CLRParser(file)
    engine = QueryEngine(parser, include_fbm_duplicates=not exclude_fbm)
    for cls in _get_all_query_classes():
        engine.register_query(cls())
    return engine


def _convert_result(result: QueryResult, fields: list[str] | None = None,
                    limit: int | None = None, offset: int | None = None) -> QueryResultBlock:
    """Convert a legacy QueryResult to a Pydantic QueryResultBlock."""
    # Standard fields that go into QueryResultItem directly
    STANDARD_FIELDS = {"row", "sku", "field", "severity", "details", "product_type"}

    items = []
    for issue in result.issues:
        std = {k: issue.get(k, "") for k in STANDARD_FIELDS}
        std["row"] = int(std["row"]) if std["row"] else 0
        extra = {k: v for k, v in issue.items() if k not in STANDARD_FIELDS}
        item = QueryResultItem(**std, extra=extra)

        # Apply field mask
        if fields:
            masked = {}
            for f in fields:
                if f in STANDARD_FIELDS and hasattr(item, f):
                    masked[f] = getattr(item, f)
                elif f in item.extra:
                    masked[f] = item.extra[f]
            item = QueryResultItem(
                row=masked.get("row", 0),
                sku=masked.get("sku", ""),
                field=masked.get("field", ""),
                severity=masked.get("severity", ""),
                details=masked.get("details", ""),
                product_type=masked.get("product_type", ""),
                extra={k: v for k, v in masked.items() if k not in STANDARD_FIELDS},
            )

        items.append(item)

    # Apply offset and limit
    if offset:
        items = items[offset:]
    if limit:
        items = items[:limit]

    return QueryResultBlock(
        query_name=result.query_name,
        description=result.query_description,
        total_issues=result.total_issues,
        affected_skus=result.affected_skus,
        issues=items,
        metadata=result.metadata,
    )


def execute_scan(request: ScanRequest) -> ScanResponse:
    """Run all/selected queries on a CLR file."""
    engine = _build_engine(request.file, request.exclude_fbm)

    if request.queries:
        raw_results = [engine.execute(q) for q in request.queries]
    else:
        raw_results = engine.execute_all()

    blocks = [
        _convert_result(r, request.fields, request.limit, request.offset)
        for r in raw_results
    ]

    marketplace = raw_results[0].metadata.get("marketplace", "US") if raw_results else "US"
    is_us = raw_results[0].metadata.get("is_us_marketplace", True) if raw_results else True

    return ScanResponse(
        marketplace=marketplace,
        is_us_marketplace=is_us,
        total_queries=len(blocks),
        total_issues=sum(r.total_issues for r in raw_results),
        total_affected_skus=sum(r.affected_skus for r in raw_results),
        results=blocks,
    )


def execute_check(request: CheckRequest) -> CheckResponse:
    """Run a single query on a CLR file."""
    engine = _build_engine(request.file, request.exclude_fbm)
    raw = engine.execute(request.query)
    block = _convert_result(raw, request.fields, request.limit, request.offset)

    return CheckResponse(
        marketplace=raw.metadata.get("marketplace", "US"),
        is_us_marketplace=raw.metadata.get("is_us_marketplace", True),
        query_name=block.query_name,
        description=block.description,
        total_issues=raw.total_issues,
        affected_skus=raw.affected_skus,
        issues=block.issues,
        metadata=block.metadata,
    )


def list_queries(file: str | None = None) -> list[QueryInfo]:
    """List available queries with metadata."""
    queries = []
    for cls in _get_all_query_classes():
        instance = cls()
        queries.append(QueryInfo(
            name=instance.name,
            description=instance.description,
        ))
    return queries


def get_schema(target: str | None = None) -> SchemaResponse:
    """Return schema for queries, params, response shapes."""
    return build_schema_response(target)
