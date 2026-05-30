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

Backend runtime and Godot client launch commands (R1.1), in order:

```powershell
npm.cmd run client:env   # prepare the Godot client environment (first run / after env change)
npm.cmd run start        # start the backend runtime (authoritative world state + tick loop)
npm.cmd run client:run   # launch the Godot client window
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

Identify which on-screen views MUST be visible during capture (R1.1):

- Left side: browser / Web Debug or API response. Must keep the relevant Web Debug / API response view on screen for any shot that references it.
- Right side: Godot game window. The Godot window (town slice, HUD, and Observer Dock when opened) must be visible for every NPC-life / Observer Dock / trace shot.
- If only one window can be captured, prioritize the Godot game window; the Observer Dock and trace timeline must stay readable in frame.

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

### Subject → shot coverage (R1.1)

Each subject the Demo_Recording may present has at least one dedicated shot:

| Demo subject | Covering shot(s) |
| --- | --- |
| NPC autonomous life | 5-15s Living town, 15-25s Interaction, 25-35s Event result |
| Trace causal chain | 35-48s Observer dock, 48-58s Trace evidence |
| Rashomon memory (subjective memory view) | 35-48s Observer dock (subjective memory tab; compare the same event across two NPCs) |

The Demo_Recording needs to present at least one of these subjects; the shot list above covers all three so the operator can choose.

## Machine-checkable judgment criteria (operator reference)

These criteria are written for the operator to check against while recording. They describe the acceptance conditions a recorded video must satisfy; the script does NOT decode the video, so verification of the actual `.mp4` is manual (Manual_Verification_Gate).

- **Total duration 20-60s (R1.2):** the recorded Demo_Recording MUST have a total play duration of at least 20 seconds and no more than 60 seconds. Under 20s or over 60s = not accepted.
- **Subject continuously visible >=5s (R1.3):** at least one target subject (NPC autonomous life / Trace causal chain / Rashomon memory) MUST stay continuously visible on screen for at least 5 seconds. Count the on-screen seconds for the chosen subject; brief flashes do not satisfy this.
- **Caveat caption continuously visible >=3s (R1.4):** whenever the Demo_Recording references claim C2, C3, or C4, a caption stating the `promoted with caveat` status MUST stay continuously visible for at least 3 seconds while that claim content is on screen. If no C2/C3/C4 claim is referenced, this criterion does not apply.

> Caption wording must use `promoted with caveat` (see the caption stack below). Do not use stronger wording such as `proven` / `fully validated` for C2/C3/C4 (R10 consistency).

## Suggested caption stack

- Use `Few deep NPCs with subjective memory and traceable relationships` for external copy.
- `Motivational Delegation: shape context, then let NPCs choose actions`.
- `Process Fidelity: evaluate goal completion together with the path that produced it`.
- `Current evidence: C2/C3/C4 promoted with caveat; human process review remains pending`.

## Tick-failure recovery before recording (R1.5)

If the backend runtime reports a tick failure before recording:

1. Stop recording prep. Do NOT capture while the backend is reporting tick failures.
2. Restore the backend runtime (restart `npm.cmd run start`; inspect the backend log / `http://127.0.0.1:8787/api/world/state` for the failing tick cause and resolve it).
3. Confirm the backend processes at least one tick without failure before capturing the Demo_Recording (watch the tick counter advance with no failure entry).
4. Only after one clean tick is confirmed, start recording.

## Godot window manual recheck (R2.1 / R2.2)

Each behavior below requires manual window verification before recording. For each one, record a manual pass/fail using the stated expected observable result. These are Manual_Verification_Gate items and cannot be satisfied by an offline gate.

| Behavior | Expected observable window result (operator records pass/fail) |
| --- | --- |
| Observer Dock trace filtering | Switching the trace filter among decision / tool / interrupt / memory updates the trace timeline to show only matching events, newest first, capped at the most recent 50. Pass = list visibly re-filters and re-orders; fail = stale or unfiltered list. |
| Observer Dock Prev / Next navigation | Prev / Next moves the selected trace detail one step and the position indicator shows `current/total`; at the ends the index clamps (does not wrap past first/last). Pass = single-step move with a correct `current/total` indicator; fail = index out of range, no indicator, or no movement. |
| Interruption layout | When an interruption occurs, the interruption view renders in its expected on-screen position without overlapping/clipping the Observer Dock or HUD, and remains readable. Pass = interruption layout is visible, correctly placed, and readable; fail = missing, overlapping, or clipped layout. |

## Manual verification checklist

- [ ] Backend running without tick failures (see tick-failure recovery above).
- [ ] Godot window shows the default `world_main.tscn`.
- [ ] Observer dock opens with `Tab`.
- [ ] NPC selection updates the dock.
- [ ] Trace filter and `Copy trace` feedback are visible.
- [ ] Trace Prev / Next navigation steps correctly with a `current/total` indicator (R2.1/R2.2).
- [ ] Interruption layout renders in its expected position and stays readable (R2.1/R2.2).
- [ ] Final video duration is within 20-60s (R1.2).
- [ ] Chosen subject stays continuously visible for >=5s (R1.3).
- [ ] Final video includes a `promoted with caveat` caption visible >=3s if it mentions `C2`/`C3`/`C4` (R1.4).

## Known risks

- Latest Trace navigation / interruption layout still needs real-window recheck.
- `prompt_ready` expression variants and action icons are still asset backlog.
- Backend downtime leaves the Godot scene visible but removes the live runtime story.
- Current demo output is a capture plan; final `.mp4` / `.gif` remains a manual artifact.
