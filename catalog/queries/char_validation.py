"""
Character validation queries
"""

from ..query_engine import QueryPlugin


PROHIBITED_CHARS = set("!$?_{}^¬¦<>")


class ProhibitedCharsQuery(QueryPlugin):
    """Find any fields with prohibited characters"""
    
    name = "prohibited-chars"
    description = "Find listings with prohibited characters in any field"
    
    # Fields to check
    CHECK_FIELDS = [
        'Title', 'Item Name', 'Brand', 'Bullet Point 1', 'Bullet Point 2',
        'Bullet Point 3', 'Bullet Point 4', 'Bullet Point 5', 'Product Description'
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
