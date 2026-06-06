# Loomstead

![Status: portfolio freeze](https://img.shields.io/badge/status-portfolio_freeze-6f42c1)
![Focus: agent observability](https://img.shields.io/badge/focus-agent_observability-0366d6)
![Surface: Godot town runtime](https://img.shields.io/badge/surface-Godot_town_runtime-22863a)

> **An observability-first multi-agent runtime for tracing, debugging, and auditing autonomous behavior in a simulated town.**

`Loomstead` uses a playable Godot town as a concrete surface for complex agent behavior. The project showcases how a multi-agent runtime can make NPC motivation, subjective memory, relationship state, tool execution, LLM decisions, and eval artifacts traceable end-to-end.

The final portfolio framing is **Agent Behavior Observatory**:

```text
Debugging, tracing, and evaluating autonomous agents in a simulated town.
```

The town is the interaction surface. The engineering story is the observability stack behind it: decision traces, evidence links, counterfactual replay, audit packets, and reproducible eval exports.

## 30-second portfolio path

1. **Read the portfolio story**: [docs/portfolio_story.md](docs/portfolio_story.md) explains the final positioning and the three showcase cards.
2. **Open the capability map**: [docs/portfolio_capability_map.md](docs/portfolio_capability_map.md) maps runtime / observability / eval / audit assets to interview talking points.
3. **Inspect one trace story**: [paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md](paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md) shows a concrete memory -> relationship -> decision chain.
4. **Inspect one failure-analysis story**: [.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/README.md](.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/README.md) shows high-risk tool calls under full vs missing policy evidence.

## What this project demonstrates

### 1. Agent runtime architecture

The active Phase 2 decision path is:

```text
MotivationEngine -> ToolExecutor -> ResultObserver
```

The runtime includes:

- Director / Event Skill pressure for world-level pacing.
- NPC motivation, capability preferences, and legal tool arbitration.
- Subjective memory and relationship-edge stores.
- Heuristic seeds and later decision influence.
- Authoritative Python Agent Server with Godot as the presentation layer.

### 2. Behavior observability

Loomstead records structured evidence while decisions are made:

- `phase2.trace.v1` for decisions, tool results, interruptions, memory observations, and budget events.
- `sourceEventIds` and `traceRefs` for evidence provenance.
- `candidateScores`, `scoreComponentSourceRefs`, and `scoreExplanationRefs` for arbitration inspection.
- Godot Observer Dock and Web Debug surfaces for local inspection.

The showcase question is simple:

```text
Why did this agent choose this action, and what evidence influenced it?
```

### 3. Eval and artifact pipeline

The project includes a reproducible eval/export stack:

- Process Fidelity checks for path-quality metrics.
- Stability, determinism, domain-adapter, and robustness suites.
- Manifest-backed exports, promoted artifacts, drift notes, and archive checks.
- Coding-domain adapter fixtures with dependency evidence chains.

Current research-grade claims remain intentionally limited. The Process Fidelity evidence supports metric / explainability-level statements only.

### 4. Failure analysis and audit harness

The final rescue spike is retained as an engineering artifact example:

- 5 high-risk non-narrative audit scenarios.
- Full / No Policy Evidence / Evidence Link Removal / Shortcut Agent / Direct Executor baselines.
- Counterfactual evidence removal and audit report generation.
- Real CloudApiProvider audit smoke over 5 scenarios x 2 evidence conditions.
- Reviewer-readable supplement and raw artifacts.

Latest useful audit artifacts:

```text
.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z
.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z
```

Use this as a failure-analysis case with a narrow scope.

## Three portfolio case cards

### Case 1 ? Why did Kai choose this action?

Show the runtime trace from motivation, memory, relationship evidence, and tool arbitration to a selected NPC action.

**Takeaway**: the system exposes behavior provenance alongside final state.

### Case 2 ? What changed when evidence was removed?

Show counterfactual replay where removing relationship / memory evidence changes scores or selected behavior.

**Takeaway**: eval artifacts help debug which evidence actually influenced a decision.

### Case 3 ? Why was this high-risk tool call blocked?

Show the audit supplement: full evidence allows the high-risk tool; missing policy evidence routes to a safe review tool.

**Takeaway**: the same trace/evidence idea extends to operational failure analysis.

## Honest boundaries

- Loomstead is frozen as a portfolio engineering project.
- Human-validated believability is out of scope.
- Enterprise-ready AI safety and complete causal proof are out of scope.
- The audit spike supports bounded feasibility and failure-analysis storytelling.
- Further work should move to clearer research lines unless a concrete demo or interview artifact needs small maintenance.

The strongest project claim is:

```text
I built a full-stack agent behavior observatory: a playable multi-agent runtime with structured traces, evidence-linked decisions, eval exports, and audit artifacts for debugging complex agent behavior.
```

## Local run

Use Windows PowerShell and `npm.cmd`.

```powershell
npm.cmd run context:resume
npm.cmd run context:check
npm.cmd run check
npm.cmd run client:env
npm.cmd run start
npm.cmd run client:run
```

The default Godot scene is:

```text
clients/godot/scenes/world_main.tscn
```

## Useful validation commands

```powershell
npm.cmd run check
npm.cmd run smoke
npm.cmd run eval:process
npm.cmd run eval:domain
npm.cmd run eval:robustness
npm.cmd run eval:audit
npm.cmd run eval:audit:llm-contract:full
npm.cmd run eval:archive:check
git diff --check
```

Real LLM calls require explicit environment authorization and valid local config:

```powershell
npm.cmd run eval:audit:llm-smoke:full
```

## Model configuration

Committed defaults are designed to run without secrets. Local model config and API keys stay in ignored files or environment variables.

- Template: `config/models.example.json`
- Local ignored config: `config/models.json`, `config/models.local.json`
- Check: `npm.cmd run model:check`

## Repository guide

- Current state: [docs/current_status.md](docs/current_status.md)
- Assistant entry: [AGENTS.md](AGENTS.md), [docs/agent_context.md](docs/agent_context.md)
- Portfolio story: [docs/portfolio_story.md](docs/portfolio_story.md)
- Capability map: [docs/portfolio_capability_map.md](docs/portfolio_capability_map.md)
- Technical overview: [paper/blog_main.md](paper/blog_main.md)
- Godot client: [clients/godot/README.md](clients/godot/README.md)

## Development notes

- Backend Runtime owns authoritative world state.
- Godot reads state, submits legal player actions, and presents results.
- LLM output enters visible state through parsing, validation, fallback, and event recording.
- New schemas, trace fields, eval artifacts, or Godot consumer fields start with a data contract.
- Unverified behavior is tracked as pending or manually unverified.
- Secrets, local absolute paths, unregistered assets, and temporary runtime files stay outside committed files.
