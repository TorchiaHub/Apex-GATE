# FILE 2 — Mappatura Architetturale e Concettuale: `apex_architecture_concept.md`

> **Ruolo**: ARCHITECT | **Layer DOE**: Directive  
> **Data analisi**: 2026-03-19 | **Sistemi analizzati**: SurfSense-main, NocoBase-main

---

## 1. DNA Architetturale — Sintesi Estratta

Entrambi i sistemi condividono un principio fondante: **separazione netta tra orchestrazione e
esecuzione**, implementata attraverso pattern distinti ma convergenti. SurfSense lo applica con
il pattern **Pipeline + Agent Tool Registry**; NocoBase lo applica con il pattern **Plugin
Microkernel + Schema-Driven UI**. Questo è il DNA che Apex Absolute erediterà e fonderà.

---

## 2. SurfSense — Analisi Architetturale Profonda

### 2.1 Perché è costruito così: la Visione

SurfSense è un **RAG agent** (Retrieval-Augmented Generation) progettato per rispondere a query
usando basi di conoscenza private. La sua architettura risponde a tre vincoli dominanti:

1. **Latenza percepita**: il processo di indicizzazione è lento (embedding, chunking, summarization).
   → Soluzione: separazione sincrono/asincrono. Il frontend riceve risposta immediata, il lavoro
   pesante va su Celery in background.

2. **Variabilità delle sorgenti**: 20+ connettori eterogenei (Slack, PDF, GitHub, YouTube...).
   → Soluzione: `ConnectorDocument` come documento canonico unificato. Ogni connettore produce
   questo DTO, poi l'`IndexingPipelineService` lo elabora identicamente.

3. **Streaming dell'AI response**: l'utente deve vedere la risposta in tempo reale.
   → Soluzione: SSE (Server-Sent Events) con LangGraph streaming. Il frontend usa `assistant-ui`
   che si aspetta esattamente questo protocollo.

### 2.2 Design Pattern Identificati

#### Pattern 1: Pipeline ETL con Deduplica Hash-Based

```
ConnectorDocument (DTO)
    │
    ▼
compute_unique_identifier_hash()  ← SHA256 di source URL + connector_id + space_id
compute_content_hash()            ← SHA256 del contenuto
    │
    ├─ Uguale → skip (già indicizzato, nessun cambiamento)
    ├─ Content diverso → reindex (documento aggiornato)
    └─ Nuovo → ingest
    │
    ▼
document_chunker (Chonkie RecursiveChunker / CodeChunker)
    │
    ▼
document_embedder (sentence-transformers + pgvector)
    │
    ▼
document_summarizer (LLM summary → stored in Document.summary)
    │
    ▼
document_persistence (attach chunks to Document in PostgreSQL)
```

**Perché**: La deduplica hash-based garantisce idempotenza totale. Ogni run del connettore
può essere rieseguita senza duplicare i dati. Il content hash separa "stesso documento" da
"documento aggiornato". Questo pattern è **riutilizzabile verbatim** in Apex.

#### Pattern 2: Tool Registry + Factory (Agent Tools)

```python
# tools/registry.py
BUILTIN_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="search_knowledge_base",
        description="...",
        factory=create_search_knowledge_base_tool,
        enabled_by_default=True,
    ),
    ToolDefinition(
        name="generate_podcast",
        factory=create_generate_podcast_tool,
        enabled_by_default=False,
    ),
    ...
]

def build_tools(enabled_tools: list[str], context: ...) -> list[BaseTool]:
    return [tool.factory(context) for tool in BUILTIN_TOOLS if tool.name in enabled_tools]
```

**Perché**: Ogni tool è un oggetto autonomo con la propria factory. L'agent non conosce i
tool direttamente, li riceve come lista. Questo permette configurabilità per-utente:
ogni `NewLLMConfig` può attivare/disattivare tool. **Pattern estratto = Plugin Tool Registry**.

#### Pattern 3: Hybrid Search (Dense + Sparse)

```
Query utente
    │
    ├─ Vector Search (pgvector cos similarity) → top_k chunks
    └─ Full-text Search (PostgreSQL tsvector) → top_k chunks
    │
    ▼
Merge + Deduplication (by chunk_id)
    │
    ▼
FlashRank Cross-Encoder Reranking
    │
    ▼
top-N chunks finali per l'agent
```

**Perché**: Vector search eccelle su query semantiche; full-text su keyword esatte (codice,
nomi propri, acronimi). Il reranking cross-encoder corregge i falsi positivi di entrambi.
Questo stack a tre stadi è **best practice RAG state-of-the-art** (2024-2026).

#### Pattern 4: Stateful Agent con Checkpointing LangGraph

```
User Message
    │
    ▼
LangGraph Graph (create_surfsense_deep_agent)
    ├── Node: Agent (LLM reasoning + tool selection)
    ├── Node: ToolExecution (tool calls paralleli)
    └── Node: ResponseStreaming (SSE to frontend)
    │
    ▼
PostgreSQL Checkpointer (LangGraph checkpoint tables)
    └── thread_id → serialized state snapshot
```

**Perché**: LangGraph salva ogni step dell'agent in PostgreSQL. Questo permette:
- **Ripristino della sessione**: l'utente può ricaricare una chat e proseguire.
- **Interrupt + Resume**: l'agent può essere fermato (es. approvazione umana) e ripreso.
- **Multi-turn memory**: la storia della conversazione persiste tra sessioni.

#### Pattern 5: Electric SQL per Real-Time UI

```
PostgreSQL → Electric SQL Sync Engine → Browser SQLite (PGLite)
                                              │
                                              ▼
                                        React Hooks (useMessagesElectric)
                                              │
                                              ▼
                                        Automatic UI Re-render
```

**Perché**: Invece di polling o WebSocket custom, Electric SQL sincronizza un subset
di PostgreSQL direttamente nel browser come tabelle SQLite in-memory. I hook React
ascoltano queste tabelle con query live. Risultato: UI reattiva senza infrastruttura
WebSocket custom.

#### Pattern 6: Connector Abstraction Layer

Ogni connettore esterno segue questo contratto:
1. **Auth credentials**: schema Pydantic con i campi di autenticazione (token, OAuth, API key)
2. **Fetcher**: classe che implementa `async fetch() → list[ConnectorDocument]`
3. **Route**: API endpoint per configurare il connettore (save auth, trigger sync)
4. **Celery Task**: job periodico che invoca il fetcher e passa all'IndexingPipeline

**Perché**: Il connettore è completamente isolato. Aggiungere un nuovo connettore
significa aggiungere 4 file indipendenti senza toccare il core. **Open/Closed Principle**.

### 2.3 Struttura Database — Modello Concettuale

```
User (fastapi-users)
  ├── SearchSpace (1:N) — "workspace" isolato per utente/team
  │     ├── SearchSourceConnector (N:M) — connettori abilitati per questo space
  │     ├── Document (1:N)
  │     │     ├── Chunk (1:N) [embedding: Vector(1536), content: Text]
  │     │     └── DocumentStatus (JSONB) — state machine: pending/processing/ready/failed
  │     ├── NewChatThread (1:N) — conversazioni
  │     │     └── NewChatMessage (1:N) — messaggi con role (user/assistant/tool)
  │     ├── Report (1:N)
  │     ├── Podcast (1:N)
  │     └── Note (1:N)
  ├── Team (N:M via TeamMembership)
  │     ├── Role (1:N)
  │     └── Permission (N:M)
  └── NewLLMConfig (1:N) — configurazioni LLM per-utente
```

**Principio**: `SearchSpace` è l'**unità di isolamento**. Tutto (documenti, chat, connettori)
vive dentro uno SearchSpace. Multi-tenancy si implementa creando SearchSpace separati.

### 2.4 Gestione Stato Frontend

```
Server State (PostgreSQL/API)     → TanStack Query (caching, refetch, optimistic updates)
Real-time State (Electric SQL)    → custom hooks (useMessagesElectric, useConnectorsElectric)
Client/UI State                   → Jotai atoms (modal open/close, form state, selections)
Browser Storage                   → localStorage (JWT token, preferences)
```

**Perché 3 layer distinti**: ogni layer ha caratteristiche diverse (latenza, persistenza,
frequenza di aggiornamento). Mischiare server state con UI state crea accoppiamento.

---

## 3. NocoBase — Analisi Architetturale Profonda

### 3.1 Perché è costruito così: la Visione

NocoBase è una **meta-piattaforma**: non è un'app specifica, è un framework per costruire
app senza scrivere codice. Questo impone un'architettura radicalmente flessibile dove
**nessuna feature è hardcoded nel core**. La scelta del plugin microkernel è obbligata.

### 3.2 Design Pattern Identificati

#### Pattern 1: Plugin Microkernel con Lifecycle Hooks

```typescript
abstract class Plugin {
  constructor(app: Application, options?: any)

  async beforeLoad(): Promise<void>    // Prima del caricamento (dipendenze)
  async load(): Promise<void>          // Registra risorse, middleware, hook
  async install(): Promise<void>       // Prima installazione (schema DB)
  async upgrade(): Promise<void>       // Migrazione versione
  async enable(): Promise<void>        // Abilita il plugin
  async disable(): Promise<void>       // Disabilita senza perdita dati
}
```

**Perché**: Il microkernel gestisce solo:
- Boot sequence (DI container, DB connection)
- Plugin lifecycle management
- Event bus

**Tutto il resto è plugin**: autenticazione, gestione utenti, workflow, UI blocks.
Questo permette un sistema che può essere esteso all'infinito senza fork del core.

#### Pattern 2: Toposort Plugin Dependency Resolution

```
Plugin A richiede Plugin B e Plugin C
Plugin B richiede Plugin D
Plugin C richiede Plugin D

Toposort → [D → B → C → A]  (ordine garantito di caricamento)
```

**Perché**: I plugin hanno dipendenze tra loro (ex: `plugin-workflow` richiede
`plugin-collection-manager`). Senza risoluzione topologica, il caricamento ordine-dipendente
causerebbe errori. Questo pattern è **fondamentale per sistemi a plugin**. Apex lo eredita.

#### Pattern 3: Collection-Driven Data Model

```typescript
// Invece di Sequelize models hardcoded:
db.collection({
  name: 'posts',
  fields: [
    { name: 'title', type: 'string' },
    { name: 'content', type: 'text' },
    { name: 'author', type: 'belongsTo', target: 'users' },
    { name: 'tags', type: 'belongsToMany', target: 'tags' },
  ]
})
```

**Perché**: Le `Collection` sono definizioni dichiarative dei modelli dati.
- Possono essere create **a runtime** dall'utente no-code
- Supportano ereditarietà (InheritedCollection)
- Generano automaticamente le tabelle SQL + le API REST
- Il Repository pattern over Collection garantisce type safety e testabilità

#### Pattern 4: Resource/Action REST Pattern

```
POST /api/posts:create
GET  /api/posts:list
GET  /api/posts/1:get
PUT  /api/posts/1:update
DEL  /api/posts/1:destroy
POST /api/posts/1/comments:create  ← relation resource
```

**Perché**: Invece di Express routes manuali, `Resourcer` gestisce la mappatura
URL → action automaticamente per ogni Collection. Un plugin registra una Collection
e ottiene automaticamente una REST API completa. Le Actions sono middleware chains
(Handler pattern) che possono essere intercettate dall'ACL layer.

#### Pattern 5: Schema-Driven UI (Formily)

```typescript
// Lo schema JSON diventa automaticamente un form React:
{
  type: 'object',
  properties: {
    title: {
      type: 'string',
      'x-component': 'Input',
      'x-decorator': 'FormItem',
      'x-index': 1
    },
    content: {
      type: 'string',
      'x-component': 'RichText',
      'x-decorator': 'FormItem',
    }
  }
}
```

**Perché**: Disaccoppia la definizione dell'UI dal rendering. Lo schema può essere
salvato in DB, serializzato, condiviso. Un utente no-code può costruire form e blocchi
UI senza toccare codice. Le modifiche all'UI sono "live" e persistite come configurazione.

#### Pattern 6: ACL a Tre Livelli

```
Application Level ACL  → gestisce accesso globale a risorse
Collection Level ACL   → gestisce accesso a Collection specifiche (e campi)
Row Level ACL          → gestisce accesso a singole righe (con scope conditions)
```

**Perché**: Il controllo accessi a livello di riga è necessario per multi-tenancy
(utente A vede solo i suoi record, admin vede tutti). Il design separato a 3 livelli
evita che l'authorization logic inquini il business logic layer.

### 3.3 Event-Driven Architecture (AsyncEmitter)

```typescript
// Application applica AsyncEmitter mixin:
app.on('beforeStart', async () => { ... })
app.on('afterInstall', async () => { ... })
db.on('afterCreate', 'posts', async (model, options) => { ... })
```

**Perché**: Il sistema event-driven permette ai plugin di reagire a eventi del core
senza modifica al core stesso. Un plugin può registrare hook su `db.afterCreate` di
qualsiasi Collection. Questo è il meccanismo fondamentale per l'estensibilità.

### 3.4 PubSub per Multi-Instance Sync

```
Instance 1 (Redis PUBLISH) → evento "config.changed"
    └─→ Instance 2 (Redis SUBSCRIBE) → reload config
    └─→ Instance 3 (Redis SUBSCRIBE) → reload config
```

**Perché**: In deployment scalati con più istanze dello stesso server, le modifiche
di configurazione (nuovi plugin, collection updates) devono propagarsi a tutte le istanze.
Redis PubSub è il meccanismo con zero overhead aggiuntivo (Redis è già richiesto).

---

## 4. Pattern Comuni — DNA Convergente

| Pattern | SurfSense | NocoBase | Score per Apex |
|---|---|---|---|
| **Separazione asinc/sinc** | Celery + FastAPI | Worker + Koa | ★★★★★ |
| **Plugin/Connector OCP** | Connector Layer | Plugin Microkernel | ★★★★★ |
| **Event-Driven Hooks** | LangGraph events | AsyncEmitter | ★★★★★ |
| **Canonical DTO** | ConnectorDocument | Collection model | ★★★★☆ |
| **Hash-based Deduplication** | content_hash sha256 | — | ★★★★★ |
| **Hybrid Search (dense+sparse)** | pgvector+tsvector | — | ★★★★★ |
| **Schema-driven config** | global_llm_config.yaml | Formily JSON Schema | ★★★★☆ |
| **RBAC multi-livello** | Role/Permission/Team | ACL 3-level | ★★★★★ |
| **Real-time sync** | Electric SQL | PubSub Redis | ★★★★☆ |
| **Streaming AI response** | SSE + LangGraph | — | ★★★★★ |
| **Monorepo** | — | Lerna + Workspaces | ★★★★☆ |
| **Dependency Injection** | FastAPI Depends() | Service Container | ★★★★★ |

---

## 5. Punti di Forza da Ereditare

### Da SurfSense:
1. **IndexingPipeline idempotente** — La deduplica hash-based è produzione-ready e battle-tested.
   Apex la eredita con miglioramenti (retry semantics, DLQ, metrics).

2. **Tool Registry pattern** — La factory function per tool abilitabili per-utente è elegante.
   Apex espande il concetto a un `CapabilityRegistry` generale (non solo AI tools).

3. **Hybrid Search RAG stack** — pgvector + tsvector + FlashRank è lo stack retrieval
   ottimale per PostgreSQL-native. Zero dipendenze esterne (Elasticsearch, Pinecone).

4. **LangGraph Checkpointing** — La persistenza dello stato agent su PostgreSQL elimina
   la necessità di sessionStorage/Redis separato per le sessioni AI.

5. **Electric SQL real-time** — La sincronizzazione PostgreSQL→Browser è invisibile al
   frontend developer. Apex la estende a tutti i domain objects, non solo chat.

### Da NocoBase:
1. **Plugin Microkernel** — Il cuore di Apex sarà un microkernel con lifecycle hooks identici.
   Qualsiasi feature (auth, connectors, AI) diventa un plugin rimovibile/sostituibile.

2. **Toposort dependency resolution** — Necessario per gestire plugin con dipendenze circolari
   preventivamente. Apex lo usa sia per plugin che per agenti AI.

3. **Collection-driven schema** — Apex non hardcoda schemi DB. I domini dati sono dichiarativi
   e possono evolvere senza migrazioni manuali per le entity principali.

4. **Resource/Action REST pattern** — Apex usa un Resourcer analogo per auto-generare API
   REST da dichiarazioni, riducendo boilerplate del 70%.

5. **ACL a 3 livelli** — Application → Resource → Row Level Security. Apex implementa
   RLS direttamente in PostgreSQL via pg_policies per performance ottimale.

---

## 6. Debolezze Identificate (da NON replicare)

### SurfSense:
- **Auth token su localStorage** (XSS vulnerability) → Apex usa HttpOnly cookies
- **Monolito FastAPI** con 35+ route files → Apex struttura per dominio, non per tipo
- **Config hardcoded in YAML** → Apex usa schema validato con Pydantic + hot reload
- **No circuit breaker** su LLM calls → Apex implementa Resilience4J pattern
- **Frontend Drizzle schema separato** dal backend SQLAlchemy → Apex usa un'unica source of truth

### NocoBase:
- **Complessità overhead Formily** per UI semplici → Apex usa Formily solo dove necessario
- **Yarn lock file enorme** (monorepo pesante) → Apex usa PNPM Workspaces + Turborepo
- **ACL evaluation in JavaScript** → Apex usa PostgreSQL RLS per performance
- **I18n in JSON statici** → Apex usa DB-backed translations con fallback statico

---

## 7. Flusso Dati — Come Funziona il Sistema in Produzione

### SurfSense — Flusso Completo di una Chat Session

```
1. USER REQUEST (frontend)
   Browser → POST /threads/{id}/messages
        │
        ▼
2. AUTH MIDDLEWARE
   JWT validation → User object
        │
        ▼
3. PERMISSION CHECK (RBAC)
   check_permission(user, "chat", space_id)
        │
        ▼
4. LLM CONFIG LOAD
   SELECT NewLLMConfig WHERE user_id = ? → AgentConfig
        │
        ▼
5. AGENT CREATION (LangGraph)
   create_surfsense_deep_agent(
     llm=LiteLLM(model_config),
     tools=build_tools(enabled_tools, context),
     checkpointer=PostgresCheckpointer,
     thread_id=thread_id
   )
        │
        ▼
6. STREAMING EXECUTION
   agent.astream(message, thread_id) → async generator
        │
        ▼
7. TOOL CALLS (if needed)
   search_knowledge_base:
     → embed(query) → pgvector_search + tsvector_search
     → rerank(results) → top-N chunks
     → format_documents_for_context()
        │
        ▼
8. LLM RESPONSE GENERATION
   LiteLLM → chosen provider (OpenAI/Claude/Gemini)
        │
        ▼
9. SSE STREAMING TO CLIENT
   StreamingResponse(sse_generator) → frontend
        │
        ▼
10. MESSAGE PERSISTENCE
    INSERT NewChatMessage (role=assistant, content=full_response)
        │
        ▼
11. ELECTRIC SQL SYNC
    PostgreSQL change → Electric → Browser SQLite → UI re-render
```

### NocoBase — Flusso di una API Request

```
1. HTTP Request → Koa middleware stack
2. Auth Middleware → validate token → attach user
3. Resourcer → match URL pattern → identify Resource + Action
4. ACL Middleware → check permission (App → Resource → Row level)
5. Action Handler (plugin-defined) → Database.repository.find/create/update
6. Collection Model → Sequelize query → PostgreSQL
7. Response serialization → JSON response
```

---

## 8. Logica di Business Sottostante

### SurfSense — Business Logic DNA

| Concetto | Implementazione | Perché |
|---|---|---|
| **SearchSpace** = unità di tenancy | Ogni query è filtrata per `search_space_id` | Isolamento dati tra utenti/team |
| **Document deduplication** | SHA256 hash chain | Evita embedding duplicati (costosi) |
| **Async indexing** | Celery queue | L'embedding richiede GPU/API → non bloccante |
| **Per-user LLM config** | `NewLLMConfig` table | Ogni utente sceglie modello, tool, instructions |
| **Citation system** | Chunk IDs nei messaggi | Tracciabilità delle risposte AI → trust |
| **Public chat snapshots** | Read-only thread sharing | Collaborazione senza account |
| **Rate limiting su auth** | Redis INCR+EXPIRE | Prevenzione brute force password |

### NocoBase — Business Logic DNA

| Concetto | Implementazione | Perché |
|---|---|---|
| **Everything is a plugin** | PluginManager registry | Zero core modifications per estendere |
| **Collections as API** | Auto-generated REST | Database-first development |
| **UI as Schema** | Formily JSON | UI configurabile a runtime senza redeploy |
| **Workflow automation** | flow-engine plugin | Business logic visuale senza codice |
| **Multi data source** | DataSourceManager | Federazione di DB eterogenei |
| **AI employees** | AIManager + ToolsLoader | AI integrata nei workflow business |

---

## 9. Sintesi — Il Modello Mentale per Apex Absolute

**Apex Absolute deve essere la sintesi evolutiva di entrambi i sistemi:**

```
SurfSense DNA:
  → Intelligent data ingestion pipeline (ETL + RAG)
  → LangGraph stateful agents con tool registry
  → Hybrid search ottimizzato (pgvector native)
  → Real-time UI via Electric SQL
  → Multi-provider LLM routing (LiteLLM)

NocoBase DNA:
  → Plugin microkernel (tutto è plugin, zero hardcoding)
  → Toposort dependency resolution
  → Resource/Action pattern (auto-REST generation)
  → ACL multi-livello (app → resource → row)
  → Event-driven hooks (AsyncEmitter)

Apex Absolute:
  → Un sistema RAG enterprise-grade con architettura a plugin
  → I connettori sono plugin
  → Gli agent tools sono plugin
  → L'auth è un plugin
  → Il UI è schema-driven con override via plugin
  → La knowledge base è multi-source, multi-tenant, multi-LLM
  → Real-time, streaming, observable, scalabile orizzontalmente
```

**Principio cardine di Apex**: `Se una feature non può essere implementata come plugin,
l'architettura ha un difetto che va corretto nel core, non aggirato.`

---

*Analisi completata. Step 1 terminato. In attesa di "Procedi con Apex" per Step 2 e Step 3.*
