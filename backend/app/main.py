from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from .db.database import engine, Base
from .models import schema
from .api import tenders, company

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure pgvector extension and schema columns exist in PostgreSQL
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.execute(text("ALTER TABLE tenders ADD COLUMN IF NOT EXISTS reference_id VARCHAR;"))
        conn.execute(text("ALTER TABLE tenders ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'DISCOVERED';"))
        conn.execute(text("ALTER TABLE tenders ADD COLUMN IF NOT EXISTS fit_score FLOAT;"))
        conn.execute(text("ALTER TABLE tenders ADD COLUMN IF NOT EXISTS issuer_email VARCHAR;"))
        conn.execute(text("ALTER TABLE tenders ADD COLUMN IF NOT EXISTS pdf_path VARCHAR;"))
        conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS email VARCHAR;"))
        conn.commit()
    # Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up can be added here if needed

app = FastAPI(
    title="BidPilot API",
    description="API for BidPilot Autonomous Tender Processing & Matching Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenders.router, prefix="/api/tenders", tags=["tenders"])
app.include_router(company.router, prefix="/api/company", tags=["company"])

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "BidPilot Backend is running"}
