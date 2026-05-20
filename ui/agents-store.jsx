// agents-store.jsx — React context cache for the agent library.

const AgentsContext = React.createContext({ agents: [], byId: () => null, refresh: () => {}, loaded: false });

function colorFromSlug(s = "") {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) & 0xffff;
  return `oklch(60% 0.15 ${h % 360})`;
}

function parseAgent(a) {
  const fullName = (`${a.name || ""}`).trim().toUpperCase();
  return {
    ...a,
    name: fullName || a.slug || "AGENT",
    source_type: a.source_type || "fiction",
    source_title: a.source_title || "",
    desc: typeof a.desc === "string" ? a.desc : "",
    tags: Array.isArray(a.tags) ? a.tags : [],
    color: colorFromSlug(a.slug || String(a.id)),
  };
}

function AgentsProvider({ children }) {
  const [agents, setAgents] = React.useState([]);
  const [loaded, setLoaded] = React.useState(false);

  const refresh = React.useCallback(async () => {
    try {
      const list = await window.api.get("/ui/agents");
      setAgents(list.map(parseAgent));
    } catch (e) {
      console.warn("Failed to load agents:", e.message);
    } finally {
      setLoaded(true);
    }
  }, []);

  React.useEffect(() => {
    refresh();
    // Retry once after 3s in case the server was still starting up
    const t = setTimeout(refresh, 3000);
    return () => clearTimeout(t);
  }, [refresh]);

  const byId = React.useCallback(
    (id) => agents.find(a => a.id === id || a.id === Number(id) || a.slug === id) || null,
    [agents]
  );

  return (
    <AgentsContext.Provider value={{ agents, byId, refresh, loaded }}>
      {children}
    </AgentsContext.Provider>
  );
}

window.useAgents = () => React.useContext(AgentsContext);
window.AgentsProvider = AgentsProvider;
