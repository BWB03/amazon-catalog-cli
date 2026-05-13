"""
Intent-based bullet point optimization query.

Scores bullet points against COSMO-inspired shopper intent dimensions:
  1. Audience / need fit       - target shopper, preference, problem state
  2. Function / use case       - job to be done, activity, event, use flow
  3. Context / compatibility   - season, location, material, surface, works-with
  4. Decision evidence         - specs, attributes, trust signals, differentiators

Formatting rule: bullets should read as useful intent answers, not feature dumps.
"""

import re
from ..query_engine import QueryPlugin


# Bullet length thresholds
MIN_BULLET_LENGTH = 50
IDEAL_MIN_BULLET_LENGTH = 100
MAX_BULLET_LENGTH = 500


# Shopper intent signals. These are intentionally simple lexical cues because
# Catalog CLI runs locally without calling an LLM or external classifier.
AUDIENCE_NEED_SIGNALS = [
    "ideal for", "perfect for", "designed for", "suitable for",
    "great for", "recommended for", "made for", "built for",
    "for men", "for women", "for kids", "for children", "for adults", "for teens",
    "for professional", "for beginners", "for athletes", "for pets",
    "sensitive skin", "dry skin", "oily skin", "fine hair", "curly hair",
    "if you", "whether you", "anyone who", "those who", "looking for",
    "struggling with", "suffering from", "need to", "want to",
    "helps", "helping", "reduce", "improve", "enhance", "protect", "support",
    "boost", "strengthen", "promote", "relief", "solve", "prevent",
]

FUNCTION_USE_CASE_SIGNALS = [
    "use for", "use as", "used for", "use it to", "helps you",
    "clean", "cook", "bake", "organize", "store", "carry", "travel",
    "camping", "hiking", "workout", "training", "office", "school",
    "sleep", "shower", "bath", "garden", "repair", "install", "apply",
    "mix", "attach", "remove", "charge", "display", "serve", "gift",
    "routine", "daily use", "everyday use", "on the go", "quickly",
]

CONTEXT_COMPATIBILITY_SIGNALS = [
    "compatible with", "fits", "works with", "pairs with", "connects to",
    "replacement for", "refill for", "safe for", "dishwasher safe",
    "indoor", "outdoor", "kitchen", "bathroom", "bedroom", "garage",
    "winter", "summer", "spring", "fall", "holiday", "travel",
    "skin", "hair", "face", "body", "hands", "feet", "scalp",
    "wood", "metal", "glass", "plastic", "ceramic", "cotton", "leather",
    "stainless steel", "silicone", "waterproof", "weatherproof",
]

DECISION_EVIDENCE_SIGNALS = [
    "unlike", "compared to", "vs", "versus", "instead of", "alternative",
    "only", "unique", "exclusive", "patented", "proprietary",
    "certified", "award", "fda", "usda", "organic", "non-gmo",
    "lab tested", "third party", "clinically proven", "bpa-free",
    "included", "includes", "comes with",
    "package contains", "kit includes", "in the box", "set of", "pack of",
]

INTENT_SIGNAL_GROUPS = {
    "audience_need": AUDIENCE_NEED_SIGNALS,
    "function_use_case": FUNCTION_USE_CASE_SIGNALS,
    "context_compatibility": CONTEXT_COMPATIBILITY_SIGNALS,
    "decision_evidence": DECISION_EVIDENCE_SIGNALS,
}

INTENT_DIMENSIONS = {
    "audience_need": "Audience / need fit - who it is for, preferences, or problem state",
    "function_use_case": "Function / use case - the job, activity, event, or use flow",
    "context_compatibility": "Context / compatibility - where, when, or what it works with",
    "decision_evidence": "Decision evidence - specs, attributes, trust signals, or differentiators",
}

VAGUE_MARKETING_PHRASES = [
    "premium quality", "high quality", "best in class", "world class",
    "industry leading", "revolutionary", "amazing", "incredible",
]


class IntentBulletsQuery(QueryPlugin):
    """Evaluate bullet points for COSMO-style shopper intent coverage"""

    name = "intent-bullets"
    aliases = ["rufus-bullets"]
    description = "Evaluate bullet points for COSMO-style shopper intent coverage"

    def execute(self, listings, clr_parser):
        issues = []
        sku_scores = {}

        for listing in listings:
            bullet_scores = []
            sku_bullet_issues = []
            sku_intent_coverage = set()

            for position, bullet_text in enumerate(listing.bullet_points, start=1):
                bullet_eval = self._evaluate_bullet(bullet_text)
                bullet_scores.append(bullet_eval["score"])
                sku_intent_coverage.update(bullet_eval["intent_signals"])

                if bullet_eval["score"] < 4:
                    sku_bullet_issues.append({
                        "row": listing.row_number,
                        "sku": listing.sku,
                        "field": f"Bullet Point {position}",
                        "severity": "warning",
                        "details": f"Bullet {position} scores {bullet_eval['score']}/5: {', '.join(bullet_eval['issues'])}",
                        "product_type": listing.product_type,
                        "score": bullet_eval["score"],
                        "bullet_issues": bullet_eval["issues"],
                        "suggestions": bullet_eval["suggestions"],
                        "intent_signals": sorted(bullet_eval["intent_signals"]),
                        "bullet_text": bullet_text[:100] + "..." if len(bullet_text) > 100 else bullet_text,
                    })

            missing_intents = set(INTENT_DIMENSIONS.keys()) - sku_intent_coverage
            if missing_intents:
                missing_labels = [INTENT_DIMENSIONS[intent] for intent in sorted(missing_intents)]
                issues.append({
                    "row": listing.row_number,
                    "sku": listing.sku,
                    "field": "Intent Coverage",
                    "severity": "warning",
                    "details": f"Bullets miss {len(missing_intents)} shopper intent dimension(s): {'; '.join(missing_labels)}",
                    "product_type": listing.product_type,
                    "missing_intents": sorted(missing_intents),
                    "covered_intents": sorted(sku_intent_coverage),
                })

            avg_score = sum(bullet_scores) / len(bullet_scores) if bullet_scores else 1
            tier = self._get_score_tier(avg_score)

            sku_scores[listing.sku] = {
                "avg_score": avg_score,
                "tier": tier,
            }

            if avg_score < 4:
                issues.append({
                    "row": listing.row_number,
                    "sku": listing.sku,
                    "field": "Overall Intent Score",
                    "severity": "info",
                    "details": f"Average intent score: {avg_score:.1f}/5 - {tier}",
                    "product_type": listing.product_type,
                    "avg_score": round(avg_score, 1),
                    "tier": tier,
                    "individual_scores": bullet_scores,
                    "intent_coverage": sorted(sku_intent_coverage),
                })

            issues.extend(sku_bullet_issues)

        if sku_scores:
            issues.append(self._generate_summary(sku_scores))

        return issues

    def _get_score_tier(self, avg_score: float) -> str:
        """Get tier label for average intent score"""
        if avg_score >= 4:
            return "Good - Minor improvements possible"
        elif avg_score >= 3:
            return "Fair - Several improvements needed"
        elif avg_score >= 2:
            return "Weak - Major rewrite recommended"
        else:
            return "Critical - Bullets need complete overhaul"

    def _generate_summary(self, sku_scores: dict) -> dict:
        """Generate summary statistics for all SKUs"""
        avg_all = sum(s["avg_score"] for s in sku_scores.values()) / len(sku_scores)

        tier_counts = {}
        for score_data in sku_scores.values():
            tier = score_data["tier"].split("-")[0].strip()
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        summary_text = f"Overall catalog intent score: {avg_all:.1f}/5. "
        summary_text += "Distribution: "
        summary_text += ", ".join([f"{count} {tier}" for tier, count in sorted(tier_counts.items())])

        return {
            "row": 0,
            "sku": "SUMMARY",
            "field": "Intent Summary",
            "severity": "info",
            "details": summary_text,
            "product_type": "",
            "avg_catalog_score": round(avg_all, 1),
            "tier_distribution": tier_counts,
        }

    def _evaluate_bullet(self, text: str) -> dict:
        """
        Evaluate a single bullet point against shopper intent dimensions.

        Returns:
            dict with score, issues, suggestions, and intent_signals
        """
        if not text or text.strip() == "":
            return {
                "score": 1,
                "issues": ["Bullet point is empty"],
                "suggestions": ["Add content to this bullet point"],
                "intent_signals": set(),
            }

        text = text.strip()
        text_lower = text.lower()
        intent_signals = self._detect_intent_signals(text_lower)
        issues = []
        suggestions = []
        score = 5

        if len(text) < MIN_BULLET_LENGTH:
            issues.append(f"Too short ({len(text)} chars, min {MIN_BULLET_LENGTH})")
            suggestions.append("Expand with shopper intent, product context, or decision details")
            score -= 2
        elif len(text) < IDEAL_MIN_BULLET_LENGTH:
            issues.append(f"Short ({len(text)} chars, ideal {IDEAL_MIN_BULLET_LENGTH}+)")
            suggestions.append("Consider adding the use case, audience, compatibility, or proof point")
            score -= 1

        if len(text) > MAX_BULLET_LENGTH:
            issues.append(f"Too long ({len(text)} chars, max {MAX_BULLET_LENGTH})")
            suggestions.append("Trim to the shopper intent and the most useful proof point")
            score -= 1

        found_vague = [p for p in VAGUE_MARKETING_PHRASES if p in text_lower]
        if found_vague:
            issues.append(f"Vague marketing: {', '.join(found_vague)}")
            suggestions.append("Replace with concrete attributes, compatibility, or use-case evidence")
            score -= 1

        words = text.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 3]
        caps_ratio = len(caps_words) / max(len(words), 1)
        if caps_ratio > 0.3:
            issues.append("Excessive ALL CAPS")
            suggestions.append("Use sentence case; reserve caps for brand names only")
            score -= 1

        segments = re.split(r",\s*", text)
        if len(segments) >= 4:
            short_segments = sum(1 for s in segments if len(s.split()) <= 4)
            if short_segments / len(segments) > 0.6:
                issues.append("Reads like a feature list, not an intent answer")
                suggestions.append("Rewrite as a short answer that connects features to shopper intent")
                score -= 1

        if not intent_signals:
            issues.append("Doesn't address a clear shopper intent")
            suggestions.append(
                "Each bullet should answer at least one intent: audience, use case, context, or decision evidence"
            )
            score -= 1
        elif "decision_evidence" not in intent_signals:
            issues.append("No concrete decision evidence")
            suggestions.append("Add a spec, attribute, included item, certification, material, size, count, or differentiator")
            score -= 1

        score = max(1, min(5, score))

        return {
            "score": score,
            "issues": issues,
            "suggestions": suggestions,
            "intent_signals": intent_signals,
        }

    def _detect_intent_signals(self, text_lower: str) -> set:
        """Detect which intent dimensions are represented in a bullet."""
        intent_signals = set()

        for intent, signals in INTENT_SIGNAL_GROUPS.items():
            if any(signal in text_lower for signal in signals):
                intent_signals.add(intent)

        if re.search(r"\d", text_lower):
            intent_signals.add("decision_evidence")

        return intent_signals


# Backward-compatible import name for users importing the old class directly.
RufusBulletsQuery = IntentBulletsQuery
