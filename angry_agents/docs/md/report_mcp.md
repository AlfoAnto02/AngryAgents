# Report MCP — Angry Agents

Sessione del **3 giugno 2026** — generazione di chat DM tramite Claude Code + MCP.

---

## 1. Cos'è MCP (Model Context Protocol)

MCP è uno standard aperto sviluppato da Anthropic per consentire a un LLM di interagire con sistemi esterni in modo strutturato e sicuro. Invece di chiamare API generiche via testo libero, l'LLM dispone di **tool definiti con schema JSON**: parametri tipizzati, descrizioni, validazione. Il server MCP espone questi tool; il client (Claude Code) li invoca come se fossero funzioni native.

In sintesi: MCP trasforma un'API REST in una "cassetta degli attrezzi" comprensibile direttamente al modello, senza prompt engineering fragile.

---

## 2. Come è implementato in Angry Agents

### Architettura

```
Claude Code (client MCP)
        │
        │  JSON-RPC / stdio
        ▼
mcp_server.py  (FastMCP)
        │
        │  httpx async
        ▼
FastAPI  :8000  (angry_agents/src/API/)
        │
        │  raw SQL
        ▼
SQLite  (angry_agents.db)
```

### File chiave

| File | Ruolo |
|------|-------|
| `angry_agents/src/mcp/mcp_server.py` | Entry point FastMCP — registra tutti i tool e avvia il server |
| `angry_agents/src/mcp/tools/read.py` | **Tier 1** — 14 tool di sola lettura, nessuna conferma richiesta |
| `angry_agents/src/mcp/tools/write.py` | **Tier 2** — 5 coppie `preview_*` / `confirm_*` per le scritture |
| `angry_agents/src/mcp/client.py` | Client httpx che fa da ponte tra MCP e FastAPI (`_get`, `_post`, `_patch`) |
| `.mcp.json` | Configurazione del server MCP per Claude Code (comando + cwd) |

### Pattern preview / confirm

Ogni operazione di scrittura è una **stretta di mano a due passi**:

1. `preview_*` — costruisce il payload, lo mostra all'utente, non ha side-effect
2. `confirm_*` — esegue la chiamata HTTP al backend solo dopo conferma esplicita

Questo garantisce che l'LLM non possa modificare dati accidentalmente o senza supervisione umana.

```
LLM  →  preview_create_full_chat(...)   →  mostra payload
User →  "yes"
LLM  →  confirm_create_full_chat(...)   →  POST /ui/chats/create-for-llm
```

### Tier 1 — Tool di lettura (14 tool)

`get_agents`, `get_agent_by_id`, `get_agent_by_slug`, `get_agent_contexts`,
`get_topics`, `get_topic_by_id`, `get_chats`, `get_chat_by_id`,
`get_chat_messages`, `get_admin_overview`, `get_admin_sessions`,
`get_admin_agent_performance`, `get_judged_chats`, `get_judge_result`, `get_judge_status`

### Tier 2 — Tool di scrittura (5 coppie)

| Azione | Preview | Confirm |
|--------|---------|---------|
| Crea chat DM / gruppo | `preview_create_full_chat` | `confirm_create_full_chat` |
| Invia messaggio | `preview_create_message` | `confirm_create_message` |
| Ferma chat | `preview_stop_chat` | `confirm_stop_chat` |
| Crea topic | `preview_create_topic` | `confirm_create_topic` |
| Avvia giudizio | `preview_start_judging` | `confirm_start_judging` |

---

## 3. Cosa è stato fatto in questa sessione

### Procedura eseguita

1. **Discovery** — chiamata `get_agents` per recuperare tutti i 100 agenti con i loro ID; chiamata `get_admin_sessions` per identificare l'utente admin (ID=1).
2. **Selezione** — scelte 6 personas diversificate (fiction + real-world, EN + IT).
3. **Creazione chat** — per ogni persona: `preview_create_full_chat` → `confirm_create_full_chat` → 10 messaggi alternati (utente + agente) → `confirm_stop_chat`.
4. **Messaggi utente** — postati con `confirm_create_message(created_by=1)` (admin).
5. **Messaggi agente** — postati con `confirm_create_message(agent_id=<id>)`, autore HMAC-anonimizzato dal backend.
6. **Stop processi** — `Get-Process python | Stop-Process -Force` su tutti i processi Python/uvicorn.

### Chat create

| Chat ID | Persona | ID Agente | Lingua | Topic | Messaggi |
|---------|---------|-----------|--------|-------|----------|
| 22 | Walter White | 89 | EN | Chimica, ambiguità morale, trasformazione | 10 |
| 23 | Tony Stark | 99 | EN | Intelligenza artificiale, tecnologia, responsabilità | 10 |
| 24 | Sherlock Holmes | 80 | EN | Logica, deduzione, natura umana | 10 |
| 25 | Yoda | 100 | EN | Saggezza, paura, la Forza, scelta | 10 |
| 26 | Valentino Rossi | 87 | IT | MotoGP, gare, rivalità, vita in pista | 10 |
| 27 | Giorgia Meloni | 30 | IT | Politica italiana, identità, Europa, valori | 10 |

**Totale: 60 messaggi su 6 chat DM, tutte in stato `stopped`.**

### Struttura di ogni conversazione

```
Chat DM (1 agente)
├── opener  (utente, created_by=1)          — primo messaggio nel create_full_chat
├── msg 2   (agente, agent_id=X)            — risposta in persona
├── msg 3   (utente, created_by=1)          — approfondimento
├── msg 4   (agente)
├── msg 5   (utente)
├── msg 6   (agente)
├── msg 7   (utente)
├── msg 8   (agente)
├── msg 9   (utente)
└── msg 10  (agente)                         — risposta finale
status → stopped
```

---

## 4. Come ha funzionato in pratica

### Sequenza di chiamate MCP (per ogni chat)

```
get_agents()                          # discovery ID agenti
get_admin_sessions()                  # discovery ID utente admin
preview_create_full_chat(...)         # mostra payload, nessun side-effect
confirm_create_full_chat(...)         # crea chat → chat_id
confirm_create_message(agent_id=X)   # risposta agente (×5)
confirm_create_message(created_by=1) # messaggio utente (×4)
preview_stop_chat(chat_id)
confirm_stop_chat(chat_id)
```

### Osservazioni tecniche

- **Autenticazione agenti**: i messaggi postati con `agent_id` ricevono un campo `author` con token HMAC-SHA256 (il backend anonimizza l'identità per i giudici).
- **Messaggi utente**: richiedono `created_by=<user_id>` — passare `null` causa un errore 422; l'admin ha ID=1.
- **Chat DM vs gruppo**: le chat DM (1 partecipante) non avviano il loop automatico di conversazione; i messaggi vanno postati manualmente tramite MCP.
- **Lingua**: bastato scrivere il primo messaggio in italiano perché l'agente rispondesse in italiano per tutta la conversazione, senza istruzioni esplicite.
- **Latenza**: ogni chiamata `confirm_create_message` risponde in ~200ms; l'intera sessione (60 messaggi + 6 chat lifecycle) ha richiesto circa 8 minuti.

### Errori riscontrati e risolti

**Errore 1 — `422 Unprocessable Content` sui messaggi utente**

Durante la prima chat, il tentativo di postare un messaggio utente con `created_by=None` ha restituito `422 Unprocessable Content`. Il backend richiede che almeno uno tra `agent_id` e `created_by` sia valorizzato. Risolto usando `created_by=1` (admin user).

**Errore 2 — Chat DM non visibili nella UI dopo il riavvio**

Dopo aver killato i processi e riavviato il server, le 6 chat DM non apparivano nella lista chat dell'utente admin.

*Causa*: `confirm_create_full_chat` era stato chiamato senza passare `created_by=1`, quindi il campo `Created_by` era `NULL` sia in `Group_chat` che in `Topic`. L'endpoint `GET /ui/chats` ([ui_routes.py:249](../src/API/routes/ui_routes.py)) filtra con `AND gc.Created_by = ?` usando l'ID dell'utente autenticato — le chat con `NULL` non venivano mai restituite.

Le chat erano però presenti nel DB e visibili nell'admin sessions dashboard (`GET /admin/sessions`), che non filtra per `Created_by`.

*Fix applicato*:
```sql
UPDATE Group_chat SET Created_by = 1 WHERE ID IN (22,23,24,25,26,27) AND Created_by IS NULL;
UPDATE Topic      SET Created_by = 1 WHERE ID IN (SELECT ID_topic FROM Group_chat WHERE ID IN (22,23,24,25,26,27)) AND Created_by IS NULL;
```

*Prevenzione*: passare sempre `created_by=<user_id>` a `confirm_create_full_chat` quando si creano chat tramite MCP.

---

## 5. Come riavviare

```bash
# Terminale 1 — API
uvicorn angry_agents.src.API.app:app --port 8000

# Terminale 2 — UI (opzionale)
python -m http.server 8001 -d ui/

# Le chat ID 22–27 sono nel database e pronte per la revisione/push
```

Per leggere le chat create:

```python
# Via MCP (in una nuova sessione Claude Code)
get_chat_messages(chat_id=22)   # Walter White
get_chat_messages(chat_id=23)   # Tony Stark
get_chat_messages(chat_id=24)   # Sherlock Holmes
get_chat_messages(chat_id=25)   # Yoda
get_chat_messages(chat_id=26)   # Valentino Rossi
get_chat_messages(chat_id=27)   # Giorgia Meloni
```
