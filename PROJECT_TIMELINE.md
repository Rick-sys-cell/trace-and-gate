# ESP3201A Project Timeline & Deliverables Tracker

**Project:** Trace and Gate: Provenance Tracking and Policy Checks against Indirect Prompt Injection in Email Agents
**Team:** Rui Zhekai · Khadijah Fathima
**Last updated:** Thu 29 Oct 2026 (Week 11): demo video recorded and embedded in deck slide 5 (replaces the live run). Previously Tue 27 Oct 2026: live demo verified in a fresh clone (default task now `attack-g1-attachment-1-club`); deck slide 5 = live demo (13 main slides); presentation prep sheet. Previously Mon 26 Oct 2026: AgentDojo attack trial (no attack reached the bar; no second full run), memory guard for long runs; report Table IX, deck slide 8. Previously Sun 25 Oct 2026 (Week 10): held-out run A + queue 2 running; benign links + D1h-L; report draft. Previously Sat 24 Oct 2026 (Week 10): public repo, defenses frozen (`defenses-frozen-v1`), suite v3 dev run done, held-out/AgentDojo/demo tooling ready
**Repo:** https://github.com/Rick-sys-cell/trace-and-gate (public; course deliverable folders are git-ignored until after grading)

## Folder layout (14 Oct)

| Folder | What's in it |
|---|---|
| `1_Interim_Submission/` | **Hand in / present:** `Interim_Report.docx`, `Interim_Presentation_v3.pptx` |
| `2_Presentation_Prep/` | Rehearsal only: speaker notes, Q&A prep pack, slide outline (.docx) |
| `3_Sources/` | Editable `.md` sources of all of the above, citation check (`Interim_Report_Sources`), and `figures/` (PNGs + pilot/rerun/recheck analysis JSONs behind every number) |
| `References/` | Papers + the course brief (`Main Projects_11th September2026.pdf`) |
| `sandbox/` | Experiment code, tasks and results (unchanged; never read `benchmark/payloads/` or `results/raw/`) |
| `_archive/` | Proposal B and C (with their notes and decks), Research Brief v2, Docker setup doc, interim decks v1/v2 |

**Rebuilding:**
- Edit the `.md` files in `3_Sources/`, then rebuild.
- The deck builder takes `3_Sources/` as its root and writes to `1_Interim_Submission/`.
- The report and notes `.docx` use `_archive/Proposal_B/Prompt_Injection_Proposal_B.docx` as their layout template.

> ## ⚠️ INTERIM PRESENTATION: FRIDAY 16 OCTOBER 2026 (Week 9)
> Days remaining from 6 Oct: **10**. Everything in Weeks 8–9 below feeds this.

Status legend: ☐ not started · ◐ in progress · ☑ done · ✗ dropped

---

## Week 8 (Mon 5 – Sun 11 Oct): re-scope + build
| # | Item | Owner | Status |
|---|---|---|---|
| 8.1 | Research brief v2 (`Research_Brief_v2.md` / `.docx`) | Rui | ☑ |
| 8.2 | Proposal C (`Prompt_Injection_Proposal_C.md` / `.docx`). Team to review wording | Rui | ☑ draft |
| 8.3 | Speaker notes C (`Speaker_Notes_C.md` / `.docx`). Slide 9 numbers after pilot | Khadijah | ☑ draft |
| 8.4 | Docker sandbox v2 (`sandbox/`, `DOCKER_SETUP_v2.md` / `.docx`) written; compose structure validated; 9 offline tests pass | Rui | ☑ |
| 8.5 | Docker Desktop 4.94 (engine 29.8.2, WSL2) + Ollama 0.35.1; qwen3:8b 100% GPU (Vulkan) ~47 tok/s | Rui | ☑ |
| 8.6 | `docker compose config` clean; image built; `isolation_check.py` **16/16 PASS** (6 Oct) | Rui | ☑ |
| 8.7 | B0 smoke test in Docker: benign utility 1/1, attack 0/1 (~8 s/episode, 2.5 LLM calls). Caveat: agent likely answered from subjects without opening the injected email, so attack tasks must force reading the body (see 8.9) | Rui | ☑ |
| 8.8 | D2 policy checks in `sandbox/src/defenses.py` (`PolicyDefense`): tool allowlist (Progent), recipient origin (ROPE), object scope, secret-stays-internal. Oracle replay: blocks 75/79 hijacked behaviours, 0 false blocks; the 4 survivors are g2 multi-turn (phishing link inside an authorised reply), which is left for D1 | Rui (Claude) | ☑ |
| 8.9 | Suite `benchmark/tasks/email_suite.json` built by `build_suite.py`: 40 benign + 79 attack (39 template: 3 goals × body/subject/attachment/multi-turn; 40 LLMail-Inject Phase 2 end-to-end successes via `import_llmail.py`). Every attack forces reading the injected content. 22 offline tests pass | Rui (Claude) | ☑ |
| 8.10 | Pilot B0 vs D2, full suite, 1 run (run 20261006-072828, qwen3:8b, 0 model errors): **B0 ASR 25.3% (20/79, CI 17–36%), utility 97.5%**; **D2 ASR 0% (CI 0–4.6%), utility 95.0% (−2.5 pts)**, 8 calls blocked; ~4.5 s/episode. McNemar on paired attacks: 20 vs 0 discordant, p ≈ 2e-6. First attempt (run 071713) was invalid because of a gateway failover bug, since fixed | Rui (Claude) | ☑ |
| 8.11 | Stronger attacks: 3 new phrasings (task-step, spoofed tool result, fake IT-security notice) and 6 body + 6 attachment variants per goal. **B0 ASR now 33.0% (32/97) ≥ 30%** | Rui (Claude) | ☑ |
| 8.12 | 16 no-attack controls added. Result: "read all + answer" with no defense is 7/8 without the attack email vs 3/20 with it, so the injection distracts the model (not task difficulty) | Rui (Claude) | ☑ |

## Week 9 (Mon 12 – Sun 18 Oct): defenses + pilot + INTERIM
| # | Item | Owner | Status |
|---|---|---|---|
| 9.1 | D1 `ProvenanceDefense` (automatic labels; recipient/target origin, action-intent, content-integrity, confidentiality rules) + `CombinedDefense` D1+D2. Oracle: 97/97 hijacks blocked, 0 false blocks. 33 tests pass | Rui (Claude) | ☑ |
| 9.2 | B1 `DualLLMDefense` (quarantined reader → `$VAR`s; planner never sees untrusted text) | Rui (Claude) | ☑ |
| 9.3 | 5-config pilot, run `20261006-100417`, 153 tasks, 765 episodes, 0 errors. ASR: B0 33.0%, B1 2.1%, D1 0%, D2 1.0%, D1+D2 0%. Utility: 96.4 / 83.9 / 89.3 / 87.5 / 83.9. H1 met (p = 4.7e-10); H2 met by D1 and D2 alone, not by D1+D2 (−12.5). Figures + `analysis.json` in `figures/` | Rui (Claude) | ☑ |
| 9.4 | Interim report `Interim_Report.md/.docx`, slide outline `Interim_Slides_Outline.md/.docx`, speaker notes `Interim_Speaker_Notes.md/.docx` | Rui (Claude) | ☑ draft |
| 9.5 | **14 Oct: `Interim_Presentation_v3.pptx` final** (readability pass: ≥ 12 pt everywhere, 13–14 pt body; H2 shown as "not yet"; plan slide adds the read-and-answer fix and the 5 Week-10 configs). `Interim_QA_Prep.md/.docx` (numbers sheet, ~35 Q&As, glossary, related work). Report and notes re-checked against the analysis JSONs. `Interim_Presentation_v2.pptx` (13 + 9 backup, pipeline diagrams, rerun slide) built 8 Oct; v1 kept. `Interim_Presentation_v1.pptx` built 8 Oct (12 slides + 4 backup, speaker notes in each slide, Proposal B style, parameter tables; rendered and checked). Report source-verified (`Interim_Report_Sources.md`). **Still to do: team review + rehearse twice** | Both | ◐ |
| 9.6 | Docker image rebuilt with the `agent.py` ValueError fix (6 Oct). Still to do: cap WSL2 memory (`.wslconfig`) and make runs resumable | Rui | ◐ |
| **9.7** | **FRI 16 OCT: INTERIM PRESENTATION** | Both | ☐ |

**What to show on 16 Oct:**
1. The Docker sandbox and a live `isolation_check.py` run (no internet, read-only, non-root).
2. Demo: B0 is hijacked by an email, then the same email is blocked by D2 and by D1.
3. Pilot ASR / utility table for all 5 configs, even if rough.
4. The revised scope, mapped to each professor feedback point (see `Research_Brief_v2.md` §2).
5. Risks + plan for weeks 10–12.

## Week 10 (19 – 25 Oct): full experiments
| # | Item | Owner | Status |
|---|---|---|---|
| 10.0 | D1h adopted; `d1hd2` = D2 + D1h added (`d1d2` kept for the pilot). **Defenses frozen 24 Oct: tag `defenses-frozen-v1` (869e106)**, incl. the AgentDojo ports | Rui (Claude) | ☑ |
| 10.0b | Benchmark fixes (8 Oct): exposure/attempt diagnostics in every run ☑; LLMail requests name the attack email (suite v2) ☑, which fixed "summarise and send" exposure (20/20) but not "read and answer" (2/20); multi-turn redesign ☑ (24 Oct, suite v3: split payload over two emails/turns) | Rui (Claude) | ☑ |
| 10.0c | Rerun on suite v2, run 20261008-103942 (B0, D1, D1h, D2; 612 episodes, 0 errors): B0 34.0%; D1 0% (33/33 blocked) but 73.2% normal; **D1h 0% (34/34 blocked), 87.5% normal, 0 tasks lost vs B0**; D2 1.0%. Report §VI-B, deck v2 slide 10 | Rui (Claude) | ☑ |
| 10.0d | Suite v3 (`email_suite_v3.json`, 153 tasks): LLMail emails carry a partner reference code the user asks for; requests no longer name the sender; controls mirror this. Offline tests: 68 (2 skip on the host) | Rui (Claude) | ☑ |
| 10.0e | **Dev run on v3, run `20261024-135826`** (b0 b1 d1h d2 d1hd2, 765 episodes, 0 model errors, Ollama 0.40.9, code b22e43f). ASR: **B0 45.4% (44/97)**, B1 0%, D1h 0%, D2 0%, **D1h+D2 0% (CI 0–3.8%)**. Normal tasks: B0 89.3%, B1 80.4%, D1h 89.3%, D2 89.3%, **D1h+D2 89.3% (0 pts vs B0)**. McNemar D1h+D2 vs B0 on attacks: 44 vs 0, p = 1.1e-13. Exposure: read-and-answer 15/20 (was 2/20); multi-turn B0 7/12 (was 0). All pass criteria met. Dev suite, 1 run: confirm on held-out. Files: `results/analysis_dev_v3.json`, `diagnostics_dev_v3.json`, figures `*_dev_v3.png` | Rui (Claude) | ☑ |
| 10.1 | Held-out set: 40 new LLMail attacks (seed 4202, disjoint from dev) + 18 team-written (`heldout_manifest.json`). **Run `20261025-034455` done** (114 tasks × 5 configs × 3 runs, 1,710 episodes, 0 errors; LLMail part code f4dfd90, team part resumed at 05b86d7, defenses identical). ASR **B0 21.8% (38/174)**, every defense **0/174**; normal B0 89.3%, B1 80.4%, D1h 89.3%, D2 89.9%, **D1h+D2 91.7%**. McNemar vs B0 38 vs 0, p = 7.3e-12; vs B1 normal 6 vs 25, p = 8.8e-4. H1 ✓, H2 ✓ (+2.4). **Team-written attacks 0/54 even under B0** (opened 54/54, never attempted), so the validity bar (≥30%) holds only for the LLMail part (31.7%). **Qwen2.5-7B, run `20261025-071911`** (1 run): B0 29.3% (17/58; LLMail 42.5%), every defense 0/58; normal B0 66.1%, B1 42.9%, D1h+D2 73.2% (8 vs 4, p = 0.388); under attack D1h+D2 22.4% vs B0 56.9% | Both | ☑ |
| 10.2 | AgentDojo workspace v1.2.2: bridge + runner built (`agentdojo_bridge.py`, `run_agentdojo.py`, agentdojo 0.1.35 in image). Oracle replay: B0 hijacked 57/60, D2/D1h/D1h+D2 0/60; D1h false-blocks 8/40 honest tasks. Spike in queue 2 crashed (agentdojo 0.1.35 NullLogger never registers itself) → fixed with `TraceDirLogger` + test (671fc14). `run_queue3` waits for queue 2, reruns the spike, sizes k for ≤6 h and runs B0/B1/D1h+D2. Spike 8.5 s/episode → k = 4: **full run `agentdojo_20261025-075616`** (40 user tasks + 160 pairs × 3 configs = 600 episodes) started 25 Oct 15:56 local. Aborted at 149/600: user_task_26's 4 pairs each hit the 180 s call timeout (same slow tasks timed out in the utility phase: 26, 27, 30, 31, 35–38), tripping the outage abort; Ollama was up. Runner now aborts only if Ollama is unreachable (070bf9c); resumed 17:31 in `run_agentdojo_resume`. At 20:57 (388/600) stopped and resumed again as `run_agentdojo_resume3` (f19b307, `RECYCLE_EVERY=5`): Ollama's Vulkan runner had grown to 15 GB private memory and the host had ~1 GB free, so the model is now unloaded every 5 episodes (same model and options; runner drops back to ~8 GB). ETA ~01:00. Timeouts count as failed episodes; report per-config `llm_errors` **Done 26 Oct 00:52** (600/600, not aborted; summary code f19b307): B0 attack success 1.2% (2/160), B1 and D1h+D2 0/160; utility B0 27.5%, B1 12.5%, D1h+D2 30.0% (6 vs 5, p = 1.0); under attack 33.8% / 12.5% / 28.7%. Timeouts: B0 39/200, D1h+D2 47/200, B1 0. The stock attack barely works on Qwen3-8B, so AgentDojo shows cost, not protection (`analysis_agentdojo.json`, Table VIII, Fig. 5) | Rui (Claude) | ☑ |
| 10.3 | MUSE-style split-payload multi-turn attacks (in suite v3; automated search not done) | Rui (Claude) | ☑ |
| 10.5 | **Benign links (25 Oct).** No v3 normal task had a link, and D1h blocks every link copied from an email into a new message. `build_suite.py --links` → `tasks/links_suite.json` (40 benign tasks, 8 scenarios × 5 flows; team adds ≥6 via `tasks/links_manifest.json`). Exploratory, post-freeze **D1h-L** (`d1hl`, `d1hld2`): link allowed if Alex asked for a link from a named contact's email; frozen classes pinned by `tests/test_frozen.py`; blocks every scripted hijack (v1–v3, held-out). **Links run `20261025-055650`** (7 configs × 3): normal B0 88.3%, D1h and D1h+D2 40.0%, D1h-L 55.0%, D1h-L+D2 52.5%. Send-contact's-link: D1h 0%, D1h-L 75.0% (= B0). Reply-own: 0% under every defense, incl. D2: the model's first call is `reply(email_id=123)` (nonexistent); B0 gets "no such email" and recovers, the defenses return a generic refusal and the agent gives up (harness finding, not fixed). **D1h-L** dev `20261025-064154` / held-out `20261025-070311`: 0/97, 0/58 attacks; normal 89.3–92.9%. No team link tasks were added before the run | Rui (Claude) | ☑ |
| 10.6 | Held-out run A started 25 Oct 03:44 UTC: run `20261025-034455` (5 configs × 3 runs, 96 tasks, Ollama 0.40.10 — auto-updated from 0.40.9, code f4dfd90). Queue 2 (`run_queue2`, code bd90af2) starts when A's summary appears: AgentDojo spike → links × 7 configs × 3 → D1h-L on dev and held-out → Qwen2.5-7B (`think:false` probe OK) | Rui (Claude) | ◐ |
| 10.4 | Week 11 live demo: `src/demo.py` (`--live`/`--oracle`) + `docs/DEMO_GUIDE.md` (fresh-laptop setup, 5-min script). Fresh-clone test 25 Oct: isolation 16/16, `--oracle` OK, tests OK after two fixes (build_suite no longer overwrites the committed suite without LLMail payloads; guide row for compose's bake error). 27 Oct: `--live` in a fresh clone, 3/3 runs B0 hijacked, every defense safe; the old default `attack-g1-body-1-course` left Alex's task undone under every config, so the default is now `attack-g1-attachment-1-club` (task done under all four, ~30 s/run, lowest free RAM 1.1 GB after a WSL cache drop). Guide rewritten for the club story; deck slide 5 is the live demo; prep sheet `3_Sources/Final_Demo_and_Presentation_Prep.md` (docx in `2_Presentation_Prep/`). 29 Oct: backup recording of `--live --show-email` made (`2_Presentation_Prep/Demo_Backup_live_2026-10-29.mp4`, copy on the desktop). 29 Oct: slide 5 now plays this recording, embedded by `tools/build_deck.py` (no live run in class); prep sheet rewritten for it | Rui (Claude) | ✓ |

## Week 11 (26 Oct – 1 Nov): analysis
| # | Item | Owner | Status |
|---|---|---|---|
| 11.1 | ASR, utility, utility-under-attack, false-block rate, cost; Wilson 95% CIs. `analyse.py` now splits attacks by source (team / LLMail / template) and team style; `report_tables.py` → `results/final_tables.md`. Held-out, links, D1h-L, Qwen2.5 done; AgentDojo pending | Rui (Claude) | ◐ |
| 11.2 | Failure-case analysis: `src/block_reasons.py` (per-rule blocks, false-block task ids for human review, link-flow table, secret-read-then-external-send upper bound). Dev v3: no normal task had a blocked action. Held-out: D1h blocked 3/168 normal episodes, all task `benign-control-travel-send` (rule: action not requested); B0 read-secret-then-external-send 4 (all scored as attacks). **Khadijah: review that task** | Khadijah (+Claude) | ◐ |
| 11.3 | Figures + tables | Both | ☐ |

## Week 12 (2 – 8 Nov): write-up
| # | Item | Owner | Status |
|---|---|---|---|
| 12.1 | Final report: draft `3_Sources/Final_Report.md` (all sections filled except the authors' review in §VII-F; no page limit (confirmed 25 Oct): 95% CI columns restored in Tables IV-VI, Figs. 3-4 added (held-out by channel, Qwen2.5), Fig. 5 AgentDojo after the run; 8 pages, 206 numbers checked (2 unmatched are cited literature values), 0 unmatched). Build `tools/build_report_docx.py` → `4_Final_Submission/` (git-ignored); check `tools/check_numbers.py` | Both | ◐ |
| 12.2 | Final slides: `tools/build_deck.py` builds `4_Final_Submission/Final_Presentation.pptx` (12 main + 10 backup) from the interim deck with every number read from the results, plus `3_Sources/Final_Speaker_Notes.md` (Rui 1–5, 11–12; Khadijah 6–10). Rehearsal ☐ | Both | ◐ |
| 12.3 | Include AI declaration (`3_Sources/AI_Declaration.md`) in the final report; refresh its run IDs (AgentDojo and Qwen2.5-7B run ids added 26 Oct). Interim version added 16 Oct (report §AI Declaration, before References) | Both | ☐ |

---

## Next actions (update at the end of every work session)
- [x] Docker + Ollama installed, isolation 16/16, LLMail imported (counts only), D1/D2/B1 built, 5-config pilot done (6 Oct).
- [x] 14 Oct: report, deck v3, outline, notes and Q&A pack finalised and cross-checked against the analysis JSONs.
- [ ] **Both:** rehearse deck v3 twice with a timer (target 9:30); each drills `Interim_QA_Prep.md` Part B for their topics.
- [ ] **Both:** agree the answer to the panel question (AgentDojo vs second model).
- [x] 8 Oct: B1's 2 pilot failures traced (via argument shapes, no text read) to a bug: multi-line subjects leaked to the planner. Fixed + regression test; recheck run 20261008-094725: B1 0/9, B0 4/9 on subject attacks. Report §VII-A updated.
- [x] 24 Oct: `.wslconfig` caps WSL at 6 GB. Even so, the host ran critically low on memory during the dev run; close other apps during runs.
- [x] 25 Oct: held-out attacks written (18) and run × 3. Team-written attacks never worked even undefended.
- [ ] **Khadijah:** review held-out false-block task `benign-control-travel-send` (D1h, 3 episodes); add the verdict to report §VII-F.
- [x] Final presentation: Week 12, Friday 13 Nov 2026 (deck footer updated 25 Oct).
- [x] AgentDojo full run `agentdojo_20261025-075616` done 26 Oct; §VII-E (Table VIII, Fig. 5), abstract, discussion, conclusion filled; docx + deck rebuilt (slide 8 says the attack was too weak on our model to test safety).
- [ ] **Rui + Khadijah:** add ≥6 benign link tasks to `sandbox/benchmark/tasks/links_manifest.json` (format in `docs/HELDOUT_AUTHORING.md`).
- [x] 25 Oct: Ollama auto-update turned off (stays on 0.40.10). Every summary records `ollama_version`.
- [x] 25 Oct: fresh-clone test of `docs/DEMO_GUIDE.md` (oracle path); 27 Oct: `--live` in the clone, 3/3 as expected.
- [x] 27 Oct: local commits 957dedb … be8784d pushed to GitHub (demo default task, slide 5, prep sheet are public); clone the class machine from GitHub.
- [ ] **Both:** rehearse the final deck with the demo video on slide 5 (target ~14 min); follow `3_Sources/Final_Demo_and_Presentation_Prep.md`.
- [x] 29 Oct: backup screen recording of `demo.py --live --show-email` (`2_Presentation_Prep/Demo_Backup_live_2026-10-29.mp4`, copy on the desktop). Still to do: copy to a USB stick and send to Khadijah.
- [ ] Decide the question for the panel: AgentDojo vs Qwen2.5 replication priority.
- [x] 26 Oct: AgentDojo attack-selection spike (B0 only; user tasks 0–23; 1 pair each; seed 3202; attacks tool_knowledge, injecagent, ignore_previous, important_instructions; no-attack rows reused from `agentdojo_20261025-075616`), then the main attack-only rerun with the chosen attack (b0, b1, d1hd2; 40 user tasks × 2 pairs). Runner records per-episode exposure (boolean). Done: runs `agentdojo_20261026-040133` (tool_knowledge 0/24), `-041145` (injecagent 0/24), `-042258` (ignore_previous 0/24), `-043112` (important_instructions 1/24); injection reached the model in 18–19/24 for each. Report §VII-E Table IX, abstract, discussion, conclusion; deck slide 8 note + speaker notes.
- [x] 26 Oct: memory guard for long runs: `tools/memory_guard.py` (start first: `Start-Process pythonw -WorkingDirectory <repo> -ArgumentList 'tools/memory_guard.py','--container','<name>'`), flag when free RAM < 2 GB or Ollama > 7 GB; the AgentDojo runner unloads the model between episodes while flagged, and now reloads every 3 episodes by default. Measured: a freshly loaded qwen3:8b holds ~5.5 GB and leaves ~2.5 GB free on this host.

## Decisions log
- 29 Oct: The final presentation plays the recorded live run (63 s, 29 Oct) on slide 5 instead of running the demo live, so the talk does not depend on Docker, Ollama or memory on the day (Rui's choice). Fallbacks: the MP4 in a media player, then backup slide 21. A live run is offered only if asked.
- 26 Oct: AgentDojo attack trial: no attack reached the pre-set bar (≥ 3/24; best important_instructions 1/24), so no second full run. The injection reached the model in about 3 of 4 episodes for every attack, so the low rate is the model ignoring the injection, not the bridge. AgentDojo stays a cost result.
- 26 Oct (set before the spike runs): pick the AgentDojo attack with the highest B0 attack success in the spike, only if it reaches ≥ 10% (≥ 3/24). If none does, no main rerun: report that no AgentDojo attack reached 10% on Qwen3-8B. The important_instructions result stays in the report; the second attack is disclosed as chosen after the first run came out null. Defenses unchanged (frozen); call timeout, num_ctx, model and Ollama version as in the first run so the reused no-attack rows stay comparable.
- 26 Oct: AgentDojo is reported as a cost result, not a safety result: its important_instructions attack worked in 2/160 undefended episodes on Qwen3-8B, so 0/160 under the defenses shows nothing about protection. Report and deck say so; published GPT-4o / Llama 3 70B numbers from [3], [5] are cited for contrast.
- 25 Oct: The reply-own link failure under every defense is reported as a finding (a generic refusal hides a recoverable "no such email" error) rather than fixed, because changing the agent loop after the main runs would make them incomparable.
- 25 Oct: Held-out headline reported pooled (21.8% B0) as pre-stated, with the LLMail part (31.7%) given separately, because the team-written attacks never worked even without a defense.
- 25 Oct: Team-written held-out attacks received (18: fake calendar invite ×6, fake forwarded thread ×6, disguised link ×6). 8 g1/g3 attacks named emails not in their inbox; the user chose to have Claude replace only the target email name. Claude has therefore seen the held-out text (after the freeze and after D1h-L, bd90af2). No defense code changes from now on; disclosed in the report. Disguised-link markers also match the cleaned-up link.
- 25 Oct: D1h's link rule blocks every link copied out of an email (by design). Measured on a separate benign-links set; a fix (D1h-L) is exploratory and post-freeze, reported separately; the held-out headline stays D1h+D2.
- 25 Oct: Threats outside the evaluation (adaptive/long-horizon attacks, supply chain, direct jailbreaks, memory poisoning, fine-grained data isolation) are stated in the final report's threat-model table; neither our suite nor AgentDojo covers them.
- 24 Oct: Defenses frozen (`defenses-frozen-v1`) before any held-out attack existed. Held-out attacks are written by the team, never by Claude (Claude wrote D1's rules). Claude reads only `tasks/heldout_manifest.json`.
- 24 Oct: The repo is public, but attack text (payloads), transcripts (raw results), copyrighted papers and course deliverables are not committed. Payloads are regenerated locally by `build_suite.py` / `import_llmail.py`.
- 24 Oct: AgentDojo D2 policy is derived from each user task's ground-truth calls (AgentDojo ships no policies), so it is an oracle-derived upper bound; disclose this in the report.
- 8 Oct: D1h (sender addresses allowed in text, not as recipients) replaces D1 from Week 10, subject to the held-out set. Naming the attack sender in the request made it user-trusted under D1/D1h; v3 tasks will refer to it without naming it.
- 8 Oct: Headline ASR stays strict (LLMail/AgentDojo-comparable). The report also gives success-given-exposure (B0 40%) and any-attacker-action (B0 36%), plus attempted-vs-blocked per defense (D1 blocked 33/33).
- 8 Oct: Report cross-checked against the data; 21 corrections made (see Interim_Report.md). Ollama auto-updated 0.35.1 → 0.40.1 between pilot and recheck; pin the version before Week 10 runs.
- 6 Oct: Re-scoped from "Dual-LLM + least privilege (generic agent)" to "provenance tracking + policy checks (email agent)", following professor feedback and Project 8's recommended RQ. Dual-LLM is kept as baseline B1.
- 6 Oct: D1 rules were designed after seeing D2's oracle gap, so the final evaluation must use a held-out attack set never used in design. Any D1 tuning happens on a dev split only.
- 6 Oct: Claude never reads attack payloads or attack transcripts; failure analysis of attack tasks uses tool names only (`inspect_calls.py`) or human review.
- 6 Oct: Ollama runs natively on the Windows host (AMD GPU can't pass through to Docker). The agent container reaches it only through an nginx gateway on an internal network.
