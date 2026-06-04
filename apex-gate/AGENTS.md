# APEX GATE — Guida per agenti AI

Punto di ingresso per agenti autonomi che lavorano su APEX GATE.
**Leggi questo file per primo**, poi il [`README.md`](README.md) per l'avvio, poi i documenti in `docs/` pertinenti al task.

> ⚠️ Stato del progetto: **già implementato e funzionante** (backend + frontend completi).
> Non è un progetto "da costruire da zero": stai **modificando ed estendendo** codice esistente.

---

## Cosa è APEX GATE (in 30 secondi)

Gateway HTTP self-hosted per LLM. Espone endpoint **OpenAI / Anthropic / Gemini / Ollama**, gestisce un pool di chiavi reali multi-provider con fallback automatico su rate-limit, e offre una dashboard React. I client usano una **virtual key** `apg-…`; il backend traduce protocollo, sceglie provider/modello, cifra le chiavi reali, logga uso e costi.

Flusso e razionale completi: [docs/concept.md](docs/concept.md).

---

## Indice documentazione

| File | Contenuto | Leggi se… |
|---|---|---|
| [README.md](README.md) | Overview, avvio backend+frontend, endpoint, gotchas | sempre |
| [docs/concept.md](docs/concept.md) | Visione, flusso, non-goals | serve il "perché" |
| [docs/backend.md](docs/backend.md) | Architettura backend, moduli | tocchi il backend |
| [docs/frontend.md](docs/frontend.md) | Architettura frontend reale, pagine, design system | tocchi la UI |
| [docs/database.md](docs/database.md) | Schema DB (app + auth), relazioni | tocchi i modelli/migration |
| [docs/security.md](docs/security.md) | Auth flow, Fernet, virtual key, OWASP | tocchi auth/chiavi |
| [docs/providers.md](docs/providers.md) | Catalogo provider, litellm | aggiungi un provider |
| [docs/MODEL_ROUTING.md](docs/MODEL_ROUTING.md) | Logica routing/fallback modelli | tocchi il proxy manager |
| [docs/KEY_MANAGEMENT.md](docs/KEY_MANAGEMENT.md) | Chiavi reali vs virtual key, priority | tocchi le chiavi |
| [docs/deployment.md](docs/deployment.md) | Docker, env, prod | fai deploy |

I file `docs/planning.md`, `docs/report1.md`, `docs/LITELM_AUDIT.md` e `docs/spec-front/` sono **materiale storico/di analisi**: utili come contesto, ma possono non riflettere il codice attuale. In caso di conflitto, **il codice è la fonte di verità**.

---

## Architettura in breve

```
Client ──Bearer apg-… ──▶ proxy/router.py ──▶ proxy/protocols.py (normalize_request)
                                │                       │
                                │              proxy/manager.py (sceglie api key + modello, fallback)
                                │                       │
                                │                    litellm ──▶ Provider reale
                                ▼                       │
                          request_log            proxy/protocols.py (format_response) ──▶ Client
```

- **`backend/app/proxy/router.py`** — endpoint multi-protocollo. Risolve la virtual key (`sha256_hash` su `VirtualKey.key_hash`), normalizza la request nel formato OpenAI interno, chiama il manager, riformatta la response nel protocollo richiesto.
- **`backend/app/proxy/protocols.py`** — traduzioni tra OpenAI ⇄ Anthropic/Gemini/Ollama.
- **`backend/app/proxy/manager.py`** — selezione api key/modello, budget, exhaustion, fallback.
- **`backend/app/api/*`** — REST della dashboard (JWT), prefisso `/api/v1`.
- **`backend/app/auth/*`** — DB e logica auth separati dal DB applicativo.
- **`frontend/src/api/chat.ts`** — client del proxy con i 4 formati (vedi sotto).

### Protocolli proxy (shape I/O)

| Formato | Endpoint | Response (campi letti dal frontend) | Streaming |
|---|---|---|---|
| openai | `/v1/chat/completions` | `choices[0].message.content`, `model` | ✅ |
| anthropic | `/anthropic/v1/messages` | `content[0].text`, `model` | ❌ |
| gemini | `/gemini/v1/generateContent` | `candidates[0].content.parts[].text`, `modelVersion` | ❌ |
| ollama | `/ollama/api/chat` | `message.content`, `model` | ❌ |

Nel frontend il selettore di formato è in `pages/Chat.tsx`; builder/parser per formato sono in `api/chat.ts` (`FORMAT_SPECS`).

---

## Regole operative

### Cosa NON fare
- NON modificare file fuori da `apex-gate/`.
- NON mettere logica di business nel frontend (solo presentazione + chiamate API).
- NON hardcodare API key, segreti o URL nei sorgenti (usa `.env` / `import.meta.env`).
- NON cambiare lo schema DB senza una **migration Alembic**.
- NON restituire chiavi reali in chiaro via API dopo la creazione (solo masked).
- NON committare né cancellare `backend/data/*.db` (dati reali: utenti, chiavi).

### Convenzioni di codice
- **Python**: 3.12+, type hints ovunque, `async/await` per ogni I/O. Config solo via `app.config.settings` (mai `os.environ` diretto).
- **TypeScript**: strict, niente `any` esplicito.
- **CSS**: design system a CSS custom properties in `frontend/src/styles/tokens.css` (`var(--color-*)`, `var(--space-*)`, `var(--radius-*)`, `var(--text-*)`, `var(--weight-*)`). I componenti usano CSS Modules (`*.module.css`).
- **DB session (app)**: `from app.database import AsyncSessionLocal` → `async with AsyncSessionLocal() as db:`. (Per l'auth: `app.auth.database.AuthSessionLocal`.)
- **Commit**: conventional commits (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`).

### Testing
- Test in `backend/tests/` con `pytest`. Ogni endpoint API dovrebbe avere almeno un test di integrazione; ogni funzione crypto un unit test; la logica di fallback del proxy test con provider mockati.

---

## Comandi utili

```powershell
# Backend (dalla cartella backend, con .venv attivo)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
python scripts\create_admin.py          # crea il primo admin
alembic revision --autogenerate -m "x"  # nuova migration dopo un cambio schema
alembic upgrade head                     # applica le migration
pytest                                   # esegui i test

# Frontend (dalla cartella frontend)
npm run dev      # dev server su :5173 (proxy verso :8000)
npm run build    # build di produzione (tsc -b + vite build)
npm run lint     # type-check (tsc --noEmit)
```

---

## Gotchas (leggere prima di debuggare)

- **CORS** si legge **solo all'avvio**. Se la pagina Chat dà "Failed to fetch", verifica che l'origine del frontend sia in `CORS_ORIGINS` nel `.env` del backend, poi **riavvia il backend**.
- La pagina **Chat** chiama il proxy **direttamente** su `http://localhost:8000` (`PROXY_BASE_URL` in `api/chat.ts`), non tramite il proxy Vite. Le altre chiamate dashboard passano da `api/client.ts` (baseURL `/`, proxy Vite).
- I **database** sono in `backend/data/` (path assoluto risolto da `config.py`, indipendente dalla CWD).
- **Streaming** disponibile solo su OpenAI; gli altri 3 formati rispondono non-stream.
- **Rotazione virtual key** invalida il vecchio `apg-…`: va riaggiornato nei client e nel campo della pagina Chat.

---

## Workspace layout

```
free-models/
├── apex-gate/              ← QUESTO PROGETTO
├── tools/
│   └── nvidia-free-models/ ← scraper modelli NVIDIA free (output letto dal backend)
└── vendor/
    └── litellm/            ← upstream LiteLLM (riferimento, non modificare)
```
