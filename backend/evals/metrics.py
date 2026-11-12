"""
Deterministic evaluation metrics for BidPilot across RAG, GenAI, and Agentic tiers.
"""
from typing import Callable, Dict, List, Optional, Sequence
import re


def _norm_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def default_text_match(extracted: str, expected: str, threshold: float = 0.5) -> bool:
    """Fuzzy token-recall matcher for comparing extracted vs golden requirement strings."""
    exp_tokens = _norm_tokens(expected)
    ext_tokens = _norm_tokens(extracted)
    if not exp_tokens:
        return False
    return (len(exp_tokens & ext_tokens) / len(exp_tokens)) >= threshold


def recall_at_k(retrieved_hits: Sequence[bool], total_relevant: int, k: int) -> float:
    """Recall@K = |Relevant intersect Top-K| / |Relevant|."""
    if total_relevant <= 0:
        return 1.0
    hits = sum(1 for hit in list(retrieved_hits)[:k] if hit)
    return min(1.0, hits / total_relevant)


def precision_at_k(retrieved_hits: Sequence[bool], k: int) -> float:
    """Precision@K = |Relevant intersect Top-K| / |Retrieved Top-K|."""
    top_k = list(retrieved_hits)[:k]
    if not top_k:
        return 0.0
    return sum(1 for hit in top_k if hit) / len(top_k)


def reciprocal_rank(retrieved_hits: Sequence[bool]) -> float:
    """1 / rank_of_first_relevant_chunk (1-indexed), or 0.0 if none retrieved."""
    for idx, hit in enumerate(retrieved_hits, start=1):
        if hit:
            return 1.0 / idx
    return 0.0


def mean_reciprocal_rank(queries_hits: Sequence[Sequence[bool]]) -> float:
    """MRR across a set of queries."""
    if not queries_hits:
        return 0.0
    return sum(reciprocal_rank(hits) for hits in queries_hits) / len(queries_hits)


def negative_rejection_rate(unanswerable_retrieved_counts: Sequence[int]) -> float:
    """Fraction of unanswerable/out-of-domain queries returning 0 chunks above threshold."""
    if not unanswerable_retrieved_counts:
        return 1.0
    rejected = sum(1 for count in unanswerable_retrieved_counts if count == 0)
    return rejected / len(unanswerable_retrieved_counts)


def boundary_integrity_rate(chunks: Sequence[str], target_entities: Sequence[str]) -> float:
    """Fraction of target entities/phrases found completely intact inside at least one chunk."""
    if not target_entities:
        return 1.0
    lowered_chunks = [c.lower() for c in chunks]
    intact = 0
    for entity in target_entities:
        needle = entity.lower().strip()
        if any(needle in chunk for chunk in lowered_chunks):
            intact += 1
    return intact / len(target_entities)


def extraction_prf1(
    extracted_items: Sequence[str],
    expected_items: Sequence[str],
    match_fn: Optional[Callable[[str, str], bool]] = None,
) -> Dict[str, float]:
    """Bipartite greedy precision/recall/F1 between extracted requirements and golden items."""
    matcher = match_fn or default_text_match
    if not extracted_items and not expected_items:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "matched": 0}
    if not extracted_items or not expected_items:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "matched": 0}

    matched_expected = set()
    matched_extracted = 0
    for ext in extracted_items:
        for idx, exp in enumerate(expected_items):
            if idx not in matched_expected and matcher(ext, exp):
                matched_expected.add(idx)
                matched_extracted += 1
                break

    precision = matched_extracted / len(extracted_items)
    recall = len(matched_expected) / len(expected_items)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "matched": len(matched_expected),
    }


def confusion_matrix_and_macro_f1(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str],
) -> Dict[str, object]:
    """Compute per-class confusion matrix, overall accuracy, and macro-F1."""
    matrix: Dict[str, Dict[str, int]] = {
        t: {p: 0 for p in labels} for t in labels
    }
    for true_lbl, pred_lbl in zip(y_true, y_pred):
        t_key = true_lbl if true_lbl in matrix else labels[-1]
        p_key = pred_lbl if pred_lbl in matrix[t_key] else labels[-1]
        matrix[t_key][p_key] += 1

    f1_scores: List[float] = []
    per_class: Dict[str, Dict[str, float]] = {}
    for lbl in labels:
        tp = matrix[lbl][lbl]
        fp = sum(matrix[other][lbl] for other in labels if other != lbl)
        fn = sum(matrix[lbl][other] for other in labels if other != lbl)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        per_class[lbl] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}
        if (tp + fn) > 0 or (tp + fp) > 0:
            f1_scores.append(f1)

    accuracy = (
        sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
        if y_true else 0.0
    )
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "confusion_matrix": matrix,
    }


def false_positive_go_rate(y_true_decisions: Sequence[str], y_pred_decisions: Sequence[str]) -> float:
    """Fraction of true NO_GO tenders erroneously classified as GO."""
    no_go_indices = [i for i, lbl in enumerate(y_true_decisions) if lbl == "NO_GO"]
    if not no_go_indices:
        return 0.0
    false_go = sum(1 for i in no_go_indices if y_pred_decisions[i] == "GO")
    return round(false_go / len(no_go_indices), 4)


def mean_absolute_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """MAE = (1/N) * sum(|y_pred - y_true|)."""
    if not y_true:
        return 0.0
    return round(sum(abs(p - t) for t, p in zip(y_true, y_pred)) / len(y_true), 4)


def hallucination_audit_metrics(
    expected_passed: Sequence[bool],
    pred_passed: Sequence[bool],
    pred_scores: Sequence[float],
) -> Dict[str, float]:
    """Compute Hallucination TPR, False Alarm FPR, and Audit Score Separation."""
    poisoned_indices = [i for i, exp in enumerate(expected_passed) if not exp]
    clean_indices = [i for i, exp in enumerate(expected_passed) if exp]

    tpr = (
        sum(1 for i in poisoned_indices if not pred_passed[i]) / len(poisoned_indices)
        if poisoned_indices else 1.0
    )
    fpr = (
        sum(1 for i in clean_indices if not pred_passed[i]) / len(clean_indices)
        if clean_indices else 0.0
    )
    clean_mean = (
        sum(pred_scores[i] for i in clean_indices) / len(clean_indices)
        if clean_indices else 0.0
    )
    poisoned_mean = (
        sum(pred_scores[i] for i in poisoned_indices) / len(poisoned_indices)
        if poisoned_indices else 0.0
    )
    return {
        "hallucination_tpr": round(tpr, 4),
        "false_alarm_fpr": round(fpr, 4),
        "clean_mean_score": round(clean_mean, 2),
        "hallucinated_mean_score": round(poisoned_mean, 2),
        "score_separation": round(clean_mean - poisoned_mean, 2),
    }

