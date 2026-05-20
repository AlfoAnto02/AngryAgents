"""
Seed all persona profiles from data/personas/ into the running API.
Usage: python seed_personas.py
"""
import glob
import json
import os
import sys
import urllib.request
import urllib.error

API = "http://localhost:8000"
EMAIL = "admin@example.com"
PASSWORD = "password123"


def post(path, body, token=None):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API + path, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        raise RuntimeError(f"POST {path} → {e.code}: {msg}") from e


def get_token():
    data = post("/auth/login", {"email": EMAIL, "password": PASSWORD})
    return data["access_token"]


def normalize_source_type(raw):
    if raw in ("real_world", "fiction"):
        return raw
    if raw == "podcast":
        return "real_world"
    return "fiction"


def clean_title(title):
    if not title:
        return ""
    # Keep only first source if comma/multiple
    first = title.split(",")[0].strip()
    return first.replace("-", " ").replace("_", " ").strip()


def parse_name(persona_name: str):
    """Split persona_name into (name, surname). Single-word → surname=''."""
    parts = persona_name.strip().title().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return parts[0], ""


def main():
    print("Logging in as admin…")
    try:
        token = get_token()
    except RuntimeError as e:
        print(f"Login failed: {e}")
        print("Make sure the API is running (uvicorn angry_agents.src.API.app:app --port 8000)")
        sys.exit(1)

    files = sorted(glob.glob("data/personas/*.json"))
    files = [f for f in files if "old" not in f]

    created = 0
    skipped = 0

    for path in files:
        with open(path) as fh:
            profile = json.load(fh)

        persona_name = profile.get("persona_name", os.path.basename(path).replace("_profile.json", ""))
        name, surname = parse_name(persona_name)
        source_type = normalize_source_type(profile.get("source_type", "fiction"))
        source_title = clean_title(profile.get("source_title", ""))

        # Embed everything — agents-store.jsx will read core_style, tags, etc.
        summary = json.dumps({**profile, "source_type": source_type, "source_title": source_title})

        try:
            agent = post(
                "/agents",
                {"name": name, "surname": surname, "summary": summary},
                token=token,
            )
            print(f"  ✓  {name} {surname}  (id={agent['id']}, slug={agent['slug']})")
            created += 1
        except RuntimeError as e:
            if "409" in str(e) or "already" in str(e).lower():
                print(f"  –  {name} {surname}  (already exists, skipped)")
                skipped += 1
            else:
                print(f"  ✗  {name} {surname}  ERROR: {e}")

    print(f"\nDone. {created} created, {skipped} skipped.")


if __name__ == "__main__":
    main()
