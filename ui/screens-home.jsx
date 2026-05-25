// screens-home.jsx — Landing / home screen

function HomeScreen({ user, chats, onGoAgents, onGoChats, onOpenChat, onNewDM, onNewGroup }) {
  const recentChats = chats.slice(0, 4);
  const featuredAgents = window.PERSONAS.slice(0, 5);

  return (
    <div style={{ flex: 1, overflowY: "auto", background: "var(--bg-0)" }} data-screen-label="home">
      <div style={{ maxWidth: 980, margin: "0 auto", padding: "56px 32px 64px" }}>
        {/* ── Hero ─────────────────────────────────────── */}
        <div style={{ textAlign: "left", marginBottom: 40 }}>
          <div className="t-eyebrow">Welcome back, {user.name.split(" ")[0]}</div>
          <h1 style={{
            fontFamily: "var(--font-mono)",
            fontSize: 44,
            fontWeight: 600,
            letterSpacing: "-0.01em",
            margin: "10px 0 6px",
            lineHeight: 1.05,
          }}>
            8 Angry Agents
          </h1>
          <p style={{
            fontSize: 15,
            color: "var(--fg-2)",
            margin: 0,
            maxWidth: 560,
          }}>
            Talk to AI personas one-on-one, or drop a handful of them into the same room and watch them disagree.
          </p>
        </div>

        {/* ── Two big tiles ────────────────────────────── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 32 }}>
          {/* Agents tile */}
          <button
            className="card card-hov"
            onClick={onGoAgents}
            style={{
              textAlign: "left",
              padding: 24,
              display: "flex",
              flexDirection: "column",
              gap: 18,
              cursor: "pointer",
              background: "var(--bg-1)",
              border: "1px solid var(--border-0)",
              borderRadius: 8,
              minHeight: 220,
              fontFamily: "inherit",
              color: "inherit",
            }}
          >
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{
                width: 40, height: 40, borderRadius: 6,
                background: "var(--accent-soft)", color: "var(--accent)",
                display: "flex", alignItems: "center", justifyContent: "center",
                border: "1px solid var(--accent-border)",
              }}>
                <Icons.Library size={20} sw={1.6} />
              </div>
              <Icons.ArrowRight size={16} style={{ color: "var(--fg-2)" }} />
            </div>
            <div>
              <div className="t-eyebrow">01 — Browse</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 600, marginTop: 4 }}>Agents</div>
              <div className="t-meta" style={{ marginTop: 6, fontSize: 13 }}>
                {window.PERSONAS.length} personas in your library · search, filter, and add to a session.
              </div>
            </div>
            <div style={{ marginTop: "auto" }}>
              <AvatarStack personas={featuredAgents} size="sm" max={5} />
            </div>
          </button>

          {/* Chats tile */}
          <button
            className="card card-hov"
            onClick={onGoChats}
            style={{
              textAlign: "left",
              padding: 24,
              display: "flex",
              flexDirection: "column",
              gap: 18,
              cursor: "pointer",
              background: "var(--bg-1)",
              border: "1px solid var(--border-0)",
              borderRadius: 8,
              minHeight: 220,
              fontFamily: "inherit",
              color: "inherit",
            }}
          >
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{
                width: 40, height: 40, borderRadius: 6,
                background: "var(--accent-soft)", color: "var(--accent)",
                display: "flex", alignItems: "center", justifyContent: "center",
                border: "1px solid var(--accent-border)",
              }}>
                <Icons.MessageDots size={20} sw={1.6} />
              </div>
              <Icons.ArrowRight size={16} style={{ color: "var(--fg-2)" }} />
            </div>
            <div>
              <div className="t-eyebrow">02 — Continue</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 600, marginTop: 4 }}>Chats</div>
              <div className="t-meta" style={{ marginTop: 6, fontSize: 13 }}>
                {chats.length} ongoing — {chats.reduce((a, c) => a + c.unread, 0)} unread.
              </div>
            </div>
            <div style={{ marginTop: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span className="badge">{chats.filter(c => c.type === "group").length} group</span>
              <span className="badge">{chats.filter(c => c.type === "dm").length} DM</span>
              {chats.reduce((a, c) => a + c.unread, 0) > 0 && (
                <span className="badge badge-accent">
                  {chats.reduce((a, c) => a + c.unread, 0)} unread
                </span>
              )}
            </div>
          </button>
        </div>

        {/* ── Quick start row ──────────────────────────── */}
        <div style={{
          padding: "14px 16px",
          background: "var(--bg-1)",
          border: "1px solid var(--border-0)",
          borderRadius: 6,
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 36,
        }}>
          <Icons.Sparkles size={16} sw={1.6} style={{ color: "var(--accent)" }} />
          <div style={{ flex: 1, fontSize: 13 }}>
            <strong style={{ fontWeight: 500 }}>Quick start.</strong>{" "}
            <span className="t-dim">Spin up a new conversation in two clicks.</span>
          </div>
          <Btn variant="outline" size="sm" icon={<Icons.MessageDots size={12} />} onClick={onNewDM}>
            New DM
          </Btn>
          <Btn variant="primary" size="sm" icon={<Icons.Users size={12} />} onClick={onNewGroup}>
            New group chat
          </Btn>
        </div>

        {/* ── Recent activity ──────────────────────────── */}
        {recentChats.length > 0 && (
          <div>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12 }}>
              <div>
                <div className="t-eyebrow">Recent activity</div>
                <h2 className="t-h2" style={{ marginTop: 4 }}>Pick up where you left off</h2>
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={onGoChats}
              >
                View all <Icons.ChevronRight size={12} />
              </button>
            </div>
            <div className="col" style={{ gap: 6 }}>
              {recentChats.map(c => {
                const personas = c.participants.map(window.findPersona);
                return (
                  <div
                    key={c.id}
                    className="card card-hov"
                    onClick={() => onOpenChat(c.id)}
                    style={{
                      padding: 14,
                      display: "flex",
                      alignItems: "center",
                      gap: 14,
                      cursor: "pointer",
                    }}
                  >
                    {c.type === "group" ? (
                      <AvatarStack personas={personas} size="sm" max={3} />
                    ) : (
                      <Avatar persona={personas[0]} size="sm" />
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="row" style={{ gap: 8 }}>
                        <span className="mono" style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {c.title}
                        </span>
                        <span className="badge" style={{ height: 18, fontSize: 9.5 }}>
                          {c.type === "group" ? "GROUP" : "DM"}
                        </span>
                        {c.unread > 0 && (
                          <span className="badge badge-accent" style={{ height: 18, fontSize: 9.5 }}>
                            {c.unread} new
                          </span>
                        )}
                      </div>
                      <div className="t-meta" style={{ marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {c.last}
                      </div>
                    </div>
                    <div className="mono t-meta" style={{ fontSize: 11 }}>{c.lastTime}</div>
                    <Icons.ChevronRight size={14} style={{ color: "var(--fg-2)" }} />
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

window.HomeScreen = HomeScreen;
