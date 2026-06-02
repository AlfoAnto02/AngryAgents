// components.jsx — shared UI primitives for the 8 Angry Agents prototype.

const { useState, useEffect, useRef, useMemo, useCallback } = React;

// ---- Avatar ------------------------------------------------------------
function Avatar({ persona, size = "md", className = "", style = {} }) {
  const [imgFailed, setImgFailed] = useState(false);
  const initials = persona?.name
    ? persona.name.split(/\s+/).slice(0, 2).map(w => w[0]).join("")
    : "?";
  const slug = persona?.slug ? persona.slug.replace(/-+$/, "") : null;
  const showImg = slug && !imgFailed;
  return (
    <div
      className={`avatar avatar-${size} ${className}`}
      style={{ background: showImg ? "transparent" : (persona?.color || "#5E5E68"), overflow: "hidden", ...style }}
      title={persona?.name || ""}
    >
      {showImg ? (
        <img
          src={`${window.api.base}/icons/${slug}.webp`}
          alt={persona?.name || ""}
          onError={() => setImgFailed(true)}
          style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "inherit", display: "block" }}
        />
      ) : initials}
    </div>
  );
}

function AvatarStack({ personas, max = 4, size = "sm" }) {
  const shown = personas.slice(0, max);
  const rest = personas.length - shown.length;
  return (
    <div className="avatar-stack">
      {shown.map(p => <Avatar key={p.id} persona={p} size={size} />)}
      {rest > 0 && (
        <div
          className={`avatar avatar-${size}`}
          style={{ background: "var(--bg-3)", color: "var(--fg-1)" }}
        >
          +{rest}
        </div>
      )}
    </div>
  );
}

// ---- Tension meter -----------------------------------------------------
function tensionColor(v) {
  // green → amber → red gradient
  if (v < 0.25) return "var(--tens-1)";
  if (v < 0.45) return "var(--tens-2)";
  if (v < 0.65) return "var(--tens-3)";
  if (v < 0.82) return "var(--tens-4)";
  return "var(--tens-5)";
}
function tensionLabel(v) {
  if (v < 0.25) return "calm";
  if (v < 0.45) return "cool";
  if (v < 0.65) return "warm";
  if (v < 0.82) return "hot";
  return "molten";
}
function TensionMeter({ value, showLabel = true }) {
  const color = tensionColor(value);
  return (
    <div className="tension">
      <Icons.Flame size={12} sw={1.5} style={{ color }} />
      <div className="tension-bar">
        <div
          className="tension-bar-fill"
          style={{ width: `${Math.round(value * 100)}%`, background: color }}
        />
      </div>
      {showLabel && (
        <span className="tension-label" style={{ color }}>{tensionLabel(value)}</span>
      )}
    </div>
  );
}

// ---- Buttons -----------------------------------------------------------
function Btn({ children, variant = "outline", size = "", icon, block, onClick, type = "button", disabled, title }) {
  const cls = [
    "btn",
    `btn-${variant}`,
    size && `btn-${size}`,
    block && "btn-block",
  ].filter(Boolean).join(" ");
  return (
    <button type={type} className={cls} onClick={onClick} disabled={disabled} title={title}>
      {icon}
      {children}
    </button>
  );
}
function IconBtn({ icon, onClick, title, variant = "ghost", size = "" }) {
  const cls = ["btn", `btn-${variant}`, "btn-icon", size === "sm" && "btn-icon-sm"].filter(Boolean).join(" ");
  return (
    <button className={cls} onClick={onClick} title={title}>
      {icon}
    </button>
  );
}

// ---- Checkbox ----------------------------------------------------------
function Checkbox({ checked, onChange }) {
  return (
    <span
      className={`checkbox ${checked ? "checked" : ""}`}
      onClick={(e) => { e.stopPropagation(); onChange?.(!checked); }}
    >
      <Icons.Check size={11} sw={2.5} />
    </span>
  );
}

// ---- Tag chip ----------------------------------------------------------
function TagChip({ children, active, onClick, prefix = "#" }) {
  return (
    <button
      className={`tag-chip ${active ? "active" : ""}`}
      onClick={onClick}
      type="button"
    >
      <span style={{ opacity: 0.6 }}>{prefix}</span>{children}
    </button>
  );
}

// ---- Brand logo --------------------------------------------------------
function BrandMark({ size = 48 }) {
  return (
    <img src="logo.png?v=20260528-2" className="topnav-logo" style={{ width: size, height: size }} alt="Angry Agents" />
  );
}

// ---- Empty state -------------------------------------------------------
function Empty({ icon, title, sub, action }) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon || <Icons.Library size={20} />}</div>
      <div className="empty-title">{title}</div>
      {sub && <div style={{ fontSize: 12 }}>{sub}</div>}
      {action && <div style={{ marginTop: 12 }}>{action}</div>}
    </div>
  );
}

// ---- Sparkline (admin) -------------------------------------------------
function Sparkline({ data, color = "var(--admin)", height = 32 }) {
  const w = 120, h = height;
  if (!data?.length) return null;
  const min = Math.min(...data), max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((v, i) => [
    (i / (data.length - 1)) * w,
    h - 2 - ((v - min) / span) * (h - 4),
  ]);
  const path = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="kpi-spark">
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <path d={`${path} L ${w} ${h} L 0 ${h} Z`} fill={color} opacity="0.08" />
    </svg>
  );
}

// ---- Bar / Line / Pie chart placeholders (admin) -----------------------
function BarChartPlaceholder({ label }) {
  // procedurally generate a few bars to make the placeholder feel alive
  const bars = [0.32, 0.58, 0.41, 0.74, 0.52, 0.88, 0.61, 0.44, 0.71, 0.55, 0.93, 0.48];
  return (
    <div className="chart-placeholder" style={{ display: "flex", alignItems: "flex-end", padding: "16px 14px", gap: 6 }}>
      {bars.map((h, i) => (
        <div key={i} style={{ flex: 1, height: `${h * 100}%`, background: "var(--admin)", opacity: 0.18, borderRadius: 2, borderTop: "2px solid var(--admin)" }} />
      ))}
      <div style={chartLabelStyle}>{label}</div>
    </div>
  );
}
function LineChartPlaceholder({ label }) {
  const pts = [0.4, 0.32, 0.55, 0.48, 0.62, 0.59, 0.7, 0.66, 0.82, 0.74, 0.85, 0.92];
  const w = 600, h = 200;
  const stepX = w / (pts.length - 1);
  const d = pts.map((v, i) => `${i === 0 ? "M" : "L"}${i * stepX} ${(1 - v) * h}`).join(" ");
  return (
    <div className="chart-placeholder">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: "100%", height: "100%", display: "block" }}>
        {/* grid */}
        {[0.25, 0.5, 0.75].map(g => (
          <line key={g} x1="0" x2={w} y1={g * h} y2={g * h} stroke="var(--border-0)" strokeDasharray="3 4" />
        ))}
        <path d={`${d} L ${w} ${h} L 0 ${h} Z`} fill="var(--admin)" opacity="0.10" />
        <path d={d} fill="none" stroke="var(--admin)" strokeWidth="2" />
        {pts.map((v, i) => (
          <circle key={i} cx={i * stepX} cy={(1 - v) * h} r="3" fill="var(--bg-0)" stroke="var(--admin)" strokeWidth="2" />
        ))}
      </svg>
      <div style={chartLabelStyle}>{label}</div>
    </div>
  );
}
function PieChartPlaceholder({ label }) {
  const segs = [
    { v: 0.42, c: "var(--admin)" },
    { v: 0.27, c: "#a16207" },
    { v: 0.18, c: "var(--accent)" },
    { v: 0.13, c: "#5e5e68" },
  ];
  let acc = 0;
  const C = 60, R = 48;
  return (
    <div className="chart-placeholder" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 20 }}>
      <svg width="140" height="140" viewBox="0 0 120 120">
        {segs.map((s, i) => {
          const start = acc * 2 * Math.PI - Math.PI / 2;
          acc += s.v;
          const end = acc * 2 * Math.PI - Math.PI / 2;
          const large = s.v > 0.5 ? 1 : 0;
          const x1 = C + R * Math.cos(start), y1 = C + R * Math.sin(start);
          const x2 = C + R * Math.cos(end), y2 = C + R * Math.sin(end);
          return (
            <path key={i}
              d={`M ${C} ${C} L ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2} Z`}
              fill={s.c} opacity="0.7" stroke="var(--bg-2)" strokeWidth="1.5"
            />
          );
        })}
        <circle cx={C} cy={C} r="22" fill="var(--bg-2)" />
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-2)" }}>
        {["style", "ideology", "general", "behavioral"].map((k, i) => (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 8, height: 8, background: segs[i].c, borderRadius: 2, opacity: 0.7 }} />
            <span>{k}</span>
            <span style={{ marginLeft: "auto", color: "var(--fg-1)" }}>{Math.round(segs[i].v * 100)}%</span>
          </div>
        ))}
      </div>
      <div style={chartLabelStyle}>{label}</div>
    </div>
  );
}
const chartLabelStyle = {
  position: "absolute",
  bottom: 8,
  right: 12,
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  color: "var(--fg-3)",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
};

// ---- Theme toggle ------------------------------------------------------
function ThemeToggle() {
  const [light, setLight] = useState(() => document.documentElement.classList.contains("light"));
  const toggle = () => {
    const next = !document.documentElement.classList.contains("light");
    if (next) {
      document.documentElement.classList.add("light");
    } else {
      document.documentElement.classList.remove("light");
    }
    setLight(next);
    localStorage.setItem("aa.theme", next ? "light" : "dark");
  };
  return (
    <IconBtn
      icon={light ? <Icons.Moon size={16} /> : <Icons.Sun size={16} />}
      onClick={toggle}
      title={light ? "Passa al tema scuro" : "Passa al tema chiaro"}
    />
  );
}

// ---- Top nav -----------------------------------------------------------
// Role guard:
//   - Admins see the Dashboard nav, direct "New chat" entries, AND a
//     "Chats" link so they can open any chat and send messages as a
//     participant (judge mode). There is NO toggle to switch into the
//     user view — the admin role IS the super-user role.
//   - Regular users see Home / Agents / Chats / New.
function TopNav({ role, userRole, page, onNav, user, onLogout }) {
  const isAdmin = role === "admin";
  const [menuOpen, setMenuOpen] = useState(false);

  const handleNav = (target) => {
    setMenuOpen(false);
    onNav(target);
  };

  return (
    <>
      {menuOpen && <div className="mobile-overlay open" onClick={() => setMenuOpen(false)} />}
      <header className="topnav">
        <button
          className="topnav-brand"
          onClick={() => handleNav(isAdmin ? "admin" : "home")}
          style={{ background: "transparent", border: 0, color: "inherit", cursor: "pointer", padding: 0, font: "inherit" }}
          title="Home"
        >
          <BrandMark />
        </button>

        <button
          className="btn btn-ghost btn-icon topnav-hamburger"
          onClick={() => setMenuOpen(o => !o)}
          title={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <Icons.X size={20} /> : <Icons.Menu size={20} />}
        </button>

        <nav className={`topnav-nav${menuOpen ? " open" : ""}`}>
          {!isAdmin && (
            <>
              <button
                className={`topnav-nav-item ${page === "home" ? "active" : ""}`}
                onClick={() => handleNav("home")}
              >
                <Icons.Sparkles size={14} /> Home
              </button>
              <button
                className={`topnav-nav-item ${page === "library" ? "active" : ""}`}
                onClick={() => handleNav("library")}
              >
                <Icons.Library size={14} /> Agents
              </button>
              <button
                className={`topnav-nav-item ${["chat", "newdm", "newgroup"].includes(page) ? "active" : ""}`}
                onClick={() => handleNav("chat")}
              >
                <Icons.MessageDots size={14} /> Chats
              </button>
              <button
                className={`topnav-nav-item ${page === "newgroup" ? "active" : ""}`}
                onClick={() => handleNav("newgroup")}
                style={{ marginLeft: 8, color: "var(--accent)" }}
                title="Create a new group chat session"
              >
                <Icons.Users size={13} /> New group
              </button>
              <button
                className={`topnav-nav-item ${page === "newdm" ? "active" : ""}`}
                onClick={() => handleNav("newdm")}
                style={{ color: "var(--accent)" }}
                title="Create a new 1:1 chat with an agent"
              >
                <Icons.User size={13} /> New DM
              </button>
            </>
          )}
          {isAdmin && (
            <>
              <button
                className={`topnav-nav-item ${page === "admin" ? "active" : ""}`}
                onClick={() => handleNav("admin")}
              >
                <Icons.Shield size={14} /> Dashboard
              </button>
              <button
                className={`topnav-nav-item ${page === "library" ? "active" : ""}`}
                onClick={() => handleNav("library")}
              >
                <Icons.Library size={14} /> Agents
              </button>
              <button
                className={`topnav-nav-item ${page === "chat" ? "active" : ""}`}
                onClick={() => handleNav("chat")}
                title="Open any chat and send messages as a participant"
              >
                <Icons.MessageDots size={14} /> Chats
              </button>
              <button
                className={`topnav-nav-item ${page === "newgroup" ? "active" : ""}`}
                onClick={() => handleNav("newgroup")}
                style={{ marginLeft: 8, color: "var(--admin)" }}
                title="Create a new group chat session"
              >
                <Icons.Users size={13} /> New group
              </button>
              <button
                className={`topnav-nav-item ${page === "newdm" ? "active" : ""}`}
                onClick={() => handleNav("newdm")}
                style={{ color: "var(--admin)" }}
                title="Create a new 1:1 chat with an agent"
              >
                <Icons.User size={13} /> New DM
              </button>
            </>
          )}
        </nav>

        <div className="topnav-spacer" />

        <div style={{ display: "flex", alignItems: "center", gap: 10, paddingLeft: 6 }}>
          <span className={`topnav-role-badge badge ${isAdmin ? "badge-admin" : "badge-accent"} badge-dot`}>
            {isAdmin ? "Admin" : "User"}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Avatar
              persona={{ name: user.name, color: isAdmin ? "var(--admin)" : "var(--accent)" }}
              size="sm"
            />
            <div className="topnav-user-text">
              <span style={{ fontSize: 12, fontWeight: 500 }}>{user.name}</span>
              <span style={{ fontSize: 10.5, color: "var(--fg-2)", fontFamily: "var(--font-mono)" }}>{user.handle}</span>
            </div>
          </div>
          <ThemeToggle />
          <IconBtn icon={<Icons.Logout size={14} />} onClick={onLogout} title="Sign out" />
        </div>
      </header>
    </>
  );
}

// ---- Modal -------------------------------------------------------------
function Modal({ open, onClose, title, children, footer, width }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" style={width ? { width } : null} onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div className="t-h3">{title}</div>
          <IconBtn icon={<Icons.X size={14} />} onClick={onClose} />
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

// ---- Form field -------------------------------------------------------
function Field({ label, hint, error, ok, children }) {
  return (
    <div className="field">
      {label && <label className="field-label">{label}</label>}
      {children}
      {error && <div className="field-error"><Icons.AlertCircle size={11} /> {error}</div>}
      {ok && <div className="field-ok"><Icons.Check size={11} /> {ok}</div>}
      {hint && !error && !ok && <div className="field-hint">{hint}</div>}
    </div>
  );
}

// ---- Password input ---------------------------------------------------
function PasswordInput({ value, onChange, placeholder, name }) {
  const [shown, setShown] = useState(false);
  return (
    <div className="input-wrap">
      <input
        className="input"
        type={shown ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        name={name}
        autoComplete="new-password"
      />
      <button type="button" className="input-icon-btn" onClick={() => setShown(s => !s)} tabIndex={-1}>
        {shown ? <Icons.EyeOff size={14} /> : <Icons.Eye size={14} />}
      </button>
    </div>
  );
}

// ---- AgentProfileModal -------------------------------------------------

// inline style constants — no CSS class dependencies for layout
const S = {
  divider:    { height: 1, background: "var(--border-0)", margin: "4px 0" },
  grid2:      { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 },
  block:      { display: "flex", flexDirection: "column", gap: 8 },
  blockTitle: {
    fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
    textTransform: "uppercase", color: "var(--fg-2)", marginBottom: 2,
  },
  row:        { display: "flex", alignItems: "flex-start", gap: 0, fontSize: 12.5, lineHeight: 1.5 },
  rowLabel:   {
    flexShrink: 0, width: 76, fontSize: 10, fontWeight: 600,
    textTransform: "uppercase", letterSpacing: "0.05em",
    color: "var(--fg-2)", paddingTop: 2,
  },
  rowArrow:   { color: "var(--accent)", fontSize: 10, paddingTop: 2, marginRight: 6, flexShrink: 0 },
  rowValue:   { color: "var(--fg-0)", flex: 1 },
  chips:      { display: "flex", flexWrap: "wrap", gap: 5 },
  chip:       {
    fontSize: 11, padding: "2px 9px", borderRadius: 999,
    background: "var(--bg-3)", color: "var(--fg-1)",
    border: "1px solid var(--border-1)", whiteSpace: "nowrap",
  },
  chipAccent: {
    fontSize: 11, padding: "2px 9px", borderRadius: 999,
    background: "var(--accent-soft)", color: "var(--accent-hover)",
    border: "1px solid var(--accent-border)", whiteSpace: "nowrap",
  },
  tell:       { fontSize: 12.5, color: "var(--fg-1)", lineHeight: 1.5 },
  quote:      {
    background: "var(--bg-2)", borderRadius: 8,
    borderLeft: "3px solid var(--accent-border)", padding: "12px 14px",
  },
  quoteText:  { fontSize: 13, color: "var(--fg-0)", fontStyle: "italic", lineHeight: 1.6 },
  quoteLabel: {
    fontSize: 10.5, color: "var(--fg-2)", marginTop: 6,
    textTransform: "uppercase", letterSpacing: "0.05em",
  },
  never:      {
    fontSize: 12, color: "var(--fg-2)", fontStyle: "italic",
    padding: "5px 0", borderBottom: "1px solid var(--border-0)",
  },
};

function PIChips({ items, accent }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={S.chips}>
      {items.map((t, i) => <span key={i} style={accent ? S.chipAccent : S.chip}>{t}</span>)}
    </div>
  );
}

function PIRow({ label, value }) {
  if (!value) return null;
  const text = Array.isArray(value) ? value.join(", ") : String(value);
  if (!text.trim()) return null;
  return (
    <div style={S.row}>
      <span style={S.rowLabel}>{label}</span>
      <span style={S.rowArrow}>→</span>
      <span style={S.rowValue}>{text}</span>
    </div>
  );
}

function PIBlock({ title, children }) {
  return (
    <div style={S.block}>
      <div style={S.blockTitle}>{title}</div>
      {children}
    </div>
  );
}

function AgentProfileModal({ persona, onClose, onStartDM, onAddToSession, inSession, showAddToSession = true, showStartDM = true, selectLabel }) {
  const [profile, setProfile] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!persona) return;
    setLoading(true);
    setProfile(null);
    window.api.get(`/ui/agents/${persona.id}`)
      .then(data => { setProfile(data.profile || {}); })
      .catch(() => { setProfile({}); })
      .finally(() => setLoading(false));
  }, [persona?.id]);

  if (!persona) return null;

  const p = profile || {};
  const cs  = p.core_style || {};
  const hm  = p.humor || {};
  const sir = p.self_image_vs_reality || {};
  const sp  = p.social_positioning || {};
  const kd  = p.knowledge_domains || {};
  const et  = p.emotional_tells || {};
  const wv  = p.worldview && typeof p.worldview === "object" ? p.worldview : {};
  const vf  = p.vocabulary_fingerprint || {};
  const quotes   = Array.isArray(p.annotated_quotes) ? p.annotated_quotes : [];
  const doNotSay = Array.isArray(p.do_not_say) ? p.do_not_say : [];
  const expert   = (kd.expert || []).filter(Boolean);
  const blind    = (kd.blind_spots || kd.ignorant || []).filter(Boolean);
  const beliefs  = Object.keys(wv).filter(Boolean);
  const favored  = (vf.favored_words || []).filter(Boolean);
  const avoided  = (vf.avoided_words || []).filter(Boolean);
  const firstTell = Object.values(et).find(v => typeof v === "string" && v.trim()) || "";
  const featuredQuote = quotes[0] || null;

  return (
    <Modal
      open={true}
      onClose={onClose}
      width="660px"
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Avatar persona={persona} size="lg" />
          <div>
            <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.01em" }}>{persona.name}</div>
            <div style={{ fontSize: 11, color: "var(--fg-2)", marginTop: 3, letterSpacing: "0.06em" }}>
              {persona.source_type === "fiction" ? "FICTION" : "REAL-WORLD"}
              {persona.source_title ? ` · ${persona.source_title.toUpperCase()}` : ""}
            </div>
          </div>
        </div>
      }
      footer={
        <div style={{ display: "flex", gap: 8, width: "100%" }}>
          {showAddToSession && (
            <Btn variant="outline" size="sm" onClick={() => { onAddToSession?.(persona); onClose(); }}>
              {inSession ? "✓ In session" : "+ Add to session"}
            </Btn>
          )}
          <div style={{ flex: 1 }} />
          {showStartDM && (
            <Btn variant="primary" size="sm" onClick={() => { onClose(); onStartDM?.(persona); }}>
              {selectLabel || "Start DM"}
            </Btn>
          )}
        </div>
      }
    >
      {loading ? (
        <div style={{ padding: "32px 0", textAlign: "center", color: "var(--fg-2)", fontSize: 13 }}>Loading…</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* desc + tags */}
          {persona.desc && (
            <div style={{ fontSize: 13, color: "var(--fg-2)", fontStyle: "italic", lineHeight: 1.5 }}>
              "{persona.desc}"
            </div>
          )}
          {persona.tags?.length > 0 && <PIChips items={persona.tags} />}

          <div style={S.divider} />

          {/* VOICE + PERSONALITY */}
          <div style={S.grid2}>
            <PIBlock title="Voice">
              <PIRow label="register" value={cs.default_register} />
              <PIRow label="rhythm"   value={cs.rhythm} />
              <PIRow label="humor"    value={hm.style ? `${hm.style}${hm.frequency ? ` · ${hm.frequency}` : ""}` : null} />
              <PIRow label="shape"    value={cs.sentence_shape} />
            </PIBlock>
            <PIBlock title="Personality">
              <PIRow label="self-image" value={sir.self_image} />
              <PIRow label="reality"    value={sir.reality} />
              <PIRow label="gap"        value={sir.gap_behavior} />
            </PIBlock>
          </div>

          {/* KNOWS + BLIND SPOTS */}
          {(expert.length > 0 || blind.length > 0) && (
            <div style={S.grid2}>
              {expert.length > 0 && (
                <PIBlock title="Knows">
                  <PIChips items={expert} accent />
                </PIBlock>
              )}
              {blind.length > 0 && (
                <PIBlock title="Blind spots">
                  <PIChips items={blind} />
                </PIBlock>
              )}
            </div>
          )}

          {/* BELIEFS */}
          {beliefs.length > 0 && (
            <PIBlock title="Beliefs">
              <PIChips items={beliefs} />
            </PIBlock>
          )}

          {/* SAYS OFTEN + NEVER SAYS */}
          {(favored.length > 0 || avoided.length > 0) && (
            <div style={S.grid2}>
              {favored.length > 0 && (
                <PIBlock title="Says often">
                  <PIChips items={favored} accent />
                </PIBlock>
              )}
              {avoided.length > 0 && (
                <PIBlock title="Never says">
                  <PIChips items={avoided} />
                </PIBlock>
              )}
            </div>
          )}

          {/* UNDER PRESSURE + WANTS TO BE SEEN AS */}
          {(firstTell || sp.desired_position) && (
            <div style={S.grid2}>
              {firstTell && (
                <PIBlock title="Under pressure">
                  <div style={S.tell}>{firstTell}</div>
                </PIBlock>
              )}
              {sp.desired_position && (
                <PIBlock title="Wants to be seen as">
                  <div style={S.tell}>{sp.desired_position}</div>
                </PIBlock>
              )}
            </div>
          )}

          {/* FEATURED QUOTE */}
          {featuredQuote && (
            <>
              <div style={S.divider} />
              <div style={S.quote}>
                <div style={S.quoteText}>"{featuredQuote.quote}"</div>
                {featuredQuote.illustrates && (
                  <div style={S.quoteLabel}>{featuredQuote.illustrates}</div>
                )}
              </div>
            </>
          )}

          {/* WOULD NEVER SAY */}
          {doNotSay.length > 0 && (
            <>
              <div style={S.divider} />
              <PIBlock title="Would never say">
                {doNotSay.slice(0, 2).map((d, i) => (
                  <div key={i} style={{ ...S.never, ...(i === doNotSay.slice(0,2).length - 1 ? { borderBottom: "none" } : {}) }}>
                    "{d.line}"
                    {d.contradicts && <span style={{ color: "var(--fg-2)", marginLeft: 8, fontSize: 11 }}>— {d.contradicts}</span>}
                  </div>
                ))}
              </PIBlock>
            </>
          )}

        </div>
      )}
    </Modal>
  );
}

Object.assign(window, {
  Avatar, AvatarStack, TensionMeter, tensionColor, tensionLabel,
  Btn, IconBtn, Checkbox, TagChip, BrandMark, Empty, Sparkline,
  BarChartPlaceholder, LineChartPlaceholder, PieChartPlaceholder,
  TopNav, Modal, Field, PasswordInput, AgentProfileModal,
});
