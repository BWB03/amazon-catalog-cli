"""
Hijacking Detection Query
Detects abusive language and adult/sex toy references that hijackers
implant into Amazon listings without the owner's knowledge.
"""

import re
from ..query_engine import QueryPlugin


# Explicit adult/sex toy terms hijackers inject
ADULT_TERMS = [
    "sex toy", "sex toys", "dildo", "vibrator", "butt plug",
    "anal plug", "anal bead", "cock ring", "penis ring",
    "bondage", "bdsm", "fetish", "erotic", "pornographic",
    "adult toy", "adult toys", "pleasure toy", "nipple clamp",
    "handcuffs sex", "lingerie sexy", "stripper", "fleshlight",
    "masturbat",  # catches masturbator, masturbation, etc.
]

# Abusive / offensive language hijackers inject to get listings suppressed
ABUSIVE_LANGUAGE = [
    "fuck", "shit", "bitch", "asshole", "bastard", "damn",
    "crap", "dick", "pussy", "whore", "slut", "nigger",
    "faggot", "retard", "cunt",
]

# Suspicious phrases that indicate hijacking intent
HIJACK_PHRASES = [
    "do not buy", "don't buy", "scam", "fake product",
    "counterfeit", "knock off", "knockoff", "stolen",
    "not genuine", "not authentic", "not original",
    "warning: fraud", "seller is fake",
]

# Fields to scan (title, bullets, description, search terms)
SCAN_FIELDS = [
    'Title',
    'Bullet Point 1',
    'Bullet Point 2',
    'Bullet Point 3',
    'Bullet Point 4',
    'Bullet Point 5',
    'Product Description',
    'Search Terms',
    'Generic Keywords',
]


class HijackingDetectionQuery(QueryPlugin):
    """Detect abusive language and adult content injected by hijackers"""

    name = "hijacking-detection"
    description = "Detect abusive language and adult content injected by listing hijackers"

    def execute(self, listings, clr_parser):
        issues = []

        for listing in listings:
            for field_name in SCAN_FIELDS:
                value = listing.all_fields.get(field_name, "")
                if not value:
                    continue

                value_str = str(value)
                value_lower = value_str.lower()
                detections = []

                # Check adult/sex toy terms
                for term in ADULT_TERMS:
                    if term in value_lower:
                        detections.append(("adult_content", term))

                # Check abusive language
                for term in ABUSIVE_LANGUAGE:
                    # Word boundary match to avoid false positives
                    # e.g. "asshole" but not "class"
                    if re.search(rf'\b{re.escape(term)}\w*\b', value_lower):
                        detections.append(("abusive_language", term))

                # Check hijack phrases
                for phrase in HIJACK_PHRASES:
                    if phrase in value_lower:
                        detections.append(("hijack_phrase", phrase))

                if detections:
                    categories = set(d[0] for d in detections)
                    matched_terms = [d[1] for d in detections]

                    severity = "critical"
                    category_labels = {
                        "adult_content": "Adult/sexual content",
                        "abusive_language": "Abusive language",
                        "hijack_phrase": "Hijacking phrase",
                    }
                    category_str = ", ".join(
                        category_labels[c] for c in sorted(categories)
                    )

                    issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': field_name,
                        'severity': severity,
                        'details': f"HIJACK ALERT - {field_name}: {category_str} detected. Matched: {', '.join(matched_terms)}",
                        'product_type': listing.product_type,
                        'categories': sorted(categories),
                        'matched_terms': matched_terms,
                        'field_text': value_str[:150] + '...' if len(value_str) > 150 else value_str,
                    })

        return issues
