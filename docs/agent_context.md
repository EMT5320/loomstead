---
status: active
owner_lane: context-governance
last_verified: 2026-05-22
startup_load: first-read
source_of_truth: true
scope: new-session entrypoint, boundaries, commands, and next steps
---

# Loomstead 新对话入口

> 更新时间：2026-05-22（Phase 2 JSON Schema subset）
> 用途：下一轮新对话、研究阶段开发和必要子代理任务的第一入口。

## 1. 当前入口

- 先读本文，再按任务线读取源文档。
- 长期方向以 `docs/project_vision.md` 为准（2026-05-19 重定位 + 2026-05-20 研究 framing 增补）。
- **研究 framing 源**：`docs/research_framing_motivational_delegation.md`（narrative-primary / Motivational Delegation / Process Fidelity Eval / baseline matrix）。
- **NPC agent loop 核心圣经**：`docs/agent_loop_architecture.md`（三层工具、动机系统、双轨记忆、启发式学习、仲裁、Eval）。
- **世界实体 schema**：`docs/world_entity_model.md`（FarmPlot / Item / Inventory / Shop / Building / Time / Weather + 工具空间）。
- **Process Fidelity Eval 规格**：`docs/process_fidelity_eval_spec.md`、**跨域 adapter 接口**：`docs/cross_domain_adapter.md`。
- 多层 Agent 系统设计：`docs/agentic_game_design.md`（Director / Skill / Memory / Model 分工）。
- 生产化阶段路线：`docs/production_roadmap.md`（Phase 1 done，Phase 2 骨架建立期首轮已落地，当前收紧 trace / eval）。
- 当前事实以 `docs/current_status.md` 为准；开发线源文档按任务读取。
- 前期并行开发看板 `docs/archive/goal_board.md` 已归档，仅供历史溯源。
- 视觉和资产细节见 `docs/art_direction.md`、`docs/asset_generation_prompts.md`、`assets/manifests/asset_manifest.json`。
- 历史草案、已归档文档统一放在 `docs/archive/`，通常不作为当前事实源。

## 2. 一句话定位（2026-05-19 重定位 + 2026-05-20 研究 framing 增补）

`Loomstead` 是一个 **narrative-primary 的可解释多 Agent 叙事运行时与研究环境**：通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，研究 Director 如何以 Motivational Delegation 间接驱动少量深度 NPC（4 核心 + 2 stub）朝过程约束目标演化，并用 Process Fidelity Eval 验证"过程是否可信"。差异化主轴：**少而深 + 可解释 + 可评估**。

## 3. 当前已验证事实

### 后端 Runtime / Director

- Python Agent Server 仍是权威世界状态入口。
- 已有 `GET /api/world/state`、`POST /api/player/action`、`/api/state`、`/api/model-config`、`POST /api/model-config/reload`、`/api/events`、`/api/developer`、`GET /api/debug.phase2`。
- 玩家动作已覆盖 `move`、`move_to_anchor`、`scene_action`、`farm_action`、`end_phase`、`talk`、`give_gift`、`inspect`、`attend_event`。
- `backend/app/director/v0.py` 已落地 `WorldDigest`、`TensionDetector`、`SkillRouter`、`DirectorBeat`、`DirectorValidator`、`DirectorQueueManager`。
- Runtime 会运行规则版 Director v0，并写入 `director.digest_created`、`director.beat_created`、`director.beat_validated`、`director.beat_consumed`、`director.beat_discarded`。
- 已有单个 Event Skill：`event.starlight_festival_shortage`，定义位于 `backend/app/skills/event_skill_registry.py`。
- 星灯祭事件当前支持查看、选择、关系变化、记忆写入、事件反应、夜间反思和结算记录。
- 星灯祭 Event Skill 已承载玩家画像证据模板、玩家风格信号 `styleSignal`、事件反应记忆模板、asset hints 与通用 fallback 台词模板，Runtime 继续负责执行、校验和格式化。
- 星灯祭结算会输出统一 `event_skill_outcome.v1`，API `eventResult`、`town.event_resolved.payload.outcomeRecord` 和 `completedEvents[].resolution.outcomeRecord` 共用该记录。
- 服务端已透出 `playerAnchor`，并为 `move_to_anchor` 与 `scene_action` 返回统一 `actionFeedback`。
- `/api/world/state` 已把 `npcSchedules` 与 `lifeActionPlan` 切到 `motivation_plan.v1` 只读快照，由 MotivationEngine / ToolExecutor 生成下一步候选，继续保持 Godot 可消费的旧字段外形。
- `POST /api/world/tick` 已切到 Phase 2 `MotivationEngine -> ToolExecutor` 最小闭环，返回 `clock`、`events` 与 `agents` diff；tick 事件覆盖 `motivation.decision_made`、`npc.*`、`tool.execution_completed`、`tool.execution_failed`、`tool.execution_interrupted` 和 `memory.result_observed`，工具结果会携带 `motivation_decision_trace` 引用，观察结果可追溯到工具完成 / 失败 / 中断事件；ResultObserver 已按 `observerVisibility` 输出 `observer_scope.v1`，覆盖 private / participants_only / all_in_location 三档。

### Content Codex / NPC 深度卡

- 已新增 NPC 深度卡数据契约：`docs/npc_deep_card_spec.md`。
- 已新增写作工作流：`.windsurf/workflows/author-npc-deep-card.md`。
- 已新增内容数据层：`backend/app/content/`，当前包含 `kai`、`bram`、`mira`、`tomas`、`orren`、`lena` 6 份首发 NPC 深度卡。
- Runtime 初始化会把深度卡挂到 `agent.deepCard`；玩家对话 Prompt 会读取 `voiceStyle`、`archetype`、`speechQuirks`、`innerContradiction`。
- 送礼会根据深度卡 `giftReactions` 匹配反应档，玩家对话与送礼结果会返回 `relationshipStage`。
- `monologueSeeds` 已接入夜间反思上下文和 compact memory evidence；规则 fallback 可独立引用独白素材生成反思。
- `gossipHooks` 已完成首版可消费闭环：内容校验加严，玩家对话上下文会提供 `gossipEvidence`、选择理由、传播草案、`candidateDebugSummary`、`gossip_propagation` 输出契约和 validator；Runtime 会把校验结果写入 `gossip.propagation_validated`，但仍不改世界状态、关系或记忆。
- 6 张首发 NPC 卡已准备 `lifeActionSeeds`、`dailyRumorBeats`、`relationshipBeatSeeds`，并已新增 Phase 2 的 `motivationProfile` / `capabilityPreferences` / `heuristicSeeds` 空占位字段。
- `npm.cmd run content:check` 与 `npm.cmd run check` 已覆盖 NPC 深度卡结构、seed membership、gossip hooks 可用性、资产引用 warning 和 smoke 集成。

### LLM / Debug

- 已有 `RuleBasedProvider` 和 OpenAI-compatible `CloudApiProvider`。
- 已有按 NPC / feature 选择 profile 的配置路径：`config/models.example.json` 为提交模板，`config/models.json` 和 `config/models.local.json` 为本机忽略配置；当前 `model:check` 显示提交态 rule fallback 正常。
- Web 观察台已有 LLM 配置卡片，可查看 profile、路由、key 状态，支持热重载与一次对话 smoke。
- Debug 记录已包含 `providerMode`、`profileName`、`apiKeyConfigured`、`messages`、`rawText`、`parsed`、`executed`、`usage`、`latency`、`fallbackReason`。
- 2026-05-17 曾用本机 `config/models.json` 跑通真实 `CloudApiProvider` smoke；2026-05-21 `npm.cmd run check` 曾跑通真实 cloud smoke；2026-05-22 起常规 `check` / `smoke` 默认跳过真实 LLM，真实链路改由 `npm.cmd run llm:smoke` 显式验收；2026-05-22 本轮 `npm.cmd run llm:smoke` 已通过，dialogue / event_reaction / night_reflection 均为 `deepseek-v4-flash` 且 `fallbackReason=None`。

### Godot 客户端

- `clients/godot/` 是 Godot 4.x 项目骨架。
- `project.godot` 默认主场景已切到 `res://scenes/world_main.tscn`；`npm.cmd run client:run` 会直接打开 Phase 1 tick 可视化场景，旧 `res://scenes/main.tscn` 保留为 legacy 回看入口。
- 已有 `ApiClient`、`WorldSync`、`AssetRegistry`，并新增 `WorldClockService` / `EventBusService` autoload。
- 主场景已接入三场景横向拼图、地点背景、事件 CG、玩家 + 6 NPC `map_idle` 小人、VN 面板和地图上下文动作。
- 已支持 WASD / 点击落点本地移动、靠近高亮、`E` talk、HUD 暂停/倍速、`WorldPulsePanel`、`RemoteEventCompass` 与事件 beacon；本地坐标只做表现，不改后端权威状态。
- 2026-05-17 主人确认玩家移动手感没有问题；2026-05-21 主人确认 Phase 1 可以收口。
- `check_godot_project.py`、Godot headless import、`npm.cmd run client:env`、`npm.cmd run client:run:check` 已通过。
- Phase 2 Godot 观察者面板已落地：Tab 切换、点击 NPC / `E` talk 同步选中，并读取 `/api/debug.phase2?agentId=...` 展示 motivation / subjectiveMemory / relationshipEdges / heuristics 摘要。

### 资产与文档治理

- `assets/manifests/asset_manifest.json` 当前登记 55 条资产：21 条 `source_selected`、3 条 `style_anchor_candidate`、7 条 `pending_review`、24 条 `prompt_ready`。
- 已同步到 Godot 的资产包括 3 张地点背景、星灯祭事件 CG、玩家 + 6 个首发 NPC 的 `neutral` 立绘、7 张地图小人和 3 张交互标记。
- `AssetRegistry` 已支持 `happy` / `troubled` 表情键兜底，缺图时回退 `neutral`。
- 表情差分、行动反馈图标和生活行动 UI 小组件已有 3 批 `prompt_ready` backlog，导出清单位于 `docs/asset_batches/prompt_ready_export.md`，尚未生成或接入 Godot registry。
- `AGENTS.md`、`CLAUDE.md`、`docs/README.md`、`docs/agent_context.md`、`docs/current_status.md`、`docs/open_questions.md` 是当前治理入口；`docs/archive/goal_board.md` 只作历史看板。
- 2026-05-20 新增三份研究 framing 决策源文档已落地并通过 `npm.cmd run context:check`：`docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`；`scripts/build_agent_context.py` 与 `.claude/rules/backend.md` 的历史死链（指向 `vertical_slice_spec.md` / `initial_asset_generation_plan.md`）已修复。

## 4. 当前边界

- 后端持有权威世界状态；Godot 只做表现层、本地交互缓存和 API 调用。
- LLM 当前只生成文本、结构化建议或工具意图；世界状态变更路径经过 Runtime 规则和校验。
- 密钥只放 `config/models.local.json` 或环境变量，不写入仓库。
- 资产入库路径包含来源、提示词引用、用途、状态、授权备注和 Godot 引用。
- 未在当前轮次复验的表情差分、资产晋级和新增玩法循环当前记录为待验证项；真实云端 LLM smoke 已从常规 `check` / `smoke` 拆出为 `npm.cmd run llm:smoke`。
- `frontend/` 继续作为迁移期 Debug 观察台；正式 Web Debug 后续再收敛到 `web-admin/`。
- 重定位后核心方向：NPC 决策可解释（contributing_sources 写入 EventStore）；广度铺开不稀释主观记忆/启发式学习/Eval 三条核心能力。
- Phase 2 启动后旧 `LifeActionExecutor` 退役，**不并行运行**（详见 `agent_loop_architecture.md` §13.2）。

## 5. 常用命令

```powershell
npm.cmd run context:check; npm.cmd run context:brief
npm.cmd run check; npm.cmd run smoke; npm.cmd run llm:smoke
npm.cmd run content:check; npm.cmd run asset:check
npm.cmd run client:env; npm.cmd run client:run:check
npm.cmd run start; npm.cmd run client:run
git status --short; git diff --check
```

说明：

- `context:check` 校验入口元信息、任务线路由和明显状态冲突；`context:brief` 生成下一轮 brief。
- `check` 覆盖 Python 编译、前端 JS、后端 smoke、规则 Eval、资产 manifest、NPC 内容、目标分布和 Godot 项目结构；默认不访问真实 LLM。
- `smoke` 验证后端 Runtime、Director v0、Event Skill、Debug 字段和规则 fallback；默认跳过真实 LLM。
- `llm:smoke` 显式验收真实 CloudApiProvider 链路，刷新 dialogue / event_reaction / night_reflection 的 token、延迟、成本和 fallback 证据。
- `content:check` / `asset:check` 分别校验 NPC 深度卡与资产 manifest；`client:env` / `client:run:check` 校验 Godot 环境和运行入口。
- `client:run` 会打开真实 Godot 游戏窗口，当前默认进入 `world_main.tscn`；旧 P0 UI 可用 `client:run:legacy` 回看。

## 6. 下一轮最短开发入口

### 当前状态

- Phase 1（活着的世界）done：2026-05-21 主人确认可以收口，`world_main.tscn` 进入完成基线。
- Phase 2（骨架建立期）首轮已落地：NPC 深度卡 schema 占位已补，后端 Tool / ToolContractValidator / DecisionBudgetStore / NeedAccumulator / Motivation / ToolExecutor / ResultObserver / SubjectiveMemory / RelationshipEdge / HeuristicLibrary / `phase2.trace.v1` / DomainAdapter shared Protocol / Eval L1 + 规则级 Process Fidelity + Counterfactual Replay + memory ablation + 24h stability suite 已接入 tick 与 Debug；`motivation.decision_made` 已把 need / 5 层 capability filters / 主观记忆召回 / heuristic recall / candidate scores / selected tool 接入 trace，工具完成 / 失败 / 中断会携带 decision trace ref、主观记忆 refs 和 heuristic refs；工具输入 schema / 世界前置条件失败会稳定落入 `tool.execution_failed.reason`；ToolContractValidator 已支持常用 JSON Schema 子集并覆盖 enum / additionalProperties / uniqueItems / numeric range 等稳定违规 code；LLM eligible 工具会经 `decision_budget` 路由并在耗尽时生成 `budget.decision_fallback`；ResultObserver 已按 private / participants_only / all_in_location 解析多 NPC 旁观者并把 `observerScope` 写入 trace；Hard Delegation baseline、No Subjective Memory、No Relationship Edge、Shuffled Memory Owner、Evidence-Link Removal 和 Godot 观察者 debug 摘要面板已落地，但当前 process suite 仍是规则级 / 后验 ablation 骨架。
- 项目方向：narrative-primary 的可解释多 Agent 叙事运行时，差异化主轴为"少而深 + 可解释 + 可评估"。

### Phase 2 第一入口

1. 完整总骨架以 `docs/production_roadmap.md` §4.3 的 15 项为准；`docs/agent_loop_architecture.md` §13.3 是 Agent Loop 内部 11 项。
2. 后端第十一刀已过：ToolContractValidator 已支持常用 JSON Schema 子集，10 个工具 schema 已改为严格 `additionalProperties=false`；smoke 新增 `schemaSubset`，并覆盖 `unexpected_input_field:extra`、`input_enum_mismatch:direction`、`input_array_duplicate_items:targetNpcIds`。下一刀补更真实的 LLM 预算消费策略、更细的空间可见性模型、schema 版本治理和更严格 Debug 展开。
3. Eval 第四刀已过：`scripts/run_agent_eval.py --suite process` 已输出 3 个 GoalSpec、10 项指标、Full / Hard / No Subjective Memory / No Relationship Edge / Shuffled Owner / Evidence-Link Removal 六组对照、Counterfactual Replay 和本地导出；Counterfactual Replay 已区分 `relationshipEffect`、`subjectiveMemoryEffect` 与 `heuristicEffect`；Full 关系因果使用为 `1.0`，No Subjective Memory 覆盖降至 `0.8` 且关系因果仍为 `1.0`，owner/source 等对照关系因果为 `0.0`。注意：Hard Delegation 仍是合成 baseline，No Subjective Memory 仍是后验 ablation，Counterfactual Replay 因果判据仍需收紧。`--suite stability` 已通过 24 游戏小时：`ticksCompleted=24`、`failedToolCount=0`、`interruptedToolCount=3`、`budget.decision_consumed=5`、`memory_observation_per_tool_result=1.0`、`active_agent_count=6`、`heuristic_count=18`、`heuristic_decision_ref_rate=0.104167`。下一刀补跨域 GoalSpec。
4. Godot 第二刀已过：Tab 观察者面板已读取后端 phase2 debug 摘要；下一刀补 recentTraceEvents 展开和真实窗口体验验收。
5. `LifeActionExecutor` 旧线定位为回归修复；Phase 2 不并行运行旧规则和 MotivationEngine。

### 离线基线检查

每轮新对话启动建议运行：

```powershell
npm.cmd run context:check; npm.cmd run check; npm.cmd run smoke
npm.cmd run eval:process; npm.cmd run eval:stability
npm.cmd run asset:check; npm.cmd run client:env; npm.cmd run client:run:check
```

真实模型链路不属于离线基线；修改 provider、prompt、模型配置或需要刷新真实 token / latency / cost 证据时，再单独运行 `npm.cmd run llm:smoke`。

## 7. 协作参考

- 任务拆分优先按当前开发线选择源文档：后端 Agent Loop / Eval / Godot 观察者 / Content schema / 资产管线 / 文档治理。
- 后端骨架线关注 `backend/app/tools/`、`backend/app/runtime/`、`backend/app/memory/`、`backend/app/world/entities/`，近期目标是更真实的 LLM 预算消费策略、更细的空间可见性模型、schema 版本治理、跨域 GoalSpec 和更严格 trace dataset 归档。
- Eval 线关注 `scripts/run_agent_eval.py`、`backend/app/eval/`、`backend/app/domain/`，近期目标是跨域 GoalSpec 和更严格 trace dataset 归档。
- Godot 观察者线关注 `clients/godot/`，近期目标是 `recentTraceEvents` 展开、空态 / 错误态文案和真实窗口验收。
- 多子代理并行减少后，默认不维护大看板；若临时并行，避免多个 worker 同时修改 `docs/current_status.md`、`docs/agent_context.md` 等治理入口。
