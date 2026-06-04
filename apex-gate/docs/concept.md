# APEX GATE — Concept e Visione di Progetto

## Tagline
**Il portale d'accesso al sistema.** Gateway self-hosted per LLM con pool di chiavi multi-provider, model routing automatico via LiteLLM Router e dashboard web.

## Problema che risolve

Chiunque usi più provider LLM si trova con:

1. **Key sprawl** — 10+ chiavi API da provider diversi, rate limit diversi, da gestire manualmente
2. **Rate limit interruptions** — quando una chiave esaurisce il limite, la chiamata fallisce
3. **Protocol fragmentation** — ogni provider ha protocollo diverso (OpenAI, Anthropic, Gemini, Ollama)
4. **Zero visibility** — nessuna dashboard per costi, utilizzo, latenza, modello usato
5. **Model confusion** — difficile sapere quali modelli free sono disponibili e come si chiamano in LiteLLM

## Soluzione: APEX GATE

Un proxy HTTP self-hosted che:

- Si pone tra i tuoi progetti e i provider LLM reali
- Espone **endpoint OpenAI-compatibili** (e Anthropic/Gemini in traduzione)
- Gestisce un **pool di API key** da qualsiasi provider (free e paid)
- Usa **LiteLLM Router** per il fallback automatico tra chiavi/provider
- Fornisce una **singola virtual key** (`apg-xxxx`) da usare in tutti i propri progetti
- Offre una **dashboard web** per gestire tutto in real-time

## Come funziona (flusso base)

```
[Il tuo progetto]
  Authorization: Bearer apg-abc123
  POST http://localhost:4000/v1/chat/completions
  { "model": "auto", "messages": [...] }
         ↓
[APEX GATE Proxy]
  1. Valida la virtual key "apg-abc123" (SHA-256 lookup)
  2. Carica VirtualKeyAssignment della virtual key (API key reali + priority)
  3. Determina i modelli da usare:
     - model="auto" → usa is_default=TRUE da model_catalog per ogni provider
     - model="llama-3.1-8b-instant" → trova le API key che supportano quel modello
  4. Costruisce un litellm.Router con tutte le API key disponibili (ordinate per priority)
  5. router.acompletion(model="apex-route", ...) — LiteLLM gestisce fallback
     - 429 su una chiave → passa automaticamente alla successiva
     - Successo → aggiunge X-Model-Used: groq/llama-3.3-70b-versatile all'header
  6. Logga la chiamata (token, costo, latenza, modello usato)
  7. Ritorna la risposta nel formato OpenAI
         ↓
[Provider reale]
  Groq (priority 1) → NVIDIA NIM (priority 2) → OpenRouter (priority 3) → ...
```

## Due modalità di routing

### AUTO (default)
Il client non specifica il modello (o usa `"auto"`).
Il proxy usa il modello di default di ogni provider (`model_catalog.is_default=TRUE`).

```json
{ "model": "auto", "messages": [...] }
```

Per OpenRouter in modalità AUTO, il proxy usa `openrouter/openrouter/free` — il router interno di OpenRouter che seleziona casualmente tra 24+ modelli free disponibili.

### EXPLICIT
Il client specifica esattamente quale modello usare.

```json
{ "model": "llama-3.1-8b-instant", "messages": [...] }
```

Il proxy cerca in `model_catalog` quali provider hanno quel modello, poi include solo le API key di quei provider nel Router. Se il provider assegnato non ha quel modello, viene saltato.

## Provider supportati

### Free tier (pool predefinito per la maggior parte degli utenti)

| Provider | LiteLLM prefix | Modello default (AUTO) | Limite free |
|---|---|---|---|
| Groq | `groq/` | `groq/llama-3.3-70b-versatile` | 30 RPM |
| NVIDIA NIM | `nvidia_nim/` | `nvidia_nim/meta/llama-3.1-8b-instruct` | ~40 RPM |
| Google Gemini | `gemini/` | `gemini/gemini-2.0-flash` | 1500 req/day |
| OpenRouter | `openrouter/` | `openrouter/openrouter/free` | 200 req/day |
| Mistral | `mistral/` | `mistral/mistral-small-latest` | 1 req/s |
| Cerebras | `cerebras/` | `cerebras/llama3.1-8b` | 30 RPM |
| HuggingFace | `huggingface/` | variabile | limitato |
| Ollama | `ollama/` | configurabile | illimitato (locale) |

### Paid tier

OpenAI, Anthropic, Azure OpenAI, Together AI, Fireworks AI, Perplexity, Cohere.

## Caratteristiche chiave

### 1. Pool di API Key
- Aggiungi chiavi da qualsiasi provider con nome e limiti (RPM, RPD, budget USD)
- Cifratura Fernet at-rest — mai esposte via API dopo la creazione
- Status in tempo reale: ok / esaurito / over-budget / disabilitato

### 2. Virtual Key System
- Genera chiavi `apg-xxxx` — una per progetto/applicazione
- Per ogni virtual key, selezioni le API key reali e la loro **priority** (1 = prima, 99 = ultima)
- `VirtualKeyAssignment` è l'entità che lega virtual key → API key → priority

### 3. LiteLLM Router (fallback automatico)
- Per ogni richiesta, il proxy costruisce un `litellm.Router` con le API key assegnate
- Tutte le entry hanno alias `"apex-route"` — LiteLLM sceglie in base alla priority
- Su 429 → LiteLLM passa automaticamente all'entry successiva
- Headers di risposta: `X-Model-Used`, `X-Provider-Used`, `X-Virtual-Key`

### 4. Model Catalog
- Tabella `model_catalog` con tutti i modelli noti per provider
- `is_default=TRUE` → modello usato in AUTO mode per quel provider (uno per provider)
- Discovery scheduler aggiorna automaticamente ogni 6 ore

### 5. Protocol Translation
- Il client sceglie il protocollo nell'URL:
  - `/v1/chat/completions` → OpenAI (default)
  - `/anthropic/v1/messages` → Anthropic format
  - `/gemini/v1/generateContent` → Gemini format
- La risposta è sempre nel formato del protocollo richiesto

### 6. Multi-utente
- Login JWT (access + refresh token rotation)
- Ogni utente ha il proprio pool isolato di chiavi e virtual keys
- Auth module separato su DB distinto

### 7. Dashboard analytics
- Grafico chiamate nel tempo, per provider/modello
- Latenza, token usati, costo USD per chiave paid
- Log paginato e filtrabile

## Architettura macro

```
apex-gate/
├── backend/     FastAPI + LiteLLM Router + SQLAlchemy + APScheduler
└── frontend/    React 19 + Vite + TypeScript
```

- Database dual: `apex_gate_auth.db` (utenti) + `apex_gate.db` (tutto il resto)
- SQLite in sviluppo, PostgreSQL in produzione (stessa codebase)
- Docker Compose per deploy completo

## Non-Goals (v1)

- Non è un orchestratore di agenti (no workflow multi-step)
- Non fa caching semantico delle risposte LLM
- Non include RAG o fine-tuning
- Non è multi-tenant SaaS (self-hosted per singoli o team piccoli)
- Non gestisce routing basato sul contenuto della richiesta (solo priority + model matching)

## Principi di design

- **Proxy-first**: il core è il proxy engine; la dashboard è uno strato sopra
- **DB-backed state**: tutto lo stato su database, zero file JSON di stato
- **LiteLLM Router**: non reinventare il fallback — usare il Router ufficiale LiteLLM
- **Auth isolato**: `auth/` estraibile come microservizio senza modifiche
- **Security by default**: chiavi cifrate at-rest, masked in API, JWT stateless
