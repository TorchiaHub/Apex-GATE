from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

# Allow running this script directly from backend/scripts.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.crypto import generate_virtual_key


@dataclass
class VirtualKeyInfo:
    plaintext: str
    vk_id: str
    user_id: str
    api_key_id: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(sep=" ")


def create_test_virtual_key(db_path: str, user_id: str, api_key_id: str, name: str) -> VirtualKeyInfo:
    plaintext, key_hash = generate_virtual_key()
    vk_id = str(uuid.uuid4())
    assign_id = str(uuid.uuid4())
    key_prefix = plaintext[:12]
    now = _now_iso()

    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            INSERT INTO virtual_keys (
                id, user_id, name, key_hash, key_prefix, daily_token_budget,
                allowed_providers, model_preference, is_enabled, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vk_id,
                user_id,
                name,
                key_hash,
                key_prefix,
                None,
                None,
                None,
                1,
                now,
            ),
        )
        con.execute(
            """
            INSERT INTO virtual_key_assignments (id, vk_id, api_key_id, priority)
            VALUES (?, ?, ?, ?)
            """,
            (assign_id, vk_id, api_key_id, 10),
        )
        con.commit()
    finally:
        con.close()

    return VirtualKeyInfo(
        plaintext=plaintext,
        vk_id=vk_id,
        user_id=user_id,
        api_key_id=api_key_id,
    )


def probe(proxy_base_url: str, virtual_key: str, model: str) -> None:
    url = f"{proxy_base_url.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": "Rispondi sempre in una frase corta."},
            {"role": "user", "content": "Rispondi con OK_TEST se mi ricevi."},
        ],
    }
    r = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {virtual_key}", "Content-Type": "application/json"},
        timeout=45,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Probe failed [{r.status_code}]: {r.text[:400]}")

    body = r.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    print("[probe] status=200")
    print(f"[probe] model={r.headers.get('X-Model-Used', 'n/a')}")
    print(f"[probe] provider={r.headers.get('X-Provider-Used', 'n/a')}")
    print(f"[probe] answer={content}")


def chat_loop(proxy_base_url: str, virtual_key: str, model: str) -> None:
    url = f"{proxy_base_url.rstrip('/')}/v1/chat/completions"
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "Sei un assistente rapido e conciso."}
    ]
    print("Mini chatbot pronto. Scrivi 'exit' per uscire.")

    while True:
        user_text = input("you> ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print("bye")
            return

        messages.append({"role": "user", "content": user_text})
        payload = {
            "model": model,
            "stream": False,
            "messages": messages,
        }
        r = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {virtual_key}", "Content-Type": "application/json"},
            timeout=60,
        )
        if r.status_code != 200:
            print(f"err> HTTP {r.status_code}: {r.text[:300]}")
            continue

        body = r.json()
        reply = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        messages.append({"role": "assistant", "content": reply})
        model_used = r.headers.get("X-Model-Used", "n/a")
        provider_used = r.headers.get("X-Provider-Used", "n/a")
        print(f"bot[{provider_used}]> {reply}")
        print(f"meta> model={model_used}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick terminal chatbot to test APEX GATE virtual key behavior.")
    parser.add_argument("--proxy-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--virtual-key", default=None)
    parser.add_argument("--db-path", default="data/apex_gate.db")
    parser.add_argument("--bootstrap", action="store_true", help="Create a fresh test virtual key in DB.")
    parser.add_argument("--user-id", default="21c9fa77-9edf-408d-b17a-289a5d1bfaf9")
    parser.add_argument("--api-key-id", default="de26d486-18b3-4e3a-9291-6677d362d41b")
    parser.add_argument("--name", default="quick-cli-test")
    parser.add_argument("--model", default="auto")
    args = parser.parse_args()

    vk = args.virtual_key
    if args.bootstrap:
        info = create_test_virtual_key(
            db_path=args.db_path,
            user_id=args.user_id,
            api_key_id=args.api_key_id,
            name=args.name,
        )
        vk = info.plaintext
        print(f"[bootstrap] created virtual key id={info.vk_id}")
        print(f"[bootstrap] plaintext={info.plaintext}")

    if not vk:
        raise SystemExit("Missing virtual key. Pass --virtual-key or use --bootstrap.")

    probe(args.proxy_base_url, vk, args.model)
    chat_loop(args.proxy_base_url, vk, args.model)


if __name__ == "__main__":
    main()
