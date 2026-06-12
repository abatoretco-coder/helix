import os
import secrets

from fastapi import Header, HTTPException


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def require_api_token(x_api_token: str | None = Header(default=None, alias="X-API-Token")) -> None:
    """Optional service-to-service token auth for contractual v1 endpoints.

    Controlled by env vars:
    - REQUIRE_API_TOKEN=true|false
    - HELIX_API_TOKEN=<secret>
    """
    enforce = _is_true(os.environ.get("REQUIRE_API_TOKEN", "false"))
    if not enforce:
        return

    expected = os.environ.get("HELIX_API_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="Server token auth is enabled but HELIX_API_TOKEN is not configured")

    if not x_api_token or not secrets.compare_digest(x_api_token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Token")
