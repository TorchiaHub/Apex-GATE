# APEX GATE — Provider Catalog

Questo file è la fonte di verità per tutti i provider supportati.
Ogni provider corrisponde a una riga nel seed `app/seeds/providers.py`.

---

## Catalogo provider (14 provider iniziali)

### 1. OpenAI

| Campo | Valore |
|---|---|
| `slug` | `openai` |
| `name` | `OpenAI` |
| `protocol` | `openai` |
| `api_base_url` | `https://api.openai.com/v1` |
| `supports_free_tier` | `false` |
| `litellm_prefix` | `openai/` |
| `sort_order` | `1` |
| Autenticazione | Header `Authorization: Bearer <api_key>` |
| Discovery disponibile | No (nessuna API pubblica) |
| Rate limits noti | Dipende dal tier account |
| Modelli principali | gpt-4o, gpt-4o-mini, o3, o4-mini |

### 2. Anthropic

| Campo | Valore |
|---|---|
| `slug` | `anthropic` |
| `name` | `Anthropic` |
| `protocol` | `anthropic` |
| `api_base_url` | `https://api.anthropic.com` |
| `supports_free_tier` | `false` |
| `litellm_prefix` | `anthropic/` |
| `sort_order` | `2` |
| Autenticazione | Header `x-api-key: <api_key>` |
| Discovery disponibile | No |
| Modelli principali | claude-opus-4-5, claude-sonnet-4-6, claude-haiku-4-5 |

### 3. Google Gemini

| Campo | Valore |
|---|---|
| `slug` | `gemini` |
| `name` | `Google Gemini` |
| `protocol` | `gemini` |
| `api_base_url` | `https://generativelanguage.googleapis.com` |
| `supports_free_tier` | `true` |
| `litellm_prefix` | `gemini/` |
| `sort_order` | `3` |
| Autenticazione | Query param `key=<api_key>` o header |
| Discovery disponibile | Sì (API pubblica) |
| Free tier limiti | gemini-2.0-flash: 1500 req/day, 15 RPM |
| Modelli principali | gemini-2.0-flash, gemini-1.5-pro |

### 4. NVIDIA NIM

| Campo | Valore |
|---|---|
| `slug` | `nvidia_nim` |
| `name` | `NVIDIA NIM` |
| `protocol` | `openai` |
| `api_base_url` | `https://integrate.api.nvidia.com/v1` |
| `supports_free_tier` | `true` |
| `litellm_prefix` | `nvidia_nim/` |
| `sort_order` | `4` |
| Autenticazione | Header `Authorization: Bearer <nvapi-...>` |
| Discovery disponibile | Sì (endpoint pubblico `/v1/models`) |
| Free tier limiti | ~40 RPM per modello |
| Modelli principali | meta/llama-3.1-8b-instruct, mistral-nemo-12b-instruct |

### 5. OpenRouter

| Campo | Valore |
|---|---|
| `slug` | `openrouter` |
| `name` | `OpenRouter` |
| `protocol` | `openai` |
| `api_base_url` | `https://openrouter.ai/api/v1` |
| `supports_free_tier` | `true` |
| `litellm_prefix` | `openrouter/` |
| `sort_order` | `5` |
| Autenticazione | Header `Authorization: Bearer <sk-or-v1-...>` |
| Discovery disponibile | Sì (`/api/v1/models` — modelli con `:free` suffix e pricing.prompt=="0") |
| Free tier limiti | ~200 req/day per modello `:free` |
| Modelli free principali | qwen/qwen3-235b-a22b:free, deepseek/deepseek-r1:free |
| Note extra | Header `HTTP-Referer` consigliato per rate limit migliori |

### 6. Groq

| Campo | Valore |
|---|---|
| `slug` | `groq` |
| `name` | `Groq` |
| `protocol` | `openai` |
| `api_base_url` | `https://api.groq.com/openai/v1` |
| `supports_free_tier` | `true` |
| `litellm_prefix` | `groq/` |
| `sort_order` | `6` |
| Autenticazione | Header `Authorization: Bearer <gsk_...>` |
| Discovery disponibile | Sì (`/openai/v1/models` — richiede auth) |
| Free tier limiti | 30 RPM, 14400 RPD su llama3-8b-8192 |
| Modelli principali | llama-3.3-70b-versatile, gemma2-9b-it |

### 7. Mistral

| Campo | Valore |
|---|---|
| `slug` | `mistral` |
| `name` | `Mistral AI` |
| `protocol` | `openai` |
| `api_base_url` | `https://api.mistral.ai/v1` |
| `supports_free_tier` | `true` |
| `litellm_prefix` | `mistral/` |
| `sort_order` | `7` |
| Autenticazione | Header `Authorization: Bearer <...>` |
| Discovery disponibile | Sì (`/v1/models`) |
| Free tier limiti | 1 req/s, modelli `*-free` disponibili |
| Modelli free principali | mistral-small-latest (free tier) |

### 8. Azure OpenAI

| Campo | Valore |
|---|---|
| `slug` | `azure_openai` |
| `name` | `Azure OpenAI` |
| `protocol` | `openai` |
| `api_base_url` | `https://<resource>.openai.azure.com` (variabile per utente) |
| `supports_free_tier` | `false` |
| `litellm_prefix` | `azure/` |
| `sort_order` | `8` |
| Autenticazione | Header `api-key: <key>` + `api-version` query param |
| Discovery disponibile | No |
| Note extra | `api_base_url` deve essere inserito dall'utente al momento della creazione della chiave |

### 9. Together AI

| Campo | Valore |
|---|---|
| `slug` | `together_ai` |
| `name` | `Together AI` |
| `protocol` | `openai` |
| `api_base_url` | `https://api.together.xyz/v1` |
| `supports_free_tier` | `false` |
| `litellm_prefix` | `together_ai/` |
| `sort_order` | `9` |
| Autenticazione | Header `Authorization: Bearer <...>` |
| Discovery disponibile | No |

### 10. Fireworks AI

| Campo | Valore |
|---|---|
| `slug` | `fireworks_ai` |
| `name` | `Fireworks AI` |
| `protocol` | `openai` |
| `api_base_url` | `https://api.fireworks.ai/inference/v1` |
| `supports_free_tier` | `false` |
| `litellm_prefix` | `fireworks_ai/` |
| `sort_order` | `10` |
| Autenticazione | Header `Authorization: Bearer <fw_...>` |
| Discovery disponibile | No |

### 11. Perplexity

| Campo | Valore |
|---|---|
| `slug` | `perplexity` |
| `name` | `Perplexity` |
| `protocol` | `openai` |
| `api_base_url` | `https://api.perplexity.ai` |
| `supports_free_tier` | `false` |
| `litellm_prefix` | `perplexity/` |
| `sort_order` | `11` |
| Autenticazione | Header `Authorization: Bearer <pplx-...>` |
| Discovery disponibile | No |

### 12. Cohere

| Campo | Valore |
|---|---|
| `slug` | `cohere` |
| `name` | `Cohere` |
| `protocol` | `cohere` |
| `api_base_url` | `https://api.cohere.com/v1` |
| `supports_free_tier` | `false` |
| `litellm_prefix` | `cohere/` |
| `sort_order` | `12` |
| Autenticazione | Header `Authorization: Bearer <...>` |
| Discovery disponibile | No |
| Note | Protocollo Cohere, NON OpenAI-compatible nativo |

### 13. Ollama (locale)

| Campo | Valore |
|---|---|
| `slug` | `ollama` |
| `name` | `Ollama (local)` |
| `protocol` | `openai` |
| `api_base_url` | `http://localhost:11434` (default, configurabile) |
| `supports_free_tier` | `true` |
| `litellm_prefix` | `ollama/` |
| `sort_order` | `13` |
| Autenticazione | Nessuna (locale) |
| Discovery disponibile | Sì (`/api/tags` — lista modelli installati) |
| Note | L'utente può configurare `api_base_url` personalizzato |

### 14. HuggingFace

| Campo | Valore |
|---|---|
| `slug` | `huggingface` |
| `name` | `HuggingFace` |
| `protocol` | `openai` |
| `api_base_url` | `https://router.huggingface.co` |
| `supports_free_tier` | `true` |
| `litellm_prefix` | `huggingface/` |
| `sort_order` | `14` |
| Autenticazione | Header `Authorization: Bearer <hf_...>` |
| Discovery disponibile | Parziale (API modelli pubblica ma complessa) |
| Note | Free tier limitato; variabile per modello |

### 15. Cerebras

| Campo | Valore |
|---|---|
| `slug` | `cerebras` |
| `name` | `Cerebras` |
| `protocol` | `openai` |
| `api_base_url` | `https://api.cerebras.ai/v1` |
| `supports_free_tier` | `true` |
| `litellm_prefix` | `cerebras/` |
| `sort_order` | `15` |
| Autenticazione | Header `Authorization: Bearer <csk-...>` |
| Discovery disponibile | No |
| Free tier limiti | 30 RPM, 60 RPD su modelli Llama |
| Modelli principali | llama3.1-8b, llama3.1-70b |

---

## LiteLLM Integration

### Come LiteLLM instrada le chiamate

Il nome del modello passato a LiteLLM è sempre `{provider.litellm_prefix}{model.model_id}`:

```python
# Esempi
await litellm.acompletion(
    model="groq/llama-3.3-70b-versatile",
    api_key="gsk_...",
    messages=[...]
)

await litellm.acompletion(
    model="nvidia_nim/meta/llama-3.1-8b-instruct",
    api_key="nvapi-...",
    messages=[...]
)

await litellm.acompletion(
    model="openrouter/openrouter/free",   # OpenRouter auto-router: sceglie tra 24+ modelli free
    api_key="sk-or-v1-...",
    messages=[...]
)

await litellm.acompletion(
    model="openrouter/qwen/qwen3-235b-a22b:free",  # modello free esplicito su OpenRouter
    api_key="sk-or-v1-...",
    messages=[...]
)

await litellm.acompletion(
    model="gemini/gemini-2.0-flash",
    api_key="AIza...",
    messages=[...]
)

await litellm.acompletion(
    model="cerebras/llama3.1-8b",
    api_key="csk-...",
    messages=[...]
)
```

### OpenRouter — convenzioni

| Tipo | Formato | Esempio |
|---|---|---|
| Modello free esplicito | `openrouter/<org>/<nome>:free` | `openrouter/meta-llama/llama-3.1-8b-instruct:free` |
| OpenRouter auto-router | `openrouter/openrouter/free` | Seleziona casualmente tra 24+ modelli free |

`openrouter/openrouter/free` è il valore usato come `model_id` nel `model_catalog` con `is_default=TRUE` per il provider OpenRouter. Il `litellm_prefix` è `openrouter/` e il `model_id` è `openrouter/free`, quindi il nome LiteLLM finale è `openrouter/openrouter/free`.

### Errori LiteLLM da gestire

```python
from litellm.exceptions import (
    RateLimitError,           # 429 → Router gestisce fallback automatico
    AuthenticationError,      # 401 → disabilita chiave in DB
    BadRequestError,          # 400 → skip, non esausto
    NotFoundError,            # 404 → marca modello is_active=False
    ContextWindowExceededError, # skip, non esausto
    APIConnectionError,       # rete → Router riprova
)
```

### Cost tracking

```python
from litellm import completion_cost

# Dopo una chiamata riuscita
cost = completion_cost(completion_response=response)
input_tokens = response.usage.prompt_tokens
output_tokens = response.usage.completion_tokens
# cost=0.0 per modelli free
```

---

## Discovery: endpoint per scraper

| Provider | Endpoint | Auth richiesta | Note |
|---|---|---|---|
| NVIDIA NIM | `GET https://integrate.api.nvidia.com/v1/models` | No | Ritorna lista modelli pubblici |
| OpenRouter | `GET https://openrouter.ai/api/v1/models` | No | Filter: `pricing.prompt == "0"` |
| Groq | `GET https://api.groq.com/openai/v1/models` | Sì | Richiede API key utente |
| Gemini | `GET https://generativelanguage.googleapis.com/v1beta/models` | Sì | Richiede API key |
| Ollama | `GET http://localhost:11434/api/tags` | No | Solo se installato localmente |

---

## Aggiungere un nuovo provider (processo)

1. Aggiungere la voce nel seed `app/seeds/providers.py`
2. Creare `app/proxy/providers/<slug>.py` estendendo `BaseProvider`
3. Registrare in `app/proxy/providers/registry.py`
4. (Opzionale) Creare `app/discovery/<slug>.py` se esiste un endpoint di discovery
5. Aggiungere logo in `frontend/src/components/ProviderLogo/`
6. Creare migration Alembic per il nuovo seed (o lasciare che il seed sia idempotente)
