Searched for files matching `free-models` · `apex-gate/**`, 20 matches

Searched for files matching `**/apex-gate/**`, 20 matches

Searched for files matching `**/apex-gate/backend/**`, 81 matches

Searched for files matching `**/apex-gate/frontend/src/**`, 44 matches

Now let me read the key files in parallel to understand the architecture deeply.    

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/docs/concept.md#1-1), lines 1 to 100

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/docs/architecture.md#1-1), lines 1 to 150

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/main.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/HANDOFF.md#1-1), lines 1 to 150

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/manager.py#1-1), lines 1 to 150

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/router.py#1-1), lines 1 to 100

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/auth/router.py#1-1), lines 1 to 80

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/crypto.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/websocket.py#1-1), lines 1 to 80

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/scheduler.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/config.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/protocols.py#1-1), lines 1 to 80

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/manager.py#80-80), lines 80 to 150

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/api_key.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/virtual_key.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/discovery/service.py#1-1), lines 1 to 60

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/manager.py#80-80), lines 80 to 230

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/requirements.txt)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/frontend/src/App.tsx)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/docker-compose.yml)

Created 2 todos

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/auth/service.py#1-1), lines 1 to 60

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/tests/test_auth.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/tests/conftest.py#1-1), lines 1 to 80

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/keys.py#1-1), lines 1 to 60

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/HANDOFF.md#150-150), lines 150 to 200

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/router.py#80-80), lines 80 to 100

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/providers/base.py)

Starting: *Create report on apex-gate findings* (2/2)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/stats.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/request_log.py)

Now I have enough context for a comprehensive report.

---

## Exploration: APEX GATE

### Cos'è il progetto

APEX GATE è un **API Gateway self-hosted per LLM**. Si frappone tra le applicazioni del developer e i provider AI reali (Groq, NVIDIA NIM, Gemini, OpenRouter, Anthropic, OpenAI, Mistral, Ollama…), espone endpoint OpenAI-compatibili, gestisce un pool cifrato di chiavi API con fallback automatico via LiteLLM Router, e fornisce una dashboard React per la gestione completa.

---

### Entry Points

| Trigger | Entry point |
|---|---|
| Richieste AI (client) | `POST /v1/chat/completions`, `/openai/v1/chat/completions` |
| Protocollo Anthropic | `POST /anthropic/v1/messages` |
| Protocollo Gemini | `POST /gemini/*` |
| Autenticazione | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` |
| Gestione chiavi | `GET/POST/PATCH/DELETE /api/v1/keys` |
| Virtual keys | `GET/POST/PATCH/DELETE /api/v1/virtual-keys` |
| Statistiche | `GET /api/v1/stats/overview|by-provider|by-model|by-day|costs` |
| Status real-time | WebSocket `/ws/status` |
| Health | `GET /health` |

---

### Flusso di esecuzione (percorso critico)

```
Client
  └─ POST /v1/chat/completions
       Authorization: Bearer apg-abc123
       
  1. proxy/router.py  _resolve_virtual_key()
       SHA-256(token) → lookup su virtual_keys.key_hash
       → 401 se mancante/disabilitata
       
  2. proxy/manager.py  is_budget_exceeded()
       Somma token di oggi su request_logs
       → 429 se daily_token_budget superato
       
  3. proxy/manager.py  call_with_router()
       Carica VirtualKeyAssignment (priority ASC)
       Per ogni assignment:
         - skip se api_key disabilitata
         - skip se ExhaustionState attivo
         - AUTO mode → is_default=True da ModelCatalog
         - EXPLICIT mode → LIKE '%model_request%' su ModelCatalog
         - decrypt(key_encrypted) via Fernet
         - aggiunge entry a model_list per LiteLLM Router
       
  4. litellm.Router(priority-based).acompletion()
       → 429 su una key  → passa automaticamente alla successiva
       → AuthenticationError → disabilita tutte le key tentate
       
  5. Logging su request_logs
       (user_id, virtual_key_id, api_key_id, model_id,
        input_tokens, output_tokens, cost_usd, latency_ms, status)
       
  6. Response JSON + headers
       X-Model-Used, X-Provider-Used, X-Virtual-Key
```

---

### Architettura a layer

```
┌─────────────────────────────────┐
│         Frontend (React 19)     │  Porta 3000
│  TanStack Query + Zustand       │  Lazy pages, CSS Modules
└──────────────┬──────────────────┘
               │ HTTP/REST + WebSocket
┌──────────────▼──────────────────┐
│         FastAPI (Python 3.12)   │  Porta 8000
│  ┌────────────────────────────┐ │
│  │  SecurityHeadersMiddleware  │ │  X-Frame, CORS, Referrer
│  └────────────────────────────┘ │
│  ┌──────────┐  ┌─────────────┐  │
│  │  auth/   │  │   api/v1/   │  │  JWT(15min)+Refresh(30d)
│  └──────────┘  └─────────────┘  │  Bcrypt rounds=12
│  ┌─────────────────────────────┐ │
│  │       proxy/                │ │  LiteLLM Router
│  │  router.py → manager.py     │ │  priority-based fallback
│  │  protocols.py               │ │  Anthropic/Gemini→OpenAI
│  └─────────────────────────────┘ │
│  ┌─────────────────────────────┐ │
│  │       discovery/            │ │  APScheduler every N hrs
│  │  Groq,NVIDIA,OpenRouter,    │ │  scrape model catalog
│  │  Gemini scrapers            │ │
│  └─────────────────────────────┘ │
└──────────────┬──────────────────┘
               │ SQLAlchemy async
┌──────────────▼──────────────────┐
│  Dual DB (SQLite / PostgreSQL)  │
│  apex_gate.db      apex_gate_auth.db
│  providers         users
│  api_keys          refresh_tokens
│  virtual_keys
│  model_catalog
│  exhaustion_state
│  request_logs
└─────────────────────────────────┘
```

---

### File chiave

| File | Ruolo | Importanza |
|---|---|---|
| backend/app/main.py | FastAPI app, middleware, lifespan (init DB + seed) | Critico |
| backend/app/proxy/manager.py | Core del gateway: routing, fallback, logging | Critico |
| backend/app/proxy/router.py | Endpoint proxy HTTP + virtual key validation | Critico |
| backend/app/crypto.py | Fernet encrypt/decrypt, SHA-256 hash, virtual key gen | Alta |
| backend/app/auth/service.py | JWT creation/verify, bcrypt, refresh token rotation | Alta |
| backend/app/proxy/protocols.py | Traduzione Anthropic/Gemini ↔ OpenAI | Alta |
| backend/app/scheduler.py | 3 job: reset exhaustion, cleanup logs, model discovery | Media |
| backend/app/discovery/service.py | Scraping modelli dai provider reali | Media |
| backend/app/api/stats.py | Aggregazioni SQL per analytics (costi, token, latency) | Media |
| frontend/src/App.tsx | React Router con lazy loading + ProtectedRoute | Media |
| backend/tests/conftest.py | Fixture con SQLite in-memory + DI override | Media |

---

### Dipendenze

**Esterne**:
- `litellm >= 1.40` — astrazione multi-provider + Router con fallback automatico
- `apscheduler >= 3.10` — job scheduling asincrono
- `cryptography (Fernet)` — cifratura at-rest chiavi API
- `PyJWT + bcrypt` — autenticazione stateless
- `sqlalchemy[asyncio] 2.0` + `alembic` — ORM async + migrazioni
- `aiosqlite` / `asyncpg` — driver SQLite/PostgreSQL

**Interne**:
- crypto.py usato da `proxy/manager.py`, `auth/service.py`, `api/keys.py`
- `auth/deps.py` (get_current_user) usato da tutti gli endpoint `/api/v1/*`
- `models/` importati da proxy, api, discovery, scheduler

---

### Stato della sicurezza

**Già implementato** ✅:
- `SecurityHeadersMiddleware` — X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy
- CORS origins espliciti (no wildcard)
- Fernet encryption at-rest per le API key dei provider
- SHA-256 hash per lookup virtual keys (nessun plaintext in DB)
- JWT (exp=15min) + refresh token rotation con revoca in DB
- bcrypt(rounds=12) per le password
- WebSocket `/ws/status` con auth JWT via query param **prima** di `accept()`
- Budget giornaliero token (`daily_token_budget`) per virtual key
- Auto-disable API key su `AuthenticationError`

**Vulnerabilità / problemi aperti** ❌:

1. **N+1 query in `call_with_router()`** (HIGH) — per ogni `VirtualKeyAssignment` vengono eseguiti `db.get(ApiKey)`, `db.get(Provider)`, + 1-2 scalar query separate. Con molte chiavi è un bottleneck rilevante. Fix nel HANDOFF: sostituire con un JOIN singolo.

2. **Scheduler senza try/except** (HIGH) — i 3 job in scheduler.py non hanno error handling. Una singola eccezione può silenziare il job permanentemente senza log. Il HANDOFF contiene il fix esatto da applicare.

3. **`_build_response` in `api/keys.py` decripta on-list** (MEDIUM) — la funzione chiama `decrypt_key()` per ogni chiave listata solo per produrre la versione mascherata. Con centinaia di chiavi è un overhead evitabile: `mask_key` potrebbe lavorare su un hash/prefisso persistito in DB.

4. **Auto-disable troppo aggressivo su `AuthenticationError`** (MEDIUM) — quando LiteLLM lancia `AuthenticationError`, il codice disabilita **tutte** le chiavi tentate, anche se solo una era scaduta. Questo può disabilitare chiavi valide.

5. **`model_request` non sanitizzato nella LIKE query** (LOW) — `ModelCatalog.model_id.contains(model_name)` genera un `LIKE %<value>%` dove `model_name` proviene direttamente dal body del client. SQLAlchemy parametrizza correttamente (no SQL injection), ma wildcards come `%` o `_` nel nome modello potrebbero restituire match inattesi.

---

### Test coverage

| File test | Cosa copre |
|---|---|
| test_auth.py | Register, login, logout, refresh rotation, me endpoint |
| test_crypto.py | Encrypt/decrypt, mask, virtual key generation |
| test_api_keys.py | CRUD chiavi API |
| conftest.py | SQLite in-memory, DI override, fixture `auth_headers` |
| `test_proxy.py` | Presente ma non letto — stato incerto |

**Gap**: nessun test end-to-end sul flusso proxy completo (mock LiteLLM → verifica log); nessun test per discovery scrapers.

---

### Raccomandazioni per nuovo sviluppo

1. **Applicare FIX A (scheduler error handling)** e **FIX B (N+1 → JOIN)** — entrambi chiari e chirurgici, descritti nel HANDOFF.md
2. **Riutilizzare** `_resolve_virtual_key()` come dipendenza FastAPI su tutti i nuovi endpoint proxy — non duplicare la logica di lookup
3. **Seguire il pattern** `model_to_key_id: dict[str, str]` per tracciare quale chiave ha effettivamente risposto, prima di fare log
4. **Evitare** di aggiungere provider hardcoded: usare la tabella `providers` + seed in `seeds/providers.py`
5. **Nuovi scraper** devono estendere `AbstractScraper` in `discovery/base.py` e registrarsi in `discovery/service.py._SCRAPERS`
6. **Aggiungere** `misfire_grace_time=30` al job reset_exhaustions (già nel HANDOFF) per evitare doppie esecuzioni a burst

Completed: *Create report on apex-gate findings* (2/2)


Searched for files matching `free-models` · `apex-gate/**`, 100 matches

Searched for files matching `free-models` · `apex-gate/backend/app/**`, 61 matches

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/main.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/manager.py#1-1), lines 1 to 120

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/router.py#1-1), lines 1 to 120

Created 2 todos

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/manager.py#120-120), lines 120 to 250

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/router.py#100-100), lines 100 to 187

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/protocols.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/scheduler.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/websocket.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/config.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/discovery/service.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/auth/service.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/auth/deps.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/keys.py#1-1), lines 1 to 120

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/virtual_keys.py#1-1), lines 1 to 120

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/stats.py#1-1), lines 1 to 80

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/providers/registry.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/providers/base.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/providers.py#1-1), lines 1 to 80

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/virtual_key.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/api_key.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/request_log.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/crypto.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/logs.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/admin.py#1-1), lines 1 to 100

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/frontend/src/api/client.ts)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/frontend/src/api/auth.ts)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/frontend/src/store/authStore.ts)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/auth/router.py#1-1), lines 1 to 100

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/frontend/src/hooks/useProviderStatus.ts)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/frontend/src/pages/Dashboard.tsx#1-1), lines 1 to 100

Created 2 todos

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/manager.py#100-100), lines 100 to 250

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/models_api.py#1-1), lines 1 to 80

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/exhaustion_state.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/manager.py#100-100), lines 100 to 322

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/discovery/base.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/database.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/keys.py#100-100), lines 100 to 120

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/frontend/src/api/virtualKeys.ts)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/seeds/providers.py#1-1), lines 1 to 80

Updated todo list

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/virtual_keys.py#100-100), lines 100 to 120

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/api/schemas/virtual_key_schemas.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/frontend/src/pages/VirtualKeys.tsx#1-1), lines 1 to 80

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/proxy/providers/anthropic.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/model_catalog.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/models/provider.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/docker-compose.yml)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/auth/database.py)

Read [](file:///c%3A/Users/matti/Desktop/free-models/apex-gate/backend/app/auth/models.py)

Created 3 todos

Ora ho abbastanza contesto per il report completo.

---

# Apex Gate — Bug & Architecture Report

## CRITICO

---

### [C-1] WebSocket provider status non funziona mai
**File:** frontend/src/hooks/useProviderStatus.ts · backend/app/websocket.py

Il frontend apre la connessione WS **senza il token di autenticazione**:
```ts
// ❌ nessun ?token= nella query string
const ws = new WebSocket(`${proto}://${window.location.host}/ws/status`);
```

Il backend richiede `?token=` e chiude immediatamente se assente:
```python
token = websocket.query_params.get("token")
if not token:
    await websocket.close(code=_WS_CLOSE_UNAUTHORIZED)
    return
```

Il pannello "Provider status" nella Dashboard è **sempre vuoto** — `wsStatus` sarà `null` per tutta la vita dell'app.

**Fix:**
```ts
const token = localStorage.getItem("access_token");
const ws = new WebSocket(`${proto}://${window.location.host}/ws/status?token=${token}`);
```

---

### [C-2] Richieste in streaming non vengono mai loggate — budget bypass
**File:** backend/app/proxy/manager.py

Quando `stream=True`, il manager restituisce il generatore grezzo prima di creare alcun `RequestLog`:
```python
# Streaming: return the raw generator without blocking for logging
if not hasattr(response, "model_dump"):
    return response, "streaming"   # ← esce PRIMA del log
```

Conseguenze:
- I token consumati in streaming **non vengono mai contati** nel `daily_token_budget`
- `is_budget_exceeded()` viene controllato prima della chiamata ma non viene mai aggiornato dopo → un client streaming può consumare token illimitati indipendentemente dal budget impostato
- La pagina Logs mostra solo chiamate non-streaming

---

## ALTO

---

### [H-1] `model_preference` — campo fantasma tra frontend e backend
**File:** frontend/src/api/virtualKeys.ts, backend/app/api/schemas/virtual_key_schemas.py, backend/app/models/virtual_key.py

Il frontend invia `model_preference` alla creazione di una virtual key:
```ts
createVirtualKey({
  ...
  model_preference: routingMode === "explicit" && modelPref.trim() ? modelPref.trim() : null,
})
```

Il backend (`VirtualKeyCreate`) **non ha questo campo** — viene silenziosamente scartato da Pydantic. Il modello DB `VirtualKey` ha solo `allowed_providers` (mai letto dal proxy). L'intera UI "routing esplicito / model preference" è dead code — il dato non viene mai salvato né usato nel routing.

---

### [H-2] `AuthenticationError` disabilita tutte le chiavi, non solo quella responsabile
**File:** backend/app/proxy/manager.py

```python
except litellm.exceptions.AuthenticationError:
    for key_id in tracked_key_ids:  # ← TUTTE le chiavi tentate
        ak = await db.get(ApiKey, key_id)
        if ak is not None:
            ak.is_enabled = False
```

Con `routing_strategy="priority-based"`, litellm tenta i provider in ordine. Se fallisce solo la prima chiave, vengono disabilitate anche quelle che non hanno mai ricevuto il tentativo. Un singolo errore di autenticazione può rendere inutilizzabile l'intera virtual key.

---

### [H-3] Cloudflare Workers AI sempre rotto — URL con placeholder letterale
**File:** backend/app/seeds/providers.py

```python
{"slug": "cloudflare_ai", ..., "api_base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"}
```

La stringa `{account_id}` non viene mai sostituita. Ogni chiamata verso Cloudflare fallirà con un errore HTTP 404/400.

---

### [H-4] Registrazione aperta senza rate limiting
**File:** backend/app/auth/router.py

`POST /auth/register` e `POST /auth/login` sono esposti senza alcuna forma di rate limiting o throttling. Vulnerabili a brute-force e account flooding. Non esiste sistema di inviti né whitelist.

---

### [H-5] Token JWT e refresh token in `localStorage` — vulnerabili a XSS
**File:** frontend/src/store/authStore.ts, frontend/src/api/client.ts

Entrambi i token vengono salvati in `localStorage`, accessibile da qualsiasi script sulla pagina. Un attacco XSS può esfiltrarli. Il pattern raccomandato è `HttpOnly` cookie per il refresh token.

---

## MEDIO

---

### [M-1] `PROVIDER_REGISTRY` — tutto il layer `proxy/providers/` è dead code
**File:** backend/app/proxy/providers/registry.py, backend/app/proxy/manager.py

Il `ProxyManager` non importa né usa mai `PROVIDER_REGISTRY`. Costruisce i parametri litellm direttamente dal database (colonne `litellm_prefix`, `api_base_url`). Gli 11 file in `proxy/providers/` (anthropic.py, gemini.py, openai.py, ecc.) **non vengono mai chiamati**.

---

### [M-2] Collisione in `model_to_key_id` → log attribuiti alla chiave sbagliata
**File:** backend/app/proxy/manager.py

```python
model_to_key_id[litellm_model_str] = api_key.id  # ← sovrascrittura silente
```

Se due assignment diversi (due `api_key_id` diversi) producono lo stesso `litellm_model_str` (stesso provider + stesso modello), il secondo sovrascrive il primo. Il log finirà per attribuire il costo alla chiave sbagliata, distorcendo le statistiche.

---

### [M-3] `stats/by-provider` — richieste con `api_key_id=NULL` non contate
**File:** backend/app/api/stats.py

```python
.join(ApiKey, RequestLog.api_key_id == ApiKey.id)       # INNER JOIN
.join(Provider, ApiKey.provider_id == Provider.id)       # INNER JOIN
```

I log dove `api_key_id IS NULL` (possibile quando `actual_model` non corrisponde a nessuna entry di `model_to_key_id`) vengono esclusi dalla query. Le statistiche per provider sono potenzialmente sottostimate.

---

### [M-4] Bug timezone nel reset del budget giornaliero
**File:** backend/app/proxy/manager.py

```python
today_start = datetime.combine(
    date.today(), datetime.min.time()    # ← usa timezone locale del server
).replace(tzinfo=timezone.utc)
```

`date.today()` usa il timezone locale della macchina. Se il server non è in UTC, il reset del budget avviene all'orario sbagliato (offset dipendente dalla timezone del sistema).

**Fix:**
```python
today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
```

---

### [M-5] `VirtualKey.allowed_providers` — colonna definita ma mai letta
**File:** backend/app/models/virtual_key.py, backend/app/proxy/manager.py

Il campo `allowed_providers` esiste nel modello DB ma il proxy non lo legge mai. Non è presente neanche nella schema Pydantic né nell'API frontend. È un vincolo di sicurezza non funzionante.

---

### [M-6] `RequestLog.protocol` hardcoded a `"openai"` per tutti i protocolli
**File:** backend/app/proxy/manager.py

```python
db.add(RequestLog(
    ...
    protocol="openai",   # ← anche per Anthropic e Gemini
))
```

Le chiamate `/anthropic/v1/messages` e `/gemini/v1/generateContent` vengono loggate con `protocol="openai"`, rendendo inutile il campo per filtri e analisi.

---

### [M-7] `_get_fernet()` crea un'istanza Fernet ad ogni chiamata
**File:** backend/app/crypto.py

```python
def _get_fernet() -> Fernet:
    return Fernet(settings.FERNET_KEY.encode())   # ← oggetto ricreato ogni volta
```

`Fernet()` deriva una chiave di cifratura internamente ad ogni istanziazione. Con molte chiamate concorrenti (ogni decrypt durante il routing) questo è uno spreco misurabile. Dovrebbe essere un singleton a livello di modulo.

---

### [M-8] `seed_default_models` non fa rispettare l'unicità di `is_default=True`
**File:** backend/app/seeds/providers.py, backend/app/proxy/manager.py

Il commento dice "solo uno `is_default=True` per provider è enforced a livello applicativo" ma non esiste tale enforcement. `_get_default_model` usa `db.scalar()` che restituisce uno dei valori arbitrariamente se ce ne sono più di uno. Non c'è un `UniqueConstraint` nel DB né una validazione al seed.

---

## BASSO

---

### [L-1] `_anthropic_to_openai` scarta parametri importanti
**File:** backend/app/proxy/protocols.py

La conversione Anthropic → OpenAI ignora silenziosamente: `top_k`, `top_p`, `stop_sequences`, `tools`, `tool_choice`, `metadata`, `stream`. Un client che usa tool use via `/anthropic/v1/messages` non otterrà mai i tool results.

---

### [L-2] `_gemini_to_openai` ignora `systemInstruction`
**File:** backend/app/proxy/protocols.py

Il campo Gemini `systemInstruction` non viene convertito a messaggio di sistema OpenAI. Le istruzioni di sistema vengono silenziosamente perse.

---

### [L-3] WebSocket `close()` prima di `accept()` — comportamento ASGI non definito
**File:** backend/app/websocket.py

```python
if not token:
    await websocket.close(code=_WS_CLOSE_UNAUTHORIZED)
    return
```

Chiamare `close()` prima di `accept()` non è garantito dallo standard ASGI/WebSocket. In alcuni transport il close code `4001` potrebbe non raggiungere il client. Il pattern corretto è `accept()` seguito da `close()`.

---

## Riepilogo

| Severity | Count | Aree principali |
|----------|-------|-----------------|
| CRITICO  | 2 | WS auth, streaming no-log |
| ALTO     | 5 | model_preference mismatch, auth error cascade, Cloudflare URL, no rate limit, localStorage |
| MEDIO    | 8 | dead code, stat bugs, timezone, protocol log, Fernet, allowed_providers |
| BASSO    | 3 | protocol conversion, system instruction, WS accept |

**Le due priorità assolute** sono [C-1] (la Dashboard è rotta) e [C-2] (il budget giornaliero non funziona per client streaming). [H-1] blocca un'intera feature UI già costruita.

Created 2 todos