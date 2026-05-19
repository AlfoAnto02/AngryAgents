// app.jsx — root component, routing, tweaks

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "userAccent": "#7C3AED",
  "adminAccent": "#F59E0B",
  "density": "regular",
  "showSystemMessages": true,
  "typingSpeed": "normal"
}/*EDITMODE-END*/;

const ACCENT_OPTIONS = ["#7C3AED", "#EF4444", "#3B82F6", "#22C55E"];
const ADMIN_OPTIONS = ["#F59E0B", "#EC4899", "#06B6D4", "#A78BFA"];

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // ─── auth / role
  const [authState, setAuthState] = React.useState({ screen: "login" }); // login | register | app
  const [userRole, setUserRole] = React.useState("user"); // user | admin -- account's permission
  const [role, setRole] = React.useState("user"); // user | admin -- current view (admins can switch)
  const [user, setUser] = React.useState({ name: "Ada Lovelace", handle: "ada-lovelace" });

  // ─── app navigation
  const [page, setPage] = React.useState("home"); // home | library | newdm | newgroup | chat | admin
  const [adminSection, setAdminSection] = React.useState("overview");

  // ─── chat session state
  const [chats, setChats] = React.useState(window.SAMPLE_CHATS);
  const [activeChatId, setActiveChatId] = React.useState("c-001");
  const [sessionDraft, setSessionDraft] = React.useState([]); // agent ids currently selected for a NEW group

  // when role flips to admin, jump to admin page
  React.useEffect(() => {
    if (role === "admin" && authState.screen === "app") {
      setPage("admin");
    } else if (role === "user" && page === "admin") {
      setPage("home");
    }
  }, [role]);

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

  const handleLaunchGroup = ({ participants, topics, tone }) => {
    const id = `c-${Date.now().toString().slice(-4)}`;
    const personas = participants.map(window.findPersona);
    const newChat = {
      id, type: "group",
      title: topics[0] || "Untitled session",
      topics, tone,
      participants,
      unread: 0,
      last: "Session started",
      lastTime: "now",
      started: "now",
    };
    setChats([newChat, ...chats]);
    setActiveChatId(id);
    setSessionDraft([]);
    setPage("chat");
  };

  const handleLaunchDM = ({ persona, opener }) => {
    const id = `c-${Date.now().toString().slice(-4)}`;
    const newChat = {
      id, type: "dm",
      title: persona.name,
      participants: [persona.id],
      unread: 0,
      last: opener || "Session started",
      lastTime: "now",
      started: "now",
    };
    setChats([newChat, ...chats]);
    setActiveChatId(id);
    setPage("chat");
  };

  const handleOpenAgent = (persona) => {
    // single-click on an agent card → start DM flow with that agent preselected
    handleLaunchDM({ persona, opener: "" });
  };

  // ─── render auth shells
  if (authState.screen === "login") {
    return (
      <>
        <AuthShell>
          <LoginScreen
            onSubmit={() => setAuthState({ screen: "app" })}
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
            onSubmit={(form) => {
              setUser({ name: `${form.firstName} ${form.lastName}`, handle: `${form.firstName}-${form.lastName}`.toLowerCase() });
              // new registrations are always common users
              setUserRole("user");
              setRole("user");
              setAuthState({ screen: "app" });
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
        onRoleChange={(r) => { if (userRole === "admin") setRole(r); }}
        page={page}
        onNav={setPage}
        user={user}
        onLogout={() => setAuthState({ screen: "login" })}
      />
      <div className="app-body">
        {role === "admin" && page === "admin" && (
          <AdminDashboard section={adminSection} onSection={setAdminSection} />
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
        {role === "user" && page === "newgroup" && (
          <NewGroupScreen
            initialSelection={sessionDraft}
            onCancel={() => setPage("home")}
            onLaunch={handleLaunchGroup}
          />
        )}
        {role === "user" && page === "newdm" && (
          <NewDMScreen
            onCancel={() => setPage("home")}
            onLaunch={handleLaunchDM}
          />
        )}
        {role === "user" && page === "chat" && (
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
          <AvatarStack personas={sessionDraft.map(window.findPersona)} size="sm" max={5} />
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
root.render(<App />);
