---
description: Check Loomstead schema registry, trace schema, Debug API, eval manifest, and consumer alignment after schema-shaped changes.
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# schema-drift

Use this workflow when schema-shaped changes may cause drift between runtime output, registry declarations, eval artifacts, UI consumers, and project documentation.

## Trigger

Run when a change touches:

- `schema_registry.v1`
- `phase2.trace.v1` or trace event details
- motivation, capability, budget, provider usage, observer, memory, relationship, heuristic, or Event Skill outcome schema
- `GET /api/debug.phase2` shape
- eval manifest, export, archive, drift, or promotion schema
- Web Debug or Godot consumers of Phase 2 debug / trace fields
- docs that state schema version, field shape, or verification facts

## Required context

Read only the relevant subset:

- `docs/agent_context.md`
- `docs/current_status.md`
- `docs/process_fidelity_eval_spec.md` when eval schema is involved
- `docs/cross_domain_adapter.md` when domain export schema is involved
- `backend/app/runtime/schema_registry.py`
- touched runtime / eval / debug API implementation
- touched Web Debug or Godot consumer code
- current artifact manifest only when an export or archive is being audited

## Procedure

1. Define the schema surface being checked and explicit non-goals.
2. Confirm every emitted schema id is registered and every touched registry entry is emitted or intentionally reserved.
3. Compare trace/debug payload shape against direct consumers.
4. Compare eval manifest/export/archive schema against scripts that write, read, index, drift-check, or promote it.
5. Check docs for stale schema names, stale counts, or upgraded verification claims.
6. Select the minimum command set.
7. Classify drift as aligned, needs follow-up, or blocked.

## Useful commands

Use the smallest necessary set.

```powershell
npm.cmd run schema:check
npm.cmd run smoke
npm.cmd run context:check
git diff --check
```

When eval schema, export, archive, or drift changed:

```powershell
npm.cmd run eval:process
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
```

When domain adapter export changed:

```powershell
npm.cmd run eval:domain
```

When Godot consumers changed:

```powershell
npm.cmd run client:env
npm.cmd run client:run:check
```

## Drift checklist

- registry id, version, and description match emitted payloads
- smoke or schema checks cover the new / changed field when practical
- Debug API exposes the registry or schema snapshot expected by consumers
- Web Debug and Godot read fields defensively only at external API boundary
- eval exports include schema snapshot, rowCount, hash / integrity, command context, and git context when expected
- docs distinguish command checked from manual unverified behavior

## Output template

```md
## Scope
<schema surfaces and non-goals>

## Surfaces checked
- schema registry: aligned | drift | not-touched
- runtime trace: aligned | drift | not-touched
- Debug API: aligned | drift | not-touched
- eval manifest/export/archive: aligned | drift | not-touched
- Web Debug consumer: aligned | drift | not-touched
- Godot consumer: aligned | drift | not-touched
- docs/status wording: aligned | drift | not-touched

## Commands / artifacts
- <command or artifact path>

## Drift findings
- <field/schema mismatch with file:line evidence>

## Verdict
aligned | needs-follow-up | blocked

## Next action
<smallest fix, command, or manual verification>
```

## Guardrails

- Do not broaden into unrelated gameplay, UI, or eval quality review.
- Do not require full eval suites for a registry-only change unless export/archive semantics changed.
- Do not treat docs as source of truth over emitted code or artifact manifests.
- Do not silently accept schema ids emitted outside the registry.
- Do not write status facts unless the verification level is explicit.
