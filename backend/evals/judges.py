"""GenAI LLM-as-a-Judge schemas and coverage evaluators for BidPilot."""
from typing import Dict, List, Sequence
from pydantic import BaseModel, Field, field_validator

from evals.metrics import default_text_match


class ProposalQualityEval(BaseModel):
    total_verifiable_claims: int = Field(description="Total factual assertions made in the proposal")
    supported_claims: int = Field(description="Number of assertions directly grounded in cited evidence")
    unsupported_claims: List[str] = Field(default_factory=list, description="Claims not supported by evidence")
    faithfulness_score: float = Field(description="Fraction in [0.0, 1.0] of supported claims")
    tender_relevance_score: float = Field(description="Score in [0.0, 1.0] for domain and requirement relevance")
    reasoning: str = Field(default="", description="Concise justification for scores")

    @field_validator("unsupported_claims", mode="before")
    @classmethod
    def _coerce_none_list(cls, v):
        return [] if v is None else v


def compute_requirement_coverage(proposal_text: str, requirements: Sequence[str]) -> float:
    """Compute fraction of tender requirements addressed in proposal markdown."""
    if not requirements:
        return 1.0
    lines = [ln.strip() for ln in (proposal_text or "").splitlines() if len(ln.strip()) > 10]
    covered = 0
    for req in requirements:
        if any(default_text_match(line, req, threshold=0.4) for line in lines) or default_text_match(
            proposal_text or "", req, threshold=0.5
        ):
            covered += 1
    return round(covered / len(requirements), 4)


def evaluate_proposal_with_judge(
    proposal_markdown: str,
    evidence_context: str,
    tender_title: str,
    tender_org: str,
    llm_provider,
) -> Dict[str, object]:
    """Run LLM-as-a-Judge evaluation on a drafted proposal against evidence and tender scope."""
    prompt = (
        "You are an objective Proposal Quality & Faithfulness Evaluator.\n"
        f"Tender Title: {tender_title}\n"
        f"Issuing Authority: {tender_org}\n\n"
        f"CITED COMPANY EVIDENCE:\n{evidence_context}\n\n"
        f"GENERATED PROPOSAL:\n{proposal_markdown}\n\n"
        "Score faithfulness_score in [0.0, 1.0] (strictly grounded claims / total claims) and "
        "tender_relevance_score in [0.0, 1.0] (how well the proposal addresses this specific tender scope)."
    )
    res: ProposalQualityEval = llm_provider.extract_structured_data(
        text=proposal_markdown,
        schema=ProposalQualityEval,
        prompt=prompt,
    )
    return {
        "total_verifiable_claims": max(0, res.total_verifiable_claims),
        "supported_claims": max(0, res.supported_claims),
        "unsupported_claims": res.unsupported_claims,
        "faithfulness_score": max(0.0, min(1.0, float(res.faithfulness_score))),
        "tender_relevance_score": max(0.0, min(1.0, float(res.tender_relevance_score))),
        "reasoning": res.reasoning,
    }

