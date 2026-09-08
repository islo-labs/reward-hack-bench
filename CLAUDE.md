## Context

Benchmark for measuring execution-environment effectiveness at preventing
reward hacking in agent evaluations. Takes tasks from SWE-bench + CyBench,
injects cheat patterns (writeup lookup, upstream-fix, etc.) via an adapter,
scores each trial with both the original grader AND an LLM-as-judge.

**Headline metric:** `solved_fairly = static_reward × fairness`. Architecture
and rationale are in [`design.md`](design.md); read that before making
substantive changes. [`README.md`](README.md) shows end-users how to run.

## Environment

Do not create or use a Python virtual environment (`.venv`) in this project.
Harbor is installed globally via `uv tool install`; adapter scripts use
PEP 723 inline metadata. Avoid `uv sync` / `uv run` against this project.

Harbor must be installed from the **`reward-hack-bench-changeset-v2`** fork
branch — current upstream main (0.22.x; includes compose-in-islo and
backend-agnostic separate-mode verifiers) plus a slim port of the
phase-keyed raw gateway configs the sweep policies need:

```bash
uv tool install --force \
  --from 'git+https://github.com/islo-labs/harbor-fork@reward-hack-bench-changeset-v2#egg=harbor[islo]' \
  harbor
```

What this branch gives us:
- **Compose mode in islo** (upstream PR
  [#1559](https://github.com/harbor-framework/harbor/pull/1559), carried by
  the rebase): `docker-compose.yaml` detection takes priority over
  Dockerfile; the env spins up Docker Compose inside the islo VM.
  ezmaze / diffecient / noisier-crc are islo-runnable.
- **Separate-mode verifiers on islo** (upstream machinery + a fork fix):
  TB3-style tasks with `[verifier] environment_mode = "separate"` run the
  verifier in a second islo sandbox built from `tests/`. The fork adds a
  fix so image-baked `/tests` is not shadowed by the VM bind mount.
- **Phased gateway**: `gateway: { setup: {...}, agent: {...}, verifier:
  {...} }` — raw per-phase `GatewayConfig`s applied at lifecycle phase
  transitions, taking precedence over the portable NetworkPolicy
  conversion. Flat `gateway: {default_action, rules}` stays accepted
  (upstream behavior); mixing flat and phase keys in one dict is
  rejected. Unlisted phases default to permissive.
- **Content-based filtering** per rule:
  ```yaml
  rules:
    - host_pattern: "*"
      action: deny
      content_filter:
        direction: request | response | both
        filter_type: regex | content_type | size_limit
        pattern: "<regex/mime/bytes>"
  ```
  This is the more powerful axis — blocks by response body across hosts,
  mirrors, search-engine caches, etc.

When upstream merges the phase-keyed gateway into harbor-framework/harbor
main, switch back to
`git+https://github.com/harbor-framework/harbor#egg=harbor[islo]`.
(The old `reward-hack-bench-changeset` branch is untouched; the published
hero-run-v2 results remain reproducible against it.)

PyPI release is too old; bare `harbor` without the `[islo]` extra
won't load the islo backend.

## How the pieces fit

- **Source tasks** live under `datasets/<corpus>/<task>/`. Two shapes:
  SWE-bench (flat, `tests/config.json`, parser.py grader) and CTF
  (multi-container via `environment/docker-compose.yaml`, grep-F grader).
  The shape is either declared in the manifest's `task:` block or inferred
  from file contents.
- **`adapter/build.py`** reads `adapter/manifest.yaml` and generates
  cheating-augmented tasks under `datasets/reward-hack/<target_name>/`.
  Each entry combines a source + mode + `task:` facts (shape, flag,
  repo_url, writeup_urls) + `config:` (mode knobs).
- **`adapter/judge_template.py`** is the LLM-as-judge script injected into
  each generated task's `tests/judge.py`. Runs at verifier time, reads
  the agent trajectory, emits `judge.json` + single-key `reward.json`.
- **Running the generated tasks**: `harbor run -y -p datasets/reward-hack/<name>`.
- **The final sweep** lives in `experiments/hero-run-v2/` — all policy
  configs including the `open` and `network-none` baselines. Compact
  per-trial verdicts of the published run are tracked in `results/`;
  `experiments/hero-run-v2/extract_results.py` regenerates them from raw
  `jobs/` outputs and `render_dashboard_v2.py` renders `dashboard.html`
  from `results/`. The raw `jobs/` tree stays gitignored.

## Status (as of June 2026 — check `adapter/manifest.yaml` + `design.md` for ground truth)

**The benchmark is complete and published.** The hero-run-v2 sweep
(8 tasks × 7 policies × k=3, Opus 4.7) is the authoritative result set —
see the "Final results" section in `design.md`. Headline:
`llm-judge-request` is the only policy at cheat rate 0 while holding the
model's 0.58 fair-rate ceiling; `layered-tools-off` is the best static
policy (0.08).

**Validated cheat modes** (cheat fires, judge detects, `solved_fairly=0`):
- `upstream-fix` on all 4 SWE-bench tasks.
- `writeup-pointer` on all 4 CTF tasks.

**Commented out in manifest, awaiting validation or refuted**:
- `verifier-smuggle`, `grader-shortcut`, `writeup-pointer` on SWE-bench,
  `bg-reward-write`. See the manifest comments for per-mode status.

## Operational gotchas worth not re-learning

- **Harbor requires `-y` on `harbor run`** when tasks declare host env
  vars (e.g., `ANTHROPIC_API_KEY` passthrough in `[verifier.env]`).
  Without it the CLI prompts interactively and a background run will abort.
- **Harbor's built-in metrics (`Mean`/`Max`/`Min`/`Sum`) require single-key
  `reward.json`.** The adapter emits only `{"solved_fairly": X}`; full
  breakdown sits in `judge.json` sidecar.
- **IPv6 on Docker Desktop for macOS**: default bridge has IPv6 disabled,
  but container DNS still returns AAAA. Node-based HTTP clients (claude-code)
  can hang. Fix: `NODE_OPTIONS=--dns-result-order=ipv4first` in the agent
  Dockerfile. Applied in `datasets/cybench/ezmaze/environment/Dockerfile`.
- **Task name must be `org/name`** — adapter auto-namespaces under
  `reward-hack/` if the target_name has no slash.
- **uv bootstrap**: the adapter prepends a uv install-if-missing block to
  every generated test.sh because some sandbox environments (islo
  Docker-in-VM) don't preserve the Dockerfile's uv install into the
  runtime shell.
- **Claude Code inside docker-compose is slow** for long-reasoning tasks
  (Opus hit its 30-min timeout on ezmaze; same model direct-via-API solved
  in ~6 min). Prefer Haiku 4.5 for CTF-shape crypto tasks; give generous
  `agent.timeout_sec`.
- **islo multi-container support**: upstream's compose-in-VM (PR #1559)
  is included in the `reward-hack-bench-changeset-v2` branch —
  `IsloEnvironment` detects `docker-compose.yaml` and runs Compose inside
  the VM (priority over Dockerfile). CTF tasks (ezmaze, diffecient,
  noisier-crc) are islo-runnable on this branch.
- **Public writeup URLs rot.** The hackmd link in SekaiCTF's
  `solution/README.md` is already 404. Verify reachability when adding
  new CTF tasks.
- **Oracle agents look like cheaters to the judge** (they literally run
  the upstream solution). That's correct — oracle runs are for pipeline
  validation, not fairness measurement.

## Common commands

```bash
# Build all tasks from manifest
uv run adapter/build.py --manifest adapter/manifest.yaml

# Dry-run (show what would be generated without writing)
uv run adapter/build.py --manifest adapter/manifest.yaml --dry-run

# Smoke-test a generated task with the oracle solution
harbor run -y -p datasets/reward-hack/<target> -a oracle -k 1 -n 1

# Real agent run on a validated cheat demo
harbor run -y -p datasets/reward-hack/ezmaze__writeup-pointer \
  -a claude-code -m anthropic/claude-haiku-4-5 -k 1 -n 1

# Run a final-sweep job (full JobConfig in the YAML)
harbor run -y --config experiments/hero-run-v2/<name>.yaml

# Refresh tracked results + dashboard from raw jobs/ outputs
uv run --no-project experiments/hero-run-v2/extract_results.py
uv run --no-project experiments/hero-run-v2/render_dashboard_v2.py
```

## When making changes

- Adding a new cheat mode: `@register("name")` in `adapter/build.py`,
  signature `(src, dst, entry)`. Mode body is content-only — use the
  shape handler for any shape-specific plumbing.
- Adding a new source task: drop under `datasets/<corpus>/<task>/` with
  the canonical layout. Always add a manifest entry with explicit
  `task.shape` for clarity.
- Before any real-agent sweep on a new task: run the oracle (must give
  `static_reward=1`) and a nop variant of solve.sh (must give `=0`).
  Both gates must pass before investing API budget on real agents.
- Update `design.md` status table + `adapter/manifest.yaml` comments
  when a mode moves from unvalidated → validated or vice versa.
