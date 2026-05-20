---
status: archived
owner_lane: context-governance
last_verified: 2026-05-20
startup_load: never
source_of_truth: false
scope: 已归档历史文档说明
---

# 归档区

本目录保留项目早期方向文档与阶段性快照，**不再作为当前事实源**。

## 归档时间与原因

2026-05-19 完成项目重定位（"少而深"路线 + 可解释多 Agent 叙事运行时），下列文档被新核心文档取代：

| 旧文档 | 取代文档 | 归档原因 |
| --- | --- | --- |
| `architecture_blueprint.md` | `agentic_game_design.md` + `gameplay_system_architecture.md` + `agent_loop_architecture.md` | 早期架构蓝图，已被多层 Agent 系统设计与 NPC agent loop 设计覆盖 |
| `implementation_plan.md` | `production_roadmap.md` | 早期实施计划，已被生产化路线和阶段重排取代 |
| `vertical_slice_spec.md` | `production_roadmap.md` 阶段定义 + `world_entity_model.md` | 第一版垂直切片规格，范围已被新阶段轴重写 |
| `daytime_integration_handoff.md` | `goal_board.md` + `current_status.md` | 单次白天交接快照，事实已合并到状态文档 |
| `skill_strategy.md` | `agentic_game_design.md` | 未实施的 Skill 策略草案 |
| `core_map.md` | `agent_loop_architecture.md` + `world_entity_model.md` + `production_roadmap.md` 阶段重排 | 重定位前的全面开发计划草案，结论已被三份新文档与方向文档吸收 |
| `initial_asset_generation_plan.md` | `asset_batches/` 目录 + `art_direction.md` | 早期资产生成计划，已被批次目录与艺术方向覆盖 |
| `map_sprite_first_batch_review.md` | —— | 单次资产复盘 |
| `map_sprite_second_batch_review.md` | —— | 单次资产复盘 |
| `phase2_research_addendum.md` | `research_framing_motivational_delegation.md` + `process_fidelity_eval_spec.md` + `cross_domain_adapter.md` + `project_vision.md` / `production_roadmap.md` / `agent_loop_architecture.md` 内研究 framing 增补 | 2026-05-20 一次性 patch notes，内容已应用到三份新决策源 + 三份既有事实源文档 |

## 使用规则

- 归档文档仅供历史背景查阅与需求溯源，**不得作为当前实现事实**。
- 长期方向冲突时以 `docs/project_vision.md` 为准，当前事实冲突时以 `docs/current_status.md` 为准。
- 如需复活某段历史结论，先确认其与新核心文档不冲突，再在新文档中显式吸收，不要直接引用归档文档。
