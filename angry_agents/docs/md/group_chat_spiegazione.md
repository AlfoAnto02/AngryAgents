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

La chat diretta utente ↔ agente (DM) è gestita da un modulo separato: `src/dm_chat/`, descritto
alla fine di questo documento.

---

## La radice: `PersonaAgent`

Tutto parte da `PersonaAgent`, definito in `src/agents/personas/persona_agent.py`. È un dataclass
Python che incapsula tutto ciò che un agente deve sapere su sé stesso prima di poter scrivere
un messaggio.

```python
@dataclass
class PersonaAgent:
    agent: Agent                       # riga del DB: id, name, surname, summary
    contexts: list[AgentContext]       # righe Agent_context: signature_phrases JSON
    model: str                         # es. "mistral" o "claude-sonnet-4-6"
```

Fin qui è solo un contenitore. Diventa un agente attivo quando si chiama `bind_to_chat()`.

### `bind_to_chat()` — preparazione una-tantum

```python
def bind_to_chat(self, _chat_id: int, topic: Topic,
                 template_name: str = "group_dm_persona_chat.j2") -> None:
```

Questo metodo fa tutto il lavoro costoso **una volta sola** prima che la chat inizi. Calcola e
mette in cache:

| Campo privato | Fonte | Significato |
|---|---|---|
| `_persona_name` | `agent.name + surname` | Nome completo usato in ogni prompt |
| `_profile_block` | `AgentContext.signature_phrases` (JSON) | Profilo testuale appiattito |
| `_topic_block` | `topic.description` → JSON → `title` | Titolo leggibile del topic |
| `_template_name` | parametro esplicito | Template Jinja2 da usare |
| `dominance_weight` | `social_positioning` nel profilo | Peso nello scheduler |
| `cooldown_turns` | `core_style.rhythm` nel profilo | Turni di pausa dopo aver parlato |
| `message_count` | formula multi-segnale | Frammenti per turno |
| `_sentence_shape` … `_escalation_pattern` | vari campi del profilo | Stile fine-grained |

#### Costruzione del profilo (`_build_profile_block`)

La funzione legge il primo `AgentContext` con `signature_phrases` non nullo. Se nessun contesto
è disponibile, ricade su `agent.summary`. Il dizionario JSON viene appiattito così:

- Valori scalari: `key: value`
- Dizionari annidati: `key.sub_key: value` (un'entrata per coppia)
- Liste: valori concatenati con virgola

Le chiavi `persona_name`, `source_type`, `source_title`, `annotated_quotes`, `do_not_say` sono
escluse: sono metadati del profilo, non tratti del personaggio.

#### `_extract_dominance_weight` — profili fiction corretti

I profili `fiction` memorizzano `social_positioning` come dizionario annidato con chiavi
`desired_position`, `actual_dynamic`, `contradiction`. La funzione ora appiattisce i valori prima
del confronto per parole chiave, evitando che tutti i personaggi fiction cadano nel valore di
default `0.5`.

```
"assertive" / "dominant" / "leader" / "outspoken" → 0.7
"reserved"  / "quiet"    / "passive" / "introverted" → 0.3
default → 0.5
```

#### `_calculate_message_count` — formula a punteggio

Quanti frammenti invia questo agente per turno? La risposta non è un valore fisso: è derivata da
più segnali del profilo, sommati in un punteggio:

| Segnale | Campo | Variazione |
|---|---|---|
| `rhythm` fast / staccato | `core_style` | +2 |
| `rhythm` slow / deliberate | `core_style` | −2 |
| `sentence_shape` corta (clipped, declarative…) | `core_style` | +1 |
| `sentence_shape` lunga (flowing, elaborate…) | `core_style` | −1 |
| `filler_patterns` rapido / interruzione | `vocabulary_fingerprint` | +1 |

Soglie: punteggio ≥ 3 → 3 messaggi, ≥ 1 → 2 messaggi, altrimenti → 1 messaggio.

#### `_extract_cooldown_turns`

```
rhythm fast / staccato / rapid / quick / associative → 3 turni
rhythm slow / deliberate / lecture / measured / methodical → 6 turni
default → 4 turni
```

Perché fare tutto questo una volta sola? Perché il parsing del JSON e la costruzione delle stringhe
non deve ripetersi ad ogni turno. I campi privati sono cache: il costo di preparazione viene pagato
una volta, poi ogni turno li legge in memoria.

---

### `respond()` e `respond_burst()` — i due percorsi di risposta

#### `respond()` — un messaggio singolo

```python
def respond(self, history: list[ChatMessage], turn_count: int = 0,
            author_labels: dict[str, str] | None = None,
            my_label: str = "You") -> str:
```

Chiama `_render()` per costruire system e user message, poi `llm_call()`. Restituisce la stringa
grezza. Usato quando `message_count == 1`.

#### `respond_burst()` — più frammenti, una sola chiamata LLM

```python
def respond_burst(self, history, turn_count=0,
                  author_labels=None, my_label="You") -> list[str]:
```

Chiama `_render()` e `llm_call()` **una volta sola**, esattamente come `respond()`. La differenza
è nel parsing dell'output: cerca il pattern `[N] testo` con regex e restituisce una lista di
frammenti. Se il modello non rispetta il formato, torna l'intero output come lista a un elemento.

Questo è il metodo chiamato dalla sessione quando `message_count > 1`. L'economia computazionale
è preservata: un agente che invia tre frammenti consuma comunque una sola chiamata LLM per turno.

#### `_render()` — prompt condiviso

Entrambi i metodi usano `_render()`:

```python
def _render(self, history, turn_count, author_labels, my_label) -> tuple[str, str]:
```

Serializza la storia: ogni messaggio diventa `[<etichetta>]: <testo>`, dove `<etichetta>` è
ricavata da `author_labels` (il dizionario token → "Agent1" / "Agent2" ecc.) se il token è
presente, altrimenti dal token grezzo. Imposta `reground = (turn_count % 20 == 0)`. Poi chiama
`render_prompt(self._template_name, ...)` con tutte le variabili di stile estratte al bind.

---

## I template Jinja2 — due file distinti

Il sistema ora usa **due** template separati a seconda del tipo di chat.

### `group_dm_persona_chat.j2` — conversazione autonoma tra agenti

Usato per le chat di gruppo in cui gli agenti parlano tra loro senza utente. Caratteristiche
distinctive:

- **Etichette numeriche.** Il sistema prompt comunica `You are {{ agent_label }}` (es. "Agent3").
  Gli altri agenti sono "Agent1", "Agent2", ecc. Nessun agente conosce il nome vero degli altri.
- **Blocco di stile.** Se il profilo contiene `sentence_shape`, `filler_patterns`,
  `structural_patterns`, `humor` o `avoided_words`, il template aggiunge una sezione
  "How {{ persona_name }} writes" con istruzioni concrete.
- **Blocco obiettivi.** Se il profilo contiene `conversation_goals`, vengono listati. Se c'è un
  `escalation_pattern`, viene aggiunto come regola su come reagire alle provocazioni.
- **Regola di engagement obbligatorio.** L'agente **deve** rispondere all'argomento specifico
  dell'ultimo messaggio — non può ignorarlo e ripetere la propria posizione.
- **Formato burst condizionale.** Se `message_count >= 3`, il template impone il formato
  `[1] … [2] … [3] …` con frammenti di max 10 parole. Se `message_count == 2`, due frammenti
  connessi. Se `message_count == 1`, un messaggio completo di max 2 frasi.

### `dm_persona_chat.j2` — chat diretta con utente umano (DM)

Usato per le sessioni DM. Differenze rispetto al template di gruppo:

- Nessuna etichetta numerica: l'agente sa che parla con un utente umano.
- **Regola di lingua.** L'agente risponde sempre nella lingua dell'utente. Se l'utente scrive in
  italiano, l'agente risponde in italiano anche se il personaggio è anglofono.
- **Istruzioni esplicite dell'utente.** Se l'utente chiede N messaggi o un formato specifico,
  l'agente lo segue letteralmente, esprimendosi comunque con la voce del personaggio.
- Il formato burst è invertito rispetto al gruppo: `message_count >= 3` produce risposte _brevi_
  (il personaggio parla a raffiche), mentre `message_count == 1` produce una risposta completa.

### Perché il re-grounding?

Ogni 20 turni, `_render()` imposta `reground=True`, che attiva il blocco condizionale nel
template e inietta una riga di richiamo identitario nel messaggio utente. Nel template di gruppo,
il reminder è più ricco: invita esplicitamente a non echeggiare i propri turni precedenti e a
ingaggiare l'ultimo messaggio ricevuto. Nel template DM, è più essenziale. In entrambi i casi:
non è una chiamata LLM extra, è una riga in più nello stesso messaggio. Costo zero.

---

## `AgentFactory` — come si costruiscono gli agenti dal DB

`AgentFactory` (`src/agents/personas/factory.py`) ha tre metodi statici:

```python
AgentFactory.from_db(db, agent_id, model)
# → carica Agent + lista AgentContext dal DB, restituisce PersonaAgent (non ancora bound)

AgentFactory.for_chat(db, chat_id, model)
# → trova il topic della chat, recupera tutti gli agenti ASSOCIATI AL TOPIC (non alla chat),
#    chiama from_db() + bind_to_chat() su ciascuno. Usato dalla pipeline di valutazione.

AgentFactory.from_chat_participants(db, chat_id, model)
# → legge la tabella Chat_agent (agenti selezionati esplicitamente per quella chat),
#    chiama from_db() + bind_to_chat() su ciascuno. Usato dalla UI e da GroupChatFactory.
```

La distinzione tra `for_chat` e `from_chat_participants` è importante:
- `for_chat` usa la relazione topic → agenti: carica tutti gli agenti legati al topic, indipendentemente
  da quali siano stati scelti per quella specifica chat. È pensato per la pipeline di valutazione,
  dove si vuole valutare l'intera pool.
- `from_chat_participants` usa la tabella `Chat_agent`: carica solo gli agenti esplicitamente
  assegnati a quella chat dall'utente o dall'admin. È il percorso usato dalla UI a runtime.

---

## `TurnScheduler` — chi parla quando

```python
class TurnScheduler:
    def __init__(self, agents: list[PersonaAgent],
                 strategy: Literal["round_robin", "weighted_random"]): ...

    def _effective_weight(self, agent: PersonaAgent) -> float: ...
    def next(self) -> PersonaAgent: ...
    def mark_spoke(self, agent: PersonaAgent) -> None: ...
```

### `round_robin`

Cicla sugli agenti in ordine. Deterministico, equo, utile per test e sessioni brevi. Il cooldown
non è applicato in `round_robin`.

### `weighted_random`

Usa `random.choices()` con i **pesi effettivi** come probabilità. Il peso effettivo non è sempre
uguale al `dominance_weight` base: viene ridotto a **zero** se l'agente è ancora nel suo
`cooldown_turns` dopo aver parlato.

```python
def _effective_weight(self, agent: PersonaAgent) -> float:
    turns_since = self._turn_count - self._last_spoke.get(agent.agent.id, -999)
    if turns_since < agent.cooldown_turns:
        return 0.0           # agente in cooldown: non può essere selezionato
    return agent.dominance_weight
```

Un agente con `cooldown_turns=6` che ha parlato al turno 10 non può essere selezionato fino al
turno 16. Questo evita che lo stesso agente monopolizzi turni consecutivi anche se ha un
`dominance_weight` alto.

`mark_spoke(agent)` ora è **funzionale**: registra `_last_spoke[agent.id] = _turn_count`. Non è
più un no-op.

---

## `ContextWindow` — cosa vede ogni agente

```python
class ContextWindow:
    def trim(self, history: list[ChatMessage], agent: PersonaAgent) -> list[ChatMessage]:
        if self.strategy == "full":
            return history                    # niente trimming
        if len(history) <= self.max_messages:
            return history
        if self.strategy == "rolling":
            return history[-self.max_messages:]
        k = self.max_messages // 4
        n = self.max_messages - k
        return history[:k] + history[-n:]
```

Ora ci sono tre strategie:

### `full` (default per group chat e DM)

Passa tutta la storia al modello. Nessun taglio. Adatto quando la conversazione non è ancora
molto lunga o quando il modello ha una finestra di contesto ampia. È il default attuale sia
di `GroupChatFactory` che di `DMFactory`.

### `rolling`

Tiene solo gli ultimi `max_messages` messaggi. L'agente può perdere il framing originale del topic.

### `selective`

Divide `max_messages` in 25% iniziale + 75% finale. I messaggi di apertura (che tipicamente
contengono il framing del topic e le prime posizioni degli agenti) rimangono sempre visibili.

Esempio con 60 messaggi in storia e `max_messages=40`:

```
[msg 1] … [msg 10]   ← finestra iniziale (k=10): topic framing
[msg 11] … [msg 30]  ← rimossi
[msg 31] … [msg 60]  ← finestra finale (n=30): recency
```

---

## `GroupChatSession` — il motore

`GroupChatSession` (`src/group_chat/session.py`) è l'orchestratore centrale.

```python
@dataclass
class GroupChatSession:
    chat_id: int
    topic: Topic
    agents: list[PersonaAgent]
    scheduler: TurnScheduler
    context_window: ContextWindow
    author_secret: str

    _turn_count: int          # init=False
    _author_labels: dict[str, str]  # token HMAC → "AgentN"
```

### `__post_init__()` — costruzione della mappa di etichette

Alla creazione della sessione, `__post_init__` calcola il token HMAC per ogni agente e lo
mappa a un'etichetta numerica stabile ("Agent1", "Agent2", …). Questo dizionario viene passato
agli agenti a ogni turno, così ciascuno può vedere la storia con etichette leggibili e sa quale
etichetta corrisponde a sé stesso.

```python
for i, agent in enumerate(self.agents, 1):
    token = HMAC(secret, f"{name}:{surname}")
    self._author_labels[token] = f"Agent{i}"
```

### `run(db, n_turns, on_message=None)`

Chiama `run_turn()` esattamente `n_turns` volte. Il callback `on_message` viene invocato dopo
ogni messaggio — utile per streaming su WebSocket o per logging in tempo reale.

### `run_turn(db, stop_check=None)` — il ciclo elementare

```python
def run_turn(self, db, stop_check=None) -> ChatMessage | None:
    svc = ChatMessageService(db, self.author_secret)
    agent = self.scheduler.next()
    self._turn_count += 1

    history = svc.query(filters={"id_chat": self.chat_id})
    trimmed = self.context_window.trim(history, agent)

    my_token = HMAC(secret, f"{name}:{surname}")
    my_label = self._author_labels.get(my_token, "Agent?")

    if agent.message_count > 1:
        # Una chiamata LLM → lista di frammenti
        fragments = agent.respond_burst(trimmed, turn_count, author_labels, my_label)
        for i, fragment in enumerate(fragments):
            if stop_check and stop_check(): break
            if i > 0: time.sleep(random.uniform(2.0, 4.0))
            last_msg = self._write_message(svc, agent, fragment)
    else:
        content = agent.respond(trimmed, turn_count, author_labels, my_label)
        last_msg = self._write_message(svc, agent, content)

    self.scheduler.mark_spoke(agent)
    return last_msg
```

Passo per passo:

**1. `ChatMessageService`** — istanziato ogni turno per avere una connessione fresca al DB.

**2. `scheduler.next()`** — sceglie l'agente rispettando il cooldown.

**3. Lettura della storia** — dal DB, non dalla memoria. Se la sessione viene ripresa dopo
un'interruzione, la storia è sempre quella corretta.

**4. Trimming** — `ContextWindow.trim()` decide cosa tagliare.

**5. Calcolo etichetta** — il token HMAC dell'agente viene risolto nel suo "AgentN". Questo
viene passato come `my_label` all'agente, così nel template sa come riferirsi a sé stesso.

**6. Burst o singolo messaggio** — se `message_count > 1`, si usa `respond_burst()`: una
chiamata LLM, più frammenti. Tra un frammento e l'altro, la sessione aspetta 2–4 secondi per
simulare il typing umano. Se `message_count == 1`, si usa `respond()`.

**7. `stop_check`** — callback opzionale. Se ritorna `True`, il ciclo burst si interrompe.
Permette all'endpoint `/stop` di fermare la conversazione in modo pulito.

**8. `mark_spoke(agent)`** — registra il turno per il calcolo del cooldown.

Non c'è più aggiornamento del summary ogni 10 turni nella sessione: quella logica è stata rimossa.

---

## `GroupChatFactory` — l'unico punto di ingresso

```python
GroupChatFactory.build_session(
    db,
    chat_id=42,
    model="mistral",
    author_secret=get_settings().author_secret,
    scheduler_strategy="weighted_random",   # default
    window_strategy="full",                 # default
    max_messages=24,                        # default
)
```

La factory ora chiama `AgentFactory.from_chat_participants()` (non più `for_chat()`): carica
gli agenti dalla tabella `Chat_agent`, non dall'associazione topic → agenti.

I default sono cambiati rispetto alla versione precedente:
- `window_strategy`: da `"selective"` a `"full"`
- `max_messages`: da 40 a 24

---

## `DMSession` e `DMFactory` — il modulo separato per le chat dirette

Le chat DM (utente ↔ un solo agente) usano ora un modulo dedicato `src/dm_chat/`, separato
dal codice di group chat.

### `DMSession`

```python
@dataclass
class DMSession:
    chat_id: int
    topic: Topic
    agent: PersonaAgent
    context_window: ContextWindow
    author_secret: str

    def respond(self, db) -> ChatMessage:
        svc = ChatMessageService(db, self.author_secret)
        history = svc.query(filters={"id_chat": self.chat_id})
        trimmed = self.context_window.trim(history, self.agent)
        fragments = self.agent.respond_burst(trimmed)
        for i, fragment in enumerate(fragments):
            if i > 0: time.sleep(random.uniform(1.5, 3.0))
            last_msg = svc.create(id_chat=self.chat_id, ...)
        return last_msg
```

Nessun scheduler (c'è un solo agente). Usa `respond_burst()` anche per i DM: se l'agente ha
`message_count > 1`, produce più frammenti con ritardi da typing (1.5–3.0 s, più brevi del
gruppo per simulare la risposta rapida di una chat privata).

### `DMFactory`

```python
DMFactory.build_session(
    db, chat_id, model, author_secret,
    window_strategy="full",   # default
    max_messages=40,
)
```

Carica il singolo agente con `AgentFactory.from_db()`, chiama
`agent.bind_to_chat(..., template_name="dm_persona_chat.j2")` esplicitamente — garantendo che
il template DM (con la regola di lingua e le istruzioni utente) venga usato al posto di quello
di gruppo.

---

## L'anonimato degli autori — perché e come

Questo è uno dei vincoli più importanti del progetto. I giudici che valutano la chat devono
poter dire "questo messaggio sembra scritto da Personaggio X" senza sapere quale agente lo ha
effettivamente scritto.

La soluzione è che `Chat_messages.author` non è mai un nome né una FK alla tabella `Agents`.
È un HMAC-SHA256 calcolato da `ChatMessageService` nel momento in cui il messaggio viene
salvato:

```
author = HMAC-SHA256(ANGRY_AUTHOR_SECRET, "Mario:Rossi")
```

Il secret è una variabile d'ambiente. Il risultato è un digest esadecimale deterministico: lo
stesso agente produrrà sempre lo stesso token in tutte le chat, ma un giudice che vede il token
non può risalire al nome senza il secret.

`GroupChatSession` usa lo **stesso** calcolo HMAC per costruire la mappa `_author_labels`:
gli agenti si vedono reciprocamente come "Agent1", "Agent2" ecc. — non come nomi reali. In
questo modo l'anonimato è preservato anche nel contesto interno della conversazione: gli
agenti non sanno con chi stanno parlando, e nemmeno lo vedono nel prompt.

---

## Le difese contro il persona drift

Il problema del persona drift — un agente che perde gradualmente la propria voce nel corso di
una lunga chat — è affrontato a quattro livelli distinti:

**Livello 1 — Anchor nel prompt.** Il nome, il profilo e i tratti di stile compaiono nel blocco
`system` di ogni chiamata LLM. Il sistema prompt è ricostruito a ogni turno (anche se le
variabili sono in cache), quindi il modello riceve sempre il contesto identitario completo.

**Livello 2 — Stile esplicito nel prompt.** Le variabili fine-grained (`sentence_shape`,
`filler_patterns`, `structural_patterns`, `avoided_words`) sono estratte dal profilo e iniettate
in una sezione dedicata "How X writes" del sistema prompt. Non è un richiamo generico — sono
istruzioni concrete su vocabolario e struttura sintattica.

**Livello 3 — Finestra selettiva (opzionale).** Con `window_strategy="selective"`, `ContextWindow`
mantiene i primi messaggi della chat. Se un agente ha espresso una posizione forte al turno 2,
quella posizione è ancora visibile al turno 80.

**Livello 4 — Re-grounding esplicito.** Ogni 20 turni, `_render()` aggiunge nel messaggio utente
una riga di richiamo identitario. Nel template di gruppo il reminder include anche "engage with
what was just said — do not echo your previous points". Non è una chiamata LLM extra: è una riga
condizionale nel template Jinja2. Costo zero.

---

## Il flusso completo di un turno — riepilogo visivo

Ecco cosa succede dall'inizio alla fine di un singolo turno di conversazione di gruppo:

```
GroupChatSession.run_turn(db)
        │
        ├─ TurnScheduler.next()
        │      └─ weighted_random con _effective_weight
        │         → "Vader" (cooldown scaduto, dominance=0.7)
        │
        ├─ ChatMessageService(db, secret)  ← istanziato qui
        │
        ├─ svc.query({"id_chat": 42})      ← legge N messaggi dal DB
        │
        ├─ ContextWindow.trim(history, agent)
        │      └─ "full" (default): passa tutto
        │
        ├─ calcola my_label = "Agent3"
        │
        ├─ agent.message_count = 3 → respond_burst(trimmed, turn_count=21, ...)
        │      ├─ _render() → serializza storia con etichette "Agent1/2/3..."
        │      │              reground = (21 % 20 == 1 → False; al turno 20 sarebbe True)
        │      │              template = "group_dm_persona_chat.j2"
        │      ├─ llm_call(system, user, "mistral")
        │      │      → "[1] La forza è debole in voi.\n[2] Sempre fu così.\n[3] Non cambierà."
        │      └─ regex split → ["La forza è debole in voi.", "Sempre fu così.", "Non cambierà."]
        │
        ├─ per ogni frammento:
        │      ├─ [sleep 2–4s se non è il primo]
        │      └─ svc.create(id_chat=42, message=frammento, agent_id=7)
        │             └─ HMAC("secret", "Darth:Vader") → author token
        │
        └─ scheduler.mark_spoke(agent)  ← _last_spoke[7] = 21
```

Tre frammenti → **una** chiamata LLM. Tre scritture su DB (una per frammento). Zero chiamate
LLM extra per il re-grounding.

---

## Nota sulla struttura dei package

I moduli sono organizzati in tre aree distinte:

- `src/agents/personas/` — tutto ciò che riguarda il singolo agente: il dataclass `PersonaAgent`,
  le funzioni di estrazione del profilo, l'`AgentFactory`, i template Jinja2.
- `src/group_chat/` — tutto ciò che riguarda la sessione di gruppo: lo scheduler, la finestra
  contestuale, la session, la factory.
- `src/dm_chat/` — la sessione DM e la sua factory.

La separazione riflette una distinzione concettuale precisa: un agente non sa di essere in un
gruppo. Sa solo come rispondere a una lista di messaggi. È la sessione che coordina più agenti,
gestisce i turni, e scrive sul DB.

La direzione delle dipendenze è sempre unidirezionale:
```
group_chat  →  agents/personas
dm_chat     →  agents/personas
group_chat  →  db/*
dm_chat     →  db/*
```

`PersonaAgent` non importa nulla da `group_chat` né da `dm_chat`.
