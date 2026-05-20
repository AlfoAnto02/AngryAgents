// screens-admin.jsx — Admin Dashboard

function AdminSidebar({ section, onSelect }) {
  const items = [
    { id: "overview", label: "Overview", icon: <Icons.ChartBar size={14} /> },
    { id: "analytics", label: "Chat Analytics", icon: <Icons.ChartLine size={14} /> },
    { id: "performance", label: "Agent Performance", icon: <Icons.Brain size={14} /> },
    { id: "sessions", label: "Session Log", icon: <Icons.Database size={14} /> },
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
            Actions in this area are audited. Switch to User View to chat as yourself.
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

function OverviewSection() {
  const [kpis, setKpis] = React.useState(null);
  React.useEffect(() => {
    window.api.get("/admin/overview")
      .then(data => {
        setKpis([
          { label: "Sessions today", value: String(data.sessions_today.value), delta: `${data.sessions_today.delta_pct >= 0 ? "+" : ""}${data.sessions_today.delta_pct}%`, up: data.sessions_today.delta_pct >= 0, spark: data.sessions_today.spark },
          { label: "Active users", value: String(data.active_users.value), delta: `${data.active_users.delta_pct >= 0 ? "+" : ""}${data.active_users.delta_pct}%`, up: data.active_users.delta_pct >= 0, spark: data.active_users.spark },
          { label: "Avg. session", value: String(data.avg_session.value), delta: `${data.avg_session.delta_pct >= 0 ? "+" : ""}${data.avg_session.delta_pct}%`, up: data.avg_session.delta_pct >= 0, spark: data.avg_session.spark },
          { label: "Judge confidence", value: String(data.judge_confidence.value), delta: `${data.judge_confidence.delta_abs >= 0 ? "+" : ""}${data.judge_confidence.delta_abs}`, up: data.judge_confidence.delta_abs >= 0, spark: data.judge_confidence.spark },
        ]);
      })
      .catch(() => setKpis([]));
  }, []);

  if (!kpis) return <div style={{ padding: 24, color: "var(--fg-2)" }}>Loading…</div>;

  return (
    <>
      <div className="kpi-grid">
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

        <div className="card chart-card">
          <div className="chart-card-head">
            <div className="t-h3">Judge role mix</div>
            <Icons.More size={14} />
          </div>
          <PieChartPlaceholder label="Metrics coming soon" />
        </div>
      </div>

      <div className="card chart-card" style={{ marginBottom: 24 }}>
        <div className="chart-card-head">
          <div className="t-h3">Persona ID accuracy <span className="t-meta">(rolling 7d)</span></div>
          <span className="badge">baseline 12.5%</span>
        </div>
        <LineChartPlaceholder label="Metrics coming soon" />
      </div>
    </>
  );
}

function RecentSessionsTable() {
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
              <th style={{ width: 40 }}></th>
            </tr>
          </thead>
          <tbody>
            {sessions.map(s => {
              const personas = s.participants.map(id => byId(id)).filter(Boolean);
              return (
                <tr key={s.id}>
                  <td className="col-mono">{s.id}</td>
                  <td>
                    <div className="row" style={{ gap: 8 }}>
                      <AvatarStack personas={personas} size="xs" max={4} />
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
                    <IconBtn size="sm" icon={<Icons.ChevronRight size={13} />} />
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
          <FidelityBar value={entry.group_fidelity / 5} label={Number(entry.group_fidelity).toFixed(2)} color="#7c3aed" />
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
  return (
    <>
      <div className="t-eyebrow">Quantitative</div>
      <h2 className="t-h2" style={{ marginTop: 4, marginBottom: 16 }}>Chat analytics</h2>
      <div className="chart-grid">
        <div className="card chart-card">
          <div className="t-h3">Turn distribution (Gini)</div>
          <BarChartPlaceholder label="Metrics coming soon" />
        </div>
        <div className="card chart-card">
          <div className="t-h3">Topic mix</div>
          <PieChartPlaceholder label="Metrics coming soon" />
        </div>
      </div>
      <div className="card chart-card">
        <div className="t-h3">Deliberation variance reduction</div>
        <LineChartPlaceholder label="Metrics coming soon" />
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

function AdminDashboard({ section, onSection }) {
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
              {section === "export" && "Export"}
            </h1>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <span className="badge badge-admin">
              <Icons.Crown size={11} /> Admin
            </span>
            <Btn variant="outline" size="sm" icon={<Icons.Calendar size={12} />}>May 19, 2026</Btn>
            <Btn
              variant="primary"
              size="sm"
              icon={<Icons.Plus size={12} sw={2.5} />}
              onClick={() => {}}
            >
              Add new agent
            </Btn>
            <Btn variant="outline" size="sm" icon={<Icons.Download size={12} />}>Export</Btn>
          </div>
        </div>

        {section === "overview" && (
          <>
            <OverviewSection />
            <RecentSessionsTable />
          </>
        )}
        {section === "analytics" && <ChatAnalyticsSection />}
        {section === "performance" && <AgentPerformanceSection />}
        {section === "sessions" && <RecentSessionsTable />}
        {section === "export" && <ExportSection />}
      </main>
    </div>
  );
}

window.AdminDashboard = AdminDashboard;
