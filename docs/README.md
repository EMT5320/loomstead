---
status: active
owner_lane: context-governance
last_verified: 2026-05-28
startup_load: index
source_of_truth: true
scope: 文档分层索引与渐进式读取路线
---

# Loomstead 文档索引

本目录沉淀 `Loomstead` 的核心共识。文档遵守 `docs/context_governance.md` 定义的三层边界：圣经层 / 管控层 / 自管理层 / 归档层。新对话先读短入口，再按任务线渐进加载源文档。

## 1. 当前定位

`Loomstead` 是一个 **narrative-primary 的可解释多 Agent 叙事运行时与研究环境**：通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，研究 Director 如何以 Motivational Delegation 间接驱动少量深度 NPC 朝过程约束目标演化，并用 Process Fidelity Eval 验证过程可信度。差异化主轴：**少而深 + 可解释 + 可评估**。小镇是 primary validation domain，跨域任务环境只作 secondary validation。

## 2. 新对话最小读取顺序

1. `npm.cmd run context:resume`：分支、脏区、manual gate、最近下一步与最小验证命令。
2. [`../AGENTS.md`](../AGENTS.md)：跨助手指令入口与开发风格硬约束。
3. [`context_governance.md`](./context_governance.md)：三层文档边界、改动权限、checkpoint 机制。
4. [`agent_context.md`](./agent_context.md)：当前边界、命令和最近下一步。
5. [`phase_checkpoints.md`](./phase_checkpoints.md)：当前阶段位置与下一阶段候选。
6. [`current_status.md`](./current_status.md)：当前实现事实、缺口与人工验收清单。
7. [`assistant_continuity.md`](./assistant_continuity.md)：跨家里 / 公司、多助手、子代理接续协议。

## 3. 文档分层

### 圣经层 Canon（不得自行修改）

- [`project_vision.md`](./project_vision.md)：产品愿景、差异化主轴、成功标准。
- [`research_framing_motivational_delegation.md`](./research_framing_motivational_delegation.md)：研究定位、核心反论点、baseline matrix。
- [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md)：Process Fidelity 指标与 Eval 验收线。
- [`cross_domain_adapter.md`](./cross_domain_adapter.md)：跨域 adapter 接口契约。
- [`world_entity_model.md`](./world_entity_model.md)：世界实体 schema 契约。
- [`agent_loop_architecture.md`](./agent_loop_architecture.md)：NPC agent loop 设计源（含工程清单待清理，过渡期暂入圣经层）。

### 管控层 Governed（可起草，主人审核）

- [`context_governance.md`](./context_governance.md)：治理协议本体。
- [`production_roadmap.md`](./production_roadmap.md)：阶段路线与 exit criteria。
- [`phase_checkpoints.md`](./phase_checkpoints.md)：推进 checkpoint 板。
- [`open_questions.md`](./open_questions.md)：决策记录与待解问题。
- [`../paper/claim_policy.md`](../paper/claim_policy.md)、[`../paper/claim_evidence_matrix.md`](../paper/claim_evidence_matrix.md)：论文 claim 政策与矩阵。

### 自管理层 Working（可自主更新，软上限 250 行）

- [`agent_context.md`](./agent_context.md)：新对话第一入口。
- [`current_status.md`](./current_status.md)：当前实现事实。
- [`assistant_continuity.md`](./assistant_continuity.md)：跨助手接续协议。
- [`workflows.md`](./workflows.md)：workflow 索引。
- [`demo_capture_plan.md`](./demo_capture_plan.md)：求职展示线 60 秒录屏脚本与人工验收边界。
- [`eval_dataset_archive.md`](./eval_dataset_archive.md)：Eval 归档操作流程。
- [`eval_reviewer_sampling_packet.md`](./eval_reviewer_sampling_packet.md)：Reviewer packet 操作流程。
- [`model_profile_template_guide.md`](./model_profile_template_guide.md)：模型 profile 配置流程。
- [`art_direction.md`](./art_direction.md) / [`asset_generation_prompts.md`](./asset_generation_prompts.md) / [`map_sprite_style_guide.md`](./map_sprite_style_guide.md)：资产线操作准则。
- [`game_client_environment.md`](./game_client_environment.md)：Godot 本机环境备忘。
- `asset_batches/`：批次计划与 prompt_ready 导出。

### 归档层 Archive

[`archive/`](./archive/README.md) 仅供历史溯源，不作为当前事实源。重定位前的多 Agent 系统设计、游戏本体架构、内容剧情、NPC 深度卡 schema 等已归档；如需复活结论，必须先在新核心文档显式吸收。

## 4. 按开发线读取

### 后端 / Director / Event Skill / Agent Loop
- [`agent_loop_architecture.md`](./agent_loop_architecture.md)
- [`world_entity_model.md`](./world_entity_model.md)

### Godot 客户端
- [`production_roadmap.md`](./production_roadmap.md)
- [`game_client_environment.md`](./game_client_environment.md)
- [`demo_capture_plan.md`](./demo_capture_plan.md)
- [`../clients/godot/README.md`](../clients/godot/README.md)

### LLM / Debug / Eval
- [`model_profile_template_guide.md`](./model_profile_template_guide.md)
- [`agent_loop_architecture.md`](./agent_loop_architecture.md) §10 Eval Framework
- [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md)
- [`eval_dataset_archive.md`](./eval_dataset_archive.md)

### 研究 framing / 跨域 adapter
- [`research_framing_motivational_delegation.md`](./research_framing_motivational_delegation.md)
- [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md)
- [`cross_domain_adapter.md`](./cross_domain_adapter.md)

### 内容 / NPC
NPC 深度卡的 schema 与数据已落到 `backend/app/content/`；旧设计文档已归档至 [`archive/npc_deep_card_spec.md`](./archive/npc_deep_card_spec.md) 与 [`archive/game_content_storyline.md`](./archive/game_content_storyline.md)。

### 资产管线
- [`art_direction.md`](./art_direction.md)
- [`asset_generation_prompts.md`](./asset_generation_prompts.md)
- [`map_sprite_style_guide.md`](./map_sprite_style_guide.md)
- `asset_batches/`

### 上下文治理 / 助手适配
- [`../AGENTS.md`](../AGENTS.md)、[`../CLAUDE.md`](../CLAUDE.md)、[`../.claude/rules/`](../.claude/rules/)
- [`context_governance.md`](./context_governance.md)、[`assistant_continuity.md`](./assistant_continuity.md)、[`workflows.md`](./workflows.md)
- [`../scripts/build_agent_context.py`](../scripts/build_agent_context.py)

## 5. 维护建议

- 自管理层文档保持短、准、可执行，不写历史 changelog。
- 长期愿景与阶段事实冲突时，先更新事实文档，再决定是否需要修订愿景或规格。
- 治理协议或文档边界调整后建议运行：

```powershell
npm.cmd run context:check
git diff --check
```
