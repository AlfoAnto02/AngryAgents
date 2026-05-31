// screens-chat.jsx — Active chat interface

function ChatSidebar({ chats, activeId, onSelect, onNewDM, onNewGroup, role, isOpen }) {
  const { byId } = window.useAgents();
  const [searchQ, setSearchQ] = React.useState("");
  const [topicQ, setTopicQ] = React.useState("");
  const [agentQ, setAgentQ] = React.useState("");
  const [topicSugg, setTopicSugg] = React.useState([]);
  const [agentSugg, setAgentSugg] = React.useState([]);

  // Unique topics that appear in at least one chat
  const allChatTopics = React.useMemo(() => {
    const s = new Set();
    chats.forEach(c => (c.topics || []).forEach(t => t && s.add(t)));
    return [...s].sort((a, b) => a.localeCompare(b));
  }, [chats]);

  // Unique agents that appear in at least one chat
  const allChatAgents = React.useMemo(() => {
    const map = new Map();
    chats.forEach(c =>
      (c.participants || []).forEach(id => {
        if (!map.has(id)) { const p = byId(id); if (p) map.set(id, p); }
      })
    );
    return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [chats]);

  const filtered = React.useMemo(() => {
    return chats.filter(c => {
      if (searchQ && !c.title.toLowerCase().includes(searchQ.toLowerCase())) return false;
      if (topicQ) {
        const q = topicQ.toLowerCase();
        if (!(c.topics || []).some(t => t.toLowerCase().includes(q))) return false;
      }
      if (agentQ) {
        const q = agentQ.toLowerCase();
        const names = (c.participants || []).map(id => byId(id)?.name || "").join(" ").toLowerCase();
        if (!names.includes(q)) return false;
      }
      return true;
    });
  }, [chats, searchQ, topicQ, agentQ]);

  const activeFilters = (topicQ ? 1 : 0) + (agentQ ? 1 : 0);

  const filterInputStyle = {
    width: "100%", height: 28, padding: "0 8px 0 28px",
    background: "var(--bg-2)", border: "1px solid var(--border-0)",
    borderRadius: "var(--r-input)", color: "var(--fg-0)",
    fontSize: 12, outline: "none", fontFamily: "inherit",
  };
  const filterIconStyle = {
    position: "absolute", left: 8, top: "50%",
    transform: "translateY(-50%)", color: "var(--fg-3)", pointerEvents: "none",
  };
  const suggBoxStyle = {
    position: "absolute", top: "100%", left: 0, right: 0, zIndex: 30,
    background: "var(--bg-1)", border: "1px solid var(--border-1)",
    borderRadius: "var(--r-card)", marginTop: 2,
    boxShadow: "0 4px 12px rgba(0,0,0,0.25)", overflow: "hidden",
  };
  const suggItemStyle = {
    width: "100%", textAlign: "left", padding: "6px 10px",
    background: "transparent", border: 0, color: "var(--fg-0)",
    fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
  };

  return (
    <aside className={`chat-sidebar${isOpen ? " open" : ""}`}>
      <div className="chat-sidebar-head">
        <div className="t-eyebrow" style={{ flex: 1 }}>Conversations</div>
        {activeFilters > 0 && (
          <span className="badge badge-accent" style={{ marginRight: 4 }}>{activeFilters} filter{activeFilters > 1 ? "s" : ""}</span>
        )}
        <span className="badge">{filtered.length}{filtered.length !== chats.length ? `/${chats.length}` : ""}</span>
      </div>
      <div className="chat-sidebar-search">
        {/* Title search */}
        <div className="lib-search">
          <span className="lib-search-icon"><Icons.Search size={13} /></span>
          <input
            className="input"
            placeholder="Search chats…"
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            style={{ height: 32, fontSize: 12 }}
          />
          {searchQ && (
            <button
              style={{ position: "absolute", right: 6, top: "50%", transform: "translateY(-50%)", background: "none", border: 0, cursor: "pointer", color: "var(--fg-3)", padding: 2 }}
              onMouseDown={() => setSearchQ("")}
            >
              <Icons.X size={11} />
            </button>
          )}
        </div>

        {/* Topic filter */}
        <div style={{ position: "relative", marginTop: 6 }}>
          <span style={filterIconStyle}><Icons.Hash size={11} /></span>
          <input
            style={{ ...filterInputStyle, borderColor: topicQ ? "var(--accent-border)" : "var(--border-0)" }}
            placeholder="Filter by topic…"
            value={topicQ}
            onChange={e => {
              const v = e.target.value;
              setTopicQ(v);
              setTopicSugg(v.trim() ? allChatTopics.filter(t => t.toLowerCase().includes(v.toLowerCase())).slice(0, 5) : []);
            }}
            onBlur={() => setTimeout(() => setTopicSugg([]), 150)}
            onKeyDown={e => { if (e.key === "Escape") { setTopicQ(""); setTopicSugg([]); } }}
          />
          {topicQ && (
            <button
              style={{ position: "absolute", right: 6, top: "50%", transform: "translateY(-50%)", background: "none", border: 0, cursor: "pointer", color: "var(--fg-3)", padding: 2 }}
              onMouseDown={() => { setTopicQ(""); setTopicSugg([]); }}
            >
              <Icons.X size={10} />
            </button>
          )}
          {topicSugg.length > 0 && (
            <div style={suggBoxStyle}>
              {topicSugg.map(t => (
                <button key={t} style={suggItemStyle} type="button"
                  onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                  onMouseDown={() => { setTopicQ(t); setTopicSugg([]); }}
                >
                  <Icons.Hash size={10} style={{ color: "var(--accent)", flexShrink: 0 }} />
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Agent filter */}
        <div style={{ position: "relative", marginTop: 6 }}>
          <span style={filterIconStyle}><Icons.User size={11} /></span>
          <input
            style={{ ...filterInputStyle, borderColor: agentQ ? "var(--accent-border)" : "var(--border-0)" }}
            placeholder="Filter by character…"
            value={agentQ}
            onChange={e => {
              const v = e.target.value;
              setAgentQ(v);
              setAgentSugg(v.trim() ? allChatAgents.filter(p => p.name.toLowerCase().includes(v.toLowerCase())).slice(0, 5) : []);
            }}
            onBlur={() => setTimeout(() => setAgentSugg([]), 150)}
            onKeyDown={e => { if (e.key === "Escape") { setAgentQ(""); setAgentSugg([]); } }}
          />
          {agentQ && (
            <button
              style={{ position: "absolute", right: 6, top: "50%", transform: "translateY(-50%)", background: "none", border: 0, cursor: "pointer", color: "var(--fg-3)", padding: 2 }}
              onMouseDown={() => { setAgentQ(""); setAgentSugg([]); }}
            >
              <Icons.X size={10} />
            </button>
          )}
          {agentSugg.length > 0 && (
            <div style={suggBoxStyle}>
              {agentSugg.map(p => (
                <button key={p.id} style={suggItemStyle} type="button"
                  onMouseEnter={e => e.currentTarget.style.background = "var(--bg-2)"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                  onMouseDown={() => { setAgentQ(p.name); setAgentSugg([]); }}
                >
                  <Avatar persona={p} size="xs" />
                  {p.name}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="row" style={{ gap: 6, marginTop: 8 }}>
          <Btn variant="primary" size="sm" block icon={<Icons.Plus size={12} sw={2.5} />} onClick={onNewDM}>
            New DM
          </Btn>
          <Btn variant="outline" size="sm" block icon={<Icons.Users size={12} />} onClick={onNewGroup}>
            New group
          </Btn>
        </div>
      </div>
      <div className="chat-list">
        {filtered.length === 0 && (
          <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--fg-3)", fontSize: 12 }}>
            No chats match these filters.
          </div>
        )}
        {filtered.map(c => {
          const personas = c.participants.map(id => byId(id)).filter(Boolean);
          return (
            <div
              key={c.id}
              className={`chat-list-item ${activeId === c.id ? "active" : ""}`}
              onClick={() => onSelect(c.id)}
            >
              {c.type === "group" ? (
                <AvatarStack personas={personas} size="sm" max={3} />
              ) : (
                <Avatar persona={personas[0]} size="sm" />
              )}
              <div className="chat-list-meta">
                <div className="chat-list-title">
                  <span className="chat-list-title-text" title={c.title}>{c.title}</span>
                  <span className="chat-list-time">{c.lastTime}</span>
                </div>
                <div className="row" style={{ gap: 4 }}>
                  <span className="chat-list-preview">{c.last}</span>
                  {c.unread > 0 && (
                    <span className="badge badge-accent" style={{ height: 16, padding: "0 6px", fontSize: 9.5 }}>{c.unread}</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function MessageBubble({ msg, withAuthor }) {
  const { byId } = window.useAgents();
  if (msg.kind === "system") {
    return <div className="msg-system">{msg.text}</div>;
  }
  if (msg.kind === "user") {
    return (
      <div className="msg-row self">
        <div className="msg-col" style={{ alignItems: "flex-end" }}>
          <div className="msg-meta" style={{ flexDirection: "row-reverse" }}>
            <span className="msg-time">{msg.time}</span>
            <span className="msg-author" style={{ color: "var(--accent)" }}>YOU</span>
          </div>
          <div className="msg-bubble">{msg.text}</div>
        </div>
      </div>
    );
  }
  // agent — author is the HMAC digest; persona_id may be present
  const p = msg.persona_id ? byId(msg.persona_id) : null;
  const authorColor = p?.color || "var(--fg-1)";
  const displayAuthor = p?.name || (msg.author ? msg.author.split("::")[0] : "AGENT");
  return (
    <div className="msg-row">
      {withAuthor ? <Avatar persona={p} size="sm" /> : <div style={{ width: 28, height: 28, flexShrink: 0 }} />}
      <div className="msg-col">
        {withAuthor && (
          <div className="msg-meta">
            <span className="msg-author" style={{ color: authorColor }}>{displayAuthor}</span>
            <span className="msg-time">{msg.time}</span>
          </div>
        )}
        <div className="msg-bubble" style={withAuthor ? null : { marginTop: -4 }}>{msg.text}</div>
      </div>
    </div>
  );
}

function ChatScreen({ chats, activeId, onSelectChat, onNewDM, onNewGroup, role }) {
  const { byId } = window.useAgents();
  const [messages, setMessages] = React.useState([]);
  const [draft, setDraft] = React.useState("");
  const [sending, setSending] = React.useState(false);
  const [chatStatus, setChatStatus] = React.useState("pending");
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [infoOpen, setInfoOpen] = React.useState(false);
  const [profilePersona, setProfilePersona] = React.useState(null);
  const scrollRef = React.useRef(null);
  // True when the user is within 100px of the bottom — used to decide whether
  // to auto-scroll on new messages. We use a ref (not state) so the scroll
  // listener never causes a re-render.
  const isNearBottomRef = React.useRef(true);

  const chat = chats.find(c => c.id === activeId) || chats[0];
  const personas = chat ? chat.participants.map(id => byId(id)).filter(Boolean) : [];

  // When the active chat changes, always jump to the bottom and reset the flag.
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      isNearBottomRef.current = true;
    }
  }, [activeId]);

  // When messages arrive, only scroll if the user is already near the bottom.
  // This lets users scroll up to read history without being yanked back down.
  React.useEffect(() => {
    if (scrollRef.current && isNearBottomRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleChatScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    isNearBottomRef.current = scrollHeight - scrollTop - clientHeight < 100;
  };

  // Load messages + status and poll for agent replies
  React.useEffect(() => {
    if (!chat) return;
    let cancelled = false;

    const load = () => {
      const fetches = [window.api.get(`/ui/chats/${chat.id}/messages`)];
      if (chat.type === "group") {
        fetches.push(window.api.get(`/ui/chats/${chat.id}/status`).catch(() => null));
      }
      Promise.all(fetches).then(([msgs, statusData]) => {
        if (cancelled) return;
        setMessages(msgs);
        if (statusData) setChatStatus(statusData.status);
      }).catch(() => { if (!cancelled) setMessages([]); });
    };

    load();
    const interval = setInterval(load, 2000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [chat && chat.id]);

  const send = async () => {
    if (!draft.trim() || sending) return;
    const text = draft.trim();
    setDraft("");
    setSending(true);
    // Sending your own message always snaps to the bottom, even if you'd scrolled up.
    isNearBottomRef.current = true;
    try {
      await window.api.post(`/ui/chats/${chat.id}/messages`, { text });
      const fresh = await window.api.get(`/ui/chats/${chat.id}/messages`);
      setMessages(fresh);
    } catch (err) {
      console.error("Send failed:", err);
    } finally {
      setSending(false);
    }
  };

  const stopChat = () => {
    window.api.post(`/ui/chats/${chat.id}/stop`, {})
      .then(() => setChatStatus("stopped"))
      .catch(err => console.error("Stop failed:", err));
  };

  const resumeChat = () => {
    window.api.post(`/ui/chats/${chat.id}/start`, {})
      .then(() => setChatStatus("running"))
      .catch(err => console.error("Resume failed:", err));
  };

  if (!chat) return <Empty title="No chat selected" />;

  // Group consecutive agent messages by author for display
  const decorated = [];
  let lastAuthor = null;
  messages.forEach((m) => {
    if (m.kind === "agent") {
      const key = m.author || m.persona_id || null;
      decorated.push({ ...m, _withAuthor: key !== lastAuthor });
      lastAuthor = key;
    } else {
      decorated.push(m);
      lastAuthor = null;
    }
  });

  return (
    <div className="chat-shell" data-screen-label="active-chat">
      {sidebarOpen && (
        <div className="mobile-overlay open" onClick={() => setSidebarOpen(false)} />
      )}
      <ChatSidebar
        chats={chats}
        activeId={chat.id}
        onSelect={(id) => { onSelectChat(id); setSidebarOpen(false); }}
        onNewDM={onNewDM}
        onNewGroup={onNewGroup}
        role={role}
        isOpen={sidebarOpen}
      />
      <main className="chat-main">
        <header className="chat-header">
          <button
            className="btn btn-ghost btn-icon topnav-hamburger"
            onClick={() => setSidebarOpen(o => !o)}
            title="Show conversations"
          >
            <Icons.Menu size={20} />
          </button>
          <button
            className="chat-header-id"
            onClick={() => setInfoOpen(true)}
            title="Informazioni chat"
          >
            {chat.type === "group" ? (
              <AvatarStack personas={personas} size="md" max={4} />
            ) : (
              <Avatar persona={personas[0]} size="md" />
            )}
            <div className="chat-header-info">
            <div className="chat-header-title">{chat.title}</div>
            <div className="chat-header-sub">
              {chat.type === "group" ? (
                <>
                  <Icons.Users size={11} />
                  {personas.length} agents
                  <span className="dot-sep" />
                  <span className="mono" style={{ fontSize: 11 }}>{chat.tone || "Debate"}</span>
                  {chat.topics?.map(t => (
                    <span key={t} className="badge" style={{ height: 18 }}>#{t}</span>
                  ))}
                  <span className="dot-sep" />
                  {chatStatus === "running" && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--ok)" }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ok)", animation: "typingDot 1.4s infinite" }} />
                      <span className="mono" style={{ fontSize: 11 }}>live</span>
                    </span>
                  )}
                  {chatStatus === "stopped" && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--warn)" }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--warn)" }} />
                      <span className="mono" style={{ fontSize: 11 }}>paused</span>
                    </span>
                  )}
                  {chatStatus === "done" && (
                    <span className="mono" style={{ fontSize: 11, color: "var(--fg-3)" }}>finished</span>
                  )}
                </>
              ) : (
                <>
                  <Icons.MessageDots size={11} />
                  Direct message
                  <span className="dot-sep" />
                  <span className="mono" style={{ fontSize: 11 }}>{personas[0]?.source_title}</span>
                </>
              )}
            </div>
          </div>
          <Icons.ChevronDown size={14} style={{ color: "var(--fg-3)", flexShrink: 0 }} />
          </button>
          <div className="row" style={{ gap: 6 }}>
            {chat.type === "group" && chatStatus === "running" && (
              <Btn
                variant="outline"
                size="sm"
                icon={<Icons.Pause size={12} />}
                onClick={stopChat}
                title="Metti in pausa la generazione dei messaggi"
              >
                Pausa
              </Btn>
            )}
            {chat.type === "group" && chatStatus === "stopped" && (
              <Btn
                variant="primary"
                size="sm"
                icon={<Icons.Play size={12} />}
                onClick={resumeChat}
                title="Riprendi la generazione dei messaggi"
              >
                Riprendi
              </Btn>
            )}
          </div>
        </header>

        <div className="chat-messages" ref={scrollRef} onScroll={handleChatScroll}>
          {decorated.map((m, i) => (
            <MessageBubble key={i} msg={m} withAuthor={m._withAuthor !== false} />
          ))}
          {decorated.length === 0 && (
            <Empty title="No messages yet" sub="Type below to kick things off." icon={<Icons.MessageDots size={20} />} />
          )}
        </div>

        <footer className="chat-composer">
          <div className="chat-composer-input">
            <textarea
              className="input textarea"
              rows={1}
              value={draft}
              onChange={e => setDraft(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
              }}
              placeholder={`Message ${chat.type === "dm" ? (personas[0]?.name || "the agent") : "the group"}…`}
              style={{ flex: 1, resize: "none" }}
              disabled={sending}
            />
            <Btn
              variant="primary"
              onClick={send}
              disabled={!draft.trim() || sending}
              icon={<Icons.Send size={13} />}
            >
              {sending ? "Sending…" : "Send"}
            </Btn>
          </div>
          <div className="chat-composer-tools">
            <span><span className="kbd">Enter</span> to send · <span className="kbd">Shift</span>+<span className="kbd">Enter</span> for newline</span>
          </div>
        </footer>
      </main>

      <Modal
        open={infoOpen}
        onClose={() => setInfoOpen(false)}
        width="440px"
        title={<span><Icons.Info size={15} style={{ verticalAlign: "-2px", marginRight: 8 }} />Informazioni chat</span>}
      >
        <div className="col" style={{ gap: 18 }}>
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 6 }}>Titolo</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{chat.title}</div>
          </div>
          <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
            <span className="badge badge-accent">{chat.type === "group" ? "Gruppo" : "Messaggio diretto"}</span>
            <span className="badge">{chat.tone || "Debate"}</span>
            {chatStatus === "running" && <span className="badge badge-ok badge-dot">Live</span>}
            {chatStatus === "stopped" && <span className="badge badge-dot">In pausa</span>}
            {chatStatus === "done" && <span className="badge badge-dot">Conclusa</span>}
          </div>
          {chat.topics?.length > 0 && (
            <div>
              <div className="t-eyebrow" style={{ marginBottom: 8 }}>{chat.topics.length > 1 ? "Argomenti" : "Argomento"}</div>
              <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
                {chat.topics.map(t => (
                  <span key={t} className="tag-chip"><span style={{ opacity: 0.6 }}>#</span>{t}</span>
                ))}
              </div>
            </div>
          )}
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 8 }}>
              {personas.length} partecipant{personas.length === 1 ? "e" : "i"}
            </div>
            <div className="col" style={{ gap: 6 }}>
              {personas.map(p => (
                <button
                  key={p.id}
                  className="chat-info-participant"
                  onClick={() => { setInfoOpen(false); setProfilePersona(p); }}
                  title={`Apri il profilo di ${p.name}`}
                >
                  <Avatar persona={p} size="md" />
                  <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                    <div className="mono" style={{ fontWeight: 600, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.name}</div>
                    <div className="t-meta" style={{ fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p.source_title || (p.source_type === "fiction" ? "Personaggio di fantasia" : "Persona reale")}
                    </div>
                  </div>
                  <Icons.ChevronRight size={14} style={{ color: "var(--fg-3)", flexShrink: 0 }} />
                </button>
              ))}
            </div>
          </div>
        </div>
      </Modal>

      {profilePersona && (
        <AgentProfileModal
          persona={profilePersona}
          onClose={() => setProfilePersona(null)}
        />
      )}
    </div>
  );
}

window.ChatScreen = ChatScreen;
window.ChatSidebar = ChatSidebar;
window.MessageBubble = MessageBubble;
