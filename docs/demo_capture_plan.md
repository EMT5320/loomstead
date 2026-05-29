---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-05-29
startup_load: on-demand
source_of_truth: true
scope: 60 秒求职展示录屏脚本、启动命令与人工验收边界
---

# Loomstead 60-second demo capture plan

> 自管理层文档。用于求职展示线的录屏准备；真实窗口观感与最终视频文件仍属于 `manual unverified`，需要人工录制后确认。

## Goal

Produce a short portfolio clip that shows:

1. a playable Godot town slice,
2. autonomous NPC interaction through the authoritative Python runtime,
3. the Phase 2 observer dock for motivation / memory / relationships / heuristics,
4. trace filtering and copyable evidence for Process Fidelity debugging.

## Local run commands

```powershell
npm.cmd run client:env
npm.cmd run start
npm.cmd run client:run
```

Optional preflight:

```powershell
npm.cmd run client:run:check
```

Backend health check:

```text
http://127.0.0.1:8787/api/world/state
```

## Recommended recording layout

- Left side: browser / Web Debug or API response.
- Right side: Godot game window.
- If only one window can be captured, prioritize the Godot game window.

## 60-second shot list

| Time | Shot | What to show |
| --- | --- | --- |
| 0-5s | Project identity | `Loomstead`, playable town slice, observer/debug angle. |
| 5-15s | Living town | Move the player across farm / plaza / tavern and let the HUD tick. |
| 15-25s | Interaction | Approach an NPC or event, reveal candidate actions, press `E` or `Space`. |
| 25-35s | Event result | Inspect or attend an active event and let the VN result panel appear. |
| 35-48s | Observer dock | Press `Tab`, select an NPC, show motivation, subjective memory, relationships, and heuristics. |
| 48-58s | Trace evidence | Switch trace filters, use Prev / Next, copy a trace JSON item. |
| 58-60s | Closing frame | Hold on the selected NPC plus `/api/debug.phase2`; caption: `World state + behavior trace + interactive debug`. |

## Suggested caption stack

- Use `Few deep NPCs with subjective memory and traceable relationships` for external copy.
- `Motivational Delegation: shape context, then let NPCs choose actions`.
- `Process Fidelity: evaluate goal completion together with the path that produced it`.
- `Current evidence: C2/C3/C4 promoted with caveat; human process review remains pending`.

## Manual verification checklist

- [ ] Backend running without tick failures.
- [ ] Godot window shows the default `world_main.tscn`.
- [ ] Observer dock opens with `Tab`.
- [ ] NPC selection updates the dock.
- [ ] Trace filter and `Copy trace` feedback are visible.
- [ ] Final video includes a caveat caption if it mentions `C2`/`C3`/`C4`.

## Known risks

- Latest Trace navigation / interruption layout still needs real-window recheck.
- `prompt_ready` expression variants and action icons are still asset backlog.
- Backend downtime leaves the Godot scene visible but removes the live runtime story.
- Current demo output is a capture plan; final `.mp4` / `.gif` remains a manual artifact.
