---
paths:
  - "clients/godot/**"
---

# Godot client context notes

- Godot is presentation and interaction glue; backend settlement rules stay in Python Runtime.
- Client changes usually reference `docs/game_client_environment.md` and `docs/gameplay_system_architecture.md`.
- Useful command validation includes `npm.cmd run client:env` and `npm.cmd run client:run:check`.
- Real window UX still depends on manual `npm.cmd run start` plus `npm.cmd run client:run` verification.
