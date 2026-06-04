# APEX GATE — Key Management

Questo documento descrive la logica di gestione delle chiavi in APEX GATE.
Leggilo prima di implementare qualsiasi parte del proxy engine o delle API di gestione chiavi.

---

## Due tipi di chiave

### 1. API Keys (Provider Keys)

Un'API key è una **chiave reale di un provider LLM** (es. Groq, NVIDIA NIM, Anthropic) inserita dall'utente.

- Appartiene a un utente (`user_id`) e a un provider (`provider_id`)
- Viene cifrata con Fernet at-rest, mai esposta in chiaro via API
- L'utente può configurare:
  - `rate_limit_rpm` — chiamate al minuto consentite dal provider per quella chiave (opzionale)
  - `rate_limit_rpd` — chiamate al giorno consentite dal provider per quella chiave (opzionale)
  - `budget_daily_usd` / `budget_monthly_usd` — solo per chiavi paid (opzionale)
- **NON ha una `priority`** — la priority non è un attributo dell'API key, ma dell'assignment
- NON è usata direttamente dai client: i client usano solo virtual keys

### 2. Virtual Keys (Client Keys)

Una virtual key è una **chiave di output emessa al client** (progetto, app, script) con prefisso `apg-`.

- Identificata dal suo SHA-256 hash (il plaintext è mostrato una sola volta alla creazione)
- Può avere un `daily_token_budget` (limite token giornaliero, opzionale)
- È collegata alle API key reali tramite `VirtualKeyAssignment`
- Al momento della creazione, l'utente seleziona **specificamente quali API key reali** includere
- Per ogni API key inclusa, imposta una **priority** (1 = massima, 99 = minima)

---

## VirtualKeyAssignment — l'entità centrale

`VirtualKeyAssignment` è il collegamento tra una virtual key e un'API key reale.
Ogni assignment ha:

| Campo | Tipo | Descrizione |
|---|---|---|
| `virtual_key_id` | UUID | FK → `virtual_keys.id` |
| `api_key_id` | UUID | FK → `api_keys.id` |
| `priority` | INTEGER | 1 = tentare per prima, 99 = tentare per ultima |

**Regole**:
- Una stessa API key non può essere assegnata due volte alla stessa virtual key (UNIQUE constraint)
- La priority è configurabile per ogni coppia (virtual_key, api_key) — la stessa API key può avere priority 1 in una virtual key e priority 5 in un'altra

---

## Come funziona il routing

Quando il proxy riceve una richiesta con una virtual key:

```
[Client] → Authorization: Bearer apg-abc123
           body: { "model": "auto", "messages": [...] }

APEX GATE:
  1. SHA-256("apg-abc123") → cerca in virtual_keys
  2. Verifica is_enabled=TRUE e daily_token_budget non superato
  3. Carica tutti i VirtualKeyAssignment per questa virtual key, ordina per priority ASC
  4. Per ogni assignment: salta se api_key.is_enabled=FALSE o exhaustion_state attivo
  5. Determina il modello per ogni API key:
     - "auto" → model_catalog.is_default=TRUE per il provider di quella chiave
     - "llama-3.1-8b-instant" → model_catalog.model_id LIKE '%llama-3.1-8b%' per quel provider
  6. Costruisce litellm.Router con tutte le entry valide (model_name="apex-route")
  7. router.acompletion(model="apex-route", messages=[...])
     - LiteLLM gestisce il fallback: se priority-1 → 429 → passa a priority-2, ecc.
  8. Aggiunge headers: X-Model-Used, X-Provider-Used, X-Virtual-Key
  9. Se tutti falliscono → risposta 503 con next_available_at
```

---

## Configurazione rate limits

I `rate_limit_rpm` e `rate_limit_rpd` sull'API key sono **informativi**: indicano i limiti reali che il provider impone per quella chiave.

- Il proxy li usa per capire quando una chiave è esaurita
- Se `rate_limit_rpd=200` e la chiave ha già gestito 200 richieste oggi → la chiave è considerata esaurita
- Se `rate_limit_rpm=30` e arriva un 429 → la chiave viene marcata esaurita per 60 secondi (backoff)
- Se i limiti non sono configurati (`NULL`), il proxy si basa sui 429 reali ricevuti dal provider

---

## Esempio pratico

**Scenario**: un utente ha tre API key e vuole una virtual key di produzione che usi Groq come prima scelta, NVIDIA come seconda, e OpenRouter come fallback.

**Step 1 — Configura le API key:**

| Nome | Provider | rate_limit_rpm | rate_limit_rpd |
|---|---|---|---|
| My Groq Key | Groq | 30 | 14400 |
| My NVIDIA Key | NVIDIA NIM | 40 | NULL |
| My OpenRouter Key | OpenRouter | NULL | 200 |

Nessuna priority qui — le API key sono solo contenitori di credenziali con limiti.

**Step 2 — Crea la virtual key "Prod App" e aggiunge gli assignment:**

| API Key | Priority |
|---|---|
| My Groq Key | 1 |
| My NVIDIA Key | 2 |
| My OpenRouter Key | 3 |

**Step 3 — Il proxy in azione:**

```
Richiesta con apg-prod123
  → prova My Groq Key (priority 1)
     → 429 ricevuto → marca esaurita per 60s
  → prova My NVIDIA Key (priority 2)
     → OK → risposta al client, logga chiamata
```

Dopo 60 secondi, My Groq Key viene de-marcata e torna disponibile per le richieste successive.

---

## Gestione exhaustion

Quando una chiave supera il rate limit:

1. Il proxy riceve un 429 dal provider
2. Crea/aggiorna una riga in `exhaustion_state` per quella `api_key_id`
3. `exhausted_until = NOW() + 60s`
4. Il prossimo assignment in ordine di priority viene tentato
5. Ogni 60 secondi, lo scheduler elimina le righe di `exhaustion_state` scadute

Se tutti gli assignment di una virtual key sono esauriti contemporaneamente:
- Il proxy risponde `HTTP 503` al client
- Il body include `next_available_at` (il primo `exhausted_until` in scadenza)
