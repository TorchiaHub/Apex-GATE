# Apex-GATE — Monorepo

This repository contains **Apex-GATE** and its supporting tooling.

```
apex-gate/          ← the product  (FastAPI backend + React dashboard)
tools/
└── nvidia-free-models/   ← scraper that produces the free-model catalog (latest.json)
vendor/
└── litellm/        ← upstream LiteLLM reference (do not modify)
```

## Get started

→ **[apex-gate/README.md](apex-gate/README.md)** — setup, quick start, full project map

## Repository layout

| Folder | Role | Edit? |
|---|---|---|
| `apex-gate/` | The product | ✅ yes |
| `tools/nvidia-free-models/` | Generates the NVIDIA free-model catalog read by the backend at runtime via `NVIDIA_FREE_MODELS_PATH` | ⚠️ scraper only |
| `vendor/litellm/` | Upstream LiteLLM copy kept as reference | ❌ no |

> If you move `tools/nvidia-free-models/`, update `NVIDIA_FREE_MODELS_PATH` in `apex-gate/backend/app/config.py`.

## AI agents

→ [`apex-gate/AGENTS.md`](apex-gate/AGENTS.md) — conventions, file map, and guidelines for AI-assisted development
