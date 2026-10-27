from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedRequirements(BaseModel):
    title: str = Field(description="Title of the tender")
    organization: str = Field(description="Issuing organization")
    deadline: str = Field(description="Submission deadline")
    estimated_value: str = Field(description="Estimated value or budget")
    location: str = Field(description="Location of work")
    eligibility_requirements: List[str] = Field(description="Eligibility requirements")
    technical_requirements: List[str] = Field(description="Technical requirements")
    experience_requirements: List[str] = Field(description="Experience requirements")
    certifications_required: List[str] = Field(description="Certifications required")
    deliverables: List[str] = Field(description="Deliverables")
    evaluation_criteria: List[str] = Field(description="Evaluation criteria")

class MatchResult(BaseModel):
    requirement: str
    requirement_type: str
    status: str  # SATISFIED, NOT_SATISFIED, PARTIALLY_SATISFIED, UNKNOWN
    evidence: str
    explanation: str

class TenderProcessRequest(BaseModel):
    file_path: str

class ProposalDraft(BaseModel):
    executive_summary: str = Field(description="Executive Summary addressing tender scope and client value")
    technical_approach: str = Field(description="Detailed technical approach, architecture, and deliverables")
    compliance_matrix_summary: str = Field(description="Summary of requirement fulfillment and evidence citations")
    commercial_terms: str = Field(description="Commercial and engagement terms")
    full_markdown: str = Field(description="The complete proposal document formatted in standard Markdown")

class ProposalReviewResult(BaseModel):
    passed: bool = Field(description="Whether all statements are grounded in evidence without hallucination")
    review_score: int = Field(description="Audit score from 0 to 100")
    unsupported_claims: List[str] = Field(default_factory=list, description="Any claims not backed by company evidence")
    recommendations: List[str] = Field(default_factory=list, description="Actionable suggestions to improve compliance")

class StrategicTriageAnalysis(BaseModel):
    fatal_blockers: List[str] = Field(default_factory=list, description="Requirements that legally, statutorily, or contractually disqualify the vendor and cannot be mitigated or subcontracted")
    strategic_rationale: str = Field(description="2-3 sentence executive briefing explaining the bid/no-bid qualification and risk strategy")

class TriageResult(BaseModel):
    tender_id: int
    fit_score: float
    decision: str # "GO", "REVIEW", "NO_GO"
    rationale: str
    hard_blockers: List[str] = []
    satisfied_count: int
    gap_count: int

class EmailSendRequest(BaseModel):
    recipient_email: Optional[str] = None
    subject: Optional[str] = None
    notes: Optional[str] = None
