# STEP 2 — Linee Guida e Sistema "Copy Without Copying": `apex_guidelines.md`

> **Ruolo**: ARCHITECT | **Layer DOE**: Directive  
> **Data**: 2026-03-19 | **Basato su**: apex_physical_structure.md + apex_architecture_concept.md

---

## PARTE A — PRINCIPI FONDANTI DI APEX ABSOLUTE

### A.1 Il Principio Cardine

> **"Se una feature non può essere implementata come plugin, l'architettura ha un difetto
> che va corretto nel core, non aggirato."**

Il core di Apex Absolute **non deve sapere** cosa fa l'applicazione. Deve solo sapere come:
- Caricare plugin nell'ordine corretto (Toposort)
- Fornire infrastruttura condivisa (DB, Cache, Event Bus, Auth, Logger)
- Orchestrare il lifecycle di ogni plugin (load → install → enable → disable)
- Esporre un sistema di routing HTTP + middleware chain

**Tutto il resto è plugin.** Autenticazione, connettori, agent AI, UI, report, podcast: plugin.

### A.2 Identità del Sistema

Apex Absolute è un **sistema RAG enterprise-grade a plugin** per la gestione distribuita
della conoscenza organizzativa. Non è un chatbot. Non è un no-code tool. È la fondazione
su cui entrambi possono essere costruiti come plugin intercambiabili.

### A.3 Stack Tecnologico Definitivo di Apex

| Layer | Tecnologia Scelta | Motivazione (vs Originale) |
|---|---|---|
| **Backend Language** | Python 3.12+ | Ecosistema AI nativo (LangGraph, LiteLLM, pgvector) |
| **Backend Framework** | FastAPI (async) | Performance async + OpenAPI automatico |
| **ASGI Server** | Uvicorn (prod) / Granian (perf) | Granian per throughput elevato quando necessario |
| **ORM** | SQLAlchemy 2.x async | Type-safe, async-first, PostgreSQL-native |
| **Database** | PostgreSQL 16+ | pgvector + RLS + tsvector: tutto built-in |
| **Vector Search** | pgvector | Zero dipendenze esterne (vs Elasticsearch/Pinecone) |
| **Migrations** | Alembic (autogenerate) | Standard de facto, integrazione SQLAlchemy |
| **Auth** | fastapi-users + HttpOnly JWT | Fix XSS: **cookie HttpOnly**, non localStorage |
| **Task Queue** | Celery 5 + Redis | Battle-tested, monitoring con Flower |
| **LLM Interface** | LiteLLM Router | Multi-provider unificato, fallback automatico |
| **Agent Framework** | LangGraph 1.x | Stateful agents + checkpointing PostgreSQL |
| **Chunking** | Chonkie (RecursiveChunker) | Migliore semantic-aware splitting vs caratteri fissi |
| **Reranking** | FlashRank (cross-encoder) | Locale, zero latenza API esterna |
| **Doc Parsing** | Docling + Unstructured | Migliore supporto PDF/DOCX enterprise |
| **Rate Limiting** | SlowAPI + Redis | Condiviso tra worker (no per-process) |
| **Frontend Framework** | Next.js 15 (App Router) | RSC + SSR + standalone deploy |
| **Frontend Language** | TypeScript strict | Zero `any`, schema contracts obbligatori |
| **Styling** | Tailwind CSS v4 | Performance build + utility-first |
| **Components** | shadcn/ui + Radix UI | Accessibili, unstyled, full ownership |
| **Server State** | TanStack Query v5 | Caching, background refetch, optimistic updates |
| **Client State** | Jotai atoms | Atomici, lazy, senza boilerplate Redux |
| **Real-time** | Electric SQL | PostgreSQL → Browser sync, zero infrastruttura custom |
| **Chat UI** | assistant-ui | Componenti streaming-native |
| **Rich Text** | Plate.js | Block editor plugin-based (coerente con filosofia Apex) |
| **Monorepo** | PNPM Workspaces + Turborepo | Più veloce di Yarn+Lerna, caching build intelligente |
| **Linting** | Biome (FE) + Ruff (BE) | Velocità massima, configurazione minima |
| **Testing (BE)** | pytest + pytest-asyncio | Standard Python, fixtures async |
| **Testing (FE)** | Vitest + Testing Library | Velocità (no Jest overhead) + DOM testing |
| **E2E** | Playwright | Multi-browser, affidabile, parallelizzabile |
| **Containerization** | Docker + Docker Compose | Sviluppo e produzione identici |
| **CI/CD** | GitHub Actions | Integrazione nativa, matrix testing |

---

## PARTE B — REGOLE DI STILE E CODICE

### B.1 Python (Backend) — Regole Obbligatorie

```python
# ✅ CORRETTO: ogni funzione async con type hints completi
async def index_document(
    connector_doc: ConnectorDocument,
    session: AsyncSession,
    pipeline: IndexingPipelineService,
) -> Document:
    ...

# ❌ VIETATO: wildcard imports, Any senza giustificazione
from app.models import *
from typing import Any  # solo se strettamente necessario con commento esplicativo

# ✅ CORRETTO: Pydantic v2 per tutti i DTO
class ConnectorDocument(BaseModel):
    model_config = ConfigDict(frozen=True)  # Immutabilità per DTO
    unique_id: str
    content: str
    connector_id: int
    search_space_id: int

# ✅ CORRETTO: StrEnum per valori fissi di DB
class DocumentState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

# ✅ CORRETTO: dependency injection via FastAPI Depends
async def get_pipeline(
    session: AsyncSession = Depends(get_async_session),
) -> IndexingPipelineService:
    return IndexingPipelineService(session)

# ✅ CORRETTO: gestione errori con logging strutturato
logger = logging.getLogger(__name__)  # nome modulo come logger name

# ✅ CORRETTO: context manager per transazioni DB esplicite
async with session.begin():
    session.add(document)
```

**Regole Ruff** (da `ruff.toml`):
```toml
[lint]
select = ["E", "F", "I", "N", "UP", "ANN", "S", "B", "A", "C4", "T20"]
ignore = ["ANN101", "ANN102"]  # no self/cls annotation
line-length = 100
```

### B.2 TypeScript (Frontend) — Regole Obbligatorie

```typescript
// ✅ CORRETTO: strict mode sempre attivo (tsconfig.json)
// "strict": true, "noUncheckedIndexedAccess": true

// ✅ CORRETTO: tipi espliciti per tutti i componenti
interface SearchSpaceCardProps {
  searchSpace: SearchSpace;
  onSelect: (id: number) => void;
}

// ❌ VIETATO: any esplicito
const data: any = await fetch(...)  // MAI

// ✅ CORRETTO: discriminated unions per stati
type DocumentStatus =
  | { state: "pending" }
  | { state: "processing"; startedAt: Date }
  | { state: "ready"; indexedAt: Date }
  | { state: "failed"; reason: string; failedAt: Date };

// ✅ CORRETTO: Zod per validazione runtime ai boundary (form, API response)
const SearchSpaceSchema = z.object({
  id: z.number(),
  name: z.string().min(1).max(100),
  createdAt: z.string().datetime(),
});

// ✅ CORRETTO: server components per data fetching, client components per interazione
// app/dashboard/[space_id]/page.tsx → Server Component (fetch + render)
// components/chat/ChatInput.tsx → "use client" (interazione utente)

// ✅ CORRETTO: barrel exports solo a livello di feature, mai a livello di file singolo
// components/connectors/index.ts → export delle feature pubbliche del modulo
```

**Biome config** (`biome.json`):
```json
{
  "linter": {
    "rules": {
      "correctness": { "useExhaustiveDependencies": "error" },
      "security": { "noGlobalEval": "error" },
      "suspicious": { "noExplicitAny": "warn" }
    }
  },
  "formatter": {
    "indentStyle": "tab",
    "lineWidth": 100
  }
}
```

### B.3 Struttura dei File — Convenzioni

#### Backend: Domain-First, non Type-First

```
# ✅ CORRETTO: organizzazione per dominio
src/
  connectors/           ← tutto ciò che riguarda i connettori
    base.py             ← interfaccia astratta
    slack/
      connector.py
      history.py
      tasks.py
    notion/
      connector.py
      history.py

# ❌ EVITARE da SurfSense: organizzazione per tipo che esplode a 35+ file flat
routes/
  slack_route.py
  notion_route.py
  github_route.py
  ... (35+ file)
```

#### Frontend: Feature-First

```
# ✅ CORRETTO: feature co-locata con tutto ciò che le serve
features/
  knowledge-base/
    components/         ← UI components della feature
    hooks/              ← custom hooks della feature
    atoms/              ← state Jotai della feature
    api.ts              ← API calls della feature
    types.ts            ← tipi TypeScript della feature
    index.ts            ← barrel export pubblico

# La feature conosce solo sé stessa + il layer di shared/
shared/
  components/           ← shadcn/ui wrappati + design system
  hooks/                ← use-debounce, use-media-query, etc.
  lib/                  ← utils, cn(), formatDate(), etc.
```

### B.4 Naming Conventions

| Contesto | Regola | Esempio |
|---|---|---|
| **Python classe** | PascalCase | `IndexingPipelineService` |
| **Python funzione/metodo** | snake_case | `compute_content_hash()` |
| **Python costante** | UPPER_SNAKE | `MAX_CHUNK_SIZE = 512` |
| **Python file** | snake_case | `document_chunker.py` |
| **Python StrEnum** | PascalCase + StrEnum | `class DocumentState(StrEnum)` |
| **TS Interface** | PascalCase + `I` solo se ambigua | `SearchSpace`, `ISearchSpaceService` |
| **TS type alias** | PascalCase | `type DocumentStatus = ...` |
| **TS component** | PascalCase | `SearchSpaceCard.tsx` |
| **TS hook** | camelCase + `use` | `useDocuments.ts` |
| **TS atom (Jotai)** | camelCase + `Atom` | `selectedSpaceIdAtom` |
| **TS file page** | kebab-case | `search-space-settings/page.tsx` |
| **DB table** | snake_case plurale | `search_spaces`, `chat_threads` |
| **DB colonna** | snake_case | `search_space_id`, `created_at` |
| **Git branch** | `feature/`, `fix/`, `chore/` | `feature/connector-notion` |
| **Git commit** | Conventional Commits | `feat(connectors): add notion sync` |

### B.5 Sicurezza — Regole Non Negoziabili (OWASP Top 10)

```python
# A01 - Access Control: SEMPRE verificare ownership
# ❌ VIETATO
document = await session.get(Document, document_id)
# ✅ CORRETTO: filtrare per user ownership
document = await session.scalar(
    select(Document)
    .where(Document.id == document_id)
    .where(Document.search_space.has(SearchSpace.user_id == current_user.id))
)

# A03 - Injection: MAI query string concatenate
# ❌ VIETATO
query = f"SELECT * FROM documents WHERE title = '{user_input}'"
# ✅ CORRETTO: parameterized queries (SQLAlchemy ORM o text() con bindparam)
result = await session.execute(
    select(Document).where(Document.title == user_input)
)

# A07 - Auth: HttpOnly cookies, token refresh rotation
# NON usare localStorage per JWT (XSS vulnerability da SurfSense - lezione imparata)
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,
    samesite="lax",
)

# A05 - Security Misconfiguration: validare CORS in produzione
# NON usare allow_origins=["*"] in produzione
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,  # lista esplicita da env var
    allow_credentials=True,
)
```

---

## PARTE C — SISTEMA "COPY WITHOUT COPYING"

### C.1 Estrazione Pattern — Mappatura Concettuale

Questa tabella definisce come ogni pattern dei sistemi originali viene **astratto e
migliorato** per Apex Absolute. Non si copia il codice: si copia il *concept*.

---

#### C.1.1 Da SurfSense → IndexingPipeline ETL

**Originale** (cosa fa SurfSense):
```
ConnectorDocument DTO → hash dedup → chunk → embed → summarize → persist
```

**Apex Version** (cosa miglioriamo):
```
IngestionJob (più ricco del ConnectorDocument):
  + retry_policy: RetryPolicy        ← nuovo: gestione retry intelligente
  + priority: int                    ← nuovo: priorità nella coda
  + metadata: dict                   ← esteso

Pipeline stages diventano plugin:
  ApexStage[T_in, T_out]             ← stage tipizzato (type-safe pipeline)
  ├── HashDeduplicationStage
  ├── ChunkingStage (strategy pattern: code/prose/structured)
  ├── EmbeddingStage (pluggable provider: local/API)
  ├── SummarizationStage (opzionale, skip se LLM non configurato)
  └── PersistenceStage

Dead Letter Queue per failed jobs:
  → Failed documents vanno in DLQ
  → Dashboard visualizza errori per tipo
  → Retry manuale o automatico configurabile
```

**DNA preservato**: idempotenza hash-based, separazione staging, async via Celery.  
**Miglioramento**: type-safe stages, DLQ, priority queue, strategy pattern per chunking.

---

#### C.1.2 Da SurfSense → Tool Registry

**Originale** (cosa fa SurfSense):
```python
BUILTIN_TOOLS = [ToolDefinition(name, factory, enabled_by_default), ...]
build_tools(enabled_tools, context) → list[BaseTool]
```

**Apex Version** (CapabilityRegistry — più generale):
```python
@dataclass
class Capability:
    name: str
    category: CapabilityCategory  # SEARCH | GENERATION | INTEGRATION | UTILITY
    description: str
    factory: Callable[[CapabilityContext], BaseCapability]
    requires: list[str]            # dipendenze da altri plugin (Toposort)
    enabled_by_default: bool
    config_schema: type[BaseModel] # schema Pydantic per config per-utente

class CapabilityRegistry:
    def register(self, capability: Capability) -> None: ...
    def build(self, enabled: list[str], context: CapabilityContext) -> list[BaseCapability]: ...
    def get_config_schemas(self) -> dict[str, type[BaseModel]]: ...
```

**DNA preservato**: factory pattern, per-user enablement, registry centralizzato.  
**Miglioramento**: categorie, dipendenze tra capability, config schema per UI automatica.

---

#### C.1.3 Da SurfSense → Hybrid Search

**Originale** (cosa fa SurfSense):
```
vector_search(query, top_k) + fulltext_search(query, top_k) → merge → rerank
```

**Apex Version** (SearchEngine con strategy):
```python
class ApexSearchEngine:
    strategies: list[SearchStrategy]  # pluggable
    fusion: FusionStrategy             # RRF (Reciprocal Rank Fusion) vs simple merge
    reranker: RerankerStrategy         # flashrank / cross-encoder / none
    
    async def search(self, query: SearchQuery) -> SearchResult:
        # 1. Fan-out su tutte le strategie in parallelo (asyncio.gather)
        # 2. Fusione con RRF (migliore di merge semplice per ranking)
        # 3. Filtraggio per access control (search_space_id + RLS)
        # 4. Reranking cross-encoder
        # 5. Return top-N con metadata citazione
```

**DNA preservato**: pgvector + tsvector native, FlashRank reranking.  
**Miglioramento**: RRF fusion (superiore al merge semplice), parallel fan-out, pluggable strategies.

---

#### C.1.4 Da SurfSense → LangGraph Agent

**Originale** (cosa fa SurfSense):
```python
create_surfsense_deep_agent(llm, tools, checkpointer, thread_id)
→ LangGraph graph con agent + tool nodes
→ SSE streaming via StreamingResponse
```

**Apex Version** (AgentFactory — più configurabile):
```python
class ApexAgentFactory:
    def create(
        self,
        profile: AgentProfile,          # system_prompt + tool_set + llm_config
        thread_id: str,
        context: AgentContext,           # user, space, permissions
        checkpointer: Checkpointer,      # sempre PostgreSQL in prod
    ) -> ApexAgent:
        ...

@dataclass
class AgentProfile:
    name: str
    system_prompt_template: str         # Jinja2 template
    capabilities: list[str]             # da CapabilityRegistry
    llm_config: LLMConfig
    interrupt_before: list[str] = []    # Human-in-the-loop nodes
    memory_enabled: bool = True         # short + long term memory
```

**DNA preservato**: LangGraph, SSE streaming, PostgreSQL checkpoint.  
**Miglioramento**: profile-based agent, Jinja2 system prompt, human-in-the-loop configurabile.

---

#### C.1.5 Da NocoBase → Plugin Microkernel

**Originale** (cosa fa NocoBase):
```typescript
abstract class Plugin {
  beforeLoad() → load() → install() → enable() → disable()
}
```

**Apex Version** (Python-native, ancora più strutturato):
```python
class ApexPlugin(ABC):
    def __init__(self, app: "ApexApp", config: BaseModel): ...
    
    async def on_before_load(self) -> None:
        """Validazione dipendenze. Raise se manca una dipendenza."""
    
    async def on_load(self) -> None:
        """
        Registra routes, event handlers, capabilities.
        NON fare query al DB qui (non è ancora pronto).
        """
    
    async def on_install(self) -> None:
        """Prima installazione: crea tabelle, dati seed, configurazioni default."""
    
    async def on_upgrade(self, from_version: str) -> None:
        """Migrazione da versione precedente a quella corrente."""
    
    async def on_enable(self) -> None:
        """Attiva il plugin (può registrare scheduled tasks, etc.)"""
    
    async def on_disable(self) -> None:
        """Disattiva senza perdita dati (inverso di enable)."""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    def requires(self) -> list[str]:
        """Plugin richiesti (usati da Toposort). Default: []"""
        return []
    
    @property
    def version(self) -> str:
        return "1.0.0"
```

**DNA preservato**: lifecycle hooks, dependency declaration.  
**Miglioramento**: Python-native, typed config via Pydantic, `on_upgrade` esplicito.

---

#### C.1.6 Da NocoBase → Resource/Action Pattern

**Originale** (cosa fa NocoBase):
```typescript
resourcer.define({ name: 'posts', actions: { list, get, create, update, destroy } })
// Auto-genera: GET /api/posts, POST /api/posts, GET /api/posts/:id, ...
```

**Apex Version** (ResourceRouter — FastAPI native):
```python
class ApexResource:
    """Un ApexResource auto-genera un APIRouter FastAPI con CRUD standard."""
    
    model: type[BaseModel]              # Pydantic schema della risorsa
    db_model: type[Base]                # SQLAlchemy model
    actions: set[ResourceAction]        # {LIST, GET, CREATE, UPDATE, DELETE}
    middleware: list[Callable]          # middleware chain per questa risorsa
    
    def to_router(self) -> APIRouter:
        """Genera APIRouter FastAPI con tutti i CRUD endpoints configurati."""
        ...

# Uso in un plugin:
class ConnectorsPlugin(ApexPlugin):
    async def on_load(self):
        self.app.register_resource(ApexResource(
            model=ConnectorRead,
            db_model=Connector,
            actions={LIST, GET, CREATE, UPDATE, DELETE},
            middleware=[require_permission("connectors:manage")],
        ))
```

**DNA preservato**: auto-generazione REST, middleware chain.  
**Miglioramento**: FastAPI native (OpenAPI automatico), tipo-safe con Pydantic.

---

#### C.1.7 Da NocoBase → ACL Multi-Livello

**Originale** (cosa fa NocoBase):
```
App Level → Resource Level → Row Level (JS evaluation)
```

**Apex Version** (PostgreSQL RLS-first):
```sql
-- Row Level Security direttamente in PostgreSQL (ADR-008)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_isolation ON documents
    USING (
        search_space_id IN (
            SELECT id FROM search_spaces
            WHERE user_id = current_setting('app.current_user_id')::uuid
            OR id IN (
                SELECT space_id FROM team_space_memberships
                WHERE team_id IN (
                    SELECT team_id FROM user_team_memberships
                    WHERE user_id = current_setting('app.current_user_id')::uuid
                )
            )
        )
    );
```

```python
# FastAPI middleware setta il contesto PostgreSQL
async def set_rls_context(request: Request, call_next):
    user = await get_current_user(request)
    async with get_db_session() as session:
        await session.execute(
            text("SET LOCAL app.current_user_id = :uid"),
            {"uid": str(user.id)}
        )
    return await call_next(request)
```

**DNA preservato**: ACL a 3 livelli (app → resource → row).  
**Miglioramento**: RLS in PostgreSQL = performance + sicurezza (impossibile bypassare dal codice).

---

#### C.1.8 Da NocoBase → Event-Driven Hooks

**Originale** (cosa fa NocoBase):
```typescript
app.on('afterInstall', async () => { ... })
db.on('afterCreate', 'posts', async (model) => { ... })
```

**Apex Version** (ApexEventBus — tipizzato):
```python
# Evento tipizzato
@dataclass(frozen=True)
class DocumentIndexedEvent:
    document_id: int
    search_space_id: int
    connector_type: str
    chunk_count: int
    indexed_at: datetime

# Handler registrato da un plugin
class NotificationPlugin(ApexPlugin):
    async def on_load(self):
        self.app.events.on(DocumentIndexedEvent, self._on_document_indexed)
    
    async def _on_document_indexed(self, event: DocumentIndexedEvent) -> None:
        await self.notification_service.notify_space_members(
            event.search_space_id,
            f"New document indexed: {event.chunk_count} chunks processed"
        )

# Emissione dell'evento
await self.app.events.emit(DocumentIndexedEvent(
    document_id=doc.id,
    search_space_id=doc.search_space_id,
    ...
))
```

**DNA preservato**: event-driven, plugin-to-plugin communication senza accoppiamento.  
**Miglioramento**: eventi tipizzati (no stringa libera), type checking compile-time.

---

#### C.1.9 Da SurfSense → Electric SQL Real-Time

**Originale** (cosa fa SurfSense):
```
PostgreSQL → Electric Sync Engine → PGLite in browser → React hooks
```

**Apex Version** (ApexLive — astrazione controllata):
```typescript
// Hook generato per ogni entity:
function useApexLive<T extends ApexEntity>(
  query: LiveQuery<T>,
  options: UseApexLiveOptions = {}
): { data: T[]; loading: boolean; error: Error | null } {
  // Internamente usa Electric SQL
  // Gestisce autenticazione + scope filtering automaticamente
  // Fallback a TanStack Query se Electric non disponibile
}

// Uso:
const { data: messages } = useApexLive(
  liveQuery(chatMessages).where({ threadId }).orderBy("createdAt"),
  { realtimeEnabled: true }
);
```

**DNA preservato**: PostgreSQL → Browser sync, zero WebSocket custom.  
**Miglioramento**: abstraction layer che può fallback a polling, scope filtering automatico.

---

### C.2 Architettura Complessiva di Apex — Il Blueprint

```
┌─────────────────────────────────────────────────────────────────┐
│                        APEX ABSOLUTE                            │
├─────────────────────────────────────────────────────────────────┤
│  FRONTEND (Next.js 15 App Router)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Server Comp. │  │ Client Comp. │  │ Electric SQL Sync    │  │
│  │ (data fetch) │  │ (interaction)│  │ (real-time UI)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Feature Modules (plugin-driven UI)                       │   │
│  │ knowledge-base/ | chat/ | connectors/ | reports/ | ...  │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  APEX CORE (FastAPI + Plugin Microkernel)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ApexApp      │  │ PluginMgr    │  │ ApexEventBus         │  │
│  │ (bootstrap)  │  │ (Toposort)   │  │ (typed events)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ResourceRtr  │  │ ACL Mgr      │  │ CapabilityRegistry   │  │
│  │ (auto-REST)  │  │ (RLS+policy) │  │ (tool registry)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  BUILT-IN PLUGINS (ogni feature è un plugin)                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │plugin-auth │ │plugin-rbac │ │plugin-kb   │ │plugin-chat │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │plugin-conn │ │plugin-agent│ │plugin-reprt│ │plugin-teams│   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  ASYNC INFRASTRUCTURE                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Celery       │  │ LangGraph    │  │ IngestionPipeline    │  │
│  │ (task queue) │  │ (agents)     │  │ (ETL + DLQ)          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                     │
│  ┌──────────────────────┐  ┌────────────┐  ┌────────────────┐  │
│  │ PostgreSQL 16+       │  │ Redis      │  │ S3/Local       │  │
│  │ pgvector + RLS       │  │ (cache+mq) │  │ (file storage) │  │
│  └──────────────────────┘  └────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

### C.3 Struttura Monorepo di Apex Absolute

```
apex_absolute/
├── packages/
│   ├── core/                          # @apex/core — Plugin Microkernel Python
│   │   ├── apex_core/
│   │   │   ├── app.py                 # ApexApp (bootstrap + DI)
│   │   │   ├── plugin.py              # ApexPlugin abstract base
│   │   │   ├── plugin_manager.py      # Toposort + lifecycle orchestrator
│   │   │   ├── event_bus.py           # ApexEventBus (typed events)
│   │   │   ├── resource_router.py     # Auto-REST resource generator
│   │   │   ├── capability_registry.py # CapabilityRegistry
│   │   │   └── database.py            # DB setup + RLS middleware
│   ├── plugins/                       # Plugin ufficiali
│   │   ├── plugin-auth/               # @apex/plugin-auth
│   │   ├── plugin-rbac/               # @apex/plugin-rbac
│   │   ├── plugin-knowledge-base/     # @apex/plugin-knowledge-base
│   │   │   ├── ingestion_pipeline/
│   │   │   ├── search_engine/
│   │   │   └── connectors/
│   │   ├── plugin-chat/               # @apex/plugin-chat
│   │   │   ├── agents/
│   │   │   ├── tools/
│   │   │   └── streaming/
│   │   ├── plugin-teams/              # @apex/plugin-teams
│   │   ├── plugin-reports/            # @apex/plugin-reports
│   │   └── plugin-notifications/      # @apex/plugin-notifications
│   └── sdk/                           # @apex/sdk — client TypeScript
├── apps/
│   ├── api/                           # Entrypoint FastAPI (composer)
│   │   ├── main.py
│   │   └── plugins.py                 # Registrazione plugin attivi
│   ├── web/                           # Next.js 15 frontend
│   │   ├── app/
│   │   ├── features/                  # Feature modules (una per plugin)
│   │   └── shared/
│   └── worker/                        # Celery worker entrypoint
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── migrations/                    # Alembic migrations (condivise)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/                           # Playwright
├── pnpm-workspace.yaml
├── turbo.json
├── pyproject.toml                     # Workspace Python root
└── .github/workflows/                 # CI/CD
```

---

## PARTE D — REGOLE DI QUALITÀ E PROCESSO

### D.1 TDD — Red/Green/Refactor (Metodo Sacchi)

```python
# STEP 1 (RED): scrivi il test PRIMA — deve fallire
async def test_indexing_pipeline_deduplicates_same_content():
    doc1 = ConnectorDocument(unique_id="abc", content="hello world", ...)
    doc2 = ConnectorDocument(unique_id="abc", content="hello world", ...)  # stesso
    
    pipeline = IndexingPipelineService(session)
    result1 = await pipeline.prepare_for_indexing([doc1])
    result2 = await pipeline.prepare_for_indexing([doc2])
    
    assert len(result2) == 0  # secondo run: nessun nuovo documento da indicizzare

# STEP 2 (GREEN): implementa il minimo per far passare il test
# STEP 3 (BLUE): refactoring senza rompere i test
```

### D.2 Commit Discipline

```bash
# Formato: Conventional Commits
feat(plugin-kb): add flashrank reranking to hybrid search
fix(plugin-auth): use httponly cookie instead of localstorage token  
chore(deps): upgrade litellm to 1.80.10
test(pipeline): add deduplication edge case tests
docs(adr): add ADR-008 postgresql rls decision

# Ogni commit deve:
# 1. Compilare senza errori
# 2. Passare tutti i test esistenti
# 3. Essere atomico (una sola modifica logica)
```

### D.3 Pull Request Checklist

Prima di ogni PR:
- [ ] Test scritti prima del codice (TDD)
- [ ] Tutti i test passano (`pytest` + `vitest`)
- [ ] Linting pulito (`ruff check` + `biome check`)
- [ ] Type checking pulito (`mypy` strict + `tsc --noEmit`)
- [ ] Nessuna secrets/API key committata
- [ ] Migrazioni Alembic generate se schema DB modificato
- [ ] ADR aggiornato se decisione architetturale presa
- [ ] `activeContext.md` aggiornato se fase completata

### D.4 Gestione Segreti

```bash
# ✅ CORRETTO: variabili d'ambiente con validazione Pydantic
class ApexSettings(BaseSettings):
    database_url: PostgresDsn
    redis_url: RedisDsn
    secret_key: SecretStr  # non loggato mai
    litellm_api_key: SecretStr | None = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# ❌ VIETATO: hardcoded credentials, config in codice
DATABASE_URL = "postgresql://user:password@localhost/apex"  # MAI
```

---

*Step 2 completato. Procedere con Step 3: `apex_workflow.md`*
