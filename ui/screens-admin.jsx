// screens-admin.jsx — Admin Dashboard
// Changes:
//   • Overview: removed "Avg. session", "Judge confidence", "Persona ID accuracy";
//     renamed "Judge role mix" → "Judge Accuracy".
//   • Chat Analytics: removed "Topic mix".
//   • Added Judging launcher (per-session + a top-level CTA) with a full report modal.

function AdminSidebar({ section, onSelect }) {
  const items = [
    { id: "overview", label: "Overview", icon: <Icons.ChartBar size={14} /> },
    { id: "analytics", label: "Chat Analytics", icon: <Icons.ChartLine size={14} /> },
    { id: "performance", label: "Agent Performance", icon: <Icons.Brain size={14} /> },
    { id: "sessions", label: "Session Log", icon: <Icons.Database size={14} /> },
    { id: "judging", label: "Judging", icon: <Icons.Sparkles size={14} /> },
    { id: "export", label: "Export", icon: <Icons.Download size={14} /> },
  ];
  return (
    <aside className="admin-sidebar">
      <div className="admin-sidebar-head">
        <Icons.Shield size={14} sw={2} style={{ color: "var(--admin)" }} />
        <div>
          <div className="t-eyebrow" style={{ color: "var(--admin)" }}>Admin area</div>
          <div className="mono" style={{ fontSize: 12, fontWeight: 600, marginTop: 2 }}>Console</div>
        </div>
      </div>
      <div className="admin-sidebar-nav">
        {items.map(it => (
          <button
            key={it.id}
            className={`admin-nav-item ${section === it.id ? "active" : ""}`}
            onClick={() => onSelect(it.id)}
          >
            {it.icon}
            <span style={{ flex: 1 }}>{it.label}</span>
            {section === it.id && <Icons.ChevronRight size={12} />}
          </button>
        ))}
      </div>
      <div style={{ padding: 12, borderTop: "1px solid var(--border-0)" }}>
        <div className="card" style={{ padding: 12, background: "var(--admin-soft)", borderColor: "var(--admin-border)" }}>
          <div className="row">
            <Icons.AlertCircle size={14} sw={2} style={{ color: "var(--admin)" }} />
            <span className="mono" style={{ fontSize: 11, color: "var(--admin)", fontWeight: 600 }}>RESTRICTED</span>
          </div>
          <div style={{ fontSize: 11.5, color: "var(--fg-1)", marginTop: 6, lineHeight: 1.4 }}>
            Admin accounts cannot enter user chats. Use <strong>New chat</strong> to create a session for evaluation.
          </div>
        </div>
      </div>
    </aside>
  );
}

function StatusPill({ status }) {
  const map = {
    live: { label: "Live", cls: "badge-accent" },
    complete: { label: "Complete", cls: "" },
    evaluating: { label: "Evaluating", cls: "badge-admin" },
    flagged: { label: "Flagged", cls: "badge-danger" },
  };
  const v = map[status] || { label: status, cls: "" };
  return <span className={`badge badge-dot ${v.cls}`}>{v.label}</span>;
}

// ─── Overview ────────────────────────────────────────────────
function OverviewSection() {
  const [kpis, setKpis] = React.useState(null);
  React.useEffect(() => {
    window.api.get("/admin/overview")
      .then(data => setKpis([
        { label: "Sessions today", value: String(data.sessions_today.value), delta: `${data.sessions_today.delta_pct >= 0 ? "+" : ""}${data.sessions_today.delta_pct}%`, up: data.sessions_today.delta_pct >= 0, spark: data.sessions_today.spark },
        { label: "Active users",   value: String(data.active_users.value),   delta: `${data.active_users.delta_pct >= 0 ? "+" : ""}${data.active_users.delta_pct}%`,   up: data.active_users.delta_pct >= 0,   spark: data.active_users.spark },
      ]))
      .catch(() => setKpis([]));
  }, []);

  if (!kpis) return <div style={{ padding: 24, color: "var(--fg-2)" }}>Loading…</div>;

  return (
    <>
      <div className="kpi-grid kpi-grid-2">
        {kpis.map(k => (
          <div key={k.label} className="card kpi">
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value}</div>
            <div className={`kpi-delta ${k.up ? "up" : "down"}`}>
              {k.up ? "▲" : "▼"} {k.delta} <span className="t-meta" style={{ color: "var(--fg-3)" }}>vs. yesterday</span>
            </div>
            <Sparkline data={k.spark} color={k.up ? "var(--admin)" : "var(--danger)"} />
          </div>
        ))}
      </div>

      <div className="chart-grid">
        <div className="card chart-card">
          <div className="chart-card-head">
            <div>
              <div className="t-eyebrow">Sessions per hour</div>
              <div className="t-h3" style={{ marginTop: 4 }}>Last 24h</div>
            </div>
            <div className="row" style={{ gap: 6 }}>
              <span className="badge">24h</span>
              <span className="badge" style={{ opacity: 0.5 }}>7d</span>
              <span className="badge" style={{ opacity: 0.5 }}>30d</span>
            </div>
          </div>
          <BarChartPlaceholder label="Metrics coming soon" />
        </div>

        {/* Renamed: Judge role mix → Judge Accuracy */}
        <div className="card chart-card">
          <div className="chart-card-head">
            <div>
              <div className="t-eyebrow">Persona-ID hit rate</div>
              <div className="t-h3" style={{ marginTop: 4 }}>Judge Accuracy</div>
            </div>
            <span className="badge">baseline 12.5%</span>
          </div>
          <PieChartPlaceholder label="Per judge type" />
        </div>
      </div>
      {/* Removed: "Persona ID accuracy" rolling-7d line chart */}
    </>
  );
}

// ─── Sessions table (with optional per-row Judge / View report action) ─────
function RecentSessionsTable({ onJudge, reports }) {
  const { byId } = window.useAgents();
  const [sessions, setSessions] = React.useState([]);
  React.useEffect(() => {
    window.api.get("/admin/sessions?limit=24")
      .then(data => setSessions(data))
      .catch(() => setSessions([]));
  }, []);

  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div className="chart-card-head" style={{ padding: 14 }}>
        <div>
          <div className="t-eyebrow">Recent sessions</div>
          <div className="t-h3" style={{ marginTop: 4 }}>Last 24 hours</div>
        </div>
        <div className="row" style={{ gap: 6 }}>
          <Btn variant="outline" size="sm" icon={<Icons.Filter size={12} />}>Filter</Btn>
          <Btn variant="outline" size="sm" icon={<Icons.Download size={12} />}>Export CSV</Btn>
        </div>
      </div>
      {sessions.length === 0 ? (
        <Empty title="No sessions yet" sub="Sessions appear here once users start chatting." icon={<Icons.Database size={20} />} />
      ) : (
      <table className="table">
        <thead>
          <tr>
            <th>Session ID</th>
            <th>Participants</th>
            <th>Topic</th>
            <th style={{ width: 110 }}>Duration</th>
            <th style={{ width: 150 }}>Date</th>
            <th style={{ width: 130 }}>Status</th>
            <th style={{ width: 160 }}></th>
          </tr>
        </thead>
        <tbody>
          {sessions.map(s => {
            const judged = !!reports?.[s.id];
            return (
              <tr key={s.id}>
                <td className="col-mono">{s.id}</td>
                <td>
                  <div className="row" style={{ gap: 8 }}>
                    <AvatarStack personas={s.participants.map(id => byId(id)).filter(Boolean)} size="xs" max={4} />
                    <span className="t-meta">{s.participants.length}</span>
                  </div>
                </td>
                <td style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={s.topic}>
                  {s.topic}
                </td>
                <td className="col-mono">{s.duration}</td>
                <td className="t-meta col-mono">{s.date}</td>
                <td><StatusPill status={s.status} /></td>
                <td>
                  <div className="row" style={{ gap: 4, justifyContent: "flex-end" }}>
                    {judged ? (
                      <Btn
                        variant="outline"
                        size="sm"
                        icon={<Icons.ChartBar size={12} />}
                        onClick={() => onJudge?.(s)}
                        title="View saved judging report"
                      >
                        View report
                      </Btn>
                    ) : (
                      <Btn
                        variant="outline"
                        size="sm"
                        icon={<Icons.Sparkles size={12} />}
                        onClick={() => onJudge?.(s)}
                        title="Run judging pipeline"
                      >
                        Judge
                      </Btn>
                    )}
                    <IconBtn size="sm" icon={<Icons.ChevronRight size={13} />} />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      )}
    </div>
  );
}

function AgentPerformanceSection() {
  const { byId } = window.useAgents();
  const [perf, setPerf] = React.useState([]);
  React.useEffect(() => {
    window.api.get("/admin/agent-performance")
      .then(data => setPerf(data))
      .catch(() => setPerf([]));
  }, []);

  const rows = perf.map(entry => {
    const p = byId(entry.agent_id);
    if (!p) return null;
    return (
      <tr key={entry.agent_id}>
        <td>
          <div className="row" style={{ gap: 10 }}>
            <Avatar persona={p} size="sm" />
            <div>
              <div className="mono" style={{ fontSize: 12, fontWeight: 600 }}>{p.name}</div>
              <div className="t-meta" style={{ fontSize: 10.5 }}>{String(entry.agent_id)}</div>
            </div>
          </div>
        </td>
        <td>
          <span className="badge">{p.source_type === "fiction" ? "Fiction" : "Real-world"}</span>
        </td>
        <td className="col-mono">{entry.sessions}</td>
        <td>
          <FidelityBar value={entry.individual_fidelity / 5} label={Number(entry.individual_fidelity).toFixed(2)} />
        </td>
        <td>
          <FidelityBar value={entry.group_fidelity / 5} label={Number(entry.group_fidelity).toFixed(2)} color="var(--accent)" />
        </td>
        <td>
          {entry.flagged > 4 ? (
            <span className="badge badge-danger">{entry.flagged}</span>
          ) : (
            <span className="badge">{entry.flagged}</span>
          )}
        </td>
      </tr>
    );
  }).filter(Boolean);

  return (
    <>
      <div className="t-eyebrow">Per-agent fidelity</div>
      <h2 className="t-h2" style={{ marginTop: 4, marginBottom: 16 }}>Agent performance</h2>
      {rows.length === 0 ? (
        <Empty title="No data yet" sub="Performance stats appear after agents participate in chats." icon={<Icons.Brain size={20} />} />
      ) : (
        <div className="card" style={{ overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Source</th>
                <th style={{ width: 120 }}>Sessions</th>
                <th style={{ width: 160 }}>Individual fidelity</th>
                <th style={{ width: 140 }}>Group fidelity</th>
                <th style={{ width: 90 }}>Flagged</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
      )}
    </>
  );
}

function FidelityBar({ value, label, color = "var(--admin)" }) {
  return (
    <div className="row" style={{ gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: "var(--bg-3)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ width: `${value * 100}%`, height: "100%", background: color }} />
      </div>
      <span className="mono" style={{ fontSize: 11, color: "var(--fg-1)" }}>{label}</span>
    </div>
  );
}

function ChatAnalyticsSection() {
  // Change 2: removed the "Topic mix" pie chart card.
  return (
    <>
      <div className="t-eyebrow">Quantitative</div>
      <h2 className="t-h2" style={{ marginTop: 4, marginBottom: 16 }}>Chat analytics</h2>
      <div className="chart-grid">
        <div className="card chart-card" style={{ gridColumn: "span 2" }}>
          <div className="chart-card-head">
            <div className="t-h3">Turn distribution (Gini)</div>
            <span className="badge">target 0.28–0.42</span>
          </div>
          <BarChartPlaceholder label="By session" />
        </div>
      </div>
      <div className="card chart-card">
        <div className="chart-card-head">
          <div className="t-h3">Deliberation variance reduction</div>
          <span className="badge">round 0 → final</span>
        </div>
        <LineChartPlaceholder label="Δ variance across rounds" />
      </div>
    </>
  );
}

function ExportSection() {
  return (
    <>
      <div className="t-eyebrow">Data</div>
      <h2 className="t-h2" style={{ marginTop: 4, marginBottom: 16 }}>Export</h2>
      <div className="card" style={{ padding: 24, maxWidth: 640 }}>
        <div className="col" style={{ gap: 14 }}>
          {["Sessions (JSONL)", "Judge evaluations (CSV)", "Persona profiles (JSON)", "Aggregated metrics (Parquet)"].map(opt => (
            <div key={opt} className="row" style={{ padding: 12, border: "1px solid var(--border-0)", borderRadius: 6 }}>
              <Icons.Database size={16} sw={1.6} style={{ color: "var(--admin)" }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, fontSize: 13 }}>{opt}</div>
                <div className="t-meta" style={{ marginTop: 2 }}>Last generated 18 min ago · 4.2 MB</div>
              </div>
              <Btn variant="outline" size="sm" icon={<Icons.Download size={12} />}>Download</Btn>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

// ─── Judging launcher section (Change 3) ─────────────────────
// Lists eligible sessions; chats already judged are tagged so the admin sees
// at a glance which ones have a cached report.
function JudgingSection({ onJudge, reports }) {
  const { byId } = window.useAgents();
  const [q, setQ] = React.useState("");
  const [allSessions, setAllSessions] = React.useState([]);
  React.useEffect(() => {
    window.api.get("/admin/sessions?limit=100")
      .then(data => setAllSessions(data))
      .catch(() => setAllSessions([]));
  }, []);
  const sessions = allSessions.filter(s =>
    !q || s.id.toLowerCase().includes(q.toLowerCase()) || s.topic.toLowerCase().includes(q.toLowerCase())
  );
  return (
    <>
      <div className="t-eyebrow">Evaluation</div>
      <h2 className="t-h2" style={{ marginTop: 4, marginBottom: 6 }}>Run judging</h2>
      <p className="t-meta" style={{ marginBottom: 16, maxWidth: 620 }}>
        Pick a session and launch the judging pipeline. The report covers persona identification,
        individual + group fidelity, deliberation convergence, and per-group properties as defined
        in <span className="mono">EVAL.md</span>. Once a chat is judged, the report is cached —
        click <strong>View report</strong> to reopen it without re-running the pipeline.
      </p>

      <div className="judge-launcher card">
        <div className="judge-launcher-head">
          <div className="lib-search" style={{ flex: "0 1 360px" }}>
            <span className="lib-search-icon"><Icons.Search size={14} /></span>
            <input
              className="input"
              placeholder="Search by session ID or topic…"
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <div className="t-meta">{sessions.length} eligible session{sessions.length === 1 ? "" : "s"}</div>
        </div>
        <div className="judge-launcher-list">
          {sessions.map(s => {
            const judged = !!reports?.[s.id];
            return (
              <div key={s.id} className="judge-launcher-row">
                <div className="col-mono" style={{ width: 80, color: "var(--fg-1)" }}>{s.id}</div>
                <AvatarStack personas={s.participants.map(id => byId(id)).filter(Boolean)} size="xs" max={4} />
                <div style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.topic}</div>
                <div className="t-meta col-mono" style={{ width: 90 }}>{s.duration}</div>
                <StatusPill status={s.status} />
                {judged && <span className="badge badge-ok"><Icons.Check size={10} sw={2.5} /> Judged</span>}
                <Btn
                  variant={judged ? "outline" : "primary"}
                  size="sm"
                  icon={judged ? <Icons.ChartBar size={12} /> : <Icons.Sparkles size={12} sw={2} />}
                  onClick={() => onJudge(s)}
                >
                  {judged ? "View report" : "Launch judging"}
                </Btn>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

// ─── Judging report modal ────────────────────────────────────
// Pulls per-group properties straight from EVAL.md so the surface here
// mirrors the pipeline 1:1.
const EVAL_GROUPS = [
  {
    id: "persona_id",
    label: "Persona Identification",
    summary: "Can judges correctly guess which anonymous author tag corresponds to which persona?",
    props: [
      { k: "Accuracy",                     desc: "Correct guesses / total guesses, per judge + aggregated." },
      { k: "Binomial exact CI (95%)",      desc: "Clopper-Pearson interval around aggregate accuracy." },
      { k: "p-value vs 12.5% baseline",    desc: "One-sided binomial test, H₀ = random (1/8)." },
      { k: "Confusion matrix (8×8)",       desc: "True persona × predicted tag — diagonal = correct." },
      { k: "Chi-square on off-diagonal",   desc: "Are mistakes systematic or random?" },
    ],
  },
  {
    id: "individual_fidelity",
    label: "Individual Fidelity",
    summary: "How convincingly did each agent portray its persona? 1–5 judge scores against true author.",
    props: [
      { k: "Median (preferred over mean)", desc: "Ordinal 1–5 scores, robust to skew." },
      { k: "IQR (Q3 − Q1)",                desc: "Judge disagreement per persona." },
      { k: "Variance + std",               desc: "Sample variance (ddof=1) and standard deviation." },
      { k: "Bootstrap 95% CI on median",   desc: "10,000 resamples with replacement." },
      { k: "Judge-type pairwise MAD",      desc: "Style ↔ ideology ↔ general ↔ behavioral agreement." },
    ],
  },
  {
    id: "group_fidelity",
    label: "Group Fidelity",
    summary: "Does the group chat look like a real group chat — turn distribution and topic diversity?",
    props: [
      { k: "Gini coefficient",             desc: "Inequality across agent turn counts. Real-world target 0.28–0.42." },
      { k: "z-score vs reference",         desc: "z = (gini − 0.33) / 0.05." },
      { k: "Bootstrap 95% CI on Gini",     desc: "10,000-resample non-parametric CI." },
      { k: "Cosine distance matrix (8×8)", desc: "Pairwise 1 − cosine_sim on averaged message embeddings." },
      { k: "Drift score (optional)",       desc: "Mean pairwise cosine sim of last messages; > 0.85 triggers perturbation." },
    ],
  },
  {
    id: "deliberation",
    label: "Deliberation",
    summary: "When judges discuss disagreements (Phase 2), do they converge — and do more-confident judges get more accurate?",
    props: [
      { k: "Variance reduction",           desc: "Round 0 vs final-round rating variance per case." },
      { k: "F-test on variance",           desc: "Significance of variance drop (p < 0.05)." },
      { k: "Convergence rate + CI",        desc: "n_converged / n_total with two-sided binomial CI." },
      { k: "Δconfidence vs Δaccuracy",     desc: "Pearson r; positive → well-calibrated, negative → overconfidence." },
      { k: "Calibration curve",            desc: "Accuracy at each self-reported confidence level 1–5." },
    ],
  },
];

function JudgingModal({ session, cached, onClose, onSaveReport }) {
  const { byId } = window.useAgents();
  const [tab, setTab] = React.useState("persona_id");
  const [stage, setStage] = React.useState(cached ? "done" : "running");
  const [progress, setProgress] = React.useState(cached ? 100 : 0);
  const [report, setReport] = React.useState(cached || null);
  // Bumps every time the admin asks for a fresh re-run from inside the modal.
  const [runKey, setRunKey] = React.useState(0);

  // Keep refs to the latest values without making them effect dependencies.
  // The pipeline effect should ONLY re-fire when the session or runKey changes —
  // otherwise saving a fresh report (which updates `cached` upstream) would
  // re-trigger the effect and kick off another run, looping forever.
  const cachedRef = React.useRef(cached);
  const onSaveReportRef = React.useRef(onSaveReport);
  React.useEffect(() => { cachedRef.current = cached; }, [cached]);
  React.useEffect(() => { onSaveReportRef.current = onSaveReport; }, [onSaveReport]);

  // ─── pipeline simulation ──────────────────────────────────
  React.useEffect(() => {
    if (!session) return;
    // First open for a session AND a cached report exists → show it as-is.
    if (runKey === 0 && cachedRef.current && cachedRef.current.sessionId === session.id) {
      setReport(cachedRef.current);
      setStage("done");
      setProgress(100);
      setTab("persona_id");
      return;
    }

    // Otherwise: run the pipeline. Seeds change with runKey so re-runs differ.
    setStage("running");
    setProgress(0);
    setTab("persona_id");

    const baseSeed = session.id.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
    let s = (baseSeed + runKey * 1009) || 1;
    const rng = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };

    const personaIds = session.participants || [];
    const accuracy = 0.34 + rng() * 0.35;
    const ciLow = Math.max(0.125, accuracy - 0.08);
    const ciHigh = Math.min(0.99, accuracy + 0.08);
    const pValue = accuracy > 0.4 ? 0.001 + rng() * 0.01 : 0.04 + rng() * 0.08;

    const fidelityRows = personaIds.map(pid => {
      const median = 2.4 + rng() * 2.4;
      const iqr = 0.4 + rng() * 1.2;
      const ciL = Math.max(1, median - 0.5 - rng() * 0.4);
      const ciH = Math.min(5, median + 0.4 + rng() * 0.4);
      return { personaId: pid, median, iqr, ciL, ciH };
    });

    const gini = 0.24 + rng() * 0.28;
    const giniZ = (gini - 0.33) / 0.05;
    const giniCI = [Math.max(0, gini - 0.05), Math.min(1, gini + 0.05)];
    const driftScore = 0.55 + rng() * 0.28;

    const convergenceRate = 0.55 + rng() * 0.35;
    const convCIL = Math.max(0, convergenceRate - 0.1);
    const convCIH = Math.min(1, convergenceRate + 0.08);
    const pearson = -0.15 + rng() * 0.85;
    const fTestP = 0.005 + rng() * 0.06;
    const calibration = [1, 2, 3, 4, 5].map(c => ({ c, acc: Math.min(0.98, 0.18 + c * 0.13 + (rng() - 0.5) * 0.08) }));

    const N = 8;
    const cm = Array.from({ length: N }, (_, i) =>
      Array.from({ length: N }, (_, j) => {
        if (i === j) return Math.round(8 + accuracy * 10 + (rng() - 0.5) * 2);
        return Math.round(rng() * 3);
      })
    );
    const turnShares = personaIds.map((pid, i) => ({
      personaId: pid,
      share: 0.05 + (Math.sin(i * 1.7 + gini * 10) + 1.2) * 0.12,
    }));

    const fresh = {
      sessionId: session.id,
      ranAt: new Date().toISOString(),
      accuracy, ciLow, ciHigh, pValue, cm,
      fidelityRows,
      gini, giniZ, giniCI, driftScore, turnShares,
      convergenceRate, convCIL, convCIH, pearson, fTestP, calibration,
    };

    // Animated progress bar — when it hits 100%, commit the report.
    let p = 0;
    const t = setInterval(() => {
      p += 8 + Math.random() * 12;
      if (p >= 100) {
        setProgress(100);
        setReport(fresh);
        setStage("done");
        onSaveReportRef.current?.(session.id, fresh);
        clearInterval(t);
      } else {
        setProgress(p);
      }
    }, 140);
    return () => clearInterval(t);
    // Intentionally NOT depending on `cached` / `onSaveReport` — see refs above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.id, runKey]);

  // Reset run key when switching to a different session.
  React.useEffect(() => {
    setRunKey(0);
  }, [session?.id]);

  if (!session) return null;
  const personas = (session.participants || []).map(id => byId(id)).filter(Boolean);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-judge" onClick={e => e.stopPropagation()} style={{ width: 880 }}>
        <div className="modal-head" style={{ flexDirection: "column", alignItems: "stretch", gap: 10, paddingBottom: 0 }}>
          <div className="row" style={{ alignItems: "flex-start" }}>
            <div style={{ flex: 1 }}>
              <div className="t-eyebrow">Judging report</div>
              <div className="t-h2" style={{ marginTop: 2 }}>{session.topic}</div>
              <div className="row t-meta" style={{ marginTop: 6, gap: 10 }}>
                <span className="mono">{session.id}</span>
                <span className="dot-sep" />
                <AvatarStack personas={personas} size="xs" max={6} />
                <span className="mono">{personas.length} agents</span>
                <span className="dot-sep" />
                <StatusPill status={session.status} />
                {stage === "done" && report?.ranAt && (
                  <>
                    <span className="dot-sep" />
                    <span className="mono">judged · {new Date(report.ranAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  </>
                )}
              </div>
            </div>
            <IconBtn icon={<Icons.X size={14} />} onClick={onClose} />
          </div>
          {stage === "running" ? (
            <div className="judge-progress">
              <div className="judge-progress-row">
                <Icons.Sparkles size={13} sw={2} style={{ color: "var(--admin)" }} />
                <span className="mono" style={{ fontSize: 11, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--admin)" }}>
                  Pipeline running
                </span>
                <span className="spacer" />
                <span className="mono" style={{ fontSize: 11, color: "var(--fg-2)" }}>{Math.round(progress)}%</span>
              </div>
              <div className="judge-progress-bar"><div style={{ width: `${progress}%` }} /></div>
              <div className="judge-progress-steps">
                {["Bootstrap", "Persona ID", "Fidelity", "Group", "Deliberation"].map((label, i) => (
                  <span key={label} className={`judge-progress-step ${progress > i * 20 ? "done" : ""}`}>
                    {progress > i * 20 ? <Icons.Check size={10} /> : <Icons.Dot size={10} />}
                    {label}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="judge-tabs">
              {EVAL_GROUPS.map(g => (
                <button
                  key={g.id}
                  className={`judge-tab ${tab === g.id ? "active" : ""}`}
                  onClick={() => setTab(g.id)}
                >
                  {g.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="modal-body" style={{ background: "var(--bg-0)" }}>
          {stage === "running" && (
            <div className="judge-running-body">
              <div className="t-meta">Resampling 10,000× per metric. Computing bootstrap CIs.</div>
            </div>
          )}

          {stage === "done" && report && tab === "persona_id" && (
            <ReportPersonaID
              group={EVAL_GROUPS[0]}
              accuracy={report.accuracy} ciLow={report.ciLow} ciHigh={report.ciHigh} pValue={report.pValue}
              cm={report.cm} personas={personas}
            />
          )}
          {stage === "done" && report && tab === "individual_fidelity" && (
            <ReportIndividualFidelity
              group={EVAL_GROUPS[1]}
              rows={report.fidelityRows.map(r => ({ ...r, persona: byId(r.personaId) })).filter(r => r.persona)}
            />
          )}
          {stage === "done" && report && tab === "group_fidelity" && (
            <ReportGroupFidelity
              group={EVAL_GROUPS[2]}
              gini={report.gini} giniZ={report.giniZ} giniCI={report.giniCI} driftScore={report.driftScore}
              turnShares={report.turnShares}
            />
          )}
          {stage === "done" && report && tab === "deliberation" && (
            <ReportDeliberation
              group={EVAL_GROUPS[3]}
              convergenceRate={report.convergenceRate} convCIL={report.convCIL} convCIH={report.convCIH}
              pearson={report.pearson} fTestP={report.fTestP} calibration={report.calibration}
            />
          )}
        </div>

        <div className="modal-foot">
          <Btn variant="ghost" onClick={onClose}>Close</Btn>
          {stage === "done" && (
            <>
              <Btn variant="outline" icon={<Icons.Download size={12} />}>Export JSON</Btn>
              {/* Re-judge: the ONLY way to re-run the pipeline once a report is cached. */}
              <Btn
                variant="primary"
                icon={<Icons.Sparkles size={12} sw={2} />}
                onClick={() => setRunKey(k => k + 1)}
                title="Re-run the judging pipeline for this chat"
              >
                Launch judging again
              </Btn>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Report tabs ─────────────────────────────────────────────
function ReportHeader({ group }) {
  return (
    <div className="report-head">
      <div>
        <div className="t-h3">{group.label}</div>
        <div className="t-meta" style={{ marginTop: 4, maxWidth: 640 }}>{group.summary}</div>
      </div>
    </div>
  );
}

function MetricStat({ label, value, sub, tone = "default" }) {
  return (
    <div className={`metric-stat metric-stat-${tone}`}>
      <div className="metric-stat-label">{label}</div>
      <div className="metric-stat-value">{value}</div>
      {sub && <div className="metric-stat-sub">{sub}</div>}
    </div>
  );
}

function PropsList({ group }) {
  return (
    <div className="props-list">
      <div className="t-eyebrow" style={{ marginBottom: 8 }}>Properties evaluated</div>
      {group.props.map(p => (
        <div key={p.k} className="props-row">
          <Icons.Check size={11} sw={2.5} style={{ color: "var(--admin)" }} />
          <span className="mono props-key">{p.k}</span>
          <span className="props-desc">{p.desc}</span>
        </div>
      ))}
    </div>
  );
}

function ReportPersonaID({ group, accuracy, ciLow, ciHigh, pValue, cm, personas }) {
  return (
    <>
      <ReportHeader group={group} />
      <div className="metric-row">
        <MetricStat
          label="Aggregate accuracy"
          value={`${(accuracy * 100).toFixed(1)}%`}
          sub={`vs 12.5% baseline · ×${(accuracy / 0.125).toFixed(2)}`}
          tone={accuracy > 0.25 ? "good" : "warn"}
        />
        <MetricStat
          label="Binomial CI (95%)"
          value={`${(ciLow * 100).toFixed(1)} – ${(ciHigh * 100).toFixed(1)}%`}
          sub="Clopper-Pearson exact"
        />
        <MetricStat
          label="p-value"
          value={pValue < 0.001 ? "<0.001" : pValue.toFixed(3)}
          sub={pValue < 0.05 ? "Reject H₀ — above random" : "Inconclusive"}
          tone={pValue < 0.05 ? "good" : "warn"}
        />
      </div>

      <div className="t-eyebrow" style={{ margin: "20px 0 8px" }}>Confusion matrix (true × predicted)</div>
      <div className="cm-wrap">
        <table className="cm-table">
          <thead>
            <tr>
              <th></th>
              {Array.from({ length: cm.length }).map((_, j) => (
                <th key={j} className="mono">P{j + 1}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cm.map((row, i) => {
              const max = Math.max(...row);
              return (
                <tr key={i}>
                  <th className="mono">P{i + 1}</th>
                  {row.map((v, j) => {
                    const intensity = max ? v / max : 0;
                    const isDiag = i === j;
                    const bg = isDiag
                      ? `rgba(245,158,11,${0.15 + intensity * 0.6})`
                      : `rgba(124,124,140,${intensity * 0.35})`;
                    return (
                      <td key={j} style={{ background: bg, color: isDiag && intensity > 0.6 ? "#fff" : "var(--fg-1)" }}>
                        {v}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <PropsList group={group} />
    </>
  );
}

function ReportIndividualFidelity({ group, rows }) {
  return (
    <>
      <ReportHeader group={group} />
      <table className="table fidelity-table">
        <thead>
          <tr>
            <th>Persona</th>
            <th style={{ width: 100 }}>Median</th>
            <th style={{ width: 100 }}>IQR</th>
            <th style={{ width: 160 }}>Bootstrap CI</th>
            <th>Score distribution</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.persona.id}>
              <td>
                <div className="row" style={{ gap: 10 }}>
                  <Avatar persona={r.persona} size="sm" />
                  <div className="mono" style={{ fontSize: 12, fontWeight: 600 }}>{r.persona.name}</div>
                </div>
              </td>
              <td className="col-mono">{r.median.toFixed(2)}</td>
              <td className="col-mono">{r.iqr.toFixed(2)}</td>
              <td className="col-mono">[{r.ciL.toFixed(2)}, {r.ciH.toFixed(2)}]</td>
              <td>
                <div style={{ display: "flex", gap: 4, height: 28, alignItems: "flex-end" }}>
                  {[1, 2, 3, 4, 5].map(s => {
                    // distance-weighted height; the closer to median, the taller.
                    const d = Math.abs(s - r.median);
                    const h = Math.max(4, 28 - d * 11);
                    const active = s >= Math.floor(r.median) && s <= Math.ceil(r.median);
                    return (
                      <div key={s} style={{
                        flex: 1, height: h, borderRadius: 2,
                        background: active ? "var(--admin)" : "var(--bg-3)",
                        opacity: active ? 0.9 : 0.7,
                      }} />
                    );
                  })}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <PropsList group={group} />
    </>
  );
}

function ReportGroupFidelity({ group, gini, giniZ, giniCI, driftScore, turnShares }) {
  const { byId } = window.useAgents();
  const inRange = gini >= 0.28 && gini <= 0.42;
  const rows = (turnShares || []).map(t => ({ ...t, persona: byId(t.personaId) })).filter(r => r.persona);
  return (
    <>
      <ReportHeader group={group} />
      <div className="metric-row">
        <MetricStat
          label="Gini coefficient"
          value={gini.toFixed(3)}
          sub={inRange ? "In real-world range" : "Outside 0.28–0.42"}
          tone={inRange ? "good" : "warn"}
        />
        <MetricStat
          label="z-score vs reference"
          value={giniZ.toFixed(2)}
          sub="μ = 0.33, σ = 0.05"
        />
        <MetricStat
          label="Bootstrap CI (95%)"
          value={`${giniCI[0].toFixed(2)} – ${giniCI[1].toFixed(2)}`}
          sub="10,000 resamples"
        />
        <MetricStat
          label="Drift score"
          value={driftScore.toFixed(2)}
          sub={driftScore > 0.85 ? "Perturbation triggered" : "Below threshold"}
          tone={driftScore > 0.85 ? "warn" : "good"}
        />
      </div>

      <div className="t-eyebrow" style={{ margin: "20px 0 8px" }}>Turn distribution</div>
      <div className="turn-dist">
        {rows.map(r => (
          <div key={r.persona.id} className="turn-row">
            <Avatar persona={r.persona} size="xs" />
            <div className="mono" style={{ width: 140, fontSize: 11, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.persona.name}</div>
            <div className="turn-bar"><div style={{ width: `${r.share * 100}%`, background: r.persona.color }} /></div>
            <div className="mono" style={{ width: 50, textAlign: "right", fontSize: 11, color: "var(--fg-1)" }}>{(r.share * 100).toFixed(1)}%</div>
          </div>
        ))}
      </div>

      <PropsList group={group} />
    </>
  );
}

function ReportDeliberation({ group, convergenceRate, convCIL, convCIH, pearson, fTestP, calibration }) {
  const calibrated = pearson > 0;
  return (
    <>
      <ReportHeader group={group} />
      <div className="metric-row">
        <MetricStat
          label="Convergence rate"
          value={`${(convergenceRate * 100).toFixed(1)}%`}
          sub={`CI [${(convCIL * 100).toFixed(0)}, ${(convCIH * 100).toFixed(0)}]%`}
          tone={convergenceRate > 0.6 ? "good" : "warn"}
        />
        <MetricStat
          label="F-test p-value"
          value={fTestP < 0.001 ? "<0.001" : fTestP.toFixed(3)}
          sub={fTestP < 0.05 ? "Significant variance drop" : "Not significant"}
          tone={fTestP < 0.05 ? "good" : "warn"}
        />
        <MetricStat
          label="Δconf vs Δacc (Pearson r)"
          value={pearson.toFixed(2)}
          sub={calibrated ? "Well calibrated" : "Overconfidence flag"}
          tone={calibrated ? "good" : "warn"}
        />
      </div>

      <div className="t-eyebrow" style={{ margin: "20px 0 8px" }}>Calibration curve</div>
      <div className="calibration">
        {calibration.map(({ c, acc }) => (
          <div key={c} className="cal-col">
            <div className="cal-bar-wrap">
              <div className="cal-bar" style={{ height: `${acc * 100}%` }} />
            </div>
            <div className="mono cal-label">conf {c}</div>
            <div className="mono cal-val">{(acc * 100).toFixed(0)}%</div>
          </div>
        ))}
      </div>

      <PropsList group={group} />
    </>
  );
}

// ─── Admin shell ─────────────────────────────────────────────
function AdminDashboard({ section, onSection, chats, onNewGroup, onNewDM }) {
  const [judging, setJudging] = React.useState(null);
  // sessionId → cached report. Persists for the life of the session so the
  // admin can reopen a judged chat without re-running the pipeline.
  const [reports, setReports] = React.useState({});
  const openJudging = (s) => setJudging(s);
  const closeJudging = () => setJudging(null);
  const saveReport = React.useCallback((sessionId, report) => {
    setReports(r => ({ ...r, [sessionId]: report }));
  }, []);

  return (
    <div className="admin-shell" data-screen-label="admin-dashboard">
      <AdminSidebar section={section} onSelect={onSection} />
      <main className="admin-main">
        <div className="admin-header">
          <div>
            <div className="t-eyebrow">8 Angry Agents · {section}</div>
            <h1 className="t-h1" style={{ marginTop: 4 }}>
              {section === "overview" && "Overview"}
              {section === "analytics" && "Chat Analytics"}
              {section === "performance" && "Agent Performance"}
              {section === "sessions" && "Session Log"}
              {section === "judging" && "Judging"}
              {section === "export" && "Export"}
            </h1>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <span className="badge badge-admin">
              <Icons.Crown size={11} /> Admin
            </span>
            <Btn variant="outline" size="sm" icon={<Icons.Calendar size={12} />}>May 19, 2026</Btn>
            <Btn
              variant="outline"
              size="sm"
              icon={<Icons.User size={12} />}
              onClick={onNewDM}
              title="Create a new 1:1 chat with an agent"
            >
              New DM
            </Btn>
            <Btn
              variant="outline"
              size="sm"
              icon={<Icons.Users size={12} />}
              onClick={onNewGroup}
              title="Create a new group chat session"
            >
              New group
            </Btn>
            <Btn
              variant="primary"
              size="sm"
              icon={<Icons.Sparkles size={12} sw={2} />}
              onClick={() => onSection("judging")}
            >
              Launch judging
            </Btn>
          </div>
        </div>

        {section === "overview" && (
          <>
            <OverviewSection />
            <RecentSessionsTable onJudge={openJudging} reports={reports} />
          </>
        )}
        {section === "analytics" && <ChatAnalyticsSection />}
        {section === "performance" && <AgentPerformanceSection />}
        {section === "sessions" && <RecentSessionsTable onJudge={openJudging} reports={reports} />}
        {section === "judging" && <JudgingSection onJudge={openJudging} reports={reports} />}
        {section === "export" && <ExportSection />}
      </main>

      <JudgingModal
        session={judging}
        cached={judging ? reports[judging.id] : null}
        onClose={closeJudging}
        onSaveReport={saveReport}
      />
    </div>
  );
}

window.AdminDashboard = AdminDashboard;
