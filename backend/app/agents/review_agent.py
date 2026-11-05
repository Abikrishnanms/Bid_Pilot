import logging
from sqlalchemy.orm import Session
from ..models import schema
from ..services.llm_provider import get_llm_provider
from ..schemas.tender import ProposalReviewResult

logger = logging.getLogger(__name__)

class ReviewAgent:
    def __init__(self):
        self.llm_provider = get_llm_provider()

    def review_proposal(self, proposal_id: int, db: Session) -> ProposalReviewResult:
        """
        Audits proposal content against verified company documents to detect
        hallucinations, exaggerated metrics, or unverified certification claims.
        """
        proposal = db.query(schema.Proposal).filter(schema.Proposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")

        tender = proposal.tender
        logger.info(f"Auditing proposal {proposal_id} for Tender: '{tender.title}'")

        # Fetch verified company evidence chunks
        chunks = db.query(schema.DocumentChunk).limit(15).all()
        ground_truth = "\n---\n".join([c.text_content for c in chunks])

        prompt = (
            f"You are BidPilot's Compliance and Anti-Hallucination Review Agent.\n"
            f"Audit the following draft proposal against verified Company Ground Truth evidence.\n\n"
            f"COMPANY GROUND TRUTH EVIDENCE:\n{ground_truth}\n\n"
            f"DRAFT PROPOSAL TO AUDIT:\n{proposal.full_content}\n\n"
            f"TASK:\n"
            f"1. Identify any claims in the proposal that are NOT supported by the Ground Truth evidence.\n"
            f"2. Check if any missing certifications or eligibility gaps are falsely claimed as fulfilled.\n"
            f"3. Calculate a review confidence score between 0 and 100.\n"
            f"4. Provide recommendations for the human manager before submission."
        )

        try:
            result: ProposalReviewResult = self.llm_provider.extract_structured_data(
                text=proposal.full_content or "",
                schema=ProposalReviewResult,
                prompt=prompt
            )

            # Update proposal status
            proposal.fact_check_passed = 1 if result.passed else -1
            proposal.review_notes = f"Score: {result.review_score}/100\nRecommendations: " + "; ".join(result.recommendations)
            if result.passed:
                proposal.status = "VERIFIED"

            db.commit()
            db.refresh(proposal)
            logger.info(f"Audit completed for proposal {proposal_id}. Passed: {result.passed}, Score: {result.review_score}")
            return result

        except Exception as e:
            logger.error(f"Failed to audit proposal: {str(e)}")
            db.rollback()
            raise
