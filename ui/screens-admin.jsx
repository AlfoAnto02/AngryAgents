// screens-admin.jsx — Admin Dashboard
// Changes:
//   • Overview: removed "Avg. session", "Judge confidence", "Persona ID accuracy";
//     renamed "Judge role mix" → "Judge Accuracy".
//   • Chat Analytics: removed "Topic mix".
//   • Added Judging launcher (per-session + a top-level CTA) with a full report modal.

function AdminSidebar({ section, onSelect, isOpen }) {
  const items = [
    { id: "overview", label: "Overview", icon: <Icons.ChartBar size={14} /> },
    { id: "analytics", label: "Chat Analytics", icon: <Icons.ChartLine size={14} /> },
    { id: "performance", label: "Agent Performance", icon: <Icons.Brain size={14} /> },
    { id: "sessions", label: "Session Log", icon: <Icons.Database size={14} /> },
  ];
  return (
    <aside className={`admin-sidebar${isOpen ? " open" : ""}`}>
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

// ─── Admin Home (Overview) ────────────────────────────────────
function AdminHomeSection({ user, onSection, onNav, chats }) {
  const { agents } = window.useAgents();
  const [kpis, setKpis] = React.useState(null);

  React.useEffect(() => {
    window.api.get("/admin/overview")
      .then(data => setKpis({
        sessions: data.sessions_today.value,
        users: data.active_users.value,
      }))
      .catch(() => setKpis({ sessions: 0, users: 0 }));
  }, []);

  const tileStyle = {
    textAlign: "left", padding: 24, display: "flex", flexDirection: "column",
    gap: 18, cursor: "pointer", background: "var(--bg-1)",
    border: "1px solid var(--border-0)", borderRadius: 8, minHeight: 180,
    fontFamily: "inherit", color: "inherit",
  };
  const iconBox = (extra = {}) => ({
    width: 40, height: 40, borderRadius: 6,
    background: "var(--admin-soft)", color: "var(--admin)",
    display: "flex", alignItems: "center", justifyContent: "center",
    border: "1px solid var(--admin-border)", ...extra,
  });

  return (
    <div style={{ flex: 1, overflowY: "auto" }}>
      <div style={{ maxWidth: 980, margin: "0 auto", padding: "48px 0 64px" }}>

        {/* Hero */}
        <div style={{ marginBottom: 36 }}>
          <div className="t-eyebrow">Welcome back, {user?.name?.split(" ")[0] || "Admin"}</div>
          <h1 style={{ fontFamily: "var(--font-mono)", fontSize: 40, fontWeight: 600, letterSpacing: "-0.01em", margin: "10px 0 6px" }}>
            Admin Console
          </h1>
          <p style={{ fontSize: 14, color: "var(--fg-2)", margin: 0, maxWidth: 520 }}>
            Manage sessions, evaluate personas, browse agents and monitor analytics.
          </p>
        </div>

        {/* 4 tiles */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 28 }}>

          {/* Agents tile */}
          <button className="card card-hov" onClick={() => onNav?.("library")} style={tileStyle}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={iconBox()}><Icons.Library size={20} sw={1.6} /></div>
              <Icons.ArrowRight size={16} style={{ color: "var(--fg-2)" }} />
            </div>
            <div>
              <div className="t-eyebrow">01 — Browse</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 600, marginTop: 4 }}>Agents</div>
              <div className="t-meta" style={{ marginTop: 6, fontSize: 13 }}>
                {agents.length} personas in the library · search and filter.
              </div>
            </div>
          </button>

          {/* Sessions tile */}
          <button className="card card-hov" onClick={() => onSection("sessions")} style={tileStyle}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={iconBox()}><Icons.Database size={20} sw={1.6} /></div>
              <Icons.ArrowRight size={16} style={{ color: "var(--fg-2)" }} />
            </div>
            <div>
              <div className="t-eyebrow">02 — Evaluate</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 600, marginTop: 4 }}>Session Log</div>
              <div className="t-meta" style={{ marginTop: 6, fontSize: 13 }}>
                Launch the judging pipeline · view cached reports.
              </div>
            </div>
            {kpis && (
              <div style={{ marginTop: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
                <span className="badge">{kpis.sessions} sessions today</span>
                <span className="badge">{kpis.users} active users</span>
              </div>
            )}
          </button>

          {/* Analytics tile */}
          <button className="card card-hov" onClick={() => onSection("analytics")} style={tileStyle}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={iconBox()}><Icons.ChartLine size={20} sw={1.6} /></div>
              <Icons.ArrowRight size={16} style={{ color: "var(--fg-2)" }} />
            </div>
            <div>
              <div className="t-eyebrow">03 — Analyse</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 600, marginTop: 4 }}>Chat Analytics</div>
              <div className="t-meta" style={{ marginTop: 6, fontSize: 13 }}>
                Turn distribution · Gini coefficient · agent performance.
              </div>
            </div>
          </button>

          {/* Agent Performance tile */}
          <button className="card card-hov" onClick={() => onSection("performance")} style={tileStyle}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={iconBox()}><Icons.Brain size={20} sw={1.6} /></div>
              <Icons.ArrowRight size={16} style={{ color: "var(--fg-2)" }} />
            </div>
            <div>
              <div className="t-eyebrow">04 — Monitor</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 600, marginTop: 4 }}>Agent Performance</div>
              <div className="t-meta" style={{ marginTop: 6, fontSize: 13 }}>
                Per-agent fidelity scores · individual and group metrics.
              </div>
            </div>
          </button>
        </div>

        {/* Quick start */}
        <div style={{
          padding: "14px 16px", background: "var(--bg-1)", border: "1px solid var(--border-0)",
          borderRadius: 6, display: "flex", alignItems: "center", gap: 12, marginBottom: 36,
        }}>
          <Icons.Sparkles size={16} sw={1.6} style={{ color: "var(--admin)" }} />
          <div style={{ flex: 1, fontSize: 13 }}>
            <strong style={{ fontWeight: 500 }}>Quick start.</strong>{" "}
            <span className="t-dim">Create a new session to evaluate.</span>
          </div>
          <Btn variant="outline" size="sm" icon={<Icons.MessageDots size={12} />} onClick={() => onNav?.("newdm")}>
            New DM
          </Btn>
          <Btn variant="primary" size="sm" icon={<Icons.Users size={12} />} onClick={() => onNav?.("newgroup")}>
            New group chat
          </Btn>
        </div>

      </div>
    </div>
  );
}

// ─── Sessions table (with optional per-row Judge / View report action) ─────
function RecentSessionsTable({ onJudge, reports, onOpenChat }) {
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
        </div>
      </div>
      {sessions.length === 0 ? (
        <Empty title="No sessions yet" sub="Sessions appear here once users start chatting." icon={<Icons.Database size={20} />} />
      ) : (
      <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th>Session ID</th>
            <th>Participants</th>
            <th>Topic</th>
            <th style={{ width: 110 }}>Duration</th>
            <th style={{ width: 150 }}>Date</th>
            <th style={{ width: 130 }}>Status</th>
            <th style={{ width: 230 }}></th>
          </tr>
        </thead>
        <tbody>
          {sessions.map(s => {
            const judged = !!reports?.[s.id];
            return (
              <tr key={s.id}>
                <td className="col-mono">{s.display_id}</td>
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
                    {onOpenChat && (
                      <Btn
                        variant="outline"
                        size="sm"
                        icon={<Icons.MessageDots size={12} />}
                        onClick={() => onOpenChat(s)}
                        title="Open this chat and post as a participant"
                      >
                        Open
                      </Btn>
                    )}
                    {s.participants.length > 1 && (judged ? (
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
                    ))}
                    <IconBtn size="sm" icon={<Icons.ChevronRight size={13} />} />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
      )}
    </div>
  );
}

function AgentPerformanceSection() {
  const { byId } = window.useAgents();
  const [perf, setPerf] = React.useState([]);
  const [reports, setReports] = React.useState(null);
  const [sortKey, setSortKey] = React.useState("individual_fidelity");
  const [sortDir, setSortDir] = React.useState(-1); // -1 desc, 1 asc

  React.useEffect(() => {
    Promise.all([
      window.api.get("/admin/agent-performance"),
      window.api.get("/admin/judged-chats"),
    ]).then(([p, r]) => { setPerf(p); setReports(r); })
      .catch(() => {});
  }, []);

  // Compute per-agent fidelity from judged-chats reports
  const agentIndFid = {}; // agentId -> [score, ...]
  const agentGrpFid = {}; // agentId -> [score, ...]
  if (reports) {
    Object.values(reports).forEach(rep => {
      (rep.fidelityRows || []).forEach(row => {
        if (!agentIndFid[row.personaId]) agentIndFid[row.personaId] = [];
        agentIndFid[row.personaId].push(row.mean ?? 0);
      });
      const grp = rep.groupFidelityMean ?? 0;
      (rep.turnShares || []).forEach(ts => {
        if (!agentGrpFid[ts.personaId]) agentGrpFid[ts.personaId] = [];
        agentGrpFid[ts.personaId].push(grp);
      });
    });
  }
  const avg = arr => arr && arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0;

  const enriched = perf.map(e => ({
    ...e,
    individual_fidelity: avg(agentIndFid[e.agent_id]),
    group_fidelity: avg(agentGrpFid[e.agent_id]),
    judged_sessions: (agentIndFid[e.agent_id] || []).length,
  })).filter(e => byId(e.agent_id));

  const sorted = [...enriched].sort((a, b) => {
    const aHas = a.judged_sessions > 0, bHas = b.judged_sessions > 0;
    if (aHas !== bHas) return aHas ? -1 : 1; // unjudged always last
    return sortDir * (a[sortKey] - b[sortKey]);
  });

  const toggleSort = key => {
    if (sortKey === key) setSortDir(d => -d);
    else { setSortKey(key); setSortDir(-1); }
  };
  const SortIcon = ({ k }) => sortKey === k
    ? <span style={{ marginLeft: 3, fontSize: 9 }}>{sortDir < 0 ? "▼" : "▲"}</span>
    : null;

  // KPIs
  const judgedAgents = enriched.filter(e => e.judged_sessions > 0);
  const avgInd = avg(judgedAgents.map(e => e.individual_fidelity));
  const avgGrp = avg(judgedAgents.map(e => e.group_fidelity));
  const totalSessions = enriched.reduce((s, e) => s + e.sessions, 0);

  const SCALE = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"];
  const scoreColor = v => v >= 4 ? SCALE[4] : v >= 3.5 ? SCALE[3] : v >= 2.5 ? SCALE[2] : v >= 1.5 ? SCALE[1] : SCALE[0];

  return (
    <>
      <div className="t-eyebrow">Per-agent fidelity</div>
      <h2 className="t-h2" style={{ marginTop: 4, marginBottom: 16 }}>Agent performance</h2>

      {enriched.length === 0 ? (
        <Empty title="No data yet" sub="Performance stats appear after agents participate in judged chats." icon={<Icons.Brain size={20} />} />
      ) : (
        <>
          {/* ── KPI row ── */}
          <div className="metric-row" style={{ marginBottom: 20 }}>
            <MetricStat label="Active agents" value={enriched.length} sub={`${enriched.filter(e => e.sessions > 0).length} in at least 1 chat`} />
            <MetricStat label="Total sessions" value={totalSessions} sub="across all agents" />
            <MetricStat label="Avg ind. fidelity" value={judgedAgents.length ? avgInd.toFixed(2) : "—"}
              sub={judgedAgents.length ? `${judgedAgents.length} agents judged` : "no judged sessions"}
              tone={avgInd >= 4 ? "good" : avgInd >= 3 ? undefined : "warn"} />
            <MetricStat label="Avg group fidelity" value={judgedAgents.length ? avgGrp.toFixed(2) : "—"}
              sub="avg from judged sessions"
              tone={avgGrp >= 4 ? "good" : avgGrp >= 3 ? undefined : "warn"} />
          </div>

          {/* ── Full table ── */}
          <div className="card" style={{ overflow: "hidden" }}>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Source</th>
                    <th style={{ width: 100, cursor: "pointer" }} onClick={() => toggleSort("sessions")}>
                      Sessions <SortIcon k="sessions" />
                    </th>
                    <th style={{ width: 160, cursor: "pointer" }} onClick={() => toggleSort("individual_fidelity")}>
                      Ind. fidelity <SortIcon k="individual_fidelity" />
                    </th>
                    <th style={{ width: 160, cursor: "pointer" }} onClick={() => toggleSort("group_fidelity")}>
                      Group fidelity <SortIcon k="group_fidelity" />
                    </th>
                    <th style={{ width: 80, cursor: "pointer" }} onClick={() => toggleSort("judged_sessions")}>
                      Judged <SortIcon k="judged_sessions" />
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map(entry => {
                    const p = byId(entry.agent_id);
                    const hasScore = entry.judged_sessions > 0;
                    return (
                      <tr key={entry.agent_id}>
                        <td>
                          <div className="row" style={{ gap: 10 }}>
                            <Avatar persona={p} size="sm" />
                            <div>
                              <div className="mono" style={{ fontSize: 12, fontWeight: 600 }}>{p.name}</div>
                              <div className="t-meta" style={{ fontSize: 10.5 }}>{p.source_title || p.slug}</div>
                            </div>
                          </div>
                        </td>
                        <td style={{ whiteSpace: "nowrap" }}>
                          <span className="badge">{p.source_type === "fiction" ? "Fiction" : "Real-world"}</span>
                        </td>
                        <td className="col-mono">{entry.sessions}</td>
                        <td>
                          {hasScore
                            ? <FidelityBar value={entry.individual_fidelity / 5} label={entry.individual_fidelity.toFixed(2)} color={scoreColor(entry.individual_fidelity)} />
                            : <span className="t-meta" style={{ fontSize: 11 }}>—</span>}
                        </td>
                        <td>
                          {hasScore
                            ? <FidelityBar value={entry.group_fidelity / 5} label={entry.group_fidelity.toFixed(2)} color={scoreColor(entry.group_fidelity)} />
                            : <span className="t-meta" style={{ fontSize: 11 }}>—</span>}
                        </td>
                        <td className="col-mono" style={{ color: entry.judged_sessions > 0 ? "var(--fg-0)" : "var(--fg-3)" }}>
                          {entry.judged_sessions}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
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

// ─── Reusable bar chart (no external lib) ─────────────────────
function BarChart({ data, yMin = 0, yMax = 1, target = null, formatY, chartHeight = 220 }) {
  const fmt = formatY || (v => v.toFixed(2));

  if (!data || data.length === 0) {
    return (
      <div style={{ height: chartHeight, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 12, color: "var(--fg-3)", fontFamily: "var(--font-mono)" }}>
          No judged sessions yet — run the pipeline on at least one session.
        </span>
      </div>
    );
  }

  const VW = 800, VH = chartHeight;
  const ML = 46, MB = 26, MT = 10, MR = 8;
  const cW = VW - ML - MR, cH = VH - MT - MB;
  const sy = v => MT + cH * (1 - (v - yMin) / (yMax - yMin));
  const baseY = sy(yMin);
  const slot = cW / data.length;
  const bW = Math.max(8, slot * 0.55);
  const bX = i => ML + slot * i + (slot - bW) / 2;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(t => yMin + t * (yMax - yMin));

  return (
    <div style={{ height: chartHeight }}>
      <svg viewBox={`0 0 ${VW} ${VH}`} width="100%" height="100%" preserveAspectRatio="none">
        {/* target band */}
        {target && (() => {
          const y1 = sy(Math.min(target.hi, yMax));
          const y2 = sy(Math.max(target.lo, yMin));
          return (
            <>
              <rect x={ML} y={y1} width={cW} height={y2 - y1} fill="rgba(34,197,94,0.09)" />
              <line x1={ML} x2={ML + cW} y1={y1} y2={y1} stroke="rgba(34,197,94,0.4)" strokeWidth="1" strokeDasharray="4 3" />
              <line x1={ML} x2={ML + cW} y1={y2} y2={y2} stroke="rgba(34,197,94,0.4)" strokeWidth="1" strokeDasharray="4 3" />
            </>
          );
        })()}
        {/* grid + y-axis labels */}
        {ticks.map((v, i) => (
          <g key={i}>
            <line x1={ML} x2={ML + cW} y1={sy(v)} y2={sy(v)} stroke="var(--border-0)" strokeWidth="1" strokeDasharray="3 4" />
            <text x={ML - 5} y={sy(v) + 3.5} textAnchor="end" fontSize={9} fill="var(--fg-3)" fontFamily="monospace">{fmt(v)}</text>
          </g>
        ))}
        {/* bars */}
        {data.map((d, i) => {
          const x = bX(i), y = sy(d.value), h = Math.max(2, baseY - y);
          return (
            <g key={i}>
              <rect x={x} y={y} width={bW} height={h} fill={d.color || "var(--admin)"} rx={2} opacity={0.85}>
                <title>{d.tooltip || `${d.label}: ${fmt(d.value)}`}</title>
              </rect>
            </g>
          );
        })}
        {/* x-axis labels */}
        {data.map((d, i) => (
          <text key={i} x={bX(i) + bW / 2} y={VH - 5} textAnchor="middle" fontSize={8} fill="var(--fg-3)" fontFamily="monospace">
            {d.label}
          </text>
        ))}
      </svg>
    </div>
  );
}

// ─── Chat Analytics (real data) ───────────────────────────────
function ChatAnalyticsSection() {
  const [reports, setReports] = React.useState(null);
  const [sessions, setSessions] = React.useState([]);

  React.useEffect(() => {
    Promise.all([
      window.api.get("/admin/judged-chats"),
      window.api.get("/admin/sessions?limit=100"),
    ]).then(([r, s]) => { setReports(r); setSessions(s); })
      .catch(() => {});
  }, []);

  const sessMap = {};
  sessions.forEach(s => { sessMap[s.id] = s; });

  const entries = reports
    ? Object.entries(reports)
        .map(([id, r]) => ({ id: Number(id), r, s: sessMap[Number(id)] }))
        .filter(e => e.s)
        .sort((a, b) => a.id - b.id)
    : [];

  const lbl = e => e.s.display_id || `S-${e.id}`;

  const giniData = entries.map(e => ({
    label: lbl(e), value: e.r.gini ?? 0,
    color: (e.r.gini >= 0.28 && e.r.gini <= 0.42) ? "#22c55e" : "#f97316",
    tooltip: `${lbl(e)} · Gini ${(e.r.gini ?? 0).toFixed(3)}`,
  }));

  const accData = entries.map(e => ({
    label: lbl(e), value: (e.r.accuracy ?? 0) * 100,
    color: (e.r.pValue ?? 1) < 0.05 ? "#22c55e" : "#94a3b8",
    tooltip: `${lbl(e)} · ${((e.r.accuracy ?? 0) * 100).toFixed(1)}% (p=${(e.r.pValue ?? 1).toFixed(3)})`,
  }));

  const grpData = entries.map(e => ({
    label: lbl(e), value: e.r.groupFidelityMean ?? 0,
    color: (e.r.groupFidelityMean ?? 0) >= 4 ? "#22c55e" : (e.r.groupFidelityMean ?? 0) >= 3 ? "#eab308" : "#ef4444",
    tooltip: `${lbl(e)} · Group fidelity ${(e.r.groupFidelityMean ?? 0).toFixed(2)}`,
  }));

  const indData = entries.map(e => {
    const rows = e.r.fidelityRows || [];
    const mean = rows.length ? rows.reduce((s, r) => s + (r.mean ?? 0), 0) / rows.length : 0;
    return {
      label: lbl(e), value: mean,
      color: mean >= 4 ? "#22c55e" : mean >= 3 ? "#eab308" : "#ef4444",
      tooltip: `${lbl(e)} · Ind. fidelity ${mean.toFixed(2)}`,
    };
  });

  return (
    <>
      <div className="t-eyebrow">Quantitative</div>
      <h2 className="t-h2" style={{ marginTop: 4, marginBottom: 16 }}>Chat analytics</h2>

      {entries.length === 0 ? (
        <div className="card" style={{ padding: "40px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 13, color: "var(--fg-2)", fontFamily: "var(--font-mono)" }}>
            {reports === null ? "Loading…" : "No judged sessions yet — launch the pipeline on a session to see analytics."}
          </div>
        </div>
      ) : (
        <>
          {/* Gini — full width */}
          <div className="chart-grid" style={{ marginBottom: 12 }}>
            <div className="card chart-card" style={{ gridColumn: "span 2" }}>
              <div className="chart-card-head">
                <div className="t-h3">Turn distribution (Gini)</div>
                <span className="badge">target 0.28 – 0.42</span>
              </div>
              <BarChart data={giniData} yMin={0} yMax={1}
                target={{ lo: 0.28, hi: 0.42 }}
                formatY={v => v.toFixed(2)} chartHeight={220} />
            </div>
          </div>

          {/* Accuracy + Group fidelity — side by side */}
          <div className="chart-grid" style={{ marginBottom: 12 }}>
            <div className="card chart-card">
              <div className="chart-card-head">
                <div className="t-h3">Persona ID accuracy</div>
                <span className="badge">baseline 12.5%</span>
              </div>
              <BarChart data={accData} yMin={0} yMax={100}
                target={{ lo: 0, hi: 12.5 }}
                formatY={v => `${v.toFixed(0)}%`} chartHeight={200} />
            </div>
            <div className="card chart-card">
              <div className="chart-card-head">
                <div className="t-h3">Group fidelity score</div>
                <span className="badge">avg from 20 judges</span>
              </div>
              <BarChart data={grpData} yMin={0} yMax={5}
                formatY={v => v.toFixed(1)} chartHeight={200} />
            </div>
          </div>

          {/* Individual fidelity — full width */}
          <div className="chart-grid">
            <div className="card chart-card" style={{ gridColumn: "span 2" }}>
              <div className="chart-card-head">
                <div className="t-h3">Individual fidelity (mean across personas)</div>
                <span className="badge">1 – 5 scale</span>
              </div>
              <BarChart data={indData} yMin={0} yMax={5}
                formatY={v => v.toFixed(1)} chartHeight={200} />
            </div>
          </div>
        </>
      )}
    </>
  );
}


// ─── Session Log + Judging (merged) ──────────────────────────
function SessionLogSection({ onJudge, reports, onOpenChat }) {
  const { byId } = window.useAgents();
  const [sessions, setSessions] = React.useState([]);
  const [q, setQ] = React.useState("");
  const [expandedId, setExpandedId] = React.useState(null);

  React.useEffect(() => {
    window.api.get("/admin/sessions?limit=100")
      .then(data => setSessions(data))
      .catch(() => setSessions([]));
  }, []);

  const filtered = sessions.filter(s =>
    !q ||
    (s.display_id || String(s.id)).toLowerCase().includes(q.toLowerCase()) ||
    s.topic.toLowerCase().includes(q.toLowerCase())
  );

  const judgedCount = sessions.filter(s => !!reports?.[s.id]).length;

  const toggleExpand = (id) => setExpandedId(prev => prev === id ? null : id);

  return (
    <>
      <p className="t-meta" style={{ marginBottom: 16, maxWidth: 680 }}>
        All chat sessions. Launch the judging pipeline on any session to evaluate persona fidelity,
        turn distribution, and group fidelity. Sessions already judged show a cached
        report — click <strong>View report</strong> to reopen without re-running the pipeline.
      </p>

      <div className="card" style={{ overflow: "hidden" }}>
        <div className="chart-card-head" style={{ padding: "12px 14px" }}>
          <div className="lib-search" style={{ flex: "0 1 360px" }}>
            <span className="lib-search-icon"><Icons.Search size={13} /></span>
            <input
              className="input"
              placeholder="Search by session ID or topic…"
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <div className="row" style={{ gap: 10 }}>
            {judgedCount > 0 && (
              <span className="badge badge-ok">
                <Icons.Check size={10} sw={2.5} /> {judgedCount} judged
              </span>
            )}
            <div className="t-meta">{filtered.length} session{filtered.length !== 1 ? "s" : ""}</div>
          </div>
        </div>

        {sessions.length === 0 ? (
          <Empty title="No sessions yet" sub="Sessions appear here once users start chatting." icon={<Icons.Database size={20} />} />
        ) : filtered.length === 0 ? (
          <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--fg-3)", fontSize: 13 }}>
            No sessions match "{q}"
          </div>
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 32 }}></th>
                  <th>Session ID</th>
                  <th>Participants</th>
                  <th>Topic</th>
                  <th style={{ width: 100 }}>Duration</th>
                  <th style={{ width: 145 }}>Date</th>
                  <th style={{ width: 120 }}>Status</th>
                  <th style={{ width: 260 }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(s => {
                  const judged = !!reports?.[s.id];
                  const expanded = expandedId === s.id;
                  const personas = s.participants.map(id => byId(id)).filter(Boolean);
                  return (
                    <React.Fragment key={s.id}>
                      {/* ── Main row ── */}
                      <tr
                        style={{ cursor: "pointer" }}
                        onClick={() => toggleExpand(s.id)}
                      >
                        <td style={{ textAlign: "center", paddingRight: 0 }}>
                          <Icons.ChevronRight
                            size={13}
                            style={{
                              color: "var(--fg-3)",
                              transform: expanded ? "rotate(90deg)" : "none",
                              transition: "transform .15s",
                            }}
                          />
                        </td>
                        <td className="col-mono">{s.display_id}</td>
                        <td>
                          <div className="row" style={{ gap: 8 }}>
                            <AvatarStack personas={personas} size="xs" max={4} />
                            <span className="t-meta">{s.participants.length}</span>
                          </div>
                        </td>
                        <td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={s.topic}>
                          {s.topic}
                        </td>
                        <td className="col-mono">{s.duration}</td>
                        <td className="t-meta col-mono">{s.date}</td>
                        <td onClick={e => e.stopPropagation()}>
                          <StatusPill status={s.status} />
                        </td>
                        <td onClick={e => e.stopPropagation()}>
                          <div className="row" style={{ gap: 4, justifyContent: "flex-end" }}>
                            {judged && s.participants.length > 1 && (
                              <span className="badge badge-ok" style={{ whiteSpace: "nowrap" }}>
                                <Icons.Check size={10} sw={2.5} /> Judged
                              </span>
                            )}
                            {s.participants.length > 1 && (
                              <Btn
                                variant={judged ? "outline" : "primary"}
                                size="sm"
                                icon={judged ? <Icons.ChartBar size={12} /> : <Icons.Sparkles size={12} sw={2} />}
                                onClick={() => onJudge?.(s)}
                              >
                                {judged ? "View report" : "Launch judging"}
                              </Btn>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* ── Expanded detail row ── */}
                      {expanded && (
                        <tr style={{ background: "var(--bg-2)" }}>
                          <td colSpan={8} style={{ padding: "14px 16px 16px 40px", borderTop: "1px solid var(--border-0)" }}>
                            <div style={{ display: "flex", gap: 32, alignItems: "flex-start", flexWrap: "wrap" }}>
                              {/* Participants */}
                              <div style={{ flex: "0 0 auto" }}>
                                <div className="t-eyebrow" style={{ marginBottom: 8 }}>Participants ({personas.length})</div>
                                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                                  {personas.map(p => (
                                    <div key={p.id} className="row" style={{ gap: 8 }}>
                                      <Avatar persona={p} size="sm" />
                                      <div>
                                        <div style={{ fontSize: 13, fontWeight: 500, fontFamily: "var(--font-mono)" }}>{p.name}</div>
                                        <div style={{ fontSize: 11, color: "var(--fg-3)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{p.source_title}</div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>

                              {/* Session info */}
                              <div style={{ flex: "1 1 200px" }}>
                                <div className="t-eyebrow" style={{ marginBottom: 8 }}>Session info</div>
                                <div className="col" style={{ gap: 4 }}>
                                  <div className="row" style={{ gap: 6 }}>
                                    <span style={{ fontSize: 12, color: "var(--fg-3)", width: 70 }}>ID</span>
                                    <span className="mono" style={{ fontSize: 12 }}>{s.display_id}</span>
                                  </div>
                                  <div className="row" style={{ gap: 6 }}>
                                    <span style={{ fontSize: 12, color: "var(--fg-3)", width: 70 }}>Topic</span>
                                    <span style={{ fontSize: 12 }}>{s.topic}</span>
                                  </div>
                                  <div className="row" style={{ gap: 6 }}>
                                    <span style={{ fontSize: 12, color: "var(--fg-3)", width: 70 }}>Date</span>
                                    <span className="mono" style={{ fontSize: 12 }}>{s.date}</span>
                                  </div>
                                  <div className="row" style={{ gap: 6 }}>
                                    <span style={{ fontSize: 12, color: "var(--fg-3)", width: 70 }}>Duration</span>
                                    <span className="mono" style={{ fontSize: 12 }}>{s.duration}</span>
                                  </div>
                                  <div className="row" style={{ gap: 6 }}>
                                    <span style={{ fontSize: 12, color: "var(--fg-3)", width: 70 }}>Status</span>
                                    <StatusPill status={s.status} />
                                  </div>
                                </div>
                              </div>

                              {/* Actions */}
                              <div style={{ flex: "0 0 auto", display: "flex", flexDirection: "column", gap: 8, alignSelf: "center" }}>
                                {onOpenChat && (
                                  <Btn
                                    variant="primary"
                                    icon={<Icons.MessageDots size={13} />}
                                    onClick={() => onOpenChat(s)}
                                  >
                                    Go to chat
                                  </Btn>
                                )}
                                {s.participants.length > 1 && (
                                  <Btn
                                    variant="outline"
                                    icon={judged ? <Icons.ChartBar size={13} /> : <Icons.Sparkles size={13} sw={2} />}
                                    onClick={() => onJudge?.(s)}
                                  >
                                    {judged ? "View report" : "Launch judging"}
                                  </Btn>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
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
  // History of all past runs for this session (newest first).
  const [history, setHistory] = React.useState([]);
  // Which history entry is currently displayed (null = the live/latest report).
  const [historyIdx, setHistoryIdx] = React.useState(null);

  // Keep refs to the latest values without making them effect dependencies.
  // The pipeline effect should ONLY re-fire when the session or runKey changes —
  // otherwise saving a fresh report (which updates `cached` upstream) would
  // re-trigger the effect and kick off another run, looping forever.
  const cachedRef = React.useRef(cached);
  const onSaveReportRef = React.useRef(onSaveReport);
  React.useEffect(() => { cachedRef.current = cached; }, [cached]);
  React.useEffect(() => { onSaveReportRef.current = onSaveReport; }, [onSaveReport]);

  // ─── real pipeline via API + SSE ─────────────────────────────
  React.useEffect(() => {
    if (!session) return;
    // Show cached report without re-running.
    if (runKey === 0 && cachedRef.current && cachedRef.current.sessionId === session.id) {
      setReport(cachedRef.current);
      setStage("done");
      setProgress(100);
      setTab("persona_id");
      return;
    }

    setStage("running");
    setProgress(0);
    setTab("persona_id");

    let es = null;
    let cancelled = false;

    window.api.post(`/admin/judge-chat/${session.id}`, {})
      .then(() => {
        if (cancelled) return;
        // Open SSE stream for progress updates and the final result.
        es = new EventSource(`${window.api.base}/admin/judge-chat/${session.id}/stream`);

        es.onmessage = (evt) => {
          if (cancelled) { es.close(); return; }
          let data;
          try { data = JSON.parse(evt.data); } catch { return; }

          if (data.type === "progress") {
            setProgress(data.progress);
          } else if (data.type === "result") {
            const fresh = { ...data.result };
            setReport(fresh);
            setStage("done");
            setProgress(100);
            onSaveReportRef.current?.(session.id, fresh);
            es.close();
          } else if (data.type === "error") {
            setStage("error");
            es.close();
          }
        };

        es.onerror = () => {
          if (!cancelled) setStage("error");
          es.close();
        };
      })
      .catch(() => { if (!cancelled) setStage("error"); });

    return () => {
      cancelled = true;
      es?.close();
    };
    // Intentionally NOT depending on `cached` / `onSaveReport` — see refs above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.id, runKey]);

  // Reset run key and history when switching to a different session.
  React.useEffect(() => {
    setRunKey(0);
    setHistory([]);
    setHistoryIdx(null);
  }, [session?.id]);

  // Fetch run history whenever the modal reaches "done" (initial load or re-run).
  React.useEffect(() => {
    if (stage !== "done" || !session) return;
    window.api.get(`/admin/judged-chats/${session.id}/history`)
      .then(list => {
        setHistory(list || []);
        setHistoryIdx(null); // always default to latest
      })
      .catch(() => {});
  }, [stage, session?.id]);

  if (!session) return null;
  const personas = (session.participants || []).map(id => byId(id)).filter(Boolean);
  // When the user picks a history pill, show that run; otherwise show the live report.
  const activeReport = historyIdx !== null ? history[historyIdx] : report;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-judge" onClick={e => e.stopPropagation()} style={{ width: 880 }}>
        <div className="modal-head" style={{ flexDirection: "column", alignItems: "stretch", gap: 10, paddingBottom: 0 }}>
          <div className="row" style={{ alignItems: "flex-start" }}>
            <div style={{ flex: 1 }}>
              <div className="t-eyebrow">Judging report</div>
              <div className="t-h2" style={{ marginTop: 2 }}>{session.topic}</div>
              <div className="row t-meta" style={{ marginTop: 6, gap: 10 }}>
                <span className="mono">{session.display_id || session.id}</span>
                <span className="dot-sep" />
                <AvatarStack personas={personas} size="xs" max={6} />
                <span className="mono">{personas.length} agents</span>
                <span className="dot-sep" />
                <StatusPill status={session.status} />
                {stage === "done" && activeReport?.ranAt && (
                  <>
                    <span className="dot-sep" />
                    <span className="mono">judged · {new Date(activeReport.ranAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  </>
                )}
              </div>
            </div>
            <IconBtn icon={<Icons.X size={14} />} onClick={onClose} />
          </div>
          {stage === "done" && history.length > 1 && (
            <div className="judge-history-bar">
              <span className="t-eyebrow" style={{ fontSize: 10, color: "var(--fg-2)", marginRight: 6 }}>Runs</span>
              {history.map((h, i) => {
                const d = new Date(h.ranAt);
                const label = `${d.toLocaleDateString([], { month: "short", day: "numeric" })} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
                const isActive = historyIdx === i || (historyIdx === null && i === 0);
                return (
                  <button
                    key={h.ranAt + i}
                    className={`judge-history-pill${isActive ? " active" : ""}`}
                    onClick={() => setHistoryIdx(i === 0 && historyIdx === null ? null : i)}
                    title={label}
                  >
                    {i === 0 ? <><Icons.Sparkles size={10} sw={2} /> Latest</> : label}
                  </button>
                );
              })}
            </div>
          )}
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
                {["RAG index", "Persona ID", "Fidelity", "Group", "Metrics"].map((label, i) => (
                  <span key={label} className={`judge-progress-step ${progress > i * 20 ? "done" : ""}`}>
                    {progress > i * 20 ? <Icons.Check size={10} /> : <Icons.Dot size={10} />}
                    {label}
                  </span>
                ))}
              </div>
            </div>
          ) : stage !== "error" ? (
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
          ) : null}
        </div>

        <div className="modal-body" style={{ background: "var(--bg-0)" }}>
          {stage === "running" && (
            <div className="judge-running-body">
              <div className="t-meta">Running 20 judges in parallel. Computing bootstrap CIs.</div>
            </div>
          )}
          {stage === "error" && (
            <div className="judge-running-body" style={{ color: "var(--danger)" }}>
              <Icons.AlertCircle size={20} sw={2} />
              <div className="t-meta" style={{ marginTop: 8 }}>
                The judging pipeline failed. Check that ChromaDB is indexed and the OpenAI key is set, then try again.
              </div>
            </div>
          )}

          {stage === "done" && activeReport && tab === "persona_id" && (
            <ReportPersonaID
              group={EVAL_GROUPS[0]}
              accuracy={activeReport.accuracy} ciLow={activeReport.ciLow} ciHigh={activeReport.ciHigh} pValue={activeReport.pValue}
              cohenKappa={activeReport.cohenKappa ?? 0} macroF1={activeReport.macroF1 ?? 0}
              prfRows={activeReport.prfRows || []}
              judgeVarMean={activeReport.judgeVarMean ?? 0} judgeVarStd={activeReport.judgeVarStd ?? 0}
              cm={activeReport.cm} cmLabels={activeReport.cmLabels || []} personas={personas}
            />
          )}
          {stage === "done" && activeReport && tab === "individual_fidelity" && (
            <ReportIndividualFidelity
              group={EVAL_GROUPS[1]}
              rows={activeReport.fidelityRows.map(r => ({ ...r, persona: byId(r.personaId) })).filter(r => r.persona)}
              judgeTypeAgreement={activeReport.judgeTypeAgreement || { medians: {}, mad: {} }}
            />
          )}
          {stage === "done" && activeReport && tab === "group_fidelity" && (
            <ReportGroupFidelity
              group={EVAL_GROUPS[2]}
              gini={activeReport.gini} giniZ={activeReport.giniZ} giniCI={activeReport.giniCI}
              turnShares={activeReport.turnShares}
              groupFidelityMean={activeReport.groupFidelityMean ?? 0}
              groupFidelityMedian={activeReport.groupFidelityMedian ?? 0}
            />
          )}
        </div>

        <div className="modal-foot">
          <Btn variant="ghost" onClick={onClose}>Close</Btn>
          {stage === "done" && (
            <>
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
          {stage === "error" && (
            <Btn
              variant="primary"
              icon={<Icons.Sparkles size={12} sw={2} />}
              onClick={() => setRunKey(k => k + 1)}
            >
              Retry
            </Btn>
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

function kappaLabel(k) {
  if (k > 0.8) return "Excellent";
  if (k > 0.6) return "Good";
  if (k > 0.4) return "Moderate";
  if (k > 0.2) return "Fair";
  return "Poor";
}

function ReportPersonaID({ group, accuracy, ciLow, ciHigh, pValue, cohenKappa, macroF1, prfRows, judgeVarMean, judgeVarStd, cm, cmLabels }) {
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
        <MetricStat
          label="Cohen's κ"
          value={cohenKappa.toFixed(3)}
          sub={kappaLabel(cohenKappa)}
          tone={cohenKappa > 0.4 ? "good" : cohenKappa > 0.2 ? "warn" : "bad"}
        />
        <MetricStat
          label="Macro F1"
          value={macroF1.toFixed(3)}
          sub="Unweighted avg across personas"
          tone={macroF1 > 0.5 ? "good" : "warn"}
        />
      </div>

      {judgeVarStd > 0 && (
        <div className="t-meta" style={{ margin: "4px 0 16px", color: "var(--fg-2)" }}>
          Judge accuracy — mean <span className="mono">{(judgeVarMean * 100).toFixed(1)}%</span>, std <span className="mono">{(judgeVarStd * 100).toFixed(1)}%</span>
        </div>
      )}

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

      {cmLabels.length > 0 && (
        <div className="cm-legend">
          {cmLabels.map((name, i) => (
            <div key={i} className="cm-legend-row">
              <span className="mono cm-legend-key">P{i + 1}</span>
              <span className="cm-legend-name">{name}</span>
            </div>
          ))}
        </div>
      )}

      {prfRows.length > 0 && (
        <>
          <div className="t-eyebrow" style={{ margin: "20px 0 8px" }}>Precision · Recall · F1 per persona</div>
          <table className="table">
            <thead>
              <tr>
                <th>Persona</th>
                <th style={{ width: 90 }}>Precision</th>
                <th style={{ width: 90 }}>Recall</th>
                <th style={{ width: 90 }}>F1</th>
                <th>F1 bar</th>
              </tr>
            </thead>
            <tbody>
              {prfRows.map((r, i) => (
                <tr key={i}>
                  <td className="mono" style={{ fontSize: 12 }}>{r.label}</td>
                  <td className="col-mono">{r.precision.toFixed(3)}</td>
                  <td className="col-mono">{r.recall.toFixed(3)}</td>
                  <td className="col-mono">{r.f1.toFixed(3)}</td>
                  <td>
                    <div style={{ height: 8, borderRadius: 4, background: "var(--bg-3)", overflow: "hidden" }}>
                      <div style={{ width: `${r.f1 * 100}%`, height: "100%", background: r.f1 > 0.5 ? "var(--admin)" : "var(--warn)", borderRadius: 4 }} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <PropsList group={group} />
    </>
  );
}

function ReportIndividualFidelity({ group, rows, judgeTypeAgreement }) {
  const medians = judgeTypeAgreement?.medians || {};
  const mad = judgeTypeAgreement?.mad || {};
  const judgeTypes = Object.keys(medians);
  const madPairs = Object.entries(mad);

  return (
    <>
      <ReportHeader group={group} />
      <table className="table fidelity-table">
        <thead>
          <tr>
            <th>Persona</th>
            <th style={{ width: 80 }}>Mean</th>
            <th style={{ width: 80 }}>Median</th>
            <th style={{ width: 80 }}>IQR</th>
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
              <td className="col-mono">{(r.mean ?? 0).toFixed(2)}</td>
              <td className="col-mono">{r.median.toFixed(2)}</td>
              <td className="col-mono">{r.iqr.toFixed(2)}</td>
              <td className="col-mono">[{r.ciL.toFixed(2)}, {r.ciH.toFixed(2)}]</td>
              <td>
                <div style={{ display: "flex", gap: 4, height: 28, alignItems: "flex-end" }}>
                  {[1, 2, 3, 4, 5].map(s => {
                    const d = Math.abs(s - r.median);
                    const h = Math.max(4, 28 - d * 11);
                    const active = s >= Math.floor(r.median) && s <= Math.ceil(r.median);
                    const SCALE = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"];
                    return (
                      <div key={s} style={{
                        flex: 1, height: h, borderRadius: 2,
                        background: active ? SCALE[s - 1] : "var(--bg-3)",
                        opacity: active ? 0.9 : 0.6,
                        display: "flex", alignItems: "center", justifyContent: "center",
                      }}>
                        {active && (
                          <span style={{ fontSize: 9, fontWeight: 700, color: "#fff", lineHeight: 1 }}>{s}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {judgeTypes.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <div className="t-eyebrow" style={{ marginBottom: 14 }}>Judge type agreement</div>
          {(() => {
            const TYPE_COLOR = {
              style:      "#8b5cf6",
              ideology:   "#3b82f6",
              general:    "#14b8a6",
              behavioral: "#f97316",
            };
            // Build symmetric MAD lookup
            const madMap = {};
            madPairs.forEach(([pair, val]) => {
              const parts = pair.split("_vs_");
              if (parts.length === 2) {
                madMap[`${parts[0]}_${parts[1]}`] = val;
                madMap[`${parts[1]}_${parts[0]}`] = val;
              }
            });
            const madCell = (a, b) => madMap[`${a}_${b}`];
            const cellBg = v => v === undefined ? "var(--bg-1)"
              : v <= 0.3 ? "rgba(34,197,94,0.18)"
              : v <= 0.6 ? "rgba(234,179,8,0.18)"
              : "rgba(239,68,68,0.18)";
            const cellColor = v => v === undefined ? "var(--fg-3)"
              : v <= 0.3 ? "#16a34a"
              : v <= 0.6 ? "#a16207"
              : "#dc2626";

            return (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>

                {/* ── Left: median bars ── */}
                <div>
                  <div className="t-meta" style={{ marginBottom: 10, fontWeight: 600 }}>Median score by role</div>
                  {judgeTypes.map(jt => (
                    <div key={jt} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                      <div style={{ width: 76, fontSize: 11, fontFamily: "var(--font-mono)", color: TYPE_COLOR[jt] || "var(--fg-1)", flexShrink: 0 }}>
                        {jt.charAt(0).toUpperCase() + jt.slice(1)}
                      </div>
                      <div style={{ flex: 1, height: 20, background: "var(--bg-2)", borderRadius: 4, overflow: "hidden" }}>
                        <div style={{
                          width: `${(medians[jt] / 5) * 100}%`,
                          height: "100%",
                          background: TYPE_COLOR[jt] || "var(--admin)",
                          borderRadius: 4,
                          opacity: 0.75,
                          transition: "width 0.4s ease",
                        }} />
                      </div>
                      <div style={{ width: 32, fontSize: 12, fontFamily: "var(--font-mono)", textAlign: "right", color: "var(--fg-0)" }}>
                        {medians[jt].toFixed(2)}
                      </div>
                    </div>
                  ))}
                  <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                    {[1, 2, 3, 4, 5].map(n => (
                      <div key={n} style={{ flex: 1, textAlign: "center", fontSize: 9, fontFamily: "var(--font-mono)", color: "var(--fg-3)" }}>{n}</div>
                    ))}
                  </div>
                </div>

                {/* ── Right: MAD heatmap matrix ── */}
                {madPairs.length > 0 && (
                  <div>
                    <div className="t-meta" style={{ marginBottom: 10, fontWeight: 600 }}>Pairwise MAD matrix</div>
                    <div style={{
                      display: "grid",
                      gridTemplateColumns: `48px repeat(${judgeTypes.length}, 1fr)`,
                      gap: 3,
                    }}>
                      {/* header row */}
                      <div />
                      {judgeTypes.map(jt => (
                        <div key={jt} style={{
                          textAlign: "center", fontSize: 9,
                          fontFamily: "var(--font-mono)", fontWeight: 700,
                          color: TYPE_COLOR[jt] || "var(--fg-2)",
                          paddingBottom: 2, letterSpacing: "0.05em",
                        }}>
                          {jt.slice(0, 3).toUpperCase()}
                        </div>
                      ))}
                      {/* data rows */}
                      {judgeTypes.map(row => [
                        <div key={`lbl-${row}`} style={{
                          fontSize: 9, fontFamily: "var(--font-mono)", fontWeight: 700,
                          color: TYPE_COLOR[row] || "var(--fg-2)",
                          display: "flex", alignItems: "center",
                          letterSpacing: "0.05em",
                        }}>
                          {row.slice(0, 3).toUpperCase()}
                        </div>,
                        ...judgeTypes.map(col => {
                          const v = row === col ? undefined : madCell(row, col);
                          return (
                            <div key={`${row}-${col}`} style={{
                              background: row === col ? "var(--bg-1)" : cellBg(v),
                              borderRadius: 4,
                              padding: "5px 2px",
                              textAlign: "center",
                              fontSize: 10,
                              fontFamily: "var(--font-mono)",
                              fontWeight: 600,
                              color: row === col ? "var(--fg-3)" : cellColor(v),
                            }}>
                              {row === col ? "—" : v !== undefined ? v.toFixed(2) : "·"}
                            </div>
                          );
                        }),
                      ])}
                    </div>
                    {/* legend */}
                    <div style={{ display: "flex", gap: 12, marginTop: 10, alignItems: "center" }}>
                      {[
                        { color: "rgba(34,197,94,0.18)", text: "16a34a", label: "≤ 0.3 high" },
                        { color: "rgba(234,179,8,0.18)",  text: "a16207", label: "≤ 0.6 mod." },
                        { color: "rgba(239,68,68,0.18)",  text: "dc2626", label: "> 0.6 low" },
                      ].map(({ color, text, label }) => (
                        <div key={label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <div style={{ width: 10, height: 10, borderRadius: 2, background: color }} />
                          <span style={{ fontSize: 9, fontFamily: "var(--font-mono)", color: `#${text}` }}>{label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      <PropsList group={group} />
    </>
  );
}

function ReportGroupFidelity({ group, gini, giniZ, giniCI, turnShares, groupFidelityMean, groupFidelityMedian }) {
  const { byId } = window.useAgents();
  const inRange = gini >= 0.28 && gini <= 0.42;
  const rows = (turnShares || []).map(t => ({ ...t, persona: byId(t.personaId) })).filter(r => r.persona);
  return (
    <>
      <ReportHeader group={group} />

      {groupFidelityMean > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div className="t-eyebrow" style={{ marginBottom: 10 }}>Group fidelity score</div>
          <div style={{ display: "flex", gap: 6, height: 40, alignItems: "flex-end", maxWidth: 260 }}>
            {[1, 2, 3, 4, 5].map(s => {
              const d = Math.abs(s - groupFidelityMean);
              const h = Math.max(6, 40 - d * 14);
              const active = s >= Math.floor(groupFidelityMean) && s <= Math.ceil(groupFidelityMean);
              const SCALE = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"];
              return (
                <div key={s} style={{
                  flex: 1, height: h, borderRadius: 3,
                  background: active ? SCALE[s - 1] : "var(--bg-3)",
                  opacity: active ? 0.9 : 0.6,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {active && (
                    <span style={{ fontSize: 11, fontWeight: 700, color: "#fff", fontFamily: "var(--font-mono)" }}>{s}</span>
                  )}
                </div>
              );
            })}
          </div>
          <div style={{ marginTop: 6, fontSize: 11, color: "var(--fg-2)", fontFamily: "var(--font-mono)" }}>
            Average score from 20 judges
          </div>
        </div>
      )}

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
        {groupFidelityMean > 0 && (
          <MetricStat label="Mean judge score" value={groupFidelityMean.toFixed(2)} sub="group fidelity" />
        )}
        {groupFidelityMedian > 0 && (
          <MetricStat label="Median judge score" value={groupFidelityMedian.toFixed(2)} sub="group fidelity" />
        )}
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


// ─── Admin shell ─────────────────────────────────────────────
function AdminDashboard({ section, onSection, chats, onNewGroup, onNewDM, onOpenChat, onNav, user }) {
  const [navOpen, setNavOpen] = React.useState(false);
  const [judging, setJudging] = React.useState(null);
  // sessionId (number) → cached UI report. Pre-loaded from the server on
  // mount so previously judged chats show "View report" after a page reload.
  const [reports, setReports] = React.useState({});

  React.useEffect(() => {
    window.api.get("/admin/judged-chats")
      .then(data => {
        // JSON keys are strings; session IDs in the UI are numbers
        const byId = {};
        Object.entries(data).forEach(([k, v]) => { byId[Number(k)] = v; });
        setReports(byId);
      })
      .catch(() => {});
  }, []);

  const openJudging = (s) => setJudging(s);
  const closeJudging = () => setJudging(null);
  const saveReport = React.useCallback((sessionId, report) => {
    setReports(r => ({ ...r, [sessionId]: report }));
  }, []);

  return (
    <div className="admin-shell" data-screen-label="admin-dashboard">
      {navOpen && <div className="mobile-overlay open" onClick={() => setNavOpen(false)} />}
      <AdminSidebar
        section={section}
        onSelect={(s) => { onSection(s); setNavOpen(false); }}
        isOpen={navOpen}
      />

      {/* ── Overview: full-width home layout (no admin-main padding) ── */}
      {section === "overview" && (
        <AdminHomeSection
          user={user}
          onSection={onSection}
          onNav={onNav}
          chats={chats}
        />
      )}

      {/* ── Other sections: standard admin-main shell ── */}
      {section !== "overview" && (
        <main className="admin-main">
          <div className="admin-header">
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <button
                className="btn btn-ghost btn-icon topnav-hamburger"
                onClick={() => setNavOpen(o => !o)}
                title="Toggle admin menu"
              >
                <Icons.Menu size={20} />
              </button>
              <div>
                <div className="t-eyebrow">8 Angry Agents · {section}</div>
                <h1 className="t-h1" style={{ marginTop: 4 }}>
                  {section === "analytics" && "Chat Analytics"}
                  {section === "performance" && "Agent Performance"}
                  {section === "sessions" && "Session Log"}
                </h1>
              </div>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <span className="badge badge-admin">
                <Icons.Crown size={11} /> Admin
              </span>
              <Btn variant="outline" size="sm" icon={<Icons.User size={12} />} onClick={onNewDM}>New DM</Btn>
              <Btn variant="outline" size="sm" icon={<Icons.Users size={12} />} onClick={onNewGroup}>New group</Btn>
            </div>
          </div>

          {section === "analytics" && <ChatAnalyticsSection />}
          {section === "performance" && <AgentPerformanceSection />}
          {section === "sessions" && <SessionLogSection onJudge={openJudging} reports={reports} onOpenChat={onOpenChat} />}
        </main>
      )}


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
