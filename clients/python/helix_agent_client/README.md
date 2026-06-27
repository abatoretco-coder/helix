# Helix Agent Client

Small Python client for a Jarvis-like agent running in another process or
container.

## Install

From this repository:

```bash
pip install ./clients/python/helix_agent_client
```

In a Jarvis container, mount or copy this folder and install it during image
build.

## Environment

```bash
HELIX_API_URL=http://api:8000
HELIX_API_TOKEN=<HELIX_API_TOKEN>
```

Use `http://api:8000` when Jarvis is on the same Docker Compose network as
Helix. Use `http://<NAS_IP>:8000` from another host on the LAN.

## Example

```python
from helix_agent_client import HelixAgentClient

helix = HelixAgentClient()

context = helix.context(mode="top", language="fr", limit=10)
answer = helix.ask("Quels sont les signaux faibles importants aujourd'hui ?", language="fr")

helix.create_memory(
    memory_type="synthesis",
    title="Synthese IA et cyber",
    content=answer["answer"],
    tags=["ia", "cyber", "veille"],
    source_urls=[source["url"] for source in answer.get("sources", []) if source.get("url")],
    confidence=answer.get("confidence"),
)
```

Task loop:

```python
claimed = helix.claim_task(agent_id="jarvis")
if claimed["claimed"]:
    task = claimed["task"]
    try:
        helix.complete_task(
            task["id"],
            result_payload={"summary": "done"},
            create_memory={
                "agent_id": "jarvis",
                "memory_type": "synthesis",
                "title": task["title"],
                "content": "Synthese produite par Jarvis.",
                "tags": ["task"],
            },
        )
    except Exception as exc:
        helix.fail_task(task["id"], error_message=str(exc))
```

## Product Contract

Helix is the durable intelligence store:

- articles and summaries,
- source quality and recommendations,
- briefings,
- saved/read/hidden user state,
- agent memories.

Jarvis is the reasoning client:

- fetch context with `GET /v1/agent/context`,
- answer through its own model or `POST /v1/jarvis/query`,
- store durable syntheses with `POST /v1/agent/memories`,
- read prior syntheses with `GET /v1/agent/memories`.
- claim persistent work with `POST /v1/agent/tasks/claim`.
- complete or fail tasks with result payloads and optional memory writeback.
