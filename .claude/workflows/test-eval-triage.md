---
description: Choose the smallest useful verification commands for Loomstead changes and triage failures by lane.
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# test-eval-triage

Use this workflow to pick validation commands when switching environments, preparing commits, or diagnosing failures.

## Trigger

Run when:

- moving between home and company machines
- preparing a commit or PR
- a previous command failed
- a change touches multiple lanes
- a status update needs command evidence

## Lane detection

Identify touched areas from the diff or task scope:

- docs / context governance
- backend runtime / Director / Event Skill / Agent Loop
- eval / trace / schema / archive
- Godot client
- Web Debug frontend
- content / NPC cards
- assets
- LLM provider / model config

## Quick gate

Use for most changes before handoff:

```powershell
npm.cmd run context:check
npm.cmd run check
npm.cmd run smoke
git diff --check
```

## Lane gates

Use only when the lane is touched.

### Context / docs

```powershell
npm.cmd run context:check
git diff --check
```

### Backend / runtime / schema

```powershell
npm.cmd run check
npm.cmd run smoke
npm.cmd run schema:check
```

### Eval / archive / process fidelity

```powershell
npm.cmd run eval:process
npm.cmd run eval:stability
npm.cmd run eval:stability:determinism
npm.cmd run eval:domain
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
```

### Godot client

```powershell
npm.cmd run client:env
npm.cmd run client:run:check
```

Real Godot window behavior remains manual unless the user explicitly performs or requests it.

### Assets

```powershell
npm.cmd run asset:check
```

### LLM provider / true model evidence

```powershell
npm.cmd run llm:smoke
```

Run this only when provider, key, prompt, model profile, evidence freshness, latency, cost, or true-cloud behavior is part of the task.

## Failure triage

Classify failure before fixing:

- quick gate failure: broad repo breakage or formatting/context issue
- lane gate failure: targeted implementation or fixture issue
- eval gate failure: metric, fixture, artifact, schema, archive, or determinism issue
- manual gate blocked: missing key, balance, Godot binary, local environment, or human observation

## Output template

```md
## Scope
<touched lanes>

## Recommended commands
- <command>

## Commands intentionally skipped
- <command> — <reason>

## Result classification
pass | quick-gate-fail | lane-gate-fail | eval-gate-fail | manual-blocked | not-run

## Evidence level
command checked | manual unverified | local environment blocked

## Next action
<smallest next step>
```

## Guardrails

- Do not run real LLM checks by default.
- Do not treat `client:run:check` as a full Godot gameplay verification.
- Do not run long eval suites when a quick gate already fails.
- Do not hide skipped commands; list why they were skipped.
- Prefer minimum necessary validation over blanket command runs.
