# APEX GATE — Model Routing

Questo documento descrive come APEX GATE determina quale modello usare per ogni richiesta.
È la fonte di verità per la logica dentro `proxy/manager.py`.

---

## LiteLLM model naming

Ogni modello in APEX GATE è identificato da un nome LiteLLM nella forma:

```
{provider.litellm_prefix}{model.model_id}
```

### Esempi per provider

| Provider | `litellm_prefix` | `model_id` | Stringa LiteLLM finale |
|---|---|---|---|
| Groq | `groq/` | `llama-3.3-70b-versatile` | `groq/llama-3.3-70b-versatile` |
| NVIDIA NIM | `nvidia_nim/` | `meta/llama-3.1-8b-instruct` | `nvidia_nim/meta/llama-3.1-8b-instruct` |
| Google Gemini | `gemini/` | `gemini-2.0-flash` | `gemini/gemini-2.0-flash` |
| Mistral | `mistral/` | `mistral-small-latest` | `mistral/mistral-small-latest` |
| Cerebras | `cerebras/` | `llama3.1-8b` | `cerebras/llama3.1-8b` |
| Ollama | `ollama/` | `llama3.2` | `ollama/llama3.2` |

### OpenRouter — casi speciali

OpenRouter ha due convenzioni:

**Modelli con `:free` suffix** — variante free di modelli paid:
```
openrouter/meta-llama/llama-3.1-8b-instruct:free
openrouter/qwen/qwen3-235b-a22b:free
openrouter/deepseek/deepseek-r1:free
```

**`openrouter/openrouter/free`** — il router AUTO di OpenRouter:
- Non è un modello specifico, è un router interno OpenRouter
- Seleziona casualmente tra 24+ modelli free disponibili al momento della richiesta
- È il modello di default (`is_default=TRUE`) per il provider OpenRouter in APEX GATE
- Documentazione OpenRouter: https://openrouter.ai/docs/models/openrouter-free

---

## Due modalità di routing

### AUTO mode (default)

Usato quando il client non specifica il modello o usa `model: "auto"`.

```json
POST /v1/chat/completions
{
  "model": "auto",
  "messages": [...]
}
```

**Algoritmo**:
1. Carica i `VirtualKeyAssignment` della virtual key (le API key assegnate con priority)
2. Per ogni API key, ottieni il provider
3. Per ogni provider, carica il modello con `is_default=TRUE` da `model_catalog`
4. Costruisci il LiteLLM Router con quelle coppie (api_key, default_model)
5. Chiama `router.acompletion(model="apex-route", ...)`

### EXPLICIT mode

Usato quando il client specifica un modello esatto.

```json
POST /v1/chat/completions
{
  "model": "llama-3.1-8b-instruct",
  "messages": [...]
}
```

**Algoritmo**:
1. Cerca in `model_catalog` tutti i modelli il cui `model_id` contiene o corrisponde alla stringa inviata
2. Filtra: tieni solo le API key assegnate il cui provider ha quel modello
3. Costruisci il LiteLLM Router solo con quelle entry
4. Chiama `router.acompletion(model="apex-route", ...)`

Se nessuna API key assegnata supporta il modello richiesto → HTTP 422 con dettaglio.

---

## LiteLLM Router — costruzione per richiesta

Il Router viene costruito dinamicamente per ogni richiesta (non condiviso globalmente).

```python
from litellm import Router
from app.crypto import decrypt_key

async def build_router(assignments: list[VirtualKeyAssignment], db) -> Router:
    model_list = []
    for assignment in sorted(assignments, key=lambda a: a.priority):
        api_key = await db.get(ApiKey, assignment.api_key_id)
        if not api_key.is_enabled:
            continue
        provider = await db.get(Provider, api_key.provider_id)
        default_model = await get_default_model(provider.id, db)
        if default_model is None:
            continue

        litellm_model = f"{provider.litellm_prefix}{default_model.model_id}"
        model_list.append({
            "model_name": "apex-route",
            "litellm_params": {
                "model": litellm_model,
                "api_key": decrypt_key(api_key.key_encrypted),
                **({"api_base": provider.api_base_url} if provider.api_base_url else {}),
            },
            "priority": assignment.priority,  # 1 = più alta
        })

    return Router(model_list=model_list)
```

---

## Modello di default per provider (AUTO mode seed)

Questi sono i valori seedati in `model_catalog.is_default=TRUE` per ogni provider free:

| Provider | `model_id` (in `model_catalog`) | Stringa LiteLLM completa |
|---|---|---|
| Groq | `llama-3.3-70b-versatile` | `groq/llama-3.3-70b-versatile` |
| NVIDIA NIM | `meta/llama-3.1-8b-instruct` | `nvidia_nim/meta/llama-3.1-8b-instruct` |
| Google Gemini | `gemini-2.0-flash` | `gemini/gemini-2.0-flash` |
| OpenRouter | `openrouter/free` | `openrouter/openrouter/free` |
| Mistral | `mistral-small-latest` | `mistral/mistral-small-latest` |
| Cerebras | `llama3.1-8b` | `cerebras/llama3.1-8b` |
| HuggingFace | `Qwen/Qwen2.5-72B-Instruct` | `huggingface/Qwen/Qwen2.5-72B-Instruct` |
| Ollama | `llama3.2` | `ollama/llama3.2` |

**Regola**: un solo `is_default=TRUE` per provider. Verificato a livello applicativo.

---

## Exhaustion handling

Prima di aggiungere una chiave al Router, il proxy verifica `exhaustion_state`:

```python
async def is_exhausted(api_key_id: str, db: AsyncSession) -> bool:
    state = await db.scalar(
        select(ExhaustionState)
        .where(ExhaustionState.api_key_id == api_key_id)
        .where(ExhaustionState.exhausted_until > datetime.now(UTC))
    )
    return state is not None
```

Le chiavi esaurite vengono **escluse dal Router** prima della costruzione, non gestite post-429.  
Il LiteLLM Router gestisce i 429 che arrivano durante la chiamata come fallback aggiuntivo.

---

## Response headers

Ogni risposta proxy include:

| Header | Valore | Esempio |
|---|---|---|
| `X-Model-Used` | Stringa LiteLLM del modello effettivamente usato | `groq/llama-3.3-70b-versatile` |
| `X-Provider-Used` | Slug del provider | `groq` |
| `X-Virtual-Key` | Prefisso della virtual key | `apg-a1b2c3d4` |

```python
# Dopo router.acompletion()
actual_model = response._hidden_params.get("model") or response.model
provider_slug = actual_model.split("/")[0] if "/" in actual_model else "unknown"

return Response(
    content=...,
    headers={
        "X-Model-Used": actual_model,
        "X-Provider-Used": provider_slug,
        "X-Virtual-Key": virtual_key.key_prefix,
    }
)
```

---

## Flusso completo (diagramma)

```
Client
  POST /v1/chat/completions
  Authorization: Bearer apg-abc123
  { "model": "auto", "messages": [...] }
       ↓
proxy/router.py
  Estrae virtual key dall'header
       ↓
proxy/manager.py → call_with_router()
  1. SHA-256("apg-abc123") → cerca in virtual_keys
  2. Verifica is_enabled + daily_token_budget
  3. Carica VirtualKeyAssignment (ordinate per priority)
  4. Per ogni assignment: skip se api_key disabilitata o esaurita
  5. Carica modello default da model_catalog (AUTO) o cerca per nome (EXPLICIT)
  6. Costruisce litellm.Router(model_list=[...])
  7. router.acompletion(model="apex-route", messages=[...])
       ↓
litellm.Router
  Tenta priority 1 → se 429 → tenta priority 2 → ...
       ↓
Provider reale (Groq / NVIDIA / OpenRouter / ...)
       ↓
proxy/manager.py
  8. Logga su request_logs (token, costo, latenza, modello usato)
  9. Aggiunge headers X-Model-Used, X-Provider-Used, X-Virtual-Key
       ↓
Client
  200 OK + risposta OpenAI-format
```

---

## Errori possibili

| Situazione | Comportamento | HTTP |
|---|---|---|
| Virtual key non trovata | 404 | 404 |
| Virtual key disabilitata | 401 | 401 |
| Budget giornaliero superato | 429 | 429 |
| Nessuna assignment disponibile | 503 | 503 |
| Tutte le chiavi esaurite | 503 + `next_available_at` | 503 |
| Modello EXPLICIT non trovato | 422 | 422 |
| Auth error da provider | Disabilita chiave + skip | — |
