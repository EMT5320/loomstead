---
status: active
owner_lane: context-governance
last_verified: 2026-05-26
startup_load: first-read
source_of_truth: true
scope: new-session entrypoint, boundaries, commands, and next steps
---

# Loomstead 新对话入口

> 更新时间：2026-05-26（上下文治理收缩，新增 `context:resume` 接续入口）
> 用途：新对话、跨机器切换、子代理任务和多助手接手时的第一入口。

## 1. 启动路线

- 首选运行 `npm.cmd run context:resume`，用短摘要确认分支、脏区、当前阶段、manual gate 和最小验证命令。
- 只做项目定位时读本文；需要事实核对时读 `docs/current_status.md`；需要深入实现时按开发线读取源文档。
- 长期方向以 `docs/project_vision.md` 为准；研究 framing 以 `docs/research_framing_motivational_delegation.md` 为准。
- NPC agent loop 设计以 `docs/agent_loop_architecture.md` 为准；世界实体 schema 以 `docs/world_entity_model.md` 为准。
- Eval 与跨域验证以 `docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`、`docs/eval_dataset_archive.md` 为准。
- 跨助手接续协议见 `docs/assistant_continuity.md`；既有 workflow 索引见 `docs/workflows.md`。
- 历史草案和旧 handoff 在 `docs/archive/`，通常不作为当前事实源。

## 2. 一句话定位

`Loomstead` 是一个 narrative-primary 的可解释多 Agent 叙事运行时与研究环境：通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，研究 Director 如何以 Motivational Delegation 间接驱动少量深度 NPC 朝过程约束目标演化，并用 Process Fidelity Eval 验证过程是否可信。

## 3. 当前状态摘要

- Phase 1（活着的世界）已收口；`world_main.tscn` 是当前完成基线，旧 `LifeActionExecutor` 只保留回归修复。
- Phase 2（骨架建立期）首轮已落地，当前主线是 trace / eval 收紧和可解释证据复用。
- 后端权威路径已切到 `MotivationEngine -> ToolExecutor -> ResultObserver`，`/api/world/tick`、`/api/debug.phase2`、`phase2.trace.v1` 和 `schema_registry.v1` 是核心观察入口。
- Process Fidelity Eval 已包含 rule process suite、stability / determinism、memory / relationship ablation、counterfactual replay、domain adapter suite 和 eval archive manifest。
- Godot Research Dock 已接入 Phase 2 debug 摘要、trace timeline、source chip 跳转、Copy 当前 trace JSON、NPC 高亮和三 Tab UI；代码与离线验证已完成，source chip / Copy trace 仍待真实窗口最终人工验收。
- Web Debug 已有 provider / fallback / cost 总览、Heuristic Library、Arbitration Trace 和 Rashomon Memory 三卡片。
- 6 名首发 NPC 深度卡已入库；4 核心 NPC（kai / mira / bram / lena）已有实际 motivation / capability / heuristic seed，tomas / orren 保持 stub。
- 资产 manifest 登记 55 条资产；表情差分、行动反馈图标和生活行动 UI 小组件仍是 `prompt_ready` backlog。

## 4. 当前边界

- 后端持有权威世界状态；Godot 只做表现、本地交互缓存和 API 调用。
- LLM 输出进入可见结果前必须经过解析、规则校验、fallback 和事件记录。
- 密钥只放 `config/models.local.json`、`config/models.json` 或环境变量，不写入仓库。
- 常规 `check` / `smoke` 不访问真实 LLM；真实 provider 证据由 `npm.cmd run llm:smoke` 单独刷新。
- Godot headless / dry-run 不等于真实窗口手感验收；真实窗口行为需要人工记录。
- 新增 schema、事件字段、Debug 字段、eval artifact 或 Godot 消费字段前，先明确数据契约。

## 5. 最近下一步

- 先完成真实 Godot 窗口验收：`memory.result_observed` 行、source chip 跳转、NPC 高亮、Copy 当前 trace JSON、非全屏滚动和弹层关闭。
- 通过 trace 体验验收后，优先转入 Eval 线：继续加深真实依赖图、跨文件回归、review agent 分歧和 dependency evidence chain。
- Godot 线后续只保留 detail 文案、快捷键和手感 polish；不要重新扩 Phase 1 旧玩法线。
- 切换模型、key、profile 或需要刷新真实成本证据时，再单独运行 `npm.cmd run llm:smoke`。
- 资产线按 `docs/asset_batches/prompt_ready_export.md` 推进，但先按 `docs/open_questions.md` 的资产范围调整重新评估优先级。

## 6. 按开发线读取

- 后端 / Agent Loop：`docs/agent_loop_architecture.md`、`docs/world_entity_model.md`、`backend/app/runtime/`、`backend/app/tools/`、`backend/app/memory/`。
- Eval / Research：`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`、`backend/app/eval/`、`backend/app/domain/`、`scripts/run_agent_eval.py`。
- Godot 客户端：`docs/gameplay_system_architecture.md`、`docs/game_client_environment.md`、`clients/godot/README.md`、`clients/godot/`。
- Content / NPC：`docs/game_content_storyline.md`、`docs/npc_deep_card_spec.md`、`backend/app/content/`。
- LLM / Debug：`docs/model_profile_template_guide.md`、`config/`、`backend/app/providers/`、`frontend/`、`GET /api/debug.phase2` 消费侧。
- 资产：`docs/art_direction.md`、`docs/asset_generation_prompts.md`、`docs/map_sprite_style_guide.md`、`assets/manifests/asset_manifest.json`。
- 上下文治理：`AGENTS.md`、`CLAUDE.md`、`docs/assistant_continuity.md`、`docs/workflows.md`、`scripts/build_agent_context.py`。

## 7. 验证命令

- 接续摘要：`npm.cmd run context:resume`。
- 收工交接：`npm.cmd run context:handoff`。
- 上下文治理：`npm.cmd run context:check; git diff --check`。
- 常规离线门禁：`npm.cmd run check; npm.cmd run smoke`。
- 后端 trace / schema：`npm.cmd run schema:check`。
- Eval：`npm.cmd run eval:process; npm.cmd run eval:stability; npm.cmd run eval:stability:determinism; npm.cmd run eval:domain`。
- Eval archive：`npm.cmd run eval:archive:check; npm.cmd run eval:archive:drift`。
- Godot 环境：`npm.cmd run client:env; npm.cmd run client:run:check`。
- 内容 / 资产：`npm.cmd run content:check; npm.cmd run asset:check`。
- 真实 LLM：`npm.cmd run llm:smoke`，只在 provider / key / profile / prompt 或真实证据刷新任务中运行。

## 8. 协作约束

- 状态更新必须区分 `code integrated`、`command checked`、`manual verified`、`manual unverified`。
- 修改 `docs/current_status.md`、`docs/agent_context.md` 等治理入口时保持短、准、可验证，不复制源设计长文。
- 多子代理并行时避免同时修改治理入口；由主会话串行合并事实。
- 家里 / 公司切换时不要提交本机绝对路径、私有 key、临时 overlay 或 `.run/` 中未整理 artifact。
