import os
import json
from sqlalchemy.orm import Session
from .database import engine, SessionLocal, Base
from ..models import schema
from ..services.embedding_service import EmbeddingService

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(schema.Company).first():
            print("Database already seeded.")
            return

        print("Seeding database...")
        
        # 1. Create Mock Company Profile
        company = schema.Company(
            name="Mock IT Solutions",
            profile_summary="A leading software development company specializing in cloud, AI, and secure architecture."
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        
        # 2. Add Mock Evidence Documents
        doc1 = schema.Document(company_id=company.id, filename="company_profile.pdf")
        doc2 = schema.Document(company_id=company.id, filename="iso_9001_certificate.pdf")
        db.add_all([doc1, doc2])
        db.commit()
        db.refresh(doc1)
        db.refresh(doc2)
        
        # 3. Create Chunks and Embeddings
        embedding_service = EmbeddingService()
        
        chunks = [
            {"doc_id": doc1.id, "text": "Mock IT Solutions has over 10 years of experience in cloud infrastructure and DevOps."},
            {"doc_id": doc1.id, "text": "We have 50+ certified Python and React developers on staff."},
            {"doc_id": doc2.id, "text": "Mock IT Solutions is ISO 9001 certified for quality management systems."}
        ]
        
        for c in chunks:
            emb = embedding_service.get_embedding(c["text"])
            db.add(schema.DocumentChunk(
                document_id=c["doc_id"],
                text_content=c["text"],
                embedding=emb
            ))
            
        db.commit()
        print("Database seeded successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
