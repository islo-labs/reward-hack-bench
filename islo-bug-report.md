# Sandbox lifecycle regression: 500 INTERNAL_ERROR on create_sandbox, and VMs entering `paused` state ~75s into trials

## Summary

Since approximately 2026-06-01, sandbox-backed harbor trials are failing
with one of two errors at consistent points in the trial lifecycle:

1. `500 INTERNAL_ERROR` on `POST /sandboxes` (sandbox create) — fails
   within ~8 seconds of trial start.
2. `409 SANDBOX_INVALID_STATE: VM is in state 'paused', expected 'running'`
   on `POST /sandboxes/{name}/exec` — fails ~75 seconds into the trial,
   *after* a successful `create_sandbox` and (in compose-based runs)
   a successful docker build inside the VM.

The same workload ran successfully on 2026-05-31 (4 days ago) on the
same harbor binary against the same yaml shape — single trial of
`ezmaze` completed in 81 min, judged FAIR with `static_reward=1.0`.

## Severity

**Blocker.** No sandbox-backed trials can be completed against the
`rotemtam` org at this time. 8 attempted trials over a ~60 min window
all failed, none reached the agent execution phase.

## Account / environment

- Org: `rotemtam`
- Tier: `team`
- `islo --version`: (CLI installed via uv tool)
- `harbor --version`: `v0.6.6`
- harbor branch: `islo-labs/harbor-fork@reward-hack-bench-changeset`
- Auth (verified fresh after `islo logout && islo login`):
  - `Status: Logged in`
  - `Expires: 2026-06-04 21:59:21 UTC`

The earlier (stale) auth showed `Expires: 2026-05-28 20:26:31 UTC` but
re-authenticating did not change the failure pattern.

## Failure timing pattern

Across 4 attempts (8 trials total: 2 tasks × 4 attempts):

| attempt | task          | failure mode                                    | elapsed |
|---------|---------------|--------------------------------------------------|---------|
| 1       | ezmaze        | 500 INTERNAL_ERROR on `create_sandbox`           | 8s      |
| 1       | pytest-6202   | 409 VM paused on `exec_in_sandbox`               | 48s     |
| 2       | ezmaze        | 409 VM paused on `exec_in_sandbox`               | 75s     |
| 2       | pytest-6202   | 409 VM paused on `exec_in_sandbox`               | 77s     |
| 3       | ezmaze        | 500 INTERNAL_ERROR on `create_sandbox`           | 8s      |
| 3       | pytest-6202   | 409 VM paused on `exec_in_sandbox`               | 20s     |
| 4 (re-auth) | ezmaze    | 500 INTERNAL_ERROR on `create_sandbox`           | 8s      |
| 4 (re-auth) | pytest-6202 | 409 VM paused on `exec_in_sandbox`             | 75s     |

The bimodal timing (8s vs ~75s) is suspicious — it suggests two distinct
backend code paths failing, both deterministically reachable.

## Sandbox / VM / profile IDs

Identifiers from the most recent attempt (2026-06-04 ~10:00 UTC) — useful
for tracing the VM state machine on islo's side:

```
ezmaze attempt:
  gateway profile id: 019e9213-05e1-73e8-8188-dd4a7b4e4396
  (no VM id — failure was at create_sandbox, never returned)

pytest-6202 attempt:
  gateway profile id: 019e9213-05b8-719c-a662-0dd263a834b9
  VM id: 019e9213-0716-7061-b746-5f0b13ff585d
```

Earlier attempts in the same window:
```
019e91df-2227-7e41-85f4-0a7bab36e6d8  (pytest attempt 1, VM paused 409)
019e91e0-a482-7350-9bdd-57af8fdb8f1d  (pytest attempt 2, VM paused 409)
019e91e0-a900-75d3-8e41-c6e8e2f319e6  (ezmaze attempt 2, VM paused 409)
019e920f-34dc-7062-ae47-ec5ce895517c  (pytest attempt 3, VM paused 409)
```

## Reproduction

Workload: harbor trial of either of:

- `experiments/hero-run-v2/smoke-sonnet-judge__ezmaze.yaml` — CTF, uses
  `docker-compose.yaml` in the task.
- `experiments/hero-run-v2/smoke-sonnet-judge__pytest-6202.yaml` —
  SWE-bench task, uses a Dockerfile (no compose).

Both use:
- `environment.type: islo`
- A judge content_filter rule (`provider_key: anthropic`,
  `model: claude-sonnet-4-6`, `timeout_seconds: 30`,
  `direction: request`)
- Two allow-priority-10 rules for `api.anthropic.com` and `api.openai.com`
- Default action `allow` in all three phases

Command:
```bash
harbor run -y -c experiments/hero-run-v2/smoke-sonnet-judge__ezmaze.yaml \
  -o jobs/hero-run-v2/
```

Both tasks fail. Both error types are reproducible.

## Full error bodies

### 500 INTERNAL_ERROR (ezmaze, attempt 4):

```json
{
  "code": "INTERNAL_ERROR",
  "message": "An internal error occurred"
}
```

Status: 500
Date: `Thu, 04 Jun 2026 09:59:44 GMT`
Server: `nginx/1.31.1`

Stack trace tail (Python client):
```
File ".../islo/sandboxes/raw_client.py", line 2487, in create_sandbox
    raise ApiError(status_code=_response.status_code, ...)
```

The failure is at the very first call (`create_sandbox`) — no VM ever
gets allocated.

### 409 SANDBOX_INVALID_STATE (pytest-6202, attempt 4):

```json
{
  "code": "SANDBOX_INVALID_STATE",
  "message": "VM '019e9213-0716-7061-b746-5f0b13ff585d' is in state 'paused', expected 'running'"
}
```

Status: 409
Date: `Thu, 04 Jun 2026 10:00:43 GMT`
Server: `nginx/1.31.1`

Stack trace tail (Python client):
```
File ".../islo/sandboxes/raw_client.py", line 4171, in exec_in_sandbox
    raise ApiError(status_code=_response.status_code, ...)
```

Sequence on islo side leading up to this:
1. `create_sandbox` returned 200 with VM `019e9213-0716-7061-b746-5f0b13ff585d`.
2. Harbor ran docker build inside the VM — succeeded ("Docker build succeeded"
   appears in trial.log).
3. Harbor's next `exec_in_sandbox` call returned 409 — the VM had transitioned
   to `paused` state without harbor requesting it.

## What changed since the last success

- Last known successful trial: 2026-05-31 14:19 local — `ezmaze`
  completed in 81 min, fair-solved.
- Code-side changes since then: only swapped the judge prompt body and
  judge model name in the yaml. No changes to harbor, no changes to the
  task definitions, no changes to islo CLI.

## Local diagnostics already attempted

- Cleared all sandboxes via `islo rm` → no effect.
- `islo logout && islo login` to force a fresh token → no effect; same
  errors recur.
- 8 trials across 4 attempts at 10-minute intervals — pattern persists.

## What would help debug

1. islo VM state-transition log for any of the listed VM IDs — what
   triggered the `running → paused` transition.
2. islo server logs for the listed gateway profile IDs around the
   reported timestamps.
3. Whether the 500 INTERNAL_ERROR on `create_sandbox` correlates with a
   known islo deploy / version bump in the past ~72 hours.

Happy to provide trial.log / exception.txt files for any of the trials
above on request.
