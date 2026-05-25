// screens-library.jsx — Agent Library

function AgentCard({ persona, selected, onAdd, onSelect, addLabel = "Add to session", compact = false }) {
  return (
    <div
      className={`card card-hov agent-card ${selected ? "selected" : ""}`}
      onClick={onSelect}
      data-screen-label={`agent-${persona.id}`}
    >
      <div className="agent-card-head">
        <Avatar persona={persona} size="lg" />
        <div className="agent-card-meta">
          <div className="agent-name">{persona.name}</div>
          <div className="agent-source">
            {persona.source_type === "fiction" ? "Fiction" : "Real-world"} · {persona.source_title}
          </div>
        </div>
        {selected && (
          <Icons.Check size={16} sw={2} style={{ color: "var(--accent)" }} />
        )}
      </div>

      <div className="agent-desc">{persona.desc}</div>

      <div className="agent-tags">
        {persona.tags.map(t => (
          <span key={t} className="tag-chip" style={{ pointerEvents: "none" }}>
            <span style={{ opacity: 0.6 }}>#</span>{t}
          </span>
        ))}
      </div>

      {!compact && (
        <div className="agent-actions">
          <Btn
            variant={selected ? "outline" : "primary"}
            size="sm"
            icon={selected ? <Icons.Check size={12} sw={2.5} /> : <Icons.Plus size={12} sw={2.5} />}
            onClick={(e) => { e.stopPropagation(); onAdd?.(); }}
          >
            {selected ? "In session" : addLabel}
          </Btn>
          <button
            className="btn btn-ghost btn-sm"
            onClick={(e) => { e.stopPropagation(); onSelect?.(); }}
          >
            <Icons.MessageDots size={12} /> Start DM
          </button>
          <div className="spacer" />
          <span className="t-meta mono" style={{ fontSize: 10 }}>{String(persona.id)}</span>
        </div>
      )}
    </div>
  );
}

function LibraryScreen({ session, onAddToSession, onStartDM, onOpenAgent }) {
  const { agents } = window.useAgents();
  const [q, setQ] = React.useState("");
  const [activeTag, setActiveTag] = React.useState(null);
  const [sourceFilter, setSourceFilter] = React.useState("all"); // all | fiction | real_world
  const [sort, setSort] = React.useState("name");

  let list = agents.filter(p => {
    if (q && !(p.name.toLowerCase().includes(q.toLowerCase()) || p.desc.toLowerCase().includes(q.toLowerCase()))) return false;
    if (activeTag && !p.tags.includes(activeTag)) return false;
    if (sourceFilter !== "all" && p.source_type !== sourceFilter) return false;
    return true;
  });
  if (sort === "name") list = [...list].sort((a, b) => a.name.localeCompare(b.name));
  if (sort === "source") list = [...list].sort((a, b) => a.source_type.localeCompare(b.source_type) || a.name.localeCompare(b.name));

  const topTags = ["politics", "philosophy", "science", "fiction", "economics", "technology", "humor", "sports"];

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }} data-screen-label="agent-library">
      <div className="lib-toolbar">
        <div className="lib-search">
          <span className="lib-search-icon"><Icons.Search size={14} /></span>
          <input
            className="input"
            placeholder="Search agents by name, descriptor…"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>
        <div className="lib-filters">
          <TagChip prefix="" active={!activeTag} onClick={() => setActiveTag(null)}>all</TagChip>
          {topTags.map(t => (
            <TagChip key={t} active={activeTag === t} onClick={() => setActiveTag(activeTag === t ? null : t)}>
              {t}
            </TagChip>
          ))}
        </div>
        <div className="spacer" />
        <div className="row" style={{ gap: 6 }}>
          <button
            className={`btn btn-sm ${sourceFilter === "all" ? "btn-outline" : "btn-ghost"}`}
            onClick={() => setSourceFilter("all")}
          >All</button>
          <button
            className={`btn btn-sm ${sourceFilter === "fiction" ? "btn-outline" : "btn-ghost"}`}
            onClick={() => setSourceFilter(sourceFilter === "fiction" ? "all" : "fiction")}
          >Fiction</button>
          <button
            className={`btn btn-sm ${sourceFilter === "real_world" ? "btn-outline" : "btn-ghost"}`}
            onClick={() => setSourceFilter(sourceFilter === "real_world" ? "all" : "real_world")}
          >Real-world</button>
          <button
            className={`btn btn-sm btn-ghost`}
            title="Sort"
            onClick={() => setSort(s => s === "name" ? "source" : "name")}
          >
            <Icons.Adjustments size={12} /> {sort === "name" ? "A→Z" : "By source"}
          </button>
        </div>
      </div>

      <div className="lib-body">
        <div className="lib-section-head">
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 4 }}>
              {list.length} {list.length === 1 ? "agent" : "agents"} · {agents.length} total in library
            </div>
            <h2 className="t-h2">Agent library</h2>
          </div>
          <div className="row">
            <span className="t-meta">In your session</span>
            <span className="badge badge-accent">{session.length} / 8</span>
          </div>
        </div>

        {list.length === 0 ? (
          <Empty
            title="No agents match"
            sub="Try clearing filters or searching for a different descriptor."
            icon={<Icons.Search size={20} />}
            action={<Btn variant="outline" size="sm" onClick={() => { setQ(""); setActiveTag(null); setSourceFilter("all"); }}>Clear filters</Btn>}
          />
        ) : (
          <div className="lib-grid">
            {list.map(p => (
              <AgentCard
                key={p.id}
                persona={p}
                selected={session.includes(p.id)}
                onAdd={() => onAddToSession(p.id)}
                onSelect={() => onOpenAgent(p)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

window.AgentCard = AgentCard;
window.LibraryScreen = LibraryScreen;
