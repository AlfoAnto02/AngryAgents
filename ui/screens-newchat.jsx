// screens-newchat.jsx — New DM + New Group wizard

// ─── Wizard stepper ──────────────────────────────────────────
function Stepper({ step }) {
  return (
    <div className="stepper">
      <span className={`stepper-num ${step >= 1 ? "active" : ""}`}>1</span>
      <span style={{ color: step >= 1 ? "var(--fg-0)" : "var(--fg-2)" }}>Select members</span>
      <span className="stepper-line" />
      <span className={`stepper-num ${step >= 2 ? "active" : step === 1 ? "" : ""}`}>2</span>
      <span style={{ color: step >= 2 ? "var(--fg-0)" : "var(--fg-2)" }}>Set topics</span>
    </div>
  );
}

// ─── New Group Chat ──────────────────────────────────────────
function NewGroupScreen({ initialSelection = [], onCancel, onLaunch }) {
  const { agents, byId } = window.useAgents();
  const [step, setStep] = React.useState(1);
  const [selected, setSelected] = React.useState(initialSelection);
  const [topics, setTopics] = React.useState([]);
  const [topicInput, setTopicInput] = React.useState("");
  const [tone, setTone] = React.useState("Debate");
  const [search, setSearch] = React.useState("");
  const [sourceFilter, setSourceFilter] = React.useState(null); // null | "real_world" | source_title string
  const [sourceSearch, setSourceSearch] = React.useState("");
  const [sourceOpen, setSourceOpen] = React.useState(false);

  // Unique fiction source_titles, sorted by how many agents belong to them (desc)
  const sourceTitles = React.useMemo(() => {
    const counts = {};
    agents.forEach(p => {
      if (p.source_type === "fiction" && p.source_title) {
        counts[p.source_title] = (counts[p.source_title] || 0) + 1;
      }
    });
    return Object.keys(counts).sort((a, b) => counts[b] - counts[a] || a.localeCompare(b));
  }, [agents]);

  // Filter which chips are visible when the user types in the source search box
  const visibleTitles = sourceSearch
    ? sourceTitles.filter(t => t.toLowerCase().includes(sourceSearch.toLowerCase()))
    : sourceTitles;

  const filtered = agents.filter(p => {
    if (search && !(
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.desc.toLowerCase().includes(search.toLowerCase()) ||
      (p.source_title || "").toLowerCase().includes(search.toLowerCase())
    )) return false;
    if (sourceFilter === "real_world" && p.source_type !== "real_world") return false;
    if (sourceFilter && sourceFilter !== "real_world" && p.source_title !== sourceFilter) return false;
    return true;
  });

  const toggle = (id) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id)
      : prev.length >= 8 ? prev
      : [...prev, id]
    );
  };

  const addTopic = () => {
    const t = topicInput.trim();
    if (!t) return;
    if (topics.includes(t)) return;
    setTopics([...topics, t]);
    setTopicInput("");
  };

  const removeTopic = (t) => setTopics(topics.filter(x => x !== t));

  const canNext = step === 1 ? selected.length >= 2 : topics.length >= 1;

  return (
    <div className="wizard-shell" data-screen-label="new-group-chat">
      <div className="wizard-main">
        <Stepper step={step} />
        {step === 1 && (
          <>
            <h2 className="t-h1" style={{ marginTop: 4 }}>Choose your agents</h2>
            <p className="t-meta" style={{ marginBottom: 18, maxWidth: 540 }}>
              Pick 2 to 8 agents. They'll converse autonomously about the topics you set in the next step.
            </p>
            <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 10 }}>
              <div className="lib-search" style={{ flex: "0 1 320px" }}>
                <span className="lib-search-icon"><Icons.Search size={14} /></span>
                <input
                  className="input"
                  placeholder="Search agents…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>
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
              {sourceFilter && (
                <IconBtn
                  icon={<Icons.X size={12} />}
                  title="Clear source filter"
                  onClick={() => { setSourceFilter(null); setSourceSearch(""); }}
                />
              )}
              <div className="spacer" />
              <div className="t-meta">
                Selected <span className="badge badge-accent" style={{ marginLeft: 4 }}>{selected.length}/8</span>
              </div>
            </div>

            {/* ── Source filter panel (collapsible) ── */}
            {sourceOpen && (
              <div className="card" style={{ padding: "12px 14px", marginBottom: 14, background: "var(--bg-2)" }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
                  <div className="lib-search" style={{ flex: "0 1 220px" }}>
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
                    <span className="t-meta" style={{ padding: "2px 4px" }}>Nessun source trovato</span>
                  )}
                </div>
              </div>
            )}

            <div className="lib-grid">
              {filtered.map(p => (
                <div
                  key={p.id}
                  className={`card card-hov agent-card ${selected.includes(p.id) ? "selected" : ""}`}
                  onClick={() => toggle(p.id)}
                >
                  <div className="agent-card-head">
                    <Checkbox checked={selected.includes(p.id)} onChange={() => toggle(p.id)} />
                    <Avatar persona={p} size="md" />
                    <div className="agent-card-meta">
                      <div className="agent-name">{p.name}</div>
                      <div className="agent-source">{p.source_title}</div>
                    </div>
                  </div>
                  <div className="agent-desc">{p.desc}</div>
                  <div className="agent-tags">
                    {p.tags.slice(0, 3).map(t => (
                      <span key={t} className="tag-chip" style={{ pointerEvents: "none" }}>
                        <span style={{ opacity: 0.6 }}>#</span>{t}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h2 className="t-h1" style={{ marginTop: 4 }}>What are they arguing about?</h2>
            <p className="t-meta" style={{ marginBottom: 24, maxWidth: 540 }}>
              Add one or more topics. The agents will weave between them — the more pointed, the better.
            </p>

            <div className="wizard-step2-grid" style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 32, alignItems: "start" }}>
              <div className="col" style={{ gap: 20 }}>
                <Field label="Topics" hint="Press Enter to add. 1–5 topics works best.">
                  <div className="row">
                    <input
                      className="input"
                      placeholder='e.g. "free will" or "climate policy"'
                      value={topicInput}
                      onChange={e => setTopicInput(e.target.value)}
                      onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addTopic(); } }}
                    />
                    <Btn variant="outline" onClick={addTopic} icon={<Icons.Plus size={13} />}>Add</Btn>
                  </div>
                  {topics.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                      {topics.map(t => (
                        <span key={t} className="tag-chip active" style={{ height: 26, padding: "0 4px 0 10px" }}>
                          {t}
                          <button
                            onClick={() => removeTopic(t)}
                            className="btn btn-icon btn-icon-sm btn-ghost"
                            style={{ height: 20, width: 20, marginLeft: 2 }}
                          >
                            <Icons.X size={11} />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </Field>

                <Field label="Conversation tone" hint="Sets the default register the agents adopt.">
                  <div className="role-switch" style={{ height: 38, padding: 4 }}>
                    {["Formal", "Casual", "Debate"].map(opt => (
                      <button
                        key={opt}
                        className={`role-switch-btn ${tone === opt ? "active" : ""}`}
                        style={{ height: 30, flex: 1, justifyContent: "center", fontSize: 12 }}
                        onClick={() => setTone(opt)}
                        type="button"
                      >
                        {opt === "Formal" && <Icons.Brain size={12} />}
                        {opt === "Casual" && <Icons.Mood size={12} />}
                        {opt === "Debate" && <Icons.Flame size={12} />}
                        {opt}
                      </button>
                    ))}
                  </div>
                </Field>

                <Field label="Optional ground rules" hint="A short brief the agents will treat as house rules.">
                  <textarea
                    className="input textarea"
                    rows={3}
                    placeholder="e.g. Stay on topic. No personal attacks. Cite evidence when possible."
                  />
                </Field>
              </div>

              <div className="card" style={{ padding: 16 }}>
                <div className="t-eyebrow">Session preview</div>
                <div style={{ marginTop: 10, fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 600 }}>
                  {topics[0] || "Untitled session"}{topics.length > 1 ? ` + ${topics.length - 1} more` : ""}
                </div>
                <div className="t-meta" style={{ marginTop: 4 }}>
                  {selected.length} agents · {tone.toLowerCase()} tone
                </div>
                <hr className="divider" style={{ margin: "12px 0" }} />
                <div className="col" style={{ gap: 8 }}>
                  {selected.slice(0, 6).map(id => {
                    const p = byId(id);
                    if (!p) return null;
                    return (
                      <div key={id} className="row" style={{ gap: 8 }}>
                        <Avatar persona={p} size="sm" />
                        <span className="mono" style={{ fontSize: 12, fontWeight: 500 }}>{p.name}</span>
                        <div className="spacer" />
                        <span className="badge" style={{ height: 18, fontSize: 9.5 }}>
                          {p.source_type === "fiction" ? "FIC" : "REAL"}
                        </span>
                      </div>
                    );
                  })}
                  {selected.length > 6 && (
                    <div className="t-meta">+ {selected.length - 6} more</div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      <aside className="wizard-aside">
        <div className="wizard-aside-head">
          <div className="t-eyebrow">Your session panel</div>
          <div style={{ marginTop: 6, fontSize: 13, fontWeight: 500 }}>
            {selected.length} of 8 agents
          </div>
        </div>
        <div className="wizard-aside-body">
          {selected.length === 0 ? (
            <Empty
              title="No agents yet"
              sub="Tick a card to add it"
              icon={<Icons.Users size={20} />}
            />
          ) : (
            <div className="col" style={{ gap: 6 }}>
              {selected.map(id => {
                const p = byId(id);
                if (!p) return null;
                return (
                  <div key={id} className="card" style={{ padding: 8, display: "flex", alignItems: "center", gap: 8 }}>
                    <Avatar persona={p} size="sm" />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="mono" style={{ fontSize: 11.5, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {p.name}
                      </div>
                      <div className="t-meta" style={{ fontSize: 10.5, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {p.source_title}
                      </div>
                    </div>
                    <IconBtn
                      size="sm"
                      icon={<Icons.X size={11} />}
                      onClick={() => toggle(id)}
                      title="Remove"
                    />
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <div className="wizard-aside-foot">
          {step === 1 ? (
            <div className="row" style={{ gap: 8 }}>
              <Btn variant="outline" onClick={onCancel}>Cancel</Btn>
              <div className="spacer" />
              <Btn
                variant="primary"
                disabled={!canNext}
                onClick={() => setStep(2)}
                icon={<Icons.ArrowRight size={13} />}
              >
                Next: topics
              </Btn>
            </div>
          ) : (
            <div className="row" style={{ gap: 8 }}>
              <Btn variant="outline" onClick={() => setStep(1)} icon={<Icons.ChevronLeft size={13} />}>Back</Btn>
              <div className="spacer" />
              <Btn
                variant="primary"
                disabled={!canNext}
                onClick={() => onLaunch({ participants: selected, topics, tone })}
                icon={<Icons.Sparkles size={13} />}
              >
                Launch group chat
              </Btn>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

// ─── New DM ──────────────────────────────────────────────────
function NewDMScreen({ onCancel, onLaunch }) {
  const { agents, byId } = window.useAgents();
  const [pickerOpen, setPickerOpen] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState(null);
  const [opener, setOpener] = React.useState("");
  const [q, setQ] = React.useState("");

  const persona = selectedId ? byId(selectedId) : null;
  const filtered = agents.filter(p =>
    !q || p.name.toLowerCase().includes(q.toLowerCase()) || p.desc.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: 32, overflow: "auto" }} data-screen-label="new-dm">
      <div style={{ maxWidth: 720, margin: "0 auto", width: "100%" }}>
        <div className="t-eyebrow">Direct message</div>
        <h2 className="t-h1" style={{ marginTop: 6 }}>Start a 1:1 conversation</h2>
        <p className="t-meta" style={{ marginBottom: 28, maxWidth: 540 }}>
          Pick one agent. DMs are private — no group dynamics, no judges interrupting. Just you and them.
        </p>

        <Field label="Selected agent">
          {persona ? (
            <div className="card" style={{ padding: 16, display: "flex", gap: 14, alignItems: "flex-start" }}>
              <Avatar persona={persona} size="xl" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="row">
                  <div className="mono" style={{ fontSize: 14, fontWeight: 600, letterSpacing: "0.02em" }}>
                    {persona.name}
                  </div>
                  <span className="badge">{persona.source_type === "fiction" ? "Fiction" : "Real-world"}</span>
                  <div className="spacer" />
                  <Btn variant="ghost" size="sm" onClick={() => { setPickerOpen(true); setSelectedId(null); }}>
                    Change
                  </Btn>
                </div>
                <div className="agent-source" style={{ marginTop: 4 }}>{persona.source_title}</div>
                <div style={{ marginTop: 10, fontSize: 13, color: "var(--fg-1)" }}>{persona.desc}</div>
                <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 14 }}>
                  <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
                    {persona.tags.map(t => (
                      <span key={t} className="tag-chip" style={{ pointerEvents: "none" }}>
                        <span style={{ opacity: 0.6 }}>#</span>{t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <Btn
              variant="outline"
              icon={<Icons.Search size={13} />}
              onClick={() => setPickerOpen(true)}
            >
              Choose an agent…
            </Btn>
          )}
        </Field>

        <div style={{ marginTop: 18 }}>
          <Field label="Conversation starter (optional)" hint="A first message you'd like to lead with.">
            <textarea
              className="input textarea"
              rows={3}
              value={opener}
              onChange={e => setOpener(e.target.value)}
              placeholder={'e.g. "Let’s talk about wealth tax." or just leave blank and improvise.'}
            />
          </Field>
        </div>

        <div style={{ marginTop: 28, display: "flex", gap: 8 }}>
          <Btn variant="outline" onClick={onCancel}>Cancel</Btn>
          <div className="spacer" />
          <Btn
            variant="primary"
            disabled={!persona}
            icon={<Icons.MessageDots size={13} />}
            onClick={() => onLaunch({ persona, opener })}
          >
            Start DM
          </Btn>
        </div>
      </div>

      <Modal
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        title="Choose an agent"
        width={620}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setPickerOpen(false)}>Cancel</Btn>
            <Btn
              variant="primary"
              disabled={!selectedId}
              onClick={() => setPickerOpen(false)}
            >Select</Btn>
          </>
        }
      >
        <div className="lib-search" style={{ marginBottom: 12 }}>
          <span className="lib-search-icon"><Icons.Search size={14} /></span>
          <input
            className="input"
            placeholder="Search agents…"
            value={q}
            onChange={e => setQ(e.target.value)}
            autoFocus
          />
        </div>
        <div className="col" style={{ gap: 6, maxHeight: 380, overflow: "auto" }}>
          {filtered.map(p => (
            <div
              key={p.id}
              className={`card card-hov ${selectedId === p.id ? "selected" : ""}`}
              style={{
                padding: 10,
                display: "flex",
                gap: 10,
                alignItems: "center",
                cursor: "pointer",
                borderColor: selectedId === p.id ? "var(--accent)" : undefined,
                background: selectedId === p.id ? "var(--accent-soft)" : undefined,
              }}
              onClick={() => setSelectedId(p.id)}
            >
              <Avatar persona={p} size="sm" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="mono" style={{ fontSize: 12.5, fontWeight: 600 }}>{p.name}</div>
                <div className="t-meta" style={{ fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.desc}</div>
              </div>
              <span className="badge" style={{ height: 18 }}>
                {p.source_type === "fiction" ? "Fiction" : "Real-world"}
              </span>
              {selectedId === p.id && <Icons.Check size={14} sw={2.2} style={{ color: "var(--accent)" }} />}
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
}

window.NewGroupScreen = NewGroupScreen;
window.NewDMScreen = NewDMScreen;
