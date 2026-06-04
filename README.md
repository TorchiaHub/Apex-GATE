# Apex-GATE

> One key to rule them all.

---

## The idea

Every LLM provider gives you a key. You sign up to NVIDIA NIM, you get a key. OpenRouter, another key. Groq, another. You keep them in `.env` files, scattered across projects. When one hits the rate limit your app breaks. When you rotate a key you have to update every project that uses it.

**Apex-GATE inverts this.** You keep all your real keys in one place, behind a gateway you control. Everything else — your apps, your scripts, your experiments — talks to a single virtual key (`apg-…`) that never changes. The gateway decides which real key to use, in what order, with what fallback. You configure this once from a dashboard, not from code.

The philosophy is simple: **your infrastructure should absorb the complexity of managing multiple providers, not your applications.**

---

## What it does

- You add your real API keys (as many as you want, from any provider)
- You define routing rules: provider priority, rate-limit handling, fallback chains
- You generate virtual keys and hand them to your apps
- Your apps call `/v1/chat/completions` exactly as they would with OpenAI — Apex-GATE handles everything else

When a key gets rate-limited, the gateway retries with the next one automatically. When you add a new provider, your apps don't change. When you rotate a real key, same. The virtual key is the stable interface.

---

## This repository

```
apex-gate/                ← the product (FastAPI backend + React dashboard)
tools/
└── nvidia-free-models/   ← optional scraper that keeps the NVIDIA free-model catalog up to date
vendor/
└── litellm/              ← upstream LiteLLM reference (read-only)
```

**→ [apex-gate/README.md](apex-gate/README.md)** — setup, quick start, full technical reference

---

## NVIDIA free models

NVIDIA offers a large catalog of models for free under NIM. The scraper in `tools/nvidia-free-models/` fetches the current list and writes `latest.json`, which Apex-GATE reads at runtime to populate the model catalog automatically.

You don't need to run it manually — `latest.json` is included. Run it again when you want a fresh snapshot.

→ [`tools/nvidia-free-models/`](tools/nvidia-free-models/)

---

## AI agents

→ [`apex-gate/AGENTS.md`](apex-gate/AGENTS.md) — conventions and file map for AI-assisted development
