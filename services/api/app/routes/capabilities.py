import os
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


def _is_true(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


@router.get("/")
async def get_capabilities():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inbox": True,
        "watchlist_config": True,
        "research_projects_config": True,
        "dead_queues": True,
        "obsidian_export": _is_true(os.environ.get("OBSIDIAN_EXPORT_ENABLED", "false")),
        "home_assistant_skeleton": False,
        "read_state_supported": True,
        "db_watchlist_supported": True,
        "db_projects_supported": True,
    }
