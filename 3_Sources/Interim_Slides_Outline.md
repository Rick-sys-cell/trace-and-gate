# Interim Slides: Outline (deck v3, 14 Oct 2026, final)

**Deck:** `Interim_Presentation_v3.pptx` (`v1`, `v2` kept for reference) · ESP3201A Interim, Fri 16 Oct 2026 · Rui Zhekai & Khadijah Fathima
**Length:** 13 main slides (about 9:30) + 9 backup slides.
- **Rui:** slides 1–6.
- **Khadijah:** slides 7–13.

The script for each slide is in `Interim_Speaker_Notes.md` and in each slide's notes pane. Q&A prep and background knowledge: `Interim_QA_Prep.md`.

**Numbers:**
- **Pilot:** run `20261006-100417` (`figures/pilot_analysis_…json`, `figures/pilot_diagnostics_…json`).
- **Rerun:** run `20261008-103942` (`figures/rerun_analysis_…json`, `figures/rerun_diagnostics_…json`).
- **B1 recheck:** `figures/recheck_b1_subject_…json`.

**Style:**
- **Base:** Proposal B deck palette (slate ink, white content slides, dark title and closing slides), Calibri, icons in tinted circles.
- **Kicker:** a small label above every title (PROBLEM, METHOD, RESULTS…).
- **Diagrams:** pipelines drawn with native shapes and arrows, so they stay editable in PowerPoint.
- **Status:** shown with ✓ / ! *and* words, never colour alone.
- **Readability (v3):** on the 10 × 5.6 in slide, titles 28 pt, body and cards 13–14 pt, tables 13 pt, footnotes ≥ 12 pt; three rules per defense card; one-line footnotes; every number generated from the analysis JSONs by the builder.

| # | Kicker · Title | Content | Visual |
|---|---|---|---|
| 1 | Title | *Trace and Gate: Stopping prompt injection in email agents* | Dark; 3 icons (poisoned email · trace the data · gate the action) |
| 2 | Problem · Every email is attacker input | Real pilot case: a sponsor attachment makes the agent forward the club's bank-PIN email | 3-step icon flow + stat cards: #1 OWASP LLM01:2025 · 208,095 LLMail prompts · 61% attachment attacks worked |
| 3 | Re-scope · What changed since the proposal | 7 feedback points → what we did | Two-column table |
| 4 | Question · Research question | RQ; H1 ≥ 80% fewer attacks; H2 ≤ 10-pt drop | Two hypothesis cards + 5 config chips |
| 5 | Method · **How one test run works** | Task suite → payload resolver → [Docker sandbox: agent loop → defense gate → email tools, results back labelled] → final mailbox → scorer (code) → run summary → analysis | **Pipeline diagram** (serpentine, dashed sandbox boundary, INPUT/OUTPUT tags) |
| 6 | Method · **Where each defense acts** | Email → B1 reader → agent decides → D2 allowlist → D1 provenance → tool runs; "no" → blocked with a neutral error | **Pipeline diagram** with two zones: "changes what the model READS" vs "checks what it DOES" |
| 7 | Method · Three ways to defend | Three rules each for B1, D1 (+ D1h note), D2, plus each weak spot | Three cards |
| 8 | Method · Benchmark and test setup | 153 tasks (40 / 16 / 57 / 40); v2 note. Parameter table: Qwen3-8B 4-bit, temp 0.3, 16k context, 15 steps, 300 s / 180 s timeouts, pilot 765 / rerun 612 episodes, code scoring, Wilson CI + McNemar | Count card + parameter table |
| 9 | Results · pilot · Attacks fell from 33% to 0% | B0 33% → D1/D1+D2 0%; utility 96% → 84–89% | Chart + table + strip "40% when opened · 33/33 attempts blocked by D1" |
| 10 | Results · rerun · **Are we on track?** | Pilot → rerun for B0/D1/D1h/D2: opened, attack success, success if opened, normal tasks; footnote: 40 unchanged tasks 39/40 for B0, D1, D1h | Table + 3 callouts: **D1h 0% · 0 lost** · 33% → 34% stable · 2/20 "read and answer" opened (next fix) |
| 11 | Discussion · One real gap, one bug | D2 missed the multi-turn phishing reply to Jane; B1's 2 misses were our bug (fixed, 0/9) | Two case cards |
| 12 | Results · Hypotheses scorecard | Validity ✓ · H1 ✓ · safer than Dual-LLM ! not shown · H2 ! **not yet** (pilot D1+D2 −12.5; rerun D1h alone 0 lost, D2 alone −7.1; D1h+D2 not run yet) | Table + 2 cards (D1h: the fix to confirm; the attack itself hurts the user) |
| 13 | Next · Plan to the final report | W10: adopt D1h, fix "read and answer" tasks, redesign multi-turn, held-out attacks × 3 runs of B0, B1, D1h, D2, D1h+D2, Qwen2.5-7B · W10–11 AgentDojo (B0, B1, D1h+D2) · W11 analysis · W12 report; question for the panel | Dark; week pills |

**Backup slides:**
- **B1:** sandbox settings: container → network → gateway → host, plus a settings table and the 16/16 badge.
- **B2:** where attacks get in (pilot heatmap).
- **B3:** **pipeline:** how the benchmark was built (LLMail-Inject 90,916 → 145 full successes → 40 sampled across 21/24 sub-levels → suite 153: 56 normal, 57 template + 40 LLMail attacks → 48 tests → Docker runs).
- **B4:** **flow:** how D1 decides (5 checks; any "no" blocks; the D1h note).
- **B5:** engineering issues.
- **B6:** exposure and attempts (pilot).
- **B7:** attack success by goal.
- **B8:** cost per task.
- **B9:** safety and ethics.
