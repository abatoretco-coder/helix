from __future__ import annotations

from helix_agent_client import HelixAgentClient, HelixAPIError


def main() -> None:
    helix = HelixAgentClient()
    try:
        capabilities = helix.capabilities()
        context = helix.context(mode="top", language="fr", limit=5)
    except HelixAPIError as exc:
        print(f"Helix unavailable: {exc}")
        return

    print(f"Connected to {capabilities['service']} {capabilities['version']}")
    print(f"Context articles: {len(context.get('articles', []))}")
    print(f"Recent memories: {len(context.get('recent_memories', []))}")
    print(f"Queued tasks: {len(context.get('queued_tasks', []))}")

    if context.get("articles"):
        first = context["articles"][0]
        if not context.get("queued_tasks"):
            task = helix.create_task(
                title="Summarize top Helix context",
                instructions="Create a short French synthesis from the current top article context.",
                source_article_ids=[item["id"] for item in context.get("articles", [])[:5]],
                input_payload={"article_count": len(context.get("articles", []))},
            )
            print(f"Created task #{task['id']}")

        claimed = helix.claim_task()
        if claimed.get("claimed"):
            print(f"Claimed task #{claimed['task']['id']}: {claimed['task']['title']}")

        helix.create_memory(
            memory_type="note",
            title="Jarvis connectivity check",
            content=f"Helix context reachable. Top article: {first.get('title')}",
            tags=["healthcheck", "jarvis"],
            source_article_ids=[first["id"]],
            source_urls=[first["url"]] if first.get("url") else [],
            confidence=1.0,
        )
        print("Stored connectivity note in Helix agent memories.")


if __name__ == "__main__":
    main()
