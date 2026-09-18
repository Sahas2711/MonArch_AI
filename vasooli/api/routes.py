"""
Vasooli V2 FastAPI Routes.

RESTful API endpoints for deterministic MSME contract compliance,
evidence retrieval, policy registry inspection, financial calculations,
and tamper-evident audit logs.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from vasooli.domain.errors import DocumentSecurityError, VasooliError
from vasooli.domain.models import AnalysisReportV2, FinancialCalculation, TaxExposureEstimate
from vasooli.finance.interest import StatutoryInterestCalculator
from vasooli.finance.tax_exposure import estimate_section_43bh_tax_exposure
from vasooli.pipeline.orchestrator import VasooliOrchestrator
from vasooli.policy.msmed_act_rules import create_default_policy_registry
from vasooli.security.upload_guard import UploadGuard


router = APIRouter(prefix="/api/v2", tags=["Vasooli V2 Compliance Engine"])

orchestrator = VasooliOrchestrator()
upload_guard = UploadGuard()
interest_calculator = StatutoryInterestCalculator()
policy_registry = create_default_policy_registry()


class AnalyzeTextRequest(BaseModel):
    contract_text: str = Field(..., description="Raw text of the commercial contract")
    buyer_name: str = Field("Enterprise Buyer", description="Counterparty buyer name")
    file_name: Optional[str] = Field("Contract.txt", description="Document filename")
    contract_value: Optional[float] = Field(None, description="Total contract value in INR")
    delay_start_date: Optional[date] = Field(None, description="Start date of payment default if already overdue")


class ReviewSubmissionRequest(BaseModel):
    action: str = Field(..., description="approved | rejected | modified | escalated")
    reviewer_id: str = Field(..., description="ID or email of human reviewer")
    reviewer_notes: Optional[str] = Field(None, description="Reasoning or notes")
    modified_facts: Optional[Dict[str, Any]] = Field(None, description="Modifications to extracted facts if any")


class InterestCalcRequest(BaseModel):
    principal: float = Field(..., description="Principal overdue amount in INR")
    delay_start_date: date = Field(..., description="Date from which payment was overdue")
    calculation_date: Optional[date] = Field(None, description="Date up to which interest is computed")


class TaxCalcRequest(BaseModel):
    invoice_amount: float = Field(..., description="Total invoice amount in INR")
    corporate_tax_rate: Optional[float] = Field(0.25, description="Assumed corporate tax rate (e.g. 0.25 for 25%)")


@router.post("/analyze", response_model=AnalysisReportV2, summary="Run contract compliance analysis on raw text")
async def analyze_contract_text(payload: AnalyzeTextRequest):
    """
    Executes the 10-stage deterministic compliance pipeline on provided text.
    """
    try:
        report = orchestrator.analyze_contract(
            contract_text=payload.contract_text,
            buyer_name=payload.buyer_name,
            file_name=payload.file_name or "Contract.txt",
            contract_value=payload.contract_value,
            delay_start_date=payload.delay_start_date,
        )
        return report
    except VasooliError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/upload", response_model=AnalysisReportV2, summary="Upload document and run compliance analysis")
async def analyze_contract_upload(
    file: UploadFile = File(...),
    buyer_name: str = Form("Enterprise Buyer"),
    contract_value: Optional[float] = Form(None),
):
    """
    Validates uploaded file against security constraints, extracts text, and executes compliance pipeline.
    """
    try:
        content = await file.read()
        is_valid, clean_filename = upload_guard.validate_upload(file.filename, content, file.content_type)

        # Basic text decode (handles txt; for binary PDF or docx fallback to utf-8 ignore or OCR hook)
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = content.decode("latin-1", errors="ignore")

        report = orchestrator.analyze_contract(
            contract_text=raw_text,
            buyer_name=buyer_name,
            file_name=clean_filename,
            contract_value=contract_value,
        )
        return report
    except DocumentSecurityError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Security rejection: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload processing failed: {str(e)}")


@router.get("/analyses/{report_id}", response_model=AnalysisReportV2, summary="Retrieve a stored analysis report")
async def get_analysis_report(report_id: str):
    """
    Retrieves a previously computed report with all source-anchored facts and decisions.
    """
    report = orchestrator.repository.get_analysis_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")
    return report


@router.get("/analyses", summary="List historical analysis reports")
async def list_analysis_reports(limit: int = Query(50, ge=1, le=200)):
    """
    Returns list of analysis summaries.
    """
    return orchestrator.repository.list_analysis_reports(limit=limit)


@router.post("/reviews/{report_id}", summary="Submit human reviewer decision")
async def submit_review(report_id: str, payload: ReviewSubmissionRequest):
    """
    Updates the review status and records a tamper-evident audit event.
    """
    report = orchestrator.repository.get_analysis_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found.")

    report.review_status = payload.action
    orchestrator.repository.save_analysis_report(report)

    # Record Audit Event
    orchestrator.audit_manager.record_event(
        event_type="review_submitted",
        actor_id=payload.reviewer_id,
        resource_id=report_id,
        changes={
            "action": payload.action,
            "notes": payload.reviewer_notes,
            "modified_facts": payload.modified_facts,
        },
    )

    return {
        "status": "success",
        "report_id": report_id,
        "review_status": report.review_status,
        "message": f"Review action '{payload.action}' successfully recorded.",
    }


@router.get("/policies", summary="List versioned legal policy rules")
async def list_policies():
    """
    Returns the active set of legal rules enforced by the policy engine.
    """
    rules = policy_registry.list_rules()
    return [
        {
            "policy_id": r.policy_id,
            "statute": r.statute,
            "section": r.section,
            "version": r.version,
            "rule_type": r.rule_type,
            "description": r.description,
            "parameters": r.parameters,
        }
        for r in rules
    ]


@router.get("/audit/events", summary="Get audit events and verify integrity")
async def get_audit_events():
    """
    Returns all logged audit events and verifies the cryptographic SHA-256 chain integrity.
    """
    events = orchestrator.audit_manager.get_events()
    is_valid = orchestrator.audit_manager.verify_integrity()
    return {
        "integrity_verified": is_valid,
        "events_count": len(events),
        "events": events,
    }


@router.post("/finance/calculate-interest", response_model=FinancialCalculation, summary="Calculate Section 16 MSMED Interest")
async def calculate_interest_endpoint(payload: InterestCalcRequest):
    """
    Deterministic Decimal calculation of 3x RBI bank rate compound interest with monthly rests.
    """
    return interest_calculator.calculate(
        principal=Decimal(str(payload.principal)),
        delay_start_date=payload.delay_start_date,
        calculation_date=payload.calculation_date or date.today(),
    )


@router.post("/finance/estimate-tax", response_model=TaxExposureEstimate, summary="Estimate Section 43B(h) Tax Exposure")
async def estimate_tax_endpoint(payload: TaxCalcRequest):
    """
    Computes illustrative buyer tax disallowance under Section 43B(h) of the Income Tax Act, 1961.
    """
    return estimate_section_43bh_tax_exposure(
        invoice_amount=Decimal(str(payload.invoice_amount)),
        corporate_tax_rate=Decimal(str(payload.corporate_tax_rate or 0.25)),
    )
