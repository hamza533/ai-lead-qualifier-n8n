"""Create the ai_* custom contact properties in HubSpot (idempotent).

    uv run python -m scripts.hubspot_setup        # make hubspot-setup

Needs HUBSPOT_PRIVATE_APP_TOKEN with the crm.schemas.contacts.read/write scopes.
Existing properties are left as they are.
"""

from __future__ import annotations

from typing import Any

import httpx

from scripts.envfile import read_env

GROUP = "contactinformation"
PROPERTIES: list[dict[str, Any]] = [
    {"name": "ai_lead_score", "label": "AI lead score", "type": "number", "fieldType": "number",
     "description": "0-100 fit score computed by LeadPilot from the ICP criteria."},
    {"name": "ai_lead_tier", "label": "AI lead tier", "type": "enumeration",
     "fieldType": "select", "description": "Hot (>= 70), warm (40-69) or cold (< 40).",
     "options": [{"label": "Hot", "value": "hot", "displayOrder": 0},
                 {"label": "Warm", "value": "warm", "displayOrder": 1},
                 {"label": "Cold", "value": "cold", "displayOrder": 2}]},
    {"name": "ai_score_reasons", "label": "AI score reasons", "type": "string",
     "fieldType": "textarea", "description": "Per-criterion ratings and one-line reasons."},
    {"name": "ai_last_processed", "label": "AI last processed", "type": "datetime",
     "fieldType": "date", "description": "When LeadPilot last scored this contact."},
]  # fmt: skip


def ensure_properties(client: httpx.Client) -> list[tuple[str, str]]:
    """Create missing properties; returns (name, "created" | "exists") for each."""
    results = []
    for prop in PROPERTIES:
        res = client.get(f"/crm/v3/properties/contacts/{prop['name']}")
        if res.status_code == 200:
            results.append((prop["name"], "exists"))
            continue
        if res.status_code != 404:
            res.raise_for_status()
        client.post(
            "/crm/v3/properties/contacts", json={**prop, "groupName": GROUP}
        ).raise_for_status()
        results.append((prop["name"], "created"))
    return results


def main() -> None:
    env = read_env()
    token = env.get("HUBSPOT_PRIVATE_APP_TOKEN", "")
    if not token or "CHANGE_ME" in token:
        raise SystemExit("Set HUBSPOT_PRIVATE_APP_TOKEN in .env first (see README, HubSpot setup).")
    base = env.get("HUBSPOT_BASE_URL", "https://api.hubapi.com").rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base, headers=headers, timeout=30) as client:
        try:
            for name, status in ensure_properties(client):
                print(f"{status:8} {name}")
        except httpx.HTTPStatusError as exc:
            raise SystemExit(
                f"HubSpot answered {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc


if __name__ == "__main__":
    main()
