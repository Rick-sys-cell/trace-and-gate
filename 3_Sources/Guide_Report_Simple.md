# Trace and Gate: the final report in simple terms

**Due: 12:00 PM Fri 6 Nov**, together with the slides and an email with the public GitHub link (course email, 3 Nov).

A plain-language guide to `3_Sources/Final_Report.md` (built as `4_Final_Submission/Final_Report.docx`, 9 pages) for Rui and Khadijah. Every number comes from `sandbox/results/final_tables.md`; `python tools/check_numbers.py` checks the report against the result files. The terms (prompt injection, provenance, policy, attack success, utility, confidence interval, McNemar, held-out, AgentDojo, CAMEL-AI vs CaMeL, SETA) are explained in the glossary of `Guide_Presentation_Simple.md`.

**Still to do before submission:**
- **Khadijah, by Thu 5 Nov:** review the one normal task that D1h blocked, `benign-control-travel-send` (Section VII-G), and replace `[PENDING: the authors' review of this task]` with one sentence: was the block reasonable, or a false alarm?
- **Then:**
  - rebuild with `python tools/build_report_docx.py 3_Sources/Final_Report.md 4_Final_Submission/Final_Report.docx`;
  - run `python tools/check_numbers.py`. It should report 0 PENDING, and only the 2 published figures from other papers (47.7% and 39.9%) as unmatched.

---

## 1. The report in one minute

An AI email assistant can be taken over by instructions hidden in an email. We put a **gate** of two plain-code checks between the AI and its actions:
- **D2:** is this action on the task's short list?
- **D1h:** did the user ask for it, and did the recipient and content come from the user?

We tested it in a locked Docker sandbox with a local model (Qwen3-8B):
- **Development set:** attacks worked 45.4% of the time with no defense, and 0% with any defense.
- **Held-out set** (new attacks, written after we froze the code), 3 runs: **21.8% → 0%**. Normal tasks: 89.3% → 91.7% with both checks.
- **The same held for:**
  - a second model (Qwen2.5-7B, 29.3% → 0%);
  - a second agent framework, CAMEL-AI (20.7% → 0%, normal tasks 89.3% everywhere).
- **AgentDojo,** a public benchmark: its attacks almost never worked on small local models, even when reframed as a test and tried on two other models. So it could only show that the defenses cost nothing (utility 27.5% → 30.0%).
- **The real cost:** D1h blocks harmless links copied out of emails (normal link tasks 88.3% → 40.0%). A contact-trusting variant, D1h-L, gets back to 55.0%.

---

## 2. Section by section

**Abstract.** The whole story in one paragraph, with the headline numbers above.

**I. Introduction.** Why email agents are risky; why we use fixed checks outside the model rather than detection; and four contributions:
- the evaluation;
- generalisation (second model, CAMEL-AI, AgentDojo);
- cost (failure analysis and links);
- scope (what we do not cover).

**II. Changes since the interim (Table I).** What we fixed after the interim pilot:
- D1h replaced D1;
- benchmark v3 makes the agent open the attack email;
- the defenses were frozen, then a held-out set was written;
- 3 runs, a second model, AgentDojo.

The last two rows are the 30 Oct consultation: the "test" framing plus two models for AgentDojo, and the CAMEL-AI agent.

**III. Research question and hypotheses.**
- **H1 (safety):** D1h+D2 cuts attack success by at least 80%.
- **H2 (usefulness):** normal tasks drop by at most 10 points.

Both are tested on the held-out set over 3 runs, with McNemar tests.

**IV. Threat model (Table II).** What we do *not* test: adaptive attackers, supply chain, a malicious user, memory poisoning, paraphrased leaks. Neither our benchmark nor AgentDojo covers them.

**V. System design.**
- **A. Sandbox:** the container and its 16 isolation checks; the demo script.
- **B. Defenses (Table III):** the five configurations, and what D1h and D2 check.
- **C. A second agent framework (new):**
  - how CAMEL-AI's agent replaces our loop, while the model, gateway, prompt and gate stay the same;
  - a unit test shows that both loops make the same decisions;
  - CAMEL-AI is *not* CaMeL.

**VI. Benchmarks.** The four test sets:
- the development suite (153 tasks);
- the held-out attacks (40 LLMail + 18 of ours; Claude fixed an email name in 8 of ours, disclosed);
- 40 normal tasks with links;
- AgentDojo workspace. This part now mentions the "test"-framed attack template, which Claude wrote and we disclose, and the two extra models.

**VII. Results.**

| Part | What it shows | Number to remember |
|---|---|---|
| A. Development (Table IV, Fig. 1) | Every defense stops every attack; no normal task lost | 45.4% → 0%; normal tasks 89.3% → 89.3% |
| B. Held-out (Table V, Figs. 2–3) | Same on new attacks, 3 runs; H1 and H2 met | 21.8% → 0%; normal tasks 89.3% → 91.7% (p = 0.289, no real difference) |
| C. Second model (Table VI, Fig. 4) | Same safety with Qwen2.5-7B; a weaker assistant overall | 29.3% → 0%; normal tasks 66.1% → 73.2% |
| D. Links (Table VII) | D1h blocks copying a link out of an email, even a harmless one; D1h-L fixes the contact case | 88.3% → 40.0% (D1h+D2); D1h-L 55.0% |
| E. AgentDojo (Tables VIII–X, Fig. 5) | Its attacks barely work on small models, so it shows cost, not protection | 2/160 with no defense; utility 27.5% → 30.0%; trial best 1/24 |
| F. CAMEL-AI (Table XI, Fig. 6), new | The same gate protects a different agent framework | 20.7% → 0%; normal tasks 89.3% everywhere |
| G. Failure analysis and cost | What was blocked in normal tasks, and the time and token cost | D1h: 3 of 168 normal episodes (one task); D2 uses 26% fewer tokens |

**VIII. Discussion.**
- What generalised.
- Two checks, two jobs: D2 removes the tools; D1h catches attacker content inside allowed actions.
- Against Dual-LLM: equally safe, but less useful (80.4% vs 91.7%).
- Links are the real cost.
- A second model.
- AgentDojo vs our suite.
- **A second agent framework (new).**
- **Future work (new):** adaptive attacks, a direct comparison with CaMeL, and the gate around terminal tools (SETA).
- Limitations: fixed attacks, small models, hand-written policies, exact-match scoring, held-out independence, and one CAMEL-AI run.

**IX. Conclusion.** The fixed gate works and costs no normal tasks, except for links. Test your rules on normal tasks, not only on attacks.

**AI Declaration.**
- **What Claude did:** wrote code to our specifications, including the AgentDojo bridge and the CAMEL-AI adapter; wrote the "test" AgentDojo template after the freeze; helped write. It also saw and name-edited 8 of our held-out attacks.
- **What it never did:** read attack payloads or transcripts, or choose the question, hypotheses or conclusions.

The declaration also lists every run ID.

**References.** 18 sources. New: [17] CAMEL (Li et al., NeurIPS 2023) and [18] SETA (Shen et al., arXiv 2026). [2] is CaMeL (Debenedetti et al., 2025).

---

## 3. The rules we fixed before running, and how they came out

| Rule (written in the tracker before the run) | Result |
|---|---|
| Defenses frozen 24 Oct before any held-out attack existed | Kept; a unit test pins the frozen source |
| AgentDojo trial 1 (26 Oct): second full run only if an attack reaches 3/24 | Best 1/24, so no rerun |
| AgentDojo trial 2 (2 Nov, after the consultation): 3 models × stock / "test" attack, rerun only if a cell reaches 3/24 | Every new cell 0/24, so no rerun |
| CAMEL-AI: claim protection only if CAMEL-AI with no defense follows ≥ 10% of LLMail attacks | 30% (12/40): met, so the claim stands |

---

## 4. Questions a marker might ask

1. **Your held-out team attacks never worked. Is the held-out result real?** It rests on the 40 LLMail attacks, which worked 31.7% of the time with no defense and never with one, over 3 runs. We say this plainly in VIII.
2. **Isn't 0% too good?** The agent still *tried* the attack many times under the defenses, and every try was blocked: 19/19 under D1h+D2 on the held-out set, and 12/12 under D1h with CAMEL-AI. The zero comes from the gate, not from a polite model.
3. **Why does D2 have fewer attempts than D1h?** D2 hides the tools a task does not need, so the agent often has nothing to attack with.
4. **Why is AgentDojo in the report if its attacks failed?** It is a benchmark we did not write, and the defenses ran on it unchanged, at no cost in utility. We say it cannot show protection, and why: the injection reached the model, and the model ignored it.
5. **Did you try to make AgentDojo work?** Yes, twice, both times with a bar fixed beforehand: three other built-in attacks, then a "test" framing on three models. None reached 3/24.
6. **What does CAMEL-AI add?** It shows that the gate is not tied to our agent code: a different framework, the same checks, the same result (20.7% → 0%).
7. **CAMEL-AI vs CaMeL?** CAMEL-AI is a framework for building agents. CaMeL is a defense (Google DeepMind). We ran the first; comparing against the second is future work.
8. **What is the main weakness?** Fixed attacks only. An attacker who knows our rules, for example by taking over a contact's account, is untested.
9. **What does the link result mean in practice?** If users often ask the agent to pass on links from emails, D1h is too strict. D1h-L trusts named contacts, which recovers the common case but is exactly what an attacker with a stolen contact account would exploit.
10. **How did AI help?** See the AI Declaration: code and drafting help. It was blocked from attack text and transcripts. It saw 8 held-out attacks (to fix an email name) and wrote the "test" AgentDojo template, both after the freeze and both disclosed.
