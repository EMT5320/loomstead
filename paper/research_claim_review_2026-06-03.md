# Research Claim Review: 2026-06-03

## Scope

- Claims reviewed: pivot from human believability / Process Fidelity to AI Safety & Auditable Agents.
- Trigger: follow-up discussion after the 2026-06-02 strategic shrink and Gemini proposal to emphasize `sourceEventIds` / causal trace / auditability.
- Owner decision captured here: finish Loomstead first as a fallback engineering portfolio project, then run one short rescue spike. If the spike does not create stronger evidence, stop further research investment.
- Evidence level: planning snapshot only. This file does not upgrade any claim level.

## Current Verdict

The Auditable Agents direction is the most plausible rescue route because it aligns with Loomstead's actual assets: structured trace, source-linked arbitration, promoted eval artifacts, counterfactual replay, and the coding-domain adapter.

The safe research shape is:

> Loomstead provides a trace-grounded action provenance and counterfactual audit harness for toy agent workflows.

The unsafe shape is:

- Claiming complete causal proof for every agent action.
- Claiming enterprise production readiness.
- Claiming cross-domain validity from the current town / coding fixtures.
- Rebranding the old Process Fidelity suite as AI Safety evidence without new audit scenarios and artifacts.

## External Context

Relevant external signals as of 2026-06-03:

- NIST AI Agent Standards Initiative focuses on secure and interoperable agentic systems, including agent authentication and identity infrastructure: <https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative>.
- NIST NCCoE concept paper for Software and AI Agent Identity and Authorization explicitly raises tamper-proof / verifiable logging, intent logging, non-repudiation, and human authorization binding: <https://www.nccoe.nist.gov/sites/default/files/2026-02/accelerating-the-adoption-of-software-and-ai-agent-identity-and-authorization-concept-paper.pdf>.
- EU AI Act Regulation 2024/1689 Article 12 requires high-risk AI systems to technically allow automatic event recording over the system lifetime and support traceability appropriate to the intended purpose: <https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng>.
- AgentTrace frames deployed multi-agent systems around causal graph tracing for root-cause analysis: <https://arxiv.org/abs/2603.14688>.
- Counterfactual Trace Auditing of LLM Agent Skills shows that trace-level counterfactual audit can reveal behavior changes that aggregate pass rate misses: <https://arxiv.org/abs/2605.11946>.
- TraceSIR explores structured analysis and reporting of agentic execution traces: <https://arxiv.org/abs/2603.00623>.

## Mapping From Loomstead Assets

| Existing Loomstead asset | Audit interpretation | Current limitation |
| --- | --- | --- |
| `sourceEventIds` / `traceRefs` | Action provenance links | Shows structured citation; causal proof still needs counterfactual evidence |
| `candidateScores` | Decision-time arbitration surface | Needs policy-specific score components for audit scenarios |
| `scoreComponentSourceRefs` / `scoreExplanationRefs` | Evidence-to-score trace | Needs clearer false-positive / false-negative accounting |
| Counterfactual replay | Causal sensitivity test | Current promoted narrative ablations often do not change `goalToolEvents` |
| Coding domain adapter | Non-narrative domain seed | Current fixtures are contract-level, not high-risk audit tasks |
| Promoted manifests / provider usage | Reproducible artifact trail | Does not provide tamper-evident append-only logs |

## Metric Reframe

| Old metric / concept | Safer audit metric name | Notes |
| --- | --- | --- |
| `causal_trace_coverage` | `action_provenance_coverage` | Valid if denominator is high-risk actions / state changes |
| `shortcut_violation_rate` | `policy_bypass_rate` | Strong fit for SOP and guardrail bypass scenarios |
| `intervention_overreach_rate` | `unauthorized_intervention_rate` | Useful when agent authority and approval gates are explicit |
| `relationship_memory_causal_use_rate` | `decision_evidence_influence_rate` | Requires redesigned denominator; current metric does not equal precision |
| `counterfactual_tool_selection_change_rate` | `counterfactual_action_sensitivity` | Strongest rescue metric, but needs scenarios where key evidence changes behavior |

## Short Rescue Spike Plan

Recommended duration: 3-5 days after portfolio fallback closeout.

### Goal

Build a small `audit` suite that tests whether Loomstead can produce reviewer-readable provenance and counterfactual audit reports for high-risk tool actions.

### Non-goals

- No human believability claim.
- No enterprise compliance claim.
- No broad AI Safety claim.
- No cloud rerun unless a specific audit question requires it and the owner approves cost / keys.

### Minimal scenarios

1. Coding patch scenario: agent must read policy / issue / tests before patching; direct patching counts as policy bypass.
2. Ops file-change scenario: destructive file operation requires ticket / approval / source context.
3. Data export scenario: export requires redaction policy evidence before tool execution.

### Baselines

- Full Runtime.
- No Policy Evidence.
- Evidence Link Removal.
- Shortcut Agent.
- Direct Executor.

### Required artifact

Each action should emit an audit report with:

- selected tool and risk level;
- required policy evidence;
- actual `sourceEventIds` / `traceRefs`;
- score components and source refs;
- policy check verdict;
- counterfactual replay result;
- human-readable audit summary.

### Go / No-Go criteria

Continue only if the spike demonstrates:

- high-risk actions carry complete provenance in the toy suite;
- shortcut / direct baselines show higher bypass rates than Full;
- removing key policy / context evidence changes selected action or violation verdict in at least two scenarios;
- a reviewer can use the generated report to identify which evidence influenced the action and where responsibility should be assigned.

If these criteria fail, Loomstead remains a portfolio engineering project and the research rescue route closes.

## Recommended Wording

Safe wording:

> Loomstead includes a trace-grounded audit harness that records structured provenance for agent actions and tests selected counterfactuals in toy narrative and coding fixtures.

中文口径：

> Loomstead 展示了一个结构化 Agent 行为溯源与反事实审计 harness，可在 toy narrative / coding 场景中检查动作是否有证据链、是否绕过规则、关键上下文移除后决策是否变化。

Avoid wording:

- 完全严密的因果审查。
- 精准证明任何动作背后的真实原因。
- 企业级 Agent 审计生产可用。
- 双域指标有效性已经成立。
- AI Safety 前沿核心贡献已完成。
