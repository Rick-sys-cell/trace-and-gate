# Interim Report: Source Verification

Checked 8 Oct 2026 against the primary sources. Each row gives a claim made in `Interim_Report.md` about outside work, the source, and the passage that supports it. Our own numbers are checked separately against `figures/pilot_analysis_20261006-100417.json` and `figures/recheck_b1_subject_20261008-094725.json`.

| Report claim | Ref | Source | Supporting passage |
|---|---|---|---|
| Prompt injection is the top risk for LLM applications | [15] | [OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | Listed as "LLM01:2025 Prompt Injection", first in the OWASP Top 10 for LLM Applications |
| Challenge led by Microsoft with partners; over 200,000 attack emails against an email assistant | [11] | [arXiv:2506.09956](https://arxiv.org/html/2506.09956v1) | "208,095 unique prompts"; primary organisers from Microsoft, with Trend Micro, ISTA, HiddenLayer and others; an IEEE SaTML 2025 competition |
| LLMail-Inject attacks aim to send an email to contact@contact.com | [11] | [arXiv:2506.09956](https://arxiv.org/html/2506.09956v1); dataset `scenarios.json` | "destination=contact@contact.com, content=confirmation" |
| Our 40 emails come from 21 of the 24 Phase 2 sub-levels | [11] | [arXiv:2506.09956](https://arxiv.org/html/2506.09956v1); our `import_llmail.py` output | "Phase 2 consisted of 24 sub-levels"; our successful samples covered 21 |
| Email-borne attacks still work against current agents | [14] | [arXiv:2605.17986](https://arxiv.org/abs/2605.17986) | "total attack success rates range from 10.7% to 29.6%" across five frontier backbones |
| MELON re-runs the agent with the user request masked and compares actions | [12] | [arXiv:2502.05174](https://arxiv.org/abs/2502.05174) | "re-executing the agent's trajectory with a masked user prompt … an attack if the actions … are similar" |
| Adaptive attacks broke all eight defenses tested | [16] | [arXiv:2503.00061](https://arxiv.org/abs/2503.00061) | "we evaluate eight different defenses and bypass all of them using adaptive attacks" |
| Dual-LLM: privileged and quarantined models, `$VAR` variables; Apr 2023 | [1] | [Willison, 25 Apr 2023](https://simonwillison.net/2023/Apr/25/dual-llm-pattern/) | Privileged LLM has tools; quarantined LLM "does not have access to tools"; `$VAR1` placeholders |
| Dual-LLM's known weakness is data flow into tool arguments | [2] | [arXiv:2503.18813](https://arxiv.org/html/2503.18813) | "even if the global plan itself is not hijacked, the data being processed according to the plan is manipulated" (attacker-chosen recipient example) |
| Dual-LLM is one of several design patterns | [10] | [arXiv:2506.08837](https://arxiv.org/html/2506.08837) | Six patterns; "The Dual LLM Pattern" is one of them |
| D1 follows FIDES: labels plus deterministic policy | [4] | [arXiv:2505.23643](https://arxiv.org/abs/2505.23643) | "a planner that tracks confidentiality and integrity labels, deterministically enforces security policies" |
| D1 follows PACT: argument-level provenance | [6] | [arXiv:2605.11039](https://arxiv.org/abs/2605.11039) | Injection "becomes dangerous … when it determines an authority-bearing argument" |
| D2 follows Progent: rules over tools and arguments | [5] | [arXiv:2504.11703](https://arxiv.org/abs/2504.11703) | "symbolic rules over tool names and arguments … checked against such a policy through a deterministic procedure" |
| D2's recipient rule follows ROPE | [7] | [arXiv:2608.27496](https://arxiv.org/abs/2608.27496) | "a value may reach a state-changing tool only if it traces unforgeably to the user, a source the user explicitly named, or the user's own authoritative records" |
| CaMeL's guarantees fail across agents (multi-agent, not multi-turn) | [8] | [arXiv:2610.05640](https://arxiv.org/abs/2610.05640) | "CaMeL's guarantees do not compose" in "hierarchical multi-agent systems" |
| AgentDojo scores tasks by code on the environment state; NeurIPS 2024 D&B | [3] | [arXiv:2406.13352](https://arxiv.org/html/2406.13352); [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) | "The utility function is implemented as a deterministic binary function … the state of the environment before and after execution" |
| Progent on a 7B model: task success 45% → 27% | [9] | [arXiv:2606.26479](https://arxiv.org/html/2606.26479v1) | Qwen2.5-7B-Instruct; undefended utility 45.2%, Progent 27.1%; ASR 25.8% → 4.2% |
| MUSE: multi-turn attacks found by tree search | [13] | [arXiv:2509.14651](https://arxiv.org/abs/2509.14651) | MUSE-A "uses frame semantics and heuristic tree search"; EMNLP 2025 |
| Course brief recommends provenance tracking and policy checks | – | `Main Projects_11th September2026.pdf`, Project 8 | "Does implementing instruction provenance tracking and policy-check verification significantly reduce unauthorized tool execution…" |

## Bibliographic details confirmed
| Ref | Confirmed |
|---|---|
| [2] | Debenedetti, Shumailov, Fan, Hayes, Carlini, Fabian, Kern, Shi, Terzis, Tramèr; 24 Mar 2025 |
| [3] | Debenedetti, Zhang, Balunović, Beurer-Kellner, Fischer, Tramèr; NeurIPS 2024 D&B |
| [6] | Fan, Li, Tian, Wang, Li, Wang; 11 May 2026 |
| [9] | Narisetty, Kore, Kattamanchi, Kumarapu; 25 Jun 2026 |
| [10] | Beurer-Kellner et al. (14 authors); 10 Jun 2025 |
| [12] | Zhu, Yang, Wang, Guo, Wang; ICML 2025 |
| [13] | Yan et al. (9 authors); EMNLP 2025 main |
| [14] | Zhao, Bhaskar, Dobriban; 18 May 2026 |
| [16] | Zhan, Fang, Panchal, Kang; Findings of NAACL 2025 |
