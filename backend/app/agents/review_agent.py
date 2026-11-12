import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from ..models import schema
from ..services.chunking import extract_verifiable_claims
from ..services.llm_provider import get_llm_provider
from ..services.retrieval_service import RetrievalService
from ..schemas.tender import ProposalReviewResult

logger = logging.getLogger(__name__)


class ReviewAgent:
    def __init__(self, retrieval_service: Optional[RetrievalService] = None, llm_provider=None):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.llm_provider = llm_provider or get_llm_provider()

    def review_proposal(self, proposal_id: int, db: Session) -> ProposalReviewResult:
        """
        Audits proposal content against claim-retrieved company ground truth and tender scope
        to detect hallucinations, exaggerated metrics, domain mismatches, or unverified claims.
        """
        proposal = db.query(schema.Proposal).filter(schema.Proposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")

        tender = proposal.tender
        logger.info(f"Auditing proposal {proposal_id} for Tender: '{tender.title}'")

        proposal_text = proposal.full_content or "\n\n".join(
            part for part in [proposal.executive_summary, proposal.technical_approach, proposal.commercial_terms] if part
        )

        # 1. Claim-level Hybrid RAG across entire document repository (no blind .limit(15))
        claims = extract_verifiable_claims(proposal_text)
        retrieved_chunks = self.retrieval_service.retrieve_for_claims(
            claims=claims or [tender.title or ""],
            db=db,
            top_k_per_claim=3,
            max_total_chunks=18,
            min_similarity=0.22,
        )
        evidence_blocks: List[str] = []
        formatted_rag = RetrievalService.format_evidence(retrieved_chunks, max_chars=5000)
        if formatted_rag:
            evidence_blocks.append(formatted_rag)

        # 2. Include cited requirement match evidence linked to this tender
        if tender and tender.requirements:
            req_ids = [r.id for r in tender.requirements]
            if req_ids:
                matches = db.query(schema.Match).filter(schema.Match.requirement_id.in_(req_ids)).all()
                seen_snippets = {c.text_content for c in retrieved_chunks}
                for m in matches:
                    if m.evidence and m.evidence not in seen_snippets:
                        seen_snippets.add(m.evidence)
                        evidence_blocks.append(f"[Cited Requirement Evidence]\n{m.evidence[:600]}")

        ground_truth = "\n---\n".join(evidence_blocks) if evidence_blocks else (
            "NO COMPANY EVIDENCE FOUND IN VECTOR KNOWLEDGE BASE."
        )

        tender_context = (
            f"Tender Title: {tender.title}\n"
            f"Issuing Authority: {tender.organization}\n"
            f"Budget / Value: {tender.estimated_value}\n"
            if tender
            else ""
        )

        prompt = (
            f"You are BidPilot's Compliance and Anti-Hallucination Review Agent.\n"
            f"Adversarially audit the following draft proposal against verified Company Ground Truth evidence AND the actual tender scope.\n\n"
            f"TENDER SCOPE:\n{tender_context}\n"
            f"COMPANY GROUND TRUTH EVIDENCE (Retrieved via Hybrid RAG):\n{ground_truth}\n\n"
            f"DRAFT PROPOSAL TO AUDIT:\n{proposal_text}\n\n"
            f"TASK:\n"
            f"1. Identify any claims in the proposal (certifications, past contracts, team counts, technical stack, clearances) that are NOT supported by the Company Ground Truth evidence.\n"
            f"2. Flag domain mismatches if the tender asks for non-company work (e.g. civil works/construction) while the proposal claims unrelated software/IT delivery.\n"
            f"3. Calculate a review confidence score between 0 and 100 (set passed=False if unsupported claims or domain mismatch exist, or score < 70).\n"
            f"4. Provide actionable recommendations for the human manager before submission."
        )

        try:
            result: ProposalReviewResult = self.llm_provider.extract_structured_data(
                text=proposal_text,
                schema=ProposalReviewResult,
                prompt=prompt,
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
