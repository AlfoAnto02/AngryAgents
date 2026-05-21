# Local Setup — 8 Angry Agents

How to get the full stack running on your machine.

---

## Prerequisites

- Python 3.12+
- An OpenAI API key (`gpt-4o-mini` by default)

---

## 1. Install dependencies

```bash
cd angry-agents
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. Configure environment

Create a `.env` file in the project root (copy the block below and fill in your key):

```env
OPENAI_API_KEY=sk-...
ANGRY_AUTHOR_SECRET=dev-author-secret-changeme
JWT_SECRET_KEY=dev-jwt-secret-changeme
ANGRY_DB_PATH=angry_agents.db
LLM_BACKEND=openai
OPENAI_MODEL=gpt-4o-mini
REFRESH_TOKEN_EXPIRE_MINUTES=10
```

> `ANGRY_AUTHOR_SECRET` and `JWT_SECRET_KEY` can be any random strings in dev.
> Change them to long random secrets before deploying anywhere.

---

## 3. Start the API server

Run from the project root:

```bash
uvicorn angry_agents.src.API.app:app --port 8000 --reload
```

The API is now at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

## 4. Seed the database

On first run the database is empty. Create the admin user and load all persona profiles:

```bash
# Create admin user (only needed once)
python -c "
import sqlite3, hashlib, os
from dotenv import load_dotenv
load_dotenv()
db = sqlite3.connect(os.getenv('ANGRY_DB_PATH', 'angry_agents.db'))        
db.execute('''INSERT OR IGNORE INTO User (Username, Name, Surname, Email, Password, Role, Slug)
              VALUES (?,?,?,?,?,?,?)''',
           ('admin', 'Admin', 'User', 'admin@example.com',
            'password123',               
            'admin', 'admin-user'))
db.commit(); db.close()
print('Admin created')
"

# Seed persona profiles (requires the API to be running on :8000)
python seed_personas.py
```

Default admin credentials: `admin@example.com` / `password123`

---

## 5. Start the UI server

In a **second terminal** (API must stay running):

```bash
python -m http.server 8001 -d ui/
```

Open `http://localhost:8001` in your browser.

---

## 6. Full restart checklist

When resuming development after the machine has been off:

1. Activate the virtualenv: `source .venv/bin/activate`
2. Start API: `uvicorn angry_agents.src.API.app:app --port 8000 --reload`
3. Start UI: `python -m http.server 8001 -d ui/`
4. Open `http://localhost:8001`

If a port is already in use:

```bash
lsof -ti:8000,8001 | xargs kill -9
```

---

## 7. Run tests

```bash
pytest                      # standard run
STRICT_MODE=1 pytest        # strict mode (deviations become hard raises)
```

---

## Common issues

| Symptom | Fix |
|---|---|
| Browser shows stale UI | Hard reload: **Cmd+Shift+R** (Mac) or **Ctrl+Shift+R** (Windows) |
| `Address already in use` on port 8000/8001 | `lsof -ti:8000,8001 \| xargs kill -9` |
| Agents missing after restart | Server must be running before the page loads; hard-reload after server is up |
| `ANGRY_AUTHOR_SECRET` not set | `.env` file missing or not in project root |
| Login fails immediately | DB was deleted — re-run the admin seed command in step 4 |
