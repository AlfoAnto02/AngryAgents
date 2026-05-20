// api.js — single source of truth for talking to the FastAPI backend.
const API_BASE = window.__API_BASE__ || "http://localhost:8000";
let _token = localStorage.getItem("aa.token") || null;
let _refreshToken = localStorage.getItem("aa.refresh") || null;
let _refreshing = null; // in-flight refresh promise, deduplicate concurrent 401s

function headers() {
  return {
    "Content-Type": "application/json",
    ...(_token ? { "Authorization": `Bearer ${_token}` } : {}),
  };
}

async function _doRefresh() {
  if (!_refreshToken) throw new Error("no refresh token");
  const r = await fetch(API_BASE + "/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: _refreshToken }),
  });
  if (!r.ok) throw new Error("refresh failed");
  const data = await r.json();
  _token = data.access_token;
  localStorage.setItem("aa.token", _token);
  return _token;
}

async function req(method, path, body, _retry = true) {
  const r = await fetch(API_BASE + path, {
    method,
    headers: headers(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (r.status === 401 && _retry && _refreshToken) {
    try {
      if (!_refreshing) _refreshing = _doRefresh().finally(() => { _refreshing = null; });
      await _refreshing;
      return req(method, path, body, false);
    } catch {
      _token = null; _refreshToken = null;
      localStorage.removeItem("aa.token");
      localStorage.removeItem("aa.refresh");
      window.dispatchEvent(new Event("aa:session-expired"));
      throw new Error("Session expired");
    }
  }

  if (!r.ok) {
    const text = await r.text().catch(() => "");
    const err = new Error(`${method} ${path} → ${r.status} ${text}`);
    err.status = r.status;
    throw err;
  }
  if (r.status === 204) return null;
  return r.json();
}

window.api = {
  base: API_BASE,
  get token() { return _token; },
  setToken(token, refresh) {
    _token = token;
    localStorage.setItem("aa.token", token);
    if (refresh) {
      _refreshToken = refresh;
      localStorage.setItem("aa.refresh", refresh);
    }
  },
  clear() {
    _token = null; _refreshToken = null;
    localStorage.removeItem("aa.token");
    localStorage.removeItem("aa.refresh");
  },

  get:   (p)    => req("GET",    p),
  post:  (p, b) => req("POST",   p, b),
  patch: (p, b) => req("PATCH",  p, b),
  del:   (p)    => req("DELETE", p),
};
