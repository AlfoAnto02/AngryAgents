// app.jsx — root component, routing, tweaks

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { err: null }; }
  static getDerivedStateFromError(err) { return { err }; }
  render() {
    if (this.state.err) {
      return (
        <div style={{ padding: 32, fontFamily: "monospace", color: "#ef4444", background: "#0a0a0a", minHeight: "100vh" }}>
          <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 8 }}>React crash — open DevTools for full stack trace</div>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{String(this.state.err)}</pre>
          <button onClick={() => this.setState({ err: null })} style={{ marginTop: 16, padding: "6px 12px", cursor: "pointer" }}>Retry</button>
        </div>
      );
    }
    return this.props.children;
  }
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "userAccent": "#7C3AED",
  "adminAccent": "#F59E0B",
  "density": "regular",
  "showSystemMessages": true,
  "typingSpeed": "normal"
}/*EDITMODE-END*/;

// User accent — orange family, matching the warmth of the app icon.
const ACCENT_OPTIONS = ["#7C3AED", "#8B5CF6", "#9333EA", "#A21CAF"];
const ADMIN_OPTIONS = ["#F59E0B", "#EC4899", "#06B6D4", "#A78BFA"];

function App() {
  const { byId, refresh: refreshAgents } = window.useAgents();
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // ─── auth / role
  const [authState, setAuthState] = React.useState({ screen: "login" });
  const [userRole, setUserRole] = React.useState("user");
  const [role, setRole] = React.useState("user");
  const [user, setUser] = React.useState({ name: "Ada Lovelace", handle: "ada-lovelace" });

  // ─── app navigation
  const [page, setPage] = React.useState("home");
  const [adminSection, setAdminSection] = React.useState("overview");

  // ─── chat session state
  const [chats, setChats] = React.useState([]);
  const [activeChatId, setActiveChatId] = React.useState(null);
  const [sessionDraft, setSessionDraft] = React.useState([]);

  // Session-expired event (fired by api.js when refresh fails)
  React.useEffect(() => {
    const handler = () => {
      setChats([]);
      setActiveChatId(null);
      setAuthState({ screen: "login" });
    };
    window.addEventListener("aa:session-expired", handler);
    return () => window.removeEventListener("aa:session-expired", handler);
  }, []);

  // Session restore on mount
  React.useEffect(() => {
    if (!window.api.token) return;
    window.api.get("/auth/me")
      .then(me => {
        setUser({ name: `${me.name} ${me.surname}`, handle: me.slug });
        const r = me.role === "admin" ? "admin" : "user";
        setUserRole(r);
        setRole(r);
        if (r === "admin") setPage("admin");
        setAuthState({ screen: "app" });
      })
      .catch(() => window.api.clear());
  }, []);

  // Load chats when entering app
  const reloadChats = React.useCallback(async () => {
    if (!window.api.token) return;
    try {
      const list = await window.api.get("/ui/chats");
      setChats(list);
    } catch (e) {
      setChats([]);
    }
  }, []);

  React.useEffect(() => {
    if (authState.screen === "app") {
      reloadChats();
      refreshAgents();
    }
  }, [authState.screen, reloadChats, refreshAgents]);


  // Inject accent CSS overrides
  React.useEffect(() => {
    const id = "__accent-override";
    let style = document.getElementById(id);
    if (!style) {
      style = document.createElement("style");
      style.id = id;
      document.head.appendChild(style);
    }
    style.textContent = `
      :root { --accent: ${t.userAccent}; --accent-hover: ${t.userAccent}; }
      .role-admin { --accent: ${t.adminAccent}; --accent-hover: ${t.adminAccent}; --admin: ${t.adminAccent}; }
    `;
  }, [t.userAccent, t.adminAccent]);

  // ─── handlers
  const handleAddToSession = (id) => {
    setSessionDraft(s => s.includes(id) ? s.filter(x => x !== id) : s.length >= 8 ? s : [...s, id]);
  };

  const handleNewDM = () => setPage("newdm");
  const handleNewGroup = () => setPage("newgroup");

  const handleLaunchGroup = async ({ participants, topics, tone }) => {
    try {
      const chat = await window.api.post("/ui/chats", { type: "group", participants, topics, tone });
      setChats(cs => [chat, ...cs]);
      setActiveChatId(chat.id);
      setSessionDraft([]);
      // Admins (judges) enter the chat too so they can post messages.
      setPage("chat");
    } catch (err) {
      alert("Failed to create group chat: " + err.message);
    }
  };

  const handleLaunchDM = async ({ persona, opener }) => {
    try {
      const chat = await window.api.post("/ui/chats", { type: "dm", participants: [persona.id], opener });
      setChats(cs => [chat, ...cs]);
      setActiveChatId(chat.id);
      // Admins (judges) enter the chat too so they can post messages.
      setPage("chat");
    } catch (err) {
      alert("Failed to create DM: " + err.message);
    }
  };

  const [agentProfileOpen, setAgentProfileOpen] = React.useState(null);

  const handleOpenAgent = (persona) => {
    setAgentProfileOpen(persona);
  };

  // Admin: open any session row in the chat view so they can post as a
  // participant. The session ID matches the chat ID; if the chat isn't in
  // the local `chats` cache (admin may not own it), splice in a stub so the
  // sidebar and the message-poller in ChatScreen have something to bind to.
  const handleOpenChat = async (session) => {
    setActiveChatId(session.id);
    setPage("chat");
    const known = chats.find(c => c.id === session.id);
    if (!known) {
      const stub = {
        id: session.id,
        type: (session.participants && session.participants.length > 1) ? "group" : "dm",
        title: session.topic || (session.participants && session.participants[0]) || "Session",
        participants: session.participants || [],
        topics: session.topic ? [session.topic] : [],
        tone: "Debate",
        last: "",
        lastTime: session.date || "",
        unread: 0,
      };
      setChats(cs => [stub, ...cs]);
      // Best-effort: ask the backend for the canonical chat record and replace the stub.
      try {
        const real = await window.api.get(`/ui/chats/${session.id}`);
        if (real && real.id) {
          setChats(cs => [real, ...cs.filter(c => c.id !== real.id)]);
        }
      } catch (e) { /* stub is fine */ }
    }
  };

  // ─── render auth shells
  if (authState.screen === "login") {
    return (
      <>
        <AuthShell>
          <LoginScreen
            onSubmit={async ({ email, password }) => {
              try {
                const data = await window.api.post("/auth/login", { email, password });
                window.api.setToken(data.access_token, data.refresh_token);
                const me = data.user;
                setUser({ name: `${me.name} ${me.surname}`, handle: me.slug });
                const r = me.role === "admin" ? "admin" : "user";
                setUserRole(r);
                setRole(r);
                if (r === "admin") setPage("admin");
                setAuthState({ screen: "app" });
              } catch (err) {
                alert("Login failed. Check email and password.");
              }
            }}
            onSwitch={() => setAuthState({ screen: "register" })}
          />
        </AuthShell>
        {renderTweaksPanel(t, setTweak)}
      </>
    );
  }
  if (authState.screen === "register") {
    return (
      <>
        <AuthShell>
          <RegisterScreen
            onSubmit={async (form) => {
              try {
                const username = (form.firstName + form.lastName).toLowerCase().replace(/[^a-z0-9]/g, "") + Date.now().toString().slice(-4);
                await window.api.post("/auth/register", {
                  username,
                  name: form.firstName,
                  surname: form.lastName,
                  email: form.email,
                  password: form.password,
                  role: "common",
                });
                const data = await window.api.post("/auth/login", { email: form.email, password: form.password });
                window.api.setToken(data.access_token, data.refresh_token);
                const me = data.user;
                setUser({ name: `${me.name} ${me.surname}`, handle: me.slug });
                setUserRole("user");
                setRole("user");
                setAuthState({ screen: "app" });
              } catch (err) {
                alert("Registration failed: " + err.message);
              }
            }}
            onSwitch={() => setAuthState({ screen: "login" })}
          />
        </AuthShell>
        {renderTweaksPanel(t, setTweak)}
      </>
    );
  }

  // ─── main app
  return (
    <div className={`app ${role === "admin" ? "role-admin" : ""}`}>
      <TopNav
        role={role}
        userRole={userRole}
        page={page}
        onNav={setPage}
        user={user}
        onLogout={() => {
          window.api.clear();
          setChats([]);
          setActiveChatId(null);
          setAuthState({ screen: "login" });
        }}
      />
      <div className="app-body">
        {role === "admin" && page === "admin" && (
          <AdminDashboard
            section={adminSection}
            onSection={setAdminSection}
            onNewDM={handleNewDM}
            onNewGroup={handleNewGroup}
            onOpenChat={handleOpenChat}
            onNav={setPage}
            user={user}
          />
        )}
        {role === "admin" && page === "library" && (
          <LibraryScreen
            session={[]}
            onAddToSession={() => {}}
            onStartDM={(p) => handleLaunchDM({ persona: p, opener: "" })}
            onOpenAgent={handleOpenAgent}
          />
        )}
        {role === "user" && page === "home" && (
          <HomeScreen
            user={user}
            chats={chats}
            onGoAgents={() => setPage("library")}
            onGoChats={() => setPage("chat")}
            onOpenChat={(id) => { setActiveChatId(id); setPage("chat"); }}
            onNewDM={handleNewDM}
            onNewGroup={handleNewGroup}
          />
        )}
        {role === "user" && page === "library" && (
          <LibraryScreen
            session={sessionDraft}
            onAddToSession={handleAddToSession}
            onStartDM={(p) => handleLaunchDM({ persona: p, opener: "" })}
            onOpenAgent={handleOpenAgent}
          />
        )}
        {page === "newgroup" && (
          <NewGroupScreen
            initialSelection={sessionDraft}
            onCancel={() => setPage(role === "admin" ? "admin" : "home")}
            onLaunch={handleLaunchGroup}
          />
        )}
        {page === "newdm" && (
          <NewDMScreen
            onCancel={() => setPage(role === "admin" ? "admin" : "home")}
            onLaunch={handleLaunchDM}
          />
        )}
        {/* Chat playback for BOTH roles. Admins (judges) post as participants. */}
        {page === "chat" && (
          <ChatScreen
            chats={chats}
            activeId={activeChatId}
            onSelectChat={setActiveChatId}
            onNewDM={handleNewDM}
            onNewGroup={handleNewGroup}
            role={role}
          />
        )}
      </div>

      {role === "user" && page === "library" && sessionDraft.length > 0 && (
        <div style={{
          position: "fixed",
          bottom: 16,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 50,
          background: "var(--bg-1)",
          border: "1px solid var(--border-2)",
          borderRadius: 8,
          padding: "10px 14px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          boxShadow: "0 12px 32px rgba(0,0,0,0.5)",
        }}>
          <AvatarStack personas={sessionDraft.map(id => byId(id)).filter(Boolean)} size="sm" max={5} />
          <div style={{ fontSize: 12.5 }}>
            <strong>{sessionDraft.length}</strong> agent{sessionDraft.length === 1 ? "" : "s"} in your session
          </div>
          <Btn variant="ghost" size="sm" onClick={() => setSessionDraft([])}>Clear</Btn>
          <Btn
            variant="primary"
            size="sm"
            icon={<Icons.Users size={12} />}
            onClick={() => setPage("newgroup")}
          >
            Start group chat
          </Btn>
        </div>
      )}

      {renderTweaksPanel(t, setTweak)}

      {agentProfileOpen && (
        <AgentProfileModal
          persona={agentProfileOpen}
          onClose={() => setAgentProfileOpen(null)}
          onStartDM={(p) => handleLaunchDM({ persona: p, opener: "" })}
          onAddToSession={(p) => {
            if (!sessionDraft.includes(p.id)) setSessionDraft(d => [...d, p.id]);
          }}
          inSession={sessionDraft.includes(agentProfileOpen.id)}
        />
      )}
    </div>
  );
}

function renderTweaksPanel(t, setTweak) {
  return (
    <TweaksPanel>
      <TweakSection label="Theme" />
      <TweakColor
        label="User accent"
        value={t.userAccent}
        options={ACCENT_OPTIONS}
        onChange={(v) => setTweak("userAccent", v)}
      />
      <TweakColor
        label="Admin accent"
        value={t.adminAccent}
        options={ADMIN_OPTIONS}
        onChange={(v) => setTweak("adminAccent", v)}
      />
      <TweakSection label="Behaviour" />
      <TweakToggle
        label="System messages"
        value={t.showSystemMessages}
        onChange={(v) => setTweak("showSystemMessages", v)}
      />
      <TweakRadio
        label="Typing speed"
        value={t.typingSpeed}
        options={["slow", "normal", "fast"]}
        onChange={(v) => setTweak("typingSpeed", v)}
      />
    </TweaksPanel>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<ErrorBoundary><AgentsProvider><App /></AgentsProvider></ErrorBoundary>);
