"""
CLR Parser Module
Extracts and normalizes data from Amazon Category Listing Reports
"""

import openpyxl
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class Listing:
    """Normalized listing data"""
    row_number: int
    sku: str
    product_type: str
    item_type: str
    title: str
    brand: str
    parentage: str
    parent_sku: str
    status: str
    bullet_points: List[str]
    all_fields: Dict[str, any]  # Full row data


class CLRParser:
    """Parse Amazon Category Listing Reports"""
    
    # Standard CLR row structure
    ROW_SETTINGS = 1
    ROW_INSTRUCTIONS = 2
    ROW_GROUP_HEADERS = 3
    ROW_COL_HEADERS = 4
    ROW_FIELD_IDS = 5
    ROW_EXAMPLE = 6
    ROW_DATA_START = 7
    
    def __init__(self, clr_file_path: str):
        """Load and parse CLR file"""
        self.file_path = clr_file_path
        self.workbook = openpyxl.load_workbook(clr_file_path, data_only=True, read_only=True)
        
        # Load sheets
        self.template_sheet = self.workbook['Template']
        
        # Parse structure
        self.headers = self._extract_headers()
        self.field_definitions = self._extract_field_definitions()
        
    def _extract_headers(self) -> Dict[str, int]:
        """Extract column headers and their positions"""
        headers = {}
        header_row = self.template_sheet[self.ROW_COL_HEADERS]
        
        for idx, cell in enumerate(header_row, start=1):
            if cell.value:
                headers[str(cell.value).strip()] = idx
        
        return headers
    
    def _extract_field_definitions(self) -> Dict[str, Dict]:
        """Extract field definitions from Data Definitions sheet"""
        definitions = {}
        
        try:
            dd_sheet = self.workbook['Data Definitions']
            
            # Find header row (usually row 1, but scan first 5)
            header_row_idx = None
            for i in range(1, 6):
                row = dd_sheet[i]
                if any(cell.value and 'field name' in str(cell.value).lower() for cell in row):
                    header_row_idx = i
                    break
            
            if not header_row_idx:
                return definitions
            
            # Extract headers
            dd_headers = {}
            for idx, cell in enumerate(dd_sheet[header_row_idx], start=1):
                if cell.value:
                    dd_headers[str(cell.value).strip().lower()] = idx
            
            # Extract definitions
            for row in dd_sheet.iter_rows(min_row=header_row_idx + 1):
                field_name_idx = dd_headers.get('field name')
                required_idx = dd_headers.get('required?')
                
                if not field_name_idx:
                    continue
                
                field_name = row[field_name_idx - 1].value
                if not field_name:
                    continue
                
                required = row[required_idx - 1].value if required_idx else None
                
                definitions[str(field_name).strip()] = {
                    'required': str(required).strip().lower() if required else '',
                    'field_name': str(field_name).strip()
                }
        
        except KeyError:
            # No Data Definitions sheet
            pass
        
        return definitions
    
    def get_required_fields(self) -> List[str]:
        """Get list of required field names"""
        return [
            field_name 
            for field_name, definition in self.field_definitions.items()
            if definition['required'] == 'required'
        ]
    
    def get_conditional_fields(self) -> List[str]:
        """Get list of conditionally required field names"""
        return [
            field_name 
            for field_name, definition in self.field_definitions.items()
            if 'conditional' in definition['required'].lower()
        ]
    
    def get_listings(self, skip_parents: bool = True, skip_examples: bool = True, skip_fbm_duplicates: bool = True) -> List[Listing]:
        """
        Extract all listings from CLR
        
        Args:
            skip_parents: Skip parent SKUs (variations)
            skip_examples: Skip example/dummy rows
        
        Returns:
            List of normalized Listing objects
        """
        listings = []
        
        # Get column indices
        col_sku = self.headers.get('SKU', 3)
        col_status = self.headers.get('Status', 1)
        col_title = self.headers.get('Title', 2)
        col_product_type = self.headers.get('Product Type', 4)
        col_item_type = self.headers.get('Item Type Keyword', 13)
        col_brand = self.headers.get('Brand', 10)
        col_parentage = self.headers.get('Parentage', 6)
        col_parent_sku = self.headers.get('Parent SKU', 7)
        
        # Bullet point columns (typically around columns 43-47)
        bullet_cols = []
        for i in range(1, 6):
            col_name = f'Bullet Point {i}'
            if col_name in self.headers:
                bullet_cols.append(self.headers[col_name])
        
        # Iterate through data rows
        for row_idx, row in enumerate(self.template_sheet.iter_rows(min_row=self.ROW_DATA_START), 
                                      start=self.ROW_DATA_START):
            # Extract basic fields
            sku = self._get_cell_value(row, col_sku)
            
            if not sku:
                continue
            
            # Skip examples
            if skip_examples and sku.upper() in ['ABC123', 'EXAMPLE', 'TEST']:
                continue
            
            status = self._get_cell_value(row, col_status)
            parentage = self._get_cell_value(row, col_parentage)
            
            # Skip parents if requested
            if skip_parents and parentage and 'parent' in parentage.lower():
                continue
            
            # Extract all fields
            all_fields = {}
            for header_name, col_idx in self.headers.items():
                all_fields[header_name] = self._get_cell_value(row, col_idx)
            
            # Extract bullet points
            bullets = []
            for bullet_col in bullet_cols:
                bullet_text = self._get_cell_value(row, bullet_col)
                bullets.append(bullet_text if bullet_text else "")
            
            # Create listing object
            listing = Listing(
                row_number=row_idx,
                sku=sku,
                product_type=self._get_cell_value(row, col_product_type) or "",
                item_type=self._get_cell_value(row, col_item_type) or "",
                title=self._get_cell_value(row, col_title) or "",
                brand=self._get_cell_value(row, col_brand) or "",
                parentage=parentage or "",
                parent_sku=self._get_cell_value(row, col_parent_sku) or "",
                status=status or "",
                bullet_points=bullets,
                all_fields=all_fields
            )
            
            listings.append(listing)
        
        # Filter FBM/MFN duplicates (keep FBA versions)
        if skip_fbm_duplicates:
            listings = self._filter_fbm_duplicates(listings)
        
        return listings
    
    def _filter_fbm_duplicates(self, listings: List[Listing]) -> List[Listing]:
        """
        Filter out FBM/MFN duplicates of FBA listings.
        When multiple SKUs have the same item name (title), keep the FBA version.
        """
        seen_names = {}
        filtered = []
        skipped_count = 0
        
        for listing in listings:
            # Use title as the unique identifier (item name)
            item_name = listing.title.strip() if listing.title else ""
            
            if not item_name:
                # No title, can't detect duplicates - keep it
                filtered.append(listing)
                continue
            
            if item_name in seen_names:
                # Duplicate found
                existing_sku = seen_names[item_name]
                
                # If this one is FBA, replace the existing one
                if "_FBA_" in listing.sku.upper() or "FBA" in listing.sku.upper():
                    # Remove the old one, add this FBA version
                    filtered = [l for l in filtered if l.sku != existing_sku]
                    filtered.append(listing)
                    seen_names[item_name] = listing.sku
                else:
                    # This is FBM/MFN, skip it
                    skipped_count += 1
                    continue
            else:
                # First time seeing this item name
                seen_names[item_name] = listing.sku
                filtered.append(listing)
        
        if skipped_count > 0:
            print(f"Skipped {skipped_count} FBM/MFN duplicates (keeping FBA versions)")
        
        return filtered
    
    def get_product_types(self) -> List[str]:
        """Get unique product types in catalog"""
        product_types = set()
        listings = self.get_listings()
        
        for listing in listings:
            if listing.product_type:
                product_types.add(listing.product_type)
        
        return sorted(list(product_types))
    
    def _get_cell_value(self, row, col_idx: int) -> Optional[str]:
        """Safely get cell value from row"""
        try:
            if col_idx <= 0 or col_idx > len(row):
                return None
            
            cell = row[col_idx - 1]
            if cell.value is None:
                return None
            
            return str(cell.value).strip()
        except (IndexError, AttributeError):
            return None
    
    def __del__(self):
        """Clean up workbook"""
        if hasattr(self, 'workbook'):
            self.workbook.close()
