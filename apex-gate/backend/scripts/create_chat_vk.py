"""
create_chat_vk.py
=================
Crea una virtual key dedicata alla pagina Chat della dashboard, con
memory_mode='off' (la UI gestisce la cronologia lato client).

La key viene assegnata alle api_key esistenti dell'utente (tutte), così
il routing/failover funziona. Stampa il PLAINTEXT una sola volta: incollalo
nel campo "Virtual key" della pagina Chat.

Uso:
  cd apex-gate/backend
  .venv/Scripts/python.exe scripts/create_chat_vk.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.crypto import generate_virtual_key  # noqa: E402

USER_ID = "21c9fa77-9edf-408d-b17a-289a5d1bfaf9"
VK_NAME = "vk-chat"
DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "apex_gate.db")
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(sep=" ")


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    try:
        # Rimuovi eventuale vk-chat precedente (e relative assegnazioni).
        old = con.execute(
            "SELECT id FROM virtual_keys WHERE name=? AND user_id=?", (VK_NAME, USER_ID)
        ).fetchone()
        if old:
            con.execute(
                "DELETE FROM virtual_key_assignments WHERE vk_id=?", (old[0],)
            )
            con.execute("DELETE FROM virtual_keys WHERE id=?", (old[0],))

        plaintext, key_hash = generate_virtual_key()
        vk_id = str(uuid.uuid4())
        con.execute(
            """
            INSERT INTO virtual_keys
                (id, user_id, name, key_hash, key_prefix, daily_token_budget,
                 allowed_providers, model_preference, is_enabled,
                 memory_mode, memory_max_messages, memory_max_context_tokens,
                 memory_ttl_hours, created_at)
            VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, 1, 'off', 50, 8000, 720, ?)
            """,
            (vk_id, USER_ID, VK_NAME, key_hash, plaintext[:12], _now_iso()),
        )

        # Assegna tutte le api_key dell'utente (priorità per ordine di creazione).
        api_keys = con.execute(
            "SELECT id FROM api_keys WHERE user_id=? ORDER BY created_at ASC",
            (USER_ID,),
        ).fetchall()
        for priority, (api_key_id,) in enumerate(api_keys, start=10):
            con.execute(
                """
                INSERT INTO virtual_key_assignments (id, vk_id, api_key_id, priority)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), vk_id, api_key_id, priority),
            )

        con.commit()

        print("─" * 60)
        print(f"  Virtual key '{VK_NAME}' creata (memory_mode=off)")
        print(f"  id        : {vk_id}")
        print(f"  api_keys  : {len(api_keys)} assegnate")
        print("─" * 60)
        print("  INCOLLA QUESTA KEY nella pagina Chat (mostrata solo ora):")
        print()
        print(f"    {plaintext}")
        print()
        print("─" * 60)
    finally:
        con.close()


if __name__ == "__main__":
    main()
