---
status: archive
owner_lane: context-governance
last_verified: 2026-05-28
startup_load: never
source_of_truth: false
scope: 已归档历史文档说明
---

# 归档区

本目录保留项目早期方向文档与阶段性快照，**不再作为当前事实源**。AI 助手不得引用归档文档作为决策依据；如需复活结论，必须先在新核心文档显式吸收。

## 归档时间与原因

### 2026-05-19 项目重定位归档

由"二次元田园 RPG"重定位为"narrative-primary 可解释多 Agent 叙事运行时"，下列文档被新核心文档取代：

| 旧文档 | 取代文档 | 归档原因 |
|---|---|---|
| `architecture_blueprint.md` | `agent_loop_architecture.md` | 早期架构蓝图，已被多层 Agent 系统设计与 NPC agent loop 设计覆盖 |
| `implementation_plan.md` | `production_roadmap.md` | 早期实施计划，已被生产化路线和阶段重排取代 |
| `vertical_slice_spec.md` | `production_roadmap.md` 阶段定义 + `world_entity_model.md` | 第一版垂直切片规格，范围已被新阶段轴重写 |
| `daytime_integration_handoff.md` | `current_status.md` + `agent_context.md` | 单次白天交接快照 |
| `goal_board.md` | `current_status.md` + `agent_context.md` | 前期多线程并行开发看板，已收敛到状态文档与新对话入口 |
| `skill_strategy.md` | `agent_loop_architecture.md` | 未实施的 Skill 策略草案 |
| `core_map.md` | `agent_loop_architecture.md` + `world_entity_model.md` + `production_roadmap.md` | 重定位前的全面开发计划草案 |
| `initial_asset_generation_plan.md` | `asset_batches/` + `art_direction.md` | 早期资产生成计划 |
| `map_sprite_first_batch_review.md` / `map_sprite_second_batch_review.md` | —— | 单次资产复盘 |
| `phase2_research_addendum.md` | `research_framing_motivational_delegation.md` + `process_fidelity_eval_spec.md` + `cross_domain_adapter.md` | 2026-05-20 一次性 patch notes，内容已应用到决策源文档 |
| `eval_agent_paper_exploration_2026-05-27.md` | `paper/` 目录 + `paper/claim_evidence_matrix.md` | 一次性论文探索快照 |

### 2026-05-28 上下文治理归档

随治理协议 `docs/context_governance.md` 落地，下列重定位后引用度极低的设计文档归入归档层。它们仍记录早期一致设计意图，但已不在新决策路径上：

| 旧文档 | 取代文档 | 归档原因 |
|---|---|---|
| `agentic_game_design.md` | `agent_loop_architecture.md` + `project_vision.md` | 多层 Agent 系统总论已被 NPC agent loop 圣经吸收，重定位后未再引导决策 |
| `gameplay_system_architecture.md` | `production_roadmap.md` + `world_entity_model.md` + `clients/godot/` 实现 | 游戏本体架构在 Phase 1 收口后已转为代码与 roadmap 维护 |
| `game_content_storyline.md` | `backend/app/content/` 实现 + `npc_codex` 数据 | 内容剧情线方向已固化到代码与 NPC 深度卡数据中 |
| `npc_deep_card_spec.md` | `backend/app/content/codex_schema.py` + `npc_codex` 数据 | NPC 深度卡 schema 已落到代码契约 |

## 使用说明

- 归档文档仅供历史背景查阅与需求溯源，当前实现事实以 active 文档为准。
- 长期方向冲突时以 `docs/project_vision.md` 为准，当前事实冲突时以 `docs/current_status.md` 为准。
- 治理协议见 `docs/context_governance.md`。
