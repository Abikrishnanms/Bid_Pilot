"""Tier-2 GenAI Evaluation Suite (LLM telemetry, strict failover guard, extraction & faithfulness)."""
import os
import sys
import types
import pytest

from app.schemas.tender import MatchResult
from app.services.llm_provider import GeminiProvider, MockLLMProvider, get_llm_telemetry
from evals.runners import run_genai_benchmark


def test_llm_telemetry_tracks_calls_and_summary():
    telemetry = get_llm_telemetry()
    telemetry.reset()

    provider = MockLLMProvider()
    provider.extract_structured_data("sample", MatchResult, "evaluate")
    summary = telemetry.summary()

    assert summary["total_calls"] == 1
    assert summary["schema_compliance_rate"] == 1.0
    assert summary["fallback_rate"] == 0.0
    assert summary["p95_latency_ms"] >= 0.0


def test_gemini_strict_mode_prevents_silent_mock_fallback(monkeypatch):
    class _BrokenModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, *args, **kwargs):
            raise RuntimeError("Simulated API quota failure")

    fake_genai = types.SimpleNamespace(
        configure=lambda api_key=None: None,
        GenerativeModel=_BrokenModel,
        GenerationConfig=lambda **kwargs: kwargs,
    )
    monkeypatch.setitem(sys.modules, "google.generativeai", fake_genai)
    monkeypatch.setenv("GEMINI_API_KEY", "test-dummy-key")

    telemetry = get_llm_telemetry()
    telemetry.reset()

    strict_provider = GeminiProvider(strict_mode=True)
    with pytest.raises(RuntimeError, match="All Gemini models failed in strict_mode"):
        strict_provider.extract_structured_data("sample", MatchResult, "test prompt")

    # Non-strict mode falls back to mock AND explicitly flags fallback_triggered=True
    telemetry.reset()
    resilient_provider = GeminiProvider(strict_mode=False)
    res = resilient_provider.extract_structured_data("sample", MatchResult, "test prompt")
    assert res.status == "SATISFIED"
    summary = telemetry.summary()
    assert summary["fallback_rate"] > 0.0


def test_gemini_retries_once_on_429_rate_limit(monkeypatch):
    calls = {"count": 0}

    class _RateLimitThenSuccessModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] <= 2:
                raise RuntimeError("429 Quota exceeded for metric. Please retry in 5s.")
            return types.SimpleNamespace(
                text='{"requirement": "test", "requirement_type": "technical", "status": "SATISFIED", "evidence": "ok", "explanation": "ok"}',
                usage_metadata={"prompt_token_count": 10, "candidates_token_count": 5, "total_token_count": 15},
            )

    fake_genai = types.SimpleNamespace(
        configure=lambda api_key=None: None,
        GenerativeModel=_RateLimitThenSuccessModel,
        GenerationConfig=lambda **kwargs: kwargs,
    )
    monkeypatch.setitem(sys.modules, "google.generativeai", fake_genai)
    monkeypatch.setenv("GEMINI_API_KEY", "test-dummy-key")
    monkeypatch.setattr("app.services.llm_provider.time.sleep", lambda s: None)

    provider = GeminiProvider(strict_mode=True)
    res = provider.extract_structured_data("sample", MatchResult, "test prompt")
    assert res.status == "SATISFIED"
    assert calls["count"] == 3


def test_genai_benchmark_metrics():
    run_live = os.getenv("RUN_LIVE_EVALS", "0") == "1"
    report = run_genai_benchmark(live=run_live)

    assert report["telemetry"]["total_calls"] > 0
    assert report["telemetry"]["schema_compliance_rate"] == 1.0
    if run_live:
        assert report["execution_mode"] == "live_gemini_strict"
        assert report["mean_extraction_f1"] >= 0.70
        assert report["mean_faithfulness"] >= 0.80
