// screens-library.jsx — Agent Library

function AgentCard({ persona, selected, onAdd, onSelect, addLabel = "Add to session", compact = false, showDM = true }) {
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
          {showDM && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={(e) => { e.stopPropagation(); onSelect?.(); }}
            >
              <Icons.MessageDots size={12} /> Start DM
            </button>
          )}
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
  const [sourceFilter, setSourceFilter] = React.useState(null); // null | "real_world" | source_title string
  const [sourceSearch, setSourceSearch] = React.useState("");
  const [sourceOpen, setSourceOpen] = React.useState(false);

  // Unique fiction source_titles sorted by count
  const sourceTitles = React.useMemo(() => {
    const counts = {};
    agents.forEach(p => {
      if (p.source_type === "fiction" && p.source_title) {
        counts[p.source_title] = (counts[p.source_title] || 0) + 1;
      }
    });
    return Object.keys(counts).sort((a, b) => counts[b] - counts[a] || a.localeCompare(b));
  }, [agents]);

  const visibleTitles = sourceSearch
    ? sourceTitles.filter(t => t.toLowerCase().includes(sourceSearch.toLowerCase()))
    : sourceTitles;

  const list = React.useMemo(() => {
    return agents
      .filter(p => {
        if (q && !(p.name.toLowerCase().includes(q.toLowerCase()) || p.desc.toLowerCase().includes(q.toLowerCase()))) return false;
        if (sourceFilter === "real_world" && p.source_type !== "real_world") return false;
        if (sourceFilter && sourceFilter !== "real_world" && p.source_title !== sourceFilter) return false;
        return true;
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [agents, q, sourceFilter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }} data-screen-label="agent-library">
      <div className="lib-toolbar" style={{ flexWrap: "wrap", gap: 8 }}>
        {/* Search */}
        <div className="lib-search" style={{ flex: "0 1 360px" }}>
          <span className="lib-search-icon"><Icons.Search size={14} /></span>
          <input
            className="input"
            placeholder="Search agents by name, descriptor…"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>

        {/* Source filter button */}
        <Btn
          variant={sourceFilter ? "outline" : "ghost"}
          size="sm"
          icon={<Icons.Filter size={13} />}
          onClick={() => setSourceOpen(o => !o)}
          style={sourceFilter ? { borderColor: "var(--accent)", color: "var(--accent)" } : {}}
        >
          Source{sourceFilter ? `: ${sourceFilter === "real_world" ? "Real World" : sourceFilter}` : ""}
          <Icons.ChevronDown size={11} style={{ marginLeft: 2, transform: sourceOpen ? "rotate(180deg)" : "none", transition: "transform .15s" }} />
        </Btn>

        {/* Clear filter */}
        {sourceFilter && (
          <IconBtn
            icon={<Icons.X size={12} />}
            title="Clear source filter"
            onClick={() => { setSourceFilter(null); setSourceSearch(""); }}
          />
        )}
      </div>

      {/* Source filter panel */}
      {sourceOpen && (
        <div style={{ padding: "10px 24px 14px", borderBottom: "1px solid var(--border-0)", background: "var(--bg-0)" }}>
          <div className="card" style={{ padding: "12px 14px", background: "var(--bg-2)" }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
              <div className="lib-search" style={{ flex: "0 1 240px" }}>
                <span className="lib-search-icon"><Icons.Search size={12} /></span>
                <input
                  className="input"
                  placeholder="Find a source…"
                  value={sourceSearch}
                  onChange={e => setSourceSearch(e.target.value)}
                  style={{ height: 30, fontSize: 13 }}
                  autoFocus
                />
              </div>
              {sourceSearch && (
                <IconBtn icon={<Icons.X size={11} />} onClick={() => setSourceSearch("")} title="Clear search" />
              )}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              <TagChip prefix="" active={!sourceFilter} onClick={() => { setSourceFilter(null); setSourceOpen(false); }}>
                All
              </TagChip>
              <TagChip
                prefix=""
                active={sourceFilter === "real_world"}
                onClick={() => { setSourceFilter(sourceFilter === "real_world" ? null : "real_world"); setSourceOpen(false); }}
              >
                Real World
              </TagChip>
              {visibleTitles.map(title => (
                <TagChip
                  key={title}
                  prefix=""
                  active={sourceFilter === title}
                  onClick={() => { setSourceFilter(sourceFilter === title ? null : title); setSourceOpen(false); }}
                >
                  {title}
                </TagChip>
              ))}
              {sourceSearch && visibleTitles.length === 0 && (
                <span className="t-meta" style={{ padding: "2px 4px" }}>No source found</span>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="lib-body">
        <div className="lib-section-head">
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 4 }}>
              {list.length} {list.length === 1 ? "agent" : "agents"} · {agents.length} total in library
            </div>
            <h2 className="t-h2">Agent library</h2>
          </div>
          {session.length > 0 && (
            <div className="row">
              <span className="t-meta">In your session</span>
              <span className="badge badge-accent">{session.length} / 8</span>
            </div>
          )}
        </div>

        {list.length === 0 ? (
          <Empty
            title="No agents match"
            sub="Try clearing filters or searching for a different descriptor."
            icon={<Icons.Search size={20} />}
            action={<Btn variant="outline" size="sm" onClick={() => { setQ(""); setSourceFilter(null); }}>Clear filters</Btn>}
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
