import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import schema
from ..services.embedding_service import EmbeddingService
from ..services.llm_provider import get_llm_provider
from ..schemas.tender import MatchResult
import json

logger = logging.getLogger(__name__)

class MatchingAgent:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.llm_provider = get_llm_provider()

    def evaluate_requirement(self, requirement: schema.Requirement, db: Session) -> schema.Match:
        """
        Evaluate a single requirement using RAG against company documents.
        """
        logger.info(f"Evaluating requirement: {requirement.description[:50]}...")
        
        # 1. Embed the requirement
        req_vector = self.embedding_service.get_embedding(requirement.description)
        
        # 2. Vector search for top-K matching chunks
        # Uses pgvector's cosine distance `<=>` operator
        top_chunks = db.query(schema.DocumentChunk).order_by(
            schema.DocumentChunk.embedding.cosine_distance(req_vector)
        ).limit(3).all()
        
        evidence_text = "\n\n".join([chunk.text_content for chunk in top_chunks])
        
        # 3. LLM Reasoning
        prompt = (
            f"Analyze if the company can satisfy the following tender requirement based ONLY on the provided evidence.\n"
            f"Requirement: {requirement.description}\n"
            f"Evidence: {evidence_text}\n"
            f"You must strictly output JSON matching the schema, with status as SATISFIED, NOT_SATISFIED, PARTIALLY_SATISFIED, or UNKNOWN."
        )
        
        try:
            # Using our LLM structured data extraction
            match_data = self.llm_provider.extract_structured_data(
                text="", 
                schema=MatchResult, 
                prompt=prompt
            )
            
            # Since mock provider returns static data, we manually fix it to match the requested format for demo.
            db_match = schema.Match(
                requirement_id=requirement.id,
                status=match_data.status if hasattr(match_data, "status") else "UNKNOWN",
                evidence=evidence_text[:1000], # store a snippet or reference
                explanation=match_data.explanation if hasattr(match_data, "explanation") else "Mock explanation"
            )
            return db_match
        except Exception as e:
            logger.error(f"Failed to match requirement: {str(e)}")
            # Fallback
            return schema.Match(
                requirement_id=requirement.id,
                status="UNKNOWN",
                evidence="",
                explanation=f"Error evaluating requirement: {str(e)}"
            )
