from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..models import schema
from ..schemas.tender import ExtractedRequirements, TenderProcessRequest
from ..agents.extraction_agent import ExtractionAgent
import os

router = APIRouter()
extraction_agent = ExtractionAgent()

@router.post("/process", response_model=ExtractedRequirements)
def process_tender(request: TenderProcessRequest, db: Session = Depends(get_db)):
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="Tender PDF not found")
        
    try:
        # Step 1: Extract Requirements
        extracted = extraction_agent.process_tender(request.file_path)
        
        # Step 2: Save to Database
        db_tender = schema.Tender(
            title=extracted.title,
            organization=extracted.organization,
            deadline=extracted.deadline,
            estimated_value=extracted.estimated_value,
            location=extracted.location
        )
        db.add(db_tender)
        db.commit()
        db.refresh(db_tender)
        
        for req in extracted.technical_requirements:
            db.add(schema.Requirement(tender_id=db_tender.id, req_type="technical", description=req))
        for req in extracted.eligibility_requirements:
            db.add(schema.Requirement(tender_id=db_tender.id, req_type="eligibility", description=req))
        # Add other requirements...
        db.commit()

        return extracted
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{tender_id}/matches")
def match_tender_requirements(tender_id: int, db: Session = Depends(get_db)):
    """
    Trigger the matching agent to evaluate all requirements for a given tender.
    """
    from ..agents.matching_agent import MatchingAgent
    
    tender = db.query(schema.Tender).filter(schema.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
        
    matching_agent = MatchingAgent()
    results = []
    
    for req in tender.requirements:
        # Check if already matched
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
