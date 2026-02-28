"""
Character validation queries
"""

from ..query_engine import QueryPlugin


PROHIBITED_CHARS = set("!$?_{}^¬¦<>")


class ProhibitedCharsQuery(QueryPlugin):
    """
    Find prohibited characters in Title, Brand, and Item Name.
    
    Note: Bullet points have separate, more comprehensive validation
    (see bullet-prohibited-content query). Product Description excluded
    (has different content rules).
    """
    
    name = "prohibited-chars"
    description = "Find listings with basic prohibited characters in title/brand"
    
    # Fields to check (general fields only, NOT bullets or description)
    CHECK_FIELDS = [
        'Title',
        'Item Name',
        'Brand',
    ]
    
    def execute(self, listings, clr_parser):
        issues = []
        
        for listing in listings:
            for field_name in self.CHECK_FIELDS:
                value = listing.all_fields.get(field_name, "")
                
                if not value:
                    continue
                
                found_chars = set(str(value)) & PROHIBITED_CHARS
                
                if found_chars:
                    issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': field_name,
                        'severity': 'warning',
                        'details': f"Field '{field_name}' contains prohibited characters: {', '.join(found_chars)}",
                        'product_type': listing.product_type,
                        'prohibited_chars': list(found_chars)
                    })
        
        return issues
