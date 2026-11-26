"""Post the sample leads in sample_data/leads.jsonl to the signed webhook.

    uv run python -m scripts.seed            # all sample leads
    uv run python -m scripts.seed --file x.jsonl

Each request is signed exactly like a form tool would sign it:
    X-Signature-256: sha256=<hex HMAC-SHA256(raw body, WEBHOOK_HMAC_SECRET)>
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path

import httpx

from scripts.envfile import ROOT, read_env


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=ROOT / "sample_data" / "leads.jsonl")
    args = parser.parse_args()

    env = read_env()
    url = env.get("N8N_URL", "http://localhost:5678") + "/webhook/lead"
    with httpx.Client(timeout=60) as client:
        for line in args.file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            body = json.dumps(json.loads(line)).encode()
            headers = {
                "content-type": "application/json",
                "X-Signature-256": sign(body, env["WEBHOOK_HMAC_SECRET"]),
            }
            res = client.post(url, content=body, headers=headers)
            print(f"{res.status_code} {res.text[:120]}")


if __name__ == "__main__":
    main()
