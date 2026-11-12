import os
import re
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import pdfplumber

from ..db.database import get_db
from ..models import schema
from ..services.chunking import chunk_text
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

def _extract_text_from_file(file_path: str) -> str:
    """Extract UTF-8 or PDF text from a saved document path."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        parts: List[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
        return "\n".join(parts)

    with open(file_path, "rb") as f:
        return f.read().decode("utf-8", errors="ignore")


def _embed_and_store_chunks(doc_id: int, content: str, db: Session) -> int:
    """Split text cleanly along sentence boundaries, batch-embed, and store in pgvector."""
    chunk_items = chunk_text(content, max_chars=550, overlap_sentences=1)
    if not chunk_items:
        return 0

    embeddings = embedding_service.embed_chunks([item["text"] for item in chunk_items])
    for item, emb in zip(chunk_items, embeddings):
        db.add(schema.DocumentChunk(
            document_id=doc_id,
            chunk_index=item["chunk_index"],
            text_content=item["text"],
            embedding=emb
        ))
    return len(chunk_items)


@router.post("/documents/index_text")
def index_document_text(
    request: DocumentIndexRequest,
    db: Session = Depends(get_db)
):
    """Index raw text content into the company vector knowledge base."""
    filename = os.path.basename(request.filename)
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

    chunks_count = _embed_and_store_chunks(doc.id, content, db)
    db.commit()
    return {
        "message": f"Successfully indexed '{filename}' with {chunks_count} sentence-aware vector chunks.",
        "document_id": doc.id,
        "chunks_count": chunks_count,
        "detected_company_email": detected_email
    }

@router.post("/documents/upload")
async def upload_company_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a real company capability statement, certification, or case study (PDF, TXT, MD, JSON)."""
    filename = os.path.basename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)

    content_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(content_bytes)

    try:
        extracted_text = _extract_text_from_file(save_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse document: {str(e)}")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Document contains no readable text content.")

    index_req = DocumentIndexRequest(filename=filename, content=extracted_text)
    return index_document_text(index_req, db)


@router.post("/documents/reindex")
def reindex_company_documents(db: Session = Depends(get_db)):
    """Re-chunk and re-embed all existing company documents using sentence-aware chunking."""
    docs = db.query(schema.Document).all()
    if not docs:
        return {"message": "No documents to reindex.", "reindexed_documents": 0, "total_chunks": 0}

    reindexed_docs = 0
    total_chunks = 0

    for doc in docs:
        disk_path = os.path.join(UPLOAD_DIR, os.path.basename(doc.filename))
        source_text = ""
        if os.path.exists(disk_path):
            try:
                source_text = _extract_text_from_file(disk_path)
            except Exception:
                source_text = ""

        if not source_text.strip():
            old_chunks = (
                db.query(schema.DocumentChunk)
                .filter(schema.DocumentChunk.document_id == doc.id)
                .order_by(schema.DocumentChunk.chunk_index.asc().nullslast(), schema.DocumentChunk.id.asc())
                .all()
            )
            source_text = "\n\n".join(c.text_content for c in old_chunks if c.text_content)

        if not source_text.strip():
            continue

        db.query(schema.DocumentChunk).filter(schema.DocumentChunk.document_id == doc.id).delete()
        count = _embed_and_store_chunks(doc.id, source_text, db)
        reindexed_docs += 1
        total_chunks += count

    db.commit()
    return {
        "message": f"Re-indexed {reindexed_docs} documents into {total_chunks} sentence-aware chunks.",
        "reindexed_documents": reindexed_docs,
        "total_chunks": total_chunks
    }

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
    chunks = (
        db.query(schema.DocumentChunk)
        .filter(schema.DocumentChunk.document_id == doc_id)
        .order_by(schema.DocumentChunk.chunk_index.asc().nullslast(), schema.DocumentChunk.id.asc())
        .all()
    )
    return [{
        "id": c.id,
        "document_id": c.document_id,
        "chunk_index": c.chunk_index,
        "snippet": c.text_content,
        "length": len(c.text_content)
    } for c in chunks]

