# /// script
# requires-python = ">=3.11"
# ///
"""Extract compact, trackable results from raw harbor job outputs.

Walks the same (task, mode, policy) matrix as render_dashboard_v2.py
(including __retry* job-dir variants) and copies, per trial, exactly the
files the dashboard reads:

    verifier/judge.json     judge verdict (fairness, static_reward, evidence)
    verifier/reward.txt     upstream-grader reward (SWE-bench control trials)
    verifier/reward.json    single-key solved_fairly (kept for completeness)
    result.json             trial result (agent cost)
    exception.txt           harness exception tail, if any
    trial.log               network-none trials only (legit-break detection)

plus the job-level config.json (the resolved harbor config — pins what
actually ran). Destination mirrors the jobs/ layout:

    jobs/hero-run-v2/<job>/<trial>/...  ->  results/hero-run-v2/<job>/<trial>/...

results/ is tracked in git so the dashboard is reproducible from a fresh
clone; the raw jobs/ tree (trajectories, container logs) stays gitignored.

    uv run --no-project experiments/hero-run-v2/extract_results.py
"""
from __future__ import annotations
import shutil
from pathlib import Path

import render_dashboard_v2 as dash

ROOT = dash.ROOT
JOBS = ROOT / "jobs"

TRIAL_FILES = [
    "verifier/judge.json",
    "verifier/reward.txt",
    "verifier/reward.json",
    "result.json",
    "exception.txt",
]


def copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def main():
    n_trials = n_files = 0
    # Clean slate: wipe the target sweep dirs so results/ exactly mirrors
    # POLICY_SOURCE + the current jobs/. Without this, job dirs that were
    # removed from jobs/ (e.g. retry fills replaced by a clean re-run) leave
    # orphaned copies behind in tracked results/.
    for results_dir in {d for (d, _, _) in dash.POLICY_SOURCE.values()}:
        if results_dir.exists():
            shutil.rmtree(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
    for policy in dash.POLICIES:
        results_dir, template, trial_prefix_t = dash.POLICY_SOURCE[policy]
        jobs_dir = JOBS / results_dir.name
        for (task, mode) in dash.TASKS:
            base = template.format(task=task, mode=mode)
            trial_prefix = trial_prefix_t.format(task=task, mode=mode)
            matching = [base] + sorted(
                d.name for d in jobs_dir.iterdir()
                if d.is_dir() and d.name.startswith(base + "__retry")
            )
            for jn in matching:
                job_dir = jobs_dir / jn
                if not job_dir.exists():
                    continue
                copy_if_exists(job_dir / "config.json",
                               results_dir / jn / "config.json")
                for trial_dir in sorted(job_dir.iterdir()):
                    if not trial_dir.is_dir():
                        continue
                    if not trial_dir.name.startswith(trial_prefix):
                        continue
                    dst_trial = results_dir / jn / trial_dir.name
                    wanted = list(TRIAL_FILES)
                    if policy == "network-none":
                        wanted.append("trial.log")
                    copied = sum(
                        copy_if_exists(trial_dir / rel, dst_trial / rel)
                        for rel in wanted
                    )
                    n_trials += 1
                    n_files += copied
    print(f"extracted {n_files} files across {n_trials} trials -> {dash.RESULTS}")


if __name__ == "__main__":
    main()
