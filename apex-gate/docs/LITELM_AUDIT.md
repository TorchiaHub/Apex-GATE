# LiteLLM Audit — APEX GATE

**Data:** 2026-05-28
**LiteLLM versione:** `>=1.40` (requirements.txt)
**Scope:** `manager.py`, `router.py`, `keys.py`, `seeds/providers.py`, provider classes sotto `proxy/providers/`

---

## Riepilogo

| Severità | Trovati | Stato              |
|----------|---------|--------------------|
| HIGH     | 3       | 2 fixati, 1 open   |
| MEDIUM   | 5       | 2 fixati, 3 open   |
| LOW      | 4       | note               |

---

## PASS — Corretto

- **Struttura `model_list` del Router** (`manager.py:106-110`): shape `{model_name, litellm_params, priority}` corretta
- **Tutti i `litellm_prefix`** nei seeds sono corretti (vedi tabella appendice)
- **Forwarding `api_key` / `api_base`** (`manager.py:99-104`): corretto, `api_base` passato solo quando non-null
- **Gestione `AuthenticationError`** (`manager.py:134-147`): disabilita le chiavi — comportamento corretto
- **Budget enforcement** su path non-streaming (`router.py:61-65`): corretto
- **SSE streaming format** (`router.py:42-49`): `data: {json}\n\n` + `data: [DONE]\n\n` — standard OpenAI
- **`litellm.drop_params = True`** (`manager.py:20`): appropriato per un proxy

---

## ISSUES

### ~~[HIGH-1] Doppio prefisso OpenRouter — FIXATO~~

**Fix applicato:** `seeds/providers.py:38` — `model_id "openrouter/free"` → `"auto"`

Produceva `openrouter/openrouter/free`; ora produce `openrouter/auto` (corretto).

---

### ~~[HIGH-3] Gemini registry key mismatch — FIXATO~~

**Fix applicato:**
- `registry.py:19` — chiave `"google_gemini"` → `"gemini"`
- `gemini.py:5` — `GeminiProvider.slug = "google_gemini"` → `"gemini"`

Ogni test chiave Gemini restituiva falso negativo silenzioso.

---

### [HIGH-2] Streaming bypassa budget e logging — OPEN

**File:** `apex-gate/backend/app/proxy/manager.py:155-156`

Quando `stream=True`, il metodo ritorna prima dell'inserimento nel `RequestLog` (riga 180) e prima del conteggio token/costo. Conseguenze:
- Le richieste streaming **non vengono mai scritte** in `request_logs`
- `is_budget_exceeded` non vede mai i token streaming → budget giornaliero inefficace per streaming
- Un utente con `daily_token_budget` può esaurire la quota provider via streaming illimitato

**Fix raccomandato:** Passare `stream_options={"include_usage": True}` e wrappare il generatore:

```python
extra_kwargs["stream_options"] = {"include_usage": True}

async def _logged_stream(raw_stream, ...):
    last_usage = None
    async for chunk in raw_stream:
        if hasattr(chunk, "usage") and chunk.usage:
            last_usage = chunk.usage
        yield chunk
    # scrivi RequestLog da last_usage dopo fine stream
```

---

### ~~[MEDIUM-2] `priority` ignorato senza `routing_strategy="priority-based"` — FIXATO~~

**Fix applicato:** `manager.py:125` — `Router(model_list=model_list, routing_strategy="priority-based")`

---

### ~~[MEDIUM-4] Exception espone dettagli interni al client — FIXATO~~

**Fix applicato:** `manager.py:148-152` — `str(exc)` → messaggio fisso + `logger.exception(...)`

---

### [MEDIUM-1] Router ricostruito ad ogni richiesta — OPEN

**File:** `apex-gate/backend/app/proxy/manager.py:125`

Ogni `call_with_router` crea una nuova istanza `Router`. LiteLLM Router è progettato come oggetto long-lived con pool HTTP e contatori RPM/TPM. Ricostruirlo ad ogni richiesta:
- Elimina il keep-alive HTTP
- Azzera i contatori rate-limit
- Aggiunge overhead misurabile ad alto volume

**Fix:** Cachare le istanze con chiave SHA-256 della model_list serializzata.

---

### [MEDIUM-3] URL HuggingFace inconsistente tra routing e test — OPEN

| Path | URL |
|------|-----|
| Routing (`provider.api_base_url` dal DB) | `https://router.huggingface.co` |
| Key test (`HuggingFaceProvider.get_litellm_params`) | `https://api-inference.huggingface.co/v1` |

**Fix:** Allineare entrambi a `https://api-inference.huggingface.co`.

---

### [MEDIUM-5] Risposte streaming mancano di `X-Model-Used` e `X-Provider-Used` — OPEN

**File:** `apex-gate/backend/app/proxy/router.py:81-86`

Le risposte streaming includono solo `X-Virtual-Key`. L'`actual_model` restituito dal path streaming è la stringa `"streaming"` (`manager.py:156`).

**Fix:** Estrarre il modello dal primo chunk o da `_hidden_params` prima di cedere i chunk.

---

## Note (LOW)

- **R8**: `mark_exhausted` non è chiamato da `call_with_router` — verificare che `scheduler.py` lo invochi in risposta a `RateLimitError`; altrimenti `ExhaustionState` non viene mai popolato automaticamente.
- **R9**: `OpenAIProvider.get_litellm_params` restituisce `{"model": model_id}` senza prefisso `openai/` — inconsistente con gli altri provider.
- **R10**: `GroqProvider.get_litellm_params` hardcoda `api_base` — ridondante, LiteLLM lo risolve già dal prefisso `groq/`.
- **R11**: `GeminiProvider.get_litellm_params` hardcoda `f"gemini/{model_id}"` invece di usare `self.litellm_prefix` — duplicazione che può causare drift.

---

## Appendice — Tabella model string

Regola: `litellm_model_str = litellm_prefix + model_id`. Il campo `model_id` nel DB non deve mai contenere segmenti di prefisso.

| Provider    | model_id nel DB                | litellm_prefix | Stringa risultante                      | Corretto   |
|-------------|--------------------------------|----------------|-----------------------------------------|------------|
| Groq        | `llama-3.3-70b-versatile`      | `groq/`        | `groq/llama-3.3-70b-versatile`          | SI         |
| NVIDIA NIM  | `meta/llama-3.1-8b-instruct`   | `nvidia_nim/`  | `nvidia_nim/meta/llama-3.1-8b-instruct` | SI         |
| Gemini      | `gemini-2.0-flash`             | `gemini/`      | `gemini/gemini-2.0-flash`               | SI         |
| OpenRouter  | ~~`openrouter/free`~~ → `auto` | `openrouter/`  | `openrouter/auto`                       | **FIXATO** |
| Cerebras    | `llama3.1-8b`                  | `cerebras/`    | `cerebras/llama3.1-8b`                  | SI         |
| HuggingFace | `Qwen/Qwen2.5-72B-Instruct`    | `huggingface/` | `huggingface/Qwen/Qwen2.5-72B-Instruct` | SI         |
| Mistral     | `mistral-small-latest`         | `mistral/`     | `mistral/mistral-small-latest`          | SI         |
| Ollama      | `llama3.2`                     | `ollama/`      | `ollama/llama3.2`                       | SI         |
