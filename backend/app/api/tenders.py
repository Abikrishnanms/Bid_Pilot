from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
import re

from ..db.database import get_db
from ..models import schema
from ..schemas.tender import (
    ExtractedRequirements,
    TenderProcessRequest,
    TriageResult,
    ProposalReviewResult,
    EmailSendRequest
)
from ..agents.extraction_agent import ExtractionAgent
from ..agents.matching_agent import MatchingAgent
from ..agents.triage_agent import TriageAgent
from ..agents.proposal_agent import ProposalAgent
from ..agents.review_agent import ReviewAgent
from ..services.tender_fetcher import TenderFetcherService
from ..services.email_service import EmailService

router = APIRouter()
extraction_agent = ExtractionAgent()
matching_agent = MatchingAgent()
triage_agent = TriageAgent()
proposal_agent = ProposalAgent()
review_agent = ReviewAgent()
email_service = EmailService()

@router.get("/")
def list_tenders(db: Session = Depends(get_db)):
    """List all tenders ordered by ID descending with their fit scores and statuses."""
    tenders = db.query(schema.Tender).order_by(schema.Tender.id.desc()).all()
    results = []
    for t in tenders:
        results.append({
            "id": t.id,
            "reference_id": t.reference_id,
            "title": t.title,
            "organization": t.organization,
            "deadline": t.deadline,
            "estimated_value": t.estimated_value,
            "location": t.location,
            "status": t.status,
            "fit_score": t.fit_score,
            "has_proposal": t.proposal is not None,
            "proposal_status": t.proposal.status if t.proposal else None
        })
    return results

@router.get("/{tender_id}")
def get_tender_detail(tender_id: int, db: Session = Depends(get_db)):
    """Retrieve full details of a tender, its requirements, matches, and proposal."""
    tender = db.query(schema.Tender).filter(schema.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    requirements_data = []
    for req in tender.requirements:
        match = db.query(schema.Match).filter(schema.Match.requirement_id == req.id).first()
        requirements_data.append({
            "id": req.id,
            "type": req.req_type,
            "description": req.description,
            "status": match.status if match else "PENDING",
            "evidence": match.evidence if match else None,
            "explanation": match.explanation if match else None
        })

    proposal_data = None
    if tender.proposal:
        p = tender.proposal
        proposal_data = {
            "id": p.id,
            "status": p.status,
            "executive_summary": p.executive_summary,
            "technical_approach": p.technical_approach,
            "compliance_matrix": p.compliance_matrix,
            "commercial_terms": p.commercial_terms,
            "full_content": p.full_content,
            "fact_check_passed": p.fact_check_passed,
            "review_notes": p.review_notes,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        }

    return {
        "id": tender.id,
        "reference_id": tender.reference_id,
        "title": tender.title,
        "organization": tender.organization,
        "deadline": tender.deadline,
        "estimated_value": tender.estimated_value,
        "location": tender.location,
        "status": tender.status,
        "fit_score": tender.fit_score,
        "issuer_email": tender.issuer_email,
        "requirements": requirements_data,
        "proposal": proposal_data
    }

@router.post("/fetch_new")
def fetch_new_tenders(db: Session = Depends(get_db)):
    """Triggers autonomous discovery of new tenders from procurement feeds."""
    fetcher = TenderFetcherService(db)
    new_tenders = fetcher.poll_and_ingest_all()
    return {
        "message": f"Successfully checked feeds. Ingested {len(new_tenders)} new tenders.",
        "new_count": len(new_tenders),
        "tenders": [{"id": t.id, "title": t.title, "reference_id": t.reference_id, "fit_score": t.fit_score} for t in new_tenders]
    }

@router.post("/{tender_id}/triage", response_model=TriageResult)
def triage_tender(tender_id: int, db: Session = Depends(get_db)):
    """Runs autonomous Go / No-Go qualification evaluation."""
    return triage_agent.evaluate_tender(tender_id, db)

@router.post("/{tender_id}/proposal")
def generate_tender_proposal(tender_id: int, db: Session = Depends(get_db)):
    """Generates an evidence-grounded bid proposal using GenAI."""
    try:
        proposal = proposal_agent.generate_proposal(tender_id, db)
        return {
            "message": "Proposal drafted successfully",
            "proposal_id": proposal.id,
            "status": proposal.status,
            "full_content": proposal.full_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{tender_id}/proposal/review")
def review_tender_proposal(tender_id: int, db: Session = Depends(get_db)):
    """Audits proposal against company ground truth to prevent hallucinations."""
    tender = db.query(schema.Tender).filter(schema.Tender.id == tender_id).first()
    if not tender or not tender.proposal:
        raise HTTPException(status_code=404, detail="Tender has no drafted proposal to review")

    result = review_agent.review_proposal(tender.proposal.id, db)
    return result

@router.post("/{tender_id}/proposal/submit")
def submit_tender_proposal(tender_id: int, request: EmailSendRequest = None, db: Session = Depends(get_db)):
    """Human approval gate: dispatches verified proposal to issuing organization via email."""
    tender = db.query(schema.Tender).filter(schema.Tender.id == tender_id).first()
    if not tender or not tender.proposal:
        raise HTTPException(status_code=404, detail="Tender has no proposal ready for submission")

    recipient = request.recipient_email if request else None
    notes = request.notes if request else None

    try:
        dispatch_result = email_service.send_proposal(
            proposal_id=tender.proposal.id,
            db=db,
            recipient_override=recipient,
            notes=notes
        )
        return dispatch_result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Submission failed: {str(e)}")

class TenderStatusUpdateRequest(BaseModel):
    status: str

@router.get("/metrics/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Provides dynamic, real-time KPI metrics calculated directly from database records."""
    all_tenders = db.query(schema.Tender).all()
    total_tenders = len(all_tenders)
    
    # 1. Pipeline value dynamically calculated from all active tender opportunities
    total_pipeline_val = 0.0
    for t in all_tenders:
        if t.estimated_value:
            nums = re.findall(r'[\d,]+(?:\.\d+)?', t.estimated_value)
            if nums:
                try:
                    val = float(nums[0].replace(',', ''))
                    total_pipeline_val += val
                except ValueError:
                    pass

    # Format pipeline value dynamically
    if total_pipeline_val >= 1_000_000:
        pipeline_display = f"${total_pipeline_val / 1_000_000:.2f}M"
    elif total_pipeline_val >= 1_000:
        pipeline_display = f"${total_pipeline_val / 1_000:.1f}K"
    else:
        pipeline_display = f"${total_pipeline_val:.0f}"

    # 2. Status counts
    go_tenders = sum(1 for t in all_tenders if t.status in ["PROPOSAL_READY", "APPROVED", "SUBMITTED", "WON"])
    submitted_bids = sum(1 for t in all_tenders if t.status in ["SUBMITTED", "WON", "LOST"])
    won_bids = sum(1 for t in all_tenders if t.status == "WON")
    lost_bids = sum(1 for t in all_tenders if t.status == "LOST")

    # 3. Dynamic Success Rate (%) calculated as percentage of submitted bids marked as WON
    if submitted_bids > 0:
        win_rate = round((won_bids / submitted_bids) * 100, 1)
        success_rate_display = f"{win_rate}%"
    else:
        win_rate = 0.0
        success_rate_display = "0.0%"

    # 4. Turnaround speed dynamically calculated from Proposal timestamps
    submitted_proposals = db.query(schema.Proposal).filter(schema.Proposal.status.in_(["SUBMITTED", "WON", "LOST"])).all()
    if submitted_proposals:
        total_seconds = 0
        valid_count = 0
        for p in submitted_proposals:
            if p.created_at and p.updated_at:
                diff = (p.updated_at - p.created_at).total_seconds()
                if diff > 0:
                    total_seconds += diff
                    valid_count += 1
        if valid_count > 0:
            avg_days = round(total_seconds / (valid_count * 86400), 2)
            avg_hours = round(total_seconds / (valid_count * 3600), 1)
            turnaround_display = f"{avg_hours}h" if avg_hours >= 1 else "< 1h"
            response_days_display = f"{avg_days} days"
        else:
            avg_days = 0.0
            turnaround_display = "< 1h"
            response_days_display = "< 1 day"
    else:
        avg_days = 0.0
        turnaround_display = "0h"
        response_days_display = "0 days"

    pending_approvals = db.query(schema.Proposal).filter(schema.Proposal.status.in_(["DRAFT", "VERIFIED"])).count()
    docs_count = db.query(schema.Document).count()
    chunks_count = db.query(schema.DocumentChunk).count()

    return {
        "active_tenders": total_tenders,
        "qualified_go_tenders": go_tenders,
        "pipeline_value": pipeline_display,
        "raw_pipeline_value": total_pipeline_val,
        "submitted_bids": submitted_bids,
        "submitted_proposals": submitted_bids,
        "won_bids": won_bids,
        "lost_bids": lost_bids,
        "success_rate": success_rate_display,
        "success_rate_percentage": win_rate,
        "avg_response_days": avg_days,
        "avg_response_days_display": response_days_display,
        "avg_turnaround": turnaround_display,
        "company_documents": docs_count,
        "indexed_chunks": chunks_count,
        "pending_approvals": pending_approvals
    }

@router.patch("/{tender_id}/status")
def update_tender_status(tender_id: int, request: TenderStatusUpdateRequest, db: Session = Depends(get_db)):
    """Update tender outcome (e.g. mark bid as WON or LOST to track actual win rate)."""
    tender = db.query(schema.Tender).filter(schema.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    valid_statuses = ["DISCOVERED", "EVALUATED", "PROPOSAL_READY", "APPROVED", "SUBMITTED", "WON", "LOST", "NO_GO"]
    new_status = request.status.upper().strip()
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    tender.status = new_status
    if tender.proposal and new_status in ["WON", "LOST"]:
        tender.proposal.status = new_status

    db.commit()
    db.refresh(tender)
    return {"message": f"Tender #{tender_id} status updated to {new_status}", "status": tender.status}

@router.post("/upload")
async def upload_custom_tender_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload any real-world RFP PDF tender to extract, evaluate, and triage dynamically."""
    incoming_dir = "data/incoming_tenders"
    os.makedirs(incoming_dir, exist_ok=True)
    save_path = os.path.join(incoming_dir, file.filename)
    
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
        
    req = TenderProcessRequest(file_path=save_path)
    return process_tender(req, db)

@router.post("/process", response_model=ExtractedRequirements)
def process_tender(request: TenderProcessRequest, db: Session = Depends(get_db)):
    """Manual PDF extraction endpoint (retained for custom file uploads)."""
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="Tender PDF not found")
        
    try:
        extracted = extraction_agent.process_tender(request.file_path)
        db_tender = schema.Tender(
            title=extracted.title,
            organization=extracted.organization,
            deadline=extracted.deadline,
            estimated_value=extracted.estimated_value,
            location=extracted.location,
            pdf_path=request.file_path,
            status="DISCOVERED"
        )
        db.add(db_tender)
        db.commit()
        db.refresh(db_tender)
        
        for req in extracted.technical_requirements:
            db.add(schema.Requirement(tender_id=db_tender.id, req_type="technical", description=req))
        for req in extracted.eligibility_requirements:
            db.add(schema.Requirement(tender_id=db_tender.id, req_type="eligibility", description=req))
        for req in extracted.certifications_required:
            db.add(schema.Requirement(tender_id=db_tender.id, req_type="certification", description=req))
        db.commit()

        # Run triage immediately
        triage_agent.evaluate_tender(db_tender.id, db)

        return extracted
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{tender_id}/matches")
def match_tender_requirements(tender_id: int, db: Session = Depends(get_db)):
    """Trigger the matching agent to evaluate all requirements for a given tender."""
    tender = db.query(schema.Tender).filter(schema.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
        
    results = []
    for req in tender.requirements:
        existing_match = db.query(schema.Match).filter(schema.Match.requirement_id == req.id).first()
        if existing_match:
            results.append(existing_match)
            continue
            
        match_res = matching_agent.evaluate_requirement(req, db)
        db.add(match_res)
        db.commit()
        db.refresh(match_res)
        results.append(match_res)
        
    return {"message": f"Successfully evaluated {len(results)} requirements", "tender_id": tender_id}
