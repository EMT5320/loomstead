---
paths:
  - "backend/**/*.py"
  - "scripts/**/*.py"
---

# Backend context notes

- Backend owns authoritative world state; Godot submits actions and displays results.
- `RuleBasedProvider` fallback is the current safety net for LLM, Director, Runtime, and Skill changes.
- Director / Event Skill / NPC agent loop work references `docs/agent_loop_architecture.md` and `docs/world_entity_model.md`.
- Eval / research framing work references `docs/research_framing_motivational_delegation.md` and `docs/process_fidelity_eval_spec.md`.
- Useful validation commands include the smallest relevant command first, then `npm.cmd run smoke` or `npm.cmd run check`.
- Real LLM smoke is opt-in via `npm.cmd run llm:smoke`; only run when key, profile, or evidence needs refreshing.
- Governance protocol in `docs/context_governance.md` overrides any "minimal change" preference: pick the most direct path, stop and report at checkpoints.
