---
paths:
  - "assets/**"
  - "clients/godot/assets/**"
  - "docs/art_direction.md"
  - "docs/asset_generation_prompts.md"
  - "docs/map_sprite_*.md"
---

# Asset pipeline context notes

- New assets are tracked in `assets/manifests/asset_manifest.json` with source, usage, status, prompt reference, and license note.
- Map sprites move to `source_selected` after Godot real-window review evidence.
- Prompt-only or unverified material remains outside final-source status.
- Useful validation includes `npm.cmd run asset:check`; `npm.cmd run check` is useful when code paths are affected.
