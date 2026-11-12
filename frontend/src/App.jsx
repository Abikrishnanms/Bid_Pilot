import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useNavigate, useSearchParams, Navigate } from 'react-router-dom';
import axios from 'axios';
import {
  Briefcase, LayoutDashboard, UploadCloud, FileText, CheckCircle,
  PenTool, ShieldCheck, File, Loader2, Check, AlertTriangle,
  RefreshCw, Send, CheckCircle2, XCircle, Trash2, Eye,
  Building2, ArrowRight, ArrowLeft, Copy, Layers, ExternalLink
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

function Sidebar() {
  const navItems = [
    { path: "/", icon: <LayoutDashboard size={20} />, label: "Dashboard & Pipeline" },
    { path: "/workspace", icon: <Layers size={20} />, label: "Tender Workspace" },
    { path: "/company", icon: <Building2 size={20} />, label: "Company Profile & Docs" },
  ];

  return (
    <div className="sidebar">
      <h2><Briefcase size={28} /> BidPilot</h2>
      <div className="nav-links">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
          >
            {item.icon} {item.label}
          </NavLink>
        ))}
      </div>
      <div style={{ marginTop: 'auto', padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.2rem' }}>AI Autonomous Core</div>
        <div>Gemini 3.5 & pgvector</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.4rem', color: 'var(--success)' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', display: 'inline-block' }}></span>
          <span>Pipeline Active</span>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 1. EXECUTIVE DASHBOARD & PIPELINE
// ==========================================
function Dashboard() {
  const navigate = useNavigate();
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
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [msg, setMsg] = useState("");
  const [uploadMsg, setUploadMsg] = useState("");

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
      await loadData();
      navigate(`/workspace?id=${res.data.id || ''}`);
    } catch (err) {
      setUploadMsg("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploadingPdf(false);
      e.target.value = null;
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>Executive Dashboard</h1>
          <p style={{ color: 'var(--text-muted)' }}>
            Real-time procurement feed intelligence, pgvector capability matching, and automated bid generation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button className="btn" onClick={handleAutoFetch} disabled={fetching}>
            {fetching ? <><Loader2 className="spinner" size={18} /> Polling Feeds...</> : <><RefreshCw size={18} /> Ingest Live Gov Feeds</>}
          </button>
          <label className="btn btn-secondary" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', cursor: uploadingPdf ? 'not-allowed' : 'pointer', margin: 0 }}>
            {uploadingPdf ? <><Loader2 className="spinner" size={18} /> Parsing PDF...</> : <><UploadCloud size={18} /> Upload RFP PDF</>}
            <input
              type="file"
              accept=".pdf"
              onChange={handleUploadTenderPdf}
              disabled={uploadingPdf}
              style={{ display: 'none' }}
            />
          </label>
        </div>
      </div>

      {msg && <div className="card" style={{ background: '#f0fdf4', borderLeft: '4px solid var(--success)', padding: '0.8rem', marginBottom: '1.5rem' }}>{msg}</div>}
      {uploadMsg && <div className="card" style={{ background: '#f0fdf4', borderLeft: '4px solid var(--success)', padding: '0.8rem', marginBottom: '1.5rem' }}>{uploadMsg}</div>}

      {/* KPI Cards */}
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

      {/* Tender Pipeline Table */}
      <div className="card" style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3>Active Tender Pipeline ({tenders.length})</h3>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Click any tender to open its end-to-end AI qualification, proposal draft, and email dispatch workspace.
            </span>
          </div>
        </div>

        {tenders.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', padding: '1rem 0' }}>
            No tenders discovered yet. Click "Ingest Live Gov Feeds" to poll public notices or "Upload RFP PDF".
          </p>
        ) : (
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)', paddingBottom: '0.5rem' }}>
                <th style={{ padding: '0.75rem 0.5rem' }}>Tender Opportunity</th>
                <th>Estimated Budget</th>
                <th>Fit Score</th>
                <th>Triage Decision</th>
                <th>Proposal</th>
                <th>Outcome</th>
                <th style={{ textAlign: 'right' }}>Workspace</th>
              </tr>
            </thead>
            <tbody>
              {tenders.map((t) => (
                <tr key={t.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '0.75rem 0.5rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{t.title}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                      Issuer: <strong>{t.organization || 'Public Sector'}</strong> &bull; Ref: {t.reference_id ? t.reference_id.slice(0, 24) + '...' : `TEN-${t.id}`}
                    </div>
                  </td>
                  <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{t.estimated_value || 'TBD'}</td>
                  <td>
                    <span style={{ fontWeight: 700, color: t.fit_score >= 70 ? 'var(--success)' : t.fit_score >= 50 ? 'var(--warning)' : 'var(--danger)' }}>
                      {t.fit_score !== null ? `${t.fit_score}%` : 'Pending'}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${t.status === 'WON' || t.status === 'PROPOSAL_READY' || t.status === 'SUBMITTED' ? 'SATISFIED' : t.status === 'NO_GO' || t.status === 'LOST' ? 'NOT_SATISFIED' : 'PARTIALLY_SATISFIED'}`}>
                      {t.status === 'PROPOSAL_READY' ? 'GO (Qualified)' : t.status}
                    </span>
                  </td>
                  <td>
                    {t.has_proposal ? (
                      <span style={{ color: 'var(--success)', fontWeight: 500, fontSize: '0.85rem' }}>
                        <Check size={15} style={{ verticalAlign: 'middle' }} /> {t.proposal_status || 'Drafted'}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>None</span>
                    )}
                  </td>
                  <td>
                    {t.status === 'SUBMITTED' ? (
                      <div style={{ display: 'flex', gap: '0.3rem' }}>
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
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>In Pipeline</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-sm btn-outline"
                      onClick={() => navigate(`/workspace?id=${t.id}`)}
                    >
                      Open Workspace <ArrowRight size={14} style={{ verticalAlign: 'middle', marginLeft: '0.2rem' }} />
                    </button>
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

// ==========================================
// 2. UNIFIED TENDER WORKSPACE (ALL-IN-ONE)
// ==========================================
function TenderWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const tenderIdParam = searchParams.get('id');

  const [tenders, setTenders] = useState([]);
  const [selectedTenderId, setSelectedTenderId] = useState(tenderIdParam ? Number(tenderIdParam) : null);
  const [tender, setTender] = useState(null);
  const [activeTab, setActiveTab] = useState("triage"); // "triage" | "proposal" | "review"

  // Company profile for sender
  const [companyProfile, setCompanyProfile] = useState(null);

  // Agent execution states
  const [loadingTender, setLoadingTender] = useState(false);
  const [triageLoading, setTriageLoading] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  // Outputs
  const [proposalText, setProposalText] = useState("");
  const [reviewResult, setReviewResult] = useState(null);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [msg, setMsg] = useState("");
  const [copied, setCopied] = useState(false);

  // Load tenders catalog
  const loadTendersList = async () => {
    try {
      const res = await axios.get(`${API_BASE}/tenders/`);
      setTenders(res.data);
      if (res.data.length > 0 && !selectedTenderId) {
        setSelectedTenderId(res.data[0].id);
      }
    } catch (e) {
      console.error("Failed to load tenders list", e);
    }
  };

  const loadCompanyProfile = async () => {
    try {
      const res = await axios.get(`${API_BASE}/company/profile`);
      setCompanyProfile(res.data);
    } catch (e) {
      console.error("Failed to load company profile", e);
    }
  };

  const loadTenderDetail = async (id) => {
    if (!id) return;
    setLoadingTender(true);
    setMsg("");
    try {
      const res = await axios.get(`${API_BASE}/tenders/${id}`);
      setTender(res.data);
      setRecipientEmail(res.data.issuer_email || "");
      if (res.data.proposal) {
        setProposalText(res.data.proposal.full_content || "");
      } else {
        setProposalText("");
      }
      if (res.data.proposal?.review_notes) {
        try {
          const parsed = JSON.parse(res.data.proposal.review_notes);
          setReviewResult(parsed);
        } catch {
          // simple string note
        }
      }
    } catch (e) {
      console.error(e);
      setMsg("Failed to load tender details: " + e.message);
    } finally {
      setLoadingTender(false);
    }
  };

  useEffect(() => {
    loadTendersList();
    loadCompanyProfile();
  }, []);

  useEffect(() => {
    if (tenderIdParam) {
      setSelectedTenderId(Number(tenderIdParam));
    }
  }, [tenderIdParam]);

  useEffect(() => {
    if (selectedTenderId) {
      setSearchParams({ id: selectedTenderId });
      loadTenderDetail(selectedTenderId);
    }
  }, [selectedTenderId]);

  // Actions
  const handleRunTriage = async () => {
    if (!selectedTenderId) return;
    setTriageLoading(true);
    setMsg("");
    try {
      await axios.post(`${API_BASE}/tenders/${selectedTenderId}/triage?force_refresh=true`);
      setMsg("AI Qualification & Evidence Matching complete!");
      await loadTenderDetail(selectedTenderId);
    } catch (e) {
      setMsg("Triage failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setTriageLoading(false);
    }
  };

  const handleGenerateProposal = async () => {
    if (!selectedTenderId) return;
    setDraftLoading(true);
    setMsg("");
    try {
      const res = await axios.post(`${API_BASE}/tenders/${selectedTenderId}/proposal`);
      setMsg("Proposal generated successfully with pgvector citations!");
      await loadTenderDetail(selectedTenderId);
      setActiveTab("proposal");
    } catch (e) {
      setMsg("Draft generation failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setDraftLoading(false);
    }
  };

  const handleReviewProposal = async () => {
    if (!selectedTenderId) return;
    setReviewLoading(true);
    setMsg("");
    try {
      const res = await axios.post(`${API_BASE}/tenders/${selectedTenderId}/proposal/review`);
      setReviewResult(res.data);
      setMsg("Anti-hallucination verification audit completed!");
      await loadTenderDetail(selectedTenderId);
    } catch (e) {
      setMsg("Fact-check audit failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setReviewLoading(false);
    }
  };

  const handleApproveAndSubmit = async () => {
    if (!companyProfile?.email) {
      return alert("Please register your company email in Company Profile before submitting.");
    }
    if (!recipientEmail.trim()) {
      return alert("Please enter the issuing authority's procurement submission email.");
    }

    setSubmitLoading(true);
    setMsg("");
    try {
      const res = await axios.post(`${API_BASE}/tenders/${selectedTenderId}/proposal/submit`, {
        recipient_email: recipientEmail.trim(),
        notes: "Approved by Senior Bid Director"
      });
      setMsg(res.data.message);
      await loadTenderDetail(selectedTenderId);
    } catch (e) {
      setMsg("Submission failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleUpdateOutcome = async (newStatus) => {
    try {
      await axios.patch(`${API_BASE}/tenders/${selectedTenderId}/status`, { status: newStatus });
      await loadTenderDetail(selectedTenderId);
      setMsg(`Bid status updated to ${newStatus}`);
    } catch (e) {
      alert("Failed to update status: " + e.message);
    }
  };

  const handleCopyProposal = () => {
    if (!proposalText) return;
    navigator.clipboard.writeText(proposalText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      {/* Top Bar with Tender Switcher */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>Tender Opportunity Workspace</h1>
          <p style={{ color: 'var(--text-muted)' }}>
            Single-screen AI lifecycle: verify compliance, draft evidence proposal, fact-check, and dispatch email.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Switch Tender:</label>
          <select
            value={selectedTenderId || ""}
            onChange={e => setSelectedTenderId(Number(e.target.value))}
            style={{ padding: '0.5rem 1rem', borderRadius: '4px', border: '1px solid var(--border)', maxWidth: '300px' }}
          >
            {tenders.map(t => (
              <option key={t.id} value={t.id}>
                {t.title.slice(0, 35)}... ({t.reference_id ? t.reference_id.slice(0, 10) : `TEN-${t.id}`})
              </option>
            ))}
          </select>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate("/")}>
            &larr; Back to Pipeline
          </button>
        </div>
      </div>

      {loadingTender && <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}><Loader2 className="spinner" size={16} /> Loading tender opportunity...</p>}

      {tender && (
        <>
          {/* Tender Opportunity Header Banner */}
          <div className="tender-header-banner">
            <div style={{ flex: 1, paddingRight: '1rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.3rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, background: '#e2e8f0', color: '#334155', padding: '0.15rem 0.5rem', borderRadius: '4px' }}>
                  {tender.reference_id || `TEN-${tender.id}`}
                </span>
                <span className={`status-badge ${tender.status === 'WON' || tender.status === 'PROPOSAL_READY' || tender.status === 'SUBMITTED' ? 'SATISFIED' : tender.status === 'NO_GO' || tender.status === 'LOST' ? 'NOT_SATISFIED' : 'PARTIALLY_SATISFIED'}`}>
                  {tender.status === 'PROPOSAL_READY' ? 'GO (Qualified)' : tender.status}
                </span>
              </div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.4rem' }}>
                {tender.title}
              </h2>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                <span>Issuing Authority: <strong>{tender.organization || 'Public Agency'}</strong></span>
                <span>Budget: <strong>{tender.estimated_value || 'Commercial TBD'}</strong></span>
                <span>Deadline: <strong>{tender.deadline || 'Standard Notice'}</strong></span>
                <span>Submission Email: <strong>{tender.issuer_email || 'Enter in Review stage'}</strong></span>
              </div>
            </div>

            <div style={{ textAlign: 'right', minWidth: '160px', borderLeft: '1px solid var(--border)', paddingLeft: '1.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Bid Readiness</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: tender.fit_score >= 70 ? 'var(--success)' : tender.fit_score >= 50 ? 'var(--warning)' : 'var(--danger)' }}>
                {tender.fit_score !== null ? `${tender.fit_score}%` : 'Pending'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {tender.requirements?.length || 0} requirements analyzed
              </div>
            </div>
          </div>

          {msg && (
            <div className="card" style={{ background: '#f0fdf4', borderLeft: '4px solid var(--success)', padding: '0.8rem', marginBottom: '1.5rem' }}>
              {msg}
            </div>
          )}

          {/* Unified 3-Stage Tabs */}
          <div className="tabs-container">
            <button
              className={`tab-btn ${activeTab === 'triage' ? 'active' : ''}`}
              onClick={() => setActiveTab('triage')}
            >
              <span>1. Triage & Compliance Evidence</span>
              <span className="tab-badge">{tender.requirements?.length || 0} Req</span>
            </button>
            <button
              className={`tab-btn ${activeTab === 'proposal' ? 'active' : ''}`}
              onClick={() => setActiveTab('proposal')}
            >
              <span>2. AI Proposal Drafter</span>
              <span className="tab-badge">{tender.proposal ? 'Drafted' : 'Pending'}</span>
            </button>
            <button
              className={`tab-btn ${activeTab === 'review' ? 'active' : ''}`}
              onClick={() => setActiveTab('review')}
            >
              <span>3. Anti-Hallucination & Dispatch</span>
              <span className="tab-badge">{tender.status === 'SUBMITTED' ? 'Sent' : 'Ready'}</span>
            </button>
          </div>

          {/* ======================================= */}
          {/* STAGE 1: TRIAGE & REQUIREMENT CITATIONS */}
          {/* ======================================= */}
          {activeTab === 'triage' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                  <h3>Requirement-by-Requirement Evidence Citations</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    Each tender requirement is cross-matched with your company documents in pgvector.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button className="btn" onClick={handleRunTriage} disabled={triageLoading}>
                    {triageLoading ? <><Loader2 className="spinner" size={16} /> Evaluating...</> : <><RefreshCw size={16} /> Re-run AI Triage</>}
                  </button>
                  <button className="btn btn-outline" onClick={() => setActiveTab('proposal')}>
                    Next: Draft Proposal &rarr;
                  </button>
                </div>
              </div>

              {(!tender.requirements || tender.requirements.length === 0) ? (
                <div className="card" style={{ color: 'var(--text-muted)' }}>
                  No requirements extracted for this tender yet. Click "Re-run AI Triage" to evaluate.
                </div>
              ) : (
                tender.requirements.map((req, idx) => (
                  <div key={idx} className="card" style={{ marginBottom: '1rem', borderLeft: `4px solid ${req.status === 'SATISFIED' ? 'var(--success)' : req.status === 'PARTIALLY_SATISFIED' ? 'var(--warning)' : 'var(--danger)'}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                      <h4 style={{ fontSize: '1rem' }}>{req.description}</h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                        {req.top_similarity !== null && req.top_similarity !== undefined && (
                          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', background: '#f1f5f9', padding: '0.2rem 0.45rem', borderRadius: '4px' }}>
                            RAG Sim: {Math.round(req.top_similarity * 100)}%
                          </span>
                        )}
                        <span className={`status-badge ${req.status}`}>{req.status.replace("_", " ")}</span>
                      </div>
                    </div>
                    <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                      <strong>AI Analysis:</strong> {req.explanation || "Evaluated by pgvector cosine search against company ground truth"}
                    </p>
                    {req.evidence && (
                      <div className="evidence-box">
                        <strong>Cited Company Evidence:</strong> {req.evidence}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* ======================================= */}
          {/* STAGE 2: PROPOSAL DRAFTER              */}
          {/* ======================================= */}
          {activeTab === 'proposal' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <h3>Evidence-Grounded Bid Proposal</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    Multi-section proposal drafted by Gemini strictly grounded in your cited company evidence.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <button className="btn" onClick={handleGenerateProposal} disabled={draftLoading}>
                    {draftLoading ? <><Loader2 className="spinner" size={16} /> Drafting with GenAI...</> : <><PenTool size={16} /> {tender.proposal ? 'Regenerate Draft' : 'Draft Proposal with GenAI'}</>}
                  </button>
                  {proposalText && (
                    <>
                      <button className="btn btn-secondary btn-sm" onClick={handleCopyProposal}>
                        <Copy size={14} /> {copied ? 'Copied!' : 'Copy Text'}
                      </button>
                      <button className="btn btn-outline" onClick={() => setActiveTab('review')}>
                        Next: Review & Submit &rarr;
                      </button>
                    </>
                  )}
                </div>
              </div>

              {proposalText ? (
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                      Proposal Content &bull; Status: <strong style={{ color: 'var(--primary)' }}>{tender.proposal?.status || 'DRAFT'}</strong>
                    </span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      You can edit the draft directly before running fact-check
                    </span>
                  </div>
                  <textarea
                    value={proposalText}
                    onChange={e => setProposalText(e.target.value)}
                    style={{ minHeight: '450px', width: '100%', fontFamily: 'monospace', fontSize: '0.9rem', padding: '1rem', lineHeight: '1.6' }}
                  />
                </div>
              ) : (
                <div className="card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                  <PenTool size={40} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} />
                  <h4>No Proposal Drafted Yet</h4>
                  <p style={{ color: 'var(--text-muted)', margin: '0.5rem auto 1.5rem', maxWidth: '450px' }}>
                    The Proposal Drafter Agent uses Gemini to synthesize the buyer's RFP specifications and your indexed vector evidence into 4 comprehensive sections.
                  </p>
                  <button className="btn" onClick={handleGenerateProposal} disabled={draftLoading}>
                    {draftLoading ? <><Loader2 className="spinner" size={16} /> Drafting with GenAI...</> : "Draft Proposal with GenAI"}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ======================================= */}
          {/* STAGE 3: REVIEW & EMAIL DISPATCH       */}
          {/* ======================================= */}
          {activeTab === 'review' && (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                {/* 1. Fact-Checker Agent Card */}
                <div className="card">
                  <h3>1. Anti-Hallucination Audit</h3>
                  <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 1rem', fontSize: '0.9rem' }}>
                    Adversarially cross-examines proposal claims against ground-truth company text chunks.
                  </p>
                  <button className="btn" onClick={handleReviewProposal} disabled={reviewLoading || !proposalText}>
                    {reviewLoading ? <><Loader2 className="spinner" size={16} /> Auditing Claims...</> : <><ShieldCheck size={16} /> Run Fact-Checker Agent</>}
                  </button>

                  {reviewResult && (
                    <div style={{ marginTop: '1.25rem', padding: '1rem', background: reviewResult.passed ? '#f0fdf4' : '#fff1f2', borderLeft: `4px solid ${reviewResult.passed ? 'var(--success)' : 'var(--danger)'}`, borderRadius: '4px' }}>
                      <div style={{ fontWeight: 700, color: reviewResult.passed ? 'var(--success)' : 'var(--danger)' }}>
                        Audit Result: {reviewResult.review_score}/100 ({reviewResult.passed ? "PASSED" : "FLAGS DETECTED"})
                      </div>
                      <p style={{ marginTop: '0.4rem', fontSize: '0.85rem' }}>
                        <strong>Findings:</strong> {reviewResult.recommendations?.join("; ") || "All claims verified against vector chunks."}
                      </p>
                    </div>
                  )}
                </div>

                {/* 2. Email Dispatch Station */}
                <div className="card">
                  <h3>2. Automated Submission Dispatch</h3>
                  <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 1rem', fontSize: '0.9rem' }}>
                    Sends the verified proposal directly from your company to the official buyer email.
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>From (Registered Company):</label>
                      <div style={{ padding: '0.5rem 0.75rem', background: '#f8fafc', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '0.85rem', marginTop: '0.2rem' }}>
                        {companyProfile?.email ? (
                          <span><strong>{companyProfile.name}</strong> &lt;{companyProfile.email}&gt;</span>
                        ) : (
                          <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                            ⚠️ Register sender email in "Company Profile"
                          </span>
                        )}
                      </div>
                    </div>

                    <div>
                      <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>To (Issuing Authority Bid Email):</label>
                      <input
                        type="email"
                        value={recipientEmail}
                        onChange={e => setRecipientEmail(e.target.value)}
                        placeholder="e.g. procurement@stalbans.gov.uk"
                        style={{ marginTop: '0.2rem', marginBottom: 0, padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}
                      />
                    </div>
                  </div>

                  <button
                    className="btn btn-success"
                    onClick={handleApproveAndSubmit}
                    disabled={submitLoading || !recipientEmail || !companyProfile?.email || !proposalText}
                    style={{ width: '100%', justifyContent: 'center' }}
                  >
                    {submitLoading ? <><Loader2 className="spinner" size={16} /> Dispatching...</> : <><Send size={16} /> Approve & Dispatch Proposal via Email</>}
                  </button>

                  {tender.status === 'SUBMITTED' && (
                    <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Tender Status: Awarded?</span>
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button className="btn btn-sm" style={{ background: '#22c55e', color: '#fff' }} onClick={() => handleUpdateOutcome('WON')}>Mark Won 🏆</button>
                        <button className="btn btn-sm" style={{ background: '#ef4444', color: '#fff' }} onClick={() => handleUpdateOutcome('LOST')}>Mark Lost ❌</button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ==========================================
// 3. COMPANY KNOWLEDGE BASE & PROFILE
// ==========================================
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

  // File upload state
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [selectedChunks, setSelectedChunks] = useState(null);
  const [selectedDocTitle, setSelectedDocTitle] = useState("");

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
      await axios.post(`${API_BASE}/company/profile`, {
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
    setSelectedDocTitle(title);
    try {
      const res = await axios.get(`${API_BASE}/company/documents/${id}/chunks`);
      setSelectedChunks(res.data);
    } catch (err) {
      alert("Failed to load chunks: " + err.message);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>Company Profile & Knowledge Base</h1>
          <p style={{ color: 'var(--text-muted)' }}>
            Register your official sender identity and index real capability documents into pgvector for evidence matching.
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
              placeholder="e.g. procurement-team@apexinnovations.com"
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

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1.5rem', padding: '1rem', background: '#f8fafc', borderRadius: '6px', border: '1px dashed var(--border)', flexWrap: 'wrap' }}>
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
            Automatically parsed via pdfplumber and embedded with all-MiniLM-L6-v2 into PostgreSQL pgvector.
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
                        className="btn btn-sm"
                        style={{ background: '#f1f5f9', color: '#334155' }}
                        onClick={() => handleViewChunks(d.id, d.filename)}
                      >
                        <Eye size={14} style={{ verticalAlign: 'middle' }} /> View Chunks
                      </button>
                      <button
                        className="btn btn-sm"
                        style={{ background: '#fee2e2', color: '#b91c1c' }}
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

      {/* Vector Chunks Inspector */}
      {selectedChunks && (
        <div className="card" style={{ marginTop: '2rem', border: '2px solid var(--primary)', background: '#f8fafc' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Vector Chunks for: <em>{selectedDocTitle}</em> ({selectedChunks.length} chunks)</h3>
            <button className="btn btn-sm" onClick={() => setSelectedChunks(null)}>Close</button>
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

// ==========================================
// MAIN APP ROUTER (CLEAN 3 VIEWS)
// ==========================================
function App() {
  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            {/* 3 Core Clean Views */}
            <Route path="/" element={<Dashboard />} />
            <Route path="/workspace" element={<TenderWorkspace />} />
            <Route path="/company" element={<CompanyDocuments />} />

            {/* Seamless backward-compatibility redirects */}
            <Route path="/upload" element={<Navigate to="/" replace />} />
            <Route path="/matches" element={<Navigate to="/workspace" replace />} />
            <Route path="/compliance" element={<Navigate to="/workspace" replace />} />
            <Route path="/proposal" element={<Navigate to="/workspace" replace />} />
            <Route path="/review" element={<Navigate to="/workspace" replace />} />
            <Route path="/documents" element={<Navigate to="/company" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
