# Come funziona il Group Chat — Spiegazione del sistema

## Il problema da risolvere

Immaginate di voler mettere in piedi una conversazione di gruppo in cui partecipano otto personaggi
artificiali, ciascuno con una propria voce, un proprio stile, le proprie opinioni politiche e i
propri tic linguistici. Ogni personaggio è estratto da materiale reale — trascrizioni di podcast,
dialoghi cinematografici — e il suo profilo è salvato nel database sotto forma di attributi
strutturati (stile, ideologia, posizionamento sociale).

Il sistema deve garantire tre cose contemporaneamente:

1. **Fedeltà al personaggio.** Un agente che interpreta un personaggio assertivo non può diventare
   improvvisamente remissivo al turno 30. La coerenza deve reggere per decine di messaggi.
2. **Economia computazionale.** Non si chiama il modello linguistico ad ogni tick del ciclo: lo si
   chiama solo quando è il turno di quell'agente.
3. **Anonimato verso i giudici.** I giudici che valutano la chat non devono sapere quale agente ha
   scritto quale messaggio. Il campo `author` nei messaggi è un token HMAC, non un nome.

Il modulo `src/group_chat/` risolve questi tre problemi attraverso quattro classi che lavorano
insieme: `PersonaAgent`, `TurnScheduler`, `ContextWindow` e `GroupChatSession`, assemblate
dall'unico punto di ingresso pubblico: `GroupChatFactory`.

---

## La radice: `PersonaAgent`

Tutto parte da `PersonaAgent`, definito in `src/agents/personas/persona_agent.py`. È un dataclass
Python che incapsula tutto ciò che un agente deve sapere su sé stesso prima di poter scrivere
un messaggio.

```python
@dataclass
class PersonaAgent:
    agent: Agent           # riga del DB: id, name, surname, summary
    contexts: list[AgentContext]  # righe Agent_context: signature_phrases JSON
    model: str             # es. "mistral" o "claude-sonnet-4-6"
```

Fin qui è solo un contenitore. Diventa un agente attivo quando si chiama `bind_to_chat()`.

### `bind_to_chat()` — preparazione una-tantum

```python
def bind_to_chat(self, _chat_id: int, topic: Topic) -> None:
    self._persona_name = f"{self.agent.name} {self.agent.surname}"
    self._profile_block = _build_profile_block(self.contexts)
    self._topic_block = topic.title
    if topic.description:
        self._topic_block += f": {topic.description}"
    self.dominance_weight = _extract_dominance_weight(self.contexts)
```

Questo metodo fa tre cose critiche, tutte **una volta sola** prima che la chat inizi:

- Costruisce `_profile_block`: scorre tutti i `AgentContext` dell'agente, estrae i campi JSON da
  `signature_phrases` e li appiattisce in un blocco di testo. Se un agente ha tre righe di contesto
  (stile, ideologia, sociale), il profilo finale concatena tutto.
- Costruisce `_topic_block`: titolo e descrizione del topic, usato in ogni prompt.
- Calcola `dominance_weight`: legge il campo `social_positioning` nel profilo e assegna `0.7` per
  parole come `assertive`, `dominant`, `leader`; `0.3` per `reserved`, `quiet`, `passive`; `0.5`
  come default. Questo peso numerico guiderà lo scheduler.

Perché fare tutto questo una volta sola? Perché il parsing del JSON e la costruzione delle stringhe
non deve ripetersi ad ogni turno. I tre campi privati (`_persona_name`, `_profile_block`,
`_topic_block`) sono cache: il costo di preparazione viene pagato una volta, poi ogni turno li
legge in memoria.

### `respond()` — un turno, una chiamata LLM

Quando arriva il momento di parlare, si chiama:

```python
def respond(self, history: list[ChatMessage], turn_count: int = 0) -> str:
```

Questo metodo:

1. Serializza la `history` in un blocco di testo: ogni messaggio diventa `[<author_token>]: <testo>`.
2. Decide se aggiungere un promemoria di re-grounding: ogni 20 turni, `reground=True`.
3. Chiama `render_prompt("persona_chat.j2", ...)` per costruire system e user message.
4. Chiama `llm_call(system, user, self.model)` — una singola chiamata al modello linguistico.
5. Restituisce la stringa di risposta grezza.

Niente altro. Nessuna scrittura su DB, nessuna logica di stato. La risposta torna alla sessione,
che si occupa di tutto il resto.

---

## Il template Jinja2 — `persona_chat.j2`

Il prompt non è scritto nel codice Python: vive in un file Jinja2 separato
(`src/agents/personas/templates/persona_chat.j2`). Questo segue lo stesso schema dei giudici.

```jinja
{%- block system -%}
You are {{ persona_name }}.
You are participating in a group conversation with other people. You do not know who they are.

## Your profile
{{ profile_block }}

## Conversation topic
{{ topic_block }}

## Rules
- Write exactly one message, as {{ persona_name }} would naturally write it.
- Never mention that you are an AI, a language model, or that you are playing a role.
...
{%- endblock -%}

{%- block user -%}
--- CONVERSATION SO FAR ---
{{ history_block }}

--- YOUR TURN ---
{% if reground %}
[Stay true to who you are — {{ persona_name }}. Your voice and positions must remain consistent.]
{% endif %}
Respond as {{ persona_name }}.
{%- endblock -%}
```

Il template ha due blocchi: `system` e `user`. `render_prompt()` li estrae separatamente e li passa
come messaggi distinti all'API del modello. Le variabili che cambiano ad ogni turno sono solo due:
`history_block` (i messaggi precedenti) e `reground` (bool). Tutto il resto — il profilo, il nome,
il topic — è già in cache sull'agente.

### Perché il re-grounding?

I modelli linguistici tendono a "deriva di personaggio" (persona drift) nelle conversazioni lunghe:
il tono si appiattisce, le posizioni ideologiche si ammorbidiscono, il vocabolario diventa generico.
Ogni 20 turni, il metodo `respond()` imposta `reground=True`, che attiva il blocco condizionale nel
template e inietta una riga di richiamo identitario direttamente nel messaggio utente. Non è una
chiamata LLM extra — è una riga in più nello stesso messaggio. Costo zero, beneficio misurabile.

---

## `AgentFactory` — come si costruiscono gli agenti dal DB

`AgentFactory` (`src/agents/personas/factory.py`) è il livello che parla con il database e
restituisce oggetti `PersonaAgent` pronti all'uso.

Ha due metodi statici:

```python
AgentFactory.from_db(db, agent_id, model)
# → carica Agent + lista AgentContext dal DB, restituisce PersonaAgent

AgentFactory.for_chat(db, chat_id, model)
# → trova il topic della chat, recupera tutti gli agenti associati a quel topic,
#    chiama from_db() per ciascuno, chiama bind_to_chat() su ciascuno, restituisce la lista
```

Esempio concreto: se la chat con `id=42` è sul topic `"Politica italiana"` e ci sono sette agenti
legati a quel topic nel DB, `for_chat(db, 42, "mistral")` restituisce sette `PersonaAgent` già
legati al topic, con profili in cache e pesi di dominanza calcolati.

Il database viene interrogato qui, una volta sola. Dopo, durante la chat, nessun agente interroga
il DB per leggere il proprio profilo.

---

## `TurnScheduler` — chi parla quando

Il problema dello scheduling in un gruppo di otto agenti non è banale. Si vuole che i personaggi
più assertivi parlino più spesso, ma senza che quelli timidi spariscano del tutto.

```python
class TurnScheduler:
    def __init__(self, agents: list[PersonaAgent],
                 strategy: Literal["round_robin", "weighted_random"]): ...

    def next(self) -> PersonaAgent: ...
    def mark_spoke(self, agent: PersonaAgent) -> None: ...
```

### `round_robin`

Cicla sugli agenti in ordine. L'agente 0 parla al turno 1, l'agente 1 al turno 2, e così via,
ripartendo dall'inizio. Deterministico, equo, utile per test e sessioni brevi.

```
Turno 1: Agente A
Turno 2: Agente B
Turno 3: Agente C
Turno 4: Agente A  ← ricomincia
```

### `weighted_random`

Usa `random.choices()` con i pesi di dominanza come probabilità. Se Agente A ha `dominance_weight
= 0.7` e Agente B ha `dominance_weight = 0.3`, A ha circa il doppio delle probabilità di essere
scelto. Il comportamento è stocastico: A non parla necessariamente al turno 1, ma nel lungo periodo
parla circa il 70% delle volte (normalizzato sulla somma dei pesi).

Questo è il default della factory. Rende la conversazione più naturalistica: i personaggi
dominanti monopolizzano di più, quelli riservati intervengono sporadicamente.

`mark_spoke()` è presente come hook per estensioni future (ad esempio, implementare un cooldown
per impedire che lo stesso agente parli due volte di fila) — al momento è un no-op.

---

## `ContextWindow` — cosa vede ogni agente

Dopo 50 turni, la storia della chat è lunga. Passarla tutta al modello ad ogni turno è costoso e
spesso inutile. `ContextWindow` decide cosa tagliare.

```python
class ContextWindow:
    def trim(self, history: list[ChatMessage], agent: PersonaAgent) -> list[ChatMessage]:
        if len(history) <= self.max_messages:
            return history          # niente da tagliare
        if self.strategy == "rolling":
            return history[-self.max_messages:]   # solo gli ultimi N
        k = self.max_messages // 4
        n = self.max_messages - k
        return history[:k] + history[-n:]         # primi K + ultimi N
```

### `rolling`

Tiene solo gli ultimi `max_messages` messaggi. Semplice, ma l'agente può perdere il filo del topic
originale se la conversazione si è allontanata molto dall'apertura.

### `selective` (default)

Divide `max_messages` in due parti: il 25% iniziale e il 75% finale. Con `max_messages=40`, questo
significa i primi 10 messaggi + gli ultimi 30. I messaggi iniziali sono preziosi perché tipicamente
contengono la definizione del topic e le prime posizioni degli agenti — il "framing" della
conversazione. Tenerli in cima alla finestra impedisce che l'agente dimentichi di cosa si stava
parlando.

Esempio visivo con 60 messaggi in storia e `max_messages=40`:

```
[msg 1] [msg 2] ... [msg 10]   ← finestra iniziale (k=10): topic framing
[msg 11] ... [msg 30]          ← rimossi
[msg 31] ... [msg 60]          ← finestra finale (n=30): recency
```

L'agente vede 40 messaggi, non 60, ma non ha perso l'apertura della conversazione.

---

## `GroupChatSession` — il motore

`GroupChatSession` (`src/group_chat/session.py`) è l'orchestratore centrale. È un dataclass che
tiene insieme tutti i componenti e fornisce due metodi pubblici: `run()` e `run_turn()`.

```python
@dataclass
class GroupChatSession:
    chat_id: int
    topic: Topic
    agents: list[PersonaAgent]
    scheduler: TurnScheduler
    context_window: ContextWindow
    author_secret: str
    _turn_count: int = field(default=0, init=False, repr=False)
```

### `run(db, n_turns, on_message=None)`

Chiama `run_turn()` esattamente `n_turns` volte. Se si passa un callback `on_message`, questo viene
invocato dopo ogni messaggio — utile per streaming su WebSocket o per logging in tempo reale.
Restituisce la lista di tutti i messaggi prodotti.

### `run_turn(db)` — il ciclo elementare

Questo è il metodo che fa il lavoro vero, un turno alla volta:

```python
def run_turn(self, db) -> ChatMessage:
    svc = ChatMessageService(db, self.author_secret)   # 1. istanzia il servizio
    agent = self.scheduler.next()                       # 2. sceglie l'agente
    self._turn_count += 1

    history = svc.query(filters={"id_chat": self.chat_id})  # 3. legge la storia dal DB
    trimmed = self.context_window.trim(history, agent)       # 4. taglia la storia
    content = agent.respond(trimmed, turn_count=self._turn_count)  # 5. LLM call
    msg = self._write_message(svc, agent, content)           # 6. scrive su DB

    self.scheduler.mark_spoke(agent)

    if self._turn_count % 10 == 0:                           # 7. aggiorna summary
        current_summary = json.loads(agent.agent.summary or "{}")
        new_summary = agent.update_summary(self.chat_id, content, current_summary)
        AgentService(db).update(agent.agent.id, {"summary": json.dumps(new_summary)})

    return msg
```

Passo per passo:

**1. `ChatMessageService(db, author_secret)`** — viene istanziato ogni turno, non tenuto in
sessione. Questo è intenzionale: ogni turno ottiene una connessione fresca al DB.

**2. `scheduler.next()`** — sceglie l'agente che parlerà questo turno.

**3. Lettura della storia** — si legge dal DB, non da una struttura in memoria. Questo garantisce
che se la chat fosse ripresa dopo un'interruzione, la storia sarebbe sempre quella corretta.

**4. Trimming** — la finestra contestuale decide cosa passare all'agente.

**5. `agent.respond()`** — l'unica chiamata LLM del turno. Tutta la logica sopra era preparazione.

**6. `_write_message()`** — chiama `svc.create(id_chat, message, agent_id=...)`. Il servizio
prende `agent_id`, legge `name` e `surname` dall'Agents table, calcola
`HMAC-SHA256(secret, name:surname)` e lo usa come `author`. L'agente non costruisce mai il token
da solo — questo viene gestito interamente dentro `ChatMessageService`.

**7. Aggiornamento del summary** — ogni 10 turni (non ogni turno), lo stato riassuntivo
dell'agente per quella chat viene aggiornato e scritto nel DB. La struttura è un dizionario JSON
con chiave `chat_id` (stringa), così lo stesso agente può partecipare a più chat senza conflitti:

```json
{
  "42": { "turn_count": 10 },
  "87": { "turn_count": 4 }
}
```

---

## `GroupChatFactory` — l'unico punto di ingresso

Nessun chiamante esterno costruisce `GroupChatSession` direttamente. Tutto passa da:

```python
GroupChatFactory.build_session(
    db,
    chat_id=42,
    model="mistral",
    author_secret=get_settings().author_secret,
    scheduler_strategy="weighted_random",   # default
    window_strategy="selective",            # default
    max_messages=40,                        # default
)
```

La factory recupera dal DB il `GroupChat` e il `Topic`, delega ad `AgentFactory.for_chat()` la
costruzione degli agenti (già legati al topic), istanzia `TurnScheduler` e `ContextWindow` con le
strategie richieste, e restituisce una `GroupChatSession` pronta.

Questo pattern — una factory che raccoglie tutto il wiring in un punto solo — significa che il
codice che chiama la factory non deve conoscere nulla dei service layer, dei dataclass DB, o della
logica di scheduling. Chiede una sessione, la ottiene.

---

## L'anonimato degli autori — perché e come

Questo è uno dei vincoli più importanti del progetto. I giudici che valutano la chat devono poter
dire "questo messaggio sembra scritto da Personaggio X" senza sapere quale agente lo ha effettivamente
scritto.

La soluzione è che `Chat_messages.author` non è mai un nome né una FK alla tabella `Agents`.
È un HMAC-SHA256 calcolato da `ChatMessageService` nel momento in cui il messaggio viene salvato:

```
author = HMAC-SHA256(ANGRY_AUTHOR_SECRET, "Mario:Rossi")
```

Il secret è una variabile d'ambiente. Il risultato è un digest esadecimale deterministico: lo
stesso agente produrrà sempre lo stesso token in tutte le chat, ma un giudice che vede il token
non può risalire al nome senza il secret.

`PersonaAgent` non sa nulla di questo meccanismo. Restituisce solo il testo del messaggio.
`GroupChatSession._write_message()` passa `agent_id` al servizio, e il servizio fa il resto.
La responsabilità è dove deve essere: nel layer di persistenza, non nel layer degli agenti.

---

## Le tre difese contro il persona drift

Il problema del persona drift — un agente che perde gradualmente la propria voce nel corso di una
lunga chat — è affrontato a tre livelli distinti:

**Livello 1 — Anchor nel prompt.** Il nome dell'agente e il suo profilo compaiono nel blocco
`system` di ogni chiamata LLM. Il blocco system viene ricostruito a ogni turno (anche se le
variabili sono in cache), quindi il modello riceve sempre il contesto identitario completo.

**Livello 2 — Finestra selettiva.** `ContextWindow` con strategia `selective` mantiene i primi
messaggi della chat. Se un agente ha espresso una posizione forte al turno 2, quella posizione
è ancora visibile al turno 80. Gli agenti non dimenticano la loro posizione iniziale.

**Livello 3 — Re-grounding esplicito.** Ogni 20 turni, `respond()` aggiunge nel messaggio utente
una riga che richiama esplicitamente l'identità del personaggio. Non è un secondo sistema prompt,
non è una chiamata extra: è una riga condizionale nel template Jinja2. Costo zero.

Questi tre meccanismi sono cumulativi e indipendenti. Nessuno dei tre da solo è sufficiente; insieme
formano una difesa robusta.

---

## Il flusso completo di un turno — riepilogo visivo

Ecco cosa succede dall'inizio alla fine di un singolo turno di conversazione:

```
GroupChatSession.run_turn(db)
        │
        ├─ TurnScheduler.next()
        │      └─ weighted_random → sceglie PersonaAgent "Vader"
        │
        ├─ ChatMessageService(db, secret)  ← istanziato qui
        │
        ├─ svc.query({"id_chat": 42})      ← legge 35 messaggi dal DB
        │
        ├─ ContextWindow.trim(history, agent)
        │      └─ selective: primi 10 + ultimi 30 = 40 messaggi
        │
        ├─ agent.respond(trimmed, turn_count=21)
        │      ├─ serializza history → history_block (stringa)
        │      ├─ reground = True  (21 % 20 == 1 → no; turno 20 sarebbe stato True)
        │      ├─ render_prompt("persona_chat.j2", ...) → (system, user)
        │      └─ llm_call(system, user, "mistral") → "La forza è debole in voi."
        │
        ├─ svc.create(id_chat=42, message="La forza...", agent_id=7)
        │      └─ internamente: HMAC("secret", "Darth:Vader") → author token
        │         scrive su DB → restituisce ChatMessage
        │
        ├─ scheduler.mark_spoke(agent)  ← no-op per ora
        │
        └─ [turno 30, 40, ...] AgentService.update(7, {"summary": "..."})
```

Una chiamata LLM. Due operazioni DB (una lettura, una scrittura). La terza operazione DB per il
summary avviene ogni 10 turni.

---

## Nota sulla struttura dei package

I moduli sono organizzati in due aree distinte:

- `src/agents/personas/` — tutto ciò che riguarda il singolo agente: il dataclass `PersonaAgent`,
  la `AgentFactory`, i template Jinja2.
- `src/group_chat/` — tutto ciò che riguarda la sessione: lo scheduler, la finestra contestuale,
  la session, la factory.

Questa separazione riflette una distinzione concettuale precisa: un agente non sa di essere in un
gruppo. Sa solo come rispondere a una lista di messaggi. È la sessione che coordina più agenti,
gestisce i turni, e scrive sul DB. La direzione delle dipendenze va da `group_chat` verso `personas`,
mai nella direzione opposta — `PersonaAgent` non importa nulla da `group_chat`.
