"""
Variation analysis query
"""

from ..query_engine import QueryPlugin
from collections import defaultdict


class MissingVariationsQuery(QueryPlugin):
    """Find products that should be variations but aren't"""
    
    name = "missing-variations"
    description = "Find products that might be missing variation relationships"
    
    def execute(self, listings, clr_parser):
        issues = []
        
        # Group by brand + base product name (strip size/color indicators)
        product_groups = defaultdict(list)
        
        for listing in listings:
            if not listing.brand or not listing.item_name:
                continue
            
            # Skip if already in a variation
            if listing.parentage and 'child' in listing.parentage.lower():
                continue
            
            # Create a normalized name (strip common variation indicators)
            normalized_name = self._normalize_product_name(listing.item_name)
            key = f"{listing.brand}::{normalized_name}"
            
            product_groups[key].append(listing)
        
        # Find groups with multiple standalone SKUs
        for key, group_listings in product_groups.items():
            if len(group_listings) > 1:
                # These might be variations
                skus = [l.sku for l in group_listings]
                
                for listing in group_listings:
                    issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': 'Variation',
                        'severity': 'info',
                        'details': f"May be a variation candidate. Found {len(group_listings)} similar products: {', '.join(skus)}",
                        'product_type': listing.product_type,
                        'similar_skus': skus
                    })
        
        return issues
    
    def _normalize_product_name(self, name: str) -> str:
        """Remove size/color/count indicators from product name"""
        import re
        
        # Remove common patterns
        name = re.sub(r'\b\d+\s*(oz|ml|lb|kg|g|count|pack|ct)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b(small|medium|large|xl|xxl|s|m|l)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b(black|white|red|blue|green|yellow|pink)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
