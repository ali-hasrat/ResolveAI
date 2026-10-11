import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api").replace(/\/$/, "");

function App() {
  const [view, setView] = useState("customer");

  return (
    <div className="app">
      <Header view={view} setView={setView} />
      {view === "customer" ? <CustomerPortal /> : <SupportAgent />}
    </div>
  );
}

function Header({ view, setView }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand-area">
          <div className="brand-icon">R</div>
          <div>
            <div className="brand-name">ResolveAI</div>
            <div className="brand-subtitle">Customer Operations Intelligence</div>
          </div>
        </div>

        <nav className="view-switcher">
          <button
            className={view === "customer" ? "switch active" : "switch"}
            onClick={() => setView("customer")}
          >
            Customer Portal
          </button>
          <button
            className={view === "agent" ? "switch active" : "switch"}
            onClick={() => setView("agent")}
          >
            Support Agent
          </button>
        </nav>

        <div className="system-status">
          <span className="status-dot" />
          AI-powered support workspace
        </div>
      </div>
    </header>
  );
}

function CustomerPortal() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const payload = { message: message.trim() };
      const configuredCustomerId = import.meta.env.VITE_DEFAULT_CUSTOMER_ID?.trim();
      if (configuredCustomerId) payload.customer_id = configuredCustomerId;

      const response = await fetch(`${API}/support`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Unable to process your request.");
      }
      setResult(data);
    } catch (error) {
      setResult({
        status: "ERROR",
        response:
          error.message ||
          "Could not connect to ResolveAI. Make sure the FastAPI backend is running on port 8000.",
      });
    } finally {
      setLoading(false);
    }
  }

  function example(text) {
    setMessage(text);
    setResult(null);
  }

  return (
    <main className="customer-page">
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-intro">
            <div className="hero-copy">
              <div className="eyebrow">
                <span className="green-dot" />
                AI CUSTOMER OPERATIONS
              </div>

              <h1>
                Support that
                <span> actually resolves.</span>
              </h1>

              <p className="hero-description">
                Tell ResolveAI what went wrong. It investigates the request,
                checks relevant policies and records, then takes the next
                appropriate step or prepares the case for human support.
              </p>

              <div className="hero-trust-points">
                <span><b>✓</b> Policy-aware answers</span>
                <span><b>✓</b> Verified workflows</span>
                <span><b>✓</b> Auditable decisions</span>
              </div>
            </div>

            <aside className="hero-visual" aria-label="ResolveAI customer support workspace">
              <img
                src="https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=1100&q=85"
                alt="Customer using a laptop for an online service"
                loading="eager"
                onError={(event) => { event.currentTarget.style.display = "none"; }}
              />
              <div className="visual-shade" />
              <div className="visual-floating-card visual-card-top">
                <span className="visual-icon indigo-icon">✦</span>
                <div><strong>AI investigation</strong><small>Context before action</small></div>
                <span className="mini-live-dot" />
              </div>
              <div className="visual-floating-card visual-card-bottom">
                <span className="visual-icon teal-icon">✓</span>
                <div><strong>Controlled resolution</strong><small>Policy + backend checks</small></div>
              </div>
              <div className="visual-caption">
                <span className="caption-kicker">BUILT FOR TRUST</span>
                <strong>Every decision has a reason.</strong>
              </div>
            </aside>
          </div>

          <div className="support-card">
            <div className="support-card-header">
              <div>
                <div className="section-eyebrow">HOW CAN WE HELP?</div>
                <strong>Tell us what happened.</strong>
              </div>
              <span className="secure"><span className="secure-dot" /> Support workspace</span>
            </div>

            <form onSubmit={submit}>
              <label className="sr-only" htmlFor="support-message">How can I help you?</label>
              <textarea
                id="support-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="How can I help you? For example: My order ORD-48392 arrived damaged and I need a replacement."
                rows={4}
                required
              />

              <div className="support-card-footer">
                <span className="input-hint">
                  For order-specific help, include your order number. Never share passwords or payment card details.
                </span>
                <button className="primary-button" disabled={loading || !message.trim()}>
                  {loading ? <><span className="button-spinner" /> Investigating...</> : <>Ask ResolveAI <span aria-hidden="true">↗</span></>}
                </button>
              </div>
            </form>
          </div>

          <div className="examples">
            <span>Try a scenario</span>
            <button type="button" onClick={() => example("What is your return policy?")}>Return policy</button>
            <button type="button" onClick={() => example("My order ORD-48392 arrived damaged and I want a replacement.")}>Damaged order</button>
            <button type="button" onClick={() => example("I want a refund for ORD-48393")}>Refund request</button>
            <button type="button" onClick={() => example("Where is my order ORD-48394?")}>Track delivery</button>
          </div>
        </div>
      </section>

      {result && <CustomerResult result={result} onResultUpdate={setResult} />}
      <HowItWorks />
    </main>
  );
}

function CustomerResult({ result, onResultUpdate }) {
  const status = result.status?.toLowerCase() || "open";

  const title =
    status === "resolved"
      ? "Issue resolved"
      : status === "escalated"
      ? "A support specialist will take over"
      : status === "waiting_for_information"
      ? "One more step is required"
      : status === "error"
      ? "We could not complete the request"
      : "ResolveAI decision";

  return (
    <section className="customer-result">
      <div className="result-top">
        <div>
          <div className="section-eyebrow">RESOLVEAI DECISION</div>
          <h2>{title}</h2>
        </div>
        <StatusBadge status={result.status} />
      </div>

      <div className="ai-message">
        <div className="ai-avatar">AI</div>
        <div>
          <div className="ai-label">RESOLVEAI</div>
          <p>{result.response}</p>
        </div>
      </div>

      <div className="info-grid">
        <InfoBox
          label="DETECTED INTENT"
          value={result.intent || "GENERAL"}
        />
        <InfoBox label="CASE ID" value={result.case_id || "—"} />
      </div>

      {status === "waiting_for_information" &&
        result.intent === "DAMAGED_PRODUCT" && (
          <EvidenceUpload
            caseId={result.case_id}
            onComplete={onResultUpdate}
          />
        )}

      {result.evidence?.length > 0 && (
        <div className="evidence-section">
          <div className="section-eyebrow">INVESTIGATION EVIDENCE</div>
          <h3>Information considered</h3>

          <div className="evidence-list">
            {result.evidence.map((item, index) => (
              <div className="evidence-item" key={index}>
                <span className="check">✓</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.escalation_reason && (
        <div className="human-review">
          <div className="warning-icon">!</div>
          <div>
            <div className="section-eyebrow warning-text">HUMAN REVIEW</div>
            <h3>This case needs a specialist</h3>
            <p>{result.escalation_reason}</p>
          </div>
        </div>
      )}

      {result.actions?.length > 0 && (
        <div className="actions-section">
          <div className="section-eyebrow">SYSTEM ACTIONS</div>

          {result.actions.map((action, index) => (
            <div className="action-item" key={index}>
              <span className="action-number">{index + 1}</span>
              <span>{formatAction(action)}</span>
            </div>
          ))}
        </div>
      )}

      {status === "resolved" && (
        <div className="resolution-success">
          <div className="success-mark">✓</div>
          <div>
            <strong>Resolution completed</strong>
            <p>
              The requested backend action has been successfully recorded.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

function EvidenceUpload({ caseId, onComplete }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  function validateFile(selectedFile) {
    if (!selectedFile) return false;

    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];

    if (!allowedTypes.includes(selectedFile.type)) {
      setError("Please upload a JPG, PNG, or WebP image.");
      return false;
    }

    if (selectedFile.size > 8 * 1024 * 1024) {
      setError("Image must be smaller than 8 MB.");
      return false;
    }

    setError("");
    return true;
  }

  function selectFile(selectedFile) {
    if (!validateFile(selectedFile)) return;

    if (preview) URL.revokeObjectURL(preview);

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);

    const droppedFile = event.dataTransfer.files?.[0];
    if (droppedFile) selectFile(droppedFile);
  }

  async function uploadEvidence() {
    if (!file || !caseId) return;

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API}/support/cases/${caseId}/evidence`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to upload the evidence.");
      }

      onComplete(data);

      if (preview) URL.revokeObjectURL(preview);
      setFile(null);
      setPreview("");
    } catch (uploadError) {
      setError(
        uploadError.message || "Something went wrong while uploading."
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="evidence-upload">
      <div className="evidence-upload-header">
        <div>
          <div className="section-eyebrow">REQUIRED EVIDENCE</div>
          <h3>Upload a photo of the damaged product</h3>
          <p>
            A clear photograph helps us verify the damage before creating
            your replacement request.
          </p>
        </div>

        <div className="upload-security">
          JPG / PNG / WebP
          <br />
          Maximum 8 MB
        </div>
      </div>

      {!file ? (
        <label
          className={`upload-dropzone ${dragging ? "dragging" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(event) => {
              const selectedFile = event.target.files?.[0];
              if (selectedFile) selectFile(selectedFile);
            }}
            hidden
          />

          <div className="upload-icon">+</div>
          <div className="upload-title">Drop your image here</div>
          <div className="upload-subtitle">
            or click to browse from your device
          </div>
        </label>
      ) : (
        <div className="selected-file">
          <div className="preview-container">
            <img
              src={preview}
              alt="Damaged product preview"
              className="evidence-preview"
            />
          </div>

          <div className="selected-file-info">
            <div className="section-eyebrow">READY TO UPLOAD</div>
            <h4>{file.name}</h4>
            <p>{(file.size / (1024 * 1024)).toFixed(2)} MB</p>

            <button
              type="button"
              className="remove-file"
              disabled={uploading}
              onClick={() => {
                if (preview) URL.revokeObjectURL(preview);
                setFile(null);
                setPreview("");
                setError("");
              }}
            >
              Choose another image
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="upload-error">
          <span>!</span>
          {error}
        </div>
      )}

      {file && (
        <button
          type="button"
          className="upload-button"
          onClick={uploadEvidence}
          disabled={uploading}
        >
          {uploading ? (
            <>
              <span className="upload-spinner" />
              Verifying evidence...
            </>
          ) : (
            "Upload evidence and continue"
          )}
        </button>
      )}

      {uploading && (
        <div className="upload-progress">
          <div className="upload-progress-bar" />
        </div>
      )}
    </div>
  );
}

function SupportAgent() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  async function loadCases() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/cases`);

      if (!response.ok) throw new Error("Failed to load cases");

      const data = await response.json();
      setCases(Array.isArray(data) ? data : []);
    } catch {
      setError("Unable to load support cases. Make sure FastAPI is running.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCases();
  }, []);

  const filteredCases = useMemo(() => {
    const searchText = search.toLowerCase();

    return cases.filter((item) => {
      const matchesFilter = filter === "ALL" || item.status === filter;

      const matchesSearch =
        !searchText ||
        item.case_id?.toLowerCase().includes(searchText) ||
        item.customer_id?.toLowerCase().includes(searchText) ||
        item.intent?.toLowerCase().includes(searchText) ||
        item.message?.toLowerCase().includes(searchText);

      return matchesFilter && matchesSearch;
    });
  }, [cases, filter, search]);

  const stats = {
    total: cases.length,
    escalated: cases.filter((x) => x.status === "ESCALATED").length,
    open: cases.filter((x) => x.status === "OPEN").length,
    resolved: cases.filter((x) => x.status === "RESOLVED").length,
    waiting: cases.filter((x) => x.status === "WAITING_FOR_INFORMATION").length,
  };

  if (selectedCase) {
    return (
      <CaseDetails
        supportCase={selectedCase}
        onBack={() => setSelectedCase(null)}
        onResolved={loadCases}
      />
    );
  }

  return (
    <main className="agent-page">
      <div className="agent-heading">
        <div>
          <div className="section-eyebrow">SUPPORT OPERATIONS</div>
          <h1>Case management</h1>
          <p>
            Review AI decisions, investigate escalations, and resolve customer
            cases.
          </p>
        </div>

        <button className="refresh-button" onClick={loadCases} disabled={loading}>
          Refresh cases
        </button>
      </div>

      <div className="stats-grid">
        <StatCard value={stats.total} label="Total cases" />
        <StatCard value={stats.escalated} label="Escalated" danger />
        <StatCard value={stats.open} label="Open" />
        <StatCard value={stats.waiting} label="Waiting" />
        <StatCard value={stats.resolved} label="Resolved" success />
      </div>

      <section className="cases-panel">
        <div className="cases-toolbar">
          <div>
            <h2>Support cases</h2>
            <p>{filteredCases.length} cases shown</p>
          </div>

          <div className="case-controls">
            <input
              type="text"
              placeholder="Search cases..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />

            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="ALL">All statuses</option>
              <option value="ESCALATED">Escalated</option>
              <option value="OPEN">Open</option>
              <option value="WAITING_FOR_INFORMATION">Waiting</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </div>
        </div>

        {loading && <div className="empty-state">Loading support cases...</div>}

        {error && <div className="error-box">{error}</div>}

        {!loading && !error && filteredCases.length === 0 && (
          <div className="empty-state">No cases match your search.</div>
        )}

        {!loading && !error && filteredCases.length > 0 && (
          <div className="case-table">
            <div className="table-header">
              <span>Case</span>
              <span>Customer</span>
              <span>Intent</span>
              <span>Status</span>
              <span>Created</span>
              <span />
            </div>

            {filteredCases.map((item) => (
              <button
                className="case-row"
                key={item.case_id}
                onClick={() => setSelectedCase(item)}
              >
                <div>
                  <strong>{item.case_id}</strong>
                  <small>{truncate(item.message, 65)}</small>
                </div>

                <span>{item.customer_id}</span>
                <span className="intent">{item.intent}</span>
                <span>
                  <StatusBadge status={item.status} />
                </span>
                <span className="date">{formatDate(item.created_at)}</span>
                <span className="arrow">→</span>
              </button>
            ))}
          </div>
        )}
      </section>

      <div className="agent-note">
        <div className="note-icon">✓</div>
        <div>
          <strong>AI decisions are auditable</strong>
          <p>
            Every investigation records the intent, evidence, policies,
            actions, and final decision.
          </p>
        </div>
      </div>
    </main>
  );
}

function CaseDetails({ supportCase, onBack, onResolved }) {
  const [audit, setAudit] = useState([]);
  const [loadingAudit, setLoadingAudit] = useState(true);
  const [auditError, setAuditError] = useState("");
  const [resolution, setResolution] = useState("");
  const [resolving, setResolving] = useState(false);
  const [resolveMessage, setResolveMessage] = useState("");

  async function loadAudit() {
    setLoadingAudit(true);
    setAuditError("");

    try {
      const response = await fetch(
        `${API}/cases/${supportCase.case_id}/audit`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load audit trail");
      }

      setAudit(Array.isArray(data) ? data : []);
    } catch (error) {
      setAuditError(error.message);
    } finally {
      setLoadingAudit(false);
    }
  }

  useEffect(() => {
    loadAudit();
  }, [supportCase.case_id]);

  async function resolveCase() {
    if (!resolution.trim()) return;

    setResolving(true);
    setResolveMessage("");

    try {
      const response = await fetch(
        `${API}/admin/cases/${supportCase.case_id}/resolve?resolution=${encodeURIComponent(
          resolution.trim()
        )}`,
        {
          method: "POST",
          headers: { Accept: "*/*" },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not resolve case");
      }

      setResolveMessage(data.message || "Case resolved successfully.");
      setResolution("");

      await loadAudit();

      if (onResolved) await onResolved();
    } catch (error) {
      setResolveMessage(`Error: ${error.message}`);
    } finally {
      setResolving(false);
    }
  }

  return (
    <main className="case-details-page">
      <button className="back-button" onClick={onBack}>
        ← Back to cases
      </button>

      <div className="case-detail-header">
        <div>
          <div className="section-eyebrow">CASE DETAILS</div>
          <h1>{supportCase.case_id}</h1>
          <p>Customer {supportCase.customer_id}</p>
        </div>

        <StatusBadge status={supportCase.status} />
      </div>

      <section className="detail-card">
        <div className="detail-card-heading">
          <div>
            <div className="section-eyebrow">CUSTOMER REQUEST</div>
            <h2>{supportCase.intent}</h2>
          </div>
        </div>

        <div className="customer-message">{supportCase.message}</div>

        <div className="detail-grid">
          <InfoBox label="CUSTOMER" value={supportCase.customer_id} />
          <InfoBox label="INTENT" value={supportCase.intent} />
          <InfoBox label="CREATED" value={formatDate(supportCase.created_at)} />
          <div>
            <div className="info-label">CURRENT STATUS</div>
            <StatusBadge status={supportCase.status} />
          </div>
        </div>
      </section>

      <div className="two-column">
        <section className="detail-card">
          <div className="section-eyebrow">AI DECISION</div>
          <h2>Resolution</h2>

          <div className="decision-box">
            <div className="ai-avatar">AI</div>
            <div>
              <div className="ai-label">RESOLVEAI</div>
              <p>
                {supportCase.resolution || "No resolution recorded."}
              </p>
            </div>
          </div>

          {supportCase.escalation_reason && (
            <div className="human-review">
              <div className="warning-icon">!</div>
              <div>
                <div className="section-eyebrow warning-text">
                  ESCALATION REASON
                </div>
                <p>{supportCase.escalation_reason}</p>
              </div>
            </div>
          )}
        </section>

        <section className="detail-card">
          <div className="section-eyebrow">AUDIT TRAIL</div>
          <h2>Investigation timeline</h2>

          {loadingAudit && (
            <div className="loading-small">Loading audit trail...</div>
          )}

          {auditError && <div className="error-box">{auditError}</div>}

          {!loadingAudit && !auditError && audit.length === 0 && (
            <div className="empty-state small">No audit events recorded.</div>
          )}

          {!loadingAudit && !auditError && audit.length > 0 && (
            <div className="timeline">
              {audit.map((event, index) => (
                <div
                  className="timeline-item"
                  key={`${event.event_type}-${index}`}
                >
                  <div className="timeline-dot">✓</div>
                  <div className="timeline-content">
                    <div className="timeline-title">
                      <strong>{event.event_type}</strong>
                      <span>{formatDateTime(event.created_at)}</span>
                    </div>
                    <p>{formatAuditDetails(event.details)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {supportCase.status !== "RESOLVED" && (
        <section className="resolve-panel">
          <div>
            <div className="section-eyebrow">HUMAN ACTION</div>
            <h2>Resolve this case</h2>
            <p>
              Add the final decision or action taken by the support
              representative.
            </p>
          </div>

          <textarea
            value={resolution}
            onChange={(event) => setResolution(event.target.value)}
            placeholder="Example: Approved refund after manual verification. Customer will receive the refund within 5-7 business days."
            rows={4}
          />

          <button
            className="resolve-button"
            disabled={resolving || !resolution.trim()}
            onClick={resolveCase}
          >
            {resolving ? "Resolving..." : "Resolve case"}
          </button>

          {resolveMessage && (
            <div className="resolve-message">{resolveMessage}</div>
          )}
        </section>
      )}

      {supportCase.status === "RESOLVED" && (
        <div className="resolved-banner">
          <span>✓</span>
          <div>
            <strong>Case resolved</strong>
            <p>This case has already been marked as resolved.</p>
          </div>
        </div>
      )}
    </main>
  );
}

function HowItWorks() {
  const steps = [
    { number: "01", title: "Understand", description: "Detect intent" },
    { number: "02", title: "Investigate", description: "Orders + payments" },
    { number: "03", title: "Verify", description: "Policy + rules" },
    { number: "04", title: "Act", description: "Controlled tools" },
  ];

  return (
    <section className="how-section">
      <div className="section-eyebrow">UNDER THE HOOD</div>
      <h2>Not just a chatbot.</h2>
      <p>
        ResolveAI investigates, validates and acts through controlled backend
        tools.
      </p>

      <div className="process-flow">
        {steps.map((step, index) => (
          <React.Fragment key={step.number}>
            <div className="process-step">
              <div className="process-number">{step.number}</div>
              <div>
                <strong>{step.title}</strong>
                <span>{step.description}</span>
              </div>
            </div>
            {index < steps.length - 1 && <div className="process-line" />}
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}

function InfoBox({ label, value }) {
  return (
    <div className="info-box">
      <div className="info-label">{label}</div>
      <strong>{value}</strong>
    </div>
  );
}

function StatCard({ value, label, danger, success }) {
  return (
    <div
      className={`stat-card ${danger ? "danger" : ""} ${
        success ? "success" : ""
      }`}
    >
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function StatusBadge({ status }) {
  if (!status) return null;

  const normalized = status.toLowerCase();

  return (
    <span className={`status-badge status-${normalized}`}>
      <span className="status-badge-dot" />
      {status.replaceAll("_", " ")}
    </span>
  );
}

function formatAction(action) {
  if (!action) return "Action completed";

  if (typeof action === "object") {
    if (action.replacement_id) {
      return `Replacement request ${action.replacement_id} created successfully.`;
    }

    if (action.refund_id) {
      return `Refund ${action.refund_id} created successfully.`;
    }

    return action.message || "System action completed.";
  }

  const text = String(action);

  const replacementMatch = text.match(
    /replacement_id['"]?\s*:\s*['"]([^'"]+)/
  );

  if (replacementMatch) {
    return `Replacement request ${replacementMatch[1]} created successfully.`;
  }

  const refundMatch = text.match(/refund_id['"]?\s*:\s*['"]([^'"]+)/);

  if (refundMatch) {
    return `Refund ${refundMatch[1]} created successfully.`;
  }

  const messageMatch = text.match(/message['"]?\s*:\s*['"]([^'"]+)/);

  if (messageMatch) return messageMatch[1];

  return text;
}

function truncate(text, length) {
  if (!text) return "";
  return text.length > length ? `${text.substring(0, length)}...` : text;
}

function formatDate(value) {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return value;
  }
}

function formatDateTime(value) {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function formatAuditDetails(details) {
  if (!details) return "";

  try {
    const parsed =
      typeof details === "string" ? JSON.parse(details) : details;

    return Object.entries(parsed)
      .map(([key, value]) => {
        if (Array.isArray(value)) {
          return `${key}: ${value.join(", ")}`;
        }

        return `${key}: ${value}`;
      })
      .join(" • ");
  } catch {
    return String(details);
  }
}

createRoot(document.getElementById("root")).render(<App />);
