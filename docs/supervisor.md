# Supervisor Logic

## Routing Decision Schema

Supervisor responds with strict JSON every turn:

```json
{
  "next_agent": "devops",
  "intent": "infrastructure_write",
  "confidence": 0.92,
  "reason": "Task requires creating a Dockerfile",
  "goal_for_agent": "Create a multi-stage Dockerfile for the Go app",
  "done": false
}
```

## Intent Categories

| Intent | Routes to |
|---|---|
| `code_read` | backend |
| `code_write` | backend |
| `infrastructure` | devops |
| `infrastructure_write` | devops |
| `test_run` | qa |
| `info_request` | any / finish |

## Fallback Route

If `confidence < CONFIDENCE_THRESHOLD` (default 0.55):

```
backend → qa
devops  → qa
qa      → backend
```

Set threshold via env: `CONFIDENCE_THRESHOLD=0.55`

## Loop Detection

If same agent appears in the last 3 routing decisions → stop with error `routing_loop`.

Tracked in `state.routing_history`.

## Retry / Escalation

If agent returns empty or error response:
- Retry up to `MAX_RETRIES_PER_AGENT = 2`
- After max retries → escalate (stop with `escalation:<agent>` error)

## Iteration Limit

Hard stop at `MAX_ITERATIONS` (default 8). Set via env: `MAX_ITERATIONS=8`

## Supervisor Log

Every routing decision is appended to `state.supervisor_log`:

```json
{
  "ts": "2026-03-15T10:00:00Z",
  "iteration": 2,
  "intent": "infrastructure_write",
  "confidence": 0.92,
  "next_agent": "devops",
  "reason": "...",
  "done": false
}
```
