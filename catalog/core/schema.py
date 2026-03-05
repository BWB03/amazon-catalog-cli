"""
Schema introspection for Catalog CLI.
Auto-generates schema from QueryPlugin metadata and Pydantic models.
"""

from __future__ import annotations

from .models import (
    ScanRequest, ScanResponse, CheckRequest, CheckResponse,
    QueryInfo, SchemaResponse,
)


def build_schema_response(target: str | None = None) -> SchemaResponse:
    """Build schema response, optionally filtered to a specific query."""
    from .engine import _get_all_query_classes

    queries = []
    for cls in _get_all_query_classes():
        instance = cls()
        info = QueryInfo(
            name=instance.name,
            description=instance.description,
            example_usage=f"catalog check {instance.name} <clr_file> --format json",
        )

        if target and instance.name != target:
            continue

        queries.append(info)

    return SchemaResponse(
        queries=queries,
        request_schema={
            "scan": ScanRequest.model_json_schema(),
            "check": CheckRequest.model_json_schema(),
        },
        response_schema={
            "scan": ScanResponse.model_json_schema(),
            "check": CheckResponse.model_json_schema(),
        },
    )
