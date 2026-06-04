# Apex-GATE

**Your personal LLM API gateway.** Combine API keys from multiple providers into a single smart key — with routing rules, automatic fallback, and a clean web dashboard.

---

## The problem it solves

You have 3 NVIDIA keys, 2 OpenRouter keys, and a Groq key. You want to:

- Use them all without hitting rate limits
- Let your apps use a **single stable key** that never changes
- Set priorities: try provider A first, fall back to B, then C
- Never expose real API keys in your codebase

Apex-GATE does exactly this — no code required after the initial setup.

---

## How it works

```
[Your app]                          [Apex-GATE]                       [Real Providers]
  Authorization: apg-abc123   →   validate virtual key          →    NVIDIA NIM  (priority 1)
  POST /v1/chat/completions        pick best key + provider           OpenRouter  (priority 2)
  { "model": "auto", ... }         auto-retry on 429 / errors         Groq        (priority 3)
                              ←    return response (same format)  ←
```

1. **Add your real API keys** — group them by provider, set a priority order
2. **Create a virtual key** (`apg-xxxx`) — assign it routing rules and key pools
3. **Point your app** at Apex-GATE using the virtual key — done

---

## Key features

- **Multi-provider key pooling** — add as many real keys as you want per provider; exhausted or rate-limited keys are skipped automatically
- **Virtual keys** — stable output keys (`apg-…`) that hide all routing complexity from your clients
- **Custom routing rules** — set per-key priorities, rate limits, and fallback chains manually from the dashboard
- **OpenAI-compatible API** — drop-in replacement; also supports Anthropic, Gemini, and Ollama formats
- **Web dashboard** — manage everything without touching config files or code
- **Self-hosted** — your keys stay on your machine, encrypted at rest with Fernet

---

## Quick start

### Backend

```bash
cd apex-gate/backend

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set SECRET_KEY and FERNET_KEY (generation commands are in the file comments)

python scripts/create_admin.py   # create your first admin account

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API live at **http://localhost:8000** · interactive docs at `/docs`

### Frontend

```bash
cd apex-gate/frontend
npm install
npm run dev
```

Dashboard at **http://localhost:5173**

### Docker (recommended for production)

```bash
docker compose up -d
```

---

## Virtual key model

```
Real API keys (you own these)          Virtual key (you give this to your apps)
─────────────────────────────          ─────────────────────────────────────────
NVIDIA key 1  ─┐                       apg-xxxxxxxxxxxxxxxx
NVIDIA key 2  ─┤  priority pool   →        │
OpenRouter 1  ─┤                            └─ routing rules:
OpenRouter 2  ─┤                               • providers in priority order
Groq key 1    ─┘                               • max requests / day
                                               • fallback behavior
```

One virtual key can draw from multiple real-key pools. Multiple virtual keys can share the same pool. Rotate a virtual key without changing anything in your infrastructure.

---

## Architecture overview

```
apex-gate/
├── backend/              FastAPI · SQLAlchemy async · Alembic · LiteLLM
│   ├── app/
│   │   ├── proxy/        routing engine (multi-protocol, fallback, key rotation)
│   │   ├── api/          REST dashboard API  (/api/v1/*)
│   │   ├── auth/         JWT auth (access 15m + refresh 30d)
│   │   └── crypto.py     Fernet encryption for real keys
│   └── data/             SQLite databases (gitignored — never commit these)
└── frontend/             React 19 · TypeScript · Vite · TanStack Query · Zustand
    └── src/
        ├── pages/        Dashboard · Keys · VirtualKeys · Models · Chat · Logs · Stats
        └── api/          typed axios clients for every resource
```

**Supported input protocols:** OpenAI · Anthropic · Gemini · Ollama  
**Supported providers:** NVIDIA NIM · OpenRouter · Groq · any OpenAI-compatible endpoint

---

## Security

- Real API keys are **encrypted at rest** (Fernet) and never returned in plaintext after creation
- Virtual keys are **hashed** (SHA-256) in the database — shown once at creation
- Auth uses **short-lived JWTs** (15 min access + 30-day refresh) with bcrypt passwords
- All routing happens server-side; clients never see real provider keys

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, SQLAlchemy async, Alembic, LiteLLM |
| Frontend | React 19, TypeScript (strict), Vite 6, TanStack Query, Zustand |
| Database | SQLite (two separate DBs: app + auth) |
| Auth | JWT + bcrypt + Fernet encryption |
| Deploy | Docker Compose |

---

## Roadmap

- [ ] Per-virtual-key spend limits and alerts
- [ ] Usage analytics per app / per model
- [ ] Team support (multiple users, scoped permissions)
- [ ] Webhook notifications on key exhaustion
- [ ] Import/export key configurations

---

## Contributing

Issues and PRs welcome. Please read [`AGENTS.md`](AGENTS.md) if you're working on the codebase with an AI assistant — it contains the full project map and conventions.

---

## License

MIT
