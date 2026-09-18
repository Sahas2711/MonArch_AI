"""
Clause Segmentation Module.

Splits raw contract text into structured clause segments while preserving
exact character offsets, headings, and clause numbering.
"""

from typing import List, Optional
import re
from pydantic import BaseModel, Field


class ClauseSegment(BaseModel):
    """A segment of contract text representing a clause or section."""
    segment_id: str = Field(..., description="Unique segment identifier, e.g. 'SEG-001'")
    heading: Optional[str] = Field(None, description="Clause title or heading if detected")
    clause_reference: Optional[str] = Field(None, description="Clause reference, e.g. 'Clause 4.2' or 'Section 12'")
    text: str = Field(..., description="Full text of the segment")
    start_char: int = Field(..., description="Start character offset in original document")
    end_char: int = Field(..., description="End character offset in original document")
    page_number: int = Field(1, description="Estimated 1-based page number")


class ClauseSegmenter:
    """
    Segments commercial contracts into clause units.
    
    Detects:
    1. Numbered clauses: "1.", "1.1", "Clause 4", "Section 7", "Article III", "§ 14"
    2. Header lines followed by text
    3. Fallback paragraph blocks if no structured headings exist.
    """

    HEADING_PATTERNS = [
        # Clause / Section / Article / § headers
        r'(?:^|\n)\s*(?:CLAUSE|SECTION|ARTICLE|§)\s*(\d+(?:\.\d+)*|[IVXLCDM]+)[\.\:\-\s]+([^\n]+)?',
        # Numbered headings like "1. Payment Terms" or "4.2 Interest on Overdue Invoices"
        r'(?:^|\n)\s*(\d{1,2}(?:\.\d{1,2})*)\.?\s+([A-Z][A-Za-z0-9\s,\-\/\(\)]+)(?:\n|\:)',
    ]

    def __init__(self, chars_per_page: int = 3000):
        self.chars_per_page = chars_per_page

    def segment(self, document_text: str) -> List[ClauseSegment]:
        """
        Segments text into structured clauses.
        Always preserves contiguous character offsets.
        """
        if not document_text or not document_text.strip():
            return []

        # Find all boundary matches
        boundaries = []
        for pat in self.HEADING_PATTERNS:
            for match in re.finditer(pat, document_text, re.IGNORECASE | re.MULTILINE):
                boundaries.append((match.start(), match.end(), match.group(0).strip()))

        # If no explicit headings, segment on double newlines / paragraph breaks
        if not boundaries:
            para_matches = list(re.finditer(r'\n\s*\n+', document_text))
            if not para_matches:
                # Single segment
                return [
                    ClauseSegment(
                        segment_id="SEG-001",
                        heading=None,
                        clause_reference=self._extract_clause_ref(document_text[:200]),
                        text=document_text,
                        start_char=0,
                        end_char=len(document_text),
                        page_number=1,
                    )
                ]

            segments = []
            last_pos = 0
            for i, p_match in enumerate(para_matches):
                seg_text = document_text[last_pos:p_match.start()].strip()
                if seg_text:
                    segments.append(
                        ClauseSegment(
                            segment_id=f"SEG-{i+1:03d}",
                            heading=None,
                            clause_reference=self._extract_clause_ref(seg_text[:100]),
                            text=seg_text,
                            start_char=last_pos,
                            end_char=p_match.start(),
                            page_number=(last_pos // self.chars_per_page) + 1,
                        )
                    )
                last_pos = p_match.end()

            if last_pos < len(document_text):
                remaining_text = document_text[last_pos:].strip()
                if remaining_text:
                    segments.append(
                        ClauseSegment(
                            segment_id=f"SEG-{len(segments)+1:03d}",
                            heading=None,
                            clause_reference=self._extract_clause_ref(remaining_text[:100]),
                            text=remaining_text,
                            start_char=last_pos,
                            end_char=len(document_text),
                            page_number=(last_pos // self.chars_per_page) + 1,
                        )
                    )
            return segments

        # Sort boundaries by start character
        boundaries.sort(key=lambda b: b[0])
        
        # Deduplicate overlapping boundaries
        clean_boundaries = []
        for b in boundaries:
            if not clean_boundaries or b[0] >= clean_boundaries[-1][1]:
                clean_boundaries.append(b)

        segments = []
        # Pre-heading preamble if any
        if clean_boundaries[0][0] > 0:
            preamble = document_text[:clean_boundaries[0][0]].strip()
            if preamble:
                segments.append(
                    ClauseSegment(
                        segment_id="SEG-000",
                        heading="Preamble / Recitals",
                        clause_reference=None,
                        text=preamble,
                        start_char=0,
                        end_char=clean_boundaries[0][0],
                        page_number=1,
                    )
                )

        for i, b in enumerate(clean_boundaries):
            start = b[0]
            end = clean_boundaries[i+1][0] if i + 1 < len(clean_boundaries) else len(document_text)
            seg_text = document_text[start:end].strip()
            heading_text = b[2]
            clause_ref = self._extract_clause_ref(heading_text)

            segments.append(
                ClauseSegment(
                    segment_id=f"SEG-{i+1:03d}",
                    heading=heading_text,
                    clause_reference=clause_ref,
                    text=seg_text,
                    start_char=start,
                    end_char=end,
                    page_number=(start // self.chars_per_page) + 1,
                )
            )

        return segments

    def _extract_clause_ref(self, text: str) -> Optional[str]:
        """Helper to extract a standard clause reference."""
        m = re.search(r'(?:clause|section|article|§)\s*(\d+(?:\.\d+)*)', text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
        m_num = re.match(r'^(\d{1,2}(?:\.\d{1,2})*)', text.strip())
        if m_num:
            return f"Clause {m_num.group(1)}"
        return None
