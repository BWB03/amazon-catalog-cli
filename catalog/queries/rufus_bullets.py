"""
RUFUS Bullet Point Optimization Query
Based on Amazon's RUFUS AI shopping assistant framework.

Scores bullet points against three core RUFUS questions:
  1. "Is this right for me?"  — target user, lifestyle, problem state
  2. "What is the difference?" — differentiators, certifications, unique claims
  3. "How do I use it?"        — usage instructions, what's in the box, compatibility

Formatting rule: bullets should read as short FAQ answers, not feature lists.
"""

import re
from ..query_engine import QueryPlugin


# ── Bullet length thresholds ─────────────────────────────────────────────────
MIN_BULLET_LENGTH = 50
IDEAL_MIN_BULLET_LENGTH = 100
MAX_BULLET_LENGTH = 500

# ── RUFUS Question 1: "Is this right for me?" ───────────────────────────────
# Signals that a bullet addresses target audience, lifestyle, or problem state
RIGHT_FOR_ME_SIGNALS = [
    # Audience phrases (multi-word to reduce false positives)
    "ideal for", "perfect for", "designed for", "suitable for",
    "great for", "recommended for", "made for", "built for",
    # Demographic targets
    "for men", "for women", "for kids", "for children", "for adults", "for teens",
    "for professional", "for beginners", "for athletes",
    # Problem / need language
    "if you", "whether you", "anyone who", "those who",
    "looking for", "struggling with", "suffering from",
    # Benefit / solution language
    "help", "reduce", "improve", "enhance", "protect", "support",
    "boost", "strengthen", "promote", "relief", "solve", "prevent",
]

# ── RUFUS Question 2: "What is the difference?" ─────────────────────────────
# Signals that a bullet provides differentiators vs. competitors
DIFFERENCE_SIGNALS = [
    # Comparison language
    "unlike", "compared to", "vs", "versus", "instead of", "alternative",
    # Unique claims
    "only", "unique", "exclusive", "patented", "proprietary",
    # Certifications and trust
    "certified", "award", "fda", "usda", "organic", "non-gmo",
    "lab tested", "third party", "clinically proven",
]

# ── RUFUS Question 3: "How do I use it?" ─────────────────────────────────────
# Signals that a bullet explains usage, contents, or compatibility
HOW_TO_USE_SIGNALS = [
    # Usage instructions
    "simply", "just apply", "easy to use", "ready to",
    "how to", "instructions", "apply", "install", "attach", "mix",
    # What's in the box
    "includes", "comes with", "package contains", "kit includes",
    "in the box", "set of", "piece",
    # Compatibility
    "compatible with", "fits", "works with",
]

# ── Formatting: anti-patterns ────────────────────────────────────────────────
VAGUE_MARKETING_PHRASES = [
    "premium quality", "high quality", "best in class", "world class",
    "industry leading", "revolutionary", "amazing", "incredible",
]

# Labels for output
RUFUS_QUESTIONS = {
    'right_for_me': '"Is this right for me?" — state the target user (age, lifestyle, problem state)',
    'difference':   '"What is the difference?" — list 1-2 crisp differentiators (ingredient, durability, form factor)',
    'how_to_use':   '"How do I use it?" — usage instructions and what\'s in the box',
}


class RufusBulletsQuery(QueryPlugin):
    """Evaluate bullet points against Amazon's RUFUS AI optimization framework"""

    name = "rufus-bullets"
    description = "Evaluate bullet points against Amazon's RUFUS AI optimization framework"

    def execute(self, listings, clr_parser):
        issues = []
        sku_scores = {}

        for listing in listings:
            bullet_scores = []
            sku_bullet_issues = []
            sku_rufus_coverage = set()  # Track which RUFUS questions are addressed

            for position, bullet_text in enumerate(listing.bullet_points, start=1):
                bullet_eval = self._evaluate_bullet(bullet_text, position)
                bullet_scores.append(bullet_eval['score'])
                sku_rufus_coverage.update(bullet_eval['rufus_signals'])

                if bullet_eval['score'] < 4:
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
                        'rufus_signals': sorted(bullet_eval['rufus_signals']),
                        'bullet_text': bullet_text[:100] + "..." if len(bullet_text) > 100 else bullet_text
                    })

            # RUFUS question coverage check (SKU-level)
            missing_questions = set(RUFUS_QUESTIONS.keys()) - sku_rufus_coverage
            if missing_questions:
                missing_labels = [RUFUS_QUESTIONS[q] for q in sorted(missing_questions)]
                issues.append({
                    'row': listing.row_number,
                    'sku': listing.sku,
                    'field': 'RUFUS Question Coverage',
                    'severity': 'warning',
                    'details': f"Bullets don't answer {len(missing_questions)} RUFUS question(s): {'; '.join(missing_labels)}",
                    'product_type': listing.product_type,
                    'missing_questions': sorted(missing_questions),
                    'covered_questions': sorted(sku_rufus_coverage),
                })

            # Average score for this SKU
            avg_score = sum(bullet_scores) / len(bullet_scores) if bullet_scores else 1
            tier = self._get_score_tier(avg_score)

            sku_scores[listing.sku] = {
                'avg_score': avg_score,
                'tier': tier
            }

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
                    'individual_scores': bullet_scores,
                    'rufus_coverage': sorted(sku_rufus_coverage),
                })

            issues.extend(sku_bullet_issues)

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

        tier_counts = {}
        for score_data in sku_scores.values():
            tier = score_data['tier'].split('\u2014')[0].strip()
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
        Evaluate a single bullet point against RUFUS framework.

        Returns:
            dict with 'score' (1-5), 'issues', 'suggestions', 'rufus_signals'
        """
        if not text or text.strip() == "":
            return {
                'score': 1,
                'issues': ["Bullet point is empty"],
                'suggestions': ["Add content to this bullet point"],
                'rufus_signals': set(),
            }

        text = text.strip()
        text_lower = text.lower()
        issues = []
        suggestions = []
        score = 5

        # ── Formatting checks ────────────────────────────────────────────

        # Length
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

        # Excessive ALL CAPS
        words = text.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 3]
        caps_ratio = len(caps_words) / max(len(words), 1)
        if caps_ratio > 0.3:
            issues.append("Excessive ALL CAPS")
            suggestions.append("Use sentence case; reserve caps for brand names only")
            score -= 1

        # Specifics (numbers, measurements, data)
        has_specifics = bool(re.search(r'\d', text))
        if not has_specifics:
            issues.append("No specific numbers or data points")
            suggestions.append("Add concrete specs (oz, count, %, time, dimensions)")
            score -= 1

        # ── FAQ-style check ───────────────────────────────────────────────
        # Bullets should read as short answers, not comma-separated feature dumps
        segments = re.split(r',\s*', text)
        if len(segments) >= 4:
            short_segments = sum(1 for s in segments if len(s.split()) <= 4)
            if short_segments / len(segments) > 0.6:
                issues.append("Reads like a feature list, not an FAQ answer")
                suggestions.append("Rewrite as a short answer — explain why each feature matters")
                score -= 1

        # ── RUFUS question signal detection ───────────────────────────────
        rufus_signals = set()

        if any(signal in text_lower for signal in RIGHT_FOR_ME_SIGNALS):
            rufus_signals.add('right_for_me')

        if any(signal in text_lower for signal in DIFFERENCE_SIGNALS):
            rufus_signals.add('difference')

        if any(signal in text_lower for signal in HOW_TO_USE_SIGNALS):
            rufus_signals.add('how_to_use')

        if not rufus_signals:
            issues.append("Doesn't answer any RUFUS question")
            suggestions.append(
                "Each bullet should answer at least one: "
                "'Is this right for me?', 'What is the difference?', or 'How do I use it?'"
            )
            score -= 1

        # Clamp to 1-5
        score = max(1, min(5, score))

        return {
            'score': score,
            'issues': issues,
            'suggestions': suggestions,
            'rufus_signals': rufus_signals,
        }
