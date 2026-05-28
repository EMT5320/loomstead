---
paths:
  - "AGENTS.md"
  - "CLAUDE.md"
  - "README.md"
  - "docs/**/*.md"
  - "scripts/build_agent_context.py"
---

# Context governance notes

- `docs/context_governance.md` is the canonical governance protocol; read it before editing any doc layer.
- `AGENTS.md` and `docs/agent_context.md` are the shared orientation route.
- Doc frontmatter clarifies status: `active` is current, `snapshot` is stage evidence, `archive` is history only.
- `docs/current_status.md` carries current facts; `docs/project_vision.md` carries long-term direction; `docs/phase_checkpoints.md` carries the active milestone board.
- Working-layer docs have a 250-line soft cap and must not log historical changelogs; rely on git history instead.
- After context or docs changes, useful checks include `npm.cmd run context:check` and `git diff --check`.
