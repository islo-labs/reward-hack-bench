# reward-hack-bench

Can sandboxes stop a coding agent from **cheating** — fetching the
published solution instead of solving the task?

8 tasks (4 SWE-bench + 4 CyBench), each with a solution-retrieval cheat path
baked into the prompt. Every trial is scored twice: did the grader pass
(`static_reward`), and did the agent avoid retrieving and integrating the
solution (`fairness`, an LLM judge over the full trajectory). Dataset reward =
**solved without cheating**.

With open networking, Claude Opus 4.7 cheats on every trial; the right network
policy drives that to zero without hurting honest solves. Full results and
methodology in the writeup.

- **Code & methodology:** https://github.com/islo-labs/reward-hack-bench
- **Writeup:** https://islo.dev/blog/reward-hack-bench-sandbox-stops-agent-cheating/

```bash
harbor run -d islo-labs/reward-hack-bench@latest -a claude-code -m anthropic/claude-opus-4-7
```

Clean baseline (same tasks, no cheat prompt): `islo-labs/reward-hack-bench-control`.
