import os
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from ..models import schema
from ..agents.matching_agent import MatchingAgent
from ..services.llm_provider import get_llm_provider
from ..schemas.tender import TriageResult, StrategicTriageAnalysis

logger = logging.getLogger(__name__)

class TriageAgent:
    def __init__(self):
        self.matching_agent = MatchingAgent()
        self.llm_provider = get_llm_provider()
        # Dynamic configurable thresholds (can be customized via .env or settings)
        self.go_threshold = float(os.getenv("TRIAGE_GO_THRESHOLD", "70.0"))
        self.review_threshold = float(os.getenv("TRIAGE_REVIEW_THRESHOLD", "50.0"))

    def evaluate_tender(self, tender_id: int, db: Session) -> TriageResult:
        """
        Evaluates all requirements using pgvector RAG, calculates overall Fit Score,
        uses GenAI strategic reasoning to detect true fatal blockers vs manageable risks,
        and renders an autonomous GO / NO-GO / REVIEW decision.
        """
        tender = db.query(schema.Tender).filter(schema.Tender.id == tender_id).first()
        if not tender:
            raise ValueError(f"Tender {tender_id} not found.")

        logger.info(f"Running autonomous strategic triage evaluation for Tender {tender_id}: '{tender.title}'")

        satisfied_count = 0
        partially_count = 0
        gap_count = 0
        unfulfilled_reqs = []

        total_reqs = len(tender.requirements)
        if total_reqs == 0:
            tender.fit_score = 0.0
            tender.status = "NO_GO"
            db.commit()
            return TriageResult(
                tender_id=tender_id,
                fit_score=0.0,
                decision="NO_GO",
                rationale="Tender contains no parseable requirements.",
                hard_blockers=["No requirements extracted from document"],
                satisfied_count=0,
                gap_count=0
            )

        # 1. Match each requirement against company vector knowledge base
        for req in tender.requirements:
            match = db.query(schema.Match).filter(schema.Match.requirement_id == req.id).first()
            if not match:
                match = self.matching_agent.evaluate_requirement(req, db)
                db.add(match)
                db.commit()
                db.refresh(match)

            status = match.status.upper()
            if status == "SATISFIED":
                satisfied_count += 1
            elif status == "PARTIALLY_SATISFIED":
                partially_count += 1
                unfulfilled_reqs.append({
                    "requirement": req.description,
                    "type": req.req_type,
                    "status": "PARTIALLY_SATISFIED",
                    "explanation": match.explanation
                })
            else:
                gap_count += 1
                unfulfilled_reqs.append({
                    "requirement": req.description,
                    "type": req.req_type,
                    "status": "GAP",
                    "explanation": match.explanation or "No matching evidence found in company profile"
                })

        # 2. Compute Qualification Fit Score (0.0 to 100.0)
        fit_score = round(((satisfied_count + (0.5 * partially_count)) / total_reqs) * 100, 1)
        tender.fit_score = fit_score

        # 3. Dynamic GenAI Blocker & Strategy Analysis
        hard_blockers: List[str] = []
        
        if unfulfilled_reqs:
            # Fetch company summary context
            company = db.query(schema.Company).first()
            company_context = company.profile_summary if company else "Enterprise Software and IT Engineering"

            prompt = (
                f"You are BidPilot's Senior Bid Director and Procurement Triage Officer.\n"
                f"We are evaluating qualification fit for Tender: '{tender.title}' (Issuing Org: '{tender.organization}').\n"
                f"Company Profile: {company_context}\n\n"
                f"The following requirements have potential gaps or partial fulfillment:\n"
            )
            for item in unfulfilled_reqs:
                prompt += f"- [{item['type'].upper()}] {item['requirement']} (Current Status: {item['status']})\n"

            prompt += (
                f"\nTASK:\n"
                f"1. Analyze whether any of these unfulfilled items are TRUE FATAL BLOCKERS (e.g. statutory licenses, mandatory security clearances, non-negotiable regulatory certifications that would legally void our bid).\n"
                f"2. Distinguish fatal blockers from manageable operational gaps that can be solved via teaming, subcontracting, or onboarding.\n"
                f"3. Provide a concise 2-3 sentence strategic rationale explaining the qualification stance and risk profile.\n"
                f"Return ONLY valid JSON matching the StrategicTriageAnalysis schema."
            )

            try:
                analysis: StrategicTriageAnalysis = self.llm_provider.extract_structured_data(
                    text=f"Tender: {tender.title}\nFit Score: {fit_score}%",
                    schema=StrategicTriageAnalysis,
                    prompt=prompt
                )
                hard_blockers = analysis.fatal_blockers or []
                rationale = analysis.strategic_rationale or f"Qualification match evaluated at {fit_score}%."
            except Exception as e:
                logger.warning(f"GenAI Strategic Triage analysis fell back: {e}")
                hard_blockers = []
                rationale = f"Evaluated qualification fit at {fit_score}%. {gap_count} gaps identified for review."
        else:
            hard_blockers = []
            rationale = f"Strong qualification match ({fit_score}%). All technical, eligibility, and regulatory requirements are fully verified."

        # 4. Dynamic Decision Gate using Configurable Thresholds
        if fit_score >= self.go_threshold and len(hard_blockers) == 0:
            decision = "GO"
            tender.status = "PROPOSAL_READY"
            
            # Automatically draft proposal for GO-qualified tenders
            try:
                from ..agents.proposal_agent import ProposalAgent
                proposal_agent = ProposalAgent()
                proposal_agent.generate_proposal(tender_id, db)
                logger.info(f"Automatically drafted proposal for GO-qualified tender {tender_id}.")
            except Exception as e:
                logger.warning(f"Failed to auto-draft proposal during triage: {e}")

        elif fit_score >= self.review_threshold and len(hard_blockers) == 0:
            decision = "REVIEW"
            tender.status = "EVALUATED"
        else:
            decision = "NO_GO"
            tender.status = "NO_GO"

        db.commit()
        db.refresh(tender)

        return TriageResult(
            tender_id=tender_id,
            fit_score=fit_score,
            decision=decision,
            rationale=rationale,
            hard_blockers=hard_blockers,
            satisfied_count=satisfied_count,
            gap_count=gap_count
        )
