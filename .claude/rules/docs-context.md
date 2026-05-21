---
paths:
  - "AGENTS.md"
  - "CLAUDE.md"
  - "README.md"
  - "docs/**/*.md"
  - "scripts/build_agent_context.py"
---

# Context governance notes

- `AGENTS.md` and `docs/agent_context.md` are the shared orientation route.
- Doc frontmatter clarifies status: `active` is current, `snapshot` is stage evidence.
- `docs/current_status.md` carries current facts; `docs/project_vision.md` carries long-term direction.
- After context or docs changes, useful checks include `npm.cmd run context:check` and `git diff --check`.
