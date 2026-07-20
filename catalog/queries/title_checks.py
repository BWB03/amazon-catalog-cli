"""
Title validation queries
"""

import re

from ..query_engine import QueryPlugin


MAX_TITLE_LENGTH = 200
MOBILE_TITLE_LENGTH = 75
ITEM_HIGHLIGHTS_LENGTH = 125
PROHIBITED_TITLE_CHARS = set("!$?_{}^¬¦")
SIGNIFICANT_TERM_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
MEDIA_EXEMPT_CATEGORY_VALUES = {
    "book",
    "books",
    "books_1973_and_later",
    "music",
    "music_album",
    "music_track",
    "video",
    "video_dvd",
    "dvd",
    "blu_ray",
    "blu_ray_disc",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "your",
}


def _extract_significant_terms(text):
    """Extract deterministic title terms while preserving first-seen order."""
    terms = []
    seen = set()

    for match in SIGNIFICANT_TERM_RE.finditer((text or "").lower()):
        term = match.group(0).strip("'")
        if not term or term in STOPWORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)

    return terms


def _detect_item_highlights(all_fields):
    highlights = []

    for field_name, value in (all_fields or {}).items():
        normalized = str(field_name).strip().lower().replace("_", " ").replace("-", " ")
        if "item highlight" not in normalized:
            continue

        text = str(value or "").strip()
        if text:
            highlights.append(text)

    combined = " ".join(highlights).strip()
    return bool(combined), len(combined)


def _normalized_category_value(value):
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


def _title_limit_applicability(listing):
    """Classify the 75-character rule without guessing from title text."""
    category_values = {
        _normalized_category_value(listing.product_type),
        _normalized_category_value(listing.item_type),
    }
    category_values.discard("")

    if category_values & MEDIA_EXEMPT_CATEGORY_VALUES:
        return "likely_media_exempt"
    if not category_values:
        return "category_unverified"
    return "standard_limit"


class LongTitlesQuery(QueryPlugin):
    """Find titles exceeding 200 characters"""
    
    name = "long-titles"
    description = "Find titles exceeding 200 characters"
    
    def execute(self, listings, clr_parser):
        issues = []
        
        for listing in listings:
            if listing.title and len(listing.title) > MAX_TITLE_LENGTH:
                issues.append({
                    'row': listing.row_number,
                    'sku': listing.sku,
                    'field': 'Title',
                    'severity': 'warning',
                    'details': f"Title length {len(listing.title)} exceeds {MAX_TITLE_LENGTH} characters",
                    'product_type': listing.product_type,
                    'title': listing.title[:100] + "..."  # Truncated for display
                })
        
        return issues


class MobileTitleReadinessQuery(QueryPlugin):
    """Find titles that exceed Amazon's 75-character mobile title guidance"""

    name = "mobile-title-readiness"
    description = "Find titles over 75 characters and prepare title rewrite inputs"
    aliases = ["title-75", "amazon-title-75"]

    def execute(self, listings, clr_parser):
        issues = []

        for listing in listings:
            title = (listing.title or "").strip()
            title_length = len(title)

            if title_length <= MOBILE_TITLE_LENGTH:
                continue

            mobile_visible_title = title[:MOBILE_TITLE_LENGTH]
            overflow_title = title[MOBILE_TITLE_LENGTH:].strip()
            priority_terms = _extract_significant_terms(mobile_visible_title)
            overflow_terms = _extract_significant_terms(overflow_title)
            all_terms = _extract_significant_terms(title)
            has_highlights, highlights_length = _detect_item_highlights(listing.all_fields)
            applicability = _title_limit_applicability(listing)

            if applicability == "likely_media_exempt":
                severity = "info"
                details = (
                    f"Title length {title_length} exceeds {MOBILE_TITLE_LENGTH} characters, "
                    "but the listing appears to be in a media category; verify the exemption before rewriting"
                )
                recommended_action = (
                    "Verify the listing's media category before rewriting. "
                    "Media listings may be exempt from the 75-character limit."
                )
            elif applicability == "category_unverified":
                severity = "warning"
                details = (
                    f"Title length {title_length} exceeds {MOBILE_TITLE_LENGTH} characters by "
                    f"{title_length - MOBILE_TITLE_LENGTH}; confirm the listing is not media before rewriting"
                )
                recommended_action = (
                    "Confirm the listing is not in a media category, then rewrite the title to "
                    "75 characters or less and preserve the highest-value terms."
                )
            else:
                severity = "warning"
                details = (
                    f"Title length {title_length} exceeds "
                    f"{MOBILE_TITLE_LENGTH} characters by {title_length - MOBILE_TITLE_LENGTH}"
                )
                recommended_action = (
                    "Rewrite title to 75 characters or less, preserve the highest-value "
                    "terms, and move supporting detail into item highlights for human review."
                )

            issues.append({
                'row': listing.row_number,
                'sku': listing.sku,
                'field': 'Title',
                'severity': severity,
                'details': details,
                'product_type': listing.product_type,
                'original_title': title,
                'brand': listing.brand,
                'parent_sku': listing.parent_sku,
                'title_char_count': title_length,
                'max_title_chars': MOBILE_TITLE_LENGTH,
                'over_by': title_length - MOBILE_TITLE_LENGTH,
                'mobile_visible_title': mobile_visible_title,
                'overflow_title': overflow_title,
                'priority_zone_terms': priority_terms,
                'overflow_terms': overflow_terms,
                'all_significant_terms': all_terms,
                'title_limit_applicability': applicability,
                'item_highlights_present': has_highlights,
                'item_highlights_char_count': highlights_length,
                'item_highlights_max_chars': ITEM_HIGHLIGHTS_LENGTH,
                'item_highlights_remaining_chars': max(ITEM_HIGHLIGHTS_LENGTH - highlights_length, 0),
                'item_highlights_over_limit': highlights_length > ITEM_HIGHLIGHTS_LENGTH,
                'recommended_action': recommended_action,
            })

        return issues


class TitleProhibitedCharsQuery(QueryPlugin):
    """Find titles with prohibited characters"""
    
    name = "title-prohibited-chars"
    description = "Find titles containing prohibited characters (!$?_{}^¬¦)"
    
    def execute(self, listings, clr_parser):
        issues = []
        
        for listing in listings:
            if not listing.title:
                continue
            
            found_chars = set(listing.title) & PROHIBITED_TITLE_CHARS
            
            if found_chars:
                issues.append({
                    'row': listing.row_number,
                    'sku': listing.sku,
                    'field': 'Title',
                    'severity': 'warning',
                    'details': f"Title contains prohibited characters: {', '.join(found_chars)}",
                    'product_type': listing.product_type,
                    'prohibited_chars': list(found_chars)
                })
        
        return issues
