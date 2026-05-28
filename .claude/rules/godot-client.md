---
paths:
  - "clients/godot/**"
---

# Godot client context notes

- Godot is presentation and interaction glue; backend settlement rules stay in Python Runtime.
- Client environment notes live in `docs/game_client_environment.md`. The legacy gameplay architecture spec has moved to `docs/archive/gameplay_system_architecture.md`; treat it as historical only.
- Useful command validation includes `npm.cmd run client:env` and `npm.cmd run client:run:check`.
- Real window UX still depends on manual `npm.cmd run start` plus `npm.cmd run client:run` verification.
- Governance protocol in `docs/context_governance.md` applies; checkpoint reviews are required at milestone boundaries.
