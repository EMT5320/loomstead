---
description: Sweep backend, Web Debug, Godot, and docs for field and fact consistency after cross-lane Loomstead changes.
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# consistency-sweep

Use this workflow after cross-lane changes to confirm the same field, trace, feature, or verification fact is described consistently across implementation, UI consumers, and docs.

## Trigger

Run when:

- backend output changes and Web Debug or Godot consumes it
- Web Debug / Godot debug UI changes field names, filters, cards, or trace details
- `docs/current_status.md`, `docs/agent_context.md`, or research/eval docs are updated after implementation
- a handoff claims a feature is code integrated, command checked, or manually verified
- multiple agents or work sessions touched adjacent lanes

## Required context

Read the smallest relevant set:

- `docs/agent_context.md`
- `docs/current_status.md`
- source docs for the touched lane
- backend producer files for changed API / trace / eval fields
- Web Debug consumer files when frontend changed
- Godot consumer files when client changed
- command output, eval artifact, or manual verification note named by the claim

## Procedure

1. Define the consistency chain:
   - backend producer
   - Web Debug consumer
   - Godot consumer
   - eval / artifact producer when involved
   - docs / status wording
2. List the exact fields, event types, schema ids, commands, or facts under review.
3. Check code producers before docs; docs cannot override current implementation.
4. Check each direct consumer for field names, null / missing handling, filtering, labels, and displayed meaning.
5. Check docs for stale names, stale counts, over-strong wording, or missing verification boundary.
6. Label evidence as `code integrated`, `command checked`, `artifact backed`, `manual verified`, or `manual unverified`.
7. Recommend the smallest correction: code sync, docs wording, command rerun, artifact audit, or manual check.

## Common consistency chains

### Phase 2 trace / debug

- runtime event details
- `/api/debug.phase2`
- Web Debug Phase 2 card
- Godot Research Dock / observer panel
- status docs

### Process eval / archive

- eval runner output
- exported manifest / JSONL
- archive index / drift / promotion
- research claim wording
- status docs

### Godot UI verification

- backend API payload
- Godot parser / UI label
- `client:run:check` result
- true window manual observation note
- status docs

## Output template

```md
## Scope
<consistency chain and non-goals>

## Facts / fields checked
- <field, schema id, event type, command, or status claim>

## Evidence levels
- code integrated: <evidence>
- command checked: <commands or not-run>
- artifact backed: <artifact or not-needed>
- manual verified: <actual observation or none>
- manual unverified: <remaining behavior>

## Inconsistencies
- <producer/consumer/docs mismatch with file:line evidence>

## Verdict
consistent | consistent-with-caveats | needs-sync | blocked

## Next action
<smallest correction or verification>
```

## Guardrails

- Do not let docs override code, command output, artifacts, or actual manual observation.
- Do not claim UI behavior is verified from parser or headless checks alone.
- Do not expand into unrelated refactors when a wording or field sync is enough.
- Do not update status docs with design intent unless it is clearly labeled as intent or hypothesis.
- Do not hide skipped checks; list why they were not necessary or not possible.
