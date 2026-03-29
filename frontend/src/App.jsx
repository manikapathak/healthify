import { useState, useEffect, useRef } from "react";

const BASE = "http://localhost:8000/api/v1";

// ─── API helpers ───────────────────────────────────────────────────────────────
const api = {
  async upload(file, age, sex) {
    const form = new FormData();
    form.append("file", file);
    if (age) form.append("age", age);
    if (sex) form.append("sex", sex.toLowerCase());
    const res = await fetch(`${BASE}/reports/upload`, { method: "POST", body: form });
    return res.json();
  },
  async compare(parameters, age, sex) {
    const res = await fetch(`${BASE}/analysis/compare`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parameters, age: Number(age), sex: sex?.toLowerCase() || "male" }),
    });
    return res.json();
  },
  async riskAssess(parameters, age, sex, symptoms = []) {
    const res = await fetch(`${BASE}/risk/assess`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parameters, age: Number(age), sex: sex?.toLowerCase() || "male", symptoms }),
    });
    return res.json();
  },
  async predict(parameters, age, sex, symptoms = []) {
    const res = await fetch(`${BASE}/analysis/predict`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parameters, age: Number(age), sex: sex?.toLowerCase() || "male", symptoms }),
    });
    return res.json();
  },
  async explain(parameters, age, sex, symptoms = [], condition) {
    const body = { parameters, age: Number(age), sex: sex?.toLowerCase() || "male", symptoms };
    if (condition) body.condition = condition;
    const res = await fetch(`${BASE}/analysis/explain`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.json();
  },
  async symptoms() {
    const res = await fetch(`${BASE}/risk/symptoms`);
    return res.json();
  },
};

// ─── Shared styles ─────────────────────────────────────────────────────────────
const S = {
  page: { minHeight: "100vh", background: "#f0ebe0", fontFamily: "'Georgia', serif" },
  card: {
    background: "rgba(235,228,212,0.7)", borderRadius: 16,
    border: "1px solid rgba(200,190,175,0.5)", padding: "24px 28px",
  },
  btn: (variant = "dark") => ({
    padding: "12px 28px",
    background: variant === "dark" ? "#2a3a2a" : "transparent",
    color: variant === "dark" ? "#f0ebe0" : "#2a3a2a",
    border: variant === "dark" ? "none" : "1px solid rgba(60,80,60,0.4)",
    borderRadius: 8, cursor: "pointer", fontSize: 13,
    fontFamily: "'Georgia', serif", letterSpacing: "0.06em",
    transition: "all 0.2s ease",
  }),
  label: { fontSize: 11, letterSpacing: "0.18em", color: "#8a9a8a", textTransform: "uppercase" },
};

// ─── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status, is_critical }) {
  const colors = {
    high: { bg: "#ffb0b0", fg: "#5a1a1a" },
    low: { bg: "#b0c8ff", fg: "#1a2a5a" },
    normal: { bg: "#b0e0b0", fg: "#1a4a1a" },
    anomaly: { bg: "#ffb0b0", fg: "#5a1a1a" },
    unknown: { bg: "#e0e0e0", fg: "#4a4a4a" },
  };
  const c = is_critical ? { bg: "#ff6060", fg: "#fff" } : (colors[status?.toLowerCase()] || colors.unknown);
  return (
    <span style={{
      background: c.bg, color: c.fg,
      fontSize: 10, letterSpacing: "0.12em", padding: "3px 8px",
      borderRadius: 4, fontWeight: 700, textTransform: "uppercase",
    }}>{is_critical ? "CRITICAL" : status}</span>
  );
}

// ─── Disclaimer banner ─────────────────────────────────────────────────────────
function Disclaimer({ text, urgent }) {
  if (!text) return null;
  return (
    <div style={{
      background: urgent ? "rgba(255,80,80,0.1)" : "rgba(200,190,170,0.3)",
      border: `1px solid ${urgent ? "rgba(255,80,80,0.4)" : "rgba(180,170,150,0.4)"}`,
      borderRadius: 10, padding: "14px 20px", marginBottom: 24,
      fontSize: 13, color: urgent ? "#7a1a1a" : "#5a6a5a", lineHeight: 1.6,
    }}>
      {urgent && <strong>⚠ </strong>}{text}
    </div>
  );
}

// ─── Severity bar ──────────────────────────────────────────────────────────────
function SeverityBar({ severity }) {
  const levels = { normal: 0, borderline: 1, moderate: 2, severe: 3 };
  const colors = ["#b0e0b0", "#ffe0a0", "#ffb0a0", "#ff7070"];
  const n = levels[severity] ?? 0;
  return (
    <div style={{ display: "flex", gap: 3, alignItems: "center" }}>
      {[0, 1, 2, 3].map(i => (
        <div key={i} style={{ width: 10, height: 10, borderRadius: 2, background: i <= n ? colors[n] : "rgba(180,180,180,0.3)" }} />
      ))}
      <span style={{ fontSize: 11, color: "#8a9a8a", marginLeft: 6, textTransform: "capitalize" }}>{severity}</span>
    </div>
  );
}

// ─── Spinner ───────────────────────────────────────────────────────────────────
function Spinner({ label }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: "60px 0" }}>
      <div style={{ width: 40, height: 40, border: "3px solid rgba(60,80,60,0.15)", borderTop: "3px solid #2a3a2a", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      {label && <p style={{ color: "#7a8a7a", fontSize: 14, fontStyle: "italic" }}>{label}</p>}
    </div>
  );
}

// ─── Global keyframes ──────────────────────────────────────────────────────────
const GlobalStyles = () => (
  <style>{`
    @keyframes ringPulse{0%{opacity:.2;transform:scale(1)}100%{opacity:.5;transform:scale(1.04)}}
    @keyframes floatBlob0{0%{transform:translate(-50%,-50%) scale(1)}100%{transform:translate(-48%,-52%) scale(1.05)}}
    @keyframes floatBlob1{0%{transform:translate(-50%,-50%) scale(1)}100%{transform:translate(-52%,-48%) scale(1.08)}}
    @keyframes floatBlob2{0%{transform:translate(-50%,-50%) scale(1)}100%{transform:translate(-47%,-53%) scale(1.06)}}
    @keyframes floatBlob3{0%{transform:translate(-50%,-50%) scale(1)}100%{transform:translate(-53%,-47%) scale(1.04)}}
    @keyframes floatBlob4{0%{transform:translate(-50%,-50%) scale(1)}100%{transform:translate(-49%,-51%) scale(1.07)}}
    @keyframes floatBlob5{0%{transform:translate(-50%,-50%) scale(1)}100%{transform:translate(-51%,-49%) scale(1.05)}}
    @keyframes dropletAppear{from{opacity:0;transform:scale(0)}to{opacity:1;transform:scale(1)}}
    @keyframes spin{to{transform:rotate(360deg)}}
    @keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
  `}</style>
);

// ─── Loader ────────────────────────────────────────────────────────────────────
function LoaderPage({ onComplete }) {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => {
      setProgress(p => {
        if (p >= 100) { clearInterval(iv); setTimeout(onComplete, 600); return 100; }
        return p + 1.2;
      });
    }, 30);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (progress > 30) setPhase(1);
    if (progress >= 100) setPhase(2);
  }, [progress]);

  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "linear-gradient(160deg,#c8d8c8,#b8cfc0 30%,#a8c4b0 60%,#9ab5a3)",
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      transition: "opacity 0.6s ease", opacity: phase === 2 ? 0 : 1,
      fontFamily: "'Georgia', serif", overflow: "hidden",
    }}>
      <GlobalStyles />
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
        {[...Array(6)].map((_, i) => (
          <div key={i} style={{
            position: "absolute", width: `${180 + i * 40}px`, height: `${180 + i * 40}px`,
            borderRadius: "50%",
            background: `radial-gradient(circle,rgba(255,255,255,${0.08 - i * 0.01}) 0%,transparent 70%)`,
            top: `${[10, 60, 20, 70, 5, 45][i]}%`, left: `${[5, 70, 40, 10, 80, 55][i]}%`,
            transform: "translate(-50%,-50%)", animation: `floatBlob${i} ${4 + i}s ease-in-out infinite alternate`,
          }} />
        ))}
      </div>

      <div style={{ position: "relative", width: 320, height: 320, marginBottom: 40 }}>
        <svg width="320" height="320" viewBox="0 0 320 320" style={{ position: "absolute", inset: 0 }}>
          <defs><filter id="blur-sm"><feGaussianBlur stdDeviation="1.5" /></filter></defs>
          {[120, 200, 280].map((r, i) => (
            <circle key={i} cx="160" cy="160" r={r / 2} fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1"
              style={{ animation: `ringPulse ${2 + i * 0.5}s ease-in-out infinite alternate`, transformOrigin: "160px 160px" }} />
          ))}
          <circle cx="160" cy="160" r="90" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="2" />
          <circle cx="160" cy="160" r="90" fill="none" stroke="rgba(40,60,40,0.6)" strokeWidth="2.5"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 90}`}
            strokeDashoffset={`${2 * Math.PI * 90 * (1 - progress / 100)}`}
            transform="rotate(-90 160 160)"
            style={{ transition: "stroke-dashoffset 0.1s linear" }} />
          <g transform={`translate(160,160) scale(${0.3 + (progress / 100) * 0.7})`}>
            <path d="M0,-50 C20,-30 30,0 0,50 C-30,0 -20,-30 0,-50 Z" fill="rgba(40,65,40,0.5)" style={{ filter: "url(#blur-sm)" }} />
            <path d="M0,-50 C20,-30 30,0 0,50 C-30,0 -20,-30 0,-50 Z" fill="rgba(60,90,60,0.4)" />
            <line x1="0" y1="-45" x2="0" y2="45" stroke="rgba(40,65,40,0.6)" strokeWidth="1" />
            <line x1="0" y1="-10" x2="18" y2="10" stroke="rgba(40,65,40,0.4)" strokeWidth="0.7" />
            <line x1="0" y1="-10" x2="-18" y2="10" stroke="rgba(40,65,40,0.4)" strokeWidth="0.7" />
            <line x1="0" y1="10" x2="14" y2="28" stroke="rgba(40,65,40,0.4)" strokeWidth="0.7" />
            <line x1="0" y1="10" x2="-14" y2="28" stroke="rgba(40,65,40,0.4)" strokeWidth="0.7" />
            {progress > 50 && [0,1,2,3].map(i => (
              <ellipse key={i} cx={[10,-8,18,-15][i]} cy={[-30,-5,15,25][i]} rx="3" ry="4"
                fill="rgba(200,230,230,0.7)"
                style={{ animation: `dropletAppear 1s ease forwards ${i * 0.2}s` }} />
            ))}
          </g>
        </svg>
        <div style={{
          position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          opacity: phase >= 1 ? 1 : 0, transition: "opacity 1s ease",
        }}>
          <div style={{ fontSize: 12, letterSpacing: "0.25em", color: "rgba(30,50,30,0.7)", textTransform: "uppercase", marginTop: 80 }}>
            HEALTHIFY YOURSELF
          </div>
        </div>
      </div>

      <div style={{ textAlign: "center", opacity: phase >= 1 ? 1 : 0, transition: "opacity 1.2s ease 0.3s" }}>
        <h1 style={{ fontStyle: "italic", fontSize: 42, fontWeight: 400, color: "rgba(25,45,25,0.85)", margin: "0 0 8px" }}>
          Let's Healthify
        </h1>
      </div>
      <div style={{
        position: "absolute", bottom: 40, display: "flex", alignItems: "center", gap: 8,
        opacity: phase >= 1 ? 0.6 : 0, transition: "opacity 1.4s ease 0.6s",
        color: "rgba(25,45,25,0.8)", fontSize: 13, letterSpacing: "0.05em",
      }}>
        <span>⊘</span><span>Cultivating precision in wellness</span>
      </div>
    </div>
  );
}

// ─── Navbar ────────────────────────────────────────────────────────────────────
function Navbar({ activePage, onNav }) {
  return (
    <nav style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "18px 40px", background: "rgba(240,235,224,0.95)",
      position: "sticky", top: 0, zIndex: 100,
      borderBottom: "1px solid rgba(200,190,175,0.3)", backdropFilter: "blur(8px)",
    }}>
      <span style={{ fontFamily: "'Georgia', serif", fontStyle: "italic", fontSize: 18, fontWeight: 400, color: "#2a3a2a", cursor: "pointer" }}
        onClick={() => onNav("upload")}>Healthify</span>
      <div style={{ display: "flex", gap: 32 }}>
        {[["Reports", "report"], ["Insights", "insights"]].map(([label, page]) => {
          const active = activePage === page;
          return (
            <button key={label} onClick={() => onNav(page)} style={{
              background: "none", border: "none", cursor: "pointer",
              fontFamily: "'Georgia', serif", fontSize: 15, color: "#2a3a2a",
              fontStyle: active ? "italic" : "normal", fontWeight: active ? 500 : 400,
              borderBottom: active ? "2px solid #2a3a2a" : "2px solid transparent",
              paddingBottom: 2,
            }}>{label}</button>
          );
        })}
      </div>
    </nav>
  );
}

// ─── Upload Page ───────────────────────────────────────────────────────────────
function UploadPage({ onSubmit, onNav }) {
  const [file, setFile] = useState(null);
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("");
  const [weight, setWeight] = useState("");
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [error, setError] = useState(null);
  const fileRef = useRef();
  const canSubmit = file && age && sex && !loading;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true); setError(null);
    try {
      setLoadingStep("Uploading and parsing report…");
      const uploadRes = await api.upload(file, age, sex);
      if (!uploadRes.success) { setError(uploadRes.error || "Upload failed"); setLoading(false); return; }

      const params = uploadRes.data.parameters.map(p => ({ name: p.name, value: p.value, unit: p.unit }));

      setLoadingStep("Running statistical & ML analysis…");
      const [compareRes, riskRes] = await Promise.all([
        api.compare(params, age, sex),
        api.riskAssess(params, age, sex),
      ]);

      onSubmit({
        uploadData: uploadRes.data,
        compareData: compareRes.success ? compareRes.data : null,
        riskData: riskRes.success ? riskRes.data : null,
        disclaimer: uploadRes.disclaimer,
        age, sex, params,
      });
    } catch (e) {
      setError("Could not reach the Healthify server. Is it running at localhost:8000?");
    }
    setLoading(false); setLoadingStep("");
  };

  const inputStyle = {
    width: "100%", padding: "14px 18px", border: "1px solid rgba(180,170,155,0.4)",
    borderRadius: 10, background: "rgba(255,255,255,0.6)", fontSize: 15,
    fontFamily: "'Georgia', serif", color: "#3a4a3a", outline: "none", boxSizing: "border-box",
  };

  return (
    <div style={S.page}>
      <GlobalStyles />
      <Navbar activePage="upload" onNav={onNav} />
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "60px 40px" }}>
        <h1 style={{ fontSize: 56, fontWeight: 400, fontStyle: "italic", color: "#1a2a1a", margin: "0 0 12px", lineHeight: 1.1, letterSpacing: "-1px", textAlign: "center" }}>
          Translate your biology.
        </h1>
        <p style={{ fontSize: 16, color: "#5a6a5a", lineHeight: 1.7, maxWidth: 480, margin: "0 auto 60px", textAlign: "center" }}>
          Upload your laboratory blood report to receive a clinical-grade analysis.
        </p>

        {error && (
          <div style={{ background: "rgba(255,80,80,0.1)", border: "1px solid rgba(255,80,80,0.3)", borderRadius: 10, padding: "14px 20px", marginBottom: 24, color: "#7a1a1a", fontSize: 14 }}>
            ⚠ {error}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, marginBottom: 36 }}>
          {/* Drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}
            onClick={() => fileRef.current.click()}
            style={{
              background: dragging ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.7)",
              border: `2px dashed ${dragging ? "#4a6a4a" : "rgba(180,170,155,0.5)"}`,
              borderRadius: 16, padding: "60px 40px",
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              gap: 12, cursor: "pointer", transition: "all 0.2s ease",
            }}>
            <div style={{ width: 56, height: 56, borderRadius: "50%", background: "rgba(140,170,140,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>📄</div>
            <h3 style={{ fontSize: 18, fontWeight: 500, color: "#2a3a2a", margin: 0 }}>{file ? file.name : "Drop your lab report"}</h3>
            <p style={{ fontSize: 13, color: "#8a9a8a", margin: 0 }}>PDF, PNG, JPEG or CSV (Max 10MB)</p>
            <button style={S.btn()}>Browse Files</button>
            <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.csv,.webp" style={{ display: "none" }}
              onChange={e => e.target.files[0] && setFile(e.target.files[0])} />
          </div>

          {/* Profile form */}
          <div style={{ background: "rgba(235,225,205,0.6)", borderRadius: 16, padding: "36px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <p style={{ ...S.label, margin: 0 }}>Personal Profile</p>
            <div>
              <label style={{ ...S.label, display: "block", marginBottom: 8 }}>Current Age</label>
              <input style={inputStyle} placeholder="e.g. 34" value={age} onChange={e => setAge(e.target.value)} type="number" min="0" max="120" />
            </div>
            <div>
              <label style={{ ...S.label, display: "block", marginBottom: 8 }}>Sex at Birth</label>
              <select style={{ ...inputStyle, appearance: "none" }} value={sex} onChange={e => setSex(e.target.value)}>
                <option value="">Select option</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </div>
            <div>
              <label style={{ ...S.label, display: "block", marginBottom: 8 }}>Approx Weight (KG)</label>
              <input style={inputStyle} placeholder="e.g. 72" value={weight} onChange={e => setWeight(e.target.value)} type="number" />
            </div>
          </div>
        </div>

        <div style={{ textAlign: "center" }}>
          <button onClick={handleSubmit} disabled={!canSubmit} style={{
            padding: "18px 52px", background: canSubmit ? "#2a3a2a" : "rgba(60,80,60,0.35)",
            color: "#f0ebe0", border: "none", borderRadius: 50, cursor: canSubmit ? "pointer" : "not-allowed",
            fontSize: 17, fontFamily: "'Georgia', serif", fontStyle: "italic",
            display: "inline-flex", alignItems: "center", gap: 12, transition: "all 0.2s",
          }}>
            {loading
              ? <><span style={{ width: 18, height: 18, border: "2px solid rgba(255,255,255,0.3)", borderTop: "2px solid #fff", borderRadius: "50%", animation: "spin 0.8s linear infinite", display: "inline-block" }} />{loadingStep || "Analysing…"}</>
              : "Healthify Me →"
            }
          </button>
          <div style={{ marginTop: 14, display: "flex", gap: 24, justifyContent: "center", color: "#8a9a8a", fontSize: 12, letterSpacing: "0.1em" }}>
            <span>🔒 HIPAA COMPLIANT</span><span>•</span><span>🛡 ENCRYPTED RESULTS</span>
          </div>
        </div>
      </div>

      <footer style={{ borderTop: "1px solid rgba(180,170,155,0.3)", padding: "28px 40px", display: "flex", justifyContent: "space-between", alignItems: "center", color: "#7a8a7a", fontSize: 13 }}>
        <span style={{ fontFamily: "'Georgia', serif", fontStyle: "italic", fontSize: 16, color: "#2a3a2a" }}>Healthify</span>
        <span>© 2026 Healthify. A smart approach to diagnostic clarity.</span>
      </footer>
    </div>
  );
}

// ─── Report Page ───────────────────────────────────────────────────────────────
function ReportPage({ onNext, onNav, reportData }) {
  const { uploadData, compareData, riskData, disclaimer, age, sex, params } = reportData || {};
  const [activeTab, setActiveTab] = useState("narrative");
  const [symptoms, setSymptoms] = useState([]);
  const [availableSymptoms, setAvailableSymptoms] = useState([]);
  const [showSymptoms, setShowSymptoms] = useState(false);
  const [predictData, setPredictData] = useState(null);
  const [explainData, setExplainData] = useState(null);
  const [loadingPredict, setLoadingPredict] = useState(false);

  useEffect(() => {
    api.symptoms().then(r => { if (r.success) setAvailableSymptoms(r.data); }).catch(() => {});
  }, []);

  const runPredict = async () => {
    if (!params) return;
    setLoadingPredict(true);
    try {
      const [pred, exp] = await Promise.all([
        api.predict(params, age, sex, symptoms),
        api.explain(params, age, sex, symptoms),
      ]);
      if (pred.success) setPredictData(pred.data);
      if (exp.success) setExplainData(exp.data);
    } catch {}
    setLoadingPredict(false);
  };

  const toggleSymptom = s => setSymptoms(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s]);

  const urgent = riskData?.requires_immediate_attention;
  const parameters = uploadData?.parameters || [];
  const zscores = compareData?.zscore?.scores || {};
  const ifResult = compareData?.isolation_forest;

  const TABS = [["narrative","Narrative"],["parameters","Parameters"],["zscore","Z-Score"],["risk","Risk"],["ml","ML Insights"]];

  return (
    <div style={S.page}>
      <GlobalStyles />
      <Navbar activePage="report" onNav={onNav} />
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "48px 40px" }}>

        <p style={{ ...S.label, margin: "0 0 6px" }}>JOURNAL VOL. 04 &nbsp;&nbsp; AUTUMN EQUINOX</p>
        <h1 style={{ fontSize: 50, fontWeight: 400, fontStyle: "italic", color: "#1a2a1a", margin: "0 0 10px", letterSpacing: "-0.5px" }}>Report Synthesis</h1>
        <p style={{ fontStyle: "italic", color: "#7a8a7a", fontSize: 16, margin: "0 0 20px" }}>A narrative interpretation of your biological landscape.</p>

        {/* Quick stats */}
        {uploadData && (
          <div style={{ display: "flex", gap: 12, margin: "0 0 24px", flexWrap: "wrap" }}>
            {[
              { label: "Parameters", value: uploadData.parameter_count },
              { label: "Anomalies", value: uploadData.anomaly_count, alert: uploadData.anomaly_count > 0 },
              { label: "IF Agreement", value: compareData?.agreement !== undefined ? (compareData.agreement ? "✓ Yes" : "✗ No") : "—" },
              { label: "IF Score", value: ifResult ? ifResult.anomaly_score.toFixed(3) : "—", alert: ifResult?.is_anomalous },
            ].map(stat => (
              <div key={stat.label} style={{ ...S.card, padding: "14px 20px", flex: "1 1 100px", background: stat.alert ? "rgba(255,180,180,0.2)" : S.card.background }}>
                <div style={{ ...S.label, marginBottom: 4 }}>{stat.label}</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: stat.alert ? "#7a1a1a" : "#1a2a1a" }}>{stat.value}</div>
              </div>
            ))}
          </div>
        )}

        <Disclaimer text={disclaimer} urgent={urgent} />

        {/* Tab nav */}
        <div style={{ display: "flex", gap: 0, marginBottom: 28, borderBottom: "1px solid rgba(180,170,155,0.4)" }}>
          {TABS.map(([key, label]) => (
            <button key={key} onClick={() => setActiveTab(key)} style={{
              background: "none", border: "none", cursor: "pointer",
              padding: "10px 16px", fontFamily: "'Georgia', serif", fontSize: 13,
              color: activeTab === key ? "#1a2a1a" : "#8a9a8a",
              borderBottom: activeTab === key ? "2px solid #2a3a2a" : "2px solid transparent",
              fontWeight: activeTab === key ? 600 : 400, marginBottom: -1,
            }}>{label}</button>
          ))}
        </div>

        {/* ── NARRATIVE ── */}
        {activeTab === "narrative" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            {uploadData?.simplification ? (
              <div style={{ fontSize: 15, lineHeight: 1.9, color: "#3a4a3a", whiteSpace: "pre-wrap" }}>{uploadData.simplification}</div>
            ) : (
              [
                { title: "The Soil and Roots", tag: "METABOLIC INTEGRITY", paragraphs: ["Your physiological foundation resembles a dormant garden awaiting the first light of spring. The glucose stability we observed reflects a deep, grounded equilibrium — a steady nutrient flow that sustains the architecture of your energy. There is a quiet strength in the way your system handles the day's demands, moving with a rhythm that suggests biological resilience.", "However, like a root system seeking more expansive minerals, there is a subtle indication of micronutrient thirst. The levels of Vitamin D and Magnesium suggest a need for more direct exposure to the sun's warmth and the earth's deep salts. This is not a deficiency of failure, but rather a biological invitation to enrich the soil of your being."] },
                { title: "The Canopy's Breath", tag: "CARDIOVASCULAR VITALITY", paragraphs: ["In the quiet corridors of your circulation, the movement is fluid and unobstructed. Your heart rate variability speaks to a nervous system that is highly tuned, like the supple branches of a willow tree that bend gracefully in the wind rather than breaking against it.", "We find that the oxygen saturation remains at a crystalline peak, ensuring that every cell is bathed in the restorative breath of your efforts. To maintain this, consider the steady, low-intensity movement that mimics the slow growth of ancient moss."], quote: { text: "Health is not the absence of storm, but the internal architecture that allows one to thrive within it.", attribution: "CLINICAL SYNTHESIS NOTE" } },
                { title: "The Midnight Bloom", tag: "SLEEP & RECOVERY", paragraphs: ["It is in the darkness that the most profound growth occurs. Your sleep cycles have shown a beautiful expansion in the REM phase, the period where the mind prunes its overgrowth and makes sense of the day's light.", "Continue to guard these hours of shadow. Your biological report is more than data; it is a poem written in the language of cells and spirit."] },
              ].map((sec, si) => (
                <div key={si} style={{ marginBottom: 52 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
                    <h2 style={{ fontSize: 24, fontWeight: 600, color: "#1a2a1a", margin: 0 }}>{sec.title}</h2>
                    <span style={S.label}>{sec.tag}</span>
                  </div>
                  {sec.paragraphs.map((p, pi) => <p key={pi} style={{ fontSize: 15, lineHeight: 1.85, color: "#3a4a3a", textIndent: pi === 0 ? "2em" : 0, margin: "0 0 18px" }}>{p}</p>)}
                  {sec.quote && (
                    <div style={{ background: "rgba(200,190,170,0.3)", borderLeft: "3px solid rgba(100,120,100,0.4)", padding: "20px 24px", borderRadius: 4, margin: "24px 0" }}>
                      <p style={{ fontStyle: "italic", fontSize: 15, color: "#3a4a3a", lineHeight: 1.7, margin: "0 0 8px" }}>"{sec.quote.text}"</p>
                      <span style={S.label}>— {sec.quote.attribution}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* ── PARAMETERS ── */}
        {activeTab === "parameters" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            {parameters.length === 0
              ? <p style={{ color: "#8a9a8a", fontStyle: "italic" }}>No parameters loaded. Upload a report first.</p>
              : <>
                  {uploadData?.unrecognized?.length > 0 && (
                    <div style={{ background: "rgba(255,220,100,0.15)", border: "1px solid rgba(200,170,50,0.3)", borderRadius: 10, padding: "12px 18px", marginBottom: 18, fontSize: 13, color: "#6a5a1a" }}>
                      ⚠ Unrecognized columns: {uploadData.unrecognized.join(", ")}
                    </div>
                  )}
                  <div style={{ display: "grid", gap: 10 }}>
                    {parameters.map((p, i) => (
                      <div key={i} style={{ ...S.card, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 22px" }}>
                        <div>
                          <div style={{ fontWeight: 600, color: "#1a2a1a", fontSize: 15, marginBottom: 2, textTransform: "capitalize" }}>{p.name.replace(/_/g, " ")}</div>
                          <div style={S.label}>{p.raw_name}</div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: 20, fontWeight: 600, color: "#1a2a1a" }}>{p.value} <span style={{ fontSize: 12, color: "#8a9a8a" }}>{p.unit}</span></div>
                          <div style={{ fontSize: 12, color: "#8a9a8a", margin: "2px 0" }}>ref: {p.ref_low ?? "—"} – {p.ref_high ?? "—"} {p.ref_unit || ""}</div>
                          <StatusBadge status={p.status} is_critical={p.is_critical} />
                        </div>
                      </div>
                    ))}
                  </div>
                </>
            }
          </div>
        )}

        {/* ── Z-SCORE ── */}
        {activeTab === "zscore" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            {!compareData
              ? <p style={{ color: "#8a9a8a", fontStyle: "italic" }}>Upload a report to see Z-score analysis.</p>
              : <>
                  {ifResult && (
                    <div style={{ ...S.card, marginBottom: 18, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div>
                        <div style={S.label}>Isolation Forest</div>
                        <div style={{ fontSize: 20, fontWeight: 600, color: "#1a2a1a", marginTop: 4 }}>
                          {ifResult.is_anomalous ? "Anomalous Pattern Detected" : "Normal Pattern"}
                        </div>
                        <div style={{ fontSize: 13, color: "#7a8a7a", marginTop: 2 }}>Score: {ifResult.anomaly_score.toFixed(4)} · Confidence: {ifResult.confidence}</div>
                      </div>
                      <div style={{ width: 52, height: 52, borderRadius: "50%", background: ifResult.is_anomalous ? "#ffb0b0" : "#b0e0b0", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>
                        {ifResult.is_anomalous ? "⚠" : "✓"}
                      </div>
                    </div>
                  )}
                  {!compareData.agreement && (
                    <div style={{ background: "rgba(255,200,100,0.15)", border: "1px solid rgba(200,160,50,0.3)", borderRadius: 10, padding: "12px 18px", marginBottom: 14, fontSize: 13, color: "#6a5a1a" }}>
                      ⚠ Z-score and Isolation Forest disagree. Showing Z-score breakdown.
                    </div>
                  )}
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#8a9a8a", padding: "0 4px 8px" }}>
                      <span>Total: {compareData.zscore?.summary?.total_parameters}</span>
                      <span>Anomalies: {compareData.zscore?.summary?.anomaly_count}</span>
                      <span>Severe: {compareData.zscore?.summary?.severe_count}</span>
                      <span>Critical: {compareData.zscore?.summary?.has_critical ? "YES ⚠" : "No"}</span>
                    </div>
                  </div>
                  <div style={{ display: "grid", gap: 10 }}>
                    {Object.entries(zscores).map(([name, d]) => (
                      <div key={name} style={{ ...S.card, padding: "16px 22px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                          <div>
                            <div style={{ fontWeight: 600, color: "#1a2a1a", fontSize: 15, textTransform: "capitalize" }}>{name.replace(/_/g, " ")}</div>
                            <div style={{ fontSize: 13, color: "#7a8a7a", marginTop: 2 }}>{d.value} {d.unit} · z = {d.z_score?.toFixed(2)} · ref {d.ref_low}–{d.ref_high}</div>
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                            <StatusBadge status={d.status} is_critical={d.is_critical} />
                            <SeverityBar severity={d.severity} />
                          </div>
                        </div>
                        <div style={{ height: 5, background: "rgba(180,170,155,0.3)", borderRadius: 3, overflow: "hidden" }}>
                          <div style={{
                            height: "100%", borderRadius: 3,
                            width: `${Math.min(100, Math.abs(d.z_score || 0) / 4 * 100)}%`,
                            background: d.is_critical ? "#ff4040" : d.severity === "severe" ? "#ff8060" : d.severity === "moderate" ? "#ffb060" : "#80c080",
                            transition: "width 0.5s ease",
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </>
            }
          </div>
        )}

        {/* ── RISK ── */}
        {activeTab === "risk" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            {!riskData
              ? <p style={{ color: "#8a9a8a", fontStyle: "italic" }}>Upload a report to see risk assessment.</p>
              : <>
                  {urgent && (
                    <div style={{ background: "rgba(255,60,60,0.1)", border: "1px solid rgba(255,60,60,0.4)", borderRadius: 12, padding: "16px 22px", marginBottom: 20, color: "#7a1a1a", fontSize: 14, fontWeight: 600 }}>
                      ⚠ CRITICAL VALUES DETECTED — Please seek medical attention promptly.
                    </div>
                  )}
                  <div style={{ display: "grid", gap: 14 }}>
                    {riskData.conditions?.map((c, i) => (
                      <div key={i} style={S.card}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 16, color: "#1a2a1a" }}>{c.display_name}</div>
                            <div style={{ marginTop: 6 }}><SeverityBar severity={c.severity} /></div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <div style={{ fontSize: 32, fontWeight: 700, color: c.risk_percent > 60 ? "#b02020" : c.risk_percent > 30 ? "#b07020" : "#2a6a2a" }}>{c.risk_percent}%</div>
                            {c.requires_doctor && <span style={{ fontSize: 11, color: "#b02020", letterSpacing: "0.08em" }}>👨‍⚕️ SEE A DOCTOR</span>}
                          </div>
                        </div>
                        <div style={{ height: 6, background: "rgba(180,170,155,0.3)", borderRadius: 3, overflow: "hidden", marginBottom: 12 }}>
                          <div style={{ height: "100%", borderRadius: 3, width: `${c.risk_percent}%`, background: c.risk_percent > 60 ? "#d04040" : c.risk_percent > 30 ? "#d09040" : "#50a050", transition: "width 0.6s ease" }} />
                        </div>
                        <p style={{ fontSize: 14, color: "#5a6a5a", margin: "0 0 10px", lineHeight: 1.6 }}>{c.message}</p>
                        {c.lifestyle_tips?.length > 0 && (
                          <div style={{ borderTop: "1px solid rgba(180,170,155,0.3)", paddingTop: 10 }}>
                            <div style={{ ...S.label, marginBottom: 8 }}>Lifestyle Tips</div>
                            {c.lifestyle_tips.map((t, ti) => (
                              <div key={ti} style={{ fontSize: 13, color: "#3a5a3a", padding: "4px 0 4px 12px", borderLeft: "2px solid rgba(80,140,80,0.4)", marginBottom: 4 }}>🌿 {t}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
            }
          </div>
        )}

        {/* ── ML INSIGHTS ── */}
        {activeTab === "ml" && (
          <div style={{ animation: "fadeUp 0.4s ease" }}>
            {/* Symptom selector */}
            <div style={{ ...S.card, marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <div style={S.label}>Add Symptoms (optional)</div>
                <button onClick={() => setShowSymptoms(s => !s)} style={{ ...S.btn("outline"), padding: "6px 14px", fontSize: 12 }}>
                  {showSymptoms ? "Hide" : "Select Symptoms"}
                </button>
              </div>
              {symptoms.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                  {symptoms.map(s => (
                    <span key={s} onClick={() => toggleSymptom(s)} style={{ background: "rgba(60,90,60,0.15)", color: "#2a4a2a", border: "1px solid rgba(60,90,60,0.3)", borderRadius: 20, padding: "3px 10px", fontSize: 12, cursor: "pointer" }}>
                      {s.replace(/_/g, " ")} ×
                    </span>
                  ))}
                </div>
              )}
              {showSymptoms && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, maxHeight: 160, overflowY: "auto", marginBottom: 10 }}>
                  {availableSymptoms.map(s => (
                    <span key={s} onClick={() => toggleSymptom(s)} style={{
                      background: symptoms.includes(s) ? "rgba(60,90,60,0.2)" : "rgba(200,190,175,0.3)",
                      color: "#2a3a2a", border: `1px solid ${symptoms.includes(s) ? "rgba(60,90,60,0.5)" : "rgba(180,170,155,0.4)"}`,
                      borderRadius: 20, padding: "3px 10px", fontSize: 12, cursor: "pointer",
                    }}>{s.replace(/_/g, " ")}</span>
                  ))}
                </div>
              )}
              <button onClick={runPredict} disabled={loadingPredict || !params} style={{ ...S.btn(), padding: "10px 24px", fontSize: 13, marginTop: 4 }}>
                {loadingPredict ? "Running…" : "Run ML Analysis"}
              </button>
            </div>

            {loadingPredict && <Spinner label="Running ML prediction & SHAP analysis…" />}

            {predictData && !loadingPredict && (
              <div style={{ display: "grid", gap: 16 }}>
                {/* Agreement badge */}
                <div style={{ ...S.card }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                    <div style={S.label}>ML Prediction</div>
                    <span style={{ background: predictData.agreement ? "#b0e0b0" : "#ffb0b0", color: predictData.agreement ? "#1a4a1a" : "#5a1a1a", fontSize: 11, padding: "4px 10px", borderRadius: 4, fontWeight: 600, letterSpacing: "0.1em" }}>
                      {predictData.agreement ? "MODELS AGREE" : "MODELS DISAGREE"}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 28, marginBottom: 16 }}>
                    <div>
                      <div style={S.label}>Top Condition</div>
                      <div style={{ fontSize: 18, fontWeight: 600, color: "#1a2a1a", marginTop: 4, textTransform: "capitalize" }}>
                        {predictData.ml_prediction?.top_condition?.replace(/_/g, " ")}
                      </div>
                    </div>
                    <div>
                      <div style={S.label}>ML Confidence</div>
                      <div style={{ fontSize: 18, fontWeight: 600, color: "#1a2a1a", marginTop: 4 }}>
                        {(predictData.ml_prediction?.top_probability * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div>
                      <div style={S.label}>Rule-Based Risk</div>
                      <div style={{ fontSize: 18, fontWeight: 600, color: "#1a2a1a", marginTop: 4 }}>
                        {predictData.rule_based?.risk_percent}%
                      </div>
                    </div>
                  </div>
                  {/* Probability bars */}
                  <div style={{ display: "grid", gap: 8 }}>
                    {predictData.ml_prediction?.probabilities?.slice(0, 6).map((c, i) => (
                      <div key={i}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                          <span style={{ fontSize: 13, color: "#3a4a3a", textTransform: "capitalize" }}>{c.display_name}</span>
                          <span style={{ fontSize: 13, color: "#6a7a6a", fontWeight: 600 }}>{(c.probability * 100).toFixed(1)}%</span>
                        </div>
                        <div style={{ height: 5, background: "rgba(180,170,155,0.3)", borderRadius: 3, overflow: "hidden" }}>
                          <div style={{ height: "100%", borderRadius: 3, width: `${c.probability * 100}%`, background: i === 0 ? "#2a5a2a" : "rgba(80,120,80,0.4)", transition: "width 0.5s ease" }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* SHAP */}
                {explainData && (
                  <div style={S.card}>
                    <div style={S.label}>SHAP Feature Importance</div>
                    <div style={{ fontSize: 13, color: "#7a8a7a", margin: "6px 0 16px" }}>
                      Explaining: <strong style={{ color: "#2a3a2a", textTransform: "capitalize" }}>{explainData.explained_condition?.replace(/_/g, " ")}</strong>
                    </div>
                    <div style={{ display: "grid", gap: 10 }}>
                      {explainData.explanations?.map((e, i) => (
                        <div key={i}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                            <span style={{ fontSize: 14, color: "#1a2a1a", textTransform: "capitalize", fontWeight: i === 0 ? 600 : 400 }}>
                              {e.feature.replace(/_/g, " ")}
                            </span>
                            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                              <span style={{
                                fontSize: 11, padding: "2px 7px", borderRadius: 3, fontWeight: 600,
                                background: e.direction === "increases_risk" ? "rgba(220,80,80,0.15)" : "rgba(80,160,80,0.15)",
                                color: e.direction === "increases_risk" ? "#8a2020" : "#205a20",
                              }}>{e.direction === "increases_risk" ? "↑ risk" : "↓ risk"}</span>
                              <span style={{ fontSize: 13, color: "#4a5a4a", fontWeight: 600 }}>{e.percentage}</span>
                            </div>
                          </div>
                          <div style={{ height: 5, background: "rgba(180,170,155,0.3)", borderRadius: 3, overflow: "hidden" }}>
                            <div style={{ height: "100%", borderRadius: 3, width: e.percentage, maxWidth: "100%", background: e.direction === "increases_risk" ? "#d06060" : "#60a060", transition: "width 0.5s ease" }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {!predictData && !loadingPredict && (
              <div style={{ textAlign: "center", padding: "40px 0", color: "#8a9a8a", fontStyle: "italic" }}>
                Select symptoms (optional) and click "Run ML Analysis" to get predictions and SHAP explanations.
              </div>
            )}
          </div>
        )}

        {/* End of report */}
        <div style={{ textAlign: "center", borderTop: "1px solid rgba(180,170,155,0.4)", paddingTop: 48, marginTop: 60 }}>
          <div style={{ width: 44, height: 44, borderRadius: "50%", background: "#2a3a2a", color: "#f0ebe0", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, margin: "0 auto 16px" }}>✦</div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "#1a2a1a", margin: "0 0 6px" }}>End of Narrative Report</h3>
          <p style={{ fontSize: 13, color: "#8a9a8a", margin: "0 0 28px" }}>Finalized on {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}</p>
          <button onClick={onNext} style={{ ...S.btn(), padding: "14px 44px", fontSize: 14, letterSpacing: "0.08em", textTransform: "uppercase" }}>Next →</button>
        </div>
      </div>
    </div>
  );
}

// ─── Insights Page ─────────────────────────────────────────────────────────────
function InsightsPage({ onNav, reportData }) {
  const [expandedIdx, setExpandedIdx] = useState(null);
  const { uploadData, compareData, riskData, disclaimer } = reportData || {};
  const parameters = uploadData?.parameters || [];
  const anomalies = parameters.filter(p => p.status !== "normal");
  const urgent = riskData?.requires_immediate_attention;
  const zscores = compareData?.zscore?.scores || {};

  const categoryFor = name => ({ hemoglobin:"HEMATOLOGY", rbc:"HEMATOLOGY", wbc:"HEMATOLOGY", platelets:"HEMATOLOGY", hematocrit:"HEMATOLOGY", mcv:"HEMATOLOGY", mch:"HEMATOLOGY", mchc:"HEMATOLOGY", glucose:"METABOLIC", hba1c:"METABOLIC", cholesterol:"LIPID", ldl:"LIPID", hdl:"LIPID", triglycerides:"LIPID", creatinine:"RENAL", bun:"RENAL", uric_acid:"RENAL", alt:"HEPATIC", ast:"HEPATIC", alp:"HEPATIC", bilirubin_total:"HEPATIC", tsh:"THYROID", t3:"THYROID", t4:"THYROID", ferritin:"IRON", iron:"IRON", tibc:"IRON", vitamin_b12:"VITAMINS", vitamin_d:"VITAMINS", sodium:"ELECTROLYTES", potassium:"ELECTROLYTES", calcium:"ELECTROLYTES" }[name] || "OTHER");
  const iconFor = cat => ({ HEMATOLOGY:"◈", METABOLIC:"◎", LIPID:"◉", RENAL:"◌", HEPATIC:"◆", THYROID:"◇", IRON:"◍", VITAMINS:"◑", ELECTROLYTES:"◐", OTHER:"○" }[cat] || "○");
  const bgFor = cat => ({ HEMATOLOGY:"rgba(180,140,200,0.2)", METABOLIC:"rgba(150,180,150,0.25)", LIPID:"rgba(180,160,130,0.25)", RENAL:"rgba(130,160,200,0.2)", HEPATIC:"rgba(200,170,130,0.2)", THYROID:"rgba(200,140,140,0.2)", IRON:"rgba(160,140,180,0.25)", VITAMINS:"rgba(160,200,150,0.2)", ELECTROLYTES:"rgba(140,180,190,0.2)", OTHER:"rgba(170,170,170,0.2)" }[cat] || "rgba(170,170,170,0.2)");

  const insightCards = anomalies.length > 0 ? anomalies.map(p => {
    const z = zscores[p.name];
    const cat = categoryFor(p.name);
    return {
      category: cat, title: p.name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
      tag: p.is_critical ? "CRITICAL" : p.status.toUpperCase(),
      tagColor: p.is_critical ? "#ff6060" : p.status === "high" ? "#ffb0b0" : "#b0c8ff",
      icon: iconFor(cat), iconBg: bgFor(cat),
      detail: `Value: ${p.value} ${p.unit} (ref: ${p.ref_low ?? "—"} – ${p.ref_high ?? "—"} ${p.ref_unit || ""})${z ? ` · Z-score: ${z.z_score?.toFixed(2)} · Severity: ${z.severity}` : ""}`,
      value: p.value, unit: p.unit, ref_low: p.ref_low, ref_high: p.ref_high, ref_unit: p.ref_unit,
      z_score: z?.z_score, severity: z?.severity,
    };
  }) : [
    { category: "CIRCADIAN RHYTHM", title: "Elevated Resting HR", tag: "ANOMALY", tagColor: "#ffb0b0", icon: "〜", iconBg: "rgba(180,180,200,0.2)", detail: "Your heart rate during deep sleep cycles has increased by 12% over the last 4 nights. This often correlates with delayed metabolic recovery or early signs of systemic inflammation." },
    { category: "METABOLIC", title: "Hydration Density Shift", icon: "◎", iconBg: "rgba(150,180,150,0.25)", detail: "Cellular hydration markers show a measurable shift in osmotic pressure." },
    { category: "NEUROLOGICAL", title: "Cortisol Spike Patterns", icon: "◉", iconBg: "rgba(150,160,180,0.25)", detail: "Cortisol excursions detected across the diurnal window." },
    { category: "REST", title: "REM Fragmentation", icon: "☽", iconBg: "rgba(160,150,180,0.25)", detail: "REM sleep architecture shows fragmentation across the last 7 nights." },
  ];

  const mainCard = insightCards[0];
  const restCards = insightCards.slice(1);

  return (
    <div style={S.page}>
      <GlobalStyles />
      <Navbar activePage="insights" onNav={onNav} />
      <div style={{ maxWidth: 700, margin: "0 auto", padding: "60px 40px" }}>
        <h1 style={{ fontSize: 48, fontWeight: 400, color: "#1a2a1a", margin: "0 0 12px" }}>
          <span style={{ fontWeight: 600 }}>Diagnostic</span> <em>Insights</em>
        </h1>
        <p style={{ fontSize: 15, color: "#5a6a5a", lineHeight: 1.7, margin: "0 0 12px", maxWidth: 420 }}>
          Your physiological patterns analyzed with precision. We've identified key shifts in your markers this month.
        </p>

        {uploadData && (
          <div style={{ display: "flex", gap: 12, margin: "16px 0 24px", flexWrap: "wrap" }}>
            {[
              { label: "Total Markers", value: uploadData.parameter_count },
              { label: "Anomalies", value: uploadData.anomaly_count, alert: uploadData.anomaly_count > 0 },
              { label: "Top Condition", value: riskData?.top_condition?.replace(/_/g, " ") || "—" },
            ].map(s => (
              <div key={s.label} style={{ ...S.card, padding: "12px 18px", flex: "1 1 120px", background: s.alert ? "rgba(255,180,180,0.2)" : S.card.background }}>
                <div style={S.label}>{s.label}</div>
                <div style={{ fontSize: 16, fontWeight: 600, color: s.alert ? "#7a1a1a" : "#1a2a1a", marginTop: 4, textTransform: "capitalize" }}>{s.value}</div>
              </div>
            ))}
          </div>
        )}

        <Disclaimer text={disclaimer} urgent={urgent} />

        {/* Main card */}
        {mainCard && (
          <div style={{ ...S.card, padding: "28px 32px", marginBottom: 10, animation: "fadeUp 0.4s ease" }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <div style={{ width: 42, height: 42, borderRadius: "50%", background: mainCard.iconBg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, color: "#4a5a6a" }}>{mainCard.icon}</div>
                <div>
                  <p style={{ ...S.label, margin: "0 0 4px" }}>{mainCard.category}</p>
                  <h3 style={{ fontSize: 22, fontWeight: 600, color: "#1a2a1a", margin: 0 }}>{mainCard.title}</h3>
                </div>
              </div>
              {mainCard.tag && <StatusBadge status={mainCard.tag} is_critical={mainCard.tag === "CRITICAL"} />}
            </div>

            {mainCard.value !== undefined && (
              <div style={{ display: "flex", gap: 24, marginBottom: 14, flexWrap: "wrap" }}>
                <div><div style={S.label}>Value</div><div style={{ fontSize: 24, fontWeight: 700, color: "#1a2a1a" }}>{mainCard.value} <span style={{ fontSize: 14, color: "#7a8a7a" }}>{mainCard.unit}</span></div></div>
                {mainCard.z_score !== undefined && <div><div style={S.label}>Z-Score</div><div style={{ fontSize: 24, fontWeight: 700, color: "#1a2a1a" }}>{mainCard.z_score?.toFixed(2)}</div></div>}
                {mainCard.severity && <div style={{ alignSelf: "flex-end" }}><SeverityBar severity={mainCard.severity} /></div>}
              </div>
            )}

            <p style={{ fontSize: 15, color: "#4a5a4a", lineHeight: 1.75, margin: "0 0 20px" }}>{mainCard.detail}</p>
            <div style={{ display: "flex", gap: 12 }}>
              <button style={S.btn()}>REVIEW TRENDS</button>
              <button style={S.btn("outline")}>LOG ACTIVITY</button>
            </div>
          </div>
        )}

        {/* Collapsible rest */}
        {restCards.map((card, i) => (
          <div key={i} style={{ marginBottom: 10 }}>
            <div onClick={() => setExpandedIdx(expandedIdx === i ? null : i)} style={{
              ...S.card, padding: "20px 26px",
              display: "flex", alignItems: "center", justifyContent: "space-between",
              cursor: "pointer", background: expandedIdx === i ? "rgba(235,228,212,0.95)" : S.card.background,
              transition: "background 0.2s ease",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <div style={{ width: 40, height: 40, borderRadius: "50%", background: card.iconBg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, color: "#5a6a5a" }}>{card.icon}</div>
                <div>
                  <p style={{ ...S.label, margin: "0 0 2px" }}>{card.category}</p>
                  <h3 style={{ fontSize: 17, fontWeight: 600, color: "#1a2a1a", margin: 0 }}>{card.title}</h3>
                </div>
              </div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                {card.tag && <StatusBadge status={card.tag} is_critical={card.tag === "CRITICAL"} />}
                <span style={{ fontSize: 20, color: "#8a9a8a" }}>{expandedIdx === i ? "−" : "⊕"}</span>
              </div>
            </div>
            {expandedIdx === i && (
              <div style={{ ...S.card, borderRadius: "0 0 16px 16px", borderTop: "none", padding: "18px 26px", background: "rgba(245,240,230,0.85)", animation: "fadeUp 0.25s ease" }}>
                {card.value !== undefined && (
                  <div style={{ display: "flex", gap: 20, marginBottom: 12, flexWrap: "wrap" }}>
                    <div><div style={S.label}>Value</div><div style={{ fontSize: 20, fontWeight: 600 }}>{card.value} <span style={{ fontSize: 12, color: "#8a9a8a" }}>{card.unit}</span></div></div>
                    {card.z_score !== undefined && <div><div style={S.label}>Z-Score</div><div style={{ fontSize: 20, fontWeight: 600 }}>{card.z_score?.toFixed(2)}</div></div>}
                    {card.severity && <div style={{ alignSelf: "flex-end" }}><SeverityBar severity={card.severity} /></div>}
                  </div>
                )}
                <p style={{ fontSize: 14, color: "#5a6a5a", lineHeight: 1.7, margin: 0 }}>{card.detail || "No additional detail available."}</p>
                {card.ref_low != null && <p style={{ fontSize: 12, color: "#8a9a8a", margin: "8px 0 0" }}>Reference range: {card.ref_low} – {card.ref_high} {card.ref_unit}</p>}
              </div>
            )}
          </div>
        ))}

        <div style={{ marginTop: 32, borderRadius: 20, height: 200, background: "linear-gradient(135deg,#c8d4c0,#b8c8b0 50%,#a8b8a0)", display: "flex", alignItems: "center", justifyContent: "center", opacity: 0.6 }}>
          <div style={{ fontSize: 72, opacity: 0.5 }}>🌿</div>
        </div>
      </div>
    </div>
  );
}

// ─── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState("loader");
  const [reportData, setReportData] = useState(null);

  const handleNav = dest => {
    if (dest === "report") setPage("report");
    else if (dest === "insights") setPage("insights");
    else if (dest === "upload") setPage("upload");
  };

  if (page === "loader") return <LoaderPage onComplete={() => setPage("upload")} />;
  if (page === "upload") return <UploadPage onSubmit={data => { setReportData(data); setPage("report"); }} onNav={handleNav} />;
  if (page === "report") return <ReportPage onNext={() => setPage("insights")} onNav={handleNav} reportData={reportData} />;
  if (page === "insights") return <InsightsPage onNav={handleNav} reportData={reportData} />;
  return null;
}
