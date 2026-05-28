---
status: active
owner_lane: context-governance
last_verified: 2026-05-28
startup_load: first-read
source_of_truth: true
scope: new-session entrypoint, boundaries, commands, and next steps
---

# Loomstead 新对话入口

> 更新时间：2026-05-28（Eval robustness strict gate / 分域签名已接入；Godot 最新窗口复验暂缓到展示层集中处理）
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
- 后端权威路径已切到 `MotivationEngine -> ToolExecutor -> ResultObserver`，`/api/world/tick`、`/api/debug.phase2`、`phase2.trace.v1` 和 `schema_registry.v1` 是核心观察入口；arbitration `candidateScores` 已输出组件级来源和解释引用。
- CapabilityRegistry 已从 legacy tool-prefix 路由推进到 `ToolDefinition.served_needs` 显式需求匹配，并保留 legacy fallback；`scripts/check_capability_served_needs.py` 已进入 `npm.cmd run check`。
- Process Fidelity Eval 已包含 rule process suite、stability / determinism、memory / relationship ablation、counterfactual replay、domain adapter suite、evidence robustness suite 和 eval archive manifest；process suite 最新 clean five-repeat rule export 为 20/20；coding adapter 当前 8 个 fixture，已覆盖源码派生依赖图、dependency evidence chain v2、跨文件回归、reviewer judgment arbitration 和 `coding.domain_counterfactual_replay.v1`；narrative adapter 已接入 `narrative.domain_counterfactual_replay.v1`，domain suite 最新 clean deterministic five-repeat export 为 55/55，aggregate counterfactual mean 为 `0.645238`、town mean 为 `0.333333`；robustness 已升级为 strict gate，manifest scenarioIds 已覆盖 process / coding / narrative 场景，最新 clean five-seed export `.run/eval-runs/robustness_2026-05-28T03-08-43Z` 为 300/300 source perturbation checks，coding / narrative 分域 invariance rate 均为 `1.0`，并已 promote 为 regression 候选（`needs_manual_review` 仅因 drift policy 要求说明 scenario/gate 摘要变化）。
- Godot Research Dock 已接入 Phase 2 debug 摘要、trace timeline、来源跳转按钮、Copy trace JSON、Trace Copy 空态 / tooltip / 成功反馈、Phase 2 Debug 错误提示、Prev/Next 循环导航、单条 trace 提示、`[C]` / `[,]` / `[.]` / 左右方括号热键、NPC 高亮和三 Tab UI；`memory.result_observed` 行与来源跳转可发现性已通过真实窗口复验，最新导航和中断布局补修仍待真实窗口复验。
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

- Eval 线已让 coding + narrative domain 的 counterfactual route replay 拉开指标，并支持 domain `--seeds`；`eval:robustness` 已接入 strict gate、manifest `evalGates`、scenarioIds 索引和 coding / narrative 分域签名，且已有 clean five-seed promoted regression 候选。下一步可接入 research claim review 或补 promotion drift 说明。
- Godot 线暂缓中间态 UI 迭代；真实窗口复验等后端 Agent / Eval 主线稳定后集中处理。
- Research 线已把 clean domain export `.run/eval-runs/domain_2026-05-27T13-29-21Z` 写入 claim / Table 5 入口，保持 interface evidence 口径。
- 不要重新扩 Phase 1 旧玩法线。
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
- Eval：`npm.cmd run eval:process; npm.cmd run eval:stability; npm.cmd run eval:stability:determinism; npm.cmd run eval:domain; npm.cmd run eval:robustness`。
- Eval archive / research evidence：`npm.cmd run eval:archive:check; npm.cmd run eval:archive:drift; npm.cmd run research:evidence:check`。
- Eval reviewer：`npm.cmd run eval:reviewer:packet -- --process-run run_2026-05-27T13-37-33Z --domain-run domain_2026-05-27T13-29-21Z`。
- Godot 环境：`npm.cmd run client:env; npm.cmd run client:run:check`。
- 内容 / 资产：`npm.cmd run content:check; npm.cmd run asset:check`。
- 真实 LLM：`npm.cmd run llm:smoke`，只在 provider / key / profile / prompt 或真实证据刷新任务中运行。

## 8. 协作约束

- 状态更新必须区分 `code integrated`、`command checked`、`manual verified`、`manual unverified`。
- 修改 `docs/current_status.md`、`docs/agent_context.md` 等治理入口时保持短、准、可验证，不复制源设计长文。
- 多子代理并行时避免同时修改治理入口；由主会话串行合并事实。
- 家里 / 公司切换时不要提交本机绝对路径、私有 key、临时 overlay 或 `.run/` 中未整理 artifact。
