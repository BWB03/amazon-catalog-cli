"""
Title validation queries
"""

from ..query_engine import QueryPlugin


MAX_TITLE_LENGTH = 200
PROHIBITED_TITLE_CHARS = set("!$?_{}^¬¦")


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
