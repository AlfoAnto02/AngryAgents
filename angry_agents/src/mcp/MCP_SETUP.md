# MCP Setup — Angry Agents

MCP (Model Context Protocol) espone le API di Angry Agents come tool chiamabili direttamente da un LLM (es. Claude Code). Nessuna query manuale, nessun Postman — l'AI legge e scrive sul DB parlando con il server.

---

## Prerequisiti

1. API server attivo su `:8000`
2. `.mcp.json` nella root del progetto (già presente)

---

## Avvio

```bash
# 1. Avvia l'API
uvicorn angry_agents.src.API.app:app --port 8000 --reload

# 2. Il server MCP parte automaticamente tramite .mcp.json
#    (Claude Code lo legge e connette il server al proprio contesto)
```

`.mcp.json` (già configurato):
```json
{
  "mcpServers": {
    "angry-agents": {
      "command": ".venv/bin/python",
      "args": ["-m", "angry_agents.src.mcp.mcp_server"],
      "cwd": "/path/to/angry-agents"
    }
  }
}
```

---

## Tool disponibili

### Tier 1 — Lettura libera

| Tool | Descrizione |
|---|---|
| `get_topics` | Lista tutti i topic |
| `get_topic_by_id(id)` | Singolo topic per ID |
| `get_agents(id_topic?)` | Lista agenti, opzionalmente filtrati per topic |
| `get_agent_by_id(id)` | Singolo agente per ID |
| `get_agent_by_slug(slug)` | Singolo agente per slug (es. `walter-white`) |
| `get_agent_contexts(id_agent?)` | Contesti/corpus degli agenti |
| `get_chats(id_topic?)` | Lista chat di gruppo |
| `get_chat_by_id(id)` | Singola chat per ID |
| `get_chat_messages(chat_id)` | Messaggi di una chat |

### Tier 2 — Scrittura con conferma obbligatoria

Ogni operazione di scrittura ha due fasi: **preview → confirm**.
Non chiamare mai `confirm_*` senza aver mostrato il preview all'utente.

| Preview | Confirm | Descrizione |
|---|---|---|
| `preview_create_topic` | `confirm_create_topic` | Crea un topic |
| `preview_create_chat` | `confirm_create_chat` | Apre una group chat |
| `preview_create_message` | `confirm_create_message` | Posta un messaggio |

---

## Esempio completo

**Obiettivo:** creare un topic, aprire una chat, mandare un messaggio.

```
1. preview_create_topic(title="Il libero arbitrio esiste?")
   → mostrare output all'utente → chiedere conferma

2. confirm_create_topic(title="Il libero arbitrio esiste?")
   → risposta: { id: 2, title: "...", ... }

3. preview_create_chat(id_topic=2)
   → mostrare output all'utente → chiedere conferma

4. confirm_create_chat(id_topic=2)
   → risposta: { id: 2, id_topic: 2, ... }

5. preview_create_message(chat_id=2, agent_id=4, message="Speak, friend.")
   → mostrare output all'utente → chiedere conferma

6. confirm_create_message(chat_id=2, agent_id=4, message="Speak, friend.")
   → risposta: { id: 1, author: "<hmac-token>", message: "...", ... }
```

`agent_id=4` è Gandalf. Usare `get_agents()` per vedere tutti gli ID.

---

## Aggiungere nuovi tool

1. Aggiungere la funzione in `tools/read.py` (Tier 1) o `tools/write.py` (Tier 2)
2. La funzione deve essere registrata dentro `register(mcp)` con `@mcp.tool()`
3. Nessun restart manuale — Claude Code ricarica i tool alla prossima sessione
