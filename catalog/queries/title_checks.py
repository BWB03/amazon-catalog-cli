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

            issues.append({
                'row': listing.row_number,
                'sku': listing.sku,
                'field': 'Title',
                'severity': 'warning',
                'details': (
                    f"Title length {title_length} exceeds "
                    f"{MOBILE_TITLE_LENGTH} characters by {title_length - MOBILE_TITLE_LENGTH}"
                ),
                'product_type': listing.product_type,
                'title_char_count': title_length,
                'max_title_chars': MOBILE_TITLE_LENGTH,
                'over_by': title_length - MOBILE_TITLE_LENGTH,
                'mobile_visible_title': mobile_visible_title,
                'overflow_title': overflow_title,
                'priority_zone_terms': priority_terms,
                'overflow_terms': overflow_terms,
                'all_significant_terms': all_terms,
                'item_highlights_present': has_highlights,
                'item_highlights_char_count': highlights_length,
                'item_highlights_max_chars': ITEM_HIGHLIGHTS_LENGTH,
                'recommended_action': (
                    "Rewrite title to 75 characters or less, preserve the highest-value "
                    "terms, and move supporting detail into item highlights for human review."
                ),
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
