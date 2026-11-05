import os
import re
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import pdfplumber

from ..db.database import get_db
from ..models import schema
from ..services.embedding_service import EmbeddingService

router = APIRouter()
embedding_service = EmbeddingService()
UPLOAD_DIR = "data/company_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class CompanyProfileRequest(BaseModel):
    name: str
    email: str
    profile_summary: Optional[str] = None

class DocumentIndexRequest(BaseModel):
    filename: str
    content: str

@router.get("/profile")
def get_company_profile(db: Session = Depends(get_db)):
    """Retrieve the registered user/company profile and contact email."""
    company = db.query(schema.Company).first()
    if not company:
        return {
            "registered": False,
            "name": "",
            "email": "",
            "profile_summary": ""
        }
    return {
        "registered": True,
        "id": company.id,
        "name": company.name,
        "email": company.email or "",
        "profile_summary": company.profile_summary or ""
    }

@router.post("/profile")
def save_company_profile(
    request: CompanyProfileRequest,
    db: Session = Depends(get_db)
):
    """Register or update company identity, official email address, and profile specifications."""
    company = db.query(schema.Company).first()
    if not company:
        company = schema.Company(
            name=request.name.strip(),
            email=request.email.strip().lower(),
            profile_summary=request.profile_summary or ""
        )
        db.add(company)
    else:
        company.name = request.name.strip()
        company.email = request.email.strip().lower()
        if request.profile_summary:
            company.profile_summary = request.profile_summary

    db.commit()
    db.refresh(company)

    return {
        "message": "Company profile registered successfully",
        "company": {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "profile_summary": company.profile_summary
        }
    }

@router.get("/documents")
def list_company_documents(db: Session = Depends(get_db)):
    """List all indexed company documents with chunk statistics."""
    company = db.query(schema.Company).first()
    if not company:
        return []

    docs = db.query(schema.Document).filter(schema.Document.company_id == company.id).all()
    results = []
    for d in docs:
        chunk_count = db.query(schema.DocumentChunk).filter(schema.DocumentChunk.document_id == d.id).count()
        results.append({
            "id": d.id,
            "filename": d.filename,
            "chunks_indexed": chunk_count,
            "status": "Indexed" if chunk_count > 0 else "Pending"
        })
    return results

@router.post("/documents/index_text")
def index_document_text(
    request: DocumentIndexRequest,
    db: Session = Depends(get_db)
):
    """Index raw text content into the company vector knowledge base."""
    filename = request.filename
    content = request.content
    company = db.query(schema.Company).first()
    
    # Auto-extract email from company documents if not yet registered
    detected_email = None
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content)
    if email_match:
        detected_email = email_match.group(0).lower()

    if not company:
        company = schema.Company(
            name=os.path.splitext(filename)[0].replace("_", " ").title(),
            email=detected_email or "",
            profile_summary=content[:300]
        )
        db.add(company)
        db.commit()
        db.refresh(company)
    elif detected_email and not company.email:
        company.email = detected_email
        db.commit()

    doc = schema.Document(company_id=company.id, filename=filename)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Chunk text (500 chars with 50 char overlap)
    chunk_size = 500
    overlap = 50
    start = 0
    chunks = []
    while start < len(content):
        chunk_text = content[start:start + chunk_size].strip()
        if chunk_text:
            chunks.append(chunk_text)
        start += (chunk_size - overlap)

    for c in chunks:
        emb = embedding_service.get_embedding(c)
        db.add(schema.DocumentChunk(
            document_id=doc.id,
            text_content=c,
            embedding=emb
        ))

    db.commit()
    return {
        "message": f"Successfully indexed '{filename}' with {len(chunks)} vector chunks.",
        "document_id": doc.id,
        "chunks_count": len(chunks),
        "detected_company_email": detected_email
    }

@router.post("/documents/upload")
async def upload_company_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a real company capability statement, certification, or case study (PDF, TXT, MD, JSON)."""
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    save_path = os.path.join(UPLOAD_DIR, filename)

    content_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(content_bytes)

    # Extract text from file
    if ext == ".pdf":
        extracted_text = ""
        try:
            with pdfplumber.open(save_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        try:
            extracted_text = content_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to decode text file: {str(e)}")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Document contains no readable text content.")

    # Reuse index logic
    index_req = DocumentIndexRequest(filename=filename, content=extracted_text)
    return index_document_text(index_req, db)

@router.delete("/documents/{doc_id}")
def delete_company_document(doc_id: int, db: Session = Depends(get_db)):
    """Delete a company document and its associated vector embeddings."""
    doc = db.query(schema.Document).filter(schema.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    deleted_chunks = db.query(schema.DocumentChunk).filter(schema.DocumentChunk.document_id == doc_id).delete()
    db.delete(doc)
    db.commit()

    return {
        "message": f"Deleted document #{doc_id} ('{doc.filename}') and {deleted_chunks} vector chunks.",
        "deleted_chunks": deleted_chunks
    }

@router.post("/documents/clear_samples")
def clear_sample_documents(db: Session = Depends(get_db)):
    """Remove initial mock seed documents (e.g. company_profile.pdf, iso_9001_certificate.pdf)."""
    sample_filenames = ["company_profile.pdf", "iso_9001_certificate.pdf", "Mock_IT_Solutions_Corporate_Profile.pdf"]
    sample_docs = db.query(schema.Document).filter(schema.Document.filename.in_(sample_filenames)).all()
    
    deleted_count = 0
    deleted_chunks = 0
    for doc in sample_docs:
        chunks = db.query(schema.DocumentChunk).filter(schema.DocumentChunk.document_id == doc.id).delete()
        deleted_chunks += chunks
        db.delete(doc)
        deleted_count += 1
    
    db.commit()
    return {
        "message": f"Purged {deleted_count} sample documents and {deleted_chunks} mock vector chunks.",
        "deleted_documents": deleted_count,
        "deleted_chunks": deleted_chunks
    }

@router.get("/documents/{doc_id}/chunks")
def get_document_chunks(doc_id: int, db: Session = Depends(get_db)):
    """Inspect the pgvector chunks indexed for a specific company document."""
    chunks = db.query(schema.DocumentChunk).filter(schema.DocumentChunk.document_id == doc_id).all()
    return [{
        "id": c.id,
        "document_id": c.document_id,
        "snippet": c.text_content,
        "length": len(c.text_content)
    } for c in chunks]

