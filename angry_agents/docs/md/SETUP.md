# Setup — 8 Angry Agents

How to get the full stack running on your machine, from a fresh clone to a working app with the shared demo database.

---

## Prerequisites

- Python 3.12+
- An OpenAI API key (`gpt-4o-mini` by default)
- `sqlite3` CLI (optional — only needed for `restore_db.sh`)

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

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
ANGRY_AUTHOR_SECRET=dev-author-secret-changeme
JWT_SECRET_KEY=dev-jwt-secret-changeme
ANGRY_DB_PATH=angry_agents.db
LLM_BACKEND=openai
OPENAI_MODEL=gpt-4o-mini
REFRESH_TOKEN_EXPIRE_MINUTES=10
```

> **`ANGRY_AUTHOR_SECRET` must be identical across the whole team.** Chat messages are signed with this secret — if it differs, the judging pipeline will fail to match messages to agents (see [Troubleshooting](#troubleshooting)).

---

## 3. Start the API

```bash
uvicorn angry_agents.src.API.app:app --port 8000 --reload
```

The API is now at `http://localhost:8000` · docs at `http://localhost:8000/docs`.  
On first start it creates `angry_agents.db` and auto-seeds the 20 judge rows.

---

## 4. Database setup

Choose **one** of the two paths below.

### Option A — Restore the shared demo database (recommended)

The repo ships a `seed_database.sql` dump with demo chats and all personas pre-loaded.

Stop the API server, then:

```bash
python restore_db.py        # Windows / Mac / Linux
```

Your existing DB (if any) is backed up automatically before being replaced.  
Restart the API after the restore.

### Option B — Fresh empty database

If you prefer to start from scratch:

```bash
# 1. Create the admin user (API must be running)
python -c "
import sqlite3, os
from dotenv import load_dotenv
load_dotenv()
db = sqlite3.connect(os.getenv('ANGRY_DB_PATH', 'angry_agents.db'))
db.execute('''INSERT OR IGNORE INTO User (Username, Name, Surname, Email, Password, Role, Slug)
              VALUES (?,?,?,?,?,?,?)''',
           ('admin', 'Admin', 'User', 'admin@example.com', 'password123', 'admin', 'admin-user'))
db.commit(); db.close()
print('Admin created')
"

# 2. Seed all 101 persona profiles (API must be running)
python seed_personas.py
```

Default admin credentials: `admin@example.com` / `password123`

---

## 5. Build the RAG index

Required for the judging pipeline. Run once; re-run only if personas change.

```bash
python -m angry_agents.src.rag.build_index
```

Takes ~5–10 minutes. The index is stored in `data/chroma/` (git-ignored).

---

## 6. Start the UI

In a **second terminal** (keep the API running):

```bash
python -m http.server 8001 -d ui/
```

Open `http://localhost:8001`.

---

## Daily restart checklist

```bash
source .venv/bin/activate                                    # activate venv
uvicorn angry_agents.src.API.app:app --port 8000 --reload   # terminal 1
python -m http.server 8001 -d ui/                           # terminal 2
```

If a port is already in use (Mac/Linux):
```bash
lsof -ti:8000,8001 | xargs kill -9
```

---

## Sharing the database with the team

### Export and push

When you want to share your current DB state (new chats, evaluations, etc.):

```bash
python export_db.py              # writes seed_database.sql
git add seed_database.sql
git commit -m "update: demo database seed"
git push
```

Make sure all chats have **COMPLETE** status in the Session Log before exporting.

### Pull a teammate's update

```bash
git pull
# stop the API, then:
python restore_db.py
# restart the API
uvicorn angry_agents.src.API.app:app --port 8000 --reload
```

### What the dump contains

| Table | Contents |
|-------|----------|
| `User` | Admin user |
| `Agents` | All 101 persona profiles |
| `Judges` | 20 evaluation judges (4 roles × 5 instances) |
| `Topic` | Chat topics |
| `Group_chat` | Chat sessions |
| `Chat_agent` | Agent–chat links |
| `Chat_messages` | All generated messages |
| `Judge_evaluation` | Evaluation results (if any chats were judged) |

**Not included:** `.env` secrets · `data/chroma/` RAG index · `data/eval/` per-chat reports.

> The RAG index does **not** need to be rebuilt after a restore — it is independent of the DB.

---

## Run tests

```bash
pytest                   # standard
STRICT_MODE=1 pytest     # strict — deviations become hard raises
ruff check .             # lint
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Browser shows stale UI | Hard reload: **Ctrl+Shift+R** (Windows) / **Cmd+Shift+R** (Mac) |
| `Address already in use` | `lsof -ti:8000,8001 \| xargs kill -9` |
| Agents missing after restart | API must be running before the page loads; hard-reload after |
| Login fails immediately | DB was deleted or not seeded — run step 4B |
| Judging fails: `ValueError: n must be an integer not less than 1` | Either (1) `ANGRY_AUTHOR_SECRET` differs from the one used when the DB was created — align all `.env` files; or (2) RAG index missing — run step 5 |
| Icons not updating after file rename | Hard reload (**Ctrl+Shift+R**) — browser cached the old 404 |
