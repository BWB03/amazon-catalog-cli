"""
RUFUS Bullet Point Optimization Query
Based on Amazon's RUFUS AI shopping assistant framework
"""

import re
from ..query_engine import QueryPlugin


# Bullet length thresholds
MIN_BULLET_LENGTH = 50
IDEAL_MIN_BULLET_LENGTH = 100
MAX_BULLET_LENGTH = 500

# RUFUS keyword patterns
BENEFIT_KEYWORDS = [
    "help", "reduce", "improve", "enhance", "protect", "support",
    "boost", "strengthen", "promote", "relief", "solve", "prevent"
]

AUDIENCE_KEYWORDS = [
    "for", "ideal for", "perfect for", "designed for", "suitable for",
    "men", "women", "kids", "children", "adults", "teens",
    "professional", "beginners", "athletes", "active"
]

DIFFERENTIATOR_KEYWORDS = [
    "only", "unique", "exclusive", "patented", "certified", "award",
    "unlike", "compared to", "vs", "versus", "instead of", "alternative"
]

VAGUE_MARKETING_PHRASES = [
    "premium quality", "high quality", "best in class", "world class",
    "industry leading", "revolutionary", "amazing", "incredible"
]


class RufusBulletsQuery(QueryPlugin):
    """Evaluate bullet points against RUFUS optimization framework"""
    
    name = "rufus-bullets"
    description = "Evaluate bullet points against Amazon's RUFUS AI optimization framework"
    
    def execute(self, listings, clr_parser):
        issues = []
        
        for listing in listings:
            # Evaluate each bullet point
            for position, bullet_text in enumerate(listing.bullet_points, start=1):
                bullet_issues = self._evaluate_bullet(bullet_text, position)
                
                if bullet_issues['score'] < 4:  # Only report bullets scoring below 4
                    issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': f'Bullet Point {position}',
                        'severity': 'warning',
                        'details': f"Bullet {position} scores {bullet_issues['score']}/5: {', '.join(bullet_issues['issues'])}",
                        'product_type': listing.product_type,
                        'score': bullet_issues['score'],
                        'bullet_issues': bullet_issues['issues'],
                        'suggestions': bullet_issues['suggestions'],
                        'bullet_text': bullet_text[:100] + "..." if len(bullet_text) > 100 else bullet_text
                    })
        
        return issues
    
    def _evaluate_bullet(self, text: str, position: int) -> dict:
        """
        Evaluate a single bullet point
        
        Returns:
            dict with 'score' (1-5), 'issues' (list), 'suggestions' (list)
        """
        if not text or text.strip() == "":
            return {
                'score': 0,
                'issues': ["Bullet point is empty"],
                'suggestions': ["Add content to this bullet point"]
            }
        
        text = text.strip()
        text_lower = text.lower()
        issues = []
        suggestions = []
        score = 5  # Start perfect, deduct for issues
        
        # Length checks
        if len(text) < MIN_BULLET_LENGTH:
            issues.append(f"Too short ({len(text)} chars, min {MIN_BULLET_LENGTH})")
            suggestions.append("Expand with more detail and specifics")
            score -= 2
        elif len(text) < IDEAL_MIN_BULLET_LENGTH:
            issues.append(f"Short ({len(text)} chars, ideal {IDEAL_MIN_BULLET_LENGTH}+)")
            suggestions.append("Consider adding more specific details")
            score -= 1
        
        if len(text) > MAX_BULLET_LENGTH:
            issues.append(f"Too long ({len(text)} chars, max {MAX_BULLET_LENGTH})")
            suggestions.append("Trim to key points — long bullets get skipped")
            score -= 1
        
        # Vague marketing language
        found_vague = [p for p in VAGUE_MARKETING_PHRASES if p in text_lower]
        if found_vague:
            issues.append(f"Vague marketing: {', '.join(found_vague)}")
            suggestions.append("Replace with specific, factual claims")
            score -= 1
        
        # ALL CAPS detection
        words = text.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 3]
        caps_ratio = len(caps_words) / max(len(words), 1)
        if caps_ratio > 0.3:
            issues.append("Excessive ALL CAPS")
            suggestions.append("Use sentence case; reserve caps for brand names only")
            score -= 1
        
        # Position-specific checks
        if position == 1:
            # Bullet 1 should lead with Hero Benefit
            has_benefit = any(kw in text_lower for kw in BENEFIT_KEYWORDS)
            if not has_benefit:
                issues.append("Should lead with Hero Benefit")
                suggestions.append("Start with #1 reason to buy — what problem does it solve?")
                score -= 1
        
        elif position == 2:
            # Bullet 2 should state who it's for
            has_audience = any(kw in text_lower for kw in AUDIENCE_KEYWORDS)
            if not has_audience:
                issues.append("Should state who it's for")
                suggestions.append("Mention target user, use-case, or lifestyle")
                score -= 1
        
        elif position == 3:
            # Bullet 3 should differentiate
            has_diff = any(kw in text_lower for kw in DIFFERENTIATOR_KEYWORDS)
            if not has_diff:
                issues.append("Should differentiate from competitors")
                suggestions.append("Mention certifications, unique ingredients, or 'why this vs. others'")
                score -= 1
        
        # Specifics check (numbers, measurements, data)
        has_specifics = bool(re.search(r'\d', text))
        if not has_specifics:
            issues.append("No specific numbers or data points")
            suggestions.append("Add concrete specs (oz, count, %, time, dimensions)")
            score -= 1
        
        # Clamp score
        score = max(1, min(5, score))
        
        return {
            'score': score,
            'issues': issues,
            'suggestions': suggestions
        }
