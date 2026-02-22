"""
Product Type / Item Type Keyword validation
"""

from ..query_engine import QueryPlugin


class ProductTypeMismatchQuery(QueryPlugin):
    """Find potential product type / item type keyword mismatches"""
    
    name = "product-type-mismatch"
    description = "Find potential mismatches between product type and item type keyword"
    
    def execute(self, listings, clr_parser):
        issues = []
        
        for listing in listings:
            if not listing.product_type or not listing.item_type:
                continue
            
            # Basic sanity check: look for word overlap
            pt_lower = listing.product_type.lower().replace("_", " ")
            kw_lower = listing.item_type.lower()
            
            pt_words = set(pt_lower.split())
            kw_words = set(kw_lower.split())
            
            overlap = pt_words & kw_words
            
            # Flag if no overlap and product type not in keyword
            if not overlap and pt_lower not in kw_lower:
                issues.append({
                    'row': listing.row_number,
                    'sku': listing.sku,
                    'field': 'Product Type / Item Type',
                    'severity': 'warning',
                    'details': f"Product type '{listing.product_type}' may not match item type keyword '{listing.item_type[:60]}'",
                    'product_type': listing.product_type,
                    'item_type': listing.item_type
                })
        
        return issues
