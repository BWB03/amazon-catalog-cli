"""Compare Seller Central listing copy with a Category Listing Report."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from email.message import Message
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from .models import (
    SellerListingDiscrepancy,
    SellerListingFetchRequest,
    SellerListingMonitorResponse,
    SellerListingMonitorRow,
)
from .parser import CLRParser
from .seller_central import fetch_seller_listing, resolve_cookie
from .validation import ValidationError, validate_asin


_ATTRIBUTES = {
    "item_name": ("Title", "Item Name"),
    "brand": ("Brand", "Brand Name"),
    "product_description": ("Product Description",),
    "bullet_point": ("Bullet Point",),
}
_ATTRIBUTE_ID = re.compile(r"([a-z_]+)(?:#[1-9][0-9]*)?(?:\.value)?$", re.IGNORECASE)
_SELECTOR = re.compile(r"\[[^\]]*\]")
_BULLET_LABEL = re.compile(r"Bullet Point(?:\s+([1-9][0-9]*))?$", re.IGNORECASE)
_MAX_CLR_BYTES = 50 * 1024 * 1024


def download_catalog_source(catalog_id: UUID, api_key: str) -> tuple[str, bytes]:
    """Retrieve the original workbook in an authenticated Catalog CLI Pro upload."""
    if not re.fullmatch(r"[!-~]+", api_key):
        raise ValidationError("The Catalog CLI Pro API key contains invalid characters.")
    url = f"https://api.catalogcli.com/v1/catalogs/{catalog_id}/source"
    request = Request(url)
    request.add_unredirected_header("X-API-Key", api_key)
    try:
        with urlopen(request, timeout=30) as response:
            if response.geturl() != url:
                raise ValidationError("Catalog CLI Pro redirected the source request.")
            headers = Message()
            headers["Content-Disposition"] = response.headers.get("Content-Disposition", "")
            data = response.read(_MAX_CLR_BYTES + 1)
            if len(data) > _MAX_CLR_BYTES:
                raise ValidationError("The uploaded CLR exceeds the 50 MB limit.")
            return headers.get_filename() or str(catalog_id), data
    except HTTPError as exc:
        raise ValidationError(f"Catalog CLI Pro could not return the uploaded CLR (HTTP {exc.code}).") from None
    except (URLError, TimeoutError):
        raise ValidationError("Catalog CLI Pro source download failed.") from None


def _field_name(field_id: str, label: str, *, use_title: bool = True) -> str | None:
    field_id = _SELECTOR.sub("", field_id).lower()
    match = _ATTRIBUTE_ID.fullmatch(field_id)
    if match and match[1] in _ATTRIBUTES:
        if match[1] == "bullet_point":
            slot = field_id.partition("#")[2].partition(".")[0] or "1"
            return f"Bullet Point {slot}"
        return _ATTRIBUTES[match[1]][0]

    bullet = _BULLET_LABEL.fullmatch(label)
    if bullet:
        return f"Bullet Point {bullet[1] or '1'}"
    for names in _ATTRIBUTES.values():
        if label.casefold() in (name.casefold() for name in names):
            if use_title or label.casefold() != "title":
                return names[0]
    return None


def _copy_columns(parser: CLRParser) -> dict[str, int]:
    """Resolve row 5 IDs so duplicate display labels retain their bullet slots."""
    columns = {}
    fallback_title = None
    labels = parser.template_sheet[parser.ROW_COL_HEADERS]
    field_ids = parser.template_sheet[parser.ROW_FIELD_IDS]
    for column, (label_cell, id_cell) in enumerate(zip(labels, field_ids), 1):
        label = str(label_cell.value or "").strip()
        field_id = str(id_cell.value or "").strip()
        name = _field_name(field_id, label, use_title=False)
        if name:
            columns.setdefault(name, column)
        elif label.casefold() == "title":
            fallback_title = column
    if fallback_title is not None:
        columns.setdefault("Title", fallback_title)
    return columns


def _clr_asin(fields: dict[str, Any]) -> str | None:
    fields = {field.casefold(): value for field, value in fields.items()}
    value = fields.get("asin")
    if not value and str(fields.get("product id type", "")).strip().upper() == "ASIN":
        value = fields.get("product id")
    try:
        return validate_asin(str(value or ""))
    except ValidationError:
        return None


def _copy_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _normalized(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def _live_copy(display: dict, imsv3: dict | None) -> dict[str, str | None]:
    fields = {}
    for field_id, payload in display.items():
        if isinstance(payload, dict):
            if "value" not in payload:
                continue
            label = str(payload.get("displayLabel") or "").strip()
            value = payload["value"]
        else:
            label, value = field_id, payload
        name = _field_name(field_id, label)
        if name and (value is None or isinstance(value, str)):
            fields.setdefault(name, _copy_text(value))

    for attribute, names in _ATTRIBUTES.items():
        entries = (imsv3 or {}).get(attribute)
        if not isinstance(entries, list):
            continue
        for slot, entry in enumerate(entries, 1):
            if isinstance(entry, dict) and isinstance(entry.get("value"), str):
                name = f"Bullet Point {slot}" if attribute == "bullet_point" else names[0]
                fields.setdefault(name, _copy_text(entry["value"]))
    return fields


def monitor_seller_listings(
    file: str,
    *,
    asins: tuple[str, ...] = (),
    cookie_file: str | None = None,
    timeout: float = 20,
    catalog_id: str | None = None,
    baseline: str,
) -> SellerListingMonitorResponse:
    """Fetch each selected ASIN once and compare all matching CLR SKUs."""
    selected = set(asins)
    parser = CLRParser(file)
    report = SellerListingMonitorResponse(
        baseline=baseline,
        catalog_id=catalog_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        marketplace=parser.get_marketplace(),
        status="failed",
    )
    try:
        if not parser.is_us_marketplace():
            report.error = "Seller Central monitoring currently supports US CLRs."
            return report
        listings = parser.get_listings(skip_fbm_duplicates=False)
        report.report_rows = len(listings)
        columns = _copy_columns(parser)
        if not columns:
            report.error = "The CLR does not contain supported listing content columns."
            return report

        targets = {}
        for listing in listings:
            asin = _clr_asin(listing.all_fields)
            if asin is None:
                report.rows_without_asin.append(listing.sku)
            elif not selected or asin in selected:
                targets[listing.row_number] = (asin, listing.sku)

        groups = defaultdict(list)
        if targets:
            rows = parser.template_sheet.iter_rows(
                min_row=min(targets), max_row=max(targets),
                max_col=max(columns.values()), values_only=True,
            )
            for row_number, values in enumerate(rows, min(targets)):
                if row_number not in targets:
                    continue
                asin, sku = targets[row_number]
                copy = {name: _copy_text(values[column - 1]) for name, column in columns.items()}
                groups[asin].append((row_number, sku, copy))
    finally:
        parser.workbook.close()

    report.unmatched_asins = sorted(selected - groups.keys())
    if not groups:
        report.error = (
            "No CLR rows matched the requested ASINs."
            if selected else "No CLR rows had an explicit ASIN."
        )
        return report

    cookie = resolve_cookie(cookie_file=cookie_file)
    if not cookie:
        report.error = "A local Seller Central session is required. Set CATALOG_SELLER_CENTRAL_COOKIE or use --cookie-file."
        report.unchecked_asins = dict.fromkeys(groups, "auth_required")
        return report
    if not re.fullmatch(r"[ -~]+", cookie):
        report.error = "The Seller Central cookie contains invalid characters."
        report.unchecked_asins = dict.fromkeys(groups, "auth_required")
        return report

    blocked = None
    for asin, rows in groups.items():
        if blocked:
            report.unchecked_asins[asin] = blocked
            continue
        response = fetch_seller_listing(SellerListingFetchRequest(asin=asin, cookie=cookie, timeout=timeout))
        if response.status != "success":
            reason = f"HTTP {response.status_code}" if response.status == "http_error" else response.status
            report.unchecked_asins[asin] = reason
            if response.status == "auth_required" or response.status_code == 429:
                blocked = reason
                report.error = response.error
            continue
        live = _live_copy(response.display_fields, response.parsed_imsv3)
        if not live.keys() & columns.keys():
            report.unchecked_asins[asin] = "no_comparable_amazon_fields"
            continue

        for row, sku, copy in rows:
            result = SellerListingMonitorRow(asin=asin, sku=sku, row=row)
            for name, clr_value in copy.items():
                if name not in live:
                    if clr_value is not None:
                        result.unavailable_fields.append(name)
                    continue
                amazon_value = live[name]
                result.compared_fields += 1
                if _normalized(clr_value) != _normalized(amazon_value):
                    result.discrepancies.append(SellerListingDiscrepancy(
                        field=name, clr_value=clr_value, amazon_value=amazon_value,
                    ))
            report.results.append(result)

    if report.results:
        report.status = "partial" if report.unchecked_asins or report.unmatched_asins else "complete"
    return report
