import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Briefcase, LayoutDashboard, Upload, FileText, BarChart2,
  CheckCircle, Search, PenTool, ShieldCheck, File,
  Loader2, Check, AlertTriangle, Download, RefreshCw, Send, CheckCircle2, XCircle,
  Trash2, UploadCloud, Eye, FileUp
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

function Sidebar() {
  const navItems = [
    { path: "/", icon: <LayoutDashboard size={20} />, label: "Dashboard" },
    { path: "/upload", icon: <Upload size={20} />, label: "Tenders & Discovery" },
    { path: "/documents", icon: <FileText size={20} />, label: "Company Documents" },
    { path: "/matches", icon: <BarChart2 size={20} />, label: "Match & Triage" },
    { path: "/compliance", icon: <CheckCircle size={20} />, label: "Compliance Report" },
    { path: "/proposal", icon: <PenTool size={20} />, label: "Proposal Generator" },
    { path: "/review", icon: <ShieldCheck size={20} />, label: "Review & Approval" },
  ];

  return (
    <div className="sidebar">
      <h2><Briefcase size={28} /> BidPilot</h2>
      <div className="nav-links">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
          >
            {item.icon} {item.label}
          </NavLink>
        ))}
      </div>
    </div>
  );
}

function Dashboard() {
  const [metrics, setMetrics] = useState({
    active_tenders: 0,
    qualified_go_tenders: 0,
    pipeline_value: "$0",
    submitted_bids: 0,
    won_bids: 0,
    lost_bids: 0,
    success_rate: "0.0%",
    avg_turnaround: "< 1h",
    company_documents: 0,
    indexed_chunks: 0,
    pending_approvals: 0
  });
  const [tenders, setTenders] = useState([]);
  const [fetching, setFetching] = useState(false);
  const [msg, setMsg] = useState("");

  const loadData = async () => {
    try {
      const [mRes, tRes] = await Promise.all([
        axios.get(`${API_BASE}/tenders/metrics/dashboard`),
        axios.get(`${API_BASE}/tenders/`)
      ]);
      setMetrics(mRes.data);
      setTenders(tRes.data);
    } catch (e) {
      console.error("Failed to load dashboard metrics", e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAutoFetch = async () => {
    setFetching(true);
    setMsg("");
    try {
      const res = await axios.post(`${API_BASE}/tenders/fetch_new`);
      setMsg(res.data.message);
      await loadData();
    } catch (e) {
      setMsg("Failed to auto-fetch tenders: " + (e.response?.data?.detail || e.message));
    } finally {
      setFetching(false);
    }
  };

  const handleUpdateStatus = async (id, status) => {
    try {
      await axios.patch(`${API_BASE}/tenders/${id}/status`, { status });
      await loadData();
    } catch (e) {
      alert("Failed to update status: " + (e.response?.data?.detail || e.message));
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1>Executive Dashboard</h1>
        </div>
        <button className="btn" onClick={handleAutoFetch} disabled={fetching}>
          {fetching ? <><Loader2 className="spinner" size={18} /> Discovering...</> : <><RefreshCw size={18} /> Fetch From Gov Feeds</>}
        </button>
      </div>

      {msg && <div className="card" style={{ background: '#f0fdf4', borderLeft: '4px solid var(--success)', padding: '0.8rem', marginBottom: '1.5rem' }}>{msg}</div>}

      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
        <div className="metric-card">
          <span className="metric-label">Discovered Tenders</span>
          <span className="metric-value">{metrics.active_tenders}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Pipeline Value</span>
          <span className="metric-value" style={{ color: 'var(--primary)' }}>{metrics.pipeline_value}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Qualified (GO) Bids</span>
          <span className="metric-value" style={{ color: 'var(--success)' }}>{metrics.qualified_go_tenders}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Submitted Bids</span>
          <span className="metric-value">{metrics.submitted_bids}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Win Success Rate</span>
          <span className="metric-value" style={{ color: 'var(--success)' }}>{metrics.success_rate}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Avg AI Turnaround</span>
          <span className="metric-value" style={{ color: 'var(--text-muted)' }}>{metrics.avg_turnaround}</span>
        </div>
      </div>

      <div className="card" style={{ marginTop: '2rem' }}>
        <h3 style={{ marginBottom: '1rem' }}>Active Tender Opportunities</h3>
        {tenders.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No tenders discovered yet. Click "Fetch From Gov Feeds" to poll live opportunities.</p>
        ) : (
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)', paddingBottom: '0.5rem' }}>
                <th style={{ padding: '0.75rem 0.5rem' }}>Ref ID</th>
                <th>Title</th>
                <th>Estimated Value</th>
                <th>Fit Score</th>
                <th>Triage Status</th>
                <th>Proposal</th>
                <th>Bid Outcome</th>
              </tr>
            </thead>
            <tbody>
              {tenders.map((t) => (
                <tr key={t.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>{t.reference_id || `TEN-${t.id}`}</td>
                  <td>{t.title}</td>
                  <td style={{ fontWeight: 500 }}>{t.estimated_value || 'N/A'}</td>
                  <td>
                    <span style={{ fontWeight: 700, color: t.fit_score >= 70 ? 'var(--success)' : t.fit_score >= 50 ? 'var(--warning)' : 'var(--danger)' }}>
                      {t.fit_score !== null ? `${t.fit_score}%` : 'Pending'}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${t.status === 'WON' || t.status === 'PROPOSAL_READY' || t.status === 'SUBMITTED' ? 'SATISFIED' : t.status === 'NO_GO' || t.status === 'LOST' ? 'NOT_SATISFIED' : 'PARTIALLY_SATISFIED'}`}>
                      {t.status}
                    </span>
                  </td>
                  <td>
                    {t.has_proposal ? (
                      <span style={{ color: 'var(--success)', fontWeight: 500 }}><Check size={16} style={{ verticalAlign: 'middle' }} /> {t.proposal_status || 'Drafted'}</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>None</span>
                    )}
                  </td>
                  <td>
                    {t.status === 'SUBMITTED' ? (
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button
                          className="btn"
                          style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', background: '#22c55e', color: '#fff' }}
                          onClick={() => handleUpdateStatus(t.id, 'WON')}
                        >
                          Mark Won
                        </button>
                        <button
                          className="btn"
                          style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', background: '#ef4444', color: '#fff' }}
                          onClick={() => handleUpdateStatus(t.id, 'LOST')}
                        >
                          Lost
                        </button>
                      </div>
                    ) : t.status === 'WON' ? (
                      <span style={{ color: 'var(--success)', fontWeight: 700, fontSize: '0.85rem' }}>Awarded 🏆</span>
                    ) : t.status === 'LOST' ? (
                      <span style={{ color: 'var(--danger)', fontWeight: 600, fontSize: '0.85rem' }}>Lost</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>In Progress</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function TenderUpload() {
  const [tenders, setTenders] = useState([]);
  const [fetching, setFetching] = useState(false);
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [msg, setMsg] = useState("");
  const [uploadMsg, setUploadMsg] = useState("");

  const loadTenders = async () => {
    try {
      const res = await axios.get(`${API_BASE}/tenders/`);
      setTenders(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadTenders();
  }, []);

  const handleFetchFeeds = async () => {
    setFetching(true);
    setMsg("");
    try {
      const res = await axios.post(`${API_BASE}/tenders/fetch_new`);
      setMsg(res.data.message);
      await loadTenders();
    } catch (e) {
      setMsg("Error fetching feeds: " + (e.response?.data?.detail || e.message));
    } finally {
      setFetching(false);
    }
  };

  const handleUploadTenderPdf = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadingPdf(true);
    setUploadMsg("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await axios.post(`${API_BASE}/tenders/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setUploadMsg(`Successfully uploaded & extracted '${file.name}' (${res.data.title})!`);
      await loadTenders();
    } catch (err) {
      setUploadMsg("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploadingPdf(false);
      e.target.value = null;
    }
  };

  return (
    <div>
      <h1>Automated Tender Discovery & Ingestion</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Option A: Live Gov Feed Poller */}
        <div className="card">
          <h3>1. Live Government Feeds</h3>
          <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 1rem' }}>
            Automatically ingest real public tenders from the UK Contracts Finder OCDS portal.
          </p>
          <button className="btn" onClick={handleFetchFeeds} disabled={fetching}>
            {fetching ? <><Loader2 className="spinner" size={18} /> Polling Feeds...</> : <><RefreshCw size={18} /> Ingest Live Gov Feeds</>}
          </button>
          {msg && <p style={{ marginTop: '1rem', color: 'var(--success)', fontWeight: 500 }}>{msg}</p>}
        </div>

        {/* Option B: Custom RFP PDF Upload */}
        <div className="card">
          <h3>2. Upload Custom RFP PDF</h3>
          <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 1rem' }}>
            Upload any custom government or enterprise solicitation PDF to extract requirements.
          </p>
          <label className="btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', cursor: uploadingPdf ? 'not-allowed' : 'pointer' }}>
            {uploadingPdf ? <><Loader2 className="spinner" size={18} /> Extracting PDF...</> : <><UploadCloud size={18} /> Select Tender PDF</>}
            <input
              type="file"
              accept=".pdf"
              onChange={handleUploadTenderPdf}
              disabled={uploadingPdf}
              style={{ display: 'none' }}
            />
          </label>
          {uploadMsg && <p style={{ marginTop: '1rem', color: 'var(--success)', fontWeight: 500 }}>{uploadMsg}</p>}
        </div>
      </div>

      <div className="card">
        <h3>Discovered Tender Catalog</h3>
        {tenders.map((t) => (
          <div key={t.id} style={{ padding: '1rem', border: '1px solid var(--border)', borderRadius: '0.5rem', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4>{t.title}</h4>
              <span className={`status-badge ${t.fit_score >= 70 ? 'SATISFIED' : 'PARTIALLY_SATISFIED'}`}>Fit: {t.fit_score || 0}%</span>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
              Issuer: <strong>{t.organization}</strong> &bull; Budget: <strong>{t.estimated_value}</strong> &bull; Deadline: <strong>{t.deadline}</strong>
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompanyDocuments() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filename, setFilename] = useState("");
  const [content, setContent] = useState("");
  const [msg, setMsg] = useState("");

  // Company Profile Registration State
  const [companyName, setCompanyName] = useState("");
  const [companyEmail, setCompanyEmail] = useState("");
  const [companySummary, setCompanySummary] = useState("");
  const [profileMsg, setProfileMsg] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  const loadProfile = async () => {
    try {
      const res = await axios.get(`${API_BASE}/company/profile`);
      if (res.data) {
        setCompanyName(res.data.name || "");
        setCompanyEmail(res.data.email || "");
        setCompanySummary(res.data.profile_summary || "");
      }
    } catch (e) {
      console.error("Failed to load company profile", e);
    }
  };

  const loadDocs = async () => {
    try {
      const res = await axios.get(`${API_BASE}/company/documents`);
      setDocs(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadDocs();
    loadProfile();
  }, []);

  const handleSaveProfile = async () => {
    if (!companyName.trim() || !companyEmail.trim()) {
      return alert("Please provide both Company Name and Official Email.");
    }
    setSavingProfile(true);
    setProfileMsg("");
    try {
      const res = await axios.post(`${API_BASE}/company/profile`, {
        name: companyName,
        email: companyEmail,
        profile_summary: companySummary
      });
      setProfileMsg("Official Company Profile & Submission Email registered successfully!");
    } catch (e) {
      setProfileMsg("Failed to save profile: " + (e.response?.data?.detail || e.message));
    } finally {
      setSavingProfile(false);
    }
  };

  const handleIndexText = async () => {
    if (!filename || !content) return alert("Please provide document name and text content.");
    setLoading(true);
    setMsg("");
    try {
      const res = await axios.post(`${API_BASE}/company/documents/index_text`, {
        filename,
        content
      });
      setMsg(res.data.message);
      setFilename("");
      setContent("");
      await loadDocs();
      await loadProfile();
    } catch (e) {
      setMsg("Failed: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [selectedChunks, setSelectedChunks] = useState(null);
  const [selectedDocTitle, setSelectedDocTitle] = useState("");
  const [loadingChunks, setLoadingChunks] = useState(false);

  const handleUploadFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadingDoc(true);
    setMsg("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await axios.post(`${API_BASE}/company/documents/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setMsg(res.data.message);
      await loadDocs();
      await loadProfile();
    } catch (err) {
      setMsg("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploadingDoc(false);
      e.target.value = null;
    }
  };

  const handleDeleteDoc = async (id, filename) => {
    if (!window.confirm(`Delete '${filename}' and all its vector embeddings from pgvector?`)) return;
    try {
      const res = await axios.delete(`${API_BASE}/company/documents/${id}`);
      setMsg(res.data.message);
      if (selectedChunks && selectedDocTitle === filename) {
        setSelectedChunks(null);
      }
      await loadDocs();
    } catch (err) {
      alert("Failed to delete document: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleClearSamples = async () => {
    if (!window.confirm("Purge initial mock seed documents (e.g. company_profile.pdf, iso_9001_certificate.pdf) from the database?")) return;
    try {
      const res = await axios.post(`${API_BASE}/company/documents/clear_samples`);
      setMsg(res.data.message);
      setSelectedChunks(null);
      await loadDocs();
    } catch (err) {
      alert("Failed to clear samples: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleViewChunks = async (id, title) => {
    setLoadingChunks(true);
    setSelectedDocTitle(title);
    try {
      const res = await axios.get(`${API_BASE}/company/documents/${id}/chunks`);
      setSelectedChunks(res.data);
    } catch (err) {
      alert("Failed to load chunks: " + err.message);
    } finally {
      setLoadingChunks(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1>Company Profile & Knowledge Base</h1>
          <p style={{ color: 'var(--text-muted)' }}>
            Register your official company identity and email for automated proposal submissions, and index capability documents for RAG matching.
          </p>
        </div>
        <button
          className="btn"
          style={{ background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca', fontSize: '0.85rem' }}
          onClick={handleClearSamples}
        >
          <Trash2 size={16} /> Purge Mock Seed Data
        </button>
      </div>

      {/* 1. Official Company Registration & Email */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3>1. Official Company Identity & Bid Email</h3>
          {companyEmail && <span className="status-badge SATISFIED">Registered</span>}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
              Official Company Name:
            </label>
            <input
              type="text"
              placeholder="e.g. Apex Innovations Technologies"
              value={companyName}
              onChange={e => setCompanyName(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
              Official Submission Email (Sender):
            </label>
            <input
              type="email"
              placeholder="e.g. bids@apexinnovations.com"
              value={companyEmail}
              onChange={e => setCompanyEmail(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
            />
          </div>
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
            Company Core Competency & Profile Summary:
          </label>
          <textarea
            placeholder="Enterprise software engineering, cloud migration, AI systems, and cybersecurity..."
            value={companySummary}
            onChange={e => setCompanySummary(e.target.value)}
            style={{ minHeight: '80px', width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)' }}
          />
        </div>
        <button className="btn" onClick={handleSaveProfile} disabled={savingProfile}>
          {savingProfile ? <><Loader2 className="spinner" size={18} /> Saving Profile...</> : "Save Company Identity & Email"}
        </button>
        {profileMsg && <p style={{ color: 'var(--success)', marginTop: '0.75rem', fontWeight: 500 }}>{profileMsg}</p>}
      </div>

      {/* 2. Capability Document Ingestion: File Upload + Text Paste */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h3>2. Index Capability Documents into pgvector</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Upload authentic company capability PDFs, certifications, or past performance statements to embed into 384-dimensional vector chunks.
        </p>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1.5rem', padding: '1rem', background: '#f8fafc', borderRadius: '6px', border: '1px dashed var(--border)' }}>
          <label className="btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', cursor: uploadingDoc ? 'not-allowed' : 'pointer' }}>
            {uploadingDoc ? <><Loader2 className="spinner" size={18} /> Parsing & Embedding...</> : <><UploadCloud size={18} /> Upload File (PDF, TXT, MD)</>}
            <input
              type="file"
              accept=".pdf,.txt,.md,.json"
              onChange={handleUploadFile}
              disabled={uploadingDoc}
              style={{ display: 'none' }}
            />
          </label>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Directly parse PDF text via pdfplumber or upload plain text/markdown evidence.
          </span>
        </div>

        <h4 style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>Or Paste Capability Statement / Snippet:</h4>
        <input
          type="text"
          placeholder="Document Title (e.g. FedRAMP_Compliance_Statement.txt)"
          value={filename}
          onChange={e => setFilename(e.target.value)}
          style={{ marginBottom: '0.75rem' }}
        />
        <textarea
          placeholder="Paste capability statements, project metrics, or certification details to embed into 384-dimensional vector chunks..."
          value={content}
          onChange={e => setContent(e.target.value)}
          style={{ minHeight: '100px', marginBottom: '1rem' }}
        />
        <button className="btn" onClick={handleIndexText} disabled={loading}>
          {loading ? <><Loader2 className="spinner" size={18} /> Chunking & Embedding...</> : "Index Pasted Text Into pgvector"}
        </button>
        {msg && <p style={{ color: 'var(--success)', marginTop: '0.75rem', fontWeight: 500 }}>{msg}</p>}
      </div>

      {/* 3. Indexed Documents Repository */}
      <div className="card">
        <h3>Indexed Documents Repository ({docs.length})</h3>
        {docs.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No documents indexed yet. Upload a capability PDF or paste text above.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Document</th>
                <th>Status</th>
                <th>Vector Chunks</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td><File size={16} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle' }} /> {d.filename}</td>
                  <td><span style={{ color: 'var(--success)' }}><Check size={16} style={{ verticalAlign: 'middle' }} /> {d.status}</span></td>
                  <td>{d.chunks_indexed} chunks</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="btn"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', background: '#f1f5f9', color: '#334155' }}
                        onClick={() => handleViewChunks(d.id, d.filename)}
                      >
                        <Eye size={14} style={{ verticalAlign: 'middle' }} /> View Chunks
                      </button>
                      <button
                        className="btn"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', background: '#fee2e2', color: '#b91c1c' }}
                        onClick={() => handleDeleteDoc(d.id, d.filename)}
                      >
                        <Trash2 size={14} style={{ verticalAlign: 'middle' }} /> Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Vector Chunks Inspector Modal/Box */}
      {selectedChunks && (
        <div className="card" style={{ marginTop: '2rem', border: '2px solid var(--primary)', background: '#f8fafc' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Vector Chunks for: <em>{selectedDocTitle}</em> ({selectedChunks.length} chunks)</h3>
            <button className="btn" style={{ padding: '0.2rem 0.6rem', fontSize: '0.8rem' }} onClick={() => setSelectedChunks(null)}>Close</button>
          </div>
          {selectedChunks.map((c, idx) => (
            <div key={c.id} style={{ padding: '0.75rem', background: '#fff', borderRadius: '4px', border: '1px solid var(--border)', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)' }}>Chunk #{idx + 1} (pgvector ID: {c.id}, {c.length} chars)</span>
              <p style={{ marginTop: '0.3rem', fontSize: '0.9rem', color: '#1e293b' }}>{c.snippet}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MatchReport() {
  const [tenders, setTenders] = useState([]);
  const [selectedTenderId, setSelectedTenderId] = useState(null);
  const [tenderDetail, setTenderDetail] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API_BASE}/tenders/`).then(res => {
      setTenders(res.data);
      if (res.data.length > 0) {
        setSelectedTenderId(res.data[0].id);
      }
    });
  }, []);

  const loadDetail = async (id) => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/tenders/${id}`);
      setTenderDetail(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedTenderId) {
      loadDetail(selectedTenderId);
    }
  }, [selectedTenderId]);

  const handleRunTriage = async () => {
    if (!selectedTenderId) return;
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/tenders/${selectedTenderId}/triage`);
      await loadDetail(selectedTenderId);
    } catch (e) {
      alert("Triage error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Semantic Match & Triage Report</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
        Evidence-grounded vector similarity comparison between tender requirements and company capability chunks.
      </p>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '2rem' }}>
        <label style={{ fontWeight: 600 }}>Select Tender:</label>
        <select
          value={selectedTenderId || ""}
          onChange={e => setSelectedTenderId(Number(e.target.value))}
          style={{ padding: '0.5rem 1rem', borderRadius: '0.25rem', border: '1px solid var(--border)' }}
        >
          {tenders.map(t => (
            <option key={t.id} value={t.id}>{t.title} ({t.reference_id || t.id})</option>
          ))}
        </select>
        <button className="btn" onClick={handleRunTriage} disabled={loading}>
          {loading ? <Loader2 className="spinner" size={18} /> : <RefreshCw size={18} />} Run Triage Agent
        </button>
      </div>

      {tenderDetail && (
        <>
          <div className="metrics-grid" style={{ marginBottom: '2rem' }}>
            <div className="metric-card">
              <span className="metric-label">Bid Readiness Fit Score</span>
              <span className="metric-value" style={{ color: tenderDetail.fit_score >= 70 ? 'var(--success)' : 'var(--danger)' }}>
                {tenderDetail.fit_score || 0}%
              </span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Triage Decision</span>
              <span className="metric-value" style={{ fontSize: '1.8rem', color: tenderDetail.status === 'PROPOSAL_READY' || tenderDetail.status === 'SUBMITTED' ? 'var(--success)' : 'var(--danger)' }}>
                {tenderDetail.status === 'PROPOSAL_READY' ? 'GO (Qualified)' : tenderDetail.status}
              </span>
            </div>
          </div>

          <h3>Requirement-by-Requirement Evidence Citations</h3>
          {tenderDetail.requirements.map((req, idx) => (
            <div key={idx} className="card" style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h4>{req.description}</h4>
                <span className={`status-badge ${req.status}`}>{req.status.replace("_", " ")}</span>
              </div>
              <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                <strong>Analysis:</strong> {req.explanation || "Evaluated by pgvector cosine search"}
              </p>
              {req.evidence && (
                <div className="evidence-box" style={{ marginTop: '0.5rem', background: '#f8fafc', padding: '0.75rem', borderRadius: '0.25rem' }}>
                  <strong>Cited Company Evidence:</strong> {req.evidence}
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function ComplianceReport() {
  const [tenders, setTenders] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    axios.get(`${API_BASE}/tenders/`).then(res => {
      setTenders(res.data);
      if (res.data.length > 0) {
        axios.get(`${API_BASE}/tenders/${res.data[0].id}`).then(d => setSelected(d.data));
      }
    });
  }, []);

  return (
    <div>
      <h1>Compliance & Risk Analysis</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Automated detection of non-negotiable compliance traps and certification gaps.</p>

      {selected && (
        <div className="card">
          <h3>Tender: {selected.title}</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Issuer: {selected.organization}</p>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-label">Overall Fit Score</span>
              <span className="metric-value">{selected.fit_score || 0}%</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Total Requirements</span>
              <span className="metric-value">{selected.requirements.length}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProposalGenerator() {
  const [tenders, setTenders] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const loadTender = async (id) => {
    try {
      const res = await axios.get(`${API_BASE}/tenders/${id}`);
      setProposal(res.data.proposal);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    axios.get(`${API_BASE}/tenders/`).then(res => {
      setTenders(res.data);
      if (res.data.length > 0) {
        setSelectedId(res.data[0].id);
        loadTender(res.data[0].id);
      }
    });
  }, []);

  const handleGenerate = async () => {
    if (!selectedId) return;
    setLoading(true);
    setMsg("");
    try {
      const res = await axios.post(`${API_BASE}/tenders/${selectedId}/proposal`);
      setMsg("Proposal generated successfully using GenAI!");
      await loadTender(selectedId);
    } catch (e) {
      setMsg("Generation failed: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Multi-Agent Proposal Generator</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
        Generates evidence-backed proposals using Gemini 1.5 with zero-hallucination ground truth citations.
      </p>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '2rem' }}>
        <label style={{ fontWeight: 600 }}>Select Tender:</label>
        <select
          value={selectedId || ""}
          onChange={e => {
            const id = Number(e.target.value);
            setSelectedId(id);
            loadTender(id);
          }}
          style={{ padding: '0.5rem 1rem', borderRadius: '0.25rem', border: '1px solid var(--border)' }}
        >
          {tenders.map(t => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </select>
        <button className="btn" onClick={handleGenerate} disabled={loading}>
          {loading ? <><Loader2 className="spinner" size={18} /> Drafting via GenAI...</> : <><PenTool size={18} /> Generate Grounded Proposal</>}
        </button>
      </div>

      {msg && <p style={{ color: 'var(--success)', fontWeight: 500, marginBottom: '1rem' }}>{msg}</p>}

      {proposal ? (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Draft Proposal Document</h3>
            <span className="status-badge SATISFIED">Status: {proposal.status}</span>
          </div>
          <textarea
            value={proposal.full_content || ""}
            onChange={e => setProposal({ ...proposal, full_content: e.target.value })}
            style={{ minHeight: '400px', width: '100%', fontFamily: 'monospace', fontSize: '0.95rem', padding: '1rem' }}
          />
        </div>
      ) : (
        <div className="card" style={{ color: 'var(--text-muted)' }}>
          No proposal drafted yet for this tender. Click "Generate Grounded Proposal" to trigger the GenAI Drafter Agent.
        </div>
      )}
    </div>
  );
}

function ReviewApproval() {
  const [tenders, setTenders] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [tender, setTender] = useState(null);
  const [companyProfile, setCompanyProfile] = useState(null);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [reviewResult, setReviewResult] = useState(null);
  const [reviewing, setReviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitMsg, setSubmitMsg] = useState("");

  const loadProfile = async () => {
    try {
      const res = await axios.get(`${API_BASE}/company/profile`);
      setCompanyProfile(res.data);
    } catch (e) {
      console.error("Failed to load company profile", e);
    }
  };

  const loadData = async (id) => {
    try {
      const res = await axios.get(`${API_BASE}/tenders/${id}`);
      setTender(res.data);
      setRecipientEmail(res.data.issuer_email || "");
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadProfile();
    axios.get(`${API_BASE}/tenders/`).then(res => {
      setTenders(res.data);
      if (res.data.length > 0) {
        setSelectedId(res.data[0].id);
        loadData(res.data[0].id);
      }
    });
  }, []);

  const handleReview = async () => {
    setReviewing(true);
    setSubmitMsg("");
    try {
      const res = await axios.post(`${API_BASE}/tenders/${selectedId}/proposal/review`);
      setReviewResult(res.data);
      await loadData(selectedId);
    } catch (e) {
      alert("Review failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setReviewing(false);
    }
  };

  const handleApproveAndSubmit = async () => {
    if (!companyProfile?.email) {
      return alert("Please register your company email in Company Profile before submitting.");
    }
    if (!recipientEmail.trim()) {
      return alert("Please provide the target organization's bid submission email.");
    }

    setSubmitting(true);
    setSubmitMsg("");
    try {
      const res = await axios.post(`${API_BASE}/tenders/${selectedId}/proposal/submit`, {
        recipient_email: recipientEmail.trim(),
        notes: "Approved by Senior Bid Director"
      });
      setSubmitMsg(res.data.message);
      await loadData(selectedId);
    } catch (e) {
      setSubmitMsg("Submission failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1>Human-in-the-Loop Review & Approval Gate</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
        Anti-hallucination verification agent checks claims, followed by 1-click email submission to the issuing authority.
      </p>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '2rem' }}>
        <label style={{ fontWeight: 600 }}>Select Tender:</label>
        <select
          value={selectedId || ""}
          onChange={e => {
            const id = Number(e.target.value);
            setSelectedId(id);
            loadData(id);
          }}
          style={{ padding: '0.5rem 1rem', borderRadius: '0.25rem', border: '1px solid var(--border)' }}
        >
          {tenders.map(t => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </select>
      </div>

      {tender && tender.proposal ? (
        <>
          <div className="card" style={{ marginBottom: '2rem' }}>
            <h3>1. AI Anti-Hallucination Review Agent</h3>
            <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 1rem' }}>
              Cross-examines each proposal statement against company pgvector document chunks.
            </p>
            <button className="btn" onClick={handleReview} disabled={reviewing}>
              {reviewing ? <><Loader2 className="spinner" size={18} /> Auditing Evidence Claims...</> : <><ShieldCheck size={18} /> Run Fact-Checker Agent</>}
            </button>

            {reviewResult && (
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: reviewResult.passed ? '#f0fdf4' : '#fff1f2', borderLeft: `4px solid ${reviewResult.passed ? 'var(--success)' : 'var(--danger)'}`, borderRadius: '0.25rem' }}>
                <h4>Audit Result: Score {reviewResult.review_score}/100 ({reviewResult.passed ? "PASSED" : "FLAGS DETECTED"})</h4>
                <p style={{ marginTop: '0.5rem' }}>Recommendations: {reviewResult.recommendations.join("; ")}</p>
              </div>
            )}
          </div>

          <div className="card">
            <h3>2. Human Final Approval & Automated Dispatch</h3>

            <div style={{ margin: '1.25rem 0', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Dynamic Sender Display */}
              <div>
                <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '0.3rem' }}>
                  From (Your Registered Company):
                </label>
                <div style={{ padding: '0.6rem 0.8rem', background: '#f8fafc', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '0.9rem' }}>
                  {companyProfile?.email ? (
                    <span><strong>{companyProfile.name}</strong> &lt;{companyProfile.email}&gt;</span>
                  ) : (
                    <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                      ⚠️ No company email registered! Go to "Company Documents" tab to register your company email.
                    </span>
                  )}
                </div>
              </div>

              {/* Dynamic Recipient Input */}
              <div>
                <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '0.3rem' }}>
                  To (Issuing Authority Bid Email):
                </label>
                <input
                  type="email"
                  value={recipientEmail}
                  onChange={e => setRecipientEmail(e.target.value)}
                  placeholder="Enter organization procurement email"
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '0.9rem', fontWeight: 500 }}
                />
                {!recipientEmail && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--danger)', marginTop: '0.25rem', display: 'block' }}>
                    Tender notice did not provide an email. Please input the official submission email.
                  </span>
                )}
              </div>

              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Current Proposal Status: <strong>{tender.proposal.status}</strong>
              </div>
            </div>

            <button
              className="btn btn-success"
              onClick={handleApproveAndSubmit}
              disabled={submitting || !recipientEmail || !companyProfile?.email}
            >
              {submitting ? <><Loader2 className="spinner" size={18} /> Dispatching Email...</> : <><Send size={18} /> Approve & Submit Proposal via Email</>}
            </button>
            {submitMsg && (
              <p style={{ color: submitMsg.includes('failed') || submitMsg.includes('error') ? 'var(--danger)' : 'var(--success)', marginTop: '1rem', fontWeight: 600 }}>
                {submitMsg}
              </p>
            )}
          </div>
        </>
      ) : (
        <div className="card" style={{ color: 'var(--text-muted)' }}>
          Please generate a proposal for this tender first before running review and approval.
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<TenderUpload />} />
            <Route path="/documents" element={<CompanyDocuments />} />
            <Route path="/matches" element={<MatchReport />} />
            <Route path="/compliance" element={<ComplianceReport />} />
            <Route path="/proposal" element={<ProposalGenerator />} />
            <Route path="/review" element={<ReviewApproval />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
