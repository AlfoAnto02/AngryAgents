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
          <Btn variant="outline" size="sm" icon={<Icons.Download size={12} />}>Export CSV</Btn>
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
          <div className="table-scroll">
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
            <Btn variant="outline" size="sm" icon={<Icons.Download size={12} />}>Export CSV</Btn>
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
      { k: "Drift score (optional)",       desc: "Mean pairwise cosine sim of last messages; > 0.85 triggers perturbation." },
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
                <span className="mono">{session.display_id || session.id}</span>
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

          {stage === "done" && report && tab === "persona_id" && (
            <ReportPersonaID
              group={EVAL_GROUPS[0]}
              accuracy={report.accuracy} ciLow={report.ciLow} ciHigh={report.ciHigh} pValue={report.pValue}
              cohenKappa={report.cohenKappa ?? 0} macroF1={report.macroF1 ?? 0}
              prfRows={report.prfRows || []}
              judgeVarMean={report.judgeVarMean ?? 0} judgeVarStd={report.judgeVarStd ?? 0}
              cm={report.cm} cmLabels={report.cmLabels || []} personas={personas}
            />
          )}
          {stage === "done" && report && tab === "individual_fidelity" && (
            <ReportIndividualFidelity
              group={EVAL_GROUPS[1]}
              rows={report.fidelityRows.map(r => ({ ...r, persona: byId(r.personaId) })).filter(r => r.persona)}
              judgeTypeAgreement={report.judgeTypeAgreement || { medians: {}, mad: {} }}
            />
          )}
          {stage === "done" && report && tab === "group_fidelity" && (
            <ReportGroupFidelity
              group={EVAL_GROUPS[2]}
              gini={report.gini} giniZ={report.giniZ} giniCI={report.giniCI} driftScore={report.driftScore}
              turnShares={report.turnShares}
            />
          )}
        </div>

        <div className="modal-foot">
          <Btn variant="ghost" onClick={onClose}>Close</Btn>
          {stage === "done" && (
            <>
              <Btn variant="outline" icon={<Icons.Download size={12} />}>Export JSON</Btn>
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

      {judgeTypes.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <div className="t-eyebrow" style={{ marginBottom: 12 }}>Judge type agreement</div>
          <div className="metric-row" style={{ marginBottom: 20 }}>
            {judgeTypes.map(jt => (
              <MetricStat
                key={jt}
                label={jt.charAt(0).toUpperCase() + jt.slice(1)}
                value={medians[jt].toFixed(2)}
                sub="median score"
              />
            ))}
          </div>
          {madPairs.length > 0 && (
            <table className="table" style={{ maxWidth: 480 }}>
              <thead>
                <tr>
                  <th>Judge pair</th>
                  <th style={{ width: 120 }}>MAD</th>
                  <th style={{ width: 120 }}>Agreement</th>
                </tr>
              </thead>
              <tbody>
                {madPairs.map(([pair, val]) => {
                  const badgeCls = val <= 0.3 ? "badge-ok" : val <= 0.6 ? "badge-admin" : "badge-danger";
                  const label = val <= 0.3 ? "High" : val <= 0.6 ? "Moderate" : "Low";
                  return (
                    <tr key={pair}>
                      <td className="mono" style={{ fontSize: 12 }}>{pair.replace(/_vs_/g, " vs ")}</td>
                      <td className="col-mono">{val.toFixed(3)}</td>
                      <td><span className={`badge ${badgeCls}`}>{label}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

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
