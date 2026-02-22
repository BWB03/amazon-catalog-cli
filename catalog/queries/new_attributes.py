"""
New/unused attributes detection
"""

from ..query_engine import QueryPlugin


class NewAttributesQuery(QueryPlugin):
    """Find template attributes that exist but aren't being used"""
    
    name = "new-attributes"
    description = "Find template attributes that aren't being used in any listings"
    
    def execute(self, listings, clr_parser):
        issues = []
        
        # Get all fields in template
        template_fields = set(clr_parser.headers.keys())
        
        # Track which fields are actually used
        used_fields = set()
        
        for listing in listings:
            for field_name, value in listing.all_fields.items():
                if value and str(value).strip():
                    used_fields.add(field_name)
        
        # Find unused fields
        unused_fields = template_fields - used_fields
        
        # Filter out fields that are typically unused
        ALWAYS_UNUSED = {
            'Status', 'Parent SKU', 'Parentage', 'Variation Theme',
            'Update Delete', 'Product Tax Code'
        }
        
        unused_fields = unused_fields - ALWAYS_UNUSED
        
        # Create a single issue summarizing all unused fields
        if unused_fields:
            issues.append({
                'row': 0,  # Not SKU-specific
                'sku': 'N/A',
                'field': 'Template Fields',
                'severity': 'info',
                'details': f"Found {len(unused_fields)} unused template fields that might be valuable",
                'product_type': 'N/A',
                'unused_fields': sorted(list(unused_fields))
            })
        
        return issues
