# BidPilot — Agentic AI Tender Processing & Matching Platform (Phase 1)

BidPilot is an agentic AI platform designed to help companies discover tender opportunities, parse complex RFP/tender documents into structured requirements, retrieve grounded company evidence using vector search (RAG), and generate requirement-by-requirement match reports.

This repository contains the complete **Phase 1 Implementation** (thin vertical slice).

---

## 🏗️ Architecture & Component Overview

```
bidpilot/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints (/api/tenders)
│   │   ├── agents/          # Autonomous Agents
│   │   │   ├── extraction_agent.py  # Structured JSON extraction with retry logic
│   │   │   └── matching_agent.py    # Vector RAG retrieval & match classifier
│   │   ├── db/              # DB connection & company document seeding (init_db.py)
│   │   ├── models/          # SQLAlchemy & Pydantic models (pgvector enabled)
│   │   ├── services/        # PDF parser, embeddings model, LLM client
│   │   └── main.py          # FastAPI application entrypoint
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── streamlit_app.py     # Streamlit Match Report Dashboard UI
├── data/
│   ├── sample_tenders/      # Sample RFP PDF files
│   ├── company_profile.json # Hardcoded company profile
│   └── company_docs/        # Company background TXT/PDF evidence documents
├── docker-compose.yml       # Complete local container orchestration (Postgres + pgvector + FastAPI)
└── .env.example             # Environment configuration variables
```

---

## ⚙️ Data Contracts & Database Schema

### Data Contracts
- **Extracted Tender JSON**: `{ title, organization, deadline, estimated_value, location, eligibility_requirements, technical_requirements, experience_requirements, certifications_required, deliverables, evaluation_criteria }`
- **MatchResult JSON**: `{ requirement, requirement_type, status, evidence, explanation }` where status is one of `["SATISFIED", "NOT_SATISFIED", "PARTIALLY_SATISFIED", "UNKNOWN"]`.

### PostgreSQL Database Schema
- `tenders`: Stores metadata of processed RFPs.
- `requirements`: Extracted requirements categorized by type.
- `companies`: Company profile metadata.
- `documents`: Embedded background company files.
- `document_chunks`: Text chunks + 384-dimensional vector embeddings (`pgvector`).
- `matches`: Per-requirement evaluation status, retrieved evidence citations, and LLM explanations.

---

## 🚀 How to Run BidPilot

### Option A: Running with Docker Compose (Recommended)

1. **Clone & Set Up Environment Variables**:
   ```bash
   cp .env.example .env
   ```
   *(Optionally add your `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` in `.env`. If no key is set, BidPilot operates in smart mock mode for testing).*

2. **Launch Postgres & Backend with Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```
   - **Postgres (with pgvector)**: Runs on `localhost:5432`
   - **FastAPI Backend**: Runs on `http://localhost:8000` (API Docs: `http://localhost:8000/docs`)

3. **Run Streamlit Frontend**:
   ```bash
   pip install streamlit requests
   streamlit run frontend/streamlit_app.py
   ```

---

### Option B: Running Locally (Python Venv)

1. **Start PostgreSQL Container**:
   ```bash
   docker run -d --name bidpilot_postgres -p 5432:5432 -e POSTGRES_USER=bidpilot_user -e POSTGRES_PASSWORD=bidpilot_pass -e POSTGRES_DB=bidpilot_db pgvector/pgvector:pg16
   ```

2. **Install Backend Dependencies**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Start FastAPI Backend**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Launch Streamlit UI**:
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

---

## 🧪 Testing the End-to-End Pipeline

1. Open the Streamlit App (`http://localhost:8501`).
2. In the sidebar, specify the tender PDF path (default pre-loaded: `data/sample_tenders/sample_tender_1.pdf`).
3. Click **🚀 Process Tender PDF**.
4. Observe the live pipeline execution:
   - PDF text parsing (`pdfplumber`).
   - Extraction Agent converts text into structured requirement JSON.
   - Matching Agent embeds requirements and performs vector search against company chunks in `pgvector`.
   - Classification as `SATISFIED`, `NOT_SATISFIED`, `PARTIALLY_SATISFIED`, or `UNKNOWN` with cited evidence.
5. Review the interactive **Match Matrix & Filter Tabs**.
