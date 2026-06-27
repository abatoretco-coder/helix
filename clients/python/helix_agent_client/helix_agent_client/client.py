from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class HelixAPIError(RuntimeError):
    """Raised when Helix returns a non-2xx response or cannot be reached."""


@dataclass(slots=True)
class HelixAgentClient:
    """Minimal client for a Jarvis-like agent talking to Helix.

    Environment defaults:
      HELIX_API_URL=http://localhost:8000
      HELIX_API_TOKEN=<optional token>
    """

    base_url: str = os.environ.get("HELIX_API_URL", "http://localhost:8000")
    api_token: str | None = os.environ.get("HELIX_API_TOKEN") or None
    timeout_seconds: int = 30

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        query_string = f"?{urlencode({k: v for k, v in (query or {}).items() if v is not None})}" if query else ""
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.api_token:
            headers["X-API-Token"] = self.api_token

        request = Request(
            f"{self.base_url}{path}{query_string}",
            data=payload,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status == 204:
                    return None
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HelixAPIError(f"Helix API returned {exc.code}: {detail}") from exc
        except URLError as exc:
            raise HelixAPIError(f"Helix API unavailable: {exc.reason}") from exc

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/v1/health")

    def capabilities(self) -> dict[str, Any]:
        return self._request("GET", "/v1/agent/capabilities")

    def context(
        self,
        *,
        agent_id: str = "jarvis",
        profile_id: str = "default",
        mode: str = "top",
        language: str = "fr",
        category: str | None = None,
        limit: int = 12,
        min_score: float | None = None,
        include_source_recommendations: bool = True,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/agent/context",
            query={
                "agent_id": agent_id,
                "profile_id": profile_id,
                "mode": mode,
                "language": language,
                "category": category,
                "limit": limit,
                "min_score": min_score,
                "include_source_recommendations": str(include_source_recommendations).lower(),
            },
        )

    def ask(
        self,
        query: str,
        *,
        mode: str = "search",
        language: str = "fr",
        max_sources: int = 8,
        include_links: bool = True,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/jarvis/query",
            body={
                "query": query,
                "mode": mode,
                "language": language,
                "max_sources": max_sources,
                "include_links": include_links,
            },
        )

    def source_recommendations(self, limit: int = 50) -> dict[str, Any]:
        return self._request("GET", "/v1/sources/recommendations", query={"limit": limit})

    def list_memories(
        self,
        *,
        agent_id: str = "jarvis",
        memory_type: str | None = None,
        tag: str | None = None,
        limit: int = 30,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/agent/memories",
            query={
                "agent_id": agent_id,
                "memory_type": memory_type,
                "tag": tag,
                "limit": limit,
            },
        )

    def create_memory(
        self,
        *,
        title: str,
        content: str,
        agent_id: str = "jarvis",
        memory_type: str = "summary",
        language: str = "fr",
        tags: list[str] | None = None,
        source_article_ids: list[int] | None = None,
        source_urls: list[str] | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/agent/memories",
            body={
                "agent_id": agent_id,
                "memory_type": memory_type,
                "title": title,
                "content": content,
                "language": language,
                "tags": tags or [],
                "source_article_ids": source_article_ids or [],
                "source_urls": source_urls or [],
                "confidence": confidence,
                "metadata": metadata or {},
            },
        )

    def delete_memory(self, memory_id: int) -> None:
        self._request("DELETE", f"/v1/agent/memories/{memory_id}")

    def create_task(
        self,
        *,
        title: str,
        instructions: str,
        agent_id: str = "jarvis",
        task_type: str = "synthesis",
        priority: int = 2,
        language: str = "fr",
        input_payload: dict[str, Any] | None = None,
        source_article_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/agent/tasks",
            body={
                "agent_id": agent_id,
                "task_type": task_type,
                "title": title,
                "instructions": instructions,
                "priority": priority,
                "language": language,
                "input_payload": input_payload or {},
                "source_article_ids": source_article_ids or [],
            },
        )

    def list_tasks(
        self,
        *,
        agent_id: str = "jarvis",
        status: str = "queued",
        task_type: str | None = None,
        limit: int = 30,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/agent/tasks",
            query={
                "agent_id": agent_id,
                "status": status,
                "task_type": task_type,
                "limit": limit,
            },
        )

    def claim_task(self, *, agent_id: str = "jarvis", task_type: str | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/agent/tasks/claim",
            query={"agent_id": agent_id, "task_type": task_type},
        )

    def complete_task(
        self,
        task_id: int,
        *,
        result_payload: dict[str, Any] | None = None,
        memory_id: int | None = None,
        create_memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/agent/tasks/{task_id}/complete",
            body={
                "result_payload": result_payload or {},
                "memory_id": memory_id,
                "create_memory": create_memory,
            },
        )

    def fail_task(
        self,
        task_id: int,
        *,
        error_message: str,
        result_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/agent/tasks/{task_id}/fail",
            body={"error_message": error_message, "result_payload": result_payload or {}},
        )

    def cancel_task(self, task_id: int) -> dict[str, Any]:
        return self._request("POST", f"/v1/agent/tasks/{task_id}/cancel")
