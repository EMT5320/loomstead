# Trace, Provenance, and Attribution Seed Notes

This note captures the second related-work seed pass. It is intentionally
skeletal: each entry records why the paper is useful for Loomstead and what must
be checked during a later full skim before the paper text makes strong claims.

## Intake posture

- Use these papers to support the Process Fidelity Eval and evidence-discipline
  parts of the paper.
- Keep `AgentRx` and `LongFact / SAFE` as candidate references until PDF-level
  notes confirm the exact metric, dataset, and limitation wording.
- Keep Zotero keys empty in `reading_queue.md` until the Zotero import pass
  assigns stable Better BibTeX citekeys.

## Buckets

| Bucket | Seed references | Use in Loomstead | Follow-up skim questions |
| --- | --- | --- | --- |
| Action-observation traces | ReAct (`yao2023react`) | Anchor for interleaving reasoning traces, environment actions, and observations. Helps explain why a Loomstead trace should expose motive, action, event result, and memory uptake as one process. | Which trajectory examples are most relevant for narrative simulation? How does the paper discuss interpretability limits? |
| Tool-agent risk evaluation | ToolEmu (`ruan2024toolemu`) | Anchor for scalable agent failure probing through an emulated sandbox and automatic evaluator. Useful contrast for Loomstead safety, shortcut, and invalid-intervention checks. | Which parts of ToolEmu's sandbox design map to a game-world simulator? Which risk categories transfer cleanly to narrative agents? |
| Trajectory diagnosis | AgentRx (`barke2026agentrx`) | Candidate for critical-failure-step localization and auditable validation logs. This is close to Process Fidelity Eval's future failure-attribution story. | What is the released trajectory schema? Can Loomstead export a compatible minimal trace? Which taxonomy categories match motivational delegation? |
| Factual support | FActScore (`min2023factscore`) and LongFact / SAFE (`wei2024longfact`) | Provide atomic-fact decomposition and support-check patterns. Useful for paper-claim auditing and possible trace factuality checks over event logs. | Which automated evaluator assumptions depend on web search? Which parts can be adapted to closed-world simulation logs? |
| Citation and attribution | ALCE (`gao2023alce`) and AIS (`rashkin2023ais`) | Provide citation-quality and source-attribution language for linking generated statements to identifiable evidence. Useful for both Related Work and future trace provenance UI. | Which metrics are lightweight enough for an internal research console? How should the paper separate external-source attribution from internal-event attribution? |

## Current prose hooks

- Related Work can say that existing agent frameworks and benchmarks often expose
  final task success and some execution traces; Loomstead's planned emphasis is
  motive-conditioned process evidence in a narrative simulation.
- Process Fidelity Eval can reuse three vocabulary groups:
  - trajectory step localization from AgentRx;
  - tool-risk and emulated-sandbox probing from ToolEmu;
  - source attribution / factual support from AIS, ALCE, FActScore, and SAFE.
- The first paper draft should still avoid numeric claims from these papers
  unless the exact source line is cited in the local notes.

## Immediate next actions

1. Import this batch into Zotero with PDF links where available.
2. Fill `Zotero Key` in `reading_queue.md`.
3. Add one-page PDF skim notes for ReAct and ToolEmu first.
4. Convert confirmed hooks into a short Related Work subsection only after the
   skim notes are present.
