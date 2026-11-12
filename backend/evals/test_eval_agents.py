"""Tier-3 Agentic Evaluation Suite (Matching, Triage, Anti-Hallucination Guardrails, ORM integration)."""
import os
import pytest

from evals.fixtures import DeterministicEvalEmbeddingService, load_dataset
from evals.runners import run_agentic_benchmark


def test_agentic_benchmark_triage_and_hallucination_audit():
    run_live = os.getenv("RUN_LIVE_EVALS", "0") == "1"
    report = run_agentic_benchmark(live=run_live, prefer_real_embeddings=True)

    assert report["corpus_chunk_count"] > 15
    assert report["triage"]["false_positive_go_rate"] == 0.0
    assert report["triage"]["accuracy"] >= 0.75
    assert report["anti_hallucination_review"]["hallucination_tpr"] >= 0.90, report["anti_hallucination_review"]
    assert report["anti_hallucination_review"]["false_alarm_fpr"] == 0.0, report["anti_hallucination_review"]
    assert report["anti_hallucination_review"]["score_separation"] >= 30.0, report["anti_hallucination_review"]


def test_orm_agents_integration_with_pgvector_when_available():
    """Full ORM integration check verifying MatchingAgent threshold, force_refresh, and >15-chunk ReviewAgent RAG."""
    pytest.importorskip("pgvector")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.database import Base
    from app.models import schema
    from app.schemas.tender import MatchResult, ProposalReviewResult, StrategicTriageAnalysis
    from app.services.chunking import chunk_text
    from app.services.retrieval_service import RetrievalService
    from app.agents.matching_agent import MatchingAgent
    from app.agents.triage_agent import TriageAgent
    from app.agents.review_agent import ReviewAgent

    class _StubLLM:
        def __init__(self):
            self.last_review_prompt = ""
            self.match_calls = 0

        def extract_structured_data(self, text, schema, prompt):
            if schema == MatchResult:
                self.match_calls += 1
                return MatchResult(
                    requirement="stub",
                    requirement_type="technical",
                    status="SATISFIED",
                    evidence="grounded",
                    explanation="verified",
                )
            if schema == StrategicTriageAnalysis:
                return StrategicTriageAnalysis(fatal_blockers=[], strategic_rationale="Aligned")
            if schema == ProposalReviewResult:
                self.last_review_prompt = prompt
                has_later_case = "GovDigital" in prompt and "450,000 clinical" in prompt
                return ProposalReviewResult(
                    passed=has_later_case,
                    review_score=95 if has_later_case else 40,
                    unsupported_claims=[] if has_later_case else ["Missing later chunks"],
                    recommendations=["All claims verified"] if has_later_case else ["Missing chunk >15"],
                )
            return schema()

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        emb_svc = DeterministicEvalEmbeddingService()
        retrieval = RetrievalService(embedding_service=emb_svc, min_similarity=0.30)
        stub_llm = _StubLLM()

        comp = schema.Company(name="Apex", email="bids@apex.com", profile_summary="Cloud & AI")
        db.add(comp)
        db.commit()
        db.refresh(comp)

        # Index >15 chunks from company_corpus.json so case studies sit past chunk 15
        for doc_data in load_dataset("company_corpus.json"):
            doc = schema.Document(company_id=comp.id, filename=doc_data["filename"])
            db.add(doc)
            db.commit()
            db.refresh(doc)
            for piece in chunk_text(doc_data["content"]):
                db.add(schema.DocumentChunk(
                    document_id=doc.id,
                    chunk_index=piece["chunk_index"],
                    text_content=piece["text"],
                    embedding=emb_svc.get_embedding(piece["text"]),
                ))
        db.commit()
        assert db.query(schema.DocumentChunk).count() > 15

        tender = schema.Tender(title="Cloud AI Platform", organization="Gov", status="DISCOVERED")
        db.add(tender)
        db.commit()
        db.refresh(tender)

        req_hit = schema.Requirement(tender_id=tender.id, req_type="technical", description="Python FastAPI and pgvector microservices")
        req_miss = schema.Requirement(tender_id=tender.id, req_type="technical", description="Commercial subsea hyperbaric marine welding fleet")
        db.add_all([req_hit, req_miss])
        db.commit()

        matching = MatchingAgent(retrieval_service=retrieval, llm_provider=stub_llm)
        triage = TriageAgent(matching_agent=matching, llm_provider=stub_llm, auto_draft=False)

        res1 = triage.evaluate_tender(tender.id, db, force_refresh=False)
        assert res1.fit_score == 50.0
        assert res1.decision == "REVIEW"
        assert stub_llm.match_calls == 1  # Negative query rejected cleanly before LLM!

        # force_refresh=True must re-evaluate cached requirements
        triage.evaluate_tender(tender.id, db, force_refresh=True)
        assert stub_llm.match_calls == 2

        # Verify ReviewAgent retrieves chunks past row 15 (GovDigital + NHDA clinical platform)
        clean_case = load_dataset("hallucination_cases.json")[0]
        proposal = schema.Proposal(tender_id=tender.id, full_content=clean_case["proposal_markdown"], status="DRAFT")
        db.add(proposal)
        db.commit()
        db.refresh(proposal)

        reviewer = ReviewAgent(retrieval_service=retrieval, llm_provider=stub_llm)
        audit = reviewer.review_proposal(proposal.id, db)
        assert audit.passed is True
        assert audit.review_score == 95
        assert "GovDigital" in stub_llm.last_review_prompt
        assert "450,000 clinical" in stub_llm.last_review_prompt
    finally:
        db.close()

