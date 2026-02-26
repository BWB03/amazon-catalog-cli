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
        sku_scores = {}  # Track average scores per SKU for summary
        
        for listing in listings:
            # Evaluate all bullets for this SKU
            bullet_scores = []
            sku_bullet_issues = []
            
            for position, bullet_text in enumerate(listing.bullet_points, start=1):
                bullet_eval = self._evaluate_bullet(bullet_text, position)
                bullet_scores.append(bullet_eval['score'])
                
                if bullet_eval['score'] < 4:  # Report individual bullets scoring below 4
                    sku_bullet_issues.append({
                        'row': listing.row_number,
                        'sku': listing.sku,
                        'field': f'Bullet Point {position}',
                        'severity': 'warning',
                        'details': f"Bullet {position} scores {bullet_eval['score']}/5: {', '.join(bullet_eval['issues'])}",
                        'product_type': listing.product_type,
                        'score': bullet_eval['score'],
                        'bullet_issues': bullet_eval['issues'],
                        'suggestions': bullet_eval['suggestions'],
                        'bullet_text': bullet_text[:100] + "..." if len(bullet_text) > 100 else bullet_text
                    })
            
            # Calculate average score for this SKU
            avg_score = sum(bullet_scores) / len(bullet_scores) if bullet_scores else 0
            tier = self._get_score_tier(avg_score)
            
            # Store for summary stats
            sku_scores[listing.sku] = {
                'avg_score': avg_score,
                'tier': tier
            }
            
            # If average is below 4, add a summary issue for the SKU
            if avg_score < 4:
                issues.append({
                    'row': listing.row_number,
                    'sku': listing.sku,
                    'field': 'Overall RUFUS Score',
                    'severity': 'info',
                    'details': f"Average RUFUS score: {avg_score:.1f}/5 - {tier}",
                    'product_type': listing.product_type,
                    'avg_score': round(avg_score, 1),
                    'tier': tier,
                    'individual_scores': bullet_scores
                })
            
            # Add individual bullet issues
            issues.extend(sku_bullet_issues)
        
        # Add summary stats to metadata (will be printed separately)
        if sku_scores:
            issues.append(self._generate_summary(sku_scores))
        
        return issues
    
    def _get_score_tier(self, avg_score: float) -> str:
        """Get tier label for average RUFUS score"""
        if avg_score >= 4:
            return "Good — Minor improvements possible"
        elif avg_score >= 3:
            return "Fair — Several improvements needed"
        elif avg_score >= 2:
            return "Weak — Major rewrite recommended"
        else:
            return "Critical — Bullets need complete overhaul"
    
    def _generate_summary(self, sku_scores: dict) -> dict:
        """Generate summary statistics for all SKUs"""
        avg_all = sum(s['avg_score'] for s in sku_scores.values()) / len(sku_scores)
        
        # Count SKUs per tier
        tier_counts = {}
        for score_data in sku_scores.values():
            tier = score_data['tier'].split('—')[0].strip()  # Extract just "Good", "Fair", etc.
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        summary_text = f"Overall catalog RUFUS score: {avg_all:.1f}/5. "
        summary_text += "Distribution: "
        summary_text += ", ".join([f"{count} {tier}" for tier, count in sorted(tier_counts.items())])
        
        return {
            'row': 0,
            'sku': 'SUMMARY',
            'field': 'RUFUS Summary',
            'severity': 'info',
            'details': summary_text,
            'product_type': '',
            'avg_catalog_score': round(avg_all, 1),
            'tier_distribution': tier_counts
        }
    
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
