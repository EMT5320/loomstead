# Loomstead: Building an Agent Behavior Observatory

`Loomstead` is a portfolio engineering project about **observability for complex agents**. It uses a playable Godot town as the surface, while the main system value lives in the backend runtime, trace schema, debug panels, eval exports, and audit artifacts.

The final story is straightforward:

```text
How do we debug, trace, and evaluate autonomous agents when their behavior depends on motivation, memory, relationships, tools, and LLM decisions?
```

Loomstead answers by building a compact, complete agent behavior observatory.

## 1. Why a town?

A town gives agent behavior enough structure to be interesting:

- NPCs have social relationships.
- Events create pressure and opportunities.
- Memories influence later choices.
- Tools change world state.
- The same final outcome can come from very different paths.

The town is the readable surface. The project highlights the infrastructure around that surface: runtime boundaries, traceable decisions, and artifacts that explain behavior after the fact.

## 2. Runtime architecture

The backend owns authoritative world state. Godot presents the world and sends legal player actions. Phase 2 agent decisions flow through:

```text
MotivationEngine -> ToolExecutor -> ResultObserver
```

The runtime includes:

- Director / Event Skill pressure for world-level pacing.
- NPC motivation and capability-aware tool arbitration.
- Subjective memory and relationship-edge stores.
- Heuristic seeds and later score influence.
- Tool execution, rollback, interruption, and result observation.
- OpenAI-compatible cloud provider integration with fallback and usage accounting.

This makes Loomstead more useful as a systems project than as a pure game demo: the interesting surface is how agent behavior is represented, constrained, executed, and inspected.

## 3. Observability as a first-class design goal

Agent systems become hard to debug when the only visible output is the final action. Loomstead records structured evidence while decisions are made.

Key fields:

- `sourceEventIds`: what prior event or evidence influenced this decision.
- `traceRefs`: how to jump from a result back to the decision or evidence span.
- `candidateScores`: what the agent considered.
- `scoreComponentSourceRefs`: which evidence affected each score component.
- `phase2.trace.v1`: the common trace envelope for decision, tool, budget, interruption, and memory events.

The intended debugging question is:

```text
Why did this agent choose this action, and what evidence influenced it?
```

## 4. Case card A: why did an NPC act?

The Figure 3 walkthrough shows a behavior chain around subjective memory and relationship evidence:

```text
paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md
```

The story is a compact trace:

1. a seeded relationship or memory condition,
2. a later tool decision,
3. a result-observation bridge,
4. memory / relationship updates,
5. a later decision that references those records,
6. counterfactual replay that changes selection when evidence is removed.

The showcase value is the runtime's ability to expose the behavior path and make it inspectable.

## 5. Case card B: what changed when evidence was removed?

The eval layer produces artifacts for process checks, ablations, domain adapters, robustness checks, and counterfactual replay. The strongest way to present those artifacts is a simple before/after story:

```text
Full evidence -> selected action / score components
Removed evidence -> changed score, selected tool, or verdict
```

Metrics remain useful as a verification index. The case card leads the presentation.

Useful commands:

```powershell
npm.cmd run eval:process
npm.cmd run eval:domain
npm.cmd run eval:robustness
npm.cmd run eval:archive:check
```

## 6. Case card C: why was a high-risk tool call blocked?

The final audit spike is retained as a failure-analysis artifact.

Useful artifacts:

```text
.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z
.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z
```

The audit supplement compares five high-risk tool scenarios under two evidence conditions:

```text
Full Runtime          -> high-risk tool allowed with complete required evidence
No Policy Evidence    -> safe review tool selected because required evidence is missing
```

Latest real provider smoke:

- 5 scenarios x 2 evidence conditions.
- 10/10 cases passed.
- 18,348 tokens / 0.00351806 USD.
- Missing-evidence cases routed to safe review tools.

This supports a bounded engineering point: trace-grounded audit contracts can produce readable failure-analysis artifacts for high-risk tool calls. Broad AI safety and enterprise readiness remain out of scope.

## 7. Design evolution and honest scoping

The original research framing around Motivational Delegation and Process Fidelity revealed that the most deliverable engineering contribution was the observability stack built around agent behavior: structured traces, evidence links, counterfactual replay, eval exports, and audit harnesses. The project now centers those assets. Stronger behavioral claims remain out of scope; the evidence supports explainability, metric-level guardrails, and failure-analysis storytelling.

Retained assets:

- Runtime architecture.
- Trace schema and debug surfaces.
- Eval/export/archive pipeline.
- Counterfactual replay.
- Audit harness and reviewer packets.
- Godot town as a concrete live surface.

Dropped or frozen directions:

- human-validated believability,
- broad Process Fidelity research claims,
- large human review workload,
- further Godot UI polish for metrics presentation,
- new research experiments inside Loomstead.

## 8. Current portfolio takeaway

The strongest concise claim is:

> Loomstead is a full-stack agent behavior observatory: a playable multi-agent runtime with structured traces, evidence-linked decisions, eval exports, and audit artifacts for debugging complex agent behavior.

This is an engineering showcase. It demonstrates how to build, instrument, evaluate, and honestly scope a complex agent system.

## 9. Local demo path

```powershell
npm.cmd run context:resume
npm.cmd run check
npm.cmd run client:env
npm.cmd run start
npm.cmd run client:run
```

Recommended demonstration order:

1. Show the town surface.
2. Open Observer Dock or Debug data.
3. Explain one agent decision with source evidence.
4. Open one case card from `docs/portfolio_story.md`.
5. Close with the audit supplement as the failure-analysis example.

## 10. Honest boundary

Loomstead is frozen as a portfolio project. The final story emphasizes agent observability and eval engineering. Stronger research work should move to a cleaner project with a simpler claim and a lower reviewer-comprehension burden.
