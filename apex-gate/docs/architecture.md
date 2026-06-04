# APEX GATE — Architecture Reference

Documento di riferimento per agenti e sviluppatori. Descrive la struttura completa del sistema: stack, directory, endpoint, auth flow, scheduler, configurazione.

---

## Stack tecnologico

### Backend

| Componente | Tecnologia | Versione |
|---|---|---|
| Linguaggio | Python | 3.12+ |
| Web framework | FastAPI | 0.115+ |
| ASGI server | Uvicorn | 0.34+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Migrations | Alembic | 1.13+ |
| Driver SQLite | aiosqlite | 0.20+ |
| Driver PostgreSQL | asyncpg | 0.30+ |
| Config | pydantic-settings | 2.x |
| Auth | PyJWT + bcrypt | jwt 2.x, bcrypt 4.x |
| Encryption | cryptography (Fernet) | 43+ |
| LLM proxy | litellm (Router) | 1.40+ |
| HTTP client | httpx | 0.27+ |
| Scheduler | APScheduler | 3.x |

### Frontend

| Componente | Tecnologia |
|---|---|
| Framework | React 19 |
| Build tool | Vite |
| Linguaggio | TypeScript |
| Stile | CSS Modules |
| HTTP client | Axios |

---

## Directory tree completo

### Backend

```
apex-gate/backend/
├── alembic/
│   ├── versions/          ← migration files
│   ├── env.py             ← dual-DB migration setup
│   └── script.py.mako
├── app/
│   ├── main.py            ← FastAPI app + router registration + lifespan
│   ├── config.py          ← pydantic-settings (Settings class)
│   ├── database.py        ← App DB engine + get_session dependency
│   ├── crypto.py          ← Fernet encrypt/decrypt + generate_virtual_key + mask_key
│   ├── scheduler.py       ← APScheduler jobs (discovery, exhaustion reset, log cleanup)
│   ├── websocket.py       ← WebSocket /ws/status handler
│   ├── auth/
│   │   ├── database.py    ← Auth DB engine separato (AUTH_DATABASE_URL)
│   │   ├── models.py      ← SQLAlchemy: User, RefreshToken
│   │   ├── schemas.py     ← Pydantic: LoginRequest, TokenResponse, UserResponse
│   │   ├── service.py     ← hash_password, verify_password, create_tokens, rotate_refresh
│   │   ├── router.py      ← /auth/* endpoints
│   │   └── deps.py        ← get_current_user FastAPI dependency
│   ├── api/
│   │   ├── providers.py   ← GET /api/v1/providers
│   │   ├── keys.py        ← CRUD /api/v1/keys
│   │   ├── virtual_keys.py← CRUD /api/v1/virtual-keys + rotate
│   │   ├── models_api.py  ← GET /api/v1/models + POST /refresh
│   │   ├── logs.py        ← GET /api/v1/logs
│   │   ├── stats.py       ← GET /api/v1/stats/*
│   │   ├── admin.py       ← /api/v1/admin/* (is_admin required)
│   │   └── schemas/
│   │       ├── key_schemas.py         ← ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse
│   │       └── virtual_key_schemas.py ← VirtualKeyCreate, VirtualKeyResponse, KeyAssignment
│   ├── proxy/
│   │   ├── router.py      ← proxy endpoints (/v1, /openai, /anthropic, /gemini)
│   │   ├── manager.py     ← ProxyManager.call_with_router() — LiteLLM Router logic
│   │   └── protocols.py   ← normalize_request(), format_response() per protocollo
│   ├── discovery/
│   │   ├── base.py        ← AbstractScraper
│   │   ├── service.py     ← run_discovery() — chiama tutti gli scraper
│   │   ├── nvidia.py
│   │   ├── openrouter.py
│   │   ├── groq.py
│   │   └── gemini.py
│   ├── models/
│   │   ├── __init__.py    ← Base, _uuid, _now helpers
│   │   ├── provider.py    ← Provider SQLAlchemy model
│   │   ├── api_key.py     ← ApiKey SQLAlchemy model
│   │   ├── virtual_key.py ← VirtualKey SQLAlchemy model
│   │   ├── virtual_key_assignment.py ← VirtualKeyAssignment model
│   │   ├── model_catalog.py ← ModelCatalog model (include is_default)
│   │   ├── request_log.py ← RequestLog model
│   │   └── exhaustion_state.py ← ExhaustionState model
│   └── seeds/
│       └── providers.py   ← seed providers + model_catalog defaults
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_crypto.py
│   ├── test_proxy.py
│   └── test_api_keys.py
├── requirements.txt
├── alembic.ini
├── Dockerfile
└── .env.example
```

### Frontend

```
apex-gate/frontend/
├── src/
│   ├── main.tsx           ← entrypoint React 19
│   ├── App.tsx            ← routing principale
│   ├── api/
│   │   ├── client.ts      ← Axios instance + interceptors
│   │   ├── auth.ts        ← login, refresh, logout
│   │   ├── keys.ts        ← CRUD API keys
│   │   ├── virtualKeys.ts ← CRUD virtual keys + rotate
│   │   ├── providers.ts   ← GET providers + models
│   │   ├── logs.ts        ← GET logs
│   │   └── stats.ts       ← GET stats
│   ├── components/
│   │   ├── ApiKeyList/
│   │   ├── VirtualKeyList/
│   │   ├── ProviderLogo/
│   │   ├── StatusBadge/
│   │   └── ui/            ← Button, Modal, Table, etc.
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── KeysPage.tsx
│   │   ├── VirtualKeysPage.tsx
│   │   └── LogsPage.tsx
│   └── hooks/
│       ├── useAuth.ts
│       └── useWebSocket.ts
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

---

## Dual database

| DB | Env var | File SQLite dev | Tabelle |
|---|---|---|---|
| Auth DB | `AUTH_DATABASE_URL` | `apex_gate_auth.db` | `users`, `refresh_tokens` |
| App DB | `DATABASE_URL` | `apex_gate.db` | `providers`, `api_keys`, `virtual_keys`, `virtual_key_assignments`, `model_catalog`, `request_logs`, `exhaustion_state` |

`users.id` è referenziato da `api_keys.user_id` e `virtual_keys.user_id` come cross-DB reference (no FK a livello DB).

---

## Endpoint completi

### Auth (`/auth`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| POST | `/auth/login` | No | `{username, password}` → `{access_token, refresh_token}` |
| POST | `/auth/refresh` | No | Ruota refresh token |
| POST | `/auth/logout` | Bearer | Revoca refresh token |
| GET | `/auth/me` | Bearer | Utente corrente |
| POST | `/auth/register` | Bearer (admin) | Crea nuovo utente |

### API Keys (`/api/v1/keys`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/keys` | Bearer | Lista chiavi (masked) |
| POST | `/api/v1/keys` | Bearer | Crea chiave (Fernet-encrypted) |
| GET | `/api/v1/keys/{id}` | Bearer | Dettaglio |
| PATCH | `/api/v1/keys/{id}` | Bearer | Aggiorna nome/limits/tier/enabled |
| DELETE | `/api/v1/keys/{id}` | Bearer | Elimina |
| POST | `/api/v1/keys/{id}/test` | Bearer | Testa la chiave contro il provider |

### Virtual Keys (`/api/v1/virtual-keys`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/virtual-keys` | Bearer | Lista con assignments |
| POST | `/api/v1/virtual-keys` | Bearer | Crea + ritorna plaintext (una volta sola) |
| GET | `/api/v1/virtual-keys/{id}` | Bearer | Dettaglio con assignments |
| PATCH | `/api/v1/virtual-keys/{id}` | Bearer | Aggiorna nome/budget/enabled/assignments |
| DELETE | `/api/v1/virtual-keys/{id}` | Bearer | Elimina + assignments |
| POST | `/api/v1/virtual-keys/{id}/rotate` | Bearer | Nuova key, plaintext ritornato una volta |

### Provider Catalog (`/api/v1/providers`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/providers` | Bearer | Lista provider |
| GET | `/api/v1/providers/{slug}/models` | Bearer | Modelli del provider |

### Model Catalog (`/api/v1/models`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/models` | Bearer | Lista modelli (filtri: provider, tier, is_default) |
| POST | `/api/v1/models/refresh` | Bearer | Trigger discovery manuale |

### Logs (`/api/v1/logs`)

| Metodo | Path | Query params |
|---|---|---|
| GET | `/api/v1/logs` | `limit`, `offset`, `provider`, `status`, `virtual_key_id`, `date_from`, `date_to` |

### Stats (`/api/v1/stats`)

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/api/v1/stats/overview` | Totali giornalieri |
| GET | `/api/v1/stats/by-provider` | Breakdown per provider |
| GET | `/api/v1/stats/by-model` | Breakdown per modello |
| GET | `/api/v1/stats/by-day` | Serie temporale 30 giorni |
| GET | `/api/v1/stats/costs` | Costo per chiave paid |

### Admin (`/api/v1/admin`) — `is_admin` required

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/api/v1/admin/users` | Lista utenti |
| POST | `/api/v1/admin/users` | Crea utente |
| PATCH | `/api/v1/admin/users/{id}` | Modifica is_active, is_admin |
| DELETE | `/api/v1/admin/users/{id}` | Elimina utente |
| POST | `/api/v1/admin/reset-exhaustions` | Reset tutti exhaustion_state |

### Proxy

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| POST | `/v1/chat/completions` | Virtual Key | OpenAI (alias per /openai) |
| POST | `/openai/v1/chat/completions` | Virtual Key | OpenAI format |
| POST | `/anthropic/v1/messages` | Virtual Key | Anthropic format |
| POST | `/gemini/v1/generateContent` | Virtual Key | Gemini format |
| GET | `/v1/models` | Virtual Key | Lista modelli disponibili per la virtual key |
| GET | `/health` | No | System health check |

### WebSocket

| Path | Auth | Payload |
|---|---|---|
| `/ws/status` | `?token=<access_token>` | Ogni 5s: `{providers: [{slug, active_models, exhausted_models, calls_today}]}` |

---

## Auth flow

```
Login:
  POST /auth/login {username, password}
  → access_token (JWT, 15min) + refresh_token (opaque, 30 giorni)
  → refresh_token salvato come SHA-256 hash in refresh_tokens

Richiesta autenticata:
  Authorization: Bearer <access_token>
  → FastAPI deps.get_current_user() decodifica JWT → User

Rinnovo token:
  POST /auth/refresh {refresh_token}
  → vecchio token revocato (revoked=TRUE)
  → nuovi access_token + refresh_token emessi (rotation)

Proxy auth:
  Authorization: Bearer apg-xxxx
  → SHA-256("apg-xxxx") cercato in virtual_keys
  → nessun JWT coinvolto
```

---

## Scheduler jobs (APScheduler)

| Job | Trigger | Azione |
|---|---|---|
| `discovery_job` | ogni `DISCOVERY_INTERVAL_HOURS` ore (default 6) | `run_discovery()` → aggiorna `model_catalog` |
| `reset_exhaustions_job` | ogni 60 secondi | Elimina `exhaustion_state` con `exhausted_until < NOW()` |
| `cleanup_logs_job` | cron 03:00 ogni notte | Elimina `request_logs` più vecchi di `LOG_RETENTION_DAYS` giorni |

---

## Configurazione (.env)

```env
# Database (SQLite default, PostgreSQL in prod)
DATABASE_URL=sqlite+aiosqlite:///./apex_gate.db
AUTH_DATABASE_URL=sqlite+aiosqlite:///./apex_gate_auth.db

# Security — generare con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SECRET_KEY=<jwt_signing_key>           # REQUIRED
FERNET_KEY=<fernet_key>                # REQUIRED — cifra le API key at-rest

# Token TTL
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Server
PROXY_HOST=0.0.0.0
PROXY_PORT=8000
CORS_ORIGINS=["http://localhost:5173"]

# Scheduler
DISCOVERY_INTERVAL_HOURS=6
LOG_RETENTION_DAYS=90
```

---

## Invarianti di sistema

- `virtual_keys.key_hash` è sempre SHA-256 del plaintext `apg-xxx`. Non si può risalire al plaintext.
- `api_keys.key_encrypted` è sempre Fernet-encrypted. Non è mai esposta in chiaro via API.
- Un solo `model_catalog.is_default=TRUE` per provider per utente (enforced a livello applicativo).
- `virtual_key_assignments.priority` è tra 1 e 99. Valore minore = tentato prima.
- `UNIQUE(virtual_key_id, api_key_id)` in `virtual_key_assignments`: no duplicati.
- `UNIQUE(api_key_id)` in `exhaustion_state`: upsert, non insert multipli per la stessa chiave.
- Il primo utente registrato nel sistema ottiene automaticamente `is_admin=TRUE`.
- I provider sono seed-only: gli utenti normali non possono crearli o modificarli.

---

## Error response format

```json
{
  "detail": "Messaggio leggibile",
  "code": "ERROR_CODE_SNAKE_CASE",
  "timestamp": "2026-05-28T12:00:00Z"
}
```

| HTTP | Significato |
|---|---|
| 400 | Request malformata |
| 401 | Non autenticato / token scaduto |
| 403 | Non autorizzato (es. non admin) |
| 404 | Risorsa non trovata |
| 409 | Conflitto (es. username già esistente) |
| 422 | Validazione Pydantic fallita |
| 429 | Rate limit (tutti i provider esauriti) |
| 503 | Proxy — tutti esauriti, include `next_available_at` |
