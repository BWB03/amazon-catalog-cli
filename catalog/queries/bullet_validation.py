"""
Bullet point validation based on Amazon's official requirements
Checks formatting, prohibited content, and style guidelines
"""

import re
from ..query_engine import QueryPlugin


# Prohibited special characters in bullet points
PROHIBITED_SPECIAL_CHARS = set("™®€…†‡°¢£¥©±~â")

# Prohibited emojis
PROHIBITED_EMOJIS = set("☺☹✅❌")

# Placeholder text patterns
PLACEHOLDER_PATTERNS = [
    r'\bnot applicable\b',
    r'\bNA\b',
    r'\bn/a\b',
    r'\bTBD\b',
    r'\bcopy pending\b',
]

# Prohibited claims
PROHIBITED_CLAIMS = [
    'eco-friendly',
    'anti-microbial',
    'anti-bacterial',
    'antibacterial',
    'antimicrobial',
]

# Guarantee/warranty language (not allowed in bullets)
GUARANTEE_LANGUAGE = [
    'full refund',
    'unconditional guarantee',
    'money back guarantee',
    '100% guarantee',
]


class BulletProhibitedContentQuery(QueryPlugin):
    """
    Check bullet points for prohibited content per Amazon requirements.
    Does NOT check Product Description (different rules apply).
    
    Checks for:
    - Prohibited special characters (™, ®, €, etc.)
    - Emojis (☺, ☹, ✅, ❌, etc.)
    - Placeholder text (NA, TBD, copy pending, etc.)
    - Prohibited claims (eco-friendly, anti-microbial, etc.)
    - Guarantee language (full refund, etc.)
    """
    
    name = "bullet-prohibited-content"
    description = "Find bullet points with prohibited content (chars, emojis, claims, placeholders)"
    
    BULLET_FIELDS = [
        'Bullet Point 1',
        'Bullet Point 2',
        'Bullet Point 3',
        'Bullet Point 4',
        'Bullet Point 5',
    ]
    
    def execute(self, listings, clr_parser):
        issues = []
        
        for listing in listings:
            for field_name in self.BULLET_FIELDS:
                value = listing.all_fields.get(field_name, "")
                
                if not value:
                    continue
                
                value_str = str(value)
                value_lower = value_str.lower()
                violations = []
                
                # Check for prohibited special characters
                found_special = set(value_str) & PROHIBITED_SPECIAL_CHARS
                if found_special:
                    violations.append(f"Prohibited special characters: {', '.join(found_special)}")
                
                # Check for emojis
                found_emojis = set(value_str) & PROHIBITED_EMOJIS
                if found_emojis:
                    violations.append(f"Emojis not allowed: {', '.join(found_emojis)}")
                
                # Check for placeholder text
                for pattern in PLACEHOLDER_PATTERNS:
                    if re.search(pattern, value_str, re.IGNORECASE):
                        match = re.search(pattern, value_str, re.IGNORECASE).group()
                        violations.append(f"Placeholder text: '{match}'")
                        break  # Only report first placeholder found
                
                # Check for prohibited claims
                for claim in PROHIBITED_CLAIMS:
                    if claim in value_lower:
                        violations.append(f"Prohibited claim: '{claim}'")
                
                # Check for guarantee language
                for guarantee in GUARANTEE_LANGUAGE:
                    if guarantee in value_lower:
                        violations.append(f"Guarantee language not allowed: '{guarantee}'")
                
                # If any violations found, create issue
                if violations:
                    issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': field_name,
                        'severity': 'critical',  # Amazon can suppress listings for this
                        'details': f"{field_name}: {'; '.join(violations)}",
                        'product_type': listing.product_type,
                        'violations': violations,
                        'bullet_text': value_str[:100] + '...' if len(value_str) > 100 else value_str
                    })
        
        return issues


class BulletFormattingQuery(QueryPlugin):
    """
    Check bullet point formatting per Amazon requirements:
    - Must begin with capital letter
    - Must NOT end with punctuation (sentence fragments)
    - Length between 10-255 characters
    - Should have at least 3 bullets per product
    """
    
    name = "bullet-formatting"
    description = "Check bullet point formatting (capitalization, length, punctuation)"
    
    BULLET_FIELDS = [
        'Bullet Point 1',
        'Bullet Point 2',
        'Bullet Point 3',
        'Bullet Point 4',
        'Bullet Point 5',
    ]
    
    def execute(self, listings, clr_parser):
        issues = []
        
        for listing in listings:
            bullet_count = 0
            
            for field_name in self.BULLET_FIELDS:
                value = listing.all_fields.get(field_name, "")
                
                if not value:
                    continue
                
                bullet_count += 1
                value_str = str(value).strip()
                violations = []
                
                # Check capitalization (first character should be uppercase)
                if value_str and not value_str[0].isupper():
                    violations.append("Must begin with capital letter")
                
                # Check length (10-255 characters)
                length = len(value_str)
                if length < 10:
                    violations.append(f"Too short ({length} chars, minimum 10)")
                elif length > 255:
                    violations.append(f"Too long ({length} chars, maximum 255)")
                
                # Check end punctuation (should NOT end with period, !, ?)
                if value_str and value_str[-1] in '.!?':
                    violations.append(f"Should not end with '{value_str[-1]}' (use sentence fragments)")
                
                # Report violations for this bullet
                if violations:
                    issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': field_name,
                        'severity': 'warning',
                        'details': f"{field_name}: {'; '.join(violations)}",
                        'product_type': listing.product_type,
                        'violations': violations,
                        'bullet_text': value_str[:100] + '...' if len(value_str) > 100 else value_str
                    })
            
            # Check minimum bullet count (should have at least 3)
            if 0 < bullet_count < 3:
                issues.append({
                    'row': listing.row_number,
                    'sku': listing.sku,
                    'field': 'Bullet Points',
                    'severity': 'warning',
                    'details': f"Only {bullet_count} bullet point(s) found. Amazon recommends at least 3.",
                    'product_type': listing.product_type,
                    'bullet_count': bullet_count
                })
        
        return issues
