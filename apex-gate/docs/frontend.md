# APEX GATE — Architettura Frontend

Documento di riferimento per chi lavora sulla UI. Descrive la **struttura reale** del codice in `apex-gate/frontend/src/`.

> Se cerchi avvio e gotchas, parti dal [README](../README.md). Se sei un agente AI, leggi prima [AGENTS.md](../AGENTS.md).

---

## Stack

| Componente | Tecnologia | Versione |
|---|---|---|
| Linguaggio | TypeScript (strict) | 5.6 |
| Framework | React | 19 |
| Build tool | Vite | 6 |
| Routing | React Router | 7 |
| State globale | Zustand | 5 |
| Server state | TanStack Query | 5 |
| HTTP client | Axios | 1.7 |
| Charts | Recharts | 2 |
| Styling | CSS Modules + design tokens | — |
| Package manager | **npm** | — |

Script (`package.json`): `dev` (Vite :5173) · `build` (`tsc -b && vite build`) · `preview` · `lint` (`tsc --noEmit`).

---

## Struttura directory (reale)

```
frontend/src/
├── main.tsx              ← entry point (QueryClientProvider, RouterProvider)
├── App.tsx               ← definizione route + ProtectedRoute + AppShell
├── api/
│   ├── client.ts         ← istanza axios (baseURL "/") + interceptor JWT/refresh
│   ├── auth.ts           ← login, register, refresh, getMe, updateMe, logout
│   ├── chat.ts           ← client PROXY multi-formato (vedi sezione dedicata)
│   ├── keys.ts           ← API keys reali
│   ├── virtualKeys.ts    ← virtual key
│   ├── providers.ts      ← provider + modelli
│   ├── models.ts         ← catalogo modelli
│   ├── logs.ts           ← request log
│   ├── stats.ts          ← statistiche
│   └── admin.ts          ← gestione utenti (admin)
├── store/
│   ├── authStore.ts      ← Zustand: accessToken, refreshToken, user, isAuthenticated, setTokens, setUser, clearAuth
│   └── ui.ts             ← stato UI
├── components/
│   ├── Layout/           ← AppShell.tsx, Sidebar.tsx (+ .module.css)
│   ├── ProtectedRoute/   ← guard route autenticate
│   └── ui/               ← Badge.tsx, Button.tsx (+.module.css), Card.tsx, Input.tsx, Modal.tsx
├── pages/                ← UNA PAGINA = UN FILE .tsx (struttura PIATTA, non cartelle)
│   ├── Dashboard.tsx (+.module.css)
│   ├── Chat.tsx
│   ├── Stats.tsx (+.module.css)
│   ├── ApiKeys.tsx
│   ├── VirtualKeys.tsx
│   ├── Logs.tsx
│   ├── Providers.tsx
│   ├── Models.tsx (+.module.css)
│   ├── Admin.tsx
│   ├── Settings.tsx (+.module.css)
│   └── Login.tsx (+.module.css)
├── hooks/
│   └── useProviderStatus.ts   ← WebSocket /ws/status
├── utils/
│   └── keyDetect.ts
└── styles/
    ├── tokens.css        ← design system (CSS custom properties)
    ├── reset.css
    └── global.css
```

> ⚠️ Le pagine sono **file `.tsx` piatti** in `pages/`, non sottocartelle. Idem i componenti `ui/` sono file singoli.

---

## Routing (`App.tsx`)

Tutte le route (tranne `/login`) sono lazy-loaded e avvolte in `ProtectedRoute` → `AppShell`:

| Route | Pagina | Note |
|---|---|---|
| `/` | Dashboard | overview |
| `/chat` | Chat | test multi-formato del proxy |
| `/stats` | Stats | grafici Recharts |
| `/keys` | ApiKeys | chiavi reali dei provider |
| `/virtual-keys` | VirtualKeys | virtual key `apg-…` |
| `/logs` | Logs | request log |
| `/providers` | Providers | provider + modelli |
| `/models` | Models | catalogo modelli |
| `/admin` | Admin | **solo admin** |
| `/settings` | Settings | profilo utente |
| `/login` | Login | pubblica |

`QueryClient`: `staleTime` 10s, `retry` 1.

---

## Autenticazione e chiamate API

### `api/client.ts` (dashboard, JWT)
- Istanza axios con `baseURL "/"` → le richieste passano dal **proxy Vite** verso il backend `:8000`.
- **Request interceptor**: aggiunge `Authorization: Bearer <accessToken>` letto da `authStore`.
- **Response interceptor**: su `401/403` tenta un refresh tramite una `refreshPromise` condivisa; se fallisce, `clearAuth()` e redirect a `/login`.

### `authStore.ts` (Zustand)
Tiene `accessToken`, `refreshToken`, `user`, `isAuthenticated` e le azioni `setTokens`, `setUser`, `clearAuth`. `AppShell` verifica `isAuthenticated` e chiama `getMe()` al mount.

### Pattern dati
Usa **TanStack Query** per il server state (niente duplicazione nello store). Le funzioni in `api/*.ts` sono i fetcher; le pagine le consumano via `useQuery`/`useMutation`.

---

## Chat multi-formato (feature chiave)

La pagina `pages/Chat.tsx` permette di testare il proxy con i 4 protocolli. **A differenza del resto della dashboard, chiama il proxy direttamente** su `PROXY_BASE_URL` (`import.meta.env.VITE_PROXY_BASE_URL ?? "http://localhost:8000"`), bypassando il proxy Vite → per questo il backend deve avere l'origine del frontend in `CORS_ORIGINS`.

`api/chat.ts` espone:
- `ApiFormat = "openai" | "anthropic" | "gemini" | "ollama"`
- `API_FORMATS`: array `{ value, label }` per il `<select>` "Formato API".
- `FORMAT_SPECS`: per ogni formato `{ path, buildBody, parse }` — endpoint, costruzione body e parsing della risposta.
- `sendChatCompletion({ virtualKey, model, messages, format?, conversationId?, signal? })`.

Le funzioni di gestione conversazioni (history server-side) usano invece l'istanza `client.ts` (JWT).

**Shape risposta per formato** (campo letto dal parser):

| Formato | Endpoint | Campo testo |
|---|---|---|
| openai | `/v1/chat/completions` | `choices[0].message.content` |
| anthropic | `/anthropic/v1/messages` | `content[0].text` |
| gemini | `/gemini/v1/generateContent` | `candidates[0].content.parts[].text` |
| ollama | `/ollama/api/chat` | `message.content` |

**Stato persistito in `localStorage`** (chiavi): `apex-chat-virtual-key`, `apex-chat-system-prompt`, `apex-chat-keys`, `apex-chat-format`.
Invio: **Enter** invia, **Shift+Enter** newline. Streaming solo su formato `openai`.

---

## Design system (`styles/tokens.css`)

Tema **scuro**, tutto su CSS custom properties. Usa **sempre** le variabili, mai valori hardcoded.

```css
/* Sfondi */
--color-bg-base:#07070d  --color-bg-surface:#0f0f1a  --color-bg-elevated:#161625  --color-bg-overlay:#1e1e30
--color-border: rgba(255,255,255,0.07)
/* Accento */
--color-accent:#6366f1  --color-accent-hover:#818cf8
/* Stato (ognuno con variante -dim) */
success:#34d399  warning:#fbbf24  error:#f87171
/* Testo */
--color-text-primary  (white .92)  --color-text-secondary (.55)  --color-text-muted (.3)
/* Font */
--font-sans: Inter   --font-mono: JetBrains Mono
/* Scale */
--text-xs … --text-4xl   --weight-normal … --weight-bold
--space-1 … --space-16   --radius-sm/md/lg/xl/full
--shadow-sm/md/lg/accent  --duration-fast/normal/slow  --ease-out
/* Layout */
--sidebar-width:220px   --header-height:56px
```

I componenti hanno il loro `*.module.css` che referenzia questi token.

---

## Navigazione (`components/Layout/Sidebar.tsx`)

Logo "APEX GATE / LLM Proxy ▲". Gruppi:
- **Overview**: Dashboard ◈ · Chat ◐ · Stats ◉
- **Keys**: API Keys ⚿ · Virtual Keys ⬡
- **Observability**: Request Logs ≡ · Providers ⬗ · Models ⬙
- **System** (solo admin): Admin ⚙
- Settings ⚒

`AppShell.tsx` rende `Sidebar` + `<Outlet />`.

---

## Vite (`vite.config.ts`)

- Dev server porta **5173**.
- Proxy verso il backend: `/api`, `/auth`, `/v1` → `http://localhost:8000`; `/ws` → `ws://localhost:8000` (`ws: true`).
- Build: `outDir: dist`, `sourcemap: false`.

> Ricorda: la pagina **Chat** non usa questo proxy (va diretta a `:8000`). Tutte le altre chiamate sì.

---

## Dove intervenire (per il lavoro sul frontend)

| Vuoi… | Tocca |
|---|---|
| Aggiungere/modificare una pagina | `pages/*.tsx` (+ eventuale `*.module.css`) e la route in `App.tsx` |
| Aggiungere voce di menu | `components/Layout/Sidebar.tsx` |
| Componenti riusabili | `components/ui/` (Badge, Button, Card, Input, Modal) |
| Chiamare un nuovo endpoint | aggiungi una funzione in `api/<risorsa>.ts` (usa `client.ts`) |
| Colori/spaziature/tipografia | `styles/tokens.css` (mai valori hardcoded nei componenti) |
| Stato auth/utente | `store/authStore.ts` |
| Logica del proxy/Chat | `api/chat.ts` + `pages/Chat.tsx` |

Dopo ogni modifica: `npm run lint` (type-check) e verifica in `npm run dev`.
