---
status: active
owner_lane: context-governance
last_verified: 2026-05-21
startup_load: index
source_of_truth: true
scope: 文档分层索引与渐进式读取路线
---

# Agent Valley 文档索引

本目录用于沉淀 `ai-agent-town-lab` 的核心共识。当前治理原则：新对话先读短入口，再按任务线渐进加载源文档；归档文档放在 `docs/archive/`，仅供历史溯源。

## 1. 当前定位（2026-05-19 重定位 + 2026-05-20 研究 framing）

`Agent Valley` 是一个 **narrative-primary 的可解释多 Agent 叙事运行时与研究环境**：通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，研究 Director 如何以 Motivational Delegation 间接驱动少量深度 NPC 朝过程约束目标演化，并用 Process Fidelity Eval 验证“过程是否可信”。项目以 **少而深 + 可解释 + 可评估** 为差异化主轴，小镇是 primary validation domain，跨域任务环境只作 secondary validation。详见 [`project_vision.md`](./project_vision.md)、[`research_framing_motivational_delegation.md`](./research_framing_motivational_delegation.md) 和 [`agent_loop_architecture.md`](./agent_loop_architecture.md)。

## 2. 新对话最小读取

1. [`../AGENTS.md`](../AGENTS.md)：所有开发助手共享的启动协议、任务线路由和验收规则。
2. [`agent_context.md`](./agent_context.md)：下一轮对话第一入口，记录当前边界、命令和最近下一步。
3. [`current_status.md`](./current_status.md)：当前实现事实、主要缺口、开发前硬性约束和人工验收清单。
4. [`goal_board.md`](./goal_board.md)：开发线看板、写入范围、并行任务拆分和交接格式。

## 3. 决策源文档

- [`project_vision.md`](./project_vision.md)：最高优先级产品愿景，定义长期方向、差异化主轴和成功标准。
- [`research_framing_motivational_delegation.md`](./research_framing_motivational_delegation.md)：研究定位与核心反论点，定义 narrative-primary / task-secondary、Motivational Delegation、Process Fidelity Eval、baseline matrix。
- [`agentic_game_design.md`](./agentic_game_design.md)：多层 Agent 系统设计源（Director / Event Skill / Memory / Model 分工）。
- [`agent_loop_architecture.md`](./agent_loop_architecture.md)：NPC agent loop 核心圣经（三层工具、动机系统、记忆架构、启发式学习、Arbitration、Eval）。
- [`world_entity_model.md`](./world_entity_model.md)：世界实体作为 agent 工具空间（FarmPlot / Item / Inventory / Shop / Building / Time / Weather）。
- [`gameplay_system_architecture.md`](./gameplay_system_architecture.md)：游戏本体架构、地图主循环、Godot / 后端边界。
- [`production_roadmap.md`](./production_roadmap.md)：阶段路线（Phase 1 收口 / Phase 2-6 重排）。
- [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md)：研究向 Eval 指标、hard delegation baseline、ablation protocol、dataset 输出规格。
- [`cross_domain_adapter.md`](./cross_domain_adapter.md)：跨域 adapter 接口，保证小镇 primary、为 task-secondary 验证保留路径。
- [`open_questions.md`](./open_questions.md)：已确认决策、剩余问题和实现中验证点。

## 4. 按开发线读取

### 后端 / Director / Event Skill / Agent Loop

- [`agentic_game_design.md`](./agentic_game_design.md)
- [`agent_loop_architecture.md`](./agent_loop_architecture.md)
- [`world_entity_model.md`](./world_entity_model.md)

### Godot 客户端

- [`gameplay_system_architecture.md`](./gameplay_system_architecture.md)
- [`production_roadmap.md`](./production_roadmap.md)
- [`game_client_environment.md`](./game_client_environment.md)
- [`../clients/godot/README.md`](../clients/godot/README.md)

### 内容 / NPC 深度卡

- [`game_content_storyline.md`](./game_content_storyline.md)
- [`npc_deep_card_spec.md`](./npc_deep_card_spec.md)

### LLM / Debug / Eval

- [`model_profile_template_guide.md`](./model_profile_template_guide.md)
- [`agentic_game_design.md`](./agentic_game_design.md)
- [`agent_loop_architecture.md`](./agent_loop_architecture.md)（含 Eval Framework）
- [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md)（研究向 Eval 指标、hard delegation baseline、ablation protocol）

### 研究 framing / 跨域 adapter

- [`research_framing_motivational_delegation.md`](./research_framing_motivational_delegation.md)：研究定位、核心反论点、baseline matrix、最小可行实验集。
- [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md)：Process Fidelity 指标公式、Hard Delegation baseline、关系记忆 ablation 专项。
- [`cross_domain_adapter.md`](./cross_domain_adapter.md)：DomainAdapter Protocol、Narrative / Coding domain 对比、directory proposal。

### 资产管线

- [`art_direction.md`](./art_direction.md)
- [`asset_generation_prompts.md`](./asset_generation_prompts.md)
- [`map_sprite_style_guide.md`](./map_sprite_style_guide.md)
- `asset_batches/`：批次计划与 prompt_ready 导出

### 上下文治理 / 助手适配

- [`../CLAUDE.md`](../CLAUDE.md)：Claude Code 适配层，导入根目录 `AGENTS.md`。
- [`../.claude/rules/`](../.claude/rules/)：Claude Code 路径规则。
- [`../scripts/build_agent_context.py`](../scripts/build_agent_context.py)：上下文 brief 生成和治理校验脚本。

## 5. 归档区

历史方向文档与单次快照统一放在 [`archive/`](./archive/README.md)，包含：

- `architecture_blueprint.md`（早期架构蓝图）
- `implementation_plan.md`（早期实施计划）
- `vertical_slice_spec.md`（旧第一版切片规格）
- `daytime_integration_handoff.md`（单次白天交接快照）
- `skill_strategy.md`（未实施的 Skill 策略草案）
- `core_map.md`（重定位前的全面开发计划草案）
- `initial_asset_generation_plan.md`（早期资产生成计划）
- `map_sprite_first_batch_review.md` / `map_sprite_second_batch_review.md`（单次资产复盘）

归档文档**不得作为当前事实源**。如需复活某段结论，需在新核心文档中显式吸收。

## 6. 文档状态表

| 文档 | 状态 | 开发线 | 加载策略 | 事实源 |
| --- | --- | --- | --- | --- |
| [`agent_context.md`](./agent_context.md) | active | context-governance | first-read | true |
| [`agentic_game_design.md`](./agentic_game_design.md) | active | backend-director | on-demand | true |
| [`agent_loop_architecture.md`](./agent_loop_architecture.md) | active | backend-director | on-demand | true |
| [`art_direction.md`](./art_direction.md) | active | asset-pipeline | on-demand | true |
| [`asset_generation_prompts.md`](./asset_generation_prompts.md) | active | asset-pipeline | on-demand | true |
| [`current_status.md`](./current_status.md) | active | project-status | after-agent-context | true |
| [`game_client_environment.md`](./game_client_environment.md) | active | godot-client | on-demand | true |
| [`game_content_storyline.md`](./game_content_storyline.md) | active | content-codex | on-demand | true |
| [`gameplay_system_architecture.md`](./gameplay_system_architecture.md) | active | godot-client | on-demand | true |
| [`goal_board.md`](./goal_board.md) | active | planning | after-agent-context | true |
| [`map_sprite_style_guide.md`](./map_sprite_style_guide.md) | active | asset-pipeline | on-demand | true |
| [`model_profile_template_guide.md`](./model_profile_template_guide.md) | active | llm-debug | on-demand | true |
| [`npc_deep_card_spec.md`](./npc_deep_card_spec.md) | active | content-codex | on-demand | true |
| [`open_questions.md`](./open_questions.md) | active | decisions | on-demand | true |
| [`production_roadmap.md`](./production_roadmap.md) | active | planning | on-demand | true |
| [`project_vision.md`](./project_vision.md) | active | vision | on-demand | true |
| [`README.md`](./README.md) | active | context-governance | index | true |
| [`world_entity_model.md`](./world_entity_model.md) | active | backend-director | on-demand | true |
| [`cross_domain_adapter.md`](./cross_domain_adapter.md) | active | research-runtime | on-demand | true |
| [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md) | active | eval | on-demand | true |
| [`research_framing_motivational_delegation.md`](./research_framing_motivational_delegation.md) | active | research | on-demand | true |
| [`archive/README.md`](./archive/README.md) | archived | context-governance | never | false |

## 7. 当前决策摘要

- 项目重定位为 **"可解释的多 Agent 叙事运行时"**：少量深度 NPC（4 核心 + 2 stub）+ 主观记忆 + 启发式学习 + Director/Skill 节奏 + Eval Framework + 可分享 Debug Trace。
- 三层工具分层：Physiological（规则） / Vocational（规则 + 局部 LLM） / Social-Strategic（LLM）。
- 动机系统**替换**软日程，导演层负责注入临时偏置和目标。
- 决策周期：每 NPC 每 15-30 游戏分钟评估需求；LLM 预算 social_layer ≤ 8 次/NPC/日。
- Capability registry 动态生成（NPC × 地点 × 物品状态）。
- 记忆架构：双轨（客观事件流 + 主观视图） + 关系图边带双时间戳 + 启发式记忆类型；不接 Graphiti / Mem0 等外部库，自研抽象层借鉴 Graphiti 范式。
- 启发式系统（Heuristic Library）作为 Phase 2 骨架核心，从失败/痛苦记忆自动提取，影响后续决策权重。
- Phase 1 收口后直接切换到 MotivationEngine（不并行）。
- Eval Framework 作为第五条核心能力，scripts/run_agent_eval.py 跑分层 scenario suite。
- 2026-05-20 研究 framing 增补：narrative-primary / task-secondary；研究主卖点改为 Motivational Delegation + Process Fidelity Eval；Phase 2 加入 Hard Delegation baseline 与关系记忆 ablation 作为硬验收（详见 `research_framing_motivational_delegation.md` / `process_fidelity_eval_spec.md` / `cross_domain_adapter.md`）。
- LLM Provider：DeepSeek V4 Flash 优先，RuleBasedProvider fallback；密钥只放 `config/models.local.json` 或环境变量。
- 视觉风格：二次元轻幻想轻异世界田园风（保留为 demo scenario 视觉外壳）。
- 玩家身份：参与者 + 观察者双模式，观察者模式从 Phase 5 提升为核心模式。

## 8. 文档维护规则

- `agent_context.md` 保持短入口，不堆长篇设计。
- `current_status.md` 只写当前已核对事实，未人工验收内容必须显式标注。
- `goal_board.md` 记录当前开发线、验收证据和下一轮排程。
- 长期愿景和阶段事实冲突时，先更新事实文档，再决定是否需要修订愿景或规格。
- 归档区文档不得作为当前事实源；如需复活结论，需在新核心文档中显式吸收。
- 每次调整上下文治理后运行：

```powershell
npm.cmd run context:check
git diff --check
```
