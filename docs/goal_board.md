---
status: active
owner_lane: planning
last_verified: 2026-05-21
startup_load: after-agent-context
source_of_truth: true
scope: lane board, collaboration notes, and recommended schedule
---

# Loomstead 目标看板

> 更新时间：2026-05-21（Phase 2 eval No Subjective Memory）
> 用途：为无人值守开发、并行子代理和下一轮收口提供状态、协作参考和验证命令。
> 2026-05-19 项目重定位为"可解释多 Agent 叙事运行时"，差异化主轴改为"少而深 + 可解释 + 可评估"。Phase 2-6 已重排，详见 `docs/production_roadmap.md`。

## 1. 状态标记

- `done`：本轮已核对，当前目标完成。
- `partial`：最小闭环已落地，仍有明确后续缺口。
- `blocked`：需要人工配置、真实窗口、API key 或上游资产后继续。
- `watch`：当前只读跟踪，暂不作为主线扩写。

## 2. 本轮验收证据

- `npm.cmd run check`：通过，包含 `[model-config] ok`、`[python-smoke] ok`、真实 `[llm-smoke]`、`[asset-manifest-check] ok`、`[npc-codex-check] ok (6 cards)`、`[motivation-target-check] ok`、`[godot-check] ok`；2026-05-21 本轮 cloud smoke 的 dialogue / event_reaction / night_reflection 均为 `deepseek-v4-flash` 且 `fallbackReason=None`。
- `npm.cmd run content:check`：通过，6 份 NPC 深度卡结构、关系阶段、unlock 引用、Phase 2 schema 占位与资产引用 warning 检查通过。
- 历史真实 `llm-smoke` 实测概要：dialogue 3744 tokens / 10446ms / 0.00041262 USD；event_reaction 6302 tokens / 4876ms / 0.00079765 USD；night_reflection 18514 tokens / 6418ms / 0.0024811 USD。2026-05-21 本轮最终刷新概要：dialogue 3370 tokens / 5188ms / 0.0003058 USD；event_reaction 6317 tokens / 4909ms / 0.00079877 USD；night_reflection 18659 tokens / 6836ms / 0.00251876 USD。
- `npm.cmd run client:env`：通过，Godot 4.6.2 headless 项目打开检查通过。
- `npm.cmd run client:run:check`：通过 DryRun，当前默认运行入口指向 `world_main.tscn`。
- Godot headless `world_main.tscn` 加载：通过，已加载 3 张地点背景和 6 张 NPC `map_idle` 小人贴图，日志未出现脚本解析错误或资源加载错误。
- `world_main` 玩家闭环：代码已接入玩家 `map_idle`、WASD / 方向键移动、`Camera2D` 跟随、靠近 NPC 后 `E` 键提交后端 `talk`、`WorldVnPanel` 对话弹层；已通过 headless 加载，2026-05-21 主人确认 Phase 1 可以收口。
- `world_main` NPC 轨迹修复：已确认 Phase 1 lifeAction 目标从全员同指 `farm_house_door` 修正为可见 anchor 分布；`scripts/check_life_action_targets.py` 现覆盖 `motivation_plan.v1` morning / afternoon / evening 目标防回归；Godot 路径线改为低透明短暂调试线，同锚点 NPC 使用 crowd offset 分散站位。
- `world_main` 世界动态面板：新增 `WorldPulsePanel`，启动时读取 `/api/world/state` 的 `activeEvents` 与 `npcSchedules`，tick 时读取 `clock/events/agents` 更新 NPC 当前移动或行动状态；Godot headless 加载通过，作为 Phase 1 完成基线冻结维护。
- `world_main` 远处事件提示：active event 会在事件锚点生成地图 beacon；玩家不在事件场景时，顶部 `RemoteEventCompass` 显示方向、地点和事件名；Godot headless 加载通过，作为 Phase 1 完成基线冻结维护。
- `npm.cmd run client:run:legacy:check`：通过 DryRun，旧 P0 UI 可通过 `res://scenes/main.tscn` 回看。
- Godot headless import / quit：通过，脚本可加载；退出时仅出现 Godot ObjectDB leak warning。
- 真实 Godot 窗口：2026-05-16 主人已人工验收上一版基础体验；2026-05-17 主人确认点击移动已正常；2026-05-21 主人确认 Phase 1 可以收口。
- 本轮并行开发收口：`py_compile`、`content:check`、`smoke`、强制真实 LLM smoke、`check`、`asset:check`、`context:check`、`check_godot_project.py`、prompt_ready 导出、仓库外导出、Godot headless import、Godot headless quit、`client:env`、`client:run:check`、`git diff --check` 已通过。
- 历史真实 LLM smoke 曾使用 `deepseek-v4-flash` 跑通；2026-05-21 本轮真实 cloud smoke 已恢复，离线 fallback 路径仍由普通 smoke 覆盖。
- `npm.cmd run asset:check`：通过。
- `npm.cmd run context:check`：通过，校验共享代理入口、核心文档元信息和任务线路由路径。
- `git diff --check`：通过。
- 白天后端 agent 线已合并到 `main`：`a61a16c merge: integrate day backend agent line`。
- 白天美术资产线已合并到 `main`：`6e77406 merge: integrate day art asset line`。
- Godot 新 sprite `.import` 元数据已提交：`1de91f6 chore: import Godot map sprite metadata`。
- 2026-05-20 研究 framing 增补已落地并通过 `npm.cmd run context:check`：新增 `docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`；`project_vision.md` / `production_roadmap.md` / `agent_loop_architecture.md` / `docs/README.md` / `AGENTS.md` / `docs/agent_context.md` / `docs/current_status.md` 已同步；`scripts/build_agent_context.py` 与 `.claude/rules/backend.md` 死链已修复。
- Phase 2 第二刀已验证：`NeedAccumulator -> MotivationEngine -> ToolExecutor -> ResultObserver` 最小链路可在 tick 后产生 `tool.execution_completed` / `memory.result_observed`，`GET /api/debug.phase2` 已暴露 needAccumulator、subjectiveMemory、relationshipEdges、heuristics、`traceSchemaVersion=phase2.trace.v1` 和 `recentTraceEvents`。
- `npm.cmd run eval:rule`：通过，输出 Full / Hard Delegation / No Relationship Edge 三组 `l1_rule_pass_rate`，均为 `mean=1.0 std=0.0 n=5`，并包含 `ablation_comparison`。
- `npm.cmd run eval:process`：通过，新增 No Subjective Memory；Full baseline 的 `goal_success_rate / required_process_coverage / causal_trace_coverage / process_believability_score / relationship_memory_causal_use_rate` 均为 `mean=1.0 std=0.0 n=3`；No Subjective Memory 的 `required_process_coverage=0.8`、`relationship_memory_causal_use_rate=1.0`、`process_believability_score=0.96`；Hard Delegation / No Relationship Edge / Shuffled Memory Owner / Evidence-Link Removal 的 `relationship_memory_causal_use_rate` 均为 `0.0`。
- `npm.cmd run eval:process:export`：通过，示例输出目录 `.run\eval-runs\run_2026-05-21T15-45-31Z`；导出包含 `counterfactual_replay.jsonl` 与 `memory_ablation_trace.jsonl`（`.run/` 为本地忽略目录）。
- `npm.cmd run eval:stability`：通过，规则版 AgentRuntime 连续 24 游戏小时稳定推进，`ticksCompleted=24`、`completedToolCount=144`、`failedToolCount=0`、`trace_schema_coverage=1.0`、`active_agent_count=6`、`relationship_edge_count=19`。
- `npm.cmd run eval:stability:export`：通过，示例输出目录 `.run\eval-runs\stability_2026-05-21T15-01-19Z`；导出包含 `stability_trace.jsonl` 与 `final_evidence.json`（`.run/` 为本地忽略目录）。
- Godot 观察者面板检查通过：`python scripts/check_godot_project.py`、`npm.cmd run client:run:check` 已覆盖 Tab 面板与 `/api/debug.phase2` 客户端读取路径；Godot headless quit 仍按既有非阻塞 ObjectDB warning 处理。

## 3. 本轮收口状态

### 已完成

- 文档治理入口已落地：`docs/agent_context.md`、`docs/goal_board.md`、`docs/current_status.md`、`docs/open_questions.md`。
- 规则版 Director v0 最小闭环已落地并由 smoke 覆盖。
- 单个星灯祭 Event Skill schema / registry 已落地。
- 星灯祭玩家画像证据模板与事件反应记忆模板已迁入 Event Skill 数据层。
- LLM profile、provider fallback 和 Debug 字段记录路径已落地。
- Godot P0 客户端已接入背景、neutral 立绘、NPC 选择和聊天提交。
- Godot 地图角色层已接入：玩家 + 6 NPC 小人、talk / gift / event marker、NPC 点击入口均已进入主场景。
- Godot 本地移动与靠近反馈已接入：WASD 独立连续移动、地图层直接点击当前场景空地落点、落点标记、单个最近交互目标高亮和 MapMoveHint。
- Godot 玩家出生点已和 NPC 比例站位槽分离，交互半径已收紧，降低重叠卡住和高亮抖动概率。
- Godot 点击落点会自动修正到可行走边界，地图 bounds 已随窗口动态放宽，玩家出生点已从底部边缘上移，靠近目标加入退出滞回，NPC 小人不再因非最近目标整体禁用。
- Godot 地图角色层已按当前场景过滤 NPC / event marker，玩家移动范围已扩大到舞台主体区域。
- Godot 地图输入已补点击穿透与焦点收紧：背景、顶层空白容器和标签不吃鼠标，按钮/marker 不接管键盘焦点。
- Godot 角色小人淡黄色矩形背景已移除，选中或靠近状态改用 sprite tint 与 marker 状态表达。
- Godot 事件交互代码已接入：`activeEvents` 事件区、`inspect` 查看、choices 渲染、`attend_event` 提交、VN 结果展示。
- Godot `AssetRegistry` 已接入星灯祭事件 CG，并支持 `happy` / `troubled` 表情回退到 `neutral`。
- 资产 manifest 和 Godot registry 已覆盖首批背景、事件 CG 与 neutral 立绘。
- Debug / Memory / influence HTTP 查询 API 已纳入 smoke 覆盖。
- `monologueSeeds` 已接入夜间反思上下文、compact memory evidence 和规则 fallback。
- `gossipHooks` 已接入内容校验、对话 `gossipEvidence` 选择、传播草案、选择理由、`candidateDebugSummary`、validator、运行时 `gossip.propagation_validated` 事件和 smoke 断言。
- 7 张地图小人和 3 张交互标记已进入 manifest、资产目录和 Godot 资源镜像。
- 首发 6 名 NPC 深度卡已入库：`kai`、`bram`、`mira`、`tomas`、`orren`、`lena`。
- NPC 内容工作流已落地：`.windsurf/workflows/author-npc-deep-card.md`。
- 多助手共享入口已落地：`AGENTS.md` 与导入它的 `CLAUDE.md`。
- 2026-05-20 研究 framing 增补已落地：Phase 2 骨架增加 ResearchFraming / DomainAdapter / ProcessFidelityEval 三项，收口标准新增 Hard Delegation baseline 与关系记忆 ablation 硬验收；phase2_research_addendum patch notes 已归档。
- 2026-05-21 Phase 1 收口确认：主人确认 Phase 1 可以收，默认 `world_main` 进入完成基线；Phase 2 骨架建立期启动。
- 2026-05-21 NPC 深度卡 Phase 2 schema 占位已落地：6 张卡均新增 `motivationProfile` / `capabilityPreferences` / `heuristicSeeds` 字段，实际内容 Phase 3 再填。
- 2026-05-21 Phase 2 后端记忆因果主干已落地：NeedAccumulator、ResultObserver / BiasFilter、RelationshipEdgeStore、HeuristicLibrary 最小骨架接入 Runtime，并进入 Debug snapshot。
- 2026-05-21 Eval baseline 第二刀已落地：Hard Delegation baseline、No Relationship Edge ablation 和 `ablation_comparison` 已接入 `eval:rule`。
- 2026-05-21 Process Fidelity Eval 第一刀已落地：`eval:process` 输出 3 个 GoalSpec、10 项指标、Full / Hard / No Relationship Edge 对照和 `.run/eval-runs` 本地导出。
- 2026-05-21 Process Fidelity Eval 第二刀已落地：关系边进入 Arbitration 评分输入，`eval:process` 通过 Counterfactual Replay 验证 `relationship_memory_causal_use_rate=1.0`，并导出 `counterfactual_replay.jsonl`。
- 2026-05-21 Process Fidelity Eval 第三刀已落地：Shuffled Memory Owner 与 Evidence-Link Removal 进入 process baseline，`memory_ablation_trace.jsonl` 可导出 owner / source evidence 反事实证据。
- 2026-05-21 Process Fidelity Eval 第四刀已落地：No Subjective Memory 进入 process baseline，`subjective_memory_refs=false` 时 `required_process_coverage=0.8`，关系记忆因果使用仍为 `1.0`。
- 2026-05-21 Eval stability 第一刀已落地：`eval:stability` 连续推进 24 游戏小时并验证 tick、trace、memory observation、relationship edge 与多 NPC 参与。
- 2026-05-21 Godot 观察者最小骨架已落地：`ObserverPanel` 支持 Tab 显隐、点击 NPC / `E` talk 选中和 NPC 占位信息展示。

### 部分完成

- Content Codex 首批数据已可用；`monologueSeeds` 已接入夜间反思/RAG，`gossipHooks` 已进入对话证据选择、传播草案、validator 和运行时校验事件，`lifeActionSeeds` / `dailyRumorBeats` / `relationshipBeatSeeds` 已进入 `npcSchedules` / `lifeActionPlan` 快照，Phase 2 schema 占位已完成；实际动机权重和启发式内容等 Phase 3 再填。
- Phase 2 骨架尚未完成：ToolDefinition / MotivationEngine / CapabilityRegistry / SubjectiveMemoryStore / HeuristicLibrary / ArbitrationLayer / EvalFramework / Godot 观察者模式已有最小闭环；仍需补完整 Process Fidelity 指标、关系记忆专项 scenario、旁观者可见性、启发式衰减 / 冲突处理、trace span 串联和 Godot 面板真实窗口验收。
- Godot Phase 1 已从 UI demo 推进到可移动舞台层，并已接入地图上下文候选、快捷键执行、服务端锚点、生活场景行动和行动反馈；Phase 2 缺口转为观察者模式与 Debug 信息面板。
- Event Skill 仍只有星灯祭单技能，部分结算逻辑仍有 Runtime 硬编码。
- LLM profile 可配置，Web 观察台已追加配置查看、热重载和对话 smoke 入口；2026-05-21 本轮真实 cloud smoke 已恢复，切换模型、key 或 profile 后需要刷新真实证据。
- 资产批次完成到首批背景、事件 CG、neutral 立绘、地图小人候选和交互标记；24 条 `prompt_ready` 已拆成 3 个导出批次，表情差分、行动反馈图标和生活 UI 小组件尚未生成入库。

### 阻塞项

- 真实 LLM 验证当前已恢复；后续切换模型、key 或 profile 后仍需重新跑 smoke。
- 表情差分、UI 组件、道具图标和行动反馈图标需要继续生成和人工筛选。
- 地图小人的资产晋级状态需要主人给出筛选结论。

## 4. 开发线看板

| 开发线 | 当前状态 | 下一步 | 主要写入范围 | 注意事项 | 验收命令 |
| --- | --- | --- | --- | --- | --- |
| Phase 1 sprint · 活着的世界 | done | 2026-05-21 主人确认 Phase 1 可以收口；`world_main.tscn` + tick 闭环 + NPC 移动/行动 + HUD + `E` talk + `WorldPulsePanel` + 远处事件提示进入完成基线 | Phase 1 代码只做回归修复 | Phase 1 旧线以回归维护为主；Phase 2 直接切 MotivationEngine | `npm.cmd run client:env`、`npm.cmd run client:run:check`、`npm.cmd run check` |
| Phase 2 skeleton · 骨架建立期 | partial | 当前启动中；NPC 深度卡 schema 占位已补；ToolDefinition / NeedAccumulator / MotivationEngine / CapabilityRegistry / ArbitrationLayer / ToolExecutor / ResultObserver / SubjectiveMemoryStore / RelationshipEdgeStore / HeuristicLibrary / Eval L1 + Process Fidelity suite / Counterfactual Replay / memory ablation / 24h stability / `phase2.trace.v1` / Godot 观察者 debug 摘要面板已接入 tick 与 Debug；下一步补 trace span 串联、跨域 GoalSpec 和真实窗口验收 | `backend/app/tools/`、`backend/app/runtime/`、`backend/app/memory/`、`backend/app/world/entities/`、`backend/app/domain/`、`backend/app/eval/`、`scripts/run_agent_eval.py`、`clients/godot/scripts/ui/observer_panel.gd` | 旧 `LifeActionExecutor` 不再服务 tick 主路径；关系/记忆最终状态通过 ToolExecutor + ResultObserver；Eval 跟随骨架同步推进；当前 `relationship_memory_causal_use_rate=1.0` 已由反事实回放验证，No Subjective Memory 会让过程覆盖降至 0.8，owner/source ablation 会让关系因果使用降为 0.0，24 游戏小时稳定性已通过 | `npm.cmd run content:check`、`npm.cmd run smoke`、`npm.cmd run eval:rule`、`npm.cmd run eval:process`、`npm.cmd run eval:stability`、`npm.cmd run check` |
| Godot 玩法客户端 | partial | Phase 1 主玩法入口完成；Phase 2 观察者面板已读取后端 motivation / subjectiveMemory / relationshipEdges / heuristics 摘要；下一步补 recentTraceEvents 展开和真实窗口体验验收 | `clients/godot/`、必要时 `scripts/check_godot_project.py` | 客户端保持表现和输入层定位；后端保留权威结算规则 | `npm.cmd run client:env`、`npm.cmd run client:run:check`、`npm.cmd run check` |
| Content Codex / NPC 深度卡 | partial | `monologueSeeds` / `gossipHooks` / `lifeActionSeeds` 已接入；`motivationProfile` / `capabilityPreferences` / `heuristicSeeds` 空占位已落地；实际 4 核心 NPC 数据 Phase 3 填 | `backend/app/content/`、`scripts/check_npc_codex.py`、相关 docs | 内容卡提供素材和偏好，不直接落权威世界状态；资产 id 保持来源清晰；Phase 2 侧重 schema 维护 | `npm.cmd run content:check`、`npm.cmd run check` |
| 后端 Director / Event Skill | partial | 单星灯祭 Skill 与 Director v0 已可用；Phase 2 重点转向 Tool / Motivation / Memory / Eval 骨架，事件结算硬编码迁移后置 | `backend/app/director/`、`backend/app/skills/`、必要 `backend/app/runtime/agent_runtime.py` | LLM 输出保持文本、建议或工具意图；世界状态变更经 Runtime；旧 `/api/state` 与 Debug 观察台兼容性仍有价值 | `npm.cmd run smoke`、`npm.cmd run check` |
| 资产管线 | partial | 24 条 `prompt_ready` backlog 已登记并导出到 `docs/asset_batches/prompt_ready_export.md`，下一步生成并筛选表情差分、生活 UI 组件和行动反馈图标；地图小人晋级等待主人筛选 | `assets/source/`、`assets/processed/`、`assets/manifests/`、`docs/asset_batches/`、`clients/godot/assets/` | 保留原图和来源信息；人工确认状态保持清晰；晋级到 `source_selected` 前需要筛选证据 | `npm.cmd run asset:check`、`python scripts/export_prompt_ready_assets.py`、`npm.cmd run check` |
| LLM / Debug | partial | 当前离线 fallback 正常；2026-05-21 本轮真实 cloud smoke 已恢复；后续切换 key / profile 后用 `AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE=1` 刷新 dialogue / event_reaction / night_reflection 证据 | `backend/app/providers/`、`backend/app/providers/context_builder.py`、Debug 记录结构、迁移期 `frontend/`、相关 docs | 密钥保留本地；token、延迟、错误和 fallback 状态保留 Debug 证据；live smoke 与 fallback 证据分开标注 | `npm.cmd run model:check`、`npm.cmd run smoke`、真实 LLM 手动记录 |
| Web Debug Console | watch | 等事件 UI 和 Skill 链路更稳定后展示 Director 队列、Skill、fallback、成本 | 迁移期 `frontend/`，后续 `web-admin/` | 调试台不阻塞 Godot 主体验；玩家叙事视角与研究视角分离 | `npm.cmd run check` |
| 文档与治理 | done | 常态维护入口、状态、下一步和仍需验证问题 | `AGENTS.md`、`CLAUDE.md`、`docs/README.md`、`docs/agent_context.md`、`docs/goal_board.md`、`docs/current_status.md`、`docs/open_questions.md`、`scripts/build_agent_context.py` | 保持短入口；未验证能力留在缺口或待验证项 | `npm.cmd run context:check`、`npm.cmd run check`、`git diff --check` |

## 5. 人工验收状态

2026-05-16 主人已完成上一版真实 Godot 窗口人工验收，基础体验基本无阻断问题。已覆盖地点切换、背景切换、NPC 选择、`talk` 提交、星灯祭事件查看、choices 与事件结算展示。

2026-05-21 主人确认 Phase 1 可以收口，默认 `world_main` 进入完成基线。后续人工验收重点转为 Phase 2 观察者模式真实窗口体验、表情差分、UI 组件和真实 LLM profile 切换。

## 6. 并行任务拆分建议

- Phase 2 backend worker：主要涉及 `backend/app/tools/`、`backend/app/runtime/`、`backend/app/memory/`、`backend/app/world/entities/`，下一步目标是补旁观者可见性、关系召回、启发式衰减 / 冲突和 trace span 串联。
- Eval worker：主要涉及 `scripts/run_agent_eval.py`、`backend/app/eval/`、`backend/app/domain/` 和必要测试夹具，下一步目标是在当前 Process Fidelity + Counterfactual Replay + memory ablation + 24h stability 输出基础上补跨域 GoalSpec 和更严格 trace dataset 归档。
- Godot observer worker：主要涉及 `clients/godot/` 和必要检查脚本，下一步目标是展开 recentTraceEvents、优化空态 / 错误态文案并做真实窗口验收。
- Content worker：Phase 2 侧重维护 schema 和校验；实际 motivationProfile / capabilityPreferences / heuristicSeeds 数据填充放 Phase 3。
- 资产 worker：主要涉及资产目录、manifest、`docs/asset_batches/` 和必要 Godot asset mirror，目标是按批生成表情差分、生活 UI 组件和行动反馈图标。
- Reviewer：以核对契约、过标表述、验收输出和工作区状态为主。

多 worker 并行时，建议避免同时修改 `docs/current_status.md`、`docs/agent_context.md`、`docs/goal_board.md`。

## 7. 协作信息参考

后续协作中通常有用的信息包括触达的开发线、主要文件、实际验证命令、仍依赖人工或外部条件的验证点，以及自然的后续任务。

## 8. 下一轮推荐排程

### Phase 2 启动（最高优先级）

1. **后端骨架线**：完善 ResultObserver 可见性、RelationshipEdgeStore 召回、HeuristicLibrary 衰减 / 冲突和 trace span 串联。
2. **Eval 线**：在当前 Process Fidelity 指标族、关系记忆因果使用、Counterfactual Replay、memory ablation 与 24h stability 导出基础上补跨域 GoalSpec 和更严格 trace dataset 归档。
3. **Godot 观察者线**：在当前 `/api/debug.phase2` 摘要面板上补 recentTraceEvents 展开、空态文案和真实窗口体验验收。
4. **Domain / WorldEntities 线**：继续补 `backend/app/domain/base.py` 与 `backend/app/world/entities/` 的接口完整度。
5. **Phase 1 旧线冻结**：`LifeActionExecutor` 已退出 tick 主路径；旧 simulation 代码只作历史回归参考，不扩写新玩法。

### 持续维持

10. LLM / Debug 在切换模型、key 或 profile 后刷新真实 smoke。
11. 资产线按新定位重新评估范围（详见 `open_questions.md` 末尾"资产路线的范围调整"）。
12. Web Debug 追加 Director / Skill / fallback 视图，Phase 2 后新增 Heuristic / Arbitration / 主观记忆对比视图。

早期白天整合交接快照已归档至 `docs/archive/daytime_integration_handoff.md`，仅供历史溯源。
