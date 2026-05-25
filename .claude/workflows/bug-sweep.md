---
description: Run a bounded bug sweep for high-risk Loomstead runtime, eval, schema, trace, or cross-lane changes.
allowed-tools: Read, Grep, Glob, Bash, Agent, Workflow
---

# bug-sweep

Use this workflow to find high-confidence bugs before or after risky implementation work without turning the task into an unbounded full-repo audit.

## Trigger

Run when a change touches or plans to touch:

- runtime decision flow, tool execution, memory observation, relationship edges, or heuristics
- eval metrics, baselines, ablations, manifests, archive, drift, or promotion
- schema registry, trace shape, Debug API, or schema consumers
- cross-lane backend -> Web Debug -> Godot behavior
- provider routing, budget accounting, or fallback behavior

## Required context / lane detection

Identify the smallest relevant scope from:

- current diff or planned change
- `docs/agent_context.md`
- `docs/current_status.md`
- lane source docs when the risk is design or eval related
- touched implementation files and their direct callers / consumers
- existing command output or eval artifacts when available

## Choose mode

Default to `lite`.

### Lite

Use `bughunt-lite` or a small manual sweep when:

- the diff is small or single-lane
- the bug class is known
- the goal is quick high-confidence regression detection
- validation can be covered by targeted commands

### Full

Use `bughunt` only when the user asks for a broad sweep or when multiple high-risk conditions apply:

- runtime core path plus schema or eval changes
- trace / debug / consumer contract changes across layers
- baseline or ablation logic that could produce plausible but misleading eval results
- provider / fallback / budget behavior affecting evidence credibility
- branch is near release or external presentation

## Procedure

1. State the bounded scope and selected mode.
2. Identify the highest-risk invariants.
3. Inspect the diff and direct call / consumer chain.
4. Look for correctness bugs, stale assumptions, broken schema contracts, misleading eval evidence, or unhandled boundary failures.
5. Verify each candidate bug against code, tests, command output, artifact, or trace evidence.
6. Drop low-confidence speculation unless it suggests a concrete follow-up check.
7. Recommend the smallest fix or validation step.

## Bug classes to prioritize

- decision trace points to evidence that no longer exists
- schema registry declares a version not emitted by runtime or eval output
- eval ablation removes the wrong mechanism or only changes reporting
- Debug API fields changed without Web Debug / Godot consumer updates
- fallback path hides provider, budget, or parsing failures
- docs promote manual-unverified behavior to verified fact
- generated or local artifacts leak into committed state

## Output template

```md
## Scope
<touched lanes and explicit non-goals>

## Mode
lite | full

## Invariants checked
- <invariant>

## Findings
- [blocker|high|medium|low] <bug>
  - Evidence: <file:line, command, artifact, or trace>
  - Impact: <why it matters>
  - Recommendation: <smallest fix or check>

## Not verified
- <manual, LLM, Godot, browser, or long-run behavior not checked>

## Verdict
no-bugs-found | fix-before-ship | needs-targeted-verification | needs-full-sweep
```

## Guardrails

- Do not modify code unless the user explicitly asks to fix findings.
- Do not expand from a bounded bug sweep into general refactoring.
- Do not treat passing commands as proof that eval evidence is meaningful.
- Do not claim manual UI, Godot window, browser, or true LLM behavior was verified from static review.
- Do not report a bug without a concrete evidence path or a clearly labeled verification gap.
