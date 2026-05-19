# Contributors — Commit History Summary

Periodo: 2026-05-05 → 2026-05-18

---

## Alfonso Antognozzi

**Ruolo principale:** Database layer, REST API, testing

| Data | Commit | Cosa ha implementato |
|------|--------|----------------------|
| 05-05 | First version of DB structure | Schema iniziale del database |
| 05-13 | md file for models | Documentazione dei modelli DB |
| 05-13 | Models elements for the database | Dataclass e DDL per tutte le entità (`Topic`, `Agent`, `AgentContext`, `GroupChat`, `ChatMessage`, `Judge`, `JudgeEvaluation`) con soft-delete e trigger `updated_at` |
| 05-13 | Repositories implementation | CRUD SQLite per ogni entità + `rels.py` per relazioni agent-topic e judge-chat |
| 05-13 | Refactor + services layers | Service layer con business logic: HMAC author token, validazione ruolo judge, cap 20 valutazioni per chat |
| 05-15 | Adjusted repo imports on services | Fix import relativi tra repositories e services |
| 05-18 | Added FastAPI for APIs + session report | API REST completa con FastAPI: `config.py`, `deps.py` (DI via `Depends`), 7 route file, documentazione di sessione |
| 05-18 | Added Swagger | `schemas.py` con response model Pydantic, `response_model=` su tutti gli endpoint, tag metadata, `swagger_ui_parameters` |
| 05-18 | Added tools_management.md and fixed DB initialization | Manifest tool per agenti AI (`tools_managementv1.md`), hook `lifespan` per `init_db()` all'avvio del server |
| 05-18 | Add test suite + session report | Prima suite di test (repository + services) |
| 05-18 | Added test suite for all repo/service methods (170) | 170 test su tutti i repository e service, `conftest.py` con fixture in-memory SQLite |
| 05-18 | Modified hashing method for chat messages | Author field ora è SHA-256 puro (opaco), lookup nome/cognome dal DB tramite `agent_id` — rimosso nome in chiaro |

---

## Kevin Shimaj (`kevinShi-maj`)

**Ruolo principale:** Documentazione di progetto, scraping YouTube/podcast, simulazione chat, UI

| Data | Commit | Cosa ha implementato |
|------|--------|----------------------|
| 05-05 | Add initial README | README iniziale del progetto |
| 05-06 | Experimentation pipeline overview (più commit) | Documentazione dettagliata del pipeline: estrazione persona, simulazione chat, valutazione judge, deliberazione, framework statistico e metriche |
| 05-11 | First CLAUDE.md + improvements | `CLAUDE.md` con regole architetturali, convenzioni e istruzioni operative per agenti AI |
| 05-11 | First script for YouTube scraping | Script iniziale per scraping trascrizioni YouTube |
| 05-11 | First UI implementation | Prima implementazione dell'interfaccia utente |
| 05-11 | Added ideas for context management | Note su gestione del contesto dei persona agent |
| 05-13 | First implementation of persona extraction | Script di estrazione e profilazione delle persona |
| 05-15 | First example of persona extraction and profile | Esempio concreto di profilo estratto |
| 05-18 | Chat simulation with Ollama | Prima implementazione della simulazione di chat con Ollama |
| 05-18 | Chat simulation uses extracted personas | Integrazione dei persona estratti nella simulazione |
| 05-18 | Chat simulation hashes persona_id and persona_name | Anonimizzazione dell'identità del persona nella simulazione |

---

## Gabriele Fronzoni

**Ruolo principale:** Problem statement, scraping film/PDF, test di scraping, presentazione

| Data | Commit | Cosa ha implementato |
|------|--------|----------------------|
| 05-05 – 05-10 | Problem definition (più commit) | Stesura e iterazione del problem statement del progetto |
| 05-11 | Implemented initial scraping of fictional personas from movies | Prima implementazione dello scraping HTML di script cinematografici |
| 05-11 | Initialized YouTube scraping script | Inizializzazione script YouTube |
| 05-12 | Modified scraping algorithm + configured tests | Refactor dell'algoritmo di scraping, configurazione test |
| 05-12 | Modified movies script scraping logic | Miglioramento logica estrazione dialoghi da script film |
| 05-14 | Modified implementation for scraping movie personas | Uso di libreria PDF per estrazione da file PDF |
| 05-14 | Wrote first presentation slides draft | Prima bozza slide di presentazione |
| 05-15 | Scraped first movies personas | Esecuzione e salvataggio dei primi persona estratti da film |
| 05-15 | Insert .gitignore + solved merge conflict | `.gitignore` iniziale, risoluzione conflitti |
| 05-18 | Modified fictional scripts loading | Aggiornamento caricamento script fictionali |
| 05-18 | Added movie personas | Aggiunta nuovi persona da film |
| 05-18 | Modified gitignore | Aggiornamento `.gitignore` |

---

## Davide Cabitza (`DavideCabitza`)

**Ruolo principale:** SOTA, agenti base, implementazione judge

| Data | Commit | Cosa ha implementato |
|------|--------|----------------------|
| 05-06 | Create + Update SOTA.md | State of the art del progetto |
| 05-11 | File .gitignore upload | `.gitignore` iniziale |
| 05-13 | Basic Agents | Prima implementazione base degli agenti |
| 05-13 | Judge examples and first basic implementation | Esempi e prima implementazione dei judge |
| 05-18 | First basic evaluation test + agent config file | Test di valutazione base, file di configurazione agente |
| 05-18 | Base abstract judge with judge type extensions | Classe astratta `Judge` con estensioni per i 4 tipi (`style`, `ideology`, `general`, `behavioral`) |
| 05-18 | Judge merging | Merge del branch judge nel main |

---

## Marco Massa (`marcomassa-unitn`)

**Ruolo principale:** Struttura repository, documentazione DB

| Data | Commit | Cosa ha implementato |
|------|--------|----------------------|
| 05-11 | Refactor project folders | Riorganizzazione struttura cartelle del progetto |
| 05-11 | Created DB branch | Creazione del branch `DB_creation_v1` |
| 05-13 | Modified markdown DB | Aggiornamento documentazione schema DB |
| 05-14 | Modified DB presentation | Aggiornamento slide DB per presentazione |
| 05-18 | Added db_v2.md | Documentazione DB versione 2 |
| Data | Commit principale | Co-autore di | Contributo |
| 05-06 | `a8b2689`| Added the explanation about our statistical framework and metrics | Framework statistico e metriche di valutazione |
| 05-18 | `09b15d8` | Added FastAPI for APIs + session report | API REST con FastAPI |
| 05-18 | `cc3897e` | Added Swagger | Integrazione Swagger UI |
| 05-18 | `872ebdf`  | Added tools_management.md and fixed DB initialization | Manifest tool agenti AI, hook `lifespan` per `init_db()` |
