"""
Missing Attributes Queries
"""

from ..query_engine import QueryPlugin


def _skip_virtual_bundle_identifier(field, listing, clr_parser):
    return (
        hasattr(clr_parser, "is_product_identifier_field")
        and hasattr(clr_parser, "is_virtual_bundle_listing")
        and clr_parser.is_product_identifier_field(field)
        and clr_parser.is_virtual_bundle_listing(listing)
    )


def _skip_inactive_listing(listing, clr_parser):
    return (
        hasattr(clr_parser, "is_removed_or_delete_listing")
        and clr_parser.is_removed_or_delete_listing(listing)
    )


def _skip_copy_aware_blank(field, listing, clr_parser):
    if not hasattr(clr_parser, "alternate_record_with_value"):
        return False
    alternate = clr_parser.alternate_record_with_value(listing, field)
    if not alternate:
        return False
    if hasattr(clr_parser, "record_copy_aware_blank_review"):
        clr_parser.record_copy_aware_blank_review(listing, field, alternate)
    return True


class MissingAttributesQuery(QueryPlugin):
    """Find mandatory attributes missing from listings"""
    
    name = "missing-attributes"
    description = "Find mandatory (required) attributes missing from listings"
    
    def execute(self, listings, clr_parser):
        issues = []
        required_fields = clr_parser.get_required_fields()
        
        for listing in listings:
            if _skip_inactive_listing(listing, clr_parser):
                continue
            for field in required_fields:
                if _skip_virtual_bundle_identifier(field, listing, clr_parser):
                    continue

                value = listing.all_fields.get(field)
                
                # Check if field is empty
                if not value or str(value).strip() == "":
                    if _skip_copy_aware_blank(field, listing, clr_parser):
                        continue
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
            if _skip_inactive_listing(listing, clr_parser):
                continue
            for field in all_check_fields:
                if _skip_virtual_bundle_identifier(field, listing, clr_parser):
                    continue

                value = listing.all_fields.get(field)
                
                if not value or str(value).strip() == "":
                    if _skip_copy_aware_blank(field, listing, clr_parser):
                        continue
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
