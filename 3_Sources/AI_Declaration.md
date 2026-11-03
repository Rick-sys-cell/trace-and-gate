<!--
AI declaration, copied from the final report (3_Sources/Final_Report.md, section before References) on 3 Nov.
The interim version is in Interim_Report.md. If the report's declaration changes, copy it here again.
-->

# AI Declaration

We used Claude (Anthropic), through the Claude Code assistant, as a tool during this project. It was not a source of results, data or citations.

- *Code.* It wrote code to our specifications: the sandbox, the defenses (D1h, D2, B1 and the exploratory D1h-L), the benchmark builders, the AgentDojo bridge, the CAMEL-AI adapter, and the evaluation, analysis, figure and document-build scripts. After the freeze it also wrote, to our specification, the AgentDojo attack template that frames the injection as a test (Section VI-D); that template is not part of the held-out set. We chose the design, the rules each defense enforces, and the hypotheses. We reviewed the code. It passed the offline unit tests and oracle replays before any run.
- *Writing.* It helped draft and edit this report and the slides, and summarised the analysis files into text and tables.
- *Not used for.* Choosing the research question, hypotheses or conclusions; producing data; or writing held-out attacks. The authors wrote all 18; after the freeze, at our request, the assistant replaced the target email's name in 8 of them that named emails missing from their inbox, and so saw their text. Every result comes from runs of the models under test (Qwen3-8B, Qwen2.5-7B) in our own sandbox; those models are separate from the assistant. The assistant was blocked from reading attack payloads and raw transcripts.

We checked every number in this report against the result file of the run it cites (development 20261024-135826; held-out 20261025-034455; Qwen2.5-7B 20261025-071911; benign links 20261025-055650; D1h-L 20261025-064154 and 20261025-070311; AgentDojo agentdojo_20261025-075616 and the attack trials agentdojo_20261026-040133, -041145, -042258 and -043112, and agentdojo_20261102-143641, -145250, -150020, -150758 and -151307; CAMEL-AI 20261102-151939). We also checked every citation against its source. We take full responsibility for the content of this report.
