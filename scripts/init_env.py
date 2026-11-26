"""Create .env from .env.example and fill the generated secrets.

Idempotent: existing values are never overwritten, only CHANGE_ME_GENERATED
placeholders are replaced.
"""

from __future__ import annotations

import secrets
import shutil

import bcrypt

from scripts.envfile import ENV_PATH, ROOT, read_env, set_values

PLACEHOLDER = "CHANGE_ME_GENERATED"


def main() -> None:
    if not ENV_PATH.exists():
        shutil.copy(ROOT / ".env.example", ENV_PATH)
        print("created .env from .env.example")

    env = read_env()
    updates: dict[str, str] = {}

    generated = (
        "N8N_ENCRYPTION_KEY",
        "WEBHOOK_HMAC_SECRET",
        "DB_POSTGRESDB_PASSWORD",
        "N8N_RUNNERS_AUTH_TOKEN",
    )
    for key in generated:
        if env.get(key) == PLACEHOLDER:
            updates[key] = secrets.token_hex(32 if key != "DB_POSTGRESDB_PASSWORD" else 16)

    password = env.get("N8N_OWNER_PASSWORD", "")
    if password == PLACEHOLDER:
        # n8n requires 8+ chars with a number and an uppercase letter
        password = "Lp1" + secrets.token_urlsafe(18)
        updates["N8N_OWNER_PASSWORD"] = password
    if (
        env.get("N8N_INSTANCE_OWNER_PASSWORD_HASH") in (PLACEHOLDER, "")
        or "N8N_OWNER_PASSWORD" in updates
    ):
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()
        updates["N8N_INSTANCE_OWNER_PASSWORD_HASH"] = f"'{hashed}'"

    if updates:
        set_values(updates)
        print("generated: " + ", ".join(sorted(updates)))
    else:
        print(".env already initialised")

    missing = [k for k, v in read_env().items() if v == "CHANGE_ME"]
    if missing:
        print("still to fill in .env when you reach that step: " + ", ".join(missing))


if __name__ == "__main__":
    main()
