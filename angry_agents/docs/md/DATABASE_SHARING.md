# Database Setup & Sharing

How to restore the shared demo database and keep it in sync with your team.

---

## First-time setup (new machine)

### 1. Complete the standard local setup first

Follow [LOCAL_SETUP.md](LOCAL_SETUP.md) steps 1–3 to install dependencies, configure `.env`, and start the API server. The API must run at least once so the DB schema and judges are created automatically.

### 2. Restore the shared demo database

Stop the API server, then run:

```bash
python restore_db.py
```

This imports `seed_database.sql` into `angry_agents.db`. Your existing DB (if any) is automatically backed up before being replaced.

### 3. Restart the API and UI

```bash
uvicorn angry_agents.src.API.app:app --port 8000 --reload
python -m http.server 8001 -d ui/
```

Open `http://localhost:8001` — you should see all the demo chats and personas already loaded.

---

## Updating the shared database

When you want to share new chats or data with the team:

### 1. Make sure all chats have completed

In the admin Session Log, all chats should show status **COMPLETE** before exporting.

### 2. Export the current DB

```bash
python export_db.py
```

This writes the full DB to `seed_database.sql`.

### 3. Commit and push

```bash
git add seed_database.sql
git commit -m "update: demo database seed"
git push
```

---

## Pulling a teammate's database update

When a colleague pushes a new `seed_database.sql`:

```bash
git pull

# Stop the API server, then:
python restore_db.py

# Restart the API
uvicorn angry_agents.src.API.app:app --port 8000 --reload
```

> Your old DB is automatically backed up as `angry_agents_YYYYMMDD_HHMMSS.db.bak` before being replaced.

---

## What is included in the dump

`seed_database.sql` contains the full state of the SQLite database at export time:

| Table | Contents |
|-------|----------|
| `User` | Admin user |
| `Agents` | All 101 persona profiles |
| `Judges` | 20 evaluation judges (4 roles × 5 instances) |
| `Topic` | All topics created for the demo chats |
| `Group_chat` | All chat sessions |
| `Chat_agent` | Agent–chat participation links |
| `Chat_messages` | All messages generated in each chat |
| `Judge_evaluation` | Evaluation results (if any chats were judged) |

**Not included:** `.env` secrets, the ChromaDB/RAG index (`data/chroma/`), per-chat evaluation reports (`data/eval/`).

## Notes

- The `angry_agents.db` file is git-ignored — never commit it directly.
- Only `seed_database.sql` is tracked in git.
- The RAG index (`data/chroma/`) is not included in the dump — it is built once with `python -m angry_agents.src.rag.build_index` and does not need to be rebuilt when restoring the DB.
- Backup files (`*.db.bak`) are also git-ignored.
