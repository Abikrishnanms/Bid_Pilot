import streamlit as st
import requests
import json
import os
import time

# --- Configuration ---
st.set_page_config(page_title="BidPilot", page_icon="🚀", layout="wide")
API_URL = os.getenv("API_URL", "http://localhost:8000/api/tenders")

# --- UI Styling ---
st.markdown("""
<style>
    .status-satisfied { color: #00C853; font-weight: bold; }
    .status-partial { color: #FFD600; font-weight: bold; }
    .status-not-satisfied { color: #D50000; font-weight: bold; }
    .status-unknown { color: #9E9E9E; font-weight: bold; }
    .evidence-box { background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 0.9em; border-left: 4px solid #4CAF50;}
</style>
""", unsafe_allow_html=True)

st.title("🚀 BidPilot Dashboard")
st.markdown("Automated Tender Discovery & RAG Matching Platform")

# --- Sidebar: Tender Upload ---
with st.sidebar:
    st.header("📄 Upload Tender")
    uploaded_file = st.file_uploader("Choose a Tender PDF", type=["pdf"])
    process_btn = st.button("Extract Requirements")

# --- State Management ---
if 'tender_data' not in st.session_state:
    st.session_state.tender_data = None
if 'tender_id' not in st.session_state:
    st.session_state.tender_id = None
if 'match_results' not in st.session_state:
    st.session_state.match_results = None

# --- Main Logic ---
if uploaded_file and process_btn:
    with st.spinner("Processing PDF and extracting requirements via LLM..."):
        # For this prototype, we assume the file is saved locally so the backend can read it
        # Real-world: upload file bytes directly to API via multipart/form-data
        temp_path = os.path.join("data", "sample_tenders", uploaded_file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            # Mocking the process for Phase 1 if backend is running locally
            # In a real scenario we POST to /process
            response = requests.post(f"{API_URL}/process", json={"file_path": temp_path})
            if response.status_code == 200:
                st.session_state.tender_data = response.json()
                # Mock tender ID as 1 since we're using a fresh DB
                st.session_state.tender_id = 1 
                st.success("Tender successfully extracted!")
            else:
                st.error(f"Error processing tender: {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend API. Is it running?")

# --- Extraction Results ---
if st.session_state.tender_data:
    data = st.session_state.tender_data
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Estimated Value", data.get("estimated_value", "N/A"))
    col2.metric("Deadline", data.get("deadline", "N/A"))
    col3.metric("Organization", data.get("organization", "N/A"))
    
    with st.expander("View Extracted Requirements (Raw JSON)"):
        st.json(data)
        
    st.divider()
    
    # --- Match Generation ---
    if st.button("🔍 Run RAG Matching Agent against Company Evidence"):
        with st.spinner("Generating matches using pgvector and LLM..."):
            try:
                # Trigger the matching endpoint
                m_res = requests.post(f"{API_URL}/{st.session_state.tender_id}/matches")
                if m_res.status_code == 200:
                    # In a real scenario we'd GET the matches, for now we will mock the response structure
                    # based on what we expect the DB to contain to build the UI immediately.
                    st.success("Matching complete!")
                    st.session_state.match_results = [
                        {
                            "requirement": req,
                            "type": "Technical",
                            "status": "SATISFIED",
                            "explanation": "Company profile explicitly states 10+ years of cloud experience.",
                            "evidence": "Mock IT Solutions has over 10 years of experience in cloud infrastructure and DevOps."
                        } for req in data.get("technical_requirements", [])
                    ]
                else:
                    st.error("Failed to run matching engine.")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

# --- Match Matrix & Filters ---
if st.session_state.match_results:
    st.header("📊 Match Report")
    
    # Filters
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.multiselect(
            "Filter by Status",
            ["SATISFIED", "NOT_SATISFIED", "PARTIALLY_SATISFIED", "UNKNOWN"],
            default=["SATISFIED", "NOT_SATISFIED", "PARTIALLY_SATISFIED", "UNKNOWN"]
        )
        
    # Render Matrix
    for match in st.session_state.match_results:
        if match["status"] in status_filter:
            with st.container():
                st.markdown(f"**Requirement:** {match['requirement']}")
                
                status_class = match['status'].lower().replace("_", "-")
                st.markdown(f"**Status:** <span class='status-{status_class}'>{match['status']}</span>", unsafe_allow_html=True)
                
                st.markdown(f"**Explanation:** {match['explanation']}")
                
                with st.expander("View Retrieved Evidence"):
                    st.markdown(f"<div class='evidence-box'>{match['evidence']}</div>", unsafe_allow_html=True)
                
                st.divider()
