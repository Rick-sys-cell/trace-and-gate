<!--
Reusable AI declaration. Interim version is in Interim_Report.md (section before References).
For the final report (Week 12): update the run IDs in the last paragraph, add any new runs
(e.g. AgentDojo, Qwen2.5-7B), and re-check every claim below is still true.
Markup matches build_ieee_docx.py ("# " heading, "- *Lead.* text" bullets).
-->

# AI Declaration

We used Claude (Anthropic), through the Claude Code assistant, as a tool during this project. It was not a source of results, data or citations.

- *Code.* It wrote code to our specifications: the sandbox, the defenses (D1, D2, B1), the benchmark builder, and the evaluation, analysis and figure scripts. We chose the design, the rules each defense enforces, and the hypotheses. We reviewed the code. It passed the offline unit tests and an oracle replay before any run.
- *Writing.* It helped draft and edit this report and the slides, and summarised the analysis files into text and tables.
- *Not used for.* Choosing the research question, hypotheses or conclusions, or producing data. Every result comes from runs of Qwen3-8B, the model under test, in our own sandbox; that model is separate from the assistant. The assistant was blocked from reading attack payloads and raw transcripts.

We checked every number in this report against the analysis and diagnostics files of the run it cites (pilot 20261006-100417, B1 recheck 20261008-094725, rerun 20261008-103942). We also checked every citation against its source paper. This checking found the B1 bug described in Section VII-A. We take full responsibility for the content of this report.
