---
description: Audit Loomstead Process Fidelity Eval evidence before promoting runs or updating research/status claims.
allowed-tools: Read, Grep, Glob, Bash, Agent, Workflow
---

# process-eval-audit

Use this workflow to keep Process Fidelity Eval evidence reproducible across home and office environments.

## Trigger

Run after or before:

- `npm.cmd run eval:process`
- `npm.cmd run eval:stability`
- `npm.cmd run eval:stability:determinism`
- `npm.cmd run eval:domain`
- `npm.cmd run eval:archive:check`
- `npm.cmd run eval:archive:drift`
- eval run promotion
- changes to metrics, baseline, ablation, manifest, archive, domain adapter, or trace schema

## Required context

- `docs/process_fidelity_eval_spec.md`
- `docs/current_status.md`
- `docs/eval_dataset_archive.md`
- `docs/cross_domain_adapter.md` when domain transfer is involved.
- Relevant scripts under `scripts/` and `backend/app/eval/` when implementation changed.
- Current eval artifact or manifest when available.

## Procedure

1. Identify the eval question being answered.
2. Identify the run or command evidence being audited.
3. Confirm whether evidence is offline deterministic, cloud/mixed LLM, or manual.
4. Check baseline coverage:
   - Full Motivational Delegation
   - Hard Delegation
   - Static Todo Planner if relevant
   - No Subjective Memory
   - No Relationship Edge
   - Shuffled Owner
   - Evidence-Link Removal
5. Check whether each ablation actually removes the intended mechanism.
6. Check artifact completeness:
   - manifest exists
   - row count is recorded
   - schema version / snapshot is recorded
   - hash or equivalent integrity field exists
   - command and configuration are recoverable
   - git status / commit context is represented when expected
7. Check trace quality:
   - motivation / decision evidence
   - tool execution result
   - memory or relationship consequence
   - source event ids or trace refs
8. Check drift / promotion status.
9. Decide whether current evidence supports status updates, research wording, or only a local observation.

## Command matrix

Use the smallest necessary set.

```powershell
npm.cmd run eval:process
npm.cmd run eval:stability
npm.cmd run eval:stability:determinism
npm.cmd run eval:domain
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
```

Only run real LLM checks when provider, prompt, profile, model, key, or evidence freshness requires it:

```powershell
npm.cmd run llm:smoke
```

## Output template

```md
## Eval question
<question>

## Evidence level
offline command checked | cloud/mixed command checked | artifact backed | manual unverified

## Commands / artifacts
- <command or manifest path>

## Baseline and ablation coverage
- Full: present | missing | not needed
- Hard Delegation: present | missing | not needed
- No Subjective Memory: present | missing | not needed
- No Relationship Edge: present | missing | not needed
- Shuffled Owner: present | missing | not needed
- Evidence-Link Removal: present | missing | not needed

## Trace / manifest completeness
- manifest: pass | fail | unknown
- rowCount: pass | fail | unknown
- schema snapshot: pass | fail | unknown
- hash/integrity: pass | fail | unknown
- trace refs: pass | fail | unknown

## Verdict
promotable | usable-with-caveat | local-only | insufficient

## Caveats
- <manual unverified, cloud key, drift, fairness, or schema concern>

## Recommended status wording
<safe wording if docs/current_status.md is updated>
```

## Guardrails

- Do not promote a run because one headline score improved.
- Do not compare baselines unless configs and scenario coverage are clear.
- Do not let local `.run/` artifacts become long-term facts without manifest or documented summary.
- Always distinguish offline deterministic evidence from true LLM evidence.
