---
paths:
  - "backend/**/*.py"
  - "scripts/*.py"
---

# Backend context notes

- Backend owns authoritative world state; Godot submits actions and displays results.
- `RuleBasedProvider` fallback is the current safety net for LLM, Director, Runtime, and Skill changes.
- Director or Event Skill work usually references `docs/agentic_game_design.md` and `docs/agent_loop_architecture.md`.
- Eval / research framing work usually references `docs/research_framing_motivational_delegation.md` and `docs/process_fidelity_eval_spec.md`.
- Useful validation commands include the smallest relevant command first, then `npm.cmd run smoke` or `npm.cmd run check`.
