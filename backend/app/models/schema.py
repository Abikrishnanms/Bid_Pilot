from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
from ..db.database import Base

class Tender(Base):
    __tablename__ = "tenders"
    id = Column(Integer, primary_key=True, index=True)
    reference_id = Column(String, unique=True, index=True, nullable=True)
    title = Column(String, index=True)
    organization = Column(String)
    deadline = Column(String)
    estimated_value = Column(String)
    location = Column(String)
    status = Column(String, default="DISCOVERED") # DISCOVERED, EVALUATED, PROPOSAL_READY, APPROVED, SUBMITTED, NO_GO
    fit_score = Column(Float, nullable=True) # 0 to 100
    issuer_email = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    
    requirements = relationship("Requirement", back_populates="tender", cascade="all, delete-orphan")
    proposal = relationship("Proposal", back_populates="tender", uselist=False, cascade="all, delete-orphan")

class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"))
    req_type = Column(String) # e.g. 'technical', 'eligibility'
    description = Column(Text)
    
    tender = relationship("Tender", back_populates="requirements")
    matches = relationship("Match", back_populates="requirement")

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, nullable=True)
    profile_summary = Column(Text)
    
    documents = relationship("Document", back_populates="company")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    filename = Column(String)
    
    company = relationship("Company", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    text_content = Column(Text)
    embedding = Column(Vector(384)) # Using 384 dimensions as per PRD
    
    document = relationship("Document", back_populates="chunks")

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id"))
    status = Column(String) # SATISFIED, NOT_SATISFIED, PARTIALLY_SATISFIED, UNKNOWN
    evidence = Column(Text)
    explanation = Column(Text)
    
    requirement = relationship("Requirement", back_populates="matches")

class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), unique=True, nullable=False)
    
    executive_summary = Column(Text, nullable=True)
    technical_approach = Column(Text, nullable=True)
    compliance_matrix = Column(JSON, nullable=True) # list of {requirement, status, evidence, explanation}
    commercial_terms = Column(Text, nullable=True)
    full_content = Column(Text, nullable=True) # Full Markdown draft
    
    status = Column(String, default="DRAFT") # DRAFT, VERIFIED, APPROVED, SUBMITTED
    review_notes = Column(Text, nullable=True)
    fact_check_passed = Column(Integer, default=0) # 0 = pending, 1 = passed, -1 = flags
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tender = relationship("Tender", back_populates="proposal")
