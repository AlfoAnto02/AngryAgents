// screens-auth.jsx — Register + Login

const { useState: useStateAuth } = React;

function AuthShell({ children }) {
  return (
    <div className="auth-shell">
      <div className="auth-bg-grid" />
      <div className="auth-content">
        <div className="auth-card">
          <div className="auth-brand">
            <img src="logo.png" className="auth-brand-logo" alt="Angry Agents" />
            <h1>8 Angry Agents</h1>
            <div className="auth-brand-tagline">Simulate · Argue · Understand</div>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

function validateEmail(e) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
}

function RegisterScreen({ onSubmit, onSwitch }) {
  const [form, setForm] = useStateAuth({ firstName: "", lastName: "", email: "", password: "" });
  const [touched, setTouched] = useStateAuth({});

  const errors = {
    firstName: !form.firstName.trim() && "Required",
    lastName: !form.lastName.trim() && "Required",
    email: form.email && !validateEmail(form.email) && "Doesn't look like an email",
    password: form.password && form.password.length < 8 && "Min 8 characters",
  };

  const oks = {
    email: form.email && validateEmail(form.email) && "Looks good",
    password: form.password && form.password.length >= 12 && "Strong",
  };

  const canSubmit = form.firstName && form.lastName && form.email && validateEmail(form.email) && form.password.length >= 8;

  const update = (k) => (v) => setForm(s => ({ ...s, [k]: v?.target ? v.target.value : v }));

  return (
    <div className="card" style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <div className="t-eyebrow" style={{ marginBottom: 4 }}>Step 01</div>
        <h2 className="t-h2">Create your account</h2>
        <p className="t-meta" style={{ marginTop: 4 }}>So your agents know who they're arguing with.</p>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); canSubmit && onSubmit(form); }} className="col" style={{ gap: 12 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Field label="First name" error={touched.firstName && errors.firstName}>
            <input
              className={`input ${touched.firstName && errors.firstName ? "input-error" : ""}`}
              value={form.firstName}
              onChange={update("firstName")}
              onBlur={() => setTouched(t => ({ ...t, firstName: true }))}
              placeholder="Ada"
            />
          </Field>
          <Field label="Last name" error={touched.lastName && errors.lastName}>
            <input
              className={`input ${touched.lastName && errors.lastName ? "input-error" : ""}`}
              value={form.lastName}
              onChange={update("lastName")}
              onBlur={() => setTouched(t => ({ ...t, lastName: true }))}
              placeholder="Lovelace"
            />
          </Field>
        </div>

        <Field label="Email" error={touched.email && errors.email} ok={touched.email && oks.email}>
          <input
            className={`input ${touched.email && errors.email ? "input-error" : touched.email && oks.email ? "input-success" : ""}`}
            value={form.email}
            onChange={update("email")}
            onBlur={() => setTouched(t => ({ ...t, email: true }))}
            type="email"
            placeholder="ada@example.com"
          />
        </Field>

        <Field
          label="Password"
          error={touched.password && errors.password}
          ok={touched.password && oks.password}
          hint="At least 8 characters."
        >
          <PasswordInput
            value={form.password}
            onChange={(v) => { setForm(s => ({ ...s, password: v })); setTouched(t => ({ ...t, password: true })); }}
            placeholder="••••••••"
          />
        </Field>

        <Btn variant="primary" block type="submit" disabled={!canSubmit}>
          Create account
        </Btn>
      </form>

      <div style={{ textAlign: "center", marginTop: 14, fontSize: 12.5, color: "var(--fg-2)" }}>
        Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); onSwitch(); }}>Sign in</a>
      </div>
    </div>
  );
}

function LoginScreen({ onSubmit, onSwitch, prefill }) {
  const [form, setForm] = useStateAuth({ email: prefill?.email || "ada@example.com", password: "" });
  const [error, setError] = useStateAuth("");

  const submit = (e) => {
    e.preventDefault();
    if (!validateEmail(form.email)) { setError("Doesn't look like an email"); return; }
    if (!form.password) { setError("Password required"); return; }
    setError("");
    onSubmit(form);
  };

  return (
    <div className="card" style={{ padding: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <div className="t-eyebrow" style={{ marginBottom: 4 }}>Welcome back</div>
        <h2 className="t-h2">Sign in</h2>
      </div>

      <form onSubmit={submit} className="col" style={{ gap: 12 }}>
        <Field label="Email" error={error && !validateEmail(form.email) ? error : null}>
          <input
            className={`input ${error && !validateEmail(form.email) ? "input-error" : ""}`}
            value={form.email}
            onChange={(e) => setForm(s => ({ ...s, email: e.target.value }))}
            type="email"
            placeholder="you@example.com"
          />
        </Field>
        <Field
          label="Password"
          error={error && validateEmail(form.email) ? error : null}
        >
          <PasswordInput
            value={form.password}
            onChange={(v) => setForm(s => ({ ...s, password: v }))}
            placeholder="••••••••"
          />
        </Field>

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: -2 }}>
          <a href="#" style={{ fontSize: 12 }} onClick={(e) => e.preventDefault()}>Forgot password?</a>
        </div>

        <Btn variant="primary" block type="submit">Sign in</Btn>
      </form>

      <div style={{ textAlign: "center", marginTop: 14, fontSize: 12.5, color: "var(--fg-2)" }}>
        Don't have an account? <a href="#" onClick={(e) => { e.preventDefault(); onSwitch(); }}>Register</a>
      </div>
    </div>
  );
}

window.AuthShell = AuthShell;
window.RegisterScreen = RegisterScreen;
window.LoginScreen = LoginScreen;
