"""
failover_demo.py
================
Dimostra il passaggio automatico di chiavi (failover) nelle virtual key di APEX GATE.

Strategia:
  - nvidia-A  → priorità 1, stessa chiave cifrata di 'nvidia' esistente
  - nvidia-B  → priorità 2, stessa chiave cifrata di 'nvidia' esistente
  - virtual key 'vk-failover-test' assegnata ad entrambe

Flusso:
  1. Richiesta 1 → passa per nvidia-A  (priorità più alta)
  2. Simula esaurimento di nvidia-A inserendo un exhaustion_state in futuro
  3. Richiesta 2 → passa per nvidia-B  (failover automatico)
  4. Stampa request_log con api_key_id usato per ogni richiesta
  5. Reset: rimuove exhaustion_state

Utilizzo:
  cd apex-gate/backend
  .venv/Scripts/python.exe scripts/failover_demo.py [--proxy http://127.0.0.1:8000] [--model meta/llama-4-maverick-17b-128e-instruct]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.crypto import generate_virtual_key

USER_ID  = "21c9fa77-9edf-408d-b17a-289a5d1bfaf9"
PROVIDER_NVIDIA = "2406e0fa-584c-43a1-ac08-2fda07829920"
# Stessa chiave cifrata della API key 'nvidia' già presente in DB
NVIDIA_KEY_ENCRYPTED = (
    "gAAAAABqGZF11_GalxxocVGmpVdBpyX9iO1HsksObj0IAJkwJZStzmPpOyHSFMNsIY7yUNX6HkHG"
    "Dn6d8IzXbdh9-dEtX8qr_bNmtponzM21t5tqAMG_16BeyQfU1PbUanHzOoDFkKCixsJ_hVWa3s"
    "WYdl5n59Ji2xoEknGZq5jEJ7MKQwLJR9M="
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(sep=" ")


def setup_db(db_path: str) -> tuple[str, str, str, str]:
    """Crea nvidia-A, nvidia-B e la virtual key failover. Ritorna (id_a, id_b, vk_id, vk_plaintext)."""
    con = sqlite3.connect(db_path)
    try:
        # Pulisce eventuali run precedenti dello stesso script
        for name in ("nvidia-A", "nvidia-B"):
            row = con.execute("SELECT id FROM api_keys WHERE name=? AND user_id=?", (name, USER_ID)).fetchone()
            if row:
                old_id = row[0]
                con.execute("DELETE FROM virtual_key_assignments WHERE api_key_id=?", (old_id,))
                con.execute("DELETE FROM exhaustion_state WHERE api_key_id=?", (old_id,))
                con.execute("DELETE FROM api_keys WHERE id=?", (old_id,))
        row = con.execute("SELECT id FROM virtual_keys WHERE name='vk-failover-test' AND user_id=?", (USER_ID,)).fetchone()
        if row:
            old_vk = row[0]
            con.execute("DELETE FROM virtual_key_assignments WHERE vk_id=?", (old_vk,))
            con.execute("DELETE FROM virtual_keys WHERE id=?", (old_vk,))
        con.commit()

        now = _now_iso()
        id_a = str(uuid.uuid4())
        id_b = str(uuid.uuid4())

        # nvidia-A: priorità 1 (verrà usata per prima)
        con.execute(
            """INSERT INTO api_keys
               (id, user_id, provider_id, name, key_encrypted, tier, priority,
                rate_limit_rpm, rate_limit_rpd, budget_daily_usd, is_enabled, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (id_a, USER_ID, PROVIDER_NVIDIA, "nvidia-A", NVIDIA_KEY_ENCRYPTED,
             "free", 1, 38, None, None, 1, now, now),
        )
        # nvidia-B: priorità 2 (fallback)
        con.execute(
            """INSERT INTO api_keys
               (id, user_id, provider_id, name, key_encrypted, tier, priority,
                rate_limit_rpm, rate_limit_rpd, budget_daily_usd, is_enabled, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (id_b, USER_ID, PROVIDER_NVIDIA, "nvidia-B", NVIDIA_KEY_ENCRYPTED,
             "free", 2, 38, None, None, 1, now, now),
        )

        # Virtual key assegnata ad A (priority=1) e B (priority=2)
        plaintext, key_hash = generate_virtual_key()
        vk_id = str(uuid.uuid4())
        key_prefix = plaintext[:12]
        con.execute(
            """INSERT INTO virtual_keys
               (id, user_id, name, key_hash, key_prefix, daily_token_budget,
                allowed_providers, model_preference, is_enabled, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (vk_id, USER_ID, "vk-failover-test", key_hash, key_prefix,
             None, None, None, 1, now),
        )
        con.execute(
            "INSERT INTO virtual_key_assignments (id,vk_id,api_key_id,priority) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), vk_id, id_a, 1),
        )
        con.execute(
            "INSERT INTO virtual_key_assignments (id,vk_id,api_key_id,priority) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), vk_id, id_b, 2),
        )
        con.commit()
    finally:
        con.close()

    return id_a, id_b, vk_id, plaintext


def exhaust_key(db_path: str, api_key_id: str, minutes: int = 10) -> None:
    """Inserisce un exhaustion_state per api_key_id che scade tra `minutes` minuti."""
    exhausted_until = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat(sep=" ")
    con = sqlite3.connect(db_path)
    try:
        con.execute("DELETE FROM exhaustion_state WHERE api_key_id=?", (api_key_id,))
        con.execute(
            "INSERT INTO exhaustion_state (id,api_key_id,exhausted_until,reason,created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), api_key_id, exhausted_until, "rate_limit", _now_iso()),
        )
        con.commit()
    finally:
        con.close()


def reset_exhaustion(db_path: str, api_key_id: str) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute("DELETE FROM exhaustion_state WHERE api_key_id=?", (api_key_id,))
        con.commit()
    finally:
        con.close()


def get_last_api_key_used(db_path: str, vk_id: str) -> str | None:
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            """SELECT rl.api_key_id, ak.name, rl.model_id, rl.status, rl.created_at
               FROM request_logs rl
               JOIN api_keys ak ON ak.id = rl.api_key_id
               WHERE rl.virtual_key_id = ?
               ORDER BY rl.created_at DESC LIMIT 1""",
            (vk_id,),
        ).fetchone()
        if row:
            return f"api_key_id={row[0]}  name={row[1]}  model={row[2]}  status={row[3]}  at={row[4]}"
    finally:
        con.close()
    return None


def chat(proxy_base_url: str, virtual_key: str, model: str, prompt: str) -> str:
    url = f"{proxy_base_url.rstrip('/')}/v1/chat/completions"
    r = requests.post(
        url,
        json={"model": model, "stream": False, "messages": [{"role": "user", "content": prompt}]},
        headers={"Authorization": f"Bearer {virtual_key}", "Content-Type": "application/json"},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    content = r.json()["choices"][0]["message"]["content"]
    provider = r.headers.get("X-Provider-Used", "n/a")
    model_used = r.headers.get("X-Model-Used", "n/a")
    return f"[{provider}|{model_used}] {content}"


SEP = "─" * 60


def main() -> None:
    parser = argparse.ArgumentParser(description="Failover demo: mostra il passaggio automatico di chiavi nelle virtual key.")
    parser.add_argument("--proxy", default="http://127.0.0.1:8000")
    parser.add_argument("--db-path", default="data/apex_gate.db")
    parser.add_argument("--model", default="meta/llama-4-maverick-17b-128e-instruct")
    args = parser.parse_args()

    print(SEP)
    print("SETUP: creo nvidia-A (priorità 1) e nvidia-B (priorità 2)")
    id_a, id_b, vk_id, vk_plaintext = setup_db(args.db_path)
    print(f"  nvidia-A  id={id_a}")
    print(f"  nvidia-B  id={id_b}")
    print(f"  vk-failover-test  id={vk_id}")
    print(f"  virtual key: {vk_plaintext}")

    print()
    print(SEP)
    print("RICHIESTA 1 — nessuna esauzione → attesa: nvidia-A")
    reply1 = chat(args.proxy, vk_plaintext, args.model, "Rispondi solo con: RISPOSTA_1")
    print(f"  risposta: {reply1}")
    used1 = get_last_api_key_used(args.db_path, vk_id)
    print(f"  request_log: {used1}")

    print()
    print(SEP)
    print(f"SIMULO ESAURIMENTO di nvidia-A (id={id_a[:8]}…) per 10 min")
    exhaust_key(args.db_path, id_a)
    print("  exhaustion_state inserito ✓")

    print()
    print(SEP)
    print("RICHIESTA 2 — nvidia-A esaurita → attesa: nvidia-B (failover)")
    reply2 = chat(args.proxy, vk_plaintext, args.model, "Rispondi solo con: RISPOSTA_2")
    print(f"  risposta: {reply2}")
    used2 = get_last_api_key_used(args.db_path, vk_id)
    print(f"  request_log: {used2}")

    print()
    print(SEP)
    print("RESET exhaustion_state di nvidia-A")
    reset_exhaustion(args.db_path, id_a)
    print("  rimosso ✓")

    print()
    print(SEP)
    print("RICHIESTA 3 — reset completo → attesa: torna a nvidia-A")
    reply3 = chat(args.proxy, vk_plaintext, args.model, "Rispondi solo con: RISPOSTA_3")
    print(f"  risposta: {reply3}")
    used3 = get_last_api_key_used(args.db_path, vk_id)
    print(f"  request_log: {used3}")

    print()
    print(SEP)
    print("RIEPILOGO")
    for i, used in enumerate([used1, used2, used3], 1):
        print(f"  req {i}: {used}")

    print(SEP)
    print("Demo completata.")


if __name__ == "__main__":
    main()
