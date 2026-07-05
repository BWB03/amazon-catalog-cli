"""Seller Central listing AJAX lookup and CLR diff helpers."""

from __future__ import annotations

import json
import os
import re
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import (
    SellerListingDiffRequest,
    SellerListingDiffResponse,
    SellerListingFetchRequest,
    SellerListingFetchResponse,
)
from .parser import CLRParser, Listing


SELLER_CENTRAL_COOKIE_ENV = "CATALOG_SELLER_CENTRAL_COOKIE"
SELLER_CENTRAL_BASE_URL = "https://sellercentral.amazon.com/abis/ajax/reconciledDetailsV2"


@dataclass
class HttpResult:
    """Minimal HTTP result used to keep urllib replaceable in tests."""

    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str


def build_reconciled_details_url(asin: str) -> str:
    """Build the Seller Central reconciled details AJAX URL."""
    return f"{SELLER_CENTRAL_BASE_URL}?{urlencode({'asin': asin})}"


def resolve_cookie(cookie: str | None = None, cookie_file: str | None = None) -> str | None:
    """Resolve a Seller Central cookie from explicit input, file, or env var."""
    if cookie and cookie.strip():
        return cookie.strip()

    if cookie_file:
        with open(cookie_file, encoding="utf-8") as f:
            file_cookie = f.read().strip()
        if file_cookie:
            return file_cookie

    env_cookie = os.environ.get(SELLER_CENTRAL_COOKIE_ENV, "").strip()
    return env_cookie or None


def _http_get(url: str, cookie: str, timeout: float) -> HttpResult:
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Cookie": cookie,
        "User-Agent": "CatalogCLI/2.2 SellerCentralLookup",
        "X-Requested-With": "XMLHttpRequest",
    }
    request = Request(url, headers=headers, method="GET")

    try:
        with urlopen(request, timeout=timeout) as response:
            return HttpResult(
                status_code=response.getcode(),
                headers=dict(response.headers.items()),
                body=response.read(),
                url=response.geturl(),
            )
    except HTTPError as e:
        return HttpResult(
            status_code=e.code,
            headers=dict(e.headers.items()) if e.headers else {},
            body=e.read(),
            url=url,
        )


def fetch_seller_listing(request: SellerListingFetchRequest) -> SellerListingFetchResponse:
    """Fetch and parse Seller Central's reconciled listing details JSON."""
    endpoint = build_reconciled_details_url(request.asin)
    cookie = resolve_cookie(request.cookie, request.cookie_file)

    if not cookie:
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="auth_required",
            error=(
                "Seller Central cookie is required. Pass --cookie, --cookie-file, "
                f"or set {SELLER_CENTRAL_COOKIE_ENV}."
            ),
        )

    try:
        http_result = _http_get(endpoint, cookie, request.timeout)
    except (TimeoutError, socket.timeout):
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="request_error",
            error="Seller Central request timed out.",
        )
    except URLError as e:
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="request_error",
            error=f"Seller Central request failed: {_safe_error_message(e.reason)}",
        )
    except OSError as e:
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="request_error",
            error=f"Seller Central request failed: {_safe_error_message(e)}",
        )

    text = http_result.body.decode("utf-8", errors="replace").strip()

    if http_result.status_code in (401, 403):
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="auth_required",
            status_code=http_result.status_code,
            error="Seller Central rejected the request. Refresh the logged-in cookie and try again.",
        )

    if http_result.status_code >= 400:
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="http_error",
            status_code=http_result.status_code,
            error=f"Seller Central returned HTTP {http_result.status_code}.",
        )

    if _looks_like_login_or_html(text, http_result.headers):
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="auth_required",
            status_code=http_result.status_code,
            error="Seller Central returned a login or HTML page. Refresh the logged-in cookie and try again.",
        )

    try:
        raw_response = json.loads(text)
    except json.JSONDecodeError:
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="parse_error",
            status_code=http_result.status_code,
            error="Seller Central response was not valid JSON.",
        )

    if not isinstance(raw_response, dict):
        return SellerListingFetchResponse(
            asin=request.asin,
            endpoint=endpoint,
            status="parse_error",
            status_code=http_result.status_code,
            error="Seller Central JSON response was not an object.",
        )

    display_fields = _extract_display_fields(raw_response)
    parsed_imsv3, warnings = _parse_imsv3(raw_response)

    return SellerListingFetchResponse(
        asin=request.asin,
        endpoint=endpoint,
        status="success",
        status_code=http_result.status_code,
        raw_response=raw_response,
        display_fields=display_fields,
        parsed_imsv3=parsed_imsv3,
        warnings=warnings,
    )


def diff_seller_listing(request: SellerListingDiffRequest) -> SellerListingDiffResponse:
    """Fetch Seller Central listing JSON and compare it to a matched CLR row."""
    fetch_response = fetch_seller_listing(
        SellerListingFetchRequest(
            asin=request.asin,
            cookie=request.cookie,
            cookie_file=request.cookie_file,
            timeout=request.timeout,
            format="json",
        )
    )

    if fetch_response.status != "success":
        return SellerListingDiffResponse(
            asin=request.asin,
            fetched_at=fetch_response.fetched_at,
            status=fetch_response.status,
            fetch=fetch_response,
            warnings=fetch_response.warnings,
            error=fetch_response.error,
        )

    parser = CLRParser(request.file)
    listings = parser.get_listings(skip_fbm_duplicates=False)
    match = _find_listing_match(listings, request.asin, request.sku)

    if not match:
        return SellerListingDiffResponse(
            asin=request.asin,
            fetched_at=datetime.now().isoformat(),
            status="no_clr_match",
            fetch=fetch_response,
            warnings=fetch_response.warnings,
            error="No CLR row matched the requested ASIN/SKU.",
        )

    amazon_fields = _flatten_amazon_display_fields(fetch_response.display_fields)
    clr_fields = _flatten_clr_fields(match.all_fields)

    amazon_by_norm = {_normalize_field_name(k): (k, v) for k, v in amazon_fields.items()}
    clr_by_norm = {_normalize_field_name(k): (k, v) for k, v in clr_fields.items()}

    amazon_only: dict[str, Any] = {}
    clr_only: dict[str, Any] = {}
    mismatches: list[dict[str, Any]] = []

    for norm_name, (amazon_name, amazon_value) in amazon_by_norm.items():
        if norm_name not in clr_by_norm:
            amazon_only[amazon_name] = amazon_value
            continue

        clr_name, clr_value = clr_by_norm[norm_name]
        if _normalize_value(amazon_value) != _normalize_value(clr_value):
            mismatches.append(
                {
                    "field": clr_name,
                    "amazon_field": amazon_name,
                    "clr_value": clr_value,
                    "amazon_value": amazon_value,
                }
            )

    for norm_name, (clr_name, clr_value) in clr_by_norm.items():
        if norm_name not in amazon_by_norm:
            clr_only[clr_name] = clr_value

    return SellerListingDiffResponse(
        asin=request.asin,
        fetched_at=datetime.now().isoformat(),
        status="success",
        fetch=fetch_response,
        clr_match={
            "row": match.row_number,
            "sku": match.sku,
            "product_type": match.product_type,
            "title": match.title,
        },
        amazon_only=amazon_only,
        clr_only=clr_only,
        value_mismatches=mismatches,
        missing_on_amazon=sorted(clr_only.keys()),
        missing_in_clr=sorted(amazon_only.keys()),
        warnings=fetch_response.warnings,
    )


def _extract_display_fields(raw_response: dict[str, Any]) -> dict[str, Any]:
    display_fields = raw_response.get("detailPageListingResponse", {})
    return display_fields if isinstance(display_fields, dict) else {}


def _parse_imsv3(raw_response: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    value = raw_response.get("detailPageListingResponseImsv3")

    if value in (None, ""):
        warnings.append("detailPageListingResponseImsv3 was not present.")
        return None, warnings

    if isinstance(value, dict):
        return value, warnings

    if not isinstance(value, str):
        warnings.append("detailPageListingResponseImsv3 was not a JSON string.")
        return None, warnings

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        warnings.append("detailPageListingResponseImsv3 could not be parsed as JSON.")
        return None, warnings

    if not isinstance(parsed, dict):
        warnings.append("detailPageListingResponseImsv3 parsed JSON was not an object.")
        return None, warnings

    return parsed, warnings


def _looks_like_login_or_html(text: str, headers: dict[str, str]) -> bool:
    content_type = ""
    for key, value in headers.items():
        if key.lower() == "content-type":
            content_type = value.lower()
            break

    lowered = text[:2000].lower()
    return (
        "text/html" in content_type
        or lowered.startswith("<!doctype html")
        or lowered.startswith("<html")
        or "sellercentral.amazon.com/ap/signin" in lowered
        or "sign in" in lowered and "amazon" in lowered
    )


def _safe_error_message(value: object) -> str:
    message = str(value)
    return re.sub(r"Cookie:?\s*[^\n\r]+", "Cookie: [redacted]", message, flags=re.IGNORECASE)


def _find_listing_match(listings: list[Listing], asin: str, sku: str | None) -> Listing | None:
    if sku:
        for listing in listings:
            if listing.sku == sku:
                return listing
        return None

    for listing in listings:
        product_id_type = _get_case_insensitive(listing.all_fields, "Product Id Type")
        product_id = _get_case_insensitive(listing.all_fields, "Product Id")
        if product_id_type and product_id:
            if product_id_type.strip().upper() == "ASIN" and product_id.strip().upper() == asin:
                return listing

    return None


def _get_case_insensitive(values: dict[str, Any], field_name: str) -> str | None:
    for key, value in values.items():
        if key.strip().lower() == field_name.lower():
            return str(value) if value is not None else None
    return None


def _flatten_amazon_display_fields(display_fields: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}

    for field_id, field_payload in display_fields.items():
        label = field_id
        value: Any = field_payload

        if isinstance(field_payload, dict):
            label = field_payload.get("displayLabel") or field_id
            value = field_payload.get("value")

        if value is None or str(value).strip() == "":
            continue

        label = str(label).strip()
        if label in flattened and flattened[label] != value:
            label = field_id
        flattened[label] = value

    return flattened


def _flatten_clr_fields(all_fields: dict[str, Any]) -> dict[str, Any]:
    flattened = {}
    for key, value in all_fields.items():
        if value is None or str(value).strip() == "":
            continue
        flattened[str(key).strip()] = value
    return flattened


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _normalize_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return re.sub(r"\s+", " ", str(value).strip()).lower()
