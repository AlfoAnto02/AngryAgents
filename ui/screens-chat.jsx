// screens-chat.jsx — Active chat interface

function ChatSidebar({ chats, activeId, onSelect, onNewDM, onNewGroup, role }) {
  const { byId } = window.useAgents();
  return (
    <aside className="chat-sidebar">
      <div className="chat-sidebar-head">
        <div className="t-eyebrow" style={{ flex: 1 }}>Conversations</div>
        <span className="badge">{chats.length}</span>
      </div>
      <div className="chat-sidebar-search">
        <div className="lib-search">
          <span className="lib-search-icon"><Icons.Search size={13} /></span>
          <input className="input" placeholder="Search chats…" style={{ height: 32, fontSize: 12 }} />
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
        {chats.map(c => {
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
      <ChatSidebar
        chats={chats}
        activeId={chat.id}
        onSelect={onSelectChat}
        onNewDM={onNewDM}
        onNewGroup={onNewGroup}
        role={role}
      />
      <main className="chat-main">
        <header className="chat-header">
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
            <IconBtn icon={<Icons.Sliders size={14} />} title="Session settings" />
            <IconBtn icon={<Icons.More size={14} />} title="More" />
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
    </div>
  );
}

window.ChatScreen = ChatScreen;
window.ChatSidebar = ChatSidebar;
window.MessageBubble = MessageBubble;
