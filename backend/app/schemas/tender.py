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
