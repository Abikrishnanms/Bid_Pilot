from dataclasses import dataclass
import logging
import math
import os
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "must", "of", "on", "or", "shall", "should", "that", "the",
    "their", "this", "to", "vendor", "with", "within", "will", "using", "across"
})
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*")
_RERANKER_CACHE: Dict[str, object] = {}


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    filename: str
    chunk_index: Optional[int]
    text_content: str
    dense_similarity: float
    sparse_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: Optional[float] = None


def tokenize_keywords(value: str) -> List[str]:
    """Extract normalized alphanumeric domain tokens (retaining cert IDs and numbers)."""
    if not value:
        return []
    tokens: List[str] = []
    for raw in _TOKEN_RE.findall(value.lower()):
        # Emit both compound token (e.g. iso-27001) and split parts for robust matching
        if raw not in _STOPWORDS and len(raw) > 1:
            tokens.append(raw)
        for sub in re.split(r"[._-]+", raw):
            if sub and sub not in _STOPWORDS and (len(sub) > 1 or sub.isdigit()):
                if sub != raw:
                    tokens.append(sub)
    return tokens


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute bounded cosine similarity in [-1.0, 1.0]."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def lexical_overlap_score(query: str, text_content: str) -> float:
    """Compute fraction of unique non-stopword query tokens present in chunk text."""
    q_tokens = set(tokenize_keywords(query))
    if not q_tokens:
        return 0.0
    doc_tokens = set(tokenize_keywords(text_content))
    if not doc_tokens:
        return 0.0
    return len(q_tokens & doc_tokens) / len(q_tokens)


def reciprocal_rank_fusion(
    dense_ranked_ids: Sequence[int],
    sparse_ranked_ids: Sequence[int],
    rrf_k: int = 60,
    dense_weight: float = 1.0,
    sparse_weight: float = 1.0,
) -> Dict[int, float]:
    """Combine dense and sparse ranked chunk IDs via Reciprocal Rank Fusion."""
    scores: Dict[int, float] = {}
    for rank, cid in enumerate(dense_ranked_ids, start=1):
        scores[cid] = scores.get(cid, 0.0) + dense_weight / (rrf_k + rank)
    for rank, cid in enumerate(sparse_ranked_ids, start=1):
        scores[cid] = scores.get(cid, 0.0) + sparse_weight / (rrf_k + rank)
    return scores


def passes_relevance_threshold(
    dense_similarity: float,
    lexical_coverage: float,
    min_similarity: float,
) -> bool:
    """Gate low-similarity noise while allowing high exact-keyword matches just below cutoff."""
    if min_similarity <= 0.0:
        return True
    if dense_similarity >= min_similarity:
        return True
    return lexical_coverage >= 0.50 and dense_similarity >= max(0.22, min_similarity - 0.10)


def rank_and_filter_candidates(
    query: str,
    candidates: Dict[int, RetrievedChunk],
    dense_ranked_ids: Sequence[int],
    sparse_ranked_ids: Sequence[int],
    top_k: int = 3,
    min_similarity: float = 0.30,
    strategy: str = "hybrid",
    reranker: Optional[Callable[[str, List[str]], Sequence[float]]] = None,
) -> List[RetrievedChunk]:
    """Score, fuse, threshold-filter, and optionally rerank retrieved candidates."""
    if not candidates:
        return []

    if strategy == "dense_only":
        ordered_ids = list(dense_ranked_ids)
        for cid in ordered_ids:
            candidates[cid].rrf_score = candidates[cid].dense_similarity
    else:
        rrf_scores = reciprocal_rank_fusion(dense_ranked_ids, sparse_ranked_ids)
        for cid, score in rrf_scores.items():
            if cid in candidates:
                candidates[cid].rrf_score = score
        ordered_ids = sorted(
            [cid for cid in rrf_scores if cid in candidates],
            key=lambda cid: (
                candidates[cid].rrf_score,
                candidates[cid].sparse_score,
                candidates[cid].dense_similarity,
            ),
            reverse=True,
        )

    filtered: List[RetrievedChunk] = []
    for cid in ordered_ids:
        item = candidates[cid]
        lex_cov = lexical_overlap_score(query, item.text_content)
        if item.sparse_score <= 0.0:
            item.sparse_score = lex_cov
        if passes_relevance_threshold(item.dense_similarity, lex_cov, min_similarity):
            filtered.append(item)

    if reranker and len(filtered) > 1:
        rerank_pool = filtered[:max(top_k * 3, 8)]
        scores = reranker(query, [c.text_content for c in rerank_pool])
        for chunk, r_score in zip(rerank_pool, scores):
            chunk.rerank_score = float(r_score)
        rerank_pool.sort(key=lambda c: c.rerank_score if c.rerank_score is not None else -1e9, reverse=True)
        return rerank_pool[:top_k]

    return filtered[:top_k]


def _get_default_reranker() -> Optional[Callable[[str, List[str]], Sequence[float]]]:
    """Load optional CrossEncoder reranker only when RAG_ENABLE_RERANK is truthy."""
    enabled = os.getenv("RAG_ENABLE_RERANK", "false").lower() in {"1", "true", "yes"}
    if not enabled:
        return None
    model_name = os.getenv("RAG_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    try:
        from sentence_transformers import CrossEncoder
        if model_name not in _RERANKER_CACHE:
            logger.info(f"Loading CrossEncoder reranker: {model_name}")
            _RERANKER_CACHE[model_name] = CrossEncoder(model_name)
        model = _RERANKER_CACHE[model_name]
        return lambda q, texts: model.predict([(q, t) for t in texts])
    except Exception as exc:
        logger.warning(f"Failed to load CrossEncoder reranker ({exc}); continuing without rerank.")
        return None


class RetrievalService:
    """Unified Hybrid RAG retrieval service backed by pgvector and PostgreSQL FTS."""

    def __init__(
        self,
        embedding_service=None,
        reranker: Optional[Callable[[str, List[str]], Sequence[float]]] = None,
        min_similarity: Optional[float] = None,
    ):
        self._embedding_service = embedding_service
        self._reranker = reranker
        self.default_min_similarity = (
            min_similarity
            if min_similarity is not None
            else float(os.getenv("RAG_MIN_SIMILARITY", "0.39"))
        )

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from .embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _active_reranker(self) -> Optional[Callable[[str, List[str]], Sequence[float]]]:
        return self._reranker if self._reranker is not None else _get_default_reranker()

    def retrieve(
        self,
        query: str,
        db: Session,
        top_k: int = 3,
        min_similarity: Optional[float] = None,
        candidate_k: int = 12,
        strategy: str = "hybrid",
    ) -> List[RetrievedChunk]:
        """Retrieve relevant company chunks using Hybrid pgvector + FTS + threshold filtering."""
        if not query or not query.strip():
            return []

        cutoff = self.default_min_similarity if min_similarity is None else min_similarity
        q_vec = self.embedding_service.get_embedding(query)
        dialect_name = db.bind.dialect.name if db.bind is not None else ""

        if dialect_name == "postgresql":
            return self._retrieve_postgres(
                query=query,
                q_vec=q_vec,
                db=db,
                top_k=top_k,
                min_similarity=cutoff,
                candidate_k=candidate_k,
                strategy=strategy,
            )

        return self._retrieve_python_fallback(
            query=query,
            q_vec=q_vec,
            db=db,
            top_k=top_k,
            min_similarity=cutoff,
            strategy=strategy,
        )

    def _retrieve_postgres(
        self,
        query: str,
        q_vec: List[float],
        db: Session,
        top_k: int,
        min_similarity: float,
        candidate_k: int,
        strategy: str,
    ) -> List[RetrievedChunk]:
        from ..models import schema

        # 1. Dense pgvector search
        distance_expr = schema.DocumentChunk.embedding.cosine_distance(q_vec)
        dense_rows = (
            db.query(schema.DocumentChunk, schema.Document.filename, distance_expr.label("distance"))
            .join(schema.Document, schema.Document.id == schema.DocumentChunk.document_id)
            .order_by(distance_expr)
            .limit(candidate_k)
            .all()
        )

        candidates: Dict[int, RetrievedChunk] = {}
        dense_ranked_ids: List[int] = []
        for chunk, filename, dist in dense_rows:
            dense_sim = max(-1.0, min(1.0, 1.0 - float(dist if dist is not None else 1.0)))
            dense_ranked_ids.append(chunk.id)
            candidates[chunk.id] = RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename or "Company Document",
                chunk_index=chunk.chunk_index,
                text_content=chunk.text_content,
                dense_similarity=dense_sim,
            )

        sparse_ranked_ids: List[int] = []
        if strategy != "dense_only":
            # 2. Sparse PostgreSQL Full-Text Search (uses websearch_to_tsquery OR fallback keyword match)
            sparse_hits = self._query_postgres_fts(query=query, db=db, candidate_k=candidate_k)
            for row in sparse_hits:
                cid = int(row["id"])
                sparse_ranked_ids.append(cid)
                if cid in candidates:
                    candidates[cid].sparse_score = float(row["sparse_rank"])
                else:
                    # Compute exact cosine distance for sparse-only hits via pgvector
                    dist_val = db.execute(
                        text("SELECT (embedding <=> CAST(:q_vec AS vector)) AS d FROM document_chunks WHERE id = :cid"),
                        {"q_vec": str(q_vec), "cid": cid},
                    ).scalar()
                    dense_sim = max(-1.0, min(1.0, 1.0 - float(dist_val if dist_val is not None else 1.0)))
                    candidates[cid] = RetrievedChunk(
                        chunk_id=cid,
                        document_id=int(row["document_id"]),
                        filename=row["filename"] or "Company Document",
                        chunk_index=row["chunk_index"],
                        text_content=row["text_content"],
                        dense_similarity=dense_sim,
                        sparse_score=float(row["sparse_rank"]),
                    )

            # Supplement sparse ranking with deterministic keyword overlap on loaded candidates
            if not sparse_ranked_ids and candidates:
                lex_scored = [
                    (cid, lexical_overlap_score(query, item.text_content))
                    for cid, item in candidates.items()
                ]
                lex_scored = [(cid, sc) for cid, sc in lex_scored if sc > 0.0]
                lex_scored.sort(key=lambda pair: pair[1], reverse=True)
                for cid, sc in lex_scored:
                    sparse_ranked_ids.append(cid)
                    candidates[cid].sparse_score = sc

        return rank_and_filter_candidates(
            query=query,
            candidates=candidates,
            dense_ranked_ids=dense_ranked_ids,
            sparse_ranked_ids=sparse_ranked_ids,
            top_k=top_k,
            min_similarity=min_similarity,
            strategy=strategy,
            reranker=self._active_reranker(),
        )

    @staticmethod
    def _query_postgres_fts(query: str, db: Session, candidate_k: int) -> List[Dict[str, object]]:
        """Query PostgreSQL full-text search safely using OR-joined sanitized keywords for recall."""
        keywords = list(dict.fromkeys(tokenize_keywords(query)))[:12]
        if not keywords:
            return []
        or_query = " OR ".join(keywords)
        sql = text(
            """
            SELECT dc.id, dc.document_id, d.filename, dc.chunk_index, dc.text_content,
                   ts_rank_cd(to_tsvector('english', dc.text_content), websearch_to_tsquery('english', :q)) AS sparse_rank
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE to_tsvector('english', dc.text_content) @@ websearch_to_tsquery('english', :q)
            ORDER BY sparse_rank DESC
            LIMIT :limit
            """
        )
        try:
            rows = db.execute(sql, {"q": or_query, "limit": candidate_k}).mappings().all()
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.debug(f"PostgreSQL FTS query skipped ({exc})")
            return []

    def _retrieve_python_fallback(
        self,
        query: str,
        q_vec: List[float],
        db: Session,
        top_k: int,
        min_similarity: float,
        strategy: str,
    ) -> List[RetrievedChunk]:
        """Dialect-agnostic retrieval for non-PostgreSQL unit test sessions."""
        from ..models import schema

        rows = (
            db.query(schema.DocumentChunk, schema.Document.filename)
            .join(schema.Document, schema.Document.id == schema.DocumentChunk.document_id)
            .all()
        )
        candidates: Dict[int, RetrievedChunk] = {}
        for chunk, filename in rows:
            emb = list(chunk.embedding) if chunk.embedding is not None else []
            dense_sim = cosine_similarity(q_vec, emb)
            lex = lexical_overlap_score(query, chunk.text_content)
            candidates[chunk.id] = RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename or "Company Document",
                chunk_index=chunk.chunk_index,
                text_content=chunk.text_content,
                dense_similarity=dense_sim,
                sparse_score=lex,
            )

        dense_ranked = [
            cid for cid, _ in sorted(
                candidates.items(), key=lambda kv: kv[1].dense_similarity, reverse=True
            )
        ]
        sparse_ranked = [
            cid for cid, _ in sorted(
                ((cid, c) for cid, c in candidates.items() if c.sparse_score > 0.0),
                key=lambda kv: kv[1].sparse_score,
                reverse=True,
            )
        ]
        return rank_and_filter_candidates(
            query=query,
            candidates=candidates,
            dense_ranked_ids=dense_ranked,
            sparse_ranked_ids=sparse_ranked,
            top_k=top_k,
            min_similarity=min_similarity,
            strategy=strategy,
            reranker=self._active_reranker(),
        )

    def retrieve_for_claims(
        self,
        claims: Sequence[str],
        db: Session,
        top_k_per_claim: int = 3,
        max_total_chunks: int = 18,
        min_similarity: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """Run targeted Hybrid RAG per proposal claim and deduplicate across the full KB."""
        merged: Dict[int, RetrievedChunk] = {}
        for claim in claims:
            if not claim or len(claim.strip()) < 15:
                continue
            hits = self.retrieve(
                query=claim,
                db=db,
                top_k=top_k_per_claim,
                min_similarity=min_similarity,
            )
            for hit in hits:
                existing = merged.get(hit.chunk_id)
                if existing is None or hit.dense_similarity > existing.dense_similarity:
                    merged[hit.chunk_id] = hit

        ordered = sorted(merged.values(), key=lambda c: (c.dense_similarity, c.sparse_score), reverse=True)
        return ordered[:max_total_chunks]

    @staticmethod
    def format_evidence(chunks: Sequence[RetrievedChunk], max_chars: int = 2500) -> str:
        """Format retrieved chunks with explicit source filename and similarity metadata."""
        if not chunks:
            return ""
        parts: List[str] = []
        total_len = 0
        for chunk in chunks:
            entry = f"[Source: {chunk.filename} | Sim: {chunk.dense_similarity:.2f}] {chunk.text_content}"
            if total_len + len(entry) > max_chars and parts:
                break
            parts.append(entry)
            total_len += len(entry) + 2
        return "\n\n".join(parts)
