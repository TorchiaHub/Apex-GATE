# APEX GATE — Database Schema

## Overview

APEX GATE usa **due database separati**:

| DB | Variabile env | Scopo | Tabelle |
|---|---|---|---|
| **Auth DB** | `AUTH_DATABASE_URL` | Utenti e sessioni | `users`, `refresh_tokens` |
| **App DB** | `DATABASE_URL` | Tutto il resto | `providers`, `api_keys`, `virtual_keys`, `virtual_key_assignments`, `model_catalog`, `request_logs`, `exhaustion_state` |

In sviluppo locale entrambi usano SQLite. In produzione possono essere su host PostgreSQL diversi.

Default valori:
```
DATABASE_URL=sqlite+aiosqlite:///./apex_gate.db
AUTH_DATABASE_URL=sqlite+aiosqlite:///./apex_gate_auth.db
```

---

## Auth DB

### Tabella: `users`

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(50)  UNIQUE NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,     -- bcrypt hash, cost 12
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email    ON users(email);
```

**Note**:
- `hashed_password`: mai salvare in chiaro. Usare `bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))`
- Il primo utente registrato riceve automaticamente `is_admin=TRUE`
- `updated_at` aggiornato da trigger o manualmente su ogni UPDATE

### Tabella: `refresh_tokens`

```sql
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL,    -- SHA-256 del refresh token
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_id    ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
```

**Note**:
- Il refresh token viene mai salvato in chiaro nel DB. Solo il suo SHA-256 hash.
- A ogni refresh: il vecchio token viene marcato `revoked=TRUE`, uno nuovo viene creato (rotation).
- Cleanup periodico: elimina token `revoked=TRUE` o `expires_at < NOW()` più vecchi di 7 giorni.

---

## App DB

### Tabella: `providers`

```sql
CREATE TABLE providers (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                 VARCHAR(50) UNIQUE NOT NULL,  -- 'openai', 'nvidia_nim', 'openrouter'
    name                 VARCHAR(100) NOT NULL,          -- 'OpenAI', 'NVIDIA NIM'
    protocol             VARCHAR(20) NOT NULL,           -- 'openai' | 'anthropic' | 'gemini' | 'ollama' | 'cohere'
    api_base_url         VARCHAR(500),                   -- NULL = usa LiteLLM default
    supports_free_tier   BOOLEAN NOT NULL DEFAULT FALSE,
    litellm_prefix       VARCHAR(50),                    -- 'openai/' | 'anthropic/' | 'nvidia_nim/'
    logo_url             VARCHAR(500),                   -- URL logo SVG/PNG
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order           INTEGER NOT NULL DEFAULT 99,    -- ordine display UI
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Dati seedati**: vedi `docs/providers.md` per l'elenco completo con tutti i campi.
**Questa tabella è read-only per utenti normali.** Solo admin può modificarla.

### Tabella: `api_keys`

```sql
CREATE TABLE api_keys (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL,              -- ref a Auth DB users.id
    provider_id         UUID NOT NULL REFERENCES providers(id),
    name                VARCHAR(100) NOT NULL,       -- nome display, es. "My NVIDIA Key"
    key_encrypted       TEXT NOT NULL,               -- Fernet encrypted, vedi docs/security.md
    tier                VARCHAR(10) NOT NULL DEFAULT 'free',  -- 'free' | 'paid'
    is_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    rate_limit_rpm      INTEGER,                     -- NULL = nessun limite noto
    rate_limit_rpd      INTEGER,                     -- NULL = nessun limite noto
    budget_daily_usd    NUMERIC(10,4),              -- NULL = illimitato (solo paid ha senso)
    budget_monthly_usd  NUMERIC(10,4),              -- NULL = illimitato
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user_id    ON api_keys(user_id);
CREATE INDEX idx_api_keys_provider   ON api_keys(provider_id);
```

**Note**:
- `user_id` referenzia `Auth DB.users.id` (cross-DB reference, non FK a livello DB)
- `key_encrypted`: sempre decriptata al volo solo quando serve per la chiamata proxy. Mai esposta via API.
- Nella risposta API, usare sempre `key_masked` (es. `sk-...x9f2`) calcolato al momento del GET.
- `rate_limit_rpm` e `rate_limit_rpd` rispecchiano i limiti reali del provider per quella chiave. La **priority** non appartiene all'API key ma all'assignment (vedi `virtual_key_assignments`).

### Tabella: `virtual_keys`

```sql
CREATE TABLE virtual_keys (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL,               -- ref a Auth DB users.id
    name                VARCHAR(100) NOT NULL,
    key_hash            VARCHAR(255) UNIQUE NOT NULL, -- SHA-256 di "apg-<random>"
    key_prefix          VARCHAR(20) NOT NULL,          -- "apg-" + primi 8 chars per display
    daily_token_budget  INTEGER,                       -- NULL = illimitato
    is_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_virtual_keys_user_id  ON virtual_keys(user_id);
CREATE INDEX idx_virtual_keys_hash     ON virtual_keys(key_hash);
```

**Note**:
- Il plaintext `apg-<random>` viene ritornato **una sola volta** al momento della creazione.
- Solo l'hash SHA-256 viene salvato. Non è possibile recuperare il plaintext.
- `key_prefix`: usato per display in UI (es. `apg-a1b2c3d4...`).
- Autenticazione proxy: l'utente manda `Authorization: Bearer apg-xxxx`, il proxy calcola SHA-256, cerca in `virtual_keys`.
- Le API key reali da usare per questa virtual key sono definite in `virtual_key_assignments`.

### Tabella: `virtual_key_assignments`

```sql
CREATE TABLE virtual_key_assignments (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    virtual_key_id   UUID NOT NULL REFERENCES virtual_keys(id) ON DELETE CASCADE,
    api_key_id       UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    priority         INTEGER NOT NULL DEFAULT 10,    -- 1 = massima, 99 = minima
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(virtual_key_id, api_key_id)               -- una sola riga per coppia
);

CREATE INDEX idx_vka_virtual_key  ON virtual_key_assignments(virtual_key_id);
CREATE INDEX idx_vka_priority     ON virtual_key_assignments(virtual_key_id, priority);
```

**Note**:
- `VirtualKeyAssignment` è l'entità centrale del sistema di routing: lega una virtual key a un insieme di API key reali, ognuna con la propria priority.
- Il proxy carica tutti gli assignment della virtual key in uso, li ordina per `priority ASC`, e tenta le chiavi in quell'ordine.
- Se una chiave è esaurita (rate limit raggiunto), il proxy passa all'assignment con priority successiva.
- `UNIQUE(virtual_key_id, api_key_id)`: la stessa API key non può essere assegnata due volte alla stessa virtual key.

### Tabella: `model_catalog`

```sql
CREATE TABLE model_catalog (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id             UUID NOT NULL REFERENCES providers(id),
    model_id                VARCHAR(200) NOT NULL,  -- es. 'llama-3.3-70b-versatile' (senza prefix)
    display_name            VARCHAR(200) NOT NULL,
    context_window          INTEGER,
    tier                    VARCHAR(10) NOT NULL DEFAULT 'free',  -- 'free' | 'paid'
    cost_input_per_1m_usd   NUMERIC(10,6),   -- NULL per free tier
    cost_output_per_1m_usd  NUMERIC(10,6),   -- NULL per free tier
    supports_vision         BOOLEAN NOT NULL DEFAULT FALSE,
    supports_tools          BOOLEAN NOT NULL DEFAULT FALSE,
    supports_streaming      BOOLEAN NOT NULL DEFAULT TRUE,
    is_default              BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE = usato in AUTO mode
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    last_discovered_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(provider_id, model_id)
);

CREATE INDEX idx_model_catalog_provider    ON model_catalog(provider_id);
CREATE INDEX idx_model_catalog_tier        ON model_catalog(tier);
CREATE INDEX idx_model_catalog_active      ON model_catalog(is_active);
CREATE INDEX idx_model_catalog_default     ON model_catalog(provider_id, is_default);
```

**Note**:
- Popolata dal discovery system e dal seed iniziale (`app/seeds/providers.py`).
- `model_id` è la parte senza prefix LiteLLM — il nome completo si ottiene con `{provider.litellm_prefix}{model_id}`.
- `is_default=TRUE` indica il modello usato in AUTO mode per quel provider. **Un solo `is_default=TRUE` per provider** — enforced a livello applicativo. Vedere `docs/MODEL_ROUTING.md` per la tabella dei default.
- `is_active=FALSE` significa che il modello non è più disponibile (rimosso dalla discovery).
- Upsert by `(provider_id, model_id)` a ogni discovery run.

### Tabella: `request_logs`

```sql
CREATE TABLE request_logs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL,
    virtual_key_id   UUID REFERENCES virtual_keys(id) ON DELETE SET NULL,
    api_key_id       UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    model_id         VARCHAR(200),
    input_tokens     INTEGER NOT NULL DEFAULT 0,
    output_tokens    INTEGER NOT NULL DEFAULT 0,
    cost_usd         NUMERIC(10,6) NOT NULL DEFAULT 0,
    latency_ms       INTEGER,
    status           VARCHAR(20) NOT NULL,
    -- 'success' | 'rate_limited' | 'budget_exceeded' | 'error' | 'all_exhausted'
    error_message    TEXT,
    protocol         VARCHAR(20),   -- 'openai' | 'anthropic' | 'gemini'
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_request_logs_user_id    ON request_logs(user_id);
CREATE INDEX idx_request_logs_created    ON request_logs(created_at);
CREATE INDEX idx_request_logs_vk         ON request_logs(virtual_key_id);
CREATE INDEX idx_request_logs_api_key    ON request_logs(api_key_id);
CREATE INDEX idx_request_logs_status     ON request_logs(status);
```

**Note**:
- Questa tabella cresce velocemente. Cleanup automatico: eliminare record più vecchi di 90 giorni (scheduler).
- `api_key_id = NULL` quando `status = 'all_exhausted'` (nessuna chiave ha gestito la richiesta).
- `cost_usd` calcolato da `litellm.completion_cost()` — 0 per modelli free.

### Tabella: `exhaustion_state`

```sql
CREATE TABLE exhaustion_state (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id       UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    exhausted_until  TIMESTAMPTZ NOT NULL,
    reason           VARCHAR(30) NOT NULL,
    -- 'rate_limit' | 'budget_daily' | 'budget_monthly' | 'error_429' | 'auth_error'
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(api_key_id)   -- una sola riga per chiave (upsert on conflict)
);

CREATE INDEX idx_exhaustion_until ON exhaustion_state(exhausted_until);
```

**Note**:
- UNIQUE su `api_key_id`: se una chiave già esaurita riceve un altro 429, aggiorna `exhausted_until`.
- Il `ProviderManager` controlla `exhausted_until > NOW()` prima di usare una chiave.
- Il job scheduler `reset_expired_exhaustions` elimina le righe con `exhausted_until < NOW()` ogni 60 secondi.
- Su `auth_error` (401): la chiave viene anche marcata `is_enabled=FALSE` in `api_keys`.

---

## Relazioni

```
Auth DB                    App DB
─────────                  ──────────────────────────────
users.id ──────────────→   api_keys.user_id  (cross-DB, no FK)
         ──────────────→   virtual_keys.user_id
         ──────────────→   request_logs.user_id

App DB relazioni interne:
providers.id ──────────→   api_keys.provider_id
             ──────────→   model_catalog.provider_id
api_keys.id ───────────→   exhaustion_state.api_key_id
            ───────────→   request_logs.api_key_id
            ───────────→   virtual_key_assignments.api_key_id
virtual_keys.id ───────→   request_logs.virtual_key_id
                ───────→   virtual_key_assignments.virtual_key_id
```

---

## SQLAlchemy Models (Python)

### Pattern comune per tutti i modelli

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import sqlalchemy as sa

class Base(DeclarativeBase):
    pass

# Per SQLite compatibility: usa String(36) per UUID
def uuid_column():
    return mapped_column(
        sa.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

def now_utc():
    return datetime.now(timezone.utc)
```

### Nota SQLite vs PostgreSQL

Alcuni tipi SQL differiscono:
- `UUID`: PostgreSQL ha tipo nativo, SQLite usa `VARCHAR(36)` → usare `String(36)` per compatibilità
- `TIMESTAMPTZ`: PostgreSQL nativo, SQLite usa `DATETIME` senza timezone → usare `DateTime(timezone=True)`
- `NUMERIC(10,6)`: entrambi supportano, ma SQLite arrotonda in float — accettabile per i costi

---

## Migration workflow (Alembic)

```bash
# Creare nuova migration
alembic revision --autogenerate -m "descrizione"

# Applicare migration
alembic upgrade head

# Rollback di una versione
alembic downgrade -1

# Vedere stato
alembic current
alembic history
```

Il file `alembic/env.py` deve importare tutti i modelli prima di `target_metadata = Base.metadata`.
Usare due `env.py` separati o gestire dual-DB con custom `run_migrations_online()`.
