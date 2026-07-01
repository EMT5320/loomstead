---
status: snapshot
owner_lane: asset-pipeline
last_verified: 2026-05-16
startup_load: on-demand
source_of_truth: false
scope: second map-sprite review snapshot and promotion notes
---

# 地图小人闭环重画最终检查

日期：2026-05-16
范围：`npc_orren_map_idle`、`npc_lena_map_idle`、`npc_kai_map_idle`、`npc_bram_map_idle` 四张 `idle_front` 地图小人，以及 `interaction_marker_talk`、`interaction_marker_gift`、`interaction_marker_event` 三张交互标记。

## 本轮结论

1. 第一批 `style_anchor_candidate`（`player_farmer_map_idle`、`npc_mira_map_idle`、`npc_tomas_map_idle`）继续作为地图小人风格锚点。
2. 四张失败的小人已按锚点重画，回到“二次元 Q 版低像素角色主体”方向；64x64 原图、32x32 缩略检查图、Godot PNG 均已同步。
3. 所有新增小人仍在 `asset_manifest.json` 中保持 `pending_review`，暂不晋级 `source_selected`，等待主人在游戏窗口里最终确认。
4. 当前重画批次整体比上一版抽象几何图案稳定：Orren 保留银发长者和绿色外套，Lena 保留医生白 coat，Kai 保留红发乐手暖色调，Bram 回到草帽/农场主剪影。
5. `talk/gift/event` 交互标记继续保持 `pending_review`，后续结合 UI / 地图层可读性再决定是否重画或替换。
6. 本轮重点是修正风格漂移和文档可读性，暂不扩大资产范围，避免在客户端实机验收前继续累积待审图。

## 输出文件

| 资产 ID | source | processed | Godot 路径 | Manifest 状态 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `npc_orren_map_idle` | `assets/source/sprites/npc_orren_map_idle.png` | `assets/processed/sprites/npc_orren_map_idle.png` | `clients/godot/assets/sprites/npc_orren_map_idle.png` | `pending_review` | 长者/教师小人候选 |
| `npc_lena_map_idle` | `assets/source/sprites/npc_lena_map_idle.png` | `assets/processed/sprites/npc_lena_map_idle.png` | `clients/godot/assets/sprites/npc_lena_map_idle.png` | `pending_review` | 医生小人候选 |
| `npc_kai_map_idle` | `assets/source/sprites/npc_kai_map_idle.png` | `assets/processed/sprites/npc_kai_map_idle.png` | `clients/godot/assets/sprites/npc_kai_map_idle.png` | `pending_review` | 酒馆乐手小人候选 |
| `npc_bram_map_idle` | `assets/source/sprites/npc_bram_map_idle.png` | `assets/processed/sprites/npc_bram_map_idle.png` | `clients/godot/assets/sprites/npc_bram_map_idle.png` | `pending_review` | 农场主小人候选 |
| `interaction_marker_talk` | `assets/source/sprites/interaction_marker_talk.png` | `assets/processed/sprites/interaction_marker_talk.png` | `clients/godot/assets/sprites/interaction_marker_talk.png` | `pending_review` | 交谈提示图标 |
| `interaction_marker_gift` | `assets/source/sprites/interaction_marker_gift.png` | `assets/processed/sprites/interaction_marker_gift.png` | `clients/godot/assets/sprites/interaction_marker_gift.png` | `pending_review` | 礼物提示图标 |
| `interaction_marker_event` | `assets/source/sprites/interaction_marker_event.png` | `assets/processed/sprites/interaction_marker_event.png` | `clients/godot/assets/sprites/interaction_marker_event.png` | `pending_review` | 事件提示图标 |

最终重画对比图：`assets/processed/sprites/map_sprite_redraw_final_64_32_check.png`

上一版失败对比图：`assets/processed/sprites/map_sprite_second_batch_64_32_check.png`

## 采用来源

| 资产 ID | 采用图 | 采用原因 |
| --- | --- | --- |
| `npc_orren_map_idle` | `ig_02b9e0c8567ffda2016a08041ac20881909f765220af79cfe8.png` | 更接近第一批锚点，长者银发与绿色外套在 64px/32px 下仍可读。 |
| `npc_lena_map_idle` | `ig_02b9e0c8567ffda2016a080453b1e48190b14866f7124ecf6e.png` | 医生身份更清楚，白 coat 和青绿色发型没有被几何块吞掉。 |
| `npc_kai_map_idle` | `ig_02b9e0c8567ffda2016a08023af430819092ee203392785a2d.png` | 红发、暖色披肩和乐手气质更明显，64px/32px 下主体完整。 |
| `npc_bram_map_idle` | `ig_02b9e0c8567ffda2016a0802b9ec508190aa0e5866db954800.png` | 草帽、棕色工作服和农场主剪影清楚，修正了上一版木箱/几何块压过角色的问题。 |

原始生成目录：`<local-generated-images-dir>/019e2f41-7101-72a1-b294-271937c83b81/`

## 64x64 / 32x32 检查

| 资产 ID | 角色主体 | 身份读感 | 32px 缩略 | 状态 |
| --- | --- | --- | --- | --- |
| `npc_orren_map_idle` | 银发长者轮廓、绿色外套、浅色围巾可读 | 教师/长者方向成立 | 32px 下保留银发和绿色主色 | `pending_review` |
| `npc_lena_map_idle` | 青绿色发型、白 coat、医疗 satchel 可读 | 医生身份成立 | 32px 下仍能看到白 coat 块面 | `pending_review` |
| `npc_kai_map_idle` | 红发、暖色服装、乐手装饰可读 | 酒馆乐手方向成立 | 32px 下保留红发和暖色主调 | `pending_review` |
| `npc_bram_map_idle` | 草帽/棕色工作服、农场主姿态可读 | 农场主身份成立 | 32px 下能读出草帽和土色剪影 | `pending_review` |

## 交互标记保留策略

| 资产 ID | 用途 | Manifest 状态 | 备注 |
| --- | --- | --- | --- |
| `interaction_marker_talk` | talk 操作提示 / UI 浮标 | `pending_review` | 后续结合 Godot 地图层可读性判断是否采用。 |
| `interaction_marker_gift` | gift 操作提示 / UI 浮标 | `pending_review` | 后续结合 Godot 地图层可读性判断是否采用。 |
| `interaction_marker_event` | event 操作提示 / UI 浮标 | `pending_review` | 后续结合 Godot 地图层可读性判断是否采用。 |

## 后续人工评审关注点

- Orren：32px 下是否需要进一步强化眼镜/长者符号。
- Lena：白 coat 是否会和浅色地面或 UI 高亮混在一起。
- Kai：红发和乐手装饰在动态地图上是否足够醒目。
- Bram：草帽和土色服装在农田背景里是否需要增加边缘明暗。
- 所有小人：先在 Godot 实机窗口检查碰撞层、遮挡层和摄像机缩放，再决定是否晋级 `source_selected`。
