# Live demo guide (Week 11)

A 5-minute live demo on a laptop: **one poisoned email, four agents.** The undefended agent is
hijacked. The same email is then blocked by D2, by D1h and by both, while Alex's real task still
gets done.

Everything runs **offline** once set up: the model runs locally in Ollama and the agent runs in an
isolated Docker sandbox. Venue Wi-Fi does not matter after step 2.

---

## 1. Laptop requirements

| | Minimum | Recommended |
|---|---|---|
| RAM | 16 GB | 16 GB+ |
| Free disk | 15 GB | 20 GB |
| GPU | none (CPU works, but slowly) | any GPU Ollama supports (NVIDIA, AMD, Apple silicon) |
| OS | Windows 10/11 (WSL2), macOS 13+, or Linux | |

No GPU? Use `--oracle` mode (instant, no model) or the smaller `qwen3:4b` model (see section 6).

## 2. One-time setup (do this at least 2 days before, on good Wi-Fi)

1. **Install** [Git](https://git-scm.com/downloads), [Docker Desktop](https://www.docker.com/products/docker-desktop/),
   [Ollama](https://ollama.com/download) and [Python 3.10+](https://www.python.org/downloads/).
   On Windows, Docker Desktop asks to enable WSL2: accept and reboot.
2. **Download the model** (about 5 GB):
   ```bash
   ollama pull qwen3:8b
   ```
3. **Get the code:**
   ```bash
   git clone https://github.com/Rick-sys-cell/trace-and-gate.git
   cd trace-and-gate/sandbox
   ```
4. **Generate the attack emails locally.** They are deliberately not in the repo, so no internet is
   needed for this step:
   ```bash
   python benchmark/build_suite.py --version 3
   ```
   It should print `template payloads written: 69`.
5. **Build the sandbox** (downloads Python and nginx images, about 500 MB):
   ```bash
   docker compose build
   docker compose pull llm-gateway
   ```
6. **Check it works:**
   ```bash
   docker compose run --rm agent python src/isolation_check.py   # expect: 16/16 checks not failed
   docker compose run --rm agent python src/demo.py --oracle     # expect: B0 hijacked, the rest safe
   docker compose run --rm agent python src/demo.py --live       # real model; first run is slow
   python -m unittest discover -s tests                           # offline tests (LLMail ones skip)
   ```

> **Windows:** run these in **PowerShell** or Windows Terminal. In Git Bash, prefix Docker commands
> with `MSYS_NO_PATHCONV=1`, otherwise paths like `/data/...` get rewritten.

## 3. Make a backup recording (strongly recommended)

Record one good `--live` run on a machine where it is fast, so you can play it if anything fails on
the day:

- **Windows:** `Win + Alt + R` (Xbox Game Bar) starts and stops recording the active window.
- **macOS:** `Cmd + Shift + 5`, then *Record Selected Portion*.

Use a large terminal font (Ctrl/Cmd `+`, about 18 pt) and a dark background, and keep the video
under 2 minutes.

## 4. Before the demo

**The day before**
- [ ] `git pull` in `trace-and-gate`, then run `python benchmark/build_suite.py --version 3` again.
- [ ] Run everything in section 2, step 6.
- [ ] Copy the backup video and the figures (`sandbox/results/figures/`) to the laptop desktop.
- [ ] Charge the laptop. Turn off auto-updates for Windows and Ollama.

**30 minutes before**
- [ ] Plug in power. Close browsers, Teams and OneDrive sync, since they compete for RAM.
- [ ] Start Docker Desktop and wait for "Engine running". Start Ollama.
- [ ] **Warm up the model** so the first live call is not slow:
      `ollama run qwen3:8b "hi"` (then `/bye`).
- [ ] `docker compose up -d llm-gateway`
- [ ] Run `src/demo.py --oracle` once, then `--live` once, and leave the terminal open.
- [ ] Set the terminal font to about 18 pt.

## 5. The demo script (about 5 minutes)

| Time | Show | Say |
|---|---|---|
| 0:00 | `docker compose run --rm agent python src/isolation_check.py` | "The agent runs in a locked-down container: no internet, read-only, non-root. It can only reach the model through a gateway that allows inference calls and nothing else." |
| 0:45 | `docker compose run --rm agent python src/demo.py --live --show-email` | "Alex asks a normal question about one email. That email also hides an instruction to forward Alex's confidential grades to an attacker." Point at the hidden line. |
| 1:30 | B0 block | "With no defense the model obeys: the forward to records@attacker.example is **ALLOWED**, so Alex's grades are leaked." |
| 2:15 | D2, D1h and D1h+D2 blocks | "Same email, same model. D2 hides tools the request doesn't need. D1h tracks where each value came from, and the forward wasn't requested by Alex. Each is **BLOCKED**, yet Alex's own task is still **done**." |
| 3:15 | `... src/demo.py --oracle --task attack-g2-multiturn-1-research` | "A harder case: the attack is split across two emails and two turns, and the phishing link rides inside a reply Alex *did* ask for. D2 alone lets it through. D1h catches it because the link came from untrusted text. That's why we combine them." |
| 4:15 | `sandbox/results/figures/fig1_asr_vs_utility.png` | "Over the whole benchmark, attacks succeed about a third of the time with no defense (pilot: 33%)." Then give the held-out D1h+D2 attack-success and normal-task numbers. **Fill these in from the final results before the demo; don't quote numbers you haven't checked.** |

Tips:
- `--show-email` and `--show-text` print the attacker's email and the model's answer. They are fine
  for a human audience.
- Live results vary slightly from run to run. If B0 happens **not** to be hijacked, say so: the
  model resisted this time, which is why we measure over hundreds of runs. Then switch to
  `--oracle`, which shows what happens when it does obey.
- `src/demo.py --list` shows other attacks. Good alternates are other `attack-g1-body-*` and
  `attack-g3-body-*` tasks.

## 6. Fallbacks

| Problem | Do this |
|---|---|
| Model too slow / no GPU | `src/demo.py --oracle` (instant, same defense decisions), or a smaller model: PowerShell `$env:MODEL="qwen3:4b"`; macOS/Linux `MODEL=qwen3:4b` before the command (after `ollama pull qwen3:4b`). Say that the report's numbers use qwen3:8b. |
| Docker won't start | Play the backup video, then show the figures. |
| Laptop dies | Video and figures from a USB stick on any machine. |

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `isolation_check`: *gateway reachable* WARN, or demo shows `llm_error` | Ollama is not running. Start it, run `ollama list`, then `docker compose restart llm-gateway`. |
| `502` / `ConnectionError` right after starting | The model is still loading. Run the warm-up from section 4 and retry. |
| `KeyError: 'tpl-...'` or *unknown task* | The attack emails were not generated. Run `python benchmark/build_suite.py --version 3`. |
| `FileNotFoundError: C:/Program Files/Git/data/...` | You are in Git Bash. Use PowerShell, or prefix the command with `MSYS_NO_PATHCONV=1`. |
| Docker out of memory / laptop freezes | Close other apps. On Windows, cap WSL in `%USERPROFILE%\.wslconfig` (`[wsl2]` then `memory=6GB`), run `wsl --shutdown`, and restart Docker. |
| Very slow first answer | Normal: the first call loads the model into memory. Warm it up beforehand. |
| Apple silicon | Works natively (multi-arch images). Ollama uses the GPU automatically. |

## 8. After the demo

```bash
docker compose down
```

Nothing else needs cleaning up: the demo writes nothing to disk.
