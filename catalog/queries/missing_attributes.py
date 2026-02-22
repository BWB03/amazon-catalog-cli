"""
Missing Attributes Queries
"""

from ..query_engine import QueryPlugin


class MissingAttributesQuery(QueryPlugin):
    """Find mandatory attributes missing from listings"""
    
    name = "missing-attributes"
    description = "Find mandatory (required) attributes missing from listings"
    
    def execute(self, listings, clr_parser):
        issues = []
        required_fields = clr_parser.get_required_fields()
        
        for listing in listings:
            for field in required_fields:
                value = listing.all_fields.get(field)
                
                # Check if field is empty
                if not value or str(value).strip() == "":
                    issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': field,
                        'severity': 'required',
                        'details': f"Missing required field: {field}",
                        'product_type': listing.product_type
                    })
        
        return issues


class MissingAnyAttributesQuery(QueryPlugin):
    """Find all missing attributes (required + conditional)"""
    
    name = "missing-any-attributes"
    description = "Find all missing attributes (required and conditional)"
    
    def execute(self, listings, clr_parser):
        issues = []
        required_fields = clr_parser.get_required_fields()
        conditional_fields = clr_parser.get_conditional_fields()
        all_check_fields = required_fields + conditional_fields
        
        for listing in listings:
            for field in all_check_fields:
                value = listing.all_fields.get(field)
                
                if not value or str(value).strip() == "":
                    severity = 'required' if field in required_fields else 'conditional'
                    issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': field,
                        'severity': severity,
                        'details': f"Missing {severity} field: {field}",
                        'product_type': listing.product_type
                    })
        
        return issues
