# Home Assistant Integration

## Current scope (skeleton)

Helix exposes webhook-friendly endpoints for Home Assistant integration:

- `POST /home-assistant/briefing-ready`
- `POST /home-assistant/alert`
- `POST /v1/home-assistant/briefing-ready`
- `POST /v1/home-assistant/alert`

The current implementation validates payloads and records events for observability.

## Payload examples

### Briefing ready

```json
{
  "date": "2026-06-13",
  "category": "all",
  "briefing_id": 42,
  "message": "Daily briefing generated"
}
```

### Alert

```json
{
  "alert_type": "worker_failure",
  "severity": "critical",
  "message": "worker_extract restarted 3 times",
  "source": "helix"
}
```

## Next steps

- Send Home Assistant mobile notifications when briefing is ready.
- Trigger TTS briefing playback on smart speakers.
- Emit alerts for worker crashes and queue saturation.
- Add retry/backoff delivery for outbound webhooks.
