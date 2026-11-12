"""Shared golden dataset loaders and lightweight embedding/runtime helpers for BidPilot evals."""
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"

# Semantic concept clusters used only when running offline deterministic evals without SentenceTransformers
_CONCEPT_GROUPS = [
    ("iso27001", "is-882910", "information security", "isms", "security management", "audit"),
    ("iso9001", "qms-77410", "quality management"),
    ("soc 2", "cyber essentials", "fedramp moderate", "3pao", "attestation", "accreditation"),
    ("fastapi", "python", "pydantic", "microservices", "api", "sqlalchemy"),
    ("pgvector", "postgresql", "hnsw", "vector", "rag", "retrieval-augmented", "embeddings", "semantic search"),
    ("react", "vite", "tailwind", "kubernetes", "eks", "docker", "terraform", "blue/green", "ci/cd"),
    ("64 full-time", "12 years", "engineers", "workforce", "staff", "revenue", "cleared", "reston", "london"),
    ("99.95%", "99.98%", "sla", "sre", "tier-3", "uptime", "24/7", "availability"),
    ("nhda", "clinical", "healthcare", "450,000", "medical", "sub-25ms", "aes-256"),
    ("govdigital", "monolithic", "38 legacy", "cloud migration", "portals", "62%"),
    ("civil engineering", "heritage", "stonework", "masonry", "footpath", "car park", "bridge", "riba"),
    ("sap", "s/4hana", "abap", "payroll", "erp"),
    ("subsea", "marine", "hyperbaric", "welding", "maritime", "hull"),
    ("nuclear", "asme", "nqa-1", "reactor", "cooling tower", "hvac"),
]


def load_dataset(filename: str) -> Any:
    path = DATASETS_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def has_sentence_transformers() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def has_live_gemini() -> bool:
    try:
        import google.generativeai  # noqa: F401
        return bool(os.getenv("GEMINI_API_KEY")) and os.getenv("LLM_PROVIDER", "").lower() == "gemini"
    except ImportError:
        return False


class DeterministicEvalEmbeddingService:
    """
    Lightweight 384-dim hashed concept+token embedder for fast offline RAG CI tests
    when SentenceTransformers/PyTorch is unavailable on the host.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def get_embedding(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        lowered = (text or "").lower()

        # 1. Concept cluster features (dimensions 0..127)
        for idx, terms in enumerate(_CONCEPT_GROUPS):
            hits = sum(1 for term in terms if term in lowered)
            if hits > 0:
                base_idx = (idx * 7) % 128
                vec[base_idx] += 2.0 * min(hits, 3)

        # 2. Hashed token + character trigram features (dimensions 128..383)
        tokens = re.findall(r"[a-z0-9]+", lowered)
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            vec[128 + (h % (self.dim - 128))] += 1.0
            if len(tok) >= 4:
                for i in range(len(tok) - 2):
                    tri = tok[i:i + 3]
                    th = int(hashlib.md5(tri.encode("utf-8")).hexdigest(), 16)
                    vec[128 + (th % (self.dim - 128))] += 0.25

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec

    def embed_chunks(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embedding(t) for t in texts]


def get_eval_embedding_service(prefer_real: bool = True):
    """Return real all-MiniLM-L6-v2 when installed and requested, else deterministic embedder."""
    if prefer_real and has_sentence_transformers():
        from app.services.embedding_service import EmbeddingService
        return EmbeddingService(), "sentence-transformers/all-MiniLM-L6-v2"
    return DeterministicEvalEmbeddingService(), "deterministic-concept-hash-384"

