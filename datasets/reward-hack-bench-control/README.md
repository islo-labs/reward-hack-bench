# reward-hack-bench-control

The clean baseline companion to `islo-labs/reward-hack-bench`: the same 8
SWE-bench + CyBench tasks with **no cheat prompt**. It measures the model's
natural solve rate and whether it reaches for the published solution
unprompted, with the same fairness judge attached — and doubles as a Harbor
packaging of these CyBench / GlacierCTF and SWE-bench-Verified tasks.

- **Code & methodology:** https://github.com/islo-labs/reward-hack-bench
- **Writeup:** https://islo.dev/blog/reward-hack-bench-sandbox-stops-agent-cheating/

```bash
harbor run -d islo-labs/reward-hack-bench-control@latest -a claude-code -m anthropic/claude-opus-4-7
```

The benchmark with cheat paths injected: `islo-labs/reward-hack-bench`.
