import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { 
  Briefcase, LayoutDashboard, Upload, FileText, BarChart2, 
  CheckCircle, Search, PenTool, ShieldCheck, File,
  Loader2, Check, AlertTriangle, Download
} from 'lucide-react';

const API_URL = "http://localhost:8000/api/tenders";

// --- State Context (Mocking a global store for prototype) ---
let globalState = {
  tender_data: null,
  tender_id: null,
  match_results: null,
  compliance_report: null,
  proposal_draft: null,
  approval_status: "Pending"
};

function Sidebar() {
  const navItems = [
    { path: "/", icon: <LayoutDashboard size={20} />, label: "Dashboard" },
    { path: "/upload", icon: <Upload size={20} />, label: "Tender Upload" },
    { path: "/documents", icon: <FileText size={20} />, label: "Company Documents" },
    { path: "/matches", icon: <BarChart2 size={20} />, label: "Match Report" },
    { path: "/compliance", icon: <CheckCircle size={20} />, label: "Compliance Report" },
    { path: "/research", icon: <Search size={20} />, label: "Research" },
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
            className={({isActive}) => isActive ? "nav-link active" : "nav-link"}
          >
            {item.icon} {item.label}
          </NavLink>
        ))}
      </div>
    </div>
  );
}

function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
        Welcome to BidPilot. Navigate through the tender processing workflow using the sidebar.
      </p>
      
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Active Tenders</span>
          <span className="metric-value">{globalState.tender_data ? "1" : "0"}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Company Documents</span>
          <span className="metric-value">3</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Pending Approvals</span>
          <span className="metric-value">{globalState.approval_status === "Approved" ? "0" : "1"}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Success Rate</span>
          <span className="metric-value">85%</span>
        </div>
      </div>
    </div>
  );
}

function TenderUpload() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(globalState.tender_data);
  const [error, setError] = useState(null);

  const handleProcess = async () => {
    if (!file) {
      setError("Please select a file.");
      return;
    }
    setLoading(true);
    setError(null);
    
    setTimeout(() => {
      // Mocking the extraction response
      const mockData = {
        title: "IT Infrastructure Overhaul",
        organization: "GovTech Agency",
        estimated_value: "$5,000,000",
        deadline: "2026-11-01",
        technical_requirements: [
          "10+ years cloud experience",
          "ISO 27001 Certification"
        ]
      };
      globalState.tender_data = mockData;
      globalState.tender_id = 1;
      setData(mockData);
      setLoading(false);
    }, 2000);
  };

  return (
    <div>
      <h1>Upload Tender</h1>
      <div className="card">
        <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} />
        <button className="btn" onClick={handleProcess} disabled={loading}>
          {loading ? <><Loader2 className="spinner" size={20}/> Processing...</> : "Extract Requirements"}
        </button>
        {error && <p style={{color: 'var(--danger)', marginTop: '1rem'}}>{error}</p>}
      </div>

      {data && (
        <div>
          <h2>Extracted Metadata</h2>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-label">Estimated Value</span>
              <span className="metric-value" style={{fontSize: '1.5rem'}}>{data.estimated_value || 'N/A'}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Deadline</span>
              <span className="metric-value" style={{fontSize: '1.5rem'}}>{data.deadline || 'N/A'}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Organization</span>
              <span className="metric-value" style={{fontSize: '1.5rem'}}>{data.organization || 'N/A'}</span>
            </div>
          </div>
          <div className="card">
            <h3>Raw JSON</h3>
            <pre style={{background: '#f8f9fa', padding: '1rem', borderRadius: '0.25rem', overflowX: 'auto', border: '1px solid var(--border)'}}>
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

function CompanyDocuments() {
  const [loading, setLoading] = useState(false);
  const [docs, setDocs] = useState([
    { name: "Corporate_Profile_2026.pdf", status: "Indexed", chunks: 45 },
    { name: "ISO_9001_Certificate.pdf", status: "Indexed", chunks: 3 },
    { name: "Case_Study_Cloud_Migration.docx", status: "Indexed", chunks: 12 },
  ]);

  const handleUpload = () => {
    setLoading(true);
    setTimeout(() => {
      setDocs([{ name: "New_Capability_Statement.pdf", status: "Indexed", chunks: 25 }, ...docs]);
      setLoading(false);
    }, 1500);
  };

  return (
    <div>
      <h1>Company Documents & Evidence</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Upload company policies, case studies, and capability statements for RAG indexing.</p>
      
      <div className="card">
        <input type="file" />
        <button className="btn" onClick={handleUpload} disabled={loading}>
          {loading ? <><Loader2 className="spinner" size={20}/> Indexing Document...</> : "Index Document"}
        </button>
      </div>

      <div className="card" style={{padding: 0, overflow: 'hidden'}}>
        <table>
          <thead>
            <tr>
              <th>Document Name</th>
              <th>Status</th>
              <th>Chunks Indexed</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d, i) => (
              <tr key={i}>
                <td><File size={16} style={{display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle', color: 'var(--text-muted)'}}/> {d.name}</td>
                <td><span style={{color: 'var(--success)'}}><Check size={16} style={{verticalAlign: 'middle'}}/> {d.status}</span></td>
                <td>{d.chunks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MatchReport() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(globalState.match_results);

  const runMatching = () => {
    if (!globalState.tender_data) return alert("Please extract tender first");
    setLoading(true);
    setTimeout(() => {
      const mockResults = [
        {
          requirement: "10+ years cloud experience",
          status: "SATISFIED",
          explanation: "Company profile explicitly states 10+ years of cloud experience.",
          evidence: "Mock IT Solutions has over 10 years of experience in cloud infrastructure and DevOps."
        },
        {
          requirement: "ISO 27001 Certification",
          status: "NOT_SATISFIED",
          explanation: "No ISO 27001 certificate found in indexed documents.",
          evidence: "No relevant evidence retrieved."
        }
      ];
      globalState.match_results = mockResults;
      setResults(mockResults);
      setLoading(false);
    }, 2000);
  };

  return (
    <div>
      <h1>Match Report</h1>
      {!globalState.tender_data ? (
        <div className="card" style={{color: 'var(--warning)'}}><AlertTriangle size={20} style={{verticalAlign: 'middle'}}/> Please upload and process a tender first.</div>
      ) : (
        <>
          <button className="btn" onClick={runMatching} disabled={loading} style={{marginBottom: '2rem'}}>
            <Search size={20} /> {loading ? "Generating matches..." : "Run RAG Matching Agent"}
          </button>
          
          {results && results.map((m, i) => (
            <div key={i} className="card">
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem'}}>
                <h3 style={{fontWeight: 500}}>{m.requirement}</h3>
                <span className={`status-badge ${m.status}`}>{m.status.replace("_", " ")}</span>
              </div>
              <p style={{color: 'var(--text-muted)', marginBottom: '1rem'}}><strong>Explanation:</strong> {m.explanation}</p>
              <div className="evidence-box">
                <strong>Retrieved Evidence:</strong> <br/>
                {m.evidence}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function ComplianceReport() {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(globalState.compliance_report);

  const generateReport = () => {
    if (!globalState.match_results) return alert("Run matches first");
    setLoading(true);
    setTimeout(() => {
      const rep = {
        score: "50%",
        satisfied: 1,
        gaps: 1,
        risks: ["Missing ISO 27001 Certification - High Risk"]
      };
      globalState.compliance_report = rep;
      setReport(rep);
      setLoading(false);
    }, 1500);
  };

  return (
    <div>
      <h1>Compliance Report</h1>
      {!globalState.match_results ? (
         <div className="card" style={{color: 'var(--warning)'}}>Please generate a match report first.</div>
      ) : (
        <>
          <button className="btn" onClick={generateReport} disabled={loading} style={{marginBottom: '2rem'}}>
            {loading ? "Analyzing..." : "Generate Compliance Report"}
          </button>

          {report && (
            <div>
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-label">Bid Readiness Score</span>
                  <span className="metric-value">{report.score}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Satisfied Requirements</span>
                  <span className="metric-value" style={{color: 'var(--success)'}}>{report.satisfied}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">Identified Gaps</span>
                  <span className="metric-value" style={{color: 'var(--danger)'}}>{report.gaps}</span>
                </div>
              </div>
              <div className="card" style={{borderColor: 'rgba(220, 53, 69, 0.3)'}}>
                <h3 style={{color: 'var(--danger)', marginBottom: '1rem'}}>Identified Risks</h3>
                <ul style={{paddingLeft: '1.5rem', color: 'var(--danger)'}}>
                  {report.risks.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Research() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleResearch = () => {
    if (!query) return;
    setLoading(true);
    setTimeout(() => {
      setResult(`Research Summary for "${query}": The organization tends to prioritize security and local data residency in their evaluations based on 3 recent contract awards.`);
      setLoading(false);
    }, 1500);
  };

  return (
    <div>
      <h1>Contextual Research</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Gather additional context regarding the issuer, domain, and past tenders.</p>
      
      <div className="card">
        <input type="text" placeholder="Research Topic / Issuer Name" value={query} onChange={e => setQuery(e.target.value)} />
        <button className="btn" onClick={handleResearch} disabled={loading || !query}>
          <Search size={20} /> {loading ? "Researching..." : "Run Research Agent"}
        </button>
      </div>

      {result && (
        <div className="card" style={{borderLeft: '4px solid var(--info)', background: '#f0f9ff'}}>
          <h3 style={{color: 'var(--info)', marginBottom: '0.5rem'}}>Research Results</h3>
          <p>{result}</p>
        </div>
      )}
    </div>
  );
}

function ProposalGenerator() {
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState(globalState.proposal_draft || "");

  const generateDraft = () => {
    setLoading(true);
    setTimeout(() => {
      const txt = `# Executive Summary\nWe are pleased to submit this proposal for the requested IT infrastructure overhaul...\n\n# Technical Approach\nOur proposed solution meets technical requirements for cloud infrastructure.\n\n# Compliance Gaps\nWe note the requirement for ISO 27001 and are currently in the process of certification.`;
      globalState.proposal_draft = txt;
      setDraft(txt);
      setLoading(false);
    }, 2500);
  };

  return (
    <div>
      <h1>Proposal Generator</h1>
      {!globalState.compliance_report ? (
        <div className="card" style={{color: 'var(--warning)'}}>Please complete the compliance analysis first.</div>
      ) : (
        <>
          <button className="btn" onClick={generateDraft} disabled={loading} style={{marginBottom: '2rem'}}>
            <PenTool size={20} /> {loading ? "Compiling evidence..." : "Generate Proposal Draft"}
          </button>

          {draft && (
            <div className="card">
              <h3 style={{marginBottom: '1rem'}}>Edit Proposal Draft</h3>
              <textarea 
                value={draft} 
                onChange={e => {
                  setDraft(e.target.value);
                  globalState.proposal_draft = e.target.value;
                }}
                style={{minHeight: '300px', fontSize: '1rem'}}
              />
              <button className="btn btn-secondary">
                <Download size={20} /> Download Markdown
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ReviewApproval() {
  const [reviewing, setReviewing] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const navigate = useNavigate();

  const handleReview = () => {
    setReviewing(true);
    setTimeout(() => {
      setReviewed(true);
      setReviewing(false);
    }, 1500);
  };

  const handleDecision = (decision) => {
    globalState.approval_status = decision;
    navigate("/");
  };

  return (
    <div>
      <h1>Review & Human Approval</h1>
      {!globalState.proposal_draft ? (
        <div className="card" style={{color: 'var(--warning)'}}>Please generate a proposal draft first.</div>
      ) : (
        <>
          <div className="card">
            <h3 style={{marginBottom: '1rem'}}>AI Review Agent Analysis</h3>
            <button className="btn" onClick={handleReview} disabled={reviewing}>
              <ShieldCheck size={20} /> {reviewing ? "Analyzing claims..." : "Run Review Agent"}
            </button>
            {reviewed && (
              <div style={{marginTop: '1.5rem', padding: '1rem', background: '#e6f4ea', color: 'var(--success)', borderRadius: '0.25rem', borderLeft: '4px solid var(--success)'}}>
                <strong>Review Complete.</strong> No unsupported claims found. All statements are grounded in evidence.
              </div>
            )}
          </div>

          <div className="card">
            <h3 style={{marginBottom: '1rem'}}>Human Approval Decision</h3>
            <p style={{marginBottom: '1.5rem'}}>Current Status: <strong>{globalState.approval_status}</strong></p>
            <div style={{display: 'flex', gap: '1rem'}}>
              <button className="btn btn-success" onClick={() => handleDecision("Approved")}>
                <CheckCircle size={20} /> Approve Proposal
              </button>
              <button className="btn btn-danger" onClick={() => handleDecision("Rejected")}>
                <AlertTriangle size={20} /> Reject / Request Changes
              </button>
            </div>
          </div>
        </>
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
            <Route path="/research" element={<Research />} />
            <Route path="/proposal" element={<ProposalGenerator />} />
            <Route path="/review" element={<ReviewApproval />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
