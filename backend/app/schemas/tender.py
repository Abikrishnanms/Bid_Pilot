from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class ExtractedRequirements(BaseModel):
    title: str = Field(default="Untitled Tender", description="Title of the tender")
    organization: str = Field(default="", description="Issuing organization")
    deadline: str = Field(default="", description="Submission deadline")
    estimated_value: str = Field(default="", description="Estimated value or budget")
    location: str = Field(default="", description="Location of work")
    eligibility_requirements: List[str] = Field(default_factory=list, description="Eligibility requirements")
    technical_requirements: List[str] = Field(default_factory=list, description="Technical requirements")
    experience_requirements: List[str] = Field(default_factory=list, description="Experience requirements")
    certifications_required: List[str] = Field(default_factory=list, description="Certifications required")
    deliverables: List[str] = Field(default_factory=list, description="Deliverables")
    evaluation_criteria: List[str] = Field(default_factory=list, description="Evaluation criteria")

    @field_validator("title", "organization", "deadline", "estimated_value", "location", mode="before")
    @classmethod
    def _coerce_none_str(cls, v):
        return "" if v is None else str(v)

    @field_validator(
        "eligibility_requirements",
        "technical_requirements",
        "experience_requirements",
        "certifications_required",
        "deliverables",
        "evaluation_criteria",
        mode="before",
    )
    @classmethod
    def _coerce_none_list(cls, v):
        return [] if v is None else v

class MatchResult(BaseModel):
    requirement: str = ""
    requirement_type: str = "technical"
    status: str  # SATISFIED, NOT_SATISFIED, PARTIALLY_SATISFIED, UNKNOWN
    evidence: str = ""
    explanation: str = ""

    @field_validator("requirement", "requirement_type", "evidence", "explanation", mode="before")
    @classmethod
    def _coerce_match_str(cls, v):
        return "" if v is None else str(v)

class TenderProcessRequest(BaseModel):
    file_path: str

class ProposalDraft(BaseModel):
    executive_summary: str = Field(default="", description="Executive Summary addressing tender scope and client value")
    technical_approach: str = Field(default="", description="Detailed technical approach, architecture, and deliverables")
    compliance_matrix_summary: str = Field(default="", description="Summary of requirement fulfillment and evidence citations")
    commercial_terms: str = Field(default="", description="Commercial and engagement terms")
    full_markdown: str = Field(default="", description="The complete proposal document formatted in standard Markdown")

    @field_validator(
        "executive_summary",
        "technical_approach",
        "compliance_matrix_summary",
        "commercial_terms",
        "full_markdown",
        mode="before",
    )
    @classmethod
    def _coerce_draft_str(cls, v):
        return "" if v is None else str(v)

class ProposalReviewResult(BaseModel):
    passed: bool = Field(description="Whether all statements are grounded in evidence without hallucination")
    review_score: int = Field(description="Audit score from 0 to 100")
    unsupported_claims: List[str] = Field(default_factory=list, description="Any claims not backed by company evidence")
    recommendations: List[str] = Field(default_factory=list, description="Actionable suggestions to improve compliance")

    @field_validator("unsupported_claims", "recommendations", mode="before")
    @classmethod
    def _coerce_review_lists(cls, v):
        return [] if v is None else v

class StrategicTriageAnalysis(BaseModel):
    fatal_blockers: List[str] = Field(default_factory=list, description="Requirements that legally, statutorily, or contractually disqualify the vendor and cannot be mitigated or subcontracted")
    strategic_rationale: str = Field(default="", description="2-3 sentence executive briefing explaining the bid/no-bid qualification and risk strategy")

    @field_validator("fatal_blockers", mode="before")
    @classmethod
    def _coerce_blockers(cls, v):
        return [] if v is None else v

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
