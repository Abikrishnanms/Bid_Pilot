import logging
import json
from sqlalchemy.orm import Session
from ..models import schema
from ..services.llm_provider import get_llm_provider
from ..schemas.tender import ProposalDraft

logger = logging.getLogger(__name__)

class ProposalAgent:
    def __init__(self):
        self.llm_provider = get_llm_provider()

    def generate_proposal(self, tender_id: int, db: Session) -> schema.Proposal:
        """
        Gathers evaluated requirements, evidence citations, and generates
        a comprehensive, grounded bid proposal using GenAI.
        """
        tender = db.query(schema.Tender).filter(schema.Tender.id == tender_id).first()
        if not tender:
            raise ValueError(f"Tender {tender_id} not found.")

        logger.info(f"Generating proposal for Tender {tender_id}: '{tender.title}'")

        # Compile evidence context from requirement matches
        evidence_lines = []
        compliance_matrix_data = []

        for req in tender.requirements:
            match = db.query(schema.Match).filter(schema.Match.requirement_id == req.id).first()
            status = match.status if match else "UNKNOWN"
            evidence = match.evidence if match and match.evidence else "No specific evidence cited"
            explanation = match.explanation if match and match.explanation else ""

            evidence_lines.append(
                f"- Requirement [{req.req_type}]: {req.description}\n"
                f"  Status: {status}\n"
                f"  Cited Company Evidence: {evidence}\n"
                f"  Analysis: {explanation}\n"
            )

            compliance_matrix_data.append({
                "requirement": req.description,
                "type": req.req_type,
                "status": status,
                "evidence": evidence[:250],
                "explanation": explanation
            })

        evidence_context = "\n".join(evidence_lines)

        prompt = (
            f"You are BidPilot's Senior Bid Management & Technical Proposal Agent.\n"
            f"Draft a formal, persuasive, and legally compliant proposal for the following tender.\n"
            f"IMPORTANT: You MUST ground all technical capabilities, team sizes, past projects, "
            f"and certifications strictly in the provided company evidence. DO NOT hallucinate nonexistent certifications.\n\n"
            f"TENDER SPECIFICATIONS:\n"
            f"- Title: {tender.title}\n"
            f"- Issuing Authority: {tender.organization}\n"
            f"- Budget / Estimated Value: {tender.estimated_value}\n"
            f"- Deadline: {tender.deadline}\n"
            f"- Location: {tender.location}\n\n"
            f"EVALUATED REQUIREMENTS & EVIDENCE:\n{evidence_context}\n\n"
            f"Generate a comprehensive ProposalDraft matching the schema, with a complete Markdown document "
            f"incorporating Executive Summary, Technical Architecture, Compliance Matrix, and Commercial Terms."
        )

        try:
            draft_data: ProposalDraft = self.llm_provider.extract_structured_data(
                text=evidence_context,
                schema=ProposalDraft,
                prompt=prompt
            )

            # Check if proposal already exists
            proposal = db.query(schema.Proposal).filter(schema.Proposal.tender_id == tender_id).first()
            if not proposal:
                proposal = schema.Proposal(tender_id=tender_id)
                db.add(proposal)

            proposal.executive_summary = draft_data.executive_summary
            proposal.technical_approach = draft_data.technical_approach
            proposal.compliance_matrix = compliance_matrix_data
            proposal.commercial_terms = draft_data.commercial_terms
            proposal.full_content = draft_data.full_markdown
            proposal.status = "DRAFT"
            proposal.fact_check_passed = 0

            # Update tender status
            tender.status = "PROPOSAL_READY"

            db.commit()
            db.refresh(proposal)
            logger.info(f"Proposal draft successfully saved for Tender {tender_id}.")
            return proposal

        except Exception as e:
            logger.error(f"Failed to generate proposal: {str(e)}")
            db.rollback()
            raise
