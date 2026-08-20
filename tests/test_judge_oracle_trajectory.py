"""Regression tests for oracle-run trajectory plumbing.

Harbor's built-in `oracle` agent runs a task's reference solution script
directly and writes only `/logs/agent/oracle.txt` (its stdout) — it never
produces the ATIF `/logs/agent/trajectory.json` every other agent
implementation writes. Before this fix, that meant every oracle verifier
run short-circuited to `judge_status=trajectory_missing_or_empty` and the
fairness judge never actually evaluated the oracle path, breaking the
CONTRIBUTING.md pipeline-validation gate (`harbor run -a oracle` must
exercise the judge; `-a nop` must still score `solved_fairly=0`).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "adapter"))

from judge_template import _find_oracle_log, _synthesize_oracle_trajectory  # noqa: E402

JUDGE_PY = ROOT / "adapter" / "judge_template.py"


def _run_judge(trajectory: Path, config: Path, env_overrides: dict[str, str]) -> dict:
    env = {**os.environ, **env_overrides}
    env.pop("ANTHROPIC_API_KEY", None)
    if "ANTHROPIC_API_KEY" in env_overrides:
        env["ANTHROPIC_API_KEY"] = env_overrides["ANTHROPIC_API_KEY"]
    result = subprocess.run(
        [sys.executable, str(JUDGE_PY), "--trajectory", str(trajectory), "--config", str(config)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _write_config(tmp_path: Path) -> Path:
    config = tmp_path / "judge_config.json"
    config.write_text(json.dumps({"mode": "upstream-fix", "forbidden_information": "n/a"}))
    return config


def test_find_oracle_log_absent(tmp_path):
    trajectory_path = tmp_path / "trajectory.json"
    assert _find_oracle_log(trajectory_path) is None


def test_find_oracle_log_ignores_empty_file(tmp_path):
    trajectory_path = tmp_path / "trajectory.json"
    (tmp_path / "oracle.txt").write_text("")
    assert _find_oracle_log(trajectory_path) is None


def test_find_oracle_log_present(tmp_path):
    trajectory_path = tmp_path / "trajectory.json"
    oracle_log = tmp_path / "oracle.txt"
    oracle_log.write_text("patching file lib/matplotlib/text.py\n")
    assert _find_oracle_log(trajectory_path) == oracle_log


def test_synthesize_oracle_trajectory_wraps_log_verbatim(tmp_path):
    oracle_log = tmp_path / "oracle.txt"
    oracle_log.write_text("patching file lib/matplotlib/text.py\n")

    trajectory = json.loads(_synthesize_oracle_trajectory(oracle_log))

    assert trajectory["agent"]["name"] == "oracle"
    step_contents = [
        result["content"]
        for step in trajectory["steps"]
        for result in step.get("observation", {}).get("results", [])
    ]
    assert step_contents == ["patching file lib/matplotlib/text.py\n"]
    # No content beyond the oracle's own log is introduced.
    assert "diff --git" not in json.dumps(trajectory)


def test_main_reports_trajectory_missing_when_no_oracle_log(tmp_path):
    trajectory = tmp_path / "trajectory.json"  # never written
    config = _write_config(tmp_path)

    verdict = _run_judge(trajectory, config, env_overrides={})

    assert verdict["judge_status"] == "trajectory_missing_or_empty"
    assert verdict["fairness"] is None


def test_main_falls_back_to_oracle_log_when_trajectory_missing(tmp_path):
    trajectory = tmp_path / "trajectory.json"  # never written by the oracle agent
    (tmp_path / "oracle.txt").write_text("patching file lib/matplotlib/text.py\n")
    config = _write_config(tmp_path)

    # No ANTHROPIC_API_KEY: main() should get past the trajectory check via
    # the synthesized oracle trajectory and fail later, at the API-key gate —
    # proving the oracle path is no longer treated as missing/empty.
    verdict = _run_judge(trajectory, config, env_overrides={})

    assert verdict["judge_status"] == "no_api_key"


def test_main_prefers_real_trajectory_over_oracle_log(tmp_path):
    trajectory = tmp_path / "trajectory.json"
    trajectory.write_text(json.dumps({"agent": {"name": "claude-code"}, "steps": []}))
    (tmp_path / "oracle.txt").write_text("patching file lib/matplotlib/text.py\n")
    config = _write_config(tmp_path)

    verdict = _run_judge(trajectory, config, env_overrides={})

    # Still reaches the same next gate (no API key) — a real, non-empty
    # trajectory.json is never displaced by a sibling oracle.txt.
    assert verdict["judge_status"] == "no_api_key"
