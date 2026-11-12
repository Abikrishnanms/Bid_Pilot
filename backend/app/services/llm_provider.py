from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import logging
import math
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class LLMCallRecord:
    timestamp: str
    schema_name: str
    provider: str
    model_used: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    fallback_triggered: bool = False
    schema_valid: bool = True
    error: Optional[str] = None


class LLMTelemetryTracker:
    """Thread-safe collector for LLM latency, token usage, schema compliance, and fallbacks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._records: List[LLMCallRecord] = []

    def record(self, entry: LLMCallRecord) -> None:
        with self._lock:
            self._records.append(entry)

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    def records(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self._records]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            items = list(self._records)

        if not items:
            return {
                "total_calls": 0,
                "schema_compliance_rate": 0.0,
                "fallback_rate": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "mean_latency_ms": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
            }

        latencies = sorted(r.latency_ms for r in items)
        n = len(items)
        p50 = latencies[int(0.50 * (n - 1))]
        p95 = latencies[min(n - 1, math.ceil(0.95 * (n - 1)))]
        valid_no_fallback = sum(1 for r in items if r.schema_valid and not r.fallback_triggered)
        fallbacks = sum(1 for r in items if r.fallback_triggered)

        return {
            "total_calls": n,
            "schema_compliance_rate": round(valid_no_fallback / n, 4),
            "fallback_rate": round(fallbacks / n, 4),
            "p50_latency_ms": round(p50, 2),
            "p95_latency_ms": round(p95, 2),
            "mean_latency_ms": round(sum(latencies) / n, 2),
            "total_prompt_tokens": sum(r.prompt_tokens for r in items),
            "total_completion_tokens": sum(r.completion_tokens for r in items),
            "total_tokens": sum(r.total_tokens for r in items),
        }


_TELEMETRY = LLMTelemetryTracker()


def get_llm_telemetry() -> LLMTelemetryTracker:
    return _TELEMETRY


def _extract_token_counts(response: Any) -> tuple[int, int, int]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return 0, 0, 0
    if isinstance(usage, dict):
        p = int(usage.get("prompt_token_count", 0) or 0)
        c = int(usage.get("candidates_token_count", 0) or 0)
        t = int(usage.get("total_token_count", p + c) or (p + c))
        return p, c, t
    p = int(getattr(usage, "prompt_token_count", 0) or 0)
    c = int(getattr(usage, "candidates_token_count", 0) or 0)
    t = int(getattr(usage, "total_token_count", p + c) or (p + c))
    return p, c, t


def _strip_json_fences(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

class LLMProvider(ABC):
    @abstractmethod
    def extract_structured_data(self, text: str, schema: Type[BaseModel], prompt: str) -> BaseModel:
        pass

class MockLLMProvider(LLMProvider):
    def extract_structured_data(
        self,
        text: str,
        schema: Type[BaseModel],
        prompt: str,
        record_telemetry: bool = True,
    ) -> BaseModel:
        start_time = time.perf_counter()
        result = self._build_mock_response(schema)
        if record_telemetry:
            _TELEMETRY.record(
                LLMCallRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    schema_name=schema.__name__,
                    provider="mock",
                    model_used="mock-llm",
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                    fallback_triggered=False,
                    schema_valid=True,
                )
            )
        return result

    @staticmethod
    def _build_mock_response(schema: Type[BaseModel]) -> BaseModel:
        from ..schemas.tender import ExtractedRequirements, MatchResult, ProposalDraft, ProposalReviewResult
        
        if schema == ExtractedRequirements:
            return schema(
                title="Enterprise Cloud Infrastructure Modernization & AI Analytics Platform",
                organization="GovTech Agency (Public Sector)",
                deadline="2026-11-30",
                estimated_value="$5,000,000 USD",
                location="Washington D.C. / Remote Support",
                eligibility_requirements=[
                    "Vendor must have at least 10+ years of documented experience in enterprise cloud infrastructure.",
                    "Vendor must maintain an active team of at least 25 full-time engineers."
                ],
                technical_requirements=[
                    "Modern microservices backend engineered using Python (FastAPI).",
                    "Database storage with pgvector vector similarity search.",
                    "Support for Retrieval-Augmented Generation (RAG) across large document corpuses."
                ],
                experience_requirements=[
                    "Proven track record delivering major enterprise cloud transformations."
                ],
                certifications_required=[
                    "ISO 9001 Quality Management System Certification",
                    "ISO 27001 Information Security Management Certification"
                ],
                deliverables=[
                    "Cloud Architecture Blueprint & Migration Strategy",
                    "Production containerized microservices codebase with 24/7 SLA"
                ],
                evaluation_criteria=[
                    "Technical Competence (60%)",
                    "Past Performance & Evidence (25%)",
                    "Cost Proposal (15%)"
                ]
            )
        elif schema == MatchResult:
            return schema(
                requirement="Sample Requirement",
                requirement_type="technical",
                status="SATISFIED",
                evidence="Company profile explicitly substantiates this requirement with verified documentation.",
                explanation="Demonstrated compliance based on retrieved past projects and certifications."
            )
        elif schema == ProposalDraft:
            return schema(
                executive_summary="Mock IT Solutions is pleased to submit this comprehensive proposal for the Enterprise Cloud Infrastructure Modernization project. With over a decade of specialized experience in cloud engineering and enterprise AI systems, we offer an battle-tested, evidence-grounded approach designed to maximize reliability and compliance.",
                technical_approach="We propose a modular, scalable microservices architecture built on Python FastAPI and PostgreSQL with pgvector for high-performance vector retrieval. Automated CI/CD pipelines and Docker containerization ensure zero-downtime deployment.",
                compliance_matrix_summary="All technical requirements and ISO 9001 quality criteria are fully met with verified corporate credentials. Mitigation strategies are established for in-progress ISO 27001 audit completion.",
                commercial_terms="Fixed-price milestone engagement totaling $4,750,000 USD with comprehensive 12-month post-deployment warranty and 24/7 Tier-3 engineering support.",
                full_markdown="# Technical & Commercial Bid Proposal\n\n## 1. Executive Summary\nMock IT Solutions is honored to submit this formal proposal. We align directly with the issuing authority's modernization mandates.\n\n## 2. Technical Solution\n- **Microservices Engine:** FastAPI async services with containerized orchestration.\n- **Vector Database:** PostgreSQL 16 with pgvector extension.\n- **Security & Reliability:** ISO 9001 certified delivery workflows with SOC 2 compliance.\n\n## 3. Compliance & Traceability Matrix\n| Requirement | Status | Evidence Citation |\n|---|---|---|\n| 10+ Years Cloud Experience | SATISFIED | Corp Profile Section 1 |\n| 25+ Full-time Engineers | SATISFIED | Corp Profile Section 1 (52 Engineers) |\n| ISO 9001 Certified | SATISFIED | Cert #QMS-99482-US |\n| ISO 27001 Certified | PARTIALLY SATISFIED | Stage 2 audit in progress |\n\n## 4. Past Performance\n- State Health Authority Vector Search Platform ($1.2M value, 2024)\n- Enterprise Logistics Cloud Migration (2023)"
            )
        elif schema == ProposalReviewResult:
            return schema(
                passed=True,
                review_score=94,
                unsupported_claims=[],
                recommendations=["Ensure explicit mitigation notes are provided for ISO 27001 audit completion."]
            )
        elif schema.__name__ == "StrategicTriageAnalysis":
            return schema(
                fatal_blockers=[],
                strategic_rationale="Vendor capabilities demonstrate strong alignment with critical tender criteria. Any non-critical gaps can be managed via teaming or milestone onboarding."
            )
        
        # Generic fallback
        return schema(**{})

def _parse_rate_limit_delay(err_msg: str) -> Optional[float]:
    """Return bounded retry delay (seconds) only for HTTP 429 rate-limit errors."""
    lowered = (err_msg or "").lower()
    if "429" not in lowered and "rate-limit" not in lowered and "quota exceeded" not in lowered:
        return None
    m = re.search(r"retry\s+in\s+(\d+(?:\.\d+)?)s", lowered)
    if m:
        return min(65.0, max(5.0, float(m.group(1)) + 2.0))
    m_sec = re.search(r"seconds:\s*(\d+)", lowered)
    if m_sec:
        return min(65.0, max(5.0, float(m_sec.group(1)) + 2.0))
    return 45.0


class GeminiProvider(LLMProvider):
    def __init__(self, strict_mode: Optional[bool] = None):
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")
        genai.configure(api_key=api_key)
        
        self.strict_mode = (
            strict_mode
            if strict_mode is not None
            else os.getenv("LLM_STRICT_MODE", "false").lower() in {"1", "true", "yes"}
        )
        # Primary: gemini-3.8-flash (with GEMINI_MODEL env override), Fallback: gemini-3.5-flash-lite
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.timeout_seconds = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
        self.retry_on_429 = os.getenv("LLM_RETRY_ON_429", "true").lower() in {"1", "true", "yes"}
        self.model = genai.GenerativeModel(model_name)

    def extract_structured_data(self, text: str, schema: Type[BaseModel], prompt: str) -> BaseModel:
        import google.generativeai as genai
        
        system_instruction = (
            f"{prompt}\n\n"
            f"You MUST return ONLY valid JSON matching this exact JSON schema:\n"
            f"{json.dumps(schema.model_json_schema())}\n"
            f"Do not include any Markdown backticks (like ```json), no explanations, only raw JSON."
        )
        
        contents = [system_instruction]
        if text:
            contents.append(f"Input Document Text:\n{text}")

        primary_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        models_to_try = list(dict.fromkeys([primary_model, "gemini-3.5-flash-lite"]))
        
        last_exception = None
        max_rounds = 2 if self.retry_on_429 else 1

        for round_idx in range(max_rounds):
            saw_rate_limit_delay: Optional[float] = None
            for idx, model_name in enumerate(models_to_try):
                call_start = time.perf_counter()
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        contents,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        ),
                        request_options={"timeout": self.timeout_seconds}
                    )
                    raw_text = _strip_json_fences(response.text)
                    data = json.loads(raw_text)
                    validated = schema(**data)

                    prompt_toks, comp_toks, total_toks = _extract_token_counts(response)
                    _TELEMETRY.record(
                        LLMCallRecord(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            schema_name=schema.__name__,
                            provider="gemini",
                            model_used=model_name,
                            latency_ms=round((time.perf_counter() - call_start) * 1000, 2),
                            prompt_tokens=prompt_toks,
                            completion_tokens=comp_toks,
                            total_tokens=total_toks,
                            fallback_triggered=(idx > 0),
                            schema_valid=True,
                        )
                    )
                    return validated
                except Exception as e:
                    last_exception = e
                    delay = _parse_rate_limit_delay(str(e))
                    if delay is not None:
                        saw_rate_limit_delay = delay
                    _TELEMETRY.record(
                        LLMCallRecord(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            schema_name=schema.__name__,
                            provider="gemini",
                            model_used=model_name,
                            latency_ms=round((time.perf_counter() - call_start) * 1000, 2),
                            fallback_triggered=(idx > 0),
                            schema_valid=False,
                            error=str(e)[:200],
                        )
                    )
                    logger.warning(f"Model {model_name} failed or quota reached ({str(e)[:120]}). Trying fallback...")

            if round_idx == 0 and saw_rate_limit_delay is not None and self.retry_on_429:
                logger.info(f"Rate limit (429) hit across Gemini models; sleeping {saw_rate_limit_delay:.1f}s before retry...")
                time.sleep(saw_rate_limit_delay)
            else:
                break

        if self.strict_mode:
            raise RuntimeError(f"All Gemini models failed in strict_mode: {last_exception}")

        logger.warning(f"All Gemini models exhausted ({last_exception}). Falling back to MockLLMProvider for offline reliability.")
        _TELEMETRY.record(
            LLMCallRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                schema_name=schema.__name__,
                provider="mock_fallback",
                model_used="mock-llm",
                latency_ms=0.0,
                fallback_triggered=True,
                schema_valid=True,
                error=str(last_exception)[:200] if last_exception else None,
            )
        )
        return MockLLMProvider().extract_structured_data(text, schema, prompt, record_telemetry=False)

def get_llm_provider(strict_mode: Optional[bool] = None) -> LLMProvider:
    is_strict = (
        strict_mode
        if strict_mode is not None
        else os.getenv("LLM_STRICT_MODE", "false").lower() in {"1", "true", "yes"}
    )
    provider_name = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider_name == "gemini":
        try:
            return GeminiProvider(strict_mode=is_strict)
        except Exception as e:
            if is_strict:
                raise
            logger.error(f"Failed to initialize GeminiProvider: {e}. Falling back to MockLLMProvider.")
            return MockLLMProvider()
    return MockLLMProvider()
