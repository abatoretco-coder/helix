import os
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


def _is_true(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _news_summary_provider() -> str:
    return os.environ.get("NEWS_SUMMARY_PROVIDER", "local").strip().lower()


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
        "agent_api": True,
        "agent_memory_supported": True,
        "news_items_supported": True,
        "news_summary_supported": True,
        "dashboard_synthesis_supported": True,
        "jarvis_contextual_synthesis_supported": True,
        "openai_usage_supported": True,
        "openai_request_limits_supported": True,
        "news_summary_provider": _news_summary_provider(),
        "jarvis_answer_provider": os.environ.get("LLM_PROVIDER", "openai").strip().lower(),
        "background_ai_enabled": _is_true(os.environ.get("BACKGROUND_AI_ENABLED", "false")),
        "openai_usage_policy": "on_demand",
    }
