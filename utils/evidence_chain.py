import re
from typing import Optional
from utils.logger import log


class EvidenceBuilder:
    """Builds an evidence chain from response output and retrieved context."""

    def build_chain(self, output: str, context: str) -> list[dict]:
        """
        Extract evidence items from the output that are grounded in the context.
        Returns a list of evidence entries with claim, source, and confidence.
        """
        if not output or not context:
            return []

        # Split output into sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', output) if s.strip() and len(s.strip()) > 20]
        context_lower = context.lower()

        chain = []
        for i, sentence in enumerate(sentences):
            # Check if sentence has any word overlap with context
            words = set(re.findall(r'\b\w+\b', sentence.lower()))
            context_words = set(re.findall(r'\b\w+\b', context_lower))

            overlap = len(words & context_words) / max(len(words), 1)
            confidence = min(overlap * 1.2, 1.0)

            chain.append({
                "claim": sentence,
                "source_index": i,
                "grounding_score": round(confidence, 2),
                "source": "context" if overlap > 0.3 else "generated",
            })

        log.info("Built evidence chain with %d claims", len(chain))
        return chain


class TimelineBuilder:
    """Reconstructs a timeline of events from context."""

    def build_timeline(self, context: str) -> list[dict]:
        """
        Extract temporal markers from context and build a timeline.
        Looks for timestamps, dates, and sequential indicators.
        """
        if not context:
            return []

        # Common timestamp patterns
        time_patterns = [
            r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',
            r'\d{2}:\d{2}:\d{2}',
            r'\d{4}-\d{2}-\d{2}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}',
        ]

        events = []
        lines = context.split('\n')
        for i, line in enumerate(lines):
            for pattern in time_patterns:
                match = re.search(pattern, line)
                if match:
                    events.append({
                        "timestamp": match.group(),
                        "event": line.strip()[:200],
                        "line_index": i,
                    })
                    break

        # Sort by timestamp string (basic sort)
        events.sort(key=lambda e: e["timestamp"])
        return events


class ContradictionDetector:
    """Detects contradictions between output and evidence chain."""

    def detect_contradictions(self, output: str, evidence_chain: list, context: str) -> dict:
        """
        Check for contradictions in the output against evidence and context.
        Returns contradictions list, hypotheses, and confidence adjustment.
        """
        contradictions = []
        hypotheses = []

        if not output or not evidence_chain:
            return {
                "contradictions": [],
                "hypotheses": ["Insufficient data for contradiction analysis"],
                "confidence_adjustment": 0.0,
            }

        # Check for low-confidence claims
        low_conf_claims = [
            e for e in evidence_chain
            if e.get("grounding_score", 0) < 0.3 and e.get("source") == "generated"
        ]

        if low_conf_claims:
            contradictions.append({
                "type": "low_grounding",
                "description": f"{len(low_conf_claims)} claims have weak grounding in context",
                "severity": "medium",
            })
            hypotheses.append("Some generated claims may not be fully supported by retrieved context.")

        # Check for confidence adjustment
        avg_confidence = (
            sum(e.get("grounding_score", 0.5) for e in evidence_chain) / len(evidence_chain)
            if evidence_chain else 0.5
        )
        adjustment = (avg_confidence - 0.5) * 0.2  # ±10% based on average grounding

        return {
            "contradictions": contradictions,
            "hypotheses": hypotheses,
            "confidence_adjustment": round(adjustment, 3),
        }


# Global instances
evidence_builder = EvidenceBuilder()
timeline_builder = TimelineBuilder()
contradiction_detector = ContradictionDetector()
