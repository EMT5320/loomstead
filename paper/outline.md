# Paper Outline

## Working Title

**Loomstead: Motivational Delegation for Process-Constrained Goals in Persistent Multi-Agent Narratives**

## Abstract sketch

Persistent multi-agent narratives often involve goals whose value lies in the path taken: friendships should grow through shared events, trust repair should depend on remembered harm and observed compensation, and festivals should succeed through visible social and resource processes. Loomstead studies motivational delegation, where a Director shapes conditions through motivation bias, opportunity scheduling, information exposure, event pressure, and constraints while autonomous NPC agents choose actions through their own motivation, memory, relationships, and heuristics. The system pairs a playable Godot town slice with a Python runtime, traceable tool execution, subjective memory, relationship edges, and Process Fidelity Eval. Current results provide rule-level evidence across process-constrained scenarios, hard-delegation and memory ablations, 24h / 72h stability runs, and a small cross-domain coding adapter.

## 1. Introduction

- Process-constrained goals in narrative worlds.
- Failure mode of direct state edits and hard task assignment.
- Loomstead as a narrative-primary research environment.
- Contributions:
  1. Motivational Delegation runtime pattern.
  2. Process Fidelity Eval metrics and baselines.
  3. Traceable subjective memory / relationship evidence chain.
  4. Playable town slice plus secondary coding adapter prototype.

## 2. Related Work

- Generative agents and believable social simulation: Generative Agents, Concordia.
- Multi-agent orchestration frameworks: AutoGen, MetaGPT, ChatDev.
- Agent evaluation, traceability, and process metrics: AgentBench plus pending trace-debugging literature.
- Interactive narrative and drama management: Roberts and Isbell survey plus later interactive narrative evaluation work.
- Game AI social simulation and memory systems: pending targeted search.

## 3. System Overview

- Godot client: participant view and observer panel.
- Python Agent Server: authoritative world state.
- Director / Event Skill: indirect intervention layer.
- NPC agent loop: needs, capability filtering, arbitration, tool execution.
- Memory layer: objective events, subjective memories, relationship edges, heuristics.
- Debug trace and schema registry.
- Current draft includes Figure 1 source in `paper/diagrams/system_overview.mmd`.

## 4. Motivational Delegation

- Process-constrained GoalSpec.
- Allowed interventions.
- Intervention lifecycle: proposed, applied, observed, evaluated, expired.
- Autonomy boundary: final action selected by ArbitrationLayer.
- Example trace: close friend or repair trust scenario.
- Current draft includes Figure 2 source in `paper/diagrams/motivational_delegation_loop.mmd`.

## 5. Process Fidelity Eval

- Metric families.
- Baselines: Full, Hard Delegation, No Subjective Memory, No Relationship Edge, Shuffled Memory Owner, Evidence-Link Removal.
- Counterfactual replay and evidence-link checks.
- Dataset export and manifest validation.

## 6. Experiments

### 6.1 Process Fidelity Scenarios

- Shared chat builds traceable trust.
- Repair talk requires memory trace.
- Affiliation bias remains agent initiated.

### 6.2 Stability

- 24h and 72h rule-level stability.
- Tool completion, interruption, memory observation, heuristic references.

### 6.3 Cross-domain Adapter

- Narrative town scenarios.
- Coding fixture scenarios with patch / test / review evidence.

### 6.4 Current Evidence Boundary

- Rule-level and posterior ablation results.
- Need for more seeds, LLM-backed runs, human believability ratings, and real observer-mode validation.

### 6.5 Related-work positioning table

- Generative Agents / Concordia: believable autonomous social simulation and generative agent-based modeling.
- Drama Management: authorial control versus autonomy in interactive narrative.
- AutoGen / MetaGPT / ChatDev: explicit role, conversation, and workflow orchestration.
- AgentBench: interactive evaluation for LLM agents.
- Loomstead: process-constrained narrative goals evaluated through shortcut, autonomy, memory-causality, and trace-coverage metrics.

## 7. Discussion

- Why process fidelity matters for narrative goals.
- What relationship memory contributes.
- How traceability changes debugging and evaluation.
- Portability and limits of the adapter abstraction.

## 8. Limitations

- Thin content layer and limited Event Skills.
- Hard Delegation baseline still synthetic.
- LLM evidence not yet part of the routine eval table.
- Small sample size.
- Human believability scoring pending.

## 9. Conclusion

- Loomstead frames goal-conditioned narrative orchestration as motivational delegation.
- Process Fidelity Eval turns believable process into measurable evidence.
- Next step: expand seeds, real LLM runs, human ratings, and stronger baselines.
