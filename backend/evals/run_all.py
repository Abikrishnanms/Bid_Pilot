"""
Unified CLI Evaluation Runner & Project Report Scorecard Generator.

Usage (from backend/):
    python -m evals.run_all                # Offline / deterministic CI check
    python -m evals.run_all --live         # Live Gemini + pgvector/SentenceTransformers eval
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from evals.runners import run_agentic_benchmark, run_genai_benchmark, run_rag_benchmark


def _format_markdown_report(payload: dict) -> str:
    rag = payload["rag"]
    base = rag["baseline"]
    upg = rag["upgraded"]
    genai = payload["genai"]
    tel = genai["telemetry"]
    agents = payload["agents"]
    triage = agents["triage"]
    review = agents["anti_hallucination_review"]

    lines = [
        "# BidPilot AI, RAG & Agentic Evaluation Scorecard",
        "",
        f"- **Generated At (UTC):** `{payload['generated_at']}`",
        f"- **RAG Embedding Backend:** `{rag['embedding_backend']}` (threshold: `{rag['min_similarity_threshold']}`)",
        f"- **GenAI Execution Mode:** `{genai['execution_mode']}`",
        f"- **Agentic Execution Mode:** `{agents['execution_mode']}` (corpus chunks: `{agents['corpus_chunk_count']}`)",
        "",
        "---",
        "",
        "## 1. Tier-1: RAG Retrieval Evaluation (Baseline vs. Upgraded)",
        "",
        "| Metric | Baseline (Fixed 500c + Dense-Only) | Upgraded (Sentence-Aware + Hybrid RRF + Cutoff) | Delta |",
        "| :--- | :---: | :---: | :---: |",
        f"| Sentence Boundary Integrity | {base['sentence_boundary_integrity']:.4f} | {upg['sentence_boundary_integrity']:.4f} | {upg['sentence_boundary_integrity'] - base['sentence_boundary_integrity']:+.4f} |",
        f"| Recall@3 | {base['recall_at_3']:.4f} | {upg['recall_at_3']:.4f} | {upg['recall_at_3'] - base['recall_at_3']:+.4f} |",
        f"| Precision@3 | {base['precision_at_3']:.4f} | {upg['precision_at_3']:.4f} | {upg['precision_at_3'] - base['precision_at_3']:+.4f} |",
        f"| Recall@5 | {base['recall_at_5']:.4f} | {upg['recall_at_5']:.4f} | {upg['recall_at_5'] - base['recall_at_5']:+.4f} |",
        f"| Mean Reciprocal Rank (MRR) | {base['mrr']:.4f} | {upg['mrr']:.4f} | {upg['mrr'] - base['mrr']:+.4f} |",
        f"| Negative Rejection Rate | {base['negative_rejection_rate']:.4f} | {upg['negative_rejection_rate']:.4f} | {upg['negative_rejection_rate'] - base['negative_rejection_rate']:+.4f} |",
        "",
        "---",
        "",
        "## 2. Tier-2: GenAI Extraction, Synthesis & Telemetry Evaluation",
        "",
        "| Metric | Measured Value |",
        "| :--- | :---: |",
        f"| Schema Compliance Rate (No Fallback) | {tel['schema_compliance_rate']:.4f} |",
        f"| Fallback Trigger Rate | {tel['fallback_rate']:.4f} |",
        f"| Extraction Precision | {genai['mean_extraction_precision']:.4f} |",
        f"| Extraction Recall | {genai['mean_extraction_recall']:.4f} |",
        f"| Extraction F1 | {genai['mean_extraction_f1']:.4f} |",
        f"| Proposal Requirement Coverage | {genai['mean_requirement_coverage']:.4f} |",
        f"| Proposal Faithfulness (Groundedness) | {genai['mean_faithfulness']:.4f} |",
        f"| Tender Domain Relevance | {genai['mean_tender_relevance']:.4f} |",
        f"| Mean / P95 Latency (ms) | {tel['mean_latency_ms']} ms / {tel['p95_latency_ms']} ms |",
        f"| Total Tokens Used | {tel['total_tokens']} |",
        "",
        "---",
        "",
        "## 3. Tier-3: Agentic Decision & Anti-Hallucination Guardrail Evaluation",
        "",
        "| Metric | Measured Value |",
        "| :--- | :---: |",
        f"| Requirement Match Accuracy | {agents['matching']['accuracy']:.4f} |",
        f"| Requirement Match Macro-F1 | {agents['matching']['macro_f1']:.4f} |",
        f"| Triage Decision Accuracy (`GO`/`REVIEW`/`NO_GO`) | {triage['accuracy']:.4f} |",
        f"| False-Positive `GO` Rate | {triage['false_positive_go_rate']:.4f} |",
        f"| Fit Score Mean Absolute Error (MAE) | {triage['fit_score_mae']:.2f} |",
        f"| Anti-Hallucination Detection Recall (TPR) | {review['hallucination_tpr']:.4f} |",
        f"| Anti-Hallucination False Alarm Rate (FPR) | {review['false_alarm_fpr']:.4f} |",
        f"| Audit Score Separation (`Clean - Hallucinated`) | {review['score_separation']:.2f} pts ({review['clean_mean_score']} vs {review['hallucinated_mean_score']}) |",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run BidPilot 3-tier AI evaluation benchmarks.")
    parser.add_argument("--live", action="store_true", help="Invoke live Gemini API in strict_mode instead of offline harness.")
    parser.add_argument("--no-real-embeddings", action="store_true", help="Use deterministic hashed concept embedder even if SentenceTransformers is installed.")
    parser.add_argument("--min-similarity", type=float, default=0.39, help="RAG similarity cutoff threshold.")
    args = parser.parse_args()

    prefer_real_emb = not args.no_real_embeddings
    print("[1/3] Running Tier-1 RAG Benchmark...", flush=True)
    rag_report = run_rag_benchmark(prefer_real_embeddings=prefer_real_emb, min_similarity=args.min_similarity)
    print("[2/3] Running Tier-2 GenAI Benchmark...", flush=True)
    genai_report = run_genai_benchmark(live=args.live)
    print("[3/3] Running Tier-3 Agentic & Guardrail Benchmark...", flush=True)
    agentic_report = run_agentic_benchmark(live=args.live, prefer_real_embeddings=prefer_real_emb)

    full_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rag": rag_report,
        "genai": genai_report,
        "agents": agentic_report,
    }

    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "latest_report.json"
    md_path = reports_dir / "latest_report.md"

    json_path.write_text(json.dumps(full_payload, indent=2), encoding="utf-8")
    md_text = _format_markdown_report(full_payload)
    md_path.write_text(md_text, encoding="utf-8")

    print(md_text)
    print(f"Saved JSON report: {json_path}")
    print(f"Saved Markdown report: {md_path}")


if __name__ == "__main__":
    main()

