from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .database import Base

class Tender(Base):
    __tablename__ = "tenders"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    organization = Column(String)
    deadline = Column(String)
    estimated_value = Column(String)
    location = Column(String)
    
    requirements = relationship("Requirement", back_populates="tender")

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
