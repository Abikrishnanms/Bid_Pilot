# BidPilot AI, RAG & Agentic Evaluation Scorecard

- **Generated At (UTC):** `2026-11-12T07:07:16.739940+00:00`
- **RAG Embedding Backend:** `sentence-transformers/all-MiniLM-L6-v2` (threshold: `0.39`)
- **GenAI Execution Mode:** `live_gemini_strict`
- **Agentic Execution Mode:** `live_gemini_strict` (corpus chunks: `16`)

---

## 1. Tier-1: RAG Retrieval Evaluation (Baseline vs. Upgraded)

| Metric | Baseline (Fixed 500c + Dense-Only) | Upgraded (Sentence-Aware + Hybrid RRF + Cutoff) | Delta |
| :--- | :---: | :---: | :---: |
| Sentence Boundary Integrity | 0.7647 | 1.0000 | +0.2353 |
| Recall@3 | 0.8667 | 0.8500 | -0.0167 |
| Precision@3 | 0.4333 | 0.5000 | +0.0667 |
| Recall@5 | 0.8667 | 0.8500 | -0.0167 |
| Mean Reciprocal Rank (MRR) | 0.8000 | 0.9000 | +0.1000 |
| Negative Rejection Rate | 0.0000 | 1.0000 | +1.0000 |

---

## 2. Tier-2: GenAI Extraction, Synthesis & Telemetry Evaluation

| Metric | Measured Value |
| :--- | :---: |
| Schema Compliance Rate (No Fallback) | 0.0000 |
| Fallback Trigger Rate | 0.5000 |
| Extraction Precision | 0.7000 |
| Extraction Recall | 0.7500 |
| Extraction F1 | 0.7222 |
| Proposal Requirement Coverage | 0.9000 |
| Proposal Faithfulness (Groundedness) | 1.0000 |
| Tender Domain Relevance | 0.9250 |
| Mean / P95 Latency (ms) | 2712.6 ms / 9176.2 ms |
| Total Tokens Used | 17475 |

---

## 3. Tier-3: Agentic Decision & Anti-Hallucination Guardrail Evaluation

| Metric | Measured Value |
| :--- | :---: |
| Requirement Match Accuracy | 1.0000 |
| Requirement Match Macro-F1 | 1.0000 |
| Triage Decision Accuracy (`GO`/`REVIEW`/`NO_GO`) | 0.7500 |
| False-Positive `GO` Rate | 0.0000 |
| Fit Score Mean Absolute Error (MAE) | 0.00 |
| Anti-Hallucination Detection Recall (TPR) | 1.0000 |
| Anti-Hallucination False Alarm Rate (FPR) | 0.0000 |
| Audit Score Separation (`Clean - Hallucinated`) | 91.67 pts (100.0 vs 8.33) |
