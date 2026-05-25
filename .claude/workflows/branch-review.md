---
description: Review the current branch or PR before shipping by combining diff review, targeted bug sweep, and verification evidence.
allowed-tools: Read, Grep, Glob, Bash, Agent, Workflow
---

# branch-review

Use this workflow before merging, opening a PR, or handing off a branch that changed implementation, eval behavior, schema, UI, or project status.

## Trigger

Run when:

- preparing a PR or final branch handoff
- reviewing a branch after a multi-file implementation
- updating `docs/current_status.md` from recent changes
- deciding whether `review-branch`, `code-review`, `bughunt-lite`, or a narrower manual review is enough

## Required context

Read only the minimum relevant sources:

- `docs/agent_context.md`
- `docs/current_status.md`
- `docs/workflows.md`
- current git status and diff
- touched source files or docs named by the diff
- eval artifact / manifest only when the branch changes eval output or claims

## Procedure

1. Identify touched lanes from the diff:
   - docs / context governance
   - backend runtime / Director / Event Skill / Agent Loop
   - eval / trace / schema / archive
   - Godot client
   - Web Debug frontend
   - content / NPC cards
   - assets
   - LLM provider / model config
2. Classify review depth:
   - narrow: docs-only or single-lane low-risk change
   - standard: implementation branch with tests or smoke coverage
   - high-risk: runtime, eval, schema, trace, provider, or cross-lane UI/debug changes
3. Choose review tool:
   - use direct diff reading for narrow changes
   - use `code-review` or `review-branch` for standard PR review
   - use `bughunt-lite` for high-risk changes with bounded scope
   - use `bughunt` only when the user asks for a broad or exhaustive sweep
4. Check whether each finding points to current code, command output, artifact, or manual observation.
5. Check whether the branch updated status docs only for evidence-backed facts.
6. Recommend the smallest validation set, usually via `test-eval-triage`.
7. Report ship readiness and blockers.

## Review checklist

- correctness bugs and broken assumptions
- stale or over-strong status / research wording
- schema registry, trace, debug API, and consumer drift when touched
- eval baseline, ablation, manifest, and archive drift when touched
- UI behavior that still needs true Godot or browser observation
- secrets, local overlays, generated artifacts, or machine-specific paths accidentally staged

## Output template

```md
## Scope
<touched lanes and risk level>

## Review method
manual diff | code-review | review-branch | bughunt-lite | bughunt

## Findings
- [severity] <finding with file:line and evidence>

## Verification state
- code integrated: <yes/no/partial>
- command checked: <commands or not-run>
- artifact backed: <manifest/run or not-needed>
- manual verified: <what was actually observed>
- manual unverified: <Godot/browser/LLM behavior still needing human or true-provider check>

## Ship verdict
ready | ready-with-caveats | blocked

## Next action
<smallest next step>
```

## Guardrails

- Do not treat docs as proof when code or artifacts disagree.
- Do not run broad bug hunts for small docs-only changes.
- Do not post PR comments or create PRs unless explicitly asked.
- Do not promote local `.run/` evidence without manifest or documented summary.
- Do not claim Godot gameplay, browser behavior, or true LLM behavior was verified unless it was actually observed.
