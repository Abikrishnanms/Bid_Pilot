import logging
from typing import Optional
from sqlalchemy.orm import Session
from ..models import schema
from ..services.llm_provider import get_llm_provider
from ..services.retrieval_service import RetrievalService
from ..schemas.tender import MatchResult

logger = logging.getLogger(__name__)


class MatchingAgent:
    def __init__(self, retrieval_service: Optional[RetrievalService] = None, llm_provider=None):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.llm_provider = llm_provider or get_llm_provider()

    def evaluate_requirement(
        self,
        requirement: schema.Requirement,
        db: Session,
        tender: Optional[schema.Tender] = None,
    ) -> schema.Match:
        """
        Evaluate a single requirement using Hybrid RAG (pgvector + FTS) against company documents.
        """
        logger.info(f"Evaluating requirement: {requirement.description[:50]}...")

        # 1. Hybrid retrieval with similarity threshold filtering
        top_chunks = self.retrieval_service.retrieve(
            query=requirement.description,
            db=db,
            top_k=3,
        )

        if not top_chunks:
            return schema.Match(
                requirement_id=requirement.id,
                status="NOT_SATISFIED",
                top_similarity=0.0,
                evidence="",
                explanation="No matching company evidence met the minimum RAG relevance threshold.",
            )

        top_sim = round(max(chunk.dense_similarity for chunk in top_chunks), 4)
        evidence_text = RetrievalService.format_evidence(top_chunks, max_chars=1500)

        tender_scope = ""
        if tender is not None:
            tender_scope = (
                f"Tender Context: '{tender.title}' (Issuing Organization: '{tender.organization}')\n"
            )

        # 2. LLM Reasoning with explicit tender scope & source-attributed evidence
        prompt = (
            f"Analyze if the company can satisfy the following tender requirement based ONLY on the provided evidence.\n"
            f"Verify that the evidence genuinely aligns with the tender's domain and scope.\n"
            f"{tender_scope}"
            f"Requirement [{requirement.req_type}]: {requirement.description}\n"
            f"Evidence:\n{evidence_text}\n\n"
            f"You must strictly output JSON matching the schema, with status as SATISFIED, NOT_SATISFIED, PARTIALLY_SATISFIED, or UNKNOWN."
        )

        try:
            match_data = self.llm_provider.extract_structured_data(
                text="",
                schema=MatchResult,
                prompt=prompt,
            )

            db_match = schema.Match(
                requirement_id=requirement.id,
                status=match_data.status if hasattr(match_data, "status") and match_data.status else "UNKNOWN",
                top_similarity=top_sim,
                evidence=evidence_text[:1000],
                explanation=(
                    match_data.explanation
                    if hasattr(match_data, "explanation") and match_data.explanation
                    else "Requirement evaluated against company ground truth evidence."
                ),
            )
            return db_match
        except Exception as e:
            logger.error(f"Failed to match requirement: {str(e)}")
            return schema.Match(
                requirement_id=requirement.id,
                status="UNKNOWN",
                top_similarity=top_sim,
                evidence=evidence_text[:1000],
                explanation=f"Error evaluating requirement: {str(e)}",
            )
