"""Tier-1 RAG Evaluation Suite (chunking integrity, Hybrid RRF retrieval, negative rejection)."""
from app.services.chunking import _split_sentences, chunk_text, chunk_text_fixed
from app.services.retrieval_service import RetrievalService, RetrievedChunk, rank_and_filter_candidates
from evals.fixtures import load_dataset
from evals.metrics import boundary_integrity_rate
from evals.runners import run_rag_benchmark


def test_sentence_chunking_preserves_boundaries():
    docs = load_dataset("company_corpus.json")
    sentences_gt = [s for d in docs for s in _split_sentences(d["content"]) if len(s) <= 550]

    upgraded_chunks = [c["text"] for d in docs for c in chunk_text(d["content"], max_chars=550, overlap_sentences=1)]
    baseline_chunks = [c["text"] for d in docs for c in chunk_text_fixed(d["content"], chunk_size=500, overlap=50)]

    upgraded_rate = boundary_integrity_rate(upgraded_chunks, sentences_gt)
    baseline_rate = boundary_integrity_rate(baseline_chunks, sentences_gt)

    assert upgraded_rate == 1.0
    assert upgraded_rate > baseline_rate


def test_rag_hybrid_benchmark_meets_targets():
    report = run_rag_benchmark(prefer_real_embeddings=True, min_similarity=0.39)
    baseline = report["baseline"]
    upgraded = report["upgraded"]

    # Ensure corpus exceeds legacy .limit(15) ReviewAgent window
    assert upgraded["total_chunks"] > 15

    # Baseline had no threshold cutoff, so out-of-domain rejection is 0%
    assert baseline["negative_rejection_rate"] == 0.0

    # Upgraded Hybrid RRF + threshold targets
    assert upgraded["sentence_boundary_integrity"] == 1.0
    assert upgraded["recall_at_3"] >= 0.85, f"Low recall_at_3: {upgraded['details']}"
    assert upgraded["mrr"] >= 0.80, f"Low MRR: {upgraded['details']}"
    assert upgraded["negative_rejection_rate"] >= 0.80, f"Low neg rejection: {upgraded['details']}"


def test_rrf_resolves_confusable_certification_over_dense_only():
    query = "Active ISO 27001:2022 Information Security certification #IS-882910"
    candidates = {
        1: RetrievedChunk(
            chunk_id=1,
            document_id=1,
            filename="02_Security_Certifications.txt",
            chunk_index=0,
            text_content="Holds ISO 9001:2015 Quality Management certification (#QMS-77410).",
            dense_similarity=0.72,
            sparse_score=0.25,
        ),
        2: RetrievedChunk(
            chunk_id=2,
            document_id=1,
            filename="02_Security_Certifications.txt",
            chunk_index=1,
            text_content="Active ISO 27001:2022 Information Security Management certification (#IS-882910).",
            dense_similarity=0.70,
            sparse_score=0.95,
        ),
    }

    dense_only = rank_and_filter_candidates(
        query=query,
        candidates={k: RetrievedChunk(**vars(v)) for k, v in candidates.items()},
        dense_ranked_ids=[1, 2],
        sparse_ranked_ids=[2, 1],
        top_k=2,
        min_similarity=0.30,
        strategy="dense_only",
    )
    hybrid = rank_and_filter_candidates(
        query=query,
        candidates={k: RetrievedChunk(**vars(v)) for k, v in candidates.items()},
        dense_ranked_ids=[1, 2],
        sparse_ranked_ids=[2, 1],
        top_k=2,
        min_similarity=0.30,
        strategy="hybrid",
    )

    assert dense_only[0].chunk_id == 1
    assert hybrid[0].chunk_id == 2


def test_reranker_hook_and_source_formatting():
    candidates = {
        10: RetrievedChunk(10, 1, "docA.txt", 0, "Generic cloud overview.", dense_similarity=0.60, sparse_score=0.2),
        20: RetrievedChunk(20, 2, "docB.txt", 0, "Exact FastAPI and pgvector details.", dense_similarity=0.55, sparse_score=0.7),
    }
    reranked = rank_and_filter_candidates(
        query="FastAPI pgvector",
        candidates=candidates,
        dense_ranked_ids=[10, 20],
        sparse_ranked_ids=[20, 10],
        top_k=2,
        min_similarity=0.30,
        strategy="hybrid",
        reranker=lambda q, texts: [0.15 if "Generic" in t else 0.92 for t in texts],
    )
    assert reranked[0].chunk_id == 20
    assert reranked[0].rerank_score == 0.92

    formatted = RetrievalService.format_evidence(reranked)
    assert "[Source: docB.txt | Sim: 0.55]" in formatted

