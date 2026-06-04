# APEX GATE — Planning e Task List

**Legenda**: `[ ]` = da fare · `[x]` = completato · `[~]` = in corso · `[!]` = bloccato

---

## Phase 1 — Foundation

> Obiettivo: backend avviabile con auth funzionante, DB inizializzato, Docker Compose base.

### 1.1 Scaffolding struttura

- [ ] Creare directory `apex-gate/backend/`
- [ ] Creare directory `apex-gate/frontend/` (solo placeholder)
- [ ] Creare `apex-gate/backend/requirements.txt` con tutte le dipendenze (vedi `docs/backend.md` sezione Dependencies)
- [ ] Creare `apex-gate/backend/pyproject.toml`
- [ ] Creare `apex-gate/backend/.env.example` (vedi `docs/deployment.md` sezione Environment Variables)
- [ ] Creare `apex-gate/backend/.gitignore`

### 1.2 Configurazione e database

- [ ] Creare `apex-gate/backend/app/__init__.py`
- [ ] Creare `apex-gate/backend/app/config.py`
  - Usa `pydantic-settings`
  - Campi: `DATABASE_URL`, `AUTH_DATABASE_URL`, `SECRET_KEY`, `FERNET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `PROXY_HOST`, `PROXY_PORT`
  - Default `DATABASE_URL=sqlite+aiosqlite:///./apex_gate.db`
  - Default `AUTH_DATABASE_URL=sqlite+aiosqlite:///./apex_gate_auth.db`
- [ ] Creare `apex-gate/backend/app/database.py` (App DB: engine asincrono, `get_session` dependency)
- [ ] Creare `apex-gate/backend/alembic.ini`
- [ ] Creare `apex-gate/backend/alembic/env.py` (importa tutti i models)
- [ ] Creare `apex-gate/backend/alembic/versions/` (directory vuota)

### 1.3 Crypto module

- [ ] Creare `apex-gate/backend/app/crypto.py`
  - `encrypt_key(plaintext: str) -> str` — Fernet encrypt, usa `FERNET_KEY` da config
  - `decrypt_key(ciphertext: str) -> str` — Fernet decrypt
  - `mask_key(plaintext: str) -> str` — ritorna `sk-...xxxx` (primi 3 + ultimi 4 chars)
  - `generate_virtual_key() -> tuple[str, str]` — genera `apg-<random32>`, ritorna `(plaintext, sha256_hash)`
- [ ] Creare unit test `apex-gate/backend/tests/test_crypto.py`

### 1.4 Auth module (isolato)

- [ ] Creare `apex-gate/backend/app/auth/__init__.py`
- [ ] Creare `apex-gate/backend/app/auth/database.py`
  - Engine asincrono separato che legge `AUTH_DATABASE_URL`
  - `get_auth_session` dependency
- [ ] Creare `apex-gate/backend/app/auth/models.py`
  - `User`: id (UUID), username, email, hashed_password, is_active, is_admin, created_at, updated_at
  - `RefreshToken`: id (UUID), user_id, token_hash, expires_at, revoked, created_at
- [ ] Creare `apex-gate/backend/app/auth/schemas.py`
  - `LoginRequest`, `RegisterRequest`, `TokenResponse`, `RefreshRequest`, `UserResponse`, `UserUpdate`
- [ ] Creare `apex-gate/backend/app/auth/service.py`
  - `hash_password(password: str) -> str` — bcrypt cost 12
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(user_id: str) -> str` — JWT, 15 min
  - `create_refresh_token(user_id: str, db) -> str` — 30 giorni, hash in DB
  - `verify_access_token(token: str) -> dict` — raises HTTPException 401 se invalido
  - `rotate_refresh_token(old_token: str, db) -> tuple[str, str]` — revoca vecchio, crea nuovo
- [ ] Creare `apex-gate/backend/app/auth/deps.py`
  - `get_current_user` — FastAPI dependency, legge Bearer token, ritorna User
  - `require_admin` — come sopra ma verifica `is_admin=True`
- [ ] Creare `apex-gate/backend/app/auth/router.py`
  - `POST /auth/register` — solo se `is_admin` o primo utente del sistema
  - `POST /auth/login` — ritorna access + refresh token
  - `POST /auth/refresh` — rinnova access token
  - `POST /auth/logout` — revoca refresh token
  - `GET  /auth/me` — info utente corrente
- [ ] Creare migration Alembic per tabelle `users` e `refresh_tokens`
- [ ] Creare integration test `apex-gate/backend/tests/test_auth.py`

### 1.5 App models (SQLAlchemy)

- [ ] Creare `apex-gate/backend/app/models/__init__.py`
- [ ] Creare `apex-gate/backend/app/models/provider.py` (tabella `providers`)
- [ ] Creare `apex-gate/backend/app/models/api_key.py` (tabella `api_keys`)
- [ ] Creare `apex-gate/backend/app/models/virtual_key.py` (tabella `virtual_keys`)
- [ ] Creare `apex-gate/backend/app/models/virtual_key_assignment.py` (tabella `virtual_key_assignments`)
- [ ] Creare `apex-gate/backend/app/models/model_catalog.py` (tabella `model_catalog`)
- [ ] Creare `apex-gate/backend/app/models/request_log.py` (tabella `request_logs`)
- [ ] Creare `apex-gate/backend/app/models/exhaustion_state.py` (tabella `exhaustion_state`)
- [ ] Creare migration Alembic per tutte le tabelle app

### 1.6 Seed provider catalog

- [ ] Creare `apex-gate/backend/app/seeds/__init__.py`
- [ ] Creare `apex-gate/backend/app/seeds/providers.py`
  - Seed dei 14 provider definiti in `docs/providers.md`
  - Funzione `seed_providers(session)` — idempotente (upsert by slug)
  - Chiamata al primo avvio nel lifespan FastAPI se tabella `providers` è vuota

### 1.7 Main app

- [ ] Creare `apex-gate/backend/app/main.py`
  - FastAPI app con lifespan
  - Nel lifespan: init DB, seed providers, avvia scheduler
  - Include routers: auth, api (placeholder), proxy (placeholder)
  - Endpoint `GET /health`
  - CORS configurato (origine: `http://localhost:5173` in dev)
- [ ] Creare `apex-gate/backend/Dockerfile`
- [ ] Creare `apex-gate/docker-compose.yml` (solo backend + volume per SQLite)

### 1.8 Verifica Phase 1

- [ ] `docker-compose up` avvia il backend senza errori
- [ ] `POST /auth/login` funziona con utente admin creato via script
- [ ] `GET /health` risponde `200 OK`
- [ ] DB contiene i 14 provider seedati
- [ ] Migration Alembic applicata correttamente

---

## Phase 2 — Proxy Engine

> Obiettivo: il proxy funziona, instrada le richieste, logga i risultati, gestisce il fallback.

### 2.1 Provider base

- [ ] Creare `apex-gate/backend/app/proxy/providers/__init__.py`
- [ ] Creare `apex-gate/backend/app/proxy/providers/base.py`
  - `BaseProvider` ABC con `name`, `litellm_prefix`, `get_litellm_params(api_key: str, model_id: str) -> dict`
- [ ] Creare `apex-gate/backend/app/proxy/providers/nvidia.py`
- [ ] Creare `apex-gate/backend/app/proxy/providers/openrouter.py`
- [ ] Creare `apex-gate/backend/app/proxy/providers/openai.py`
- [ ] Creare `apex-gate/backend/app/proxy/providers/anthropic.py`
- [ ] Creare `apex-gate/backend/app/proxy/providers/gemini.py`
- [ ] Creare `apex-gate/backend/app/proxy/providers/groq.py`
- [ ] Creare `apex-gate/backend/app/proxy/providers/ollama.py`
- [ ] Creare `apex-gate/backend/app/proxy/providers/registry.py` — mappa `slug → BaseProvider instance`

### 2.2 ProviderManager (DB-backed)

- [ ] Creare `apex-gate/backend/app/proxy/manager.py`
  - `ProviderManager` class
  - `get_available_models(user_id, virtual_key) -> list[ModelInfo]` — ordinate per priorità, escluse exhausted
  - `call_with_fallback(messages, user_id, virtual_key_id, **kwargs) -> LLMResponse`
    - Loop su modelli disponibili
    - Su `RateLimitError` → chiama `mark_exhausted(api_key_id, reason='rate_limit', backoff_seconds)`
    - Su `AuthenticationError` → disabilita chiave, notifica
    - Su budget exceeded → `mark_exhausted(api_key_id, reason='budget_daily')`
    - Logga ogni tentativo in `request_logs`
  - `mark_exhausted(api_key_id, reason, backoff_seconds)`
  - `reset_expired_exhaustions()` — chiamato ogni minuto dallo scheduler

### 2.3 Protocol adapters

- [ ] Creare `apex-gate/backend/app/proxy/protocols.py`
  - `normalize_to_openai(request_body: dict, protocol: str) -> dict` — converte Anthropic/Gemini → formato interno
  - `format_response(litellm_response, protocol: str) -> dict` — converte risposta → formato richiesto dal client

### 2.4 Proxy router

- [ ] Creare `apex-gate/backend/app/proxy/router.py`
  - `POST /v1/chat/completions` (OpenAI compatibile, alias)
  - `POST /openai/v1/chat/completions`
  - `POST /anthropic/v1/messages`
  - `POST /gemini/v1/generateContent`
  - `GET  /v1/models` — lista modelli attivi non-esauriti
  - Autenticazione via virtual key (header `Authorization: Bearer apg-xxxx`)
  - Supporto streaming (SSE) per tutti i formati

### 2.5 Cost tracking e logging

- [ ] Integrare `litellm.completion_cost()` per calcolo costo USD per chiamata
- [ ] Budget check pre-call (verifica budget giornaliero non superato)
- [ ] Log ogni request in `request_logs` (success, rate_limited, error, all_exhausted)

### 2.6 WebSocket status

- [ ] Creare `apex-gate/backend/app/websocket.py`
  - `WS /ws/status`
  - Broadcast ogni 5s: stato di ogni provider (active_models, exhausted_models, total_calls_today)
  - Autenticazione via token in query param (`?token=<access_token>`)

### 2.7 Verifica Phase 2

- [ ] `POST /v1/chat/completions` con virtual key valida → risposta LLM
- [ ] Su rate limit simulato → fallback automatico al modello successivo
- [ ] Log salvato in `request_logs` per ogni chiamata
- [ ] `GET /v1/models` → lista modelli
- [ ] WebSocket `/ws/status` → aggiornamenti live

---

## Phase 3 — REST API

> Obiettivo: tutti gli endpoint di gestione funzionanti e testati.

### 3.1 API Keys

- [ ] Creare `apex-gate/backend/app/api/keys.py`
  - `GET    /api/v1/keys` — lista chiavi utente (key_masked, no plaintext)
  - `POST   /api/v1/keys` — crea chiave (riceve plaintext, salva encrypted, ritorna masked)
  - `GET    /api/v1/keys/{id}` — dettaglio chiave
  - `PATCH  /api/v1/keys/{id}` — aggiorna (nome, limiti, priority, enabled)
  - `DELETE /api/v1/keys/{id}` — elimina
  - `POST   /api/v1/keys/{id}/test` — verifica chiave (chiama API provider con modello leggero)

### 3.2 Virtual Keys

- [ ] Creare `apex-gate/backend/app/api/virtual_keys.py`
  - `GET    /api/v1/virtual-keys`
  - `POST   /api/v1/virtual-keys` — genera `apg-xxxx`, salva hash, ritorna plaintext UNA sola volta
  - `GET    /api/v1/virtual-keys/{id}`
  - `PATCH  /api/v1/virtual-keys/{id}` — aggiorna nome/budget/enabled
  - `DELETE /api/v1/virtual-keys/{id}`
  - `POST   /api/v1/virtual-keys/{id}/rotate` — revoca vecchia, genera nuova, ritorna plaintext UNA sola volta
  - `GET    /api/v1/virtual-keys/{id}/assignments` — lista assignment (api_key_id + priority)
  - `POST   /api/v1/virtual-keys/{id}/assignments` — aggiunge assignment `{api_key_id, priority}`
  - `PATCH  /api/v1/virtual-keys/{id}/assignments/{aid}` — modifica priority
  - `DELETE /api/v1/virtual-keys/{id}/assignments/{aid}` — rimuove assignment

### 3.3 Provider catalog

- [ ] Creare `apex-gate/backend/app/api/providers.py`
  - `GET /api/v1/providers` — lista provider con conteggio chiavi utente per provider
  - `GET /api/v1/providers/{slug}` — dettaglio provider
  - `GET /api/v1/providers/{slug}/models` — modelli del provider (dal catalog)

### 3.4 Model catalog

- [ ] Creare `apex-gate/backend/app/api/models_api.py`
  - `GET  /api/v1/models` — tutti i modelli, query params: `provider`, `tier`, `vision`, `tools`, `active`
  - `POST /api/v1/models/refresh` — trigger discovery manuale (admin o utente con chiave del provider)

### 3.5 Logs

- [ ] Creare `apex-gate/backend/app/api/logs.py`
  - `GET /api/v1/logs` — paginato (limit/offset), filtri: `provider`, `status`, `virtual_key_id`, `date_from`, `date_to`

### 3.6 Stats

- [ ] Creare `apex-gate/backend/app/api/stats.py`
  - `GET /api/v1/stats/overview` — totali (calls_today, tokens_today, cost_today, active_providers)
  - `GET /api/v1/stats/by-provider` — breakdown per provider (ultimi N giorni)
  - `GET /api/v1/stats/by-model` — breakdown per modello
  - `GET /api/v1/stats/by-day` — serie temporale chiamate/costo per giorno (ultimi 30 giorni)
  - `GET /api/v1/stats/costs` — solo per chiavi paid, breakdown costo per chiave

### 3.7 Admin

- [ ] Creare `apex-gate/backend/app/api/admin.py`
  - `GET    /api/v1/admin/users`
  - `POST   /api/v1/admin/users`
  - `PATCH  /api/v1/admin/users/{id}` — is_active, is_admin
  - `DELETE /api/v1/admin/users/{id}`
  - `POST   /api/v1/admin/reset-exhaustions` — reset tutti gli exhaustion state

### 3.8 Verifica Phase 3

- [ ] Tutti gli endpoint CRUD funzionanti
- [ ] Chiave creata → recuperata masked → mai plaintext in GET
- [ ] Virtual key creata → plaintext visibile solo al momento della creazione
- [ ] Stats aggregano correttamente da `request_logs`

---

## Phase 4 — Discovery System

> Obiettivo: scraper automatici aggiornano il model catalog in background.

### 4.1 Base scraper

- [ ] Creare `apex-gate/backend/app/discovery/__init__.py`
- [ ] Creare `apex-gate/backend/app/discovery/base.py`
  - `AbstractScraper` ABC con `provider_slug`, `scrape() -> list[ModelData]`
  - `ModelData` dataclass: model_id, display_name, context_window, tier, cost_input, cost_output, supports_vision, supports_tools

### 4.2 Scraper per provider

- [ ] Creare `apex-gate/backend/app/discovery/nvidia.py`
  - Chiama `https://integrate.api.nvidia.com/v1/models`
  - Filtra modelli di tipo `completion` o `chat`
  - Non richiede autenticazione per la lista pubblica
- [ ] Creare `apex-gate/backend/app/discovery/openrouter.py`
  - Chiama `https://openrouter.ai/api/v1/models`
  - Filtra modelli con `pricing.prompt == "0"` per free tier
  - Estrae context_window, pricing, capabilities
- [ ] Creare `apex-gate/backend/app/discovery/groq.py`
  - Chiama `https://api.groq.com/openai/v1/models` (richiede API key)
  - Solo se l'utente ha una chiave Groq configurata
- [ ] Creare `apex-gate/backend/app/discovery/gemini.py`
  - Chiama Google AI API per lista modelli
  - Distingue free e paid tier

### 4.3 Discovery service

- [ ] Creare `apex-gate/backend/app/discovery/service.py`
  - `run_discovery(provider_slug: str | None = None, db)` — esegue scraper(s), upsert in `model_catalog`
  - `deactivate_missing_models(provider_slug, discovered_ids, db)` — marca `is_active=False` modelli non più trovati
  - Log risultati: nuovi modelli aggiunti, rimossi, invariati

### 4.4 Scheduler

- [ ] Creare `apex-gate/backend/app/scheduler.py`
  - APScheduler con `AsyncIOScheduler`
  - Job `discovery_job`: ogni 6 ore, chiama `run_discovery()`
  - Job `reset_exhaustions_job`: ogni 60 secondi, chiama `manager.reset_expired_exhaustions()`
  - Job `cleanup_old_logs_job`: ogni 24 ore, elimina `request_logs` più vecchi di 90 giorni
  - Avviato nel lifespan FastAPI

### 4.5 Verifica Phase 4

- [ ] Discovery manuale via `POST /api/v1/models/refresh` aggiorna il catalog
- [ ] Discovery schedulata parte automaticamente all'avvio
- [ ] Modelli non più disponibili vengono marcati `is_active=False`

---

## Phase 5 — Frontend

> Obiettivo: dashboard web completa, funzionale, ben stilizzata.

### 5.1 Scaffolding

- [ ] Creare app React con Vite: `pnpm create vite frontend -- --template react-ts`
- [ ] Installare dipendenze: `react-router-dom`, `@tanstack/react-query`, `axios`, `zustand`, `recharts`
- [ ] Configurare `vite.config.ts` (proxy `/api` → `http://localhost:8000`, alias `@/`)
- [ ] Configurare `tsconfig.json` (strict: true, paths)
- [ ] Creare `src/styles/tokens.css` (design tokens — vedi `docs/frontend.md`)
- [ ] Creare `src/styles/reset.css`
- [ ] Creare `src/styles/global.css`

### 5.2 Auth layer

- [ ] Creare `src/api/client.ts` (axios instance con interceptor per JWT + refresh automatico)
- [ ] Creare `src/store/auth.ts` (Zustand: user, accessToken, login, logout)
- [ ] Creare `src/pages/Login/Login.tsx` + `Login.module.css`
- [ ] Creare `src/components/ProtectedRoute/ProtectedRoute.tsx`
- [ ] Creare `src/App.tsx` con React Router (routes protette e pubblica `/login`)

### 5.3 Layout

- [ ] Creare `src/components/Layout/Layout.tsx` + `Layout.module.css`
- [ ] Creare `src/components/Sidebar/Sidebar.tsx` + `Sidebar.module.css`
- [ ] Creare `src/components/TopBar/TopBar.tsx` + `TopBar.module.css`
- [ ] Creare `src/components/StatusBadge/StatusBadge.tsx` + `.module.css` (green/yellow/red)
- [ ] Creare `src/components/Modal/Modal.tsx` + `.module.css`
- [ ] Creare `src/components/Toast/` (notifiche)
- [ ] Creare `src/components/Table/Table.tsx` (tabella generica con sorting/paginazione)

### 5.4 Dashboard page

- [ ] Creare `src/pages/Dashboard/Dashboard.tsx`
- [ ] Widget: chiamate ultime 24h (numero + trend)
- [ ] Widget: provider status (card verde/giallo/rosso per ogni provider con chiave configurata)
- [ ] Widget: costo oggi (solo paid keys)
- [ ] Grafico: line chart chiamate per ora (ultime 24h)
- [ ] Tabella: top 5 modelli usati oggi

### 5.5 Keys page

- [ ] Creare `src/pages/Keys/Keys.tsx`
- [ ] Tabella chiavi con: nome, provider logo, tier badge (FREE/PAID), stato, RPM/RPD, azioni
- [ ] Drawer/Modal "Aggiungi chiave":
  - Seleziona provider da dropdown (con logo)
  - Campo nome
  - Campo API key (input password, mai ri-mostrata)
  - Seleziona tier (FREE / PAID)
  - Rate limits: RPM, RPD (opzionale — rispecchiano i limiti reali del provider)
  - Budget: daily USD, monthly USD (solo tier PAID)
- [ ] Toggle enable/disable in-table
- [ ] Tasto "Test key" con feedback (✓ funziona / ✗ errore)
- [ ] Delete con conferma

### 5.6 Virtual Keys page

- [ ] Creare `src/pages/VirtualKeys/VirtualKeys.tsx`
- [ ] Lista virtual keys: nome, key mascherata (`apg-xxxx...xxxx`), budget, API keys assegnate, stato
- [ ] Modale "Crea": nome, budget token giornaliero
- [ ] Tasto "Copia chiave" (visibile solo al momento della creazione, poi mascherata)
- [ ] Tasto "Rotate" con warning "la vecchia chiave smetterà di funzionare"
- [ ] Sezione "Assignments": lista API key assegnate con priority (1–99)
  - Aggiungere assignment: seleziona API key da quelle dell'utente + imposta priority
  - Modificare priority di un assignment esistente
  - Rimuovere assignment con conferma

### 5.7 Models page

- [ ] Creare `src/pages/Models/Models.tsx`
- [ ] Tabella modelli: nome, provider logo, tier badge, contesto, costo input/output, vision, tools, ultimo aggiornamento
- [ ] Filtri: provider (multi-select), tier, vision, tools, solo attivi
- [ ] Badge "NEW" per modelli aggiunti nelle ultime 24h
- [ ] Tasto "Aggiorna ora" (trigger discovery manuale)
- [ ] Indicatore "Ultimo aggiornamento: X ore fa"

### 5.8 Logs page

- [ ] Creare `src/pages/Logs/Logs.tsx`
- [ ] Tabella paginata: timestamp, virtual key (mascherata), modello, provider, token in/out, costo, latenza, status badge
- [ ] Filtri: data range, provider, status, virtual key
- [ ] Export CSV

### 5.9 Stats page

- [ ] Creare `src/pages/Stats/Stats.tsx`
- [ ] Line chart: chiamate per giorno (ultimi 30 giorni)
- [ ] Pie chart: distribuzione per provider
- [ ] Bar chart: latenza media per modello (top 10)
- [ ] Area chart: costo cumulativo (se paid keys presenti)
- [ ] Tabella summary: per provider (chiamate, successi, rate-limit, costo)

### 5.10 Settings page

- [ ] Creare `src/pages/Settings/Settings.tsx`
- [ ] Sezione "Profilo": cambia username, email, password
- [ ] Sezione "Discovery": intervallo scheduler (ogni N ore), provider abilitati alla discovery
- [ ] Sezione "Sicurezza": lista refresh token attivi con revoca
- [ ] Sezione "Dati": export config JSON (senza segreti), import config

### 5.11 Admin page

- [ ] Creare `src/pages/Admin/Admin.tsx` (solo utenti `is_admin`)
- [ ] Tabella utenti: username, email, is_active, is_admin, created_at
- [ ] Crea utente (username, email, password, is_admin)
- [ ] Toggle is_active, promuovi/rimuovi admin
- [ ] Tasto "Reset tutti gli exhaustion" con conferma

### 5.12 WebSocket live status

- [ ] Creare `src/hooks/useProviderStatus.ts`
- [ ] Connessione WS a `/ws/status` con reconnect automatico
- [ ] Aggiorna stato provider nel Zustand store ogni 5s
- [ ] Sidebar mostra pallino live per ogni provider

### 5.13 Verifica Phase 5

- [ ] Login funziona, JWT salvato, refresh automatico
- [ ] Navigazione tra tutte le pagine
- [ ] CRUD chiavi completo end-to-end
- [ ] Virtual key creata → usabile nel proxy
- [ ] Dashboard mostra dati reali
- [ ] WebSocket aggiorna status in tempo reale

---

## Phase 6 — Docker e Deploy

> Obiettivo: `docker-compose up` porta su tutto in locale; config pronta per produzione.

### 6.1 Docker locale

- [ ] Creare `apex-gate/frontend/Dockerfile` (build stage + nginx stage)
- [ ] Creare `apex-gate/frontend/nginx.conf` (serve SPA, proxy `/api` e `/ws` al backend)
- [ ] Aggiornare `apex-gate/docker-compose.yml` (backend + frontend)
- [ ] Verificare CORS, WebSocket, hot-reload in development

### 6.2 Docker produzione

- [ ] Creare `apex-gate/docker-compose.prod.yml` (backend + frontend + PostgreSQL)
- [ ] Creare `apex-gate/backend/Dockerfile` ottimizzato (multi-stage, non-root user)
- [ ] Creare `apex-gate/.env.example` completo (vedi `docs/deployment.md`)
- [ ] Health check per backend (`/health`) e frontend (nginx status)

### 6.3 Migrazioni produzione

- [ ] Script `apex-gate/backend/scripts/init_db.sh` (applica migration + seed providers)
- [ ] Script `apex-gate/backend/scripts/create_admin.py` (crea primo utente admin interattivamente)
- [ ] Alembic `env.py` configurato per leggere `DATABASE_URL` e `AUTH_DATABASE_URL` da env

### 6.4 Verifica Phase 6

- [ ] `docker-compose up` avvia tutto senza errori
- [ ] Frontend accessibile su `http://localhost:3000`
- [ ] Backend accessibile su `http://localhost:8000`
- [ ] `docker-compose.prod.yml` avvia con PostgreSQL

---

## Backlog / Future Features (post v1)

- [ ] Notifiche email/webhook quando provider esaurito
- [ ] Model routing avanzato (instrada verso modello specifico per tipo di richiesta)
- [ ] Caching semantico risposte (hash del prompt → cache hit)
- [ ] Fine-tuning model preference per utente
- [ ] Metriche Prometheus + Grafana dashboard
- [ ] Rate limiting per virtual key (non solo budget token)
- [ ] Multi-tenant namespace isolation
- [ ] API key rotation automatica
- [ ] Integrazione con secret manager (Vault, AWS Secrets Manager)
