// screens-chat.jsx — Active chat interface

function ChatSidebar({ chats, activeId, onSelect, onNewDM, onNewGroup, role }) {
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
          const personas = c.participants.map(window.findPersona);
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
  // agent
  const p = window.findPersona(msg.agentId);
  return (
    <div className="msg-row">
      {withAuthor ? <Avatar persona={p} size="sm" /> : <div style={{ width: 28, height: 28, flexShrink: 0 }} />}
      <div className="msg-col">
        {withAuthor && (
          <div className="msg-meta">
            <span className="msg-author" style={{ color: p.color }}>{p.name}</span>
            <span className="msg-time">{msg.time}</span>
          </div>
        )}
        {msg.kind === "typing" ? (
          <div className="msg-bubble" style={{ padding: "8px 14px" }}>
            <div className="typing-row">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        ) : (
          <div className="msg-bubble" style={withAuthor ? null : { marginTop: -4 }}>{msg.text}</div>
        )}
      </div>
    </div>
  );
}

function ChatScreen({ chats, activeId, onSelectChat, onNewDM, onNewGroup, onProvoke, role }) {
  const [messages, setMessages] = React.useState(window.SAMPLE_MESSAGES);
  const [draft, setDraft] = React.useState("");
  const [provoking, setProvoking] = React.useState(false);
  const scrollRef = React.useRef(null);

  const chat = chats.find(c => c.id === activeId) || chats[0];
  const personas = chat?.participants.map(window.findPersona) || [];

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activeId]);

  // Reset messages when switching chats — use a slightly different transcript per chat
  React.useEffect(() => {
    if (!chat) return;
    if (chat.id === "c-001") {
      setMessages(window.SAMPLE_MESSAGES);
    } else if (chat.type === "dm") {
      const p = personas[0];
      setMessages([
        { kind: "system", text: `Direct message started with ${p?.name}` },
        { kind: "agent", agentId: p?.id, time: "10:08", text: greetingFor(p) },
        { kind: "user", time: "10:09", text: "I want to think clearly about something. Help me." },
        { kind: "agent", agentId: p?.id, time: "10:09", text: secondLineFor(p) },
      ]);
    } else {
      setMessages([
        { kind: "system", text: `Group session — ${chat.title}` },
        ...personas.slice(0, 3).map((p, i) => ({
          kind: "agent", agentId: p.id, time: `${10 + i}:0${i}`, text: groupLineFor(p, chat.title),
        })),
      ]);
    }
  }, [activeId]);

  const send = () => {
    if (!draft.trim()) return;
    const t = new Date();
    const time = `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`;
    const newMsgs = [...messages, { kind: "user", time, text: draft.trim() }];
    setMessages(newMsgs);
    setDraft("");

    // Simulate one agent responding
    const respondent = personas[Math.floor(Math.random() * personas.length)];
    if (!respondent) return;
    setMessages(m => [...m, { kind: "typing", agentId: respondent.id }]);
    setTimeout(() => {
      setMessages(m => [
        ...m.filter(x => x.kind !== "typing"),
        { kind: "agent", agentId: respondent.id, time, text: replyFor(respondent, draft) }
      ]);
    }, 1400);
  };

  const provoke = () => {
    setProvoking(true);
    let i = 0;
    const seq = personas.slice(0, 3);
    const tick = () => {
      if (i >= seq.length) {
        setProvoking(false);
        return;
      }
      const p = seq[i];
      setMessages(m => [...m, { kind: "typing", agentId: p.id }]);
      setTimeout(() => {
        const t = new Date();
        const time = `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`;
        setMessages(m => [
          ...m.filter(x => !(x.kind === "typing" && x.agentId === p.id)),
          { kind: "agent", agentId: p.id, time, text: provokeLineFor(p) }
        ]);
        i++;
        setTimeout(tick, 700);
      }, 900);
    };
    tick();
  };

  if (!chat) return <Empty title="No chat selected" />;

  // Walk through messages and figure out when to show author header
  const decorated = [];
  let lastAgent = null;
  messages.forEach((m, idx) => {
    if (m.kind === "agent") {
      decorated.push({ ...m, _withAuthor: m.agentId !== lastAgent });
      lastAgent = m.agentId;
    } else if (m.kind === "typing") {
      decorated.push({ ...m, _withAuthor: m.agentId !== lastAgent });
      lastAgent = m.agentId;
    } else {
      decorated.push(m);
      lastAgent = null;
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
            <IconBtn icon={<Icons.Sliders size={14} />} title="Session settings" />
            <IconBtn icon={<Icons.More size={14} />} title="More" />
          </div>
        </header>

        <div className="chat-messages" ref={scrollRef}>
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
              placeholder={`Message ${chat.type === "dm" ? personas[0]?.name : "the group"}…`}
              style={{ flex: 1, resize: "none" }}
            />
            <Btn
              variant="primary"
              onClick={send}
              disabled={!draft.trim()}
              icon={<Icons.Send size={13} />}
            >
              Send
            </Btn>
          </div>
          <div className="chat-composer-tools">
            <span><span className="kbd">Enter</span> to send · <span className="kbd">Shift</span>+<span className="kbd">Enter</span> for newline</span>
            <div className="spacer" />
            {chat.type === "group" && (
              <button
                className={`btn btn-sm ${provoking ? "btn-outline" : "btn-ghost"}`}
                onClick={provoke}
                disabled={provoking}
                title="Make every agent jump in"
                style={{ color: provoking ? "var(--danger)" : undefined }}
              >
                <Icons.Sparkles size={12} sw={2} style={{ color: provoking ? "var(--danger)" : "var(--accent)" }} />
                {provoking ? "Round in progress…" : "Provoke all agents"}
              </button>
            )}
          </div>
        </footer>
      </main>
    </div>
  );
}

// ─── Toy reply generator (mock) ───────────────────────────
function greetingFor(p) {
  const lines = {
    "p-02": "Hello. Sit. Tell me what's bothering you, and try to use a verb in the present tense.",
    "p-09": "Before we start — who is benefiting from this conversation? Let's notice that out loud.",
    "p-01": "Quick. What's your prior, and what evidence would change it. We'll go from there.",
    "p-05": "Alright. Pour the coffee and tell me what you think happened.",
  };
  return lines[p?.id] || "Alright. Where do you want to start?";
}
function secondLineFor(p) {
  return "Begin from a fact you can defend in one sentence. We'll work outward.";
}
function groupLineFor(p, topic) {
  return `${(topic || "The topic").trim()} is interesting because the framing assumes the answer. Let's interrogate the framing first.`;
}
function replyFor(p, user) {
  // tiny mood-aware mock
  const angry = p.tension > 0.7;
  if (angry) return "That's a stretch. Name one mechanism that actually delivers what you just claimed.";
  if (p.tension < 0.3) return "Slow down. The question behind the question is more useful here. Try restating it.";
  return "Plausible — but I'd want to see two things before I sign on. What's the falsification, and who pays the cost?";
}
function provokeLineFor(p) {
  if (p.tension > 0.7) return "Fine. You asked for it: the entire framing is a category error. Start over.";
  if (p.tension < 0.3) return "I'll only say this: heat doesn't equal insight. But — if it must be said: the consensus is shakier than reported.";
  return "Honestly? The reason we're not converging is that we haven't named the actual disagreement. Let me try.";
}

window.ChatScreen = ChatScreen;
window.ChatSidebar = ChatSidebar;
window.MessageBubble = MessageBubble;
