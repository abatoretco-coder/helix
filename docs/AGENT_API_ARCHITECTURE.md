# Agent API Architecture

Helix now exposes a dedicated agent contract under `/v1/agent/*`.

## Responsibility split

Helix is the durable intelligence service:

- collects and extracts articles,
- stores article summaries and embeddings,
- generates source-quality recommendations,
- stores briefings,
- stores durable agent memories and syntheses.

Jarvis is the reasoning client:

- asks for a compact context bundle,
- reasons over the provided articles, memories, and source recommendations,
- writes back durable summaries or decisions,
- can call source actions through the existing `/v1/sources/*` endpoints.

This keeps Jarvis stateless enough to run in its own Docker container while
Helix remains the source of truth.

## Endpoints

- `GET /v1/agent/capabilities`
- `GET /v1/agent/context`
- `GET /v1/agent/memories`
- `POST /v1/agent/memories`
- `GET /v1/agent/memories/{memory_id}`
- `DELETE /v1/agent/memories/{memory_id}`
- `POST /v1/agent/tasks`
- `GET /v1/agent/tasks`
- `POST /v1/agent/tasks/claim`
- `POST /v1/agent/tasks/{task_id}/complete`
- `POST /v1/agent/tasks/{task_id}/fail`
- `POST /v1/agent/tasks/{task_id}/cancel`

The context endpoint returns:

- latest briefing,
- top/recent/saved article cards,
- recent memories for the agent,
- source maintenance recommendations,
- queued tasks for the target agent,
- a small contract block that tells the agent how to answer and where to write
  durable syntheses.

## Docker topology

Recommended topology:

```text
Helix API container  <----HTTP + X-API-Token----  Jarvis container
PostgreSQL
Workers
Dashboard
```

Jarvis should use:

```bash
HELIX_API_URL=http://api:8000
HELIX_API_TOKEN=<HELIX_API_TOKEN>
```

An example container template is provided:

```text
docker/jarvis-agent.example.Dockerfile
docker/jarvis_agent_example.py
docker-compose.agent.example.yml
```

Run it with the main Compose file when the NAS is back:

```bash
docker compose -f docker-compose.yml -f docker-compose.agent.example.yml --profile agent up jarvis_agent_example
```

If Jarvis runs outside the Compose network, use:

```bash
HELIX_API_URL=http://<NAS_IP>:8000
```

## Python SDK

The Python client lives in:

```text
clients/python/helix_agent_client
```

Install it into a Jarvis container with:

```bash
pip install ./clients/python/helix_agent_client
```

Minimal usage:

```python
from helix_agent_client import HelixAgentClient

helix = HelixAgentClient()
context = helix.context(mode="top", language="fr", limit=10)
helix.create_memory(
    memory_type="synthesis",
    title="Daily synthesis",
    content="...",
    tags=["daily", "jarvis"],
)
```

## Persistence

Agent memories are stored in PostgreSQL table `agent_memories` with:

- `agent_id`,
- `memory_type`,
- `title`,
- `content`,
- `language`,
- `tags`,
- source article ids and source URLs,
- confidence,
- metadata.

This is intentionally generic so Jarvis can store daily summaries, ad hoc
syntheses, decisions, and notes without schema churn.

Agent tasks are stored in `agent_tasks` with:

- `queued`, `running`, `done`, `failed`, or `cancelled` status,
- target `agent_id`,
- task type and priority,
- natural-language instructions,
- optional input payload and source article ids,
- result payload,
- optional linked memory id.

Recommended task loop for Jarvis:

```python
claimed = helix.claim_task(agent_id="jarvis")
if claimed["claimed"]:
    task = claimed["task"]
    try:
        # reason over task["instructions"] and task["input_payload"]
        helix.complete_task(
            task["id"],
            result_payload={"status": "ok"},
            create_memory={
                "agent_id": "jarvis",
                "memory_type": "synthesis",
                "title": task["title"],
                "content": "...",
                "tags": ["task"],
            },
        )
    except Exception as exc:
        helix.fail_task(task["id"], error_message=str(exc))
```
