# Trace and Gate

**Provenance tracking and policy checks against indirect prompt injection in email agents.**
ESP3201A project, National University of Singapore, AY 2026/27 Sem 1. Rui Zhekai and Khadijah Fathima.

An LLM email assistant reads mail written by strangers and can send, forward and delete mail for its
user. Any incoming email can carry hidden instructions that take the agent over (*indirect prompt
injection*). We compare two system-level defenses against a no-defense baseline and the Dual-LLM pattern:

| Config | What it does |
|---|---|
| **B0** | No defense |
| **B1** | Dual-LLM: a quarantined reader turns untrusted text into `$VAR`s; the planner never sees it |
| **D1 / D1h** | Provenance tracking: every value is labelled with where it came from; recipients, targets and links must come from the user's own words (D1h also lets sender addresses be *mentioned*) |
| **D2** | Policy checks: per-task tool allowlist, recipient origin, object scope, secrets stay internal |
| **D1h+D2** | Both: an action must pass both checks |

## Results (Qwen3-8B, local)

Held-out attacks, written after the defenses were frozen (git tag `defenses-frozen-v1`): run `20261025-034455`,
58 attack and 56 normal tasks, 3 runs pooled, 1,710 episodes, 0 model errors.

| | B0 | B1 | D1h | D2 | D1h+D2 |
|---|---|---|---|---|---|
| Attack success | 21.8% (38/174) | **0%** | **0%** | **0%** | **0%** |
| Normal tasks done | 89.3% | 80.4% | 89.3% | 89.9% | **91.7%** |

- Development suite v3 (run `20261024-135826`, 97 attacks): B0 45.4% (44/97); every defense 0%; normal tasks 89.3% for B0 and D1h+D2.
- Second model, Qwen2.5-7B (run `20261025-071911`): B0 29.3% (17/58); every defense 0/58.
- Cost: on 40 harmless tasks with links (run `20261025-055650`), normal tasks fall from 88.3% (B0) to 40.0% (D1h+D2), because D1h blocks links copied out of emails. An exploratory, post-freeze fix (D1h-L) reaches 55.0%.
- AgentDojo workspace (run `agentdojo_20261025-075616`): its attack worked in only 2/160 episodes even without a defense, so it measures cost, not safety: utility 27.5% (B0) vs 30.0% (D1h+D2).

All numbers: [`sandbox/results/final_tables.md`](sandbox/results/final_tables.md).

![Attack success vs normal-task success, held-out](sandbox/results/figures/fig1_asr_vs_utility_heldout.png)

## How it is built

```
agent container ──(internal network, no internet)──► nginx gateway ──► Ollama on the host (GPU)
  read-only fs, non-root, no capabilities              whitelists only the inference endpoints
```

- `sandbox/src/`: agent loop (`agent.py`), simulated mailbox (`email_env.py`), defenses (`defenses.py`), scoring, runner (`run_eval.py`), analysis, live demo (`demo.py`), isolation check, AgentDojo bridge (`agentdojo_bridge.py`, `run_agentdojo.py`).
- `sandbox/benchmark/`: `build_suite.py` generates the tasks; `import_llmail.py` samples real attacks from [LLMail-Inject](https://huggingface.co/datasets/microsoft/llmail-inject-challenge).
- `sandbox/tests/`: offline unit tests, including oracle replays of every scripted hijack against each defense.
- `sandbox/results/`: numbers-only summaries and figures.

**Attack text is never committed.** Task files contain only `{{payload:ID}}` placeholders; the text lives in
`sandbox/benchmark/payloads/`, which is git-ignored and regenerated locally. Full transcripts
(`results/raw/`) are also git-ignored. The AI coding assistant used on this project was blocked from reading
both (`.claude/settings.json`, `.claude/hooks/`), so it could not itself be prompt-injected.

## Quick start

Needs Git, Docker Desktop, Ollama and Python 3.10+.

```bash
ollama pull qwen3:8b
git clone https://github.com/Rick-sys-cell/trace-and-gate.git && cd trace-and-gate/sandbox
python benchmark/build_suite.py --version 3        # writes the template attack payloads locally
docker compose build
docker compose run --rm agent python src/isolation_check.py
docker compose run --rm agent python src/demo.py --oracle   # instant, no model needed
docker compose run --rm agent python src/demo.py --live     # real model
python -m unittest discover -s tests                         # offline tests
```

**Long runs on a 16 GB Windows host.** Ollama's runner process grows during long runs. Start the memory guard
first (PowerShell, from the repo root): `Start-Process pythonw -ArgumentList 'tools/memory_guard.py','--container','<name>'`,
then launch the run with `docker compose run -d --name <name> ...`. While free RAM is under 2 GB or Ollama is
over 7 GB, the guard sets a flag; between episodes the AgentDojo runner unloads the model and waits for it to clear.

- [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md): step-by-step setup and a 5-minute demo script for a fresh laptop.
- [`docs/HELDOUT_AUTHORING.md`](docs/HELDOUT_AUTHORING.md): how the held-out attacks are written (by the team, never by the AI assistant).

## AI use

Claude (Anthropic), through Claude Code, was used as a tool to write code to our specifications and to help
draft and summarise. Every reported number was checked against the result files. See
[`3_Sources/AI_Declaration.md`](3_Sources/AI_Declaration.md).
