"""Call the ops webhook from the command line.

uv run python -m scripts.ops run_digest
uv run python -m scripts.ops run_reminders
uv run python -m scripts.ops replay ld_0123456789ab
"""

from __future__ import annotations

import argparse
import json

import httpx

from scripts.envfile import read_env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run_digest", "run_reminders", "replay"])
    parser.add_argument("lead_id", nargs="?", default="")
    args = parser.parse_args()
    if args.action == "replay" and not args.lead_id:
        parser.error("replay needs a lead id")
    env = read_env()
    body = {"action": args.action, **({"lead_id": args.lead_id} if args.lead_id else {})}
    res = httpx.post(
        f"{env.get('N8N_URL', 'http://localhost:5678')}/webhook/ops", json=body, timeout=120,
        headers={"X-LeadPilot-Ops-Token": env["OPS_WEBHOOK_TOKEN"]},
    )  # fmt: skip
    print(res.status_code, json.dumps(res.json(), indent=2))
    raise SystemExit(0 if res.status_code < 400 else 1)


if __name__ == "__main__":
    main()
