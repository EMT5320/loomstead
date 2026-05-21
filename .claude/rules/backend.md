---
paths:
  - "backend/**/*.py"
  - "scripts/*.py"
---

# Backend rules

- Backend owns authoritative world state; Godot submits actions and displays results.
- Preserve `RuleBasedProvider` fallback when changing LLM, Director, Runtime, or Skill code.
- For Director or Event Skill work, read `docs/agentic_game_design.md` and `docs/agent_loop_architecture.md` on demand.
- For Eval / research framing work, read `docs/research_framing_motivational_delegation.md` and `docs/process_fidelity_eval_spec.md` on demand.
- Validate backend changes with the smallest relevant command first, then `npm.cmd run smoke` or `npm.cmd run check`.
