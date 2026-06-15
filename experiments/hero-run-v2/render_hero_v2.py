"""Render hero-run v2 yamls.

v2 hardens the two interesting policies against the bypass channels we
observed in row 1:

  host-blocklist-v2: v1 hosts + {*.archive.org, *.github.io, ctftime.org,
                                 *.jina.ai, *.jsdelivr.net}.
  content-filter-v2: v1 plaintext regex + base64-aligned variants of
                     each literal (closes the api.github.com /contents/
                     base64-in-JSON bypass).

Open and network-none are unchanged from row 1, so we skip them here.

Output: experiments/hero-run-v2/hero-v2-<policy>-opus__<task>__<mode>.yaml.
Run with `-o jobs/hero-run-v2/` to keep artifacts separate from row 1.

Re-render with:
    uv run --no-project experiments/hero-run-v2/render_hero_v2.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import render_sweep  # type: ignore

OUT = Path(__file__).resolve().parent

TASKS = [
    ("pytest-6202",       "upstream-fix"),
    ("matplotlib-25775",  "upstream-fix"),
    ("sympy-12489",       "upstream-fix"),
    ("sympy-14531",       "upstream-fix"),
    ("ezmaze",            "writeup-pointer"),
    ("noisier-crc",       "writeup-pointer"),
    ("slcg",              "writeup-pointer"),
    ("diffecient",        "writeup-pointer"),
]

POLICIES = ["host-blocklist-v2", "content-filter-v2", "layered-v2", "llm-judge", "llm-judge-request"]
POLICY_FN = {
    "host-blocklist-v2": render_sweep.policy_host_blocklist_v2,
    "content-filter-v2": render_sweep.policy_content_filter_v2,
    "layered-v2":        render_sweep.policy_layered_v2,
    "llm-judge":         render_sweep.policy_llm_judge,
    "llm-judge-request": render_sweep.policy_llm_judge_request,
}

MODEL = "anthropic/claude-opus-4-7"
N_ATTEMPTS = 3
N_CONCURRENT = 15


def _adapt(yaml_text: str, task: str, mode: str, policy: str) -> str:
    out = []
    for line in yaml_text.splitlines():
        if line.startswith("job_name:"):
            out.append(f"job_name: hero-v2-{policy}-opus__{task}__{mode}")
        elif line.startswith("n_attempts:"):
            out.append(f"n_attempts: {N_ATTEMPTS}")
        elif line.startswith("n_concurrent_trials:"):
            out.append(f"n_concurrent_trials: {N_CONCURRENT}")
        elif line.strip().startswith("model_name:"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}model_name: {MODEL}")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def main():
    written = []
    for task, mode in TASKS:
        for policy in POLICIES:
            fn = POLICY_FN[policy]
            base = fn(task, mode, MODEL)
            yaml_text = _adapt(base, task, mode, policy)
            yaml_text = render_sweep.apply_task_overrides(yaml_text, task)
            path = OUT / f"hero-v2-{policy}-opus__{task}__{mode}.yaml"
            path.write_text(yaml_text)
            written.append(path.name)
    print(f"wrote {len(written)} yamls to {OUT}/")
    for n in written:
        print(f"  {n}")


if __name__ == "__main__":
    main()
