# APEX GATE — Deployment

## Ambienti

| Ambiente | Database | Frontend | Comando |
|---|---|---|---|
| **Sviluppo locale** | SQLite (file) | Vite dev server | `docker-compose up` |
| **Produzione** | PostgreSQL | nginx (build statico) | `docker-compose -f docker-compose.prod.yml up` |

---

## Sviluppo locale (senza Docker)

### Backend

```bash
cd apex-gate/backend

# Crea virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt

# Configura env
cp .env.example .env
# Modifica .env con i tuoi valori (vedi sezione Environment Variables)

# Inizializza DB + applica migration
alembic upgrade head

# Crea primo utente admin
python scripts/create_admin.py

# Avvia backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd apex-gate/frontend

# Installa dipendenze
pnpm install

# Configura env
cp .env.example .env.local
# VITE_API_URL= (lascia vuoto per usare il proxy Vite)

# Avvia dev server
pnpm dev
# Accessibile su http://localhost:5173
```

---

## Docker Compose — Sviluppo locale

### docker-compose.yml

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app          # hot reload
      - sqlite_data:/app/data   # persistenza DB
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////app/data/apex_gate.db
      - AUTH_DATABASE_URL=sqlite+aiosqlite:////app/data/apex_gate_auth.db
    env_file:
      - ./backend/.env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000

volumes:
  sqlite_data:
```

---

## Docker Compose — Produzione

### docker-compose.prod.yml

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: apex_gate
      POSTGRES_USER: apexgate
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # da .env
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U apexgate"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres_auth:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: apex_gate_auth
      POSTGRES_USER: apexgate_auth
      POSTGRES_PASSWORD: ${POSTGRES_AUTH_PASSWORD}
    volumes:
      - postgres_auth_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U apexgate_auth"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      postgres_auth:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://apexgate:${POSTGRES_PASSWORD}@postgres:5432/apex_gate
      - AUTH_DATABASE_URL=postgresql+asyncpg://apexgate_auth:${POSTGRES_AUTH_PASSWORD}@postgres_auth:5432/apex_gate_auth
    env_file:
      - .env.prod
    expose:
      - "8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"    # se usi SSL con cert montato
    depends_on:
      - backend
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro

volumes:
  postgres_data:
  postgres_auth_data:
```

---

## Dockerfile Backend

```dockerfile
# apex-gate/backend/Dockerfile
FROM python:3.12-slim

# Sicurezza: utente non-root
RUN groupadd -r apexgate && useradd -r -g apexgate apexgate

WORKDIR /app

# Dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codice
COPY . .

# Applica migration al startup
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER apexgate

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### scripts/entrypoint.sh

```bash
#!/bin/bash
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting APEX GATE backend..."
exec "$@"
```

---

## Dockerfile Frontend

```dockerfile
# apex-gate/frontend/Dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder

RUN npm install -g pnpm

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# Stage 2: Serve con nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## nginx.conf (Frontend)

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA routing: tutte le route → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API al backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /auth/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    location /v1/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    location /openai/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    location /anthropic/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    location /gemini/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://backend:8000;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header Referrer-Policy strict-origin-when-cross-origin;
}
```

---

## Environment Variables

### apex-gate/backend/.env.example

```bash
# ============================================================
# APEX GATE — Backend Environment Variables
# Copia in .env e compila con i tuoi valori
# ============================================================

# --- Database ---
# Sviluppo locale (SQLite)
DATABASE_URL=sqlite+aiosqlite:///./apex_gate.db
AUTH_DATABASE_URL=sqlite+aiosqlite:///./apex_gate_auth.db
# Produzione (PostgreSQL) — decommentare e configurare
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/apex_gate
# AUTH_DATABASE_URL=postgresql+asyncpg://user:password@auth-host:5432/apex_gate_auth

# --- Security (OBBLIGATORIO — generare valori unici) ---
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=CHANGE_ME_generate_with_secrets_token_hex_32

# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=CHANGE_ME_generate_with_Fernet_generate_key

# --- Token expiry ---
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# --- Server ---
PROXY_HOST=0.0.0.0
PROXY_PORT=8000
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# --- Scheduler ---
DISCOVERY_INTERVAL_HOURS=6
LOG_RETENTION_DAYS=90

# --- Produzione PostgreSQL passwords (per docker-compose.prod.yml) ---
# POSTGRES_PASSWORD=CHANGE_ME
# POSTGRES_AUTH_PASSWORD=CHANGE_ME
```

### apex-gate/frontend/.env.example

```bash
# ============================================================
# APEX GATE — Frontend Environment Variables
# ============================================================

# URL base del backend (vuoto = usa proxy Vite in dev)
# In produzione: https://api.yourdomain.com
VITE_API_URL=
```

---

## Primo avvio

### Locale (development)

```bash
# 1. Clona e configura
cd apex-gate
cp backend/.env.example backend/.env
# Modifica SECRET_KEY e FERNET_KEY in backend/.env

# 2. Avvia
docker-compose up -d

# 3. Crea admin (prima volta)
docker-compose exec backend python scripts/create_admin.py

# 4. Accedi
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
```

### Produzione

```bash
# 1. Configura .env.prod con tutti i valori reali
cp backend/.env.example .env.prod
# Modifica: SECRET_KEY, FERNET_KEY, POSTGRES_PASSWORD, POSTGRES_AUTH_PASSWORD
# Cambia DATABASE_URL e AUTH_DATABASE_URL a PostgreSQL

# 2. Avvia con produzione compose
docker-compose -f docker-compose.prod.yml up -d

# 3. Applica migration e crea admin
docker-compose -f docker-compose.prod.yml exec backend python scripts/create_admin.py

# 4. Accedi
# Frontend: http://your-server-ip
```

---

## Health Check

`GET /health` risponde:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "ok",
  "auth_database": "ok",
  "scheduler": "running",
  "providers_active": 3,
  "models_in_catalog": 127
}
```

Status HTTP `200` se tutto ok, `503` se DB non raggiungibile.
