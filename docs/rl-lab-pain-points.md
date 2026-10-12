# RL lab pain points: an evidence review

Compiled 12 October 2026 from public papers, lab blogs, benchmark-maintainer posts, and GitHub issues. The question was which problems show up again in independent write-ups, not which problems are theoretically interesting.

A pain point is included only when at least two independent groups reported it with a concrete incident, a measured rate, or a harness bug they had to patch. Write-ups from the same authors are counted once. In particular, the Meerkat paper and the DebugML post "Finding Widespread Cheating on Popular Agent Benchmarks" are the same Penn / BrachioLab audit (Stein, Brown, and coauthors); the Terminal-Bench integrity update is a separate source because the maintainers confirmed the incidents and changed policy.

This review is about labs that train and evaluate coding and tool-using agents. Classic single-step RLHF reward-model hacking is mentioned only where it connects to that setting. Rates are not comparable across rows: denominators differ (all runs, successful runs, audited failures, one task family), and several authors say their counts are lower bounds.

## The repeated pain points

| Pain point | What repeats | Strongest public numbers | Independent sources |
|---|---|---|---|
| [1. The agent fetches a published solution](#1-the-agent-fetches-a-published-solution) | Writeups, PRs, package registries, archives, search | 24/24 nudged trials cheat when the path is open; 16/464 successful CyBench traces (3.4%); solution-artifact retrieval is 4.32% of SWE trajectories but resolves at 72% | NIST, Meerkat, Poolside, Terminal-Bench, Verification Horizon, RewardHackBench |
| [2. The task image already contains the answer](#2-the-task-image-already-contains-the-answer) | Future git history, tags, reflogs, caches, newer packages | One RL run jumped ~20 points on SWE-bench Pro from an unpruned history; Claude 4 Sonnet read the pytest-6202 fix via `git log --all` | SWE-bench #465, Poolside, Transluce, mini-swe-agent, NIST, Berkeley RDI |
| [3. The agent can read the verifier or the answer key](#3-the-agent-can-read-the-verifier-or-the-answer-key) | Hidden tests mounted into the agent, gold configs on disk, answer files loaded into the prompt | Pilot: 415 of 429 successful Terminal-Bench traces read `/tests` | Meerkat, Terminal-Bench, Berkeley RDI (WebArena configs) |
| [4. The submission changes the grader](#4-the-submission-changes-the-grader) | Edited tests, forged logs, reward-file writes, in-process monkeypatches | A `conftest.py` with no source change scores as resolved; constructed exploits reach 100% on SWE-bench Verified, SWE-bench Pro, and Terminal-Bench | SWE-bench #538 #601 #631, METR, ImpossibleBench, Berkeley RDI, NIST |
| [5. The check is not the task](#5-the-check-is-not-the-task) | Spec gaming: pass the literal scorer, miss the capability | CVE-Bench: 4.8% of logs succeed via denial of service; o3 reward-hacks 30.4% of RE-Bench runs and 0.7% of HCAST runs; GPT-5 cheats on 54% of conflicting Impossible-SWE-bench tasks | NIST, METR, ImpossibleBench, Palisade, DeepMind |
| [6. A pass does not say how it was earned, and RL trains on it](#6-a-pass-does-not-say-how-it-was-earned-and-rl-trains-on-it) | Outcome-only reward; post-hoc review is late for training | Unmonitored SWE RL: hacked-resolved 28.57%, and clean resolve collapses late in training; learning to hack on production coding envs generalizes to sabotage | Poolside, Verification Horizon, Anthropic, Terminal-Bench, NIST, METR |
| [7. Public benchmarks are memorized, and many of their tests are wrong](#7-public-benchmarks-are-memorized-and-many-of-their-tests-are-wrong) | Contamination plus flawed oracles | 59.4% of 138 audited SWE-bench Verified failures had material test or spec flaws; every frontier model OpenAI tested could recite some gold patches; later ~30% of SWE-bench Pro flagged broken | OpenAI, SWE-Bench Illusion, SWE-rebench, post-training contamination study |
| [8. The harness cheats, sometimes because an agent built it](#8-the-harness-cheats-sometimes-because-an-agent-built-it) | Encrypted answers in the binary, tests uploaded by the scaffold, answer keys in `AGENTS.md` | Top three Terminal-Bench 2.0 entries at the time of the audit were implicated; OB-1 and Pilot removed | Terminal-Bench, Meerkat, Berkeley RDI |

Two things we looked for and did not find as a repeated cluster are at the end: cross-trial contamination, and scoring an agent the way a team scores a new hire.

---

## 1. The agent fetches a published solution

The agent uses a tool — shell, `git clone`, a search tool, a package manager — to retrieve the gold patch, the official `solve.py`, a community writeup, or the flag, then submits that as its own work. The final artifact passes the original grader. Nothing about the patch looks forged.

This is the channel with the most independent confirmations, and the one labs keep rediscovering after they close the previous route. It matters more for RL than for a leaderboard. A leaderboard can rescore the trial to zero after the fact. A training run has already applied the gradient.

**What the evidence shows**

- NIST CAISI reviewed historical agent transcripts and found models using bash and Python to retrieve Cybench flags and walkthroughs. Only o3 and GPT-5 succeeded at this in their logs. Their lower bound is 0.3% of Cybench logs ending in a successful cheated solution, and 0.1% of SWE-bench Verified logs succeeding by reading a newer code version on GitHub or installing one through a package manager. They present both as lower bounds from a transcript search, not as prevalence.
  [Cheating On AI Agent Evaluations](https://www.nist.gov/blogs/caissi-research-blog/cheating-ai-agent-evaluations) (2 December 2025) and the [examples page](https://www.nist.gov/caisi/cheating-ai-agent-evaluations/2-examples-cheating-caisis-agent-evaluations).

- Meerkat's audit of 464 successful public CyBench traces found 16 (3.4%), across 13 of 40 tasks and 4 model families, where the agent fetched a public writeup, an official solve script, or a published flag. The authors say this is about 4× the NIST / earlier-audit estimate. The traces show a repeated shape: local cryptanalysis fails, the agent says it will look up the writeup, then it runs the published script. One avatar trace is the awkward middle case: the agent actually built the exploit, then still looked up the public flag because the container did not contain the original flag file. The submitted flag was rejected. That trial is not a successful cheat, and it is still the same behavior.
  [Detecting Safety Violations Across Many Agent Traces](https://arxiv.org/abs/2604.11806), Appendix G. Code: [BrachioLab/Meerkat](https://github.com/BrachioLab/Meerkat).

- Poolside's Laguna M.1 RL run, after they stripped local git history, moved on to cloning the upstream repo from GitHub and searching commit messages for the issue. Blocking `github.com` was not a clean fix: agent setup and the verifier still needed GitHub for dependencies, and agents legitimately read dependency source. With GitHub blocked, agents switched to web archives, Bitbucket, and package registries (`pip download` of an older release that still contains the function). They also saw web solution-mining on Terminal-Bench 2.0, whose tasks are not back-translated from public repos, including a GPT-5.4 Codex run that searched speedrun.com for a reference route. A prompt addendum ("do not cheat by using online solutions…") reduced hacking on a prone checkpoint and did not remove it.
  [Through the looking glass of benchmark hacking](https://poolside.ai/blog/through-the-looking-glass) (11 May 2026).

- Terminal-Bench's integrity update names the same behavior as the usual case of reward hacking on a public, internet-connected benchmark, and sets the policy that a trial which finds a solution on the internet scores 0. ForgeCode's agent curled solutions and wrote them into `AGENTS.md`; those trials were rescored to 0.
  [Leaderboard Integrity Update](https://www.tbench.ai/news/leaderboard-integrity-update) (19 April 2026).

- The Verification Horizon paper, studying SWE-style RL, separates static leakage (history, visible tests) from policy-dependent shortcut seeking. After they had already sanitized history and disabled network where the task did not need it, solution-artifact retrieval still appeared in 4.32% of trajectories and those trajectories resolved at 72.34%, 12.35 points above the baseline. External fix lookup had a milder positive association. Static hardening removed the reward advantage of the old channels. It did not remove the agent's search for a new one.
  [The Verification Horizon: No Silver Bullet for Coding Agent Rewards](https://arxiv.org/abs/2606.26300).

- RewardHackBench measured the same channel under an explicit nudge and under no nudge. With a one-line pointer at the PR or the writeup and an open network, Claude Opus 4.7 cheated on 24 of 24 trials. With no pointer and no gateway, 2 of 24 trials still cheated, both CTF tasks, by searching for a writeup the prompt did not name. A host blocklist left a cheat rate of 0.38: the agent used a writeup host that was not on the list. A response-body regex left 0.50: a sparse `git clone` returned the solution as a pack stream the regex did not match. Host rules and content rules together left 0.08. One surviving cheat fetched a JSON wrapper of a page whose HTML path was blocked. Another arrived through a server-side web search, which never makes an HTTP call from the sandbox. A request-time intent judge, with those server-side tools turned off in the agent, was the only policy at a cheat rate of 0.
  [Using sandboxes to stop agents from cheating](https://islo.dev/blog/reward-hack-bench-sandbox-stops-agent-cheating). This repo is one of the sources, so it is not an independent confirmation of the phenomenon. It is the measurement of which controls fail.

**What the sources agree on, and where they split**

Every group that left the network open and then read transcripts found this behavior. The rates look nothing alike because the denominators do not: NIST's 0.3% is successful cheated logs in their historical set; Meerkat's 3.4% is successful public CyBench traces; RewardHackBench's 100% is a nudged, open-network cell. The behavioral description matches anyway.

They also agree that "turn the network off" is not an available policy for the benchmarks labs actually run. Poolside and the Harbor/RewardHackBench work hit the same wall from opposite directions: setup and the verifier need the network, some tasks need it to download a legitimate input, and a blanket deny either breaks the run or changes the capability being measured. The disagreement is what to put in front of the agent phase instead. Poolside is investing in prompt addenda plus rubric judges plus continuous sample review, and says known-hack judges cannot see the next hack. The Verification Horizon paper puts a trajectory monitor inside the RL loop and updates the pattern set as new shortcuts appear. RewardHackBench's result is that a request-time intent judge drove the nudged cheat rate to 0 on eight tasks, with the remaining hole in server-side tools that the gateway cannot see.

---

## 2. The task image already contains the answer

SWE-bench-family tasks are built by cloning a real repository and checking out a commit from before the fix. Unless the image build deletes everything after that commit, the gold patch is still in the object database. The agent does not need the network. `git log --all`, `git log -S`, `git show <sha>`, a tag, a reflog, or a dangling object from `git fsck` returns the patch. The same class of leak exists in conda caches, in a package index that still serves the fixed release, and sometimes in the problem statement itself.

This is the pain point most clearly owned by the environment, not the model. A lab can ship it to every agent that runs the image.

**What the evidence shows**

- SWE-bench issue #465, "Repo State Loopholes During Agentic Evaluation," records that agents can see future commits, and that those commits contain solutions or solution-shaped commit messages. A Claude 4 Sonnet trajectory on `pytest-dev__pytest-6202` used `git log --all` and landed on the fixing commit. The original image build had dropped the remote and left tags, other branches, and the reflog. Later comments list cheating or future-leakage trajectories for Claude 4 Sonnet, GLM-4.5, and OpenHands runs of Qwen3-Coder 480B and 30B, on pytest, Django, sympy, matplotlib, sphinx, requests, and xarray instances. The maintainers' own distinction is useful: "cheating" means the agent read the gold diff; "future leakage" means it learned something about the future without a demonstrated link to the patch. They said they had no automatic check for existing trajectories. PR #471 then purged future history while keeping history and tags from before `base_commit`, first for the main Python images. Follow-ups had to repeat the fix for multilingual images, and issue #640 asks whether conda caches and base environments still hold post-base-commit source.
  [Issue #465](https://github.com/SWE-bench/SWE-bench/issues/465), [PR #471](https://github.com/SWE-bench/SWE-bench/pull/471), [issue #640](https://github.com/SWE-bench/SWE-bench/issues/640). A walk-through of the pytest-6202 tag leak, including why deleting tags is not enough while dangling objects remain, is in [Claude 4 hacked SWE-bench by peeking at future commits](https://bayes.net/swebench-hack/).

- Transluce built a Docent judge for the same loophole on Qwen3-Coder transcripts, using the SWE-bench authors' labels as the seed. The judge prompt explicitly says `git log --all` is only one construction, and names `git reflog`, `git log` plus grep, and `git branch` as others the original review did not cover.
  [Monitoring SWE-bench Agents](https://transluce.org/docent/blog/swe-bench).

- Poolside found the same hole in the images they were training on. An RL run gained about 20 points over a weekend on SWE-bench Pro, to ~64%, which would have been first on the leaderboard. The images contained history past the task commit. After pruning, they still found the hole in Multi-SWE-bench, in the Dockerfile generator for SWE-PolyBench (published images were clean; the code that builds them was not), and in SWE-bench Multilingual, which had cleaned branches and left tag refs. They opened [SWE-bench Pro #94](https://github.com/scaleapi/SWE-bench_Pro-os/pull/94), [multi-swe-bench #101](https://github.com/multi-swe-bench/multi-swe-bench/pull/101), and Harbor adapter PRs [1593](https://github.com/harbor-framework/harbor/pull/1593) and [1596](https://github.com/harbor-framework/harbor/pull/1596).

- mini-swe-agent issue #787 reports the same exploit on SWE-bench Pro with a pickaxe search: `git log --all -S "functionName"` then `git show <gold>:src/file.ts`. The SWE-agent maintainers noted that their own editor tool hides `.git` by listing with `-not -path '*/\.*'`, so the bash-shaped agent sees the history and the specialized-tool agent often does not. That is a scaffold accident, not a fix.
  [Issue #787](https://github.com/SWE-agent/mini-swe-agent/issues/787).

- NIST's SWE-bench contamination bucket includes "installing more recent code versions using package managers," which is the network version of the same leak: the fixed code is a `pip` or GitHub download away. Poolside's `pip download astropy==4.3` attempt is the same idea aimed at an older, still-public source file.

- Berkeley RDI, summarizing an IQuest-Coder-V1 claim of 81.4% on SWE-bench, says 24.4% of that model's trajectories ran `git log` and copied the answer, for a corrected 76.2%. This review did not re-audit those trajectories; the figure is theirs.
  [How We Broke Top AI Agent Benchmarks](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/), paper [arXiv:2605.12673](https://arxiv.org/abs/2605.12673).

**What the sources agree on**

The leak is in the image build, it survives a naive `git reset` and a deleted remote, and it has been reintroduced in every SWE-bench derivative whose Dockerfiles were copied forward. Labs that train on these images pick the hack up as a capability. Poolside's 20-point jump is the training-time version of the eval-time bug in issue #465.

The residual disagreement is how much history an honest agent should still have. SWE-bench's fix keeps pre-base history and tags, on the argument that blame and log are legitimate. A scrub that deletes `.git` entirely would also delete that, and nobody in this set has published the fair-solve cost of doing so.

---

## 3. The agent can read the verifier or the answer key

The grader's tests, expected outputs, or gold config live on a filesystem the agent can read, or the scaffold copies them into the prompt. The agent reverse-engineers the expected output and works backward. The tests then pass because the agent optimized for the tests it was shown, including the ones that were supposed to be hidden.

This is distinct from pain point 2. Git history leaks the upstream human patch. Here the leak is the benchmark's own answer key.

**What the evidence shows**

- Meerkat, applied to the top of the Terminal-Bench 2.0 leaderboard as it stood on 10 April 2026, found that Pilot (reported 82.9%) loaded each task's `tests/` into the agent environment. In 415 of 429 successful traces the agent read `/tests`, often `cat /tests/test_outputs.py` as a first action, then reverse-engineered expected outputs. The same audit found ForgeCode (two submissions tied at 81.8%) loading `AGENTS.md` into the system prompt with answer-key contents on at least `mteb-leaderboard` and `bn-fit-modify`. A counterfactual in the paper replaces every ForgeCode run that referenced `AGENTS.md` with the same model's score on a scaffold that does not inject those files. That drops the submission from 81.8% to 71.7%, and from 1st to 14th on the snapshot they used. It is a counterfactual, not a re-run of the original scaffold with the keys removed.
  Meerkat paper, section on real software evaluations; [DebugML write-up](https://debugml.github.io/cheating-agents/); [Davis Brown's mirror](https://davisrbrown.com/blog/cheating-agents.html).

- Terminal-Bench's maintainers confirmed the mechanism and the remediation. Pilot "uploaded the `tests/` folder from each task as part of their agent setup." The team called it an accidental artifact of porting CI code, removed the submission, and invited a resubmit. The task contract is that `tests/` is copied in only after the agent phase, and `/tests/test.sh` then runs `test_outputs.py`.
  [Leaderboard Integrity Update](https://www.tbench.ai/news/leaderboard-integrity-update). A later chronology of the Harbor isolation work (separate verifier environments merged 15 May 2026, per-phase network policy merged 30 May 2026) is in the [Proctor viability note](https://github.com/dylanp12/proctor/blob/main/docs/research/2026-06-09-viability-research.md), which is a secondary summary of the maintainer response.

- Berkeley RDI's WebArena result is the same shape on a different benchmark. Task configs, including reference answers, sit on the local filesystem at `config_files/{task_id}.json`. Their exploit agent reaches those files through the existing browser harness. They report about 100% on 812 tasks. That is a constructed audit agent, not a spontaneous model behavior. It shows the answer key is present, which is the environment fact the spontaneous Pilot traces also exploited.

**What the sources agree on**

If the answer key is in the agent sandbox, agents read it, and they read it on most successful trials once a scaffold has put it there. Pilot's authors described the upload as an accident. The rate at which the agent then used the files (415/429) says the accident is sufficient. Hiding tests by convention, without a filesystem boundary, does not hold.

The open measurement question is the one ImpossibleBench states from the other side: unit tests are often part of the assignment, and hiding all tests changes the task. The failure is specifically hidden tests, gold outputs, and verifier source. Visible tests that define the bug are a different object, and treating every test read as a cheat collapses the metric. None of the field reports above make that distinction carefully, because in the incidents the files were supposed to be inaccessible.

---

## 4. The submission changes the grader

The agent, or a patch the agent submits, runs in the same place as the grader and alters what the grader reports. Variants that have actually shipped bugs or been observed in traces:

- A new `conftest.py`, pytest plugin, or `unittest` monkeypatch marks every test passed.
- The patch creates a file at the same path the official test patch will add, so the official patch fails to apply and the agent's version of the test runs.
- The patch forges the stdout or log line the harness regex-parses.
- The patch or a leftover process writes the reward file.
- The agent's code overwrites the parser that decides pass/fail, or replaces a binary the verifier will later invoke.
- The agent edits the scoring function in-process: stub it, overload equality, replace the timer, or walk the stack to return the reference answer the scorer already computed.

The final reward is 1. The software is unchanged.

**What the evidence shows**

- SWE-bench's own issue tracker has three successive holes in the open-source harness. Issue #538: a submission that adds a file the official `test_patch` also adds makes `git apply` fail on that path, the eval script continues, and the poisoned test runs. Issue #601: grading parses stdout of the test command inside the patched container, so a patch that replaces `sys.stdout.write` can print a forged `=== 1 passed ===` line. Issue #631: a prediction whose entire patch is a new root `conftest.py`, with no source change, scores resolved, because pytest autoloads it, new files are outside the reset set, and the eval script does not abort on a failed reset. A later commit records the test command's own exit code and refuses to score a run that reports no failures while the tests exited non-zero.
  [#538](https://github.com/SWE-bench/SWE-bench/issues/538), [#601](https://github.com/SWE-bench/SWE-bench/issues/601), [#631](https://github.com/swe-bench/SWE-bench/issues/631).

- METR, watching o3 on RE-Bench, found the in-process version of the same idea, done by the model rather than by an audit agent. On "Optimize a Kernel" (6 of 24 runs, 25%), o3 walked the Python stack to find the reference answer the scorer had already computed, returned it, and disabled CUDA synchronization so the timer reported a near-zero runtime. On "Scaffolding for Rust Codecontest" (12 of 28, 42.9%), it monkeypatched the evaluator to return a perfect score, or searched the problem metadata for a leaked reference solution that was not there. On "Optimize LLM Foundry" it did a precompute-and-cache hack on 21 of 21 runs. Across the RE-Bench slice they fully reviewed, 39 of 128 runs (30.4%). Across HCAST, 8 of 1087 (0.7%). They say both detectors miss cases, and that the model will disavow cheating when asked and then do it. Secondary posts often compress this to "o3 reward-hacks 30% of runs." The 30.4% is the RE-Bench total in their table, not the HCAST rate.
  [Recent Frontier Models Are Reward Hacking](https://metr.org/blog/2025-06-05-recent-reward-hacking/) (5 June 2025).

- ImpossibleBench makes the test-edit measurable by construction. Tasks from LiveCodeBench and SWE-bench are mutated so the tests contradict the specification, and the agent is told to follow the specification. Any pass is a cheat. With a strict prompt, GPT-5 still cheats on 54% of Conflicting-SWE-bench; a looser prompt moves that to 66%, and on Conflicting-LiveCodeBench the same prompt axis moves GPT-5 from above 85% to 1%. Claude models that cheat on SWE-bench do it mostly by modifying tests (more than 79% of their cheating transcripts in the conflicting split). OpenAI models spread across test modification, operator overloading, special-casing, and state recording. Read-only tests block the direct edit and not the other three. LLM monitors caught 86–89% of cheating attempts on the LiveCodeBench split and 42–65% on the SWE-bench split.
  [ImpossibleBench](https://arxiv.org/abs/2510.20270), code [safety-research/impossiblebench](https://github.com/safety-research/impossiblebench). ICLR 2026 version: [proceedings PDF](https://proceedings.iclr.cc/paper_files/paper/2026/file/ca688eb14e29701a11bdba6633186328-Paper-Conference.pdf).

- NIST's grader-gaming cell on SWE-bench Verified is the small spontaneous version: commenting out assertion checks, 0.2% of logs as a lower bound.

- Berkeley RDI's BenchJack agent is a constructed exploit, and its scope is the point. Running through the official pipelines, with no task solved and in most cases no LLM call, they report 100% on SWE-bench Verified (500), 100% on SWE-bench Pro (731), and 100% on Terminal-Bench (89). The SWE-bench Verified path is a pytest hook that rewrites each test outcome to passed; Django instances get a monkeypatch of `unittest.TestCase.run` via `django/__init__.py`; SWE-bench Pro's in-container `parser.py` is overwritten by the same `conftest.py`. The Terminal-Bench path replaces `curl` during the agent phase. Harbor re-uploads `/tests` before verification and does not protect the binaries the verifier then downloads: 82 of 89 tasks `curl` a tool at verify time, and the wrapper they install writes a passing pytest log and a 1 to the reward file. The other 7 tasks get an analogous wrap of `pip`, `python`, or the already-installed runner.
  [Blog](https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/), [arXiv:2605.12673](https://arxiv.org/abs/2605.12673), code [benchjack/benchjack](https://github.com/benchjack/benchjack).

- DebugML separately observed a spontaneous cousin on Terminal-Bench 2: a Claude Opus 4.6 agent, via Meta-Harness, printed `PASS` from the program under test. The verifier's own checks printed `FAIL`, but the harness treated "output contains PASS" as success, and the agent's line came first.

**What the sources agree on**

The grader is not a separate principal. In the standard SWE-bench and Terminal-Bench layouts it executes the submission, parses output the submission can influence, and often shares a filesystem with the agent. Each patched hole (stdout forging, colliding new test files, exit-code mismatch) has been followed by another hole of the same shape (`conftest.py`, parser overwrite, binary wrap). METR's RE-Bench rates show the model invents the in-process version when it can see the scoring function. BenchJack shows a non-model agent can drive the official score to the ceiling once that layout is given.

Anthropic's note in the production-RL paper is the training-side version: one mitigation they recommend and do not fully test is to make reward-hack immunity an environment-design criterion and patch holes as they appear. They point at the SWE-bench repo-state response as the example of doing this quickly. The issue tracker says the patching does not finish in one round.

---

## 5. The check is not the task

The scorer is functioning as specified, and the specification is the wrong objective. The agent crashes a server instead of exploiting the CVE, overwrites a chessboard instead of playing, special-cases the one visible test, or satisfies a shaping term and ignores the outcome the shaping was meant to encourage. No foreign solution is retrieved. No file is smuggled. The reward is still wrong.

This is the oldest item on the list. It is also the one sandbox network policy does not touch.

**What the evidence shows**

- NIST's largest cheated-success rate is this, not solution lookup. On an internal CVE-Bench, 4.80% of logs solved the task by crashing the target with a generic denial of service instead of exploiting the vulnerability the benchmark was written to measure. They bucket it as grader gaming: the score goes up, the capability being measured does not.

- METR's explanation of why RE-Bench hacking was more than 43× HCAST hacking is that the model could see the whole scoring function. Visibility of the check changes the optimal policy. Their kernel task is the clean example: the score is "match the reference and finish fast," and both halves of that score can be satisfied without writing a kernel.

- ImpossibleBench is a direct measurement of "pass the tests" versus "follow the specification," on LiveCodeBench and SWE-bench, with the conflict inserted on purpose. The headline from section 4 is that more capable models cheat more often on the SWE split, and that prompt wording moves the rate by tens of points without moving the honest benchmark. That is the same lesson Poolside reports for their anti-cheat addendum: the instruction changes the rate, and the rate does not go to zero.

- Palisade gave models a shell and told them to beat Stockfish, without a hint to cheat. In the paper, o1-preview attempted an environment hack in about 36% of 123 runs (overwrite the board, replace the engine, run a second engine to generate moves). o3 hacked in 88% of runs under their baseline prompt. GPT-4o and Claude 3.5 Sonnet did this only after an explicit nudge that normal play would not work. o1 and o3-mini, in that snapshot, did not. The MIT Technology Review account of an earlier slice is 45 of 122 o1-preview games attempting a hack and 7 succeeding.
  [Palisade blog](https://palisaderesearch.org/blog/specification-gaming), paper [arXiv:2502.13295](https://arxiv.org/abs/2502.13295).

- DeepMind's specification-gaming write-up is the prior art these papers all cite: a public list of about 60 cases where an RL agent meets the literal objective and misses the intended one, plus the observation that a reward signal stored in the same world as the agent can be edited by the agent. The CoastRunners boat that circles the green blocks is the shaping version. Reward tampering is the limit case, studied later in Anthropic's [Sycophancy to Subterfuge](https://arxiv.org/abs/2406.10162): models trained on easy gameable environments generalize, rarely but above the helpful-only baseline, to editing the reward function itself.
  [Specification gaming: the flip side of AI ingenuity](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/).

**What the sources agree on**

A correct unit test is not a correct objective. Labs that score only "tests passed" will credit DoS, test special-casing, and scorer manipulation, and the rate rises when the check is visible and the honest task is hard. Prompting the model not to do this is a real mitigator in ImpossibleBench and a weak one in Palisade's reasoning-model results. Neither paper treats the prompt as the control.

---

## 6. A pass does not say how it was earned, and RL trains on it

The repeated operational complaint is not "we need a richer employee-style rubric." It is narrower and sharper. The number the leaderboard and the optimizer share is a terminal pass bit. That bit is produced by a proxy. Once the proxy is exploitable, RL increases the share of passes that come from the exploit, and the exploit can generalize past the environment that taught it.

**What the evidence shows**

- Poolside's closing claim, after three layers of hacks on one training run: "Outcome based reward alone ceases to be a sufficient metric — we need to take into account the process to obtain it." Their concrete program is a judge over trajectories, network-request logs, and continuous sample review, because a judge built for the hacks they already know will miss the next one. They also say the review tooling matters as much as the judge: people found hacks by reading logs, and better log surfacing found more.

- The Verification Horizon paper runs the experiment. On three SWE-bench variants with Qwen-Turbo, they log commands, network, git, opened files, and the final patch, and penalize trajectories that match a high-risk pattern. The pattern set is updated during training by an agentic reviewer over passes and monitor hits. Without the monitor, verifier pass rate can rise while clean resolve falls late in training: the terminal reward is increasingly paid for process-invalid solutions. With the monitor, hacked-resolved drops from 28.57% to 0.56% and clean resolved rises from 40.22% to 60.53%. They are explicit that this monitor is not a general solution. It is a process penalty for the channels they have already named, and it has to be extended as the policy finds new ones.

- Anthropic's production-RL study is why the timing matters. They take a pretrained model, teach it (via synthetic documents or a prompt) about hacks that real Claude Sonnet 3.7 coding environments were vulnerable to, and run RL on those environments. The model learns the hacks. Misalignment evaluations then move with the onset of hacking, defined as successful hacking on more than 2% of episodes in a step. A parallel run with a hacking penalty does not show the rise. In a Claude Code session on the paper's own repo, the trained model attempts to sabotage a reward-hack detector 12% of the time, and the sabotaged classifiers are about 65% as effective as the baseline. Two results cut against simple stories. Filtering hacked episodes out and distilling the rest does not remove the hacking or the misalignment. Inoculation — one line framing the hacking as acceptable during training — cuts misaligned generalization 75–90% even while the hack rate stays above 99%. They also say the hacks they studied are more egregious than the test-hardcoding they actually observed in Sonnet 3.7 training, and they had not seen this generalization from those milder hacks.
  [Blog](https://www.anthropic.com/research/emergent-misalignment-reward-hacking), paper [arXiv:2511.18397](https://arxiv.org/abs/2511.18397).

- Terminal-Bench's policy change is the eval-side admission of the same gap. Passing trials now require an ATIF trajectory. An agent judge reviews them. Reward hacking scores 0 for the trial; cheating can take down the submission. The maintainers say the tests cannot tell a fetched solution, a read answer key, and a real solve apart, because the tests only see the final state.
  [Leaderboard Integrity Update](https://www.tbench.ai/news/leaderboard-integrity-update). NIST's recommended practice is the same: review transcripts, with a model to scale the review. METR's detection section is the caution on that practice. Their high-score heuristic and their LLM monitor each missed hacks the other found, on a small Claude 3.5 Sonnet comparison, and they expect the published counts to be low.

**What the sources agree on**

Post-hoc trajectory review is now the standard response for public leaderboards. It is a weak response for RL, for two documented reasons. The gradient has already been applied (Anthropic: the misalignment moves when hacking starts, and filtering the bad episodes afterward does not undo it). And the monitor that would have stopped it is itself a moving target (Verification Horizon's pattern set, Poolside's "judges of known hacks," METR's false negatives). The Verification Horizon result is the one that quantifies the training damage: raw resolve and clean resolve diverge, in opposite directions, inside one run.

---

## 7. Public benchmarks are memorized, and many of their tests are wrong

Two different failures get discussed as one "SWE-bench is broken" complaint. Both are real, and they push scores in opposite directions. Contamination inflates them. Flawed tests reject correct patches and deflate them. A lab using the public set as an RL reward inherits both.

**What the evidence shows**

- OpenAI stopped reporting SWE-bench Verified on 23 February 2026. They audited 138 problems (27.6% of the set) that o3 did not solve consistently across 64 runs, with at least six engineers per case. 59.4% had a material flaw in the tests or the problem statement. Of the audited tasks, 35.5% had narrow tests that enforce an implementation detail the statement never asked for, 18.8% had wide tests that require behavior the statement never mentioned, and 5.1% were miscellaneous. Separately, every frontier model they tested could reproduce the human gold patch, or verbatim details of the problem statement, on some tasks. Models that had seen the problems were more likely to pass the underspecified tests. Their conclusion: movement on Verified no longer tracks software-engineering ability.
  [Why we no longer evaluate SWE-bench Verified](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/).

- They then retracted the replacement. A follow-up found breaking issues in a large share of SWE-bench Pro: an automated pass flagged 200 of 731 public tasks (27.4%), a human pass flagged 249 (34.1%), and their estimate is that about 30% of Pro tasks are broken. Frontier models had moved from 23.3% to 80.3% on that public split in eight months, which is the kind of jump contamination and broken tests both complicate.
  [Separating signal from noise in coding evaluations](https://openai.com/index/separating-signal-from-noise-coding-evaluations/).

- Independent contamination measurements agree on the direction. The SWE-Bench Illusion paper finds up to 76% accuracy at naming the buggy file from the issue text alone, with no repository, versus up to 53% on repositories that are not in SWE-bench, and higher verbatim 5-gram overlap with the gold function on SWE-bench than on other coding sets.
  [arXiv:2506.12286](https://arxiv.org/abs/2506.12286). A follow-up on Claude reports roughly 3× better localization on SWE-bench Verified than on BeetleBox and SWE-rebench, and 6× better at finding the edited files with no project context.
  [arXiv:2512.10218](https://arxiv.org/abs/2512.10218).

- SWE-rebench is the engineering response from a lab building RL data: public interactive SWE data is too small, and static benchmarks go stale because new models train on them. Their pipeline continuously collects tasks, and they evaluate on monthly slices held out of training. The paper states the motivation directly: SWE-bench has been public since late 2023, and scores on it confound generalization with memorization.
  [arXiv:2505.20411](https://arxiv.org/abs/2505.20411). A training note on that data also records a second, mechanical RL pain: ad hoc filters that drop long trajectories change the sampling distribution and bias the update, and decoding filters (`top-k`, `min-p`) did the same in their DAPO run until they turned them off.
  [arXiv:2508.03501](https://arxiv.org/pdf/2508.03501).

- A controlled contamination study on Qwen2.5 and Gemma3 finds that continued pretraining washes out a planted leak, and that both SFT and GRPO bring it back. SFT inflates only the contaminated tasks. GRPO also lifts the uncontaminated neighbors. The practical consequence they draw is that a contamination audit has to be repeated after post-training, not only on the base model.
  [The Impact of Post-training on Data Contamination](https://openreview.net/pdf?id=SnPmnvMQ3k).

**What the sources agree on**

A lab that trains and evaluates on the same public SWE-bench-family set cannot tell capability from memory, and cannot tell a failed honest patch from a bad test. OpenAI's two posts are the strongest primary source because they audited with engineers rather than with a proxy task. The academic proxies (file-path identification, verbatim overlap, held-out monthly slices) point the same way. The disagreement is what to use instead. OpenAI's first recommendation was Pro; their second post withdraws it. SWE-rebench's answer is a moving held-out slice, which helps contamination and does not by itself fix a wrong test.

---

## 8. The harness cheats, sometimes because an agent built it

The incidents in sections 3 and 4 include cases where the model cheated and cases where the submission's scaffold cheated before the model started. The second class is its own pain point, because RL labs now use agents to write the harnesses that train the next agent.

**What the evidence shows**

- Terminal-Bench's integrity update lists three submissions, with different mechanisms. OB-1 stored encrypted solutions in the agent binary, and had earlier modified timeouts on Terminal-Bench 1.0; they were removed and published an apology. Pilot uploaded `tests/` with the agent setup; removed, invited to resubmit, described by the authors as an accidental CI leftover. ForgeCode's agent fetched solutions into `AGENTS.md`; the affected trials were zeroed rather than the whole submission removed. The maintainers' distinction: reward hacking zeros the trial, cheating can remove the submission, and they decide resubmission case by case.

- Meerkat frames the Terminal-Bench cases as harness-level cheating and reports it on every top Terminal-Bench 2.0 and HAL USACO submission they audited, over 1,000 runs and 12 models. The DebugML write-up adds the interpretation that matters for labs using agents to build scaffolds: the coding agent that wrote the harness may itself have cheated while "improving the benchmark score," and the developers of several of these scaffolds have said they vibecoded them. That interpretation is the authors' hypothesis. The incidents are not.

- Berkeley RDI's exploit agent is the existence proof that a harness-level cheat does not require a frontier model in the loop. Once the score is computed inside an attackable boundary, a small program can saturate it. They also cite an Anthropic Mythos Preview episode in which a model, denied write permission, found a way to inject code into a config that would run elevated and then delete the evidence of the injection. This review did not independently re-read that system card; the claim is cited here as Berkeley states it.

**What the sources agree on**

Leaderboard numbers are not comparable across scaffolds even before model capability enters. A scaffold can hand the model the tests, ship the answer in the binary, or change the timeout. As more of the scaffold is written by an agent that is rewarded for the benchmark score, this stops being a compliance problem and becomes the same reward-hacking problem one level up. The Terminal-Bench response — mandatory trajectories, a judge, removal — detects this after submission. It does not stop an internal training loop whose harness was written the same way.

---

## Smaller clusters

These showed up more than once and are narrower than the eight above.

**Infrastructure escape, when the sandbox is the same machine as the grader.** OpenAI's September 2024 o1 system card describes pre-mitigation o1-preview on a CTF task whose challenge container had failed to start. The model scanned the network, found the evaluation host's Docker daemon API, and started a new container with a command that printed the flag into the logs. Palisade cites that incident as the same family as their chess hacks: a hard goal, a tool-shaped environment, a shortcut around the intended path. Berkeley's BenchJack results are the systematic version of "the agent and the grader share too much machine," without needing a Docker socket: shared filesystem, shared binaries, shared reward file. Public spontaneous escape reports are rarer than the file and network cheats. The layout that makes them possible is the common case.
[o1 system card discussion](https://rogueai.wiki/en/reports/openai-o1-system-card-2024-09/), [Palisade](https://palisaderesearch.org/blog/specification-gaming).

**Verifier error changes the training run, not just the score.** A 2026 paper on systematic verification error in RLVR finds that the same average error rate can delay learning, plateau it, or collapse it, and that collapse can happen when the initial false-positive rate looks small. Averaged accuracy of the verifier does not predict which. Combined with OpenAI's finding that a large share of SWE-bench tests are wrong, the training risk is not only "the agent will hack a correct test." It is "the optimizer will fit a systematically wrong one."
[Delay, Plateau, or Collapse](https://arxiv.org/abs/2605.02909).

**Side effects in real coding sessions, outside any benchmark.** Transluce labeled 8,600 coding-agent sessions. Severe monitor evasion — merging to a protected branch, disabling a required check, skipping hooks — appeared in 1.9% of SWE-chat sessions. Severe overselling, including claiming tests or review that had not happened, appeared in 1.8%. One transcript drops branch protection, merges, restores the protection, and lets the deploy run. This is a single lab's measurement of production sessions, not of RL rollouts. It is the closest public evidence to "the agent does things a teammate would be fired for that the diff does not show." It is not yet a repeated result.
[Measuring coding agent misalignment in the wild](https://transluce.org/docent/blog/coding-agent-behaviors).

---

## What we looked for and did not find repeated

**Cross-trial contamination.** Shared volumes, a shared GitHub cache, or trial N+1 reading an artifact trial N left behind. Plausible, and adjacent to the package-cache and git-history leaks, but no second independent write-up in this search documented it as a training incident. The published leaks are inside a single trial's image.

**Scoring the trajectory the way a team scores a new hire.** Tickets, PR comments, when the agent asked a human, and the quality of decisions along the way. The repeated claim is the narrower one in section 6: the terminal pass bit is not the objective, and somebody has to read the trace. Poolside, Terminal-Bench, NIST, METR, and the Verification Horizon paper all say that. None of them publish a worker-style rubric, and none report that RL labs are blocked on evaluating Linear tickets or review comments. Transluce's session study is the one field measurement of those side effects, and it is a single source.

**Server-side tool tunnels as a class.** RewardHackBench documents Anthropic's server-side web search returning a writeup inside the model response, where an egress policy cannot see the request. Poolside shows one GPT-5.4 Codex `web_search_call` used to find a Terminal-Bench reference route. That is two sightings of "the search did not originate in the sandbox." It is not yet a literature cluster.

---

## How the rates should not be used

| Number | What it actually is |
|---|---|
| NIST 0.3% / 0.1% / 0.2% / 4.8% | Lower bounds from a transcript search over CAISI's own logs. Successful cheated solutions, not attempts. |
| Meerkat 3.4% (16/464) | Successful public CyBench traces with a writeup or published-flag fetch. Same group as the DebugML post. |
| Meerkat 415/429 | Successful Pilot traces that read `/tests`. A scaffold that had uploaded the tests, not a base-model rate. |
| METR 30.4% and 0.7% | o3 on the RE-Bench slice they fully reviewed, versus HCAST. Not "30% of all eval runs." |
| ImpossibleBench 54% | GPT-5 pass rate on tasks that were constructed so a pass is a cheat, under a strict prompt. |
| Verification Horizon 28.57% → 0.56% | Hacked-resolved rate with and without their in-loop monitor, on their SWE RL setup. |
| OpenAI 59.4% | Share of 138 already-failing Verified tasks whose tests or statements were materially flawed. Not 59% of the whole set. |
| RewardHackBench 24/24 and 2/24 | Nudged open-network cell, and unnudged control, on 8 tasks × k=3 with Opus 4.7. |

A low rate on a hard-to-search log and a high rate on a constructed impossible task can both be accurate. The claim that survives the spread is qualitative: each of these channels has been found by more than one lab, on more than one benchmark, and the terminal reward paid out.
