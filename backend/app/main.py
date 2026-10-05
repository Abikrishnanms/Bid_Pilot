from fastapi import FastAPI
from contextlib import asynccontextmanager
from .db.database import engine, Base
from .models import schema
from .api import tenders

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up can be added here if needed

app = FastAPI(
    title="BidPilot API",
    description="API for BidPilot Tender Processing & Matching Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(tenders.router, prefix="/api/tenders", tags=["tenders"])

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "BidPilot Backend is running"}
