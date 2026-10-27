# Final presentation: slide outline (draft, 25 Oct)

Built from `1_Interim_Submission/Interim_Presentation_v3.pptx` as the template (same theme, icons,
cards and footer). "From" = the interim slide that is duplicated and edited. Numbers come only
from `sandbox/results/final_tables.md`; **[PENDING]** marks results not yet run.
Target: 13 main slides in about 14 minutes (one minute per slide, two for the live demo), plus backups. Speaker notes go in each slide's notes.

| # | Section | Title (one message per slide) | Content | From |
|---|---|---|---|---|
| 1 | Title | Trace and Gate | Subtitle "Stopping prompt injection in email agents"; ESP3201A · Final presentation · date | 1 |
| 2 | Problem | Every email is attacker input | Same Alex / attachment / agent obeys strip; stat cards: OWASP #1, 208,095 LLMail prompts, dev B0 attack success 45.4% (44/97) | 2 |
| 3 | Question | Research question and hypotheses | H1 ASR(D1h+D2) ≤ 0.2 × ASR(none); H2 U drop ≤ 10 pts; five configs B0 B1 D1h D2 D1h+D2; tested on held-out, 3 runs | 4 |
| 4 | Method | Where each defense acts | Flow diagram with D1h in place of D1 | 6 |
| 5 | Live demo | Live demo: one poisoned email, four agents | Cue table: Alex's sponsor-attachment request; B0 forward ALLOWED (hijacked); D2 tool hidden; D1h forward BLOCKED; D1h+D2 safe; Alex's task done in all four. Rui runs `src/demo.py --live --show-email` (default task attack-g1-attachment-1-club); fallback `--oracle` or slide B8 | 18 (table slide) |
| 6 | Method | What we tested on | Cards: dev v3 (153 tasks), held-out (40 new LLMail + team-written [PENDING n]), benign links (40 + team), AgentDojo workspace; "defenses frozen 24 Oct before any held-out attack existed" | 8 |
| 7 | Results | Development: attacks 45% → 0%, no normal task lost | fig1_asr_vs_utility_slide_dev_v3.png + small table; McNemar 44 vs 0, p = 1.1e-13 | 9 |
| 8 | Results | Held-out: [PENDING headline] | Chart + table pooled over 3 runs with CIs and per-run spread; team-written attacks separately | 9 |
| 9 | Results | It generalises? Second model and AgentDojo | Two panels: Qwen2.5-7B (1 run) and AgentDojo B0 / B1 / D1h+D2; note D2 policy from ground truth = upper bound [PENDING] | 10 |
| 10 | Cost | The cost we almost missed: harmless links | Flow table: ask / forward / reply-own allowed; send-link blocked by D1h; D1h-L recovers contact links, still 0 attacks; exploratory, post-freeze [PENDING] | 11 |
| 11 | Scorecard | Hypotheses scorecard | H1, H2, vs Dual-LLM, generalisation, link cost; Met / Not met / Open | 12 |
| 12 | Scope | What this does not show | Five-row table: adaptive / long-horizon, supply chain, direct jailbreak, memory poisoning, fine-grained isolation × AgentDojo / ours / D1h-D2 in principle | 3 (table) |
| 13 | Close | Takeaways | 3 cards: gate actions outside the model; D2 removes attack surface, D1h catches what rides inside allowed actions; measure the cost on harmless work | 13 |
| B1 | Backup | Sandbox settings | unchanged | 14 |
| B2 | Backup | How D1h decides | 17, D1 → D1h, link rule highlighted | 17 |
| B3 | Backup | Exposure and attempts (held-out) | diagnostics_heldout | 19 |
| B4 | Backup | Attack success by channel / goal (held-out) | fig2 heldout | 15 / 20 |
| B5 | Backup | Failure analysis: which rule fired | block_reasons_heldout | 18 |
| B6 | Backup | Cost per episode | final_tables cost columns | 21 |
| B7 | Backup | Safety and ethics | unchanged + disclosure: the AI assistant saw the team-written attacks after the freeze and edited target-email names in 8 (no defense change after) | 22 |
| B8 | Backup | Live demo fallback | demo.py --oracle output for attack-g1-attachment-1-club (scripted agent that obeys the attack) | 18 (table slide) |

Dropped from the interim: 7 (three ways to defend: merged into 4), 10 (rerun), 11 (one real gap, one bug: now history), 13 (plan).
