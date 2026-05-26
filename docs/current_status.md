---
status: active
owner_lane: project-status
last_verified: 2026-05-26
startup_load: after-agent-context
source_of_truth: true
scope: current implementation facts, verification state, and work constraints
---

# 当前项目状态与开发前约束

> 状态更新时间：2026-05-26（真实窗口已确认 `memory.result_observed` 行与来源跳转按钮；下一阶段转入 Eval 证据链收紧）
> 本文记录当前仓库中已核对、命令已检或明确标注人工未验收的事实。长期方向见 `docs/project_vision.md`，研究 framing 见 `docs/research_framing_motivational_delegation.md`，Agent loop 设计见 `docs/agent_loop_architecture.md`。

## 1. 当前阶段判断

- 项目名：`Loomstead`。
- 当前定位：narrative-primary 的可解释多 Agent 叙事运行时与研究环境。
- 技术骨架：Godot 4.x 客户端 + Python Agent Server + Web Debug / 研究控制台。
- Phase 1（活着的世界）：done；2026-05-21 主人确认可以收口，默认 `world_main.tscn` 是完成基线。
- Phase 2（骨架建立期）：首轮骨架已落地，当前进入 trace / eval 收紧期。
- 当前差异化主轴：少而深 + 可解释 + 可评估。

## 2. 当前已验证事实

| 开发线 | 当前事实 | 仍需关注 |
| --- | --- | --- |
| 后端 Runtime / Director | Python Agent Server 是权威世界状态入口；已有 `GET /api/world/state`、`POST /api/player/action`、`POST /api/world/tick`、`GET /api/debug.phase2`；规则版 Director v0 与单个 Event Skill `event.starlight_festival_shortage` 已运行；Phase 2 tick 主路径已切到 `MotivationEngine -> ToolExecutor -> ResultObserver`；`motivation.decision_made`、工具完成 / 失败 / 中断、`memory.result_observed` 均带 trace 证据；`schema_registry.v1` 已集中治理主要 schema。 | 继续扩展 schema 迁移覆盖、失败模式、真实预算策略和更完整竞争上下文裁决；旧 `LifeActionExecutor` 只做回归修复。 |
| Eval / Research | `scripts/run_agent_eval.py` 已覆盖 rule process suite、stability、stability determinism、domain adapter suite；Process Fidelity Eval 包含 Hard Delegation、No Subjective Memory、No Relationship Edge、Shuffled Owner、Evidence-Link Removal、Branna Forgiveness fixture、Counterfactual Replay 和本地 export / archive manifest；coding domain adapter 已覆盖 8 类 repo fixture，并新增源码派生依赖图、`dependency_evidence_chain.v2`、跨文件回归 fixture 和 reviewer judgment 事件。 | Eval 是 Phase 2 硬验收线；继续加深 counterfactual / ablation 可拉开差距的证据，真实 cloud LLM 证据不进默认 CI。 |
| Godot 客户端 | `clients/godot/` 是 Godot 4.x 项目；默认主场景为 `res://scenes/world_main.tscn`；Phase 1 玩家移动、`E` talk、tick NPC 行动、远处事件提示和三场景拼图已收口；Research Dock 三 Tab 已读取 `/api/debug.phase2` 并展示 motivation、subjective memory、relationship edges、heuristics 与 trace timeline；`memory.result_observed` 行、来源跳转按钮、Copy 当前 trace JSON 和 NPC 高亮代码已落地。 | 主人已确认 UI 重设计后的整体观感、非全屏滚动、6 NPC 密度、遮挡风险修复，以及 `memory.result_observed` 可发现性和来源跳转按钮；Copy 当前 trace JSON、trace detail 文案和快捷键手感保留为后续 polish 验收。 |
| Web Debug / LLM | `RuleBasedProvider` 与 OpenAI-compatible `CloudApiProvider` 已接入；`config/models.example.json` 默认 rule fallback；Web Debug 已展示 provider / fallback / cost 总览、Heuristic Library、Arbitration Trace 和 Rashomon Memory。 | 最新成功真实 LLM smoke 是 2026-05-23；2026-05-24 曾触达 CloudApiProvider 但供应商返回 `HTTP 402 Insufficient Balance`，未刷新通过证据；切换 key / profile / prompt 后需单独跑 `npm.cmd run llm:smoke`。 |
| Content / NPC | 6 名首发 NPC 深度卡已入库；`voiceStyle`、`speechQuirks`、`monologueSeeds`、`giftReactions`、`gossipHooks` 已被 runtime / smoke 覆盖；4 核心 NPC（kai / mira / bram / lena）已有实际 motivation / capability / heuristic seed；tomas / orren 保持 stub。 | 谣言传播仍只记录校验结果，不写入世界状态、关系或记忆扩散；2 名 stub NPC 后续按剧情需要升级。 |
| 资产管线 | `assets/manifests/asset_manifest.json` 登记 55 条资产；3 张地点背景、星灯祭 CG、玩家 + 6 NPC 立绘、7 张地图小人和 3 类交互 marker 已进入 Godot；`AssetRegistry` 支持 happy / troubled 回退。 | 表情差分、行动反馈图标和生活行动 UI 小组件仍是 `prompt_ready` backlog；地图小人是否晋级 `source_selected` 仍需主人确认。 |
| 上下文治理 | `AGENTS.md`、`CLAUDE.md`、`docs/agent_context.md`、`docs/current_status.md`、`docs/README.md` 是基础入口；`docs/assistant_continuity.md` 和 `docs/workflows.md` 负责跨助手接续与 workflow 索引；`scripts/build_agent_context.py` 提供 `context:check` / `context:brief` / `context:resume`。 | 状态文档只记录当前事实和验证边界；长历史、过时 handoff 和旧看板留在 `docs/archive/`。 |

## 3. 最近核对结果

- 2026-05-26 Eval 线按顺序加深：dependency evidence chain 升级到 `coding.dependency_evidence_chain.v2`，fixture 源码派生 `derivedDependencyGraph`，新增 `coding.skill_cross_file_regression_dryrun`，reviewer disagreement 记录 `coding.reviewer_judgment_recorded` 后再进入 arbitration；`npm.cmd run eval:domain` 为 11/11，`npm.cmd run eval:domain:export` 生成 `.run/eval-runs/domain_2026-05-26T13-47-52Z`，artifactCount=65，`npm.cmd run eval:archive:check` 通过。
- 2026-05-26 真实 Godot 窗口复验发现 `memory.result_observed` 行和 source chip 可发现性不足：`memory.result_observed` 只藏在 detail `type` 字段里，source chip 外观像标签；已补显式行名、观察记忆提示、来源跳转按钮文案和聚焦状态提示，主人随后确认通过，可转入 Eval 证据链收紧阶段。
- 2026-05-26 上下文治理收缩：`docs/agent_context.md` 从长事实堆叠改为短入口；`docs/current_status.md` 聚焦当前事实、manual gate 和下一步；接续流程开始收敛到 `context:resume`。
- 2026-05-25 Trace 体验闭环代码已落地：`GET /api/debug.phase2` 支持 `focusEventId` / `focusTraceId`，`recentTraceEvents[]` 支持 `sourceLinks[]`，响应可返回 `traceFocus`；Godot Research Dock Trace detail 新增“证据链”chip，点击 source chip 会重拉 focus 并选中源事件；Copy trace 会复制当前 trace JSON。
- 2026-05-25 晚间 Godot 可读性补修已落地：NPC 一览双层行、集中字号 / 布局缩放和 Tab 底部滚动留白；主人随后确认非全屏滚动到底、6 NPC 密度和 HUD / TopBanner 遮挡风险修复。
- 2026-05-24 Round 2 已落地：Process Eval cloud / mixed provider 接入、Web Debug Phase 2 三卡片、跨域测试框架矩阵和 JavaScript smoke dry-run。
- 2026-05-24 stability 证据口径已收紧：24h / 72h stability 和 72h determinism 以硬门禁不变量为准，run-specific exact count 只记录在 artifact 中。

## 4. 开发前硬约束

- 后端 Runtime 是权威世界状态修改点；Godot 本地坐标只做表现，不写回权威世界。
- LLM 输出只生成文本、结构化建议或工具意图；世界状态变更必须经过 Runtime 规则、schema 校验和 fallback。
- 密钥、私有模型配置、本机绝对路径和临时 overlay 不写入仓库。
- 新增 API、事件类型、schema、eval artifact、Debug 字段或 Godot 消费字段前，先写清数据契约。
- 未由代码、命令或人工窗口验证的能力必须标注 `manual unverified` 或同等说明。
- Phase 2 直接使用 MotivationEngine；不并行扩写旧 `LifeActionExecutor`。

## 5. 人工验收与本机门禁

- `manual verified`：2026-05-21 主人确认 Phase 1 可以收口，默认 `world_main.tscn` 进入完成基线。
- `manual verified`：2026-05-25 主人确认 UI 重设计后整体观感与主路径无大问题。
- `manual verified`：2026-05-25 晚间主人确认 Research Dock 可读性补修，包括非全屏滚动到底、NPC 密度和遮挡风险。
- `manual verified`：2026-05-26 主人确认 Trace 时间线中 `memory.result_observed` 行可发现，来源跳转按钮可点击并可进入下一阶段。
- `manual unverified`：Copy 当前 trace JSON、trace detail 文案和快捷键逐项手感仍作为后续 polish 验收。
- `manual unverified`：真实 LLM 最新成功证据仍沿用 2026-05-23；2026-05-24 的真实 provider 尝试因 `HTTP 402 Insufficient Balance` 未形成通过证据。
- `manual unverified`：`prompt_ready` 资产尚未生成、筛选、登记源图或接入 Godot registry。

## 6. 当前可运行命令

```powershell
npm.cmd run context:resume
npm.cmd run context:check
npm.cmd run context:brief
npm.cmd run check
npm.cmd run smoke
npm.cmd run schema:check
npm.cmd run eval:process
npm.cmd run eval:stability
npm.cmd run eval:stability:long
npm.cmd run eval:stability:determinism
npm.cmd run eval:domain
npm.cmd run eval:archive:check
npm.cmd run eval:archive:drift
npm.cmd run content:check
npm.cmd run asset:check
npm.cmd run model:check
npm.cmd run client:env
npm.cmd run client:run:check
npm.cmd run llm:smoke
git diff --check
```

按任务线选择最小必要命令。真实 LLM、真实 Godot 窗口和玩家手感验收不属于默认离线门禁。

## 7. 下一轮建议

- Eval 线下一步继续强化 counterfactual / ablation 能拉开差距的场景证据，并把 `counterfactual_tool_selection_change_rate` 从干跑脚手架推进到更有区分度的样例。
- Godot trace 后续只保留 Copy 当前 trace JSON、detail 文案、快捷键和手感 polish。
- Godot 线后续以 detail 文案、快捷键和手感 polish 为主，不重开 Phase 1 旧玩法扩写。
- LLM / Debug 线只在切换模型、key、profile、prompt 或需要刷新真实成本证据时运行 `npm.cmd run llm:smoke`。
- 资产线按 `docs/asset_batches/prompt_ready_export.md` 推进前，先结合 `docs/open_questions.md` 的资产范围调整重新排序。
