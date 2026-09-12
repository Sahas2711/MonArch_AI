from typing import List, Optional
from pydantic import BaseModel, Field


class ViolationItem(BaseModel):
    clause_text: str = Field(..., description="The offending contractual clause")
    violation_type: str = Field(..., description="payment_cycle | interest_penalty | tax_disallowance | dispute_resolution")
    cited_law: str = Field(..., description="The specific Indian statute or section violated")
    cited_chunk_id: Optional[str] = Field(None, description="RAG chunk reference identifier")
    severity: str = Field("high", description="high | medium | low")
    draft_counter_clause: str = Field(..., description="Legally sound substitute clause compliant with MSME Act")
    samadhaan_ready: bool = Field(True, description="Whether this violation qualifies for MSME Samadhaan dispute filing")


class AnalysisReport(BaseModel):
    report_id: str
    buyer_name: str
    file_name: Optional[str] = "Contract Agreement"
    compliance_score: int = Field(..., description="0-100 score where 100 is fully compliant")
    violations: List[ViolationItem] = []
    overall_summary: str
    draft_samadhaan_complaint: Optional[str] = None
    analyzed_at: str
    disclaimer: str = "For informational and compliance guidance purposes only. Not formal legal advice."
