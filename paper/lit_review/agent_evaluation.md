# Agent Evaluation and Traceability

## Why this bucket matters

Process Fidelity Eval must connect to broader agent evaluation while emphasizing a different target: believable process under constraints plus final task success.

## Selected sources

| Source | What to cite | Contrast for Loomstead |
| --- | --- | --- |
| AgentBench | Multi-dimensional benchmark over interactive environments for LLM-as-agent reasoning and decision-making. | AgentBench motivates interactive evaluation; Loomstead adds process constraints, shortcut checks, autonomy metrics, memory causality, and trace evidence for narrative goals. |
| ReAct | Interleaved reasoning traces, actions, and observations in decision-making tasks. | ReAct motivates readable action-observation trajectories; Loomstead extends the trace target toward motives, social context, event consequences, and memory uptake. |
| ToolEmu | LM-emulated sandbox and automatic safety evaluator for tool-agent risk analysis. | ToolEmu supports scalable probing of unsafe or invalid agent behavior; Loomstead can adapt the idea to narrative-world constraints and intervention validity. |
| AgentRx | Failed trajectory benchmark with critical failure-step labels and auditable validation logs. | AgentRx is a candidate anchor for future Process Fidelity Eval failure localization once Loomstead exports richer trajectory traces. |

## Notes to turn into prose

- AgentBench can anchor the need for interactive environments instead of static QA tasks.
- Loomstead's metrics should be presented as complementary: they check whether a social process was earned and explainable.
- ReAct, ToolEmu, and AgentRx cover the first pass of trace / trajectory / sandbox evaluation. They still need PDF-level skim notes before the final related-work prose uses detailed claims.

## Citation keys

- `liu2024agentbench`
- `yao2023react`
- `ruan2024toolemu`
- `barke2026agentrx`

## Open literature search tasks

- Search human believability scoring protocols for interactive narrative and social simulation.
- Add PDF skim notes for ReAct, ToolEmu, and AgentRx.
