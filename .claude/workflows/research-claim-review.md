---
description: Review whether a Loomstead research claim is supported by implementation, metrics, trace artifacts, and documented verification state.
allowed-tools: Read, Grep, Glob, Bash, Agent, Workflow
---

# research-claim-review

Use this workflow before strengthening research claims, updating research framing, publishing portfolio text, or moving eval observations into `docs/current_status.md`.

## Trigger

Run when a change or discussion introduces claims about:

- Motivational Delegation.
- Process Fidelity Eval.
- narrative-primary / task-secondary transfer.
- traceability, explainability, memory causality, relationship evolution, or baseline superiority.

## Required context

Read only the minimum relevant sources:

- `docs/agent_context.md`
- `docs/current_status.md`
- `docs/research_framing_motivational_delegation.md`
- `docs/process_fidelity_eval_spec.md`
- `docs/cross_domain_adapter.md` when transfer or task-secondary claims are involved.
- Relevant code or artifacts named by the claim.

## Procedure

1. Restate the claim in one sentence.
2. Classify the claim type:
   - design intent
   - code integrated
   - command checked
   - artifact backed
   - manual verified
   - manual unverified
3. Identify the strongest counterclaim.
4. Check whether the evidence directly addresses the counterclaim.
5. Verify whether evidence comes from current code, current docs, command output, eval artifacts, or manual observation.
6. Check whether baseline / ablation evidence is required.
7. Check whether the claim depends on true LLM or Godot window behavior.
8. Recommend one of:
   - keep as current fact
   - weaken wording
   - move to design / hypothesis doc
   - require another command
   - require manual verification
   - reject for now

## Evidence checklist

A strong claim should point to at least one of:

- specific code path
- specific test or npm command
- promoted eval run / manifest
- trace chain
- baseline / ablation comparison
- schema registry snapshot
- manual verification note

For Process Fidelity claims, prefer evidence involving:

- `forced_action_rate`
- `intervention_overreach_rate`
- `causal_trace_coverage`
- `relationship_memory_causal_use_rate`
- process believability / shortcut violation signals

## Output template

```md
## Claim
<one sentence>

## Verdict
keep | weaken | move-to-hypothesis | needs-command | needs-manual-verification | reject-for-now

## Evidence level
code integrated | command checked | artifact backed | manual verified | manual unverified | design intent

## Supporting evidence
- <file:line, command, artifact, or trace reference>

## Counterclaim
<best opposing interpretation>

## Gaps
- <missing evidence or fairness issue>

## Recommended wording
<safe wording for docs/current_status.md or research docs>
```

## Guardrails

- Do not upgrade design intent into current fact.
- Do not treat a passing final-task metric as Process Fidelity proof by itself.
- Do not let task-secondary evidence override the narrative-primary claim.
- Do not write to `docs/current_status.md` unless the evidence level is explicit.
