"""
memory_demo.py
==============
Dimostra la memoria conversazionale lato server di APEX GATE.

Strategia:
  - crea una virtual key 'vk-memory-test' con memory_mode='optional',
    assegnata alla chiave nvidia (stessa key_encrypted del demo failover)
  - Richiesta 1: il client comunica un fatto, inviando SOLO quel messaggio,
    con header X-Conversation-Id = <uuid>
  - Richiesta 2: il client chiede di ricordare il fatto, inviando di nuovo
    SOLO la nuova domanda, con lo STESSO X-Conversation-Id
  - Se la memoria funziona, il modello ricorda il fatto della richiesta 1
    anche se il client non l'ha re-inviato (opzione a: history lato server).

Utilizzo:
  cd apex-gate/backend
  .venv/Scripts/python.exe scripts/memory_demo.py [--proxy http://127.0.0.1:8000]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.crypto import generate_virtual_key

USER_ID = "21c9fa77-9edf-408d-b17a-289a5d1bfaf9"
PROVIDER_NVIDIA = "2406e0fa-584c-43a1-ac08-2fda07829920"
NVIDIA_KEY_ENCRYPTED = (
    "gAAAAABqGZF11_GalxxocVGmpVdBpyX9iO1HsksObj0IAJkwJZStzmPpOyHSFMNsIY7yUNX6HkHG"
    "Dn6d8IzXbdh9-dEtX8qr_bNmtponzM21t5tqAMG_16BeyQfU1PbUanHzOoDFkKCixsJ_hVWa3s"
    "WYdl5n59Ji2xoEknGZq5jEJ7MKQwLJR9M="
)

SEP = "─" * 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(sep=" ")


def setup_db(db_path: str) -> tuple[str, str]:
    """Crea la VK con memoria e una api_key nvidia dedicata. Ritorna (vk_id, plaintext)."""
    con = sqlite3.connect(db_path)
    try:
        # pulizia run precedenti
        row = con.execute(
            "SELECT id FROM api_keys WHERE name='nvidia-mem' AND user_id=?", (USER_ID,)
        ).fetchone()
        if row:
            old = row[0]
            con.execute("DELETE FROM virtual_key_assignments WHERE api_key_id=?", (old,))
            con.execute("DELETE FROM exhaustion_state WHERE api_key_id=?", (old,))
            con.execute("DELETE FROM api_keys WHERE id=?", (old,))
        row = con.execute(
            "SELECT id FROM virtual_keys WHERE name='vk-memory-test' AND user_id=?",
            (USER_ID,),
        ).fetchone()
        if row:
            old_vk = row[0]
            con.execute("DELETE FROM virtual_key_assignments WHERE vk_id=?", (old_vk,))
            con.execute(
                "DELETE FROM conversation_messages WHERE conversation_id IN "
                "(SELECT id FROM conversations WHERE virtual_key_id=?)",
                (old_vk,),
            )
            con.execute("DELETE FROM conversations WHERE virtual_key_id=?", (old_vk,))
            con.execute("DELETE FROM virtual_keys WHERE id=?", (old_vk,))
        con.commit()

        now = _now_iso()
        ak_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO api_keys
               (id, user_id, provider_id, name, key_encrypted, tier, priority,
                rate_limit_rpm, rate_limit_rpd, budget_daily_usd, is_enabled, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ak_id, USER_ID, PROVIDER_NVIDIA, "nvidia-mem", NVIDIA_KEY_ENCRYPTED,
             "free", 1, 38, None, None, 1, now, now),
        )

        plaintext, key_hash = generate_virtual_key()
        vk_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO virtual_keys
               (id, user_id, name, key_hash, key_prefix, daily_token_budget,
                allowed_providers, model_preference, is_enabled, created_at,
                memory_mode, memory_max_messages, memory_max_context_tokens, memory_ttl_hours)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (vk_id, USER_ID, "vk-memory-test", key_hash, plaintext[:12],
             None, None, None, 1, now, "optional", 50, 8000, 720),
        )
        con.execute(
            "INSERT INTO virtual_key_assignments (id,vk_id,api_key_id,priority) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), vk_id, ak_id, 1),
        )
        con.commit()
    finally:
        con.close()
    return vk_id, plaintext


def chat(proxy: str, vk: str, model: str, prompt: str, conv_id: str | None) -> tuple[str, str | None]:
    headers = {"Authorization": f"Bearer {vk}", "Content-Type": "application/json"}
    if conv_id:
        headers["X-Conversation-Id"] = conv_id
    r = requests.post(
        f"{proxy.rstrip('/')}/v1/chat/completions",
        json={"model": model, "stream": False, "messages": [{"role": "user", "content": prompt}]},
        headers=headers,
        timeout=90,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    content = r.json()["choices"][0]["message"]["content"]
    return content, r.headers.get("X-Conversation-Id")


def dump_conversation(db_path: str, vk_id: str) -> None:
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            """SELECT cm.role, cm.content, cm.token_count, cm.created_at
               FROM conversation_messages cm
               JOIN conversations c ON c.id = cm.conversation_id
               WHERE c.virtual_key_id = ?
               ORDER BY cm.created_at""",
            (vk_id,),
        ).fetchall()
        print(f"  messaggi salvati in DB: {len(rows)}")
        for role, content, tokens, created in rows:
            short = content if len(content) <= 80 else content[:77] + "..."
            print(f"    [{role:9}] ({tokens} tok) {short}")
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo memoria conversazionale lato server.")
    parser.add_argument("--proxy", default="http://127.0.0.1:8000")
    parser.add_argument("--db-path", default="data/apex_gate.db")
    parser.add_argument("--model", default="meta/llama-4-maverick-17b-128e-instruct")
    args = parser.parse_args()

    print(SEP)
    print("SETUP: creo vk-memory-test (memory_mode='optional')")
    vk_id, vk = setup_db(args.db_path)
    conv_id = str(uuid.uuid4())
    print(f"  vk_id={vk_id}")
    print(f"  virtual key: {vk}")
    print(f"  X-Conversation-Id: {conv_id}")

    print()
    print(SEP)
    print("RICHIESTA 1 — comunico un fatto (invio SOLO questo messaggio)")
    r1, echoed1 = chat(args.proxy, vk, args.model,
                       "Ricorda questo: il mio numero fortunato è 7421. Rispondi solo 'OK'.",
                       conv_id)
    print(f"  prompt: 'il mio numero fortunato è 7421'")
    print(f"  risposta: {r1}")
    print(f"  X-Conversation-Id ricevuto: {echoed1}")

    print()
    print(SEP)
    print("RICHIESTA 2 — chiedo di ricordare (NON re-invio il fatto)")
    r2, echoed2 = chat(args.proxy, vk, args.model,
                       "Qual è il mio numero fortunato? Rispondi solo con il numero.",
                       conv_id)
    print(f"  prompt: 'qual è il mio numero fortunato?'")
    print(f"  risposta: {r2}")

    print()
    print(SEP)
    print("VERIFICA MEMORIA")
    ok = "7421" in r2
    print(f"  il modello ricorda 7421? {'SI ✓' if ok else 'NO ✗'}")
    dump_conversation(args.db_path, vk_id)

    print()
    print(SEP)
    print("CONTROLLO: stessa VK SENZA X-Conversation-Id → nessuna memoria")
    r3, echoed3 = chat(args.proxy, vk, args.model,
                       "Qual è il mio numero fortunato? Se non lo sai dillo.",
                       None)
    print(f"  risposta (stateless): {r3[:120]}")
    print(f"  X-Conversation-Id ricevuto: {echoed3} (atteso: None)")

    print(SEP)
    print("Demo completata." + ("  ESITO: MEMORIA OK ✓" if ok else "  ESITO: memoria NON confermata"))


if __name__ == "__main__":
    main()
