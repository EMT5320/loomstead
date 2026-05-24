# Prior Related Work Inventory

This file records related-work material already found on this machine before the Loomstead literature review grows further. It is a routing index, not a source of final claims.

## Summary

Loomstead already has three useful reservoirs:

1. Current Loomstead seed set under `paper/lit_review/`.
2. AlgoCoach-Flywheel / PromptGym-Code paper workspace under `D:\WorkSpace\leetcode_agent\paper\lit_review\`.
3. SecAbstainBench related-work matrices under `D:\WorkSpace\research\SecAbstainBench\`.

Use these as source-discovery and contrast-pattern material. Re-check every source before citing it in the Loomstead draft.

## Reservoir A: Loomstead seed set

Local paths:

- `paper/lit_review/source_index.md`
- `paper/lit_review/reading_queue.md`
- `paper/lit_review/generative_agents.md`
- `paper/lit_review/multi_agent_orchestration.md`
- `paper/lit_review/agent_evaluation.md`
- `paper/lit_review/narrative_simulation.md`

Current strongest reusable sources:

| Bucket | Existing seed | Use in Loomstead |
| --- | --- | --- |
| Believable generative agents | Generative Agents, Concordia | Closest social-simulation and generative-agent environment anchors. |
| Drama management | Roberts and Isbell survey | Authorial control / autonomy history for Director boundaries. |
| Task multi-agent orchestration | AutoGen, MetaGPT, ChatDev | Contrast with explicit workflow decomposition and hard delegation. |
| Agent evaluation | AgentBench | Broad interactive-agent benchmark anchor. |

## Reservoir B: AlgoCoach-Flywheel paper workspace

Local paths:

- `D:\WorkSpace\leetcode_agent\paper\lit_review\related_work_matrix.md`
- `D:\WorkSpace\leetcode_agent\paper\lit_review\reading_queue.md`
- `D:\WorkSpace\leetcode_agent\paper\lit_review\intake_report_2026-05-24.md`
- `D:\WorkSpace\leetcode_agent\paper\latex\sections\06_related_work.tex`
- `D:\WorkSpace\leetcode_agent\docs\RELATED_WORK_DIFFERENTIATOR.md`

Already imported there:

| Bucket | Examples | Direct reuse for Loomstead |
| --- | --- | --- |
| LLM tutoring benchmarks | TutorBench, PEBBLE, MathDial, MathChat | Mostly background only; useful as an example of conservative benchmark positioning. |
| Code process reward / verifier work | CodePRM, FunPRM, property-feedback, Code2Bench | Secondary-domain/coding-adapter context only. |
| Self-play / reward loops | Self-Rewarding LMs, SPIN, Absolute Zero | Useful if Loomstead later discusses data flywheels or synthetic-verifiable training. |
| Student simulation | LLM-based role-playing student agents, ITS feedback | Conceptually adjacent to NPC simulation, but education-domain claims should stay separate. |

Most useful transferable artifact:

- The matrix style: `Area -> Paper/System -> Core Idea -> Difference -> Citation Key -> Status`.
- The discipline of keeping `imported; needs skim` separate from `anchored`.
- The Zotero intake report format with Zotero key + BibTeX key + source URL.

## Reservoir C: SecAbstainBench matrices

Local paths:

- `D:\WorkSpace\research\SecAbstainBench\docs\literature_matrix.md`
- `D:\WorkSpace\research\SecAbstainBench\paper\sections\02_related_work.md`
- `D:\WorkSpace\research\SecAbstainBench-worktrees\a-related-work-20260516\docs\literature_matrix.md`

Potentially reusable source buckets:

| Bucket | Examples | Use in Loomstead |
| --- | --- | --- |
| Tool-using agent reliability | ToolEmu, ReAct, AgentRx | Useful for trace / tool failure / trajectory diagnostics. |
| Claim attribution and evidence support | FActScore, SAFE / LongFact, ALCE, AIS | Useful for Process Fidelity trace-support and evidence-link evaluation. |
| Abstention / selective prediction | AbstentionBench, selective prediction | Only relevant if Loomstead adds "insufficient process evidence" refusal or uncertainty framing. |
| Provenance-aware agent auditing | ARGUS / AgentLure, DFAH | Useful for provenance and trace faithfulness framing, not central narrative claims. |

Transferable pattern:

- Adjacent-work comparison matrix using: primary evaluation unit, main decision target, typical failure focus, and role in the paper.
- Collision-avoidance guardrails that keep the claim surface narrow.

## Recommended import order for Loomstead

1. Finish Zotero import for the seven existing Loomstead seed papers.
2. Add a second batch for trace / trajectory / provenance:
   - ReAct
   - ToolEmu
   - AgentRx
   - FActScore
   - SAFE / LongFact
   - ALCE or AIS
3. Add a third batch for human believability and interactive narrative evaluation.
4. Pull only narrow ideas from AlgoCoach and SecAbstainBench:
   - matrix structure,
   - Zotero key tracking,
   - status discipline,
   - collision guardrails.

## Current caution

The AlgoCoach and SecAbstainBench papers target different domains. Their source lists should not be copied into Loomstead wholesale. Treat them as search seeds and workflow templates, then verify relevance against Loomstead's primary frame: motivational delegation and process fidelity in persistent multi-agent narratives.
