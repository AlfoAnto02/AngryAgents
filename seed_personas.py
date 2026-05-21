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


def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        raise RuntimeError(f"GET {path} → {e.code}: {msg}") from e


def delete(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API + path, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()) if r.length else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        raise RuntimeError(f"DELETE {path} → {e.code}: {msg}") from e


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
    first = title.split(",")[0].strip()
    return first.replace("-", " ").replace("_", " ").strip()


def parse_name(persona_name: str):
    """Split persona_name into (name, surname). Single-word → surname=''."""
    parts = persona_name.strip().title().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return parts[0], ""


def delete_all_agents(token):
    """Fetch all agents and delete them one by one."""
    print("Fetching existing agents…")
    try:
        agents = get("/agents", token=token)
    except RuntimeError as e:
        print(f"  Could not fetch agents: {e}")
        return

    if not agents:
        print("  No existing agents found.")
        return

    print(f"  Deleting {len(agents)} existing agent(s)…")
    deleted = 0
    for agent in agents:
        agent_id = agent.get("id") or agent.get("slug")
        try:
            delete(f"/agents/{agent_id}", token=token)
            deleted += 1
        except RuntimeError as e:
            print(f"  ✗  Could not delete agent {agent_id}: {e}")

    print(f"  Deleted {deleted}/{len(agents)} agents.\n")


def main():
    print("Logging in as admin…")
    try:
        token = get_token()
    except RuntimeError as e:
        print(f"Login failed: {e}")
        print("Make sure the API is running (uvicorn angry_agents.src.API.app:app --port 8000)")
        sys.exit(1)

    delete_all_agents(token)

    files = sorted(glob.glob("data/personas/*.json"))
    files = [f for f in files if "old" not in f]

    created = 0
    failed = 0

    for path in files:
        with open(path) as fh:
            profile = json.load(fh)

        persona_name = profile.get("persona_name", os.path.basename(path).replace("_profile.json", ""))
        name, surname = parse_name(persona_name)
        source_type = normalize_source_type(profile.get("source_type", "fiction"))
        source_title = clean_title(profile.get("source_title", ""))

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
            print(f"  ✗  {name} {surname}  ERROR: {e}")
            failed += 1

    print(f"\nDone. {created} created, {failed} failed.")


if __name__ == "__main__":
    main()