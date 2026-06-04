# APEX GATE — Backend Architecture

## Tech Stack

| Componente | Tecnologia | Versione minima |
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
| LLM proxy | litellm | 1.40+ |
| HTTP client | httpx | 0.27+ |
| Scheduler | APScheduler | 3.x |
| Validazione | Pydantic v2 | 2.x |

## Struttura directory

```
apex-gate/backend/
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── __init__.py
│   ├── main.py                 ← FastAPI app entry point
│   ├── config.py               ← pydantic-settings
│   ├── database.py             ← App DB engine + session
│   ├── crypto.py               ← Fernet + hashing utilities
│   ├── scheduler.py            ← APScheduler jobs
│   ├── websocket.py            ← WS /ws/status handler
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── database.py         ← Auth DB engine separato
│   │   ├── models.py           ← User, RefreshToken
│   │   ├── schemas.py          ← Pydantic request/response
│   │   ├── service.py          ← hash, JWT, token rotation
│   │   ├── router.py           ← /auth/* endpoints
│   │   └── deps.py             ← FastAPI dependencies
│   ├── api/
│   │   ├── __init__.py
│   │   ├── providers.py
│   │   ├── keys.py
│   │   ├── virtual_keys.py
│   │   ├── models_api.py
│   │   ├── logs.py
│   │   ├── stats.py
│   │   └── admin.py
│   ├── proxy/
│   │   ├── __init__.py
│   │   ├── router.py           ← proxy endpoints
│   │   ├── manager.py          ← ProviderManager
│   │   ├── protocols.py        ← request/response adapters
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── registry.py
│   │       ├── nvidia.py
│   │       ├── openrouter.py
│   │       ├── openai.py
│   │       ├── anthropic.py
│   │       ├── gemini.py
│   │       ├── groq.py
│   │       └── ollama.py
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── service.py
│   │   ├── nvidia.py
│   │   ├── openrouter.py
│   │   ├── groq.py
│   │   └── gemini.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   ├── api_key.py
│   │   ├── virtual_key.py
│   │   ├── virtual_key_assignment.py
│   │   ├── model_catalog.py
│   │   ├── request_log.py
│   │   └── exhaustion_state.py
│   └── seeds/
│       ├── __init__.py
│       └── providers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_crypto.py
│   ├── test_proxy.py
│   └── test_api_keys.py
├── scripts/
│   ├── init_db.sh
│   └── create_admin.py
├── requirements.txt
├── pyproject.toml
├── alembic.ini
├── Dockerfile
└── .env.example
```

## requirements.txt

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
sqlalchemy[asyncio]>=2.0.0
alembic>=1.13.0
aiosqlite>=0.20.0
asyncpg>=0.30.0
pydantic-settings>=2.0.0
pydantic>=2.0.0
PyJWT>=2.8.0
bcrypt>=4.0.0
cryptography>=43.0.0
litellm>=1.40.0
httpx>=0.27.0
apscheduler>=3.10.0
python-multipart>=0.0.9
```

---

## Moduli principali

### app/config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./apex_gate.db"
    AUTH_DATABASE_URL: str = "sqlite+aiosqlite:///./apex_gate_auth.db"

    # Security
    SECRET_KEY: str          # JWT signing key, REQUIRED
    FERNET_KEY: str          # API key encryption, REQUIRED (generare con Fernet.generate_key())
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Server
    PROXY_HOST: str = "0.0.0.0"
    PROXY_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Scheduler
    DISCOVERY_INTERVAL_HOURS: int = 6
    LOG_RETENTION_DAYS: int = 90

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### app/crypto.py

```python
from cryptography.fernet import Fernet
import hashlib, secrets, base64

# Encrypt/decrypt API key con Fernet (symmetric, reversibile)
def encrypt_key(plaintext: str) -> str: ...
def decrypt_key(ciphertext: str) -> str: ...

# Mask per display: "sk-abc...xyz" → "sk-...xyz"
def mask_key(plaintext: str) -> str:
    if len(plaintext) < 8:
        return "***"
    return plaintext[:4] + "..." + plaintext[-4:]

# Genera virtual key + hash per storage
def generate_virtual_key() -> tuple[str, str]:
    """Ritorna (plaintext, sha256_hash)"""
    random_part = secrets.token_urlsafe(32)
    plaintext = f"apg-{random_part}"
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, key_hash

# Hash password
def sha256_hash(value: str) -> str: ...
```

### app/proxy/manager.py

Il `ProxyManager` è il cuore del sistema di routing. Usa **`litellm.Router`** per il fallback automatico — non un loop manuale.

```python
from litellm import Router

class ProxyManager:
    async def call_with_router(
        self,
        messages: list[dict],
        virtual_key: VirtualKey,
        model_request: str,          # "auto" | nome modello esplicito
        db: AsyncSession,
    ) -> tuple[dict, str]:           # (response_dict, actual_litellm_model)
        """
        Algoritmo:
        1. Carica VirtualKeyAssignment per virtual_key.id, ordina per priority ASC
        2. Per ogni assignment:
           a. Salta se api_key.is_enabled=FALSE
           b. Salta se exhaustion_state.exhausted_until > NOW()
        3. Determina il modello per ogni API key:
           - model_request="auto" → model_catalog WHERE provider_id=X AND is_default=TRUE
           - model_request=<nome> → model_catalog WHERE model_id LIKE '%<nome>%' AND provider_id=X
        4. Costruisce model_list per litellm.Router:
           [{"model_name": "apex-route",
             "litellm_params": {"model": "{prefix}{model_id}", "api_key": decrypt(key)},
             "priority": assignment.priority}]
        5. router = Router(model_list=model_list)
        6. response = await router.acompletion(model="apex-route", messages=messages)
        7. Logga su request_logs (token, costo, latenza, modello effettivo)
        8. Ritorna (response.model_dump(), response.model)
        """

    async def _get_default_model(self, provider_id: str, db: AsyncSession) -> ModelCatalog | None:
        return await db.scalar(
            select(ModelCatalog)
            .where(ModelCatalog.provider_id == provider_id)
            .where(ModelCatalog.is_default == True)
            .where(ModelCatalog.is_active == True)
        )
```

**Errori LiteLLM** (il Router gestisce il fallback internamente; si intercetta solo l'eccezione finale):

```python
from litellm.exceptions import (
    RateLimitError,               # 429 → Router gestisce fallback automatico
    AuthenticationError,          # 401 → disabilita api_key in DB
    BadRequestError,              # 400 → non esausto, logga errore
    ContextWindowExceededError,   # non esausto, logga errore
    APIConnectionError,           # rete → Router riprova
)
```

Se il Router esaurisce tutti i provider → risponde HTTP 503 con `next_available_at`.

### app/proxy/protocols.py

Gestisce la traduzione dei protocolli.

```python
SUPPORTED_PROTOCOLS = ["openai", "anthropic", "gemini"]

def normalize_request(body: dict, protocol: str) -> dict:
    """Normalizza qualsiasi richiesta in formato interno (OpenAI-like)"""
    if protocol == "anthropic":
        # converte messages Anthropic → OpenAI format
        ...
    elif protocol == "gemini":
        # converte parts Gemini → messages format
        ...
    return body  # openai già nel formato giusto

def format_response(litellm_response, protocol: str) -> dict:
    """Converte risposta LiteLLM nel formato atteso dal client"""
    if protocol == "anthropic":
        # converte → Anthropic Messages API format
        ...
    elif protocol == "gemini":
        # converte → Gemini generateContent format
        ...
    return litellm_response.model_dump()  # openai già ok
```

---

## Endpoints completi

### Auth (`/auth`)

| Metodo | Path | Auth | Body | Response |
|---|---|---|---|---|
| POST | `/auth/login` | No | `{username, password}` | `{access_token, refresh_token, token_type}` |
| POST | `/auth/refresh` | No | `{refresh_token}` | `{access_token, refresh_token}` |
| POST | `/auth/logout` | Bearer | `{refresh_token}` | `{message}` |
| GET | `/auth/me` | Bearer | — | `UserResponse` |
| POST | `/auth/register` | Bearer (admin) | `{username, email, password, is_admin}` | `UserResponse` |

### API Keys (`/api/v1/keys`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/keys` | Bearer | Lista chiavi utente (masked) |
| POST | `/api/v1/keys` | Bearer | Crea chiave (plaintext → encrypted) |
| GET | `/api/v1/keys/{id}` | Bearer | Dettaglio singola chiave (masked) |
| PATCH | `/api/v1/keys/{id}` | Bearer | Aggiorna nome/limits/priority/enabled |
| DELETE | `/api/v1/keys/{id}` | Bearer | Elimina chiave + exhaustion_state |
| POST | `/api/v1/keys/{id}/test` | Bearer | Verifica chiave contro il provider |

### Virtual Keys (`/api/v1/virtual-keys`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/virtual-keys` | Bearer | Lista virtual keys |
| POST | `/api/v1/virtual-keys` | Bearer | Crea (plaintext ritornato una sola volta) |
| GET | `/api/v1/virtual-keys/{id}` | Bearer | Dettaglio (key_prefix solo) |
| PATCH | `/api/v1/virtual-keys/{id}` | Bearer | Aggiorna nome/budget/enabled |
| DELETE | `/api/v1/virtual-keys/{id}` | Bearer | Elimina |
| POST | `/api/v1/virtual-keys/{id}/rotate` | Bearer | Genera nuova key (old revocata) |
| GET | `/api/v1/virtual-keys/{id}/assignments` | Bearer | Lista assignment (api_key + priority) |
| POST | `/api/v1/virtual-keys/{id}/assignments` | Bearer | Aggiunge assignment `{api_key_id, priority}` |
| PATCH | `/api/v1/virtual-keys/{id}/assignments/{aid}` | Bearer | Modifica priority di un assignment |
| DELETE | `/api/v1/virtual-keys/{id}/assignments/{aid}` | Bearer | Rimuove assignment |

### Provider Catalog (`/api/v1/providers`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/providers` | Bearer | Lista provider con chiave count |
| GET | `/api/v1/providers/{slug}` | Bearer | Dettaglio provider |
| GET | `/api/v1/providers/{slug}/models` | Bearer | Modelli del provider |

### Model Catalog (`/api/v1/models`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/models` | Bearer | Lista modelli (filtri: provider, tier, vision, tools) |
| POST | `/api/v1/models/refresh` | Bearer | Trigger discovery manuale |

### Logs (`/api/v1/logs`)

| Metodo | Path | Auth | Query params |
|---|---|---|---|
| GET | `/api/v1/logs` | Bearer | `limit`, `offset`, `provider`, `status`, `virtual_key_id`, `date_from`, `date_to` |

### Stats (`/api/v1/stats`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/api/v1/stats/overview` | Bearer | Totali giornalieri |
| GET | `/api/v1/stats/by-provider` | Bearer | Breakdown per provider |
| GET | `/api/v1/stats/by-model` | Bearer | Breakdown per modello |
| GET | `/api/v1/stats/by-day` | Bearer | Serie temporale 30 giorni |
| GET | `/api/v1/stats/costs` | Bearer | Costo per chiave paid |

### Admin (`/api/v1/admin`) — solo `is_admin`

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/api/v1/admin/users` | Lista utenti |
| POST | `/api/v1/admin/users` | Crea utente |
| PATCH | `/api/v1/admin/users/{id}` | Modifica is_active, is_admin |
| DELETE | `/api/v1/admin/users/{id}` | Elimina utente |
| POST | `/api/v1/admin/reset-exhaustions` | Reset tutti exhaustion_state |

### Proxy (`/v1`, `/openai`, `/anthropic`, `/gemini`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| POST | `/v1/chat/completions` | Virtual Key | OpenAI compatibile (alias) |
| POST | `/openai/v1/chat/completions` | Virtual Key | OpenAI esplicito |
| POST | `/anthropic/v1/messages` | Virtual Key | Anthropic format |
| POST | `/gemini/v1/generateContent` | Virtual Key | Gemini format |
| GET | `/v1/models` | Virtual Key | Lista modelli disponibili |
| GET | `/health` | No | System health |

### WebSocket

| Path | Auth | Payload ogni 5s |
|---|---|---|
| `/ws/status` | `?token=<access_token>` | `{providers: [{slug, active_models, exhausted_models, calls_today}]}` |

---

## Error responses

Tutti gli endpoint seguono questo formato di errore:

```json
{
  "detail": "Messaggio di errore leggibile",
  "code": "ERROR_CODE_SNAKE_CASE",
  "timestamp": "2026-05-26T12:00:00Z"
}
```

Codici HTTP standard:
- `400` — request malformata
- `401` — non autenticato o token scaduto
- `403` — non autorizzato (es. non admin)
- `404` — risorsa non trovata
- `409` — conflitto (es. username già esistente)
- `422` — validazione fallita (Pydantic)
- `429` — rate limit sul proxy (tutti i provider esauriti)
- `503` — proxy tutti esauriti, include `next_available_at`

---

## Scheduler jobs

```python
# discovery_job
@scheduler.scheduled_job('interval', hours=settings.DISCOVERY_INTERVAL_HOURS)
async def discovery_job():
    await run_discovery()  # aggiorna model_catalog

# reset_exhaustions_job
@scheduler.scheduled_job('interval', seconds=60)
async def reset_exhaustions_job():
    await manager.reset_expired_exhaustions()  # elimina righe scadute

# cleanup_logs_job
@scheduler.scheduled_job('cron', hour=3, minute=0)
async def cleanup_logs_job():
    # elimina request_logs più vecchi di LOG_RETENTION_DAYS giorni
    cutoff = datetime.now(UTC) - timedelta(days=settings.LOG_RETENTION_DAYS)
    await db.execute(delete(RequestLog).where(RequestLog.created_at < cutoff))
```

---

## Aggiungere un nuovo provider

1. Creare `app/proxy/providers/<nome>.py` estendendo `BaseProvider`
2. Implementare `get_litellm_params(api_key: str, model_id: str) -> dict`
3. Registrare in `app/proxy/providers/registry.py`
4. Creare `app/discovery/<nome>.py` estendendo `AbstractScraper` (opzionale)
5. Aggiungere il seed in `app/seeds/providers.py`
6. Creare migration Alembic se aggiunto in tabella providers

Nessun'altra modifica necessaria.
