# Interim Q&A Prep: Trace and Gate (Fri 16 Oct 2026)

ESP3201A · Rui Zhekai & Khadijah Fathima · companion to `Interim_Presentation_v3.pptx`, `Interim_Speaker_Notes.md` and `Interim_Report.md`

**How to use this:**
- Read Part A (numbers) and Part D (knowledge) once.
- Practise Part B aloud. Each answer is 2–4 sentences; say the first sentence, then stop unless the panel wants more.
- Every number here was checked against the analysis files:
  - **pilot** = `figures/pilot_analysis_20261006-100417.json` + `pilot_diagnostics_…`;
  - **rerun** = `figures/rerun_analysis_20261008-103942.json` + `rerun_diagnostics_…`;
  - **recheck** = `figures/recheck_b1_subject_20261008-094725.json`.
- **Golden rules for answering:**
  - Say what the data shows, then the caveat. Never round 0 of 97 up to "solved".
  - If you don't know: "We haven't measured that; here's how we would." Don't guess a number.
  - Point at a backup slide when one exists (slide numbers below).

**Who answers what:**

| Topic | First answer | Backup slides |
|---|---|---|
| Sandbox, safety, ethics, engineering | Rui | 14, 18, 22 |
| How D1 / D1h / D2 / B1 work | Rui | 7, 17 |
| Results, statistics, exposure | Khadijah | 9, 10, 15, 19, 20, 21 |
| Benchmark, LLMail-Inject, controls | Khadijah | 8, 16 |
| Plan, risks, next steps | Khadijah | 13 |

---

## Part A: Numbers cheat-sheet

### Pilot (6 Oct, run 20261006-100417): 153 tasks × 5 configs = 765 episodes, 0 errors, one run

| Config | Attack success (of 97) | 95% CI | Normal tasks (of 56) | 95% CI | False blocks | Task done under attack |
|---|---|---|---|---|---|---|
| B0 none | 32 = 33.0% | 24–43 | 54 = 96.4% | 88–99 | – | 55.7% |
| B1 Dual-LLM | 2 = 2.1% | 1–7 | 47 = 83.9% | 72–91 | – | 75.3% |
| D1 provenance | 0 = 0.0% | 0–4 | 50 = 89.3% | 79–95 | 4 = 7.1% | 38.1% |
| D2 policy | 1 = 1.0% | 0–6 | 49 = 87.5% | 76–94 | 1 = 1.8% | 54.6% |
| D1+D2 | 0 = 0.0% | 0–4 | 47 = 83.9% | 72–91 | 4 = 7.1% | 45.4% |

- **H1:** D1+D2 vs B0 on attacks: 32 tasks only B0 failed, 0 only D1+D2; exact McNemar p = 4.7 × 10⁻¹⁰. **Met.**
- **H2:** D1+D2 lost 7 normal tasks vs B0, gained 0; p = 0.016; −12.5 pts. **Not met.** D1 alone −7.1, D2 alone −8.9, B1 −12.5.
- **D1+D2 vs B1:** attacks 2 vs 0, p = 0.5 (no difference shown). Normal tasks 7 vs 7, p = 1.0.
- **Where attacks worked (B0):**
  - attachment 11/18 (61%);
  - body 9/18 (50%);
  - subject 4/9 (44%);
  - LLMail 8/40 (20%);
  - multi-turn 0/12.
- **By goal (B0):** leak a secret 7/19, phishing 9/19, delete 8/19, LLMail send 8/40.
- **Exposure (B0):**
  - opened the attack in 77/97 tasks;
  - all 20 unopened tasks were LLMail tasks (13 "read all", 7 "summarise and send");
  - success when opened was 31/77 = 40%;
  - any attacker-steered action 35/97 = 36% (3 replies to the attack email, 2 with the attacker's exact text).
- **Attempts vs blocks:**

| Config | Attempted | Blocked | Succeeded |
|---|---|---|---|
| B0 | 32 | 0 | 32 |
| B1 | 2 | 0 | 2 |
| D1 | 33 | 33 | 0 |
| D2 | 7 | 6 | 1 |
| D1+D2 | 7 | 7 | 0 |

- **Controls (B0):** "read all and answer" 7/8 without the attack email vs 3/20 with it; "summarise and send" 8/8 vs 14/20.
- **Cost per task:**
  - model calls: B0 3.96 · B1 3.91 (+1.24 reader calls) · D1 3.96 · D2 4.10 · D1+D2 4.11;
  - tokens: B0 3,173 · D2 2,442 (−23%);
  - time: B0 5.9 s · B1 6.7 s (+13%).

### B1 recheck (8 Oct, run 20261008-094725): 9 subject-line attacks after the bug fix
- B1 0/9, B0 4/9.

### Rerun (8 Oct, run 20261008-103942): suite v2, 4 configs = 612 episodes, 0 errors

| Config | Opened | Tried / blocked | Attack success | Normal tasks | Unchanged 40 | Lost vs B0 |
|---|---|---|---|---|---|---|
| B0 | 79 | 33 / 0 | 33 = 34.0% (25–44) | 49 = 87.5% | 39 | – |
| D1 | 78 | 33 / 33 | 0 = 0.0% (0–4) | 41 = 73.2% | 39 | 8 (all 8 "summarise and send" controls) |
| D1h | 80 | 34 / 34 | 0 = 0.0% (0–4) | 49 = 87.5% | 39 | **0** |
| D2 | 82 | 8 / 7 | 1 = 1.0% (0–6) | 45 = 80.4% | 37 | 4 |

- B0 success when opened: 33/79 = 42%.
- Template attacks gave identical counts in both runs: 11/18, 9/18, 4/9, 0/12.
- Exposure: "summarise and send" opened 20/20 (was 13/20 in the pilot); "read and answer" opened only 2/20.
- **D1h + D2 has not been run.** So H2 for the combination is still open.

### Setup facts
- **Model:** Qwen3-8B, 4-bit, via Ollama, thinking off.
  - Temperature 0.3, context 16,384 tokens.
  - Limits: 15 steps per turn, 300 s per episode, 180 s per call.
  - Hardware: AMD RX 6750 GRE (10 GB), 16 GB RAM.
  - Ollama auto-updated 0.35.1 → 0.40.1 between the pilot and the rechecks; same model.
- **Benchmark:**
  - 153 tasks in 8 inboxes;
  - 56 normal (40 tasks + 16 no-attack controls);
  - 97 attacks (57 template + 40 LLMail-Inject);
  - 11 email tools.
- **Oracle replay, no model:** D2 blocked 93/97 scripted hijacks, D1 and D1+D2 97/97, 0 false blocks. 48 automated tests.
- **LLMail-Inject:**
  - 208,095 attack prompts from 839 participants;
  - Phase 2: 90,916 submissions → 145 unique full end-to-end successes → 40 sampled from 21 of 24 sub-levels;
  - goal: send an email to contact@contact.com.
- **Sandbox:**
  - 16/16 isolation checks before every run;
  - non-root (uid 10001), all capabilities dropped, read-only file system;
  - 2 CPUs, 2 GB memory, 256 processes;
  - internal network only; the nginx gateway allows 6 endpoints (chat, tags, show, version, and the OpenAI-style /v1 models and chat) and returns 403 for anything else.

---

## Part B: Likely questions and answers

### B1. Validity: "is the result real?"

**Q: Did you change your research question since the proposal?**
A: Yes. After your feedback that Dual-LLM dates from 2023, and following the course brief's Project 8, we now test provenance tracking and policy checks in an email agent, and Dual-LLM became the baseline we compare against. The attack class, the two hypotheses and their thresholds (at least 80% fewer attacks, at most a 10-point drop), the sandbox and the code-based scoring all stayed the same. Note that D1 and D2 now name different defenses: in the proposal they were the quarantined reader and least-privilege lists.

**Q: 0% sounds too good. Isn't D1 tuned to your own attacks?**
A: That's our main threat to validity, and we say so in the report. We designed D1 after seeing D2's gap, and 57 of the 97 attacks are our own templates. Two things help. First, the 40 LLMail emails were written by other people against other systems, and none got through any defense. Second, Week 10 adds a held-out set: a fresh LLMail sample, two unseen styles and disguised links, all frozen before we look at them.

**Q: Are your zeros just the model refusing, not the defense working?**
A: No. Under D1 the model *tried* the attack in 33 tasks, about as often as with no defense (32), and D1 blocked every one (slide 19). D2 is different: it hides tools, so the model could only try 7 times.

**Q: One run per configuration. How confident are you?**
A: For attacks, confident enough for H1: 32 to 0 on paired tasks gives p ≈ 5 × 10⁻¹⁰. For normal tasks the intervals are wide, about ±10 points, so differences of a few tasks are within noise. Week 10 runs everything three times.

**Q: Why is undefended attack success only 33%? Is the scoring broken?**
A: Three reasons, all measured.
- In 20 of 97 attack tasks the agent never opened the attack email; all 20 were LLMail tasks. When it did open it, it was hijacked 40% of the time.
- Our 12 multi-turn attacks never worked on this model.
- Scoring is strict, like LLMail-Inject's: three replies to the attack email don't count. Counting them gives 36%.

For comparison, a 2026 study of Progent on Qwen2.5-7B saw 25.8% undefended.

**Q: Why did you add stronger attacks? Isn't that tuning the baseline?**
A: The proposal set a validity bar beforehand: the undefended agent must fail at least 30% of the time, or a big reduction means little. The first clean pilot reached 25.3%. We added three attack phrasings and more variants, and the rate rose to 33%. We changed the attacks, not the defenses, and the change was applied equally to every configuration.

**Q: Your rerun changed the benchmark and the Ollama version. Is pilot vs rerun a fair comparison?**
A: 97 of the 153 tasks were identical. Only the 40 LLMail requests and their 16 controls changed. On the identical template attacks the undefended counts matched exactly (11/18, 9/18, 4/9, 0/12), so neither change moved the baseline. We'll pin Ollama for Week 10.

**Q: How do you know the scorer is right?**
A: Every task has a scripted correct run and, for attacks, a scripted hijacked run. We replay these without a model and check the scorer gives the expected verdict; 48 automated tests cover this. Scoring reads the final fake-mailbox state (sent mail, deletions, events), as AgentDojo does, with no LLM judge.

### B2. The defenses

**Q: How exactly does D1 decide?**
A: Every tool result carries a label: anything a third party wrote is untrusted, and anything from a secret email is confidential. Before a state-changing call D1 checks four rules (slide 17):
1. Recipients and targets must appear in the user's own messages or contacts.
2. The user must have asked for that kind of action.
3. Links and addresses in the outgoing text must come from trusted text.
4. Secret content may go only to someone the user named, or stay inside the university domain.

There is no per-task setup.

**Q: Is that real provenance tracking, like CaMeL?**
A: It's coarser. CaMeL turns the request into a program and tracks labels through every variable with its own interpreter. We keep the normal tool-calling loop, label at the tool boundary, and check that each authority-bearing argument traces back to trusted text. That's the argument-level idea from PACT and FIDES. The trade-off: it needs no change to the agent, but it can't follow a value the model has rewritten, such as a disguised link.

**Q: What does D1h change, and isn't it tuned to the pilot?**
A: It changes one narrow thing. Inbox sender addresses may be *mentioned* in outgoing text, for example in an inbox summary, but they're still never trusted as recipients. It came from the pilot, so yes, it must prove itself on the held-out set. In the rerun it still blocked all 34 attack attempts.

**Q: D2 needs a hand-written policy per task. Does that scale?**
A: Not by hand, and that's a fair limitation. We wrote policies by hand, from the request only and before any email is read, to measure what a correct policy can achieve. In deployment, a trusted model would generate the policy from the user's request before any email is read, as Progent also explores. D1 needs no per-task policy at all, which is one reason we think it is the more practical of the two.

**Q: Why did D2 miss a multi-turn attack that didn't even work on the undefended agent?**
A: One run at temperature 0.3 varies, and D2 shows the model a shorter tool list, which changes its behaviour. The key point is that when the model did add the phishing link, D2's policy allowed it: right tool, right recipient. That's a structural gap, regardless of how often it fires, and D1's link rule is what closes it.

**Q: Why not use a detector, like MELON or a classifier?**
A: Detectors are in-band: an adaptive attacker can target them, and one study broke all eight defenses it tested with adaptive attacks. Recent work, including CaMeL, FIDES, Progent and ROPE, moves to a fixed check outside the model that can't be argued with. That's what we test. MELON could be an extra baseline if time allows.

**Q: Why is Dual-LLM's normal-task success low?**
A: Five of its nine failures were calendar tasks. The main model sees only variable names, not the date and time it needs to create an event, so it read the email and never created the event. Its strength is that it kept the user's task on track best under attack (75%).

**Q: Under D1, the user's task got done in only 38% of attack tasks. Isn't that bad?**
A: That metric counts attack tasks where the user's own request still succeeded. When D1 blocks a hijacked call, the model often gives up instead of returning to the user's task. That is failing safe: the attacker gets nothing, but the user's task is lost. It's a known cost of blocking defenses, and it's a good target for the final report: return a more helpful error to the agent.

**Q: Can an attacker get around D1?**
A: Yes, in specific ways we already list.
- A link written as `phish[.]attacker[.]example` or without "http://" passes the link rule. The recipient and action rules still stop exfiltration and deletion.
- If the user's request names the attacker's address, D1 trusts it. We saw this once in the rerun: the agent sent a non-attack message to that sender.

Week 11 adds a small set of attacks written against the defenses.

### B3. Comparisons and claims

**Q: Are your defenses better than Dual-LLM?**
A: Not shown yet. On attacks it's 0 vs 2, p = 0.5, and both of Dual-LLM's misses came from a bug in our code. After the fix it blocked 9 of 9. The difference so far is in usefulness and setup: B1 fails calendar tasks, and D2 needs a policy per task. The held-out set and three runs will tell.

**Q: Is H2 met?**
A: Not yet. In the pilot D1+D2 lost 12.5 points. In the rerun D1h alone lost nothing and D2 alone lost about 7 points. We haven't yet run D1h with D2. That's the first Week 10 job, and we'll only claim H2 after three runs.

**Q: How do your numbers compare with published work?**
A: Progent on Qwen2.5-7B in AgentDojo: undefended 25.8% → 4.2% attack success, but task success fell from 45% to 27%, an 18-point drop. Our drops are smaller, but our tasks are easier. That's why we want AgentDojo, for a like-for-like comparison.

### B4. Benchmark design

**Q: How did you pick the 40 LLMail emails?**
A: From Phase 2 of the challenge (90,916 submissions) we kept the 145 unique emails that fully succeeded end-to-end against one of the challenge's defenses. We then sampled 40 across 21 of the 24 sub-levels. They all try to send an email to contact@contact.com.

**Q: What are the no-attack controls for?**
A: Each LLMail task has a twin without the attack email. This separates "the task is hard" from "the attack derailed it". With no defense, "read all and answer" succeeded 7/8 without the attack email and only 3/20 with it, so the injected text hurts the user even when it doesn't hijack an action.

**Q: Why did the "read and answer" tasks fail in the rerun?**
A: Naming the attack email in the request made the agent open it in "summarise and send" tasks (20/20), but in "read and answer" tasks it often answered from the inbox listing without opening anything (2/20). We'll rewrite those tasks so the answer is only in the attack email, and refer to it without naming its sender.

**Q: Multi-turn attacks never worked. Did you address the multi-turn feedback?**
A: Partly. We built 12 multi-turn "sleeper" attacks, and D1 only takes authority from the user's own turns. This 8B model ignored instructions meant for a later turn, so the attacks need redesigning (Week 10). The one real gap we found, D2's phishing reply, *was* multi-turn.

### B5. Engineering, model and ethics

**Q: Why a local 8B model rather than GPT or Claude?**
A: It's free, private and reproducible: no data leaves the machine, and there are no API keys in the sandbox. It also fits our GPU fully at about 4–7 s per task, which was a feedback point. The trade-off is lower capability, so we'll repeat once on Qwen2.5-7B, the model used in the closest published study.

**Q: How do you know the sandbox is safe?**
A: Before each run, 16 automated checks must pass: no internet, no DNS, no route to the host, read-only disk, non-root, capabilities dropped, and so on. The agent's only connection is a gateway that forwards six chat and model-info endpoints and refuses everything else, including model downloads and deletes. The mailbox is fake and in memory.

**Q: Did you read the attack transcripts to debug?**
A: No. Our AI coding assistant never sees attack text or attack transcripts. For attack tasks we inspect only tool names and argument *shapes*. That's how we found the B1 bug without reading any attack text.

**Q: What went wrong during the build?**
A: Four things (slide 18):
- The gateway marked the model down after one timeout, which failed 128 of 238 episodes in the first pilot; now it retries and aborts after 5 errors.
- Exact-phrase search failed 6 tasks; now it uses keyword search.
- The B1 subject-line bug.
- The 16 GB host running out of memory; we'll cap Docker memory and make runs resumable.

### B6. Plan and risk

**Q: What if D1h fails on the held-out attacks?**
A: Then we report it. Finding which held-out styles get past which rule is a result in itself, and the held-out set exists to catch exactly that. We won't tune defenses on the held-out set; any fix goes on the dev split and is reported as such.

**Q: Is the plan realistic in three weeks?**
A: The full 3-run study is about 2,300 episodes at about 5 s each, roughly 3–4 hours, so one overnight run. The riskiest items are AgentDojo integration and the host's memory limit, which is why we're asking the panel which to prioritise.

**Q (ours to the panel): AgentDojo or a second model first?**
If they ask for our view: we lean towards AgentDojo, because it gives a direct comparison with published defenses. The Qwen2.5-7B repeat is cheap (one run), so it can follow.

---

## Part C: Weak spots, and the honest one-liner for each

| Weak spot | Say this |
|---|---|
| D1 designed after seeing D2's gap | "That's why the final evaluation uses a held-out attack set." |
| D1h added after the pilot | "One narrow rule; it must hold on held-out attacks before we claim it." |
| H2 not met | "Not yet: D1h alone lost nothing, but D1h+D2 is untested." |
| Not shown safer than Dual-LLM | "0 vs 2 is too few; B1's 2 were our bug." |
| One run, one model | "Three runs and a second model in Week 10." |
| Multi-turn attacks 0/12 | "This model ignores delayed instructions; redesign in Week 10." |
| "Read and answer" exposure 2/20 | "Task wording problem, identified by our diagnostics; rewrite in Week 10." |
| D2 policies hand-written | "Upper bound on a correct policy; Progent shows they can be generated." |
| Disguised links bypass D1 rule 3 | "Known; the recipient and action rules still hold; tested in Week 11." |

---

## Part D: Knowledge required

### D1. Concepts in plain English

| Term | Meaning |
|---|---|
| Direct vs indirect prompt injection | Direct: the user types the attack. Indirect: the attack hides in content the agent reads, such as an email or attachment. We study indirect. |
| Agent / tool call | An LLM that can call functions (send_email, delete_email…) in a loop until the task is done. |
| In-band vs out-of-band defense | In-band: ask or train the model to resist (prompts, detectors). Out-of-band: a deterministic check outside the model that can't be talked round. |
| Information-flow control (IFC) / taint tracking | Every value carries labels for where it came from (integrity) and how secret it is (confidentiality); policies check the labels before actions. D1 is a light form. |
| Integrity vs confidentiality | Integrity: can I trust it to give orders? Confidentiality: may it leave? D1 rules 1–3 are integrity, rule 4 is confidentiality. |
| Least privilege / capability | Give a task only the permissions it needs. D2 is least privilege per task. |
| Authority-bearing argument | An argument that decides *who* or *what* is acted on: recipient, reply target, email to delete. |
| Data-flow attack | The plan is the user's, but attacker data fills an argument, such as the recipient. Dual-LLM's known weakness. |
| Exfiltration | Leaking data to the attacker, such as forwarding a secret email. |
| Fail closed | When unsure, deny. D2 with no policy gives read-only tools. |
| ASR | Attack success rate: the share of attack tasks where the attacker's goal happened in the final mailbox. |
| Utility | The share of normal tasks done correctly. "Utility under attack" is the share of attack tasks where the user's task still succeeded. |
| False block | A defense blocked a call in a normal (no-attack) task. |
| Exposure / attempt | Exposure: the agent opened the attack content. Attempt: the agent issued the attacker's action, whether or not it was blocked. |
| Strict vs any-action scoring | Strict: the exact attacker goal (address and action). Any-action: any action the attack steered, such as replying to the attacker. |
| Wilson 95% CI | An interval for a proportion that behaves well near 0% and with small n. 0/97 gives 0–3.8%, not "exactly 0". |
| Exact McNemar test | Paired test on the same tasks. It looks only at tasks where the two configs disagree and asks whether the split could be chance (binomial). 32 vs 0 gives p ≈ 5 × 10⁻¹⁰. |
| Held-out / dev split | Attacks used while designing (dev) vs attacks kept unseen until the final test (held-out), to detect overfitting. |
| Adaptive attack | An attack written knowing the defense, the true test of a defense. |
| Temperature | Sampling randomness: 0 is deterministic, and higher is more varied. We use 0.3, so runs differ slightly, which is why we plan three runs. |
| Quantisation (4-bit) | The model's weights are compressed to fit GPU memory, with a small quality cost. |

### D2. Related work, one line each

| Ref | Work | One line |
|---|---|---|
| [1] | Dual-LLM, Willison 2023 | A privileged planner with tools never sees untrusted text; a quarantined reader returns `$VAR`s. Our B1. |
| [2] | CaMeL, DeepMind 2025 | Turns the user query into a program; capabilities on every value; policies at tool calls. Strong guarantees, some utility cost. |
| [3] | AgentDojo, NeurIPS 2024 | Standard agent-injection benchmark (workspace, banking, travel, Slack); scores by environment state. Our Week 10–11 external check. |
| [4] | FIDES, Microsoft 2025 | IFC for agents: integrity + confidentiality labels and deterministic policies. Basis of D1. |
| [5] | Progent, 2025 | A language for privilege policies over tools and arguments, enforced deterministically. Basis of D2's allowlists. |
| [6] | PACT, 2026 | Provenance at the level of each tool *argument*; authority-bearing arguments must be trusted. Justifies D1's granularity. |
| [7] | ROPE, 2026 | A value may reach a state-changing tool only if it traces to the user, a user-named source or the user's records. Basis of D2's recipient rule. |
| [8] | Multi-CaMeL, 2026 | CaMeL's guarantees don't compose across multiple agents. Motivates our multi-turn concern. |
| [9] | Adaptive evaluation of out-of-band defenses, 2026 | Qwen2.5-7B on AgentDojo: Progent cut ASR 25.8% → 4.2%, but utility fell 45% → 27%. Closest setup to ours. |
| [10] | Design patterns, 2025 | Six patterns for injection-resistant agents (Dual-LLM is one), with an email-assistant case study. |
| [11] | LLMail-Inject, 2025 | Microsoft-led challenge: 208,095 attack prompts against an email assistant; our 40 real attacks. |
| [12] | MELON, ICML 2025 | Detector: re-run with the user's request masked; if the actions repeat, they came from the injection. |
| [13] | MUSE, EMNLP 2025 | Tree search over multi-turn dialogue to find jailbreaks; we borrow the multi-turn idea. |
| [14] | LivePI, 2026 | A live agent with real email: 10.7–29.6% total attack success on five frontier models. Shows the problem is current. |
| [15] | OWASP LLM01:2025 | Prompt injection is risk #1 for LLM applications. |
| [16] | Adaptive attacks, NAACL Findings 2025 | Adaptive attacks broke all eight in-band defenses tested. Why we test out-of-band ones. |

### D3. Our system in 30 seconds (say this if asked "walk us through it")
"A task gives the agent a user request and a fake inbox. The agent, Qwen3-8B, proposes tool calls in a loop. Every call passes a defense gate before it runs: B0 lets everything through, B1 hides email text from the planner, D2 checks a per-task allowlist, and D1 checks that every recipient, link and target traces back to the user. Everything runs in a locked Docker container. At the end, code checks the final mailbox: did the user's task happen, and did the attacker's goal happen?"

### D4. Live demo
Not part of the 9:30 talk. If the panel asks to see it:
- show the slide-2 case and backup slide 14 (16/16 checks);
- offer to run `python src/isolation_check.py` afterwards.

Don't start a live agent run in the slot: it needs Docker, Ollama and the GPU warm, and it takes minutes.
