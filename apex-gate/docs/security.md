# APEX GATE — Security Architecture

## Principi generali

- **Zero trust**: ogni richiesta è autenticata, nessun endpoint è "implicitamente sicuro"
- **Least privilege**: ogni token/chiave ha i minimi permessi necessari
- **Defense in depth**: più livelli di protezione (JWT + virtual key + DB encryption)
- **Fail secure**: in caso di errore, nega l'accesso (non consentire)
- **Secrets at rest**: nessun segreto in chiaro nel database

---

## 1. Autenticazione Utente (JWT)

### Flow completo

```
[Client]                          [Backend]
   │                                  │
   │  POST /auth/login                │
   │  {username, password}  ─────────►│
   │                                  │  1. Cerca user per username
   │                                  │  2. bcrypt.verify(password, hash)
   │                                  │  3. Crea access_token (JWT, 15min)
   │                                  │  4. Crea refresh_token (opaque, 30d)
   │                                  │     - SHA-256 hash → DB
   │◄────────────────────────────────-│
   │  {access_token, refresh_token}   │
   │                                  │
   │  [Successiva chiamata API]        │
   │  Header: Authorization: Bearer <access_token>
   │  GET /api/v1/keys  ─────────────►│
   │                                  │  1. Decodifica JWT
   │                                  │  2. Verifica firma + scadenza
   │                                  │  3. Carica user da Auth DB
   │◄─────────────────────────────────│
   │  200 OK + dati                   │
   │                                  │
   │  [Refresh access token]           │
   │  POST /auth/refresh              │
   │  {refresh_token}  ──────────────►│
   │                                  │  1. SHA-256 del refresh_token
   │                                  │  2. Cerca in DB (non revocato, non scaduto)
   │                                  │  3. Marca vecchio come revocato
   │                                  │  4. Crea nuovo access_token + nuovo refresh_token
   │◄─────────────────────────────────│
   │  {access_token, refresh_token}   │
```

### JWT payload

```json
{
  "sub": "user-uuid-here",
  "iat": 1748260000,
  "exp": 1748260900,
  "type": "access"
}
```

**Importante**: il JWT non contiene dati sensibili, solo l'user ID. Le info utente vengono caricate dal DB ad ogni richiesta.

### Configurazione JWT

```python
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15     # breve, refresh frequente
REFRESH_TOKEN_EXPIRE_DAYS = 30       # lungo, rotation a ogni uso
```

### Sicurezza refresh token

- Il plaintext del refresh token NON è mai salvato in DB
- Solo SHA-256 hash → DB
- A ogni refresh: rotation obbligatoria (vecchio revocato, nuovo creato)
- Rilevamento furto: se un refresh token già revocato viene usato → revoca TUTTI i token dell'utente
- Storage client: localStorage (accettabile per self-hosted, non SaaS)

---

## 2. Autenticazione Proxy (Virtual Key)

### Flow

```
[Progetto cliente]                [Proxy]
   │                                 │
   │  POST /v1/chat/completions      │
   │  Authorization: Bearer apg-xxxx │
   │  {messages: [...]}  ───────────►│
   │                                 │  1. Estrae "apg-xxxx" dall'header
   │                                 │  2. SHA-256("apg-xxxx") → cerca in virtual_keys
   │                                 │  3. Verifica is_enabled=TRUE
   │                                 │  4. Verifica budget giornaliero non superato
   │                                 │  5. Carica gli assignment della virtual key (ordinati per priority ASC)
   │                                 │  6. Esegue call_with_fallback()
   │◄────────────────────────────────│
   │  {choices: [...]}               │
```

### Generazione virtual key

```python
import secrets, hashlib

def generate_virtual_key() -> tuple[str, str]:
    random_part = secrets.token_urlsafe(32)  # 256 bit di entropia
    plaintext = f"apg-{random_part}"         # es. "apg-xK9mN2..."
    key_hash = hashlib.sha256(plaintext.encode('utf-8')).hexdigest()
    return plaintext, key_hash
```

- Il plaintext è mostrato **una sola volta** all'utente al momento della creazione
- Solo `key_hash` è salvato in DB
- Impossibile recuperare il plaintext dal hash

---

## 3. Crittografia API Keys (Fernet)

### Perché Fernet

Fernet è crittografia simmetrica autenticata (AES-128-CBC + HMAC-SHA256). È reversibile (necessario per poter usare la chiave nelle chiamate AI) ma protetta da una chiave master.

### Implementazione

```python
from cryptography.fernet import Fernet

# Generazione chiave (una sola volta, salvata in env)
# FERNET_KEY = Fernet.generate_key().decode()  # Base64 encoded

fernet = Fernet(settings.FERNET_KEY.encode())

def encrypt_key(plaintext: str) -> str:
    return fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')

def decrypt_key(ciphertext: str) -> str:
    return fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
```

### Dove avviene la decryption

La decryption avviene **solo** in `ProviderManager.call_with_fallback()` al momento della chiamata. Non avviene in nessun router API. La chiave decriptata non è mai inclusa in risposte API, log, o eccezioni.

### Masked key per display

```python
def mask_key(plaintext: str) -> str:
    """Ritorna es. 'sk-...x9f2' per display nella UI"""
    if len(plaintext) <= 8:
        return "***"
    prefix = plaintext[:min(4, len(plaintext)//4)]
    suffix = plaintext[-4:]
    return f"{prefix}...{suffix}"
```

---

## 4. Password Hashing

```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
```

**Cost factor 12**: ~0.3s per hash su hardware moderno. Adeguato per prevenire brute force.

---

## 5. Isolamento Auth Module

Il modulo `app/auth/` usa una connessione DB **completamente separata**:

```python
# app/auth/database.py — usa AUTH_DATABASE_URL, non DATABASE_URL
auth_engine = create_async_engine(settings.AUTH_DATABASE_URL)
AuthSessionLocal = async_sessionmaker(auth_engine)

async def get_auth_session():
    async with AuthSessionLocal() as session:
        yield session
```

**Benefici**:
- In produzione, `AUTH_DATABASE_URL` può puntare a un host PostgreSQL separato con accesso limitato
- I dati utente (password, email) sono fisicamente separati dai log delle chiamate AI
- Il modulo `auth/` può essere estratto come microservizio separato cambiando solo la variabile d'ambiente

---

## 6. CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ["http://localhost:5173", "http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

In produzione: `CORS_ORIGINS` contiene solo il dominio del frontend (es. `https://app.example.com`).

---

## 7. Protezione endpoint

### Dependency FastAPI

```python
# app/auth/deps.py

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_auth_session)
) -> User:
    payload = verify_access_token(token)  # raises 401 se invalido
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    return user

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user
```

### Applicazione ai router

```python
# Endpoint normale (solo autenticato)
@router.get("/keys")
async def list_keys(user: User = Depends(get_current_user), ...):
    # user.id è l'owner verificato

# Endpoint admin
@router.get("/admin/users")
async def list_users(admin: User = Depends(require_admin), ...):
    ...
```

---

## 8. Input validation

- **Pydantic v2** valida automaticamente tutti i body delle request
- Lunghezza massima per nome chiave: 100 caratteri
- Lunghezza massima per API key input: 500 caratteri
- `priority` (negli assignment) deve essere tra 1 e 99
- `budget_daily_usd` deve essere > 0 se specificato

---

## 9. Rate limiting (opzionale Phase 6+)

Per ora non implementato. In futuro: `slowapi` (basato su `limits`) per limitare tentativi di login.

```python
# Future implementation
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/login")
@limiter.limit("10/minute")
async def login(...): ...
```

---

## 10. OWASP Top 10 — checklist

| Vulnerabilità | Mitigazione |
|---|---|
| A01 Broken Access Control | Tutti gli endpoint richiedono auth; owner check su ogni risorsa |
| A02 Cryptographic Failures | Fernet per API keys, bcrypt per password, JWT con HS256 |
| A03 Injection | Pydantic validation, SQLAlchemy ORM (no raw SQL), no eval |
| A04 Insecure Design | Auth DB separato, virtual keys non reversibili, fail secure |
| A05 Security Misconfiguration | CORS restrittivo, no debug in prod, no default credentials |
| A06 Vulnerable Components | requirements.txt con versioni minime, aggiornamenti periodici |
| A07 Auth Failures | Refresh token rotation, breve expiry access token, bcrypt |
| A08 Software Integrity | No exec di codice esterno, no eval, dependency pinning |
| A09 Logging Failures | Request logs in DB, errori loggati lato server (no stack trace al client) |
| A10 SSRF | `api_base_url` dei provider è whitelistato (no URL arbitrari dagli utenti) |

---

## 11. Variabili d'ambiente sensibili

| Variabile | Descrizione | Come generare |
|---|---|---|
| `SECRET_KEY` | Firma JWT | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FERNET_KEY` | Encrypt API keys | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `AUTH_DATABASE_URL` | Connessione auth DB | Vedere deployment.md |
| `DATABASE_URL` | Connessione app DB | Vedere deployment.md |

**Regola assoluta**: nessuna di queste variabili può essere nei file sorgente, nel Dockerfile, o nel docker-compose.yml. Solo in `.env` (locale) o in variabili d'ambiente del sistema di hosting.
