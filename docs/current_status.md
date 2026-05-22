---
status: active
owner_lane: project-status
last_verified: 2026-05-22
startup_load: after-agent-context
source_of_truth: true
scope: current implementation facts, verification state, and work constraints
---

# 当前项目状态与开发前约束

> 状态更新时间：2026-05-22（Phase 2 observer visibility scope）
> 本文只记录当前仓库中已核对、命令已检或明确标注人工未验收的事实。长期方向见 `docs/project_vision.md`，研究 framing 见 `docs/research_framing_motivational_delegation.md`，NPC agent loop 设计见 `docs/agent_loop_architecture.md`，世界实体 schema 见 `docs/world_entity_model.md`，Process Fidelity Eval 规格见 `docs/process_fidelity_eval_spec.md`，跨域 adapter 接口见 `docs/cross_domain_adapter.md`，多层 Agent 系统设计见 `docs/agentic_game_design.md`。

## 1. 当前阶段判断

项目已经从早期观察台阶段进入 `Loomstead` 第一版垂直切片收束阶段。**2026-05-19 项目重定位**为"可解释多 Agent 叙事运行时"，差异化主轴改为"少而深 + 可解释 + 可评估"；**2026-05-21 对外项目名确认改为 `Loomstead`**。

当前仓库具备：

- 可运行的 Python Agent Server。
- Godot 4.x P0 客户端骨架，已接入事件查看、事件选择、地图角色层和交互 marker；真实窗口已由主人验收旧 P0 版本基本可用。
- Phase 1 sprint 已收口：`world_main.tscn` + tick 闭环 + 玩家本地控制 + `E` talk + `WorldPulsePanel` + 远处事件提示 + 三场景横向拼图已作为 Phase 1 完成基线；旧 `LifeActionExecutor` 只保留回归修复，Phase 2 tick 主路径已切到 MotivationEngine。
- 首批静态视觉资产、地图小人候选与 manifest 校验。
- 规则版 Director v0 + 单个 Event Skill 的最小闭环。
- LLM profile、fallback、Debug 字段记录路径，以及 Debug / Memory / influence 查询 API。
- 首发 6 名 NPC 的深度卡、关系阶段、送礼反应和写作工作流。
- 新对话入口与上下文治理索引。

### 当前阶段位置

- **Phase 1（活着的世界）**：done。2026-05-21 主人确认 Phase 1 可以收口，默认 `world_main` 作为已验收完成基线进入冻结维护。
- **Phase 2（骨架建立期）**：首轮骨架已落地，进入 trace / eval 收紧期。文档前置工作已完成，NPC 深度卡 schema 已增补 `motivationProfile` / `capabilityPreferences` / `heuristicSeeds` 占位字段；后端 ToolDefinition / ToolContractValidator / DecisionBudgetStore / CapabilityRegistry / MotivationEngine / NeedAccumulator / ArbitrationLayer / ToolExecutor / ResultObserver / SubjectiveMemoryStore / RelationshipEdgeStore / HeuristicLibrary / DomainAdapter shared Protocol / WorldEntity farm_plot+time skeleton / Eval L1 + 规则级 Process Fidelity + Counterfactual Replay + subjective / relationship memory ablation + 24h stability 的最小骨架已落地，并接入 Debug snapshot、`/api/world/tick`、`motivation.decision_made`、`tool.execution_failed`、`tool.execution_interrupted`、`budget.decision_consumed` / `budget.decision_fallback`、`memory.result_observed`、`phase2.trace.v1` 与 `npm.cmd run check`。SubjectiveMemoryStore 与 HeuristicLibrary 召回均已进入 ArbitrationLayer 候选评分和 decision trace。Godot 观察者面板已开始读取 `/api/debug.phase2`。ResultObserver 已按 `observerVisibility` 区分 private / participants_only / all_in_location，并输出 `observer_scope.v1`。旧 `LifeActionExecutor` 不再服务 tick 主路径。

## 2. 本轮核对结果

游戏内容剧本线的讨论、四层方案、当前实现与后续主线拆分已沉淀到 `docs/game_content_storyline.md`。

| 开发线 | 当前状态 | 已验证事实 | 仍需验证或实现 |
| --- | --- | --- | --- |
| 后端 Director / Event Skill | 部分完成 | `WorldDigest`、`DirectorBeat`、`TensionDetector`、`SkillRouter`、`DirectorValidator`、`DirectorQueueManager` 已落地；Runtime 会生成、校验、消费或丢弃 `activate_event_skill` Beat；星灯祭单技能已注册；玩家画像证据模板、玩家风格信号 `styleSignal`、事件反应记忆模板、asset hints 和通用 fallback 台词模板已迁入 Event Skill；星灯祭结算已统一输出 `event_skill_outcome.v1`，API `eventResult`、事件流和 `completedEvents` 共用 `outcomeRecord`；Debug / Memory / influence 查询 API 已由 smoke 走真实 HTTP 路由验证；Phase 2 后端骨架已新增 10 个 ToolDefinition、ToolContractValidator、DecisionBudgetStore、CapabilityRegistry、NeedAccumulator、MotivationEngine、ArbitrationLayer、ToolExecutor、ResultObserver、SubjectiveMemoryStore、RelationshipEdgeStore、HeuristicLibrary，并通过专用 `GET /api/debug.phase2` 暴露 tools / needAccumulator / decisionBudget / motivation / toolRuntime / subjectiveMemory / relationshipEdges / heuristics / recentTraceEvents；`phase2.trace.v1` 已统一 `traceId` / `spanId` / `sourceEventId` / `agentId` / `targetIds` / `worldTime` / `eventType` / `summary`；`/api/world/tick` 已切到 MotivationEngine -> ToolExecutor 主路径，先写入 `motivation.decision_made`，再把 `motivation_decision_trace`、`subjective_memory_refs` 和 `heuristic_refs` 引用带入 `tool.execution_completed`，随后 `memory.result_observed` 可追溯到工具完成事件；CapabilityRegistry 已输出 `need_relevance / preconditions / npc_profile / event_scope / decision_budget` 五层过滤 / 路由理由并进入 MotivationEngine snapshot 与 decision trace details；SubjectiveMemoryStore 与 HeuristicLibrary 召回已进入 ArbitrationLayer 候选评分，decision trace details 已展开 `subjectiveMemoryRecall` / `subjectiveMemoryRefs` / `heuristicRecall` / `heuristicRefs` / `decisionBudgetRoute`；Debug trace snapshot 已提供 compact `details` 展开字段；失败路径 `tool.execution_failed`、中断路径 `tool.execution_interrupted`、预算 fallback 路径 `budget.decision_fallback` 和观察者分发路径 `memory.result_observed.observerScope` 已接入 trace，并由 smoke 覆盖 target_unavailable / higher_priority_need / rule_fallback / private / participants_only / all_in_location | Event Skill 仍只有一个；星灯祭仍有部分结算模板留在 Runtime；通用 DirectorPlanner 和多事件 Skill 尚未完成；ToolExecutor 仍是首版事务和规则副作用；失败 / 中断路径仍是首版规则覆盖，更多工具前置条件、更真实的 LLM 预算消费策略和更细的视线 / 听力 / 距离衰减仍需扩展 |
| Content Codex / NPC 深度卡 | 已完成首批 + Phase 2 schema 占位 | `docs/npc_deep_card_spec.md` 已定义数据契约；`.windsurf/workflows/author-npc-deep-card.md` 已定义批量写作流程；`backend/app/content/data/npc/` 已入库 `kai`、`bram`、`mira`、`tomas`、`orren`、`lena` 6 份卡；`monologueSeeds` 已接入夜间反思上下文、compact evidence 和规则 fallback；`gossipHooks` 已进入校验、对话上下文 `gossipEvidence`、选择理由、传播草案、`candidateDebugSummary`、`gossip_propagation` 契约和 validator；6 张卡已新增 `lifeActionSeeds`、`dailyRumorBeats`、`relationshipBeatSeeds`，每卡当前为 `3/2/3` 条 Day 1 素材；已新增 `motivationProfile` / `capabilityPreferences` / `heuristicSeeds` 空占位字段；Runtime 会写入 `gossip.propagation_validated` 校验事件；`npm.cmd run content:check` 通过；smoke 覆盖 `deepCard`、对话 Prompt、送礼、关系阶段、monologue evidence、gossip evidence 与合法 / 非法传播样例 | 谣言传播仍只记录校验结果，不写入世界状态、关系或记忆扩散；Phase 2 ToolDefinition / MotivationEngine 已驱动 NPC 工具行动，但内容卡的实际动机权重和启发式种子仍未填充；后续批量 Event Skill 工作流未开始 |
| Godot 客户端 | Phase 1 done，Phase 2 观察者面板已接入 debug 数据 | 代码已接入：地点背景层、NPC 选择、底部 VN 对话层、聊天提交、进行中事件区、`inspect`、choices、`attend_event`、VN 结果展示；地图角色层已渲染玩家与当前场景 NPC / event marker；WASD 独立连续移动、地图层直接点击当前场景空地落点、落点标记、单个最近交互目标高亮、MapMoveHint 和更大舞台移动范围已接入；已移除小人淡黄色矩形背景；已补 UI 点击穿透、按钮禁用键盘焦点、WASD 物理键兜底、玩家 / NPC 分离站位槽、玩家出生点上移、收紧交互半径、点击落点边界修正、动态地图 bounds、靠近目标滞回和 NPC 小人保持可点；地图上下文候选面板、`E`/`Space` 执行、`actionFeedback` VN 回执已接入；已新增 `ObserverPanel`，支持 `Tab` 显隐、点击 NPC 或 `E` talk 同步选中，显示 npcId / 名称 / location / anchor，并按选中 NPC 读取 `/api/debug.phase2?agentId=...` 展示 motivation / subjectiveMemory / relationshipEdges / heuristics 摘要；`check_godot_project.py`、Godot headless import、`client:env` 与 `client:run:check` 通过；2026-05-21 主人确认 Phase 1 可以收口 | 本地 WASD 与点击移动仍只做表现层；Phase 2 Godot 观察者模式仍需真实窗口体验验收、recentTraceEvents 展开视图和更自然的内容节奏打磨 |
| 资产管线 | 部分完成 | manifest 当前有 55 条资产：21 条 `source_selected`、3 条 `style_anchor_candidate`、7 条 `pending_review`、24 条 `prompt_ready`；新增 backlog 覆盖 14 张 `happy/troubled` 表情差分、5 张行动反馈图标和 5 个生活行动 UI 小组件；`prompt_ready` 条目均引用 `docs/asset_generation_prompts.md` 锚点，并补齐 `promptBatchId`、`godotTargetPath`、`godotTargetSlot`；`docs/asset_batches/` 已生成批次计划、机器可读导出和人工筛选表；`scripts/export_prompt_ready_assets.py` 可重复导出；`AssetRegistry` 已支持表情回退；地图小人与交互 marker 已进入 Godot 场景显示链路 | `prompt_ready` 仍只是可生成 backlog，尚未生成、筛选或接入 Godot registry；地图小人是否晋级 `source_selected` 仍需主人明确筛选结论 |
| LLM / Debug | 部分完成 | 代码已接入：OpenAI-compatible cloud provider、profile 解析、本地 overlay 示例、Debug 字段记录、规则 fallback、`model:check` 配置校验、Web LLM 配置卡片和热重载接口；2026-05-17 曾用本机 `config/models.json` 跑通真实 `CloudApiProvider` smoke；2026-05-21 本轮 `npm.cmd run check` 曾跑通真实 cloud smoke，dialogue / event_reaction / night_reflection 均为 `deepseek-v4-flash` 且 `fallbackReason=None`；2026-05-22 起常规 `check` / `smoke` 默认跳过真实 LLM，真实链路改由 `npm.cmd run llm:smoke` 显式验收；2026-05-22 本轮 `npm.cmd run llm:smoke` 通过，dialogue / event_reaction / night_reflection 均为 `deepseek-v4-flash` 且 `fallbackReason=None`，tokens 为 `3289 / 6331 / 18690`，latency 为 `4540 / 5670 / 7383ms`，cost 为 `0.00028242 / 0.00080283 / 0.00252478 USD`；smoke 覆盖 compact Debug payload、RAG-lite memory search、玩家影响链 | 提交态不包含真实 API key；`debug_analysis` profile 只在配置中存在；切换模型、key 或 profile 后需用 `npm.cmd run llm:smoke` 重新刷新真实延迟、成本和失败率 |
| 文档治理 | 已完成本轮入口 | `AGENTS.md`、`CLAUDE.md`、`docs/README.md`、`agent_context`、`current_status`、`open_questions` 是当前新对话入口、分层索引和状态事实源；前期多线程并行看板 `docs/archive/goal_board.md` 已归档 | 后续状态维护以已验证变化为主，避免复制源设计长文 |

## 3. 当前已实现能力

### 后端 Runtime

- Python HTTP 服务入口已存在。
- 世界状态初始化仍保留 10 个 seed NPC、5 个地点、关系图谱、基础状态数值和 Agent 记忆列表；当前 Day 1 / Godot 切片只暴露 6 个首发 NPC，Phase 2 研究骨架按 4 核心 + 2 stub 深化。
- 时间推进、Agent 轮换调度、事件记录和公开状态导出已存在。
- 玩家游戏 API 已存在：`GET /api/world/state`、`POST /api/player/action`、`POST /api/world/tick`。
- 玩家动作已覆盖 `move`、`move_to_anchor`、`scene_action`、`farm_action`、`end_phase`、`talk`、`give_gift`、`inspect`、`attend_event`。
- 星灯祭供应短缺事件已有查看、选择、关系变化、即时记忆、事件反应、夜间反思和结算记录。
- `/api/player/action` 的根节点、`result` 和 `state` 均带有 Godot 可直接展示的 `memoryEvidence`、`relationshipEvidence`、`playerProfile`、`currentObjective`、`availableInteractions`；锚点移动和场景行动会返回统一 `actionFeedback`。
- `GET /api/world/state` 的 `npcSchedules` 与 `lifeActionPlan` 已切到 `motivation_plan.v1`，由 MotivationEngine / ToolExecutor 基于当前需求和工具目标生成只读候选快照；字段外形继续兼容 Godot 现有 WorldPulsePanel。
- `POST /api/world/tick` 已切到 `MotivationEngine -> ToolExecutor`，按游戏时间推进 NPC 工具行动，返回 `clock`、EventStore 包装后的 `events` 和 `agents` diff；移动事件已透出 `npcId/fromAnchorId/toAnchorId` 供 Godot 扁平化消费；每轮决策先写入 `motivation.decision_made`，工具完成会写入 `tool.execution_completed` 或 `tool.execution_failed`，高优先级需求打断当前行动时会写入 `tool.execution_interrupted`；`ToolContractValidator` 会在权威副作用前校验输入 schema 与世界前置条件，失败 reason 已稳定覆盖 `input_not_object`、`missing_required_input:<field>`、`farm_plot_unavailable`、`target_unavailable` 等；`DecisionBudgetStore` 已接入 `CapabilityRegistry` 第五层 `decision_budget`，LLM eligible 工具会输出 `llm` / `rule_fallback` 路由，工具开始执行时写入 `budget.decision_consumed` 或 `budget.decision_fallback`；工具结果携带 `motivation_decision_trace`、可用的 `subjective_memory_refs` 与 `heuristic_refs`，随后通过 ResultObserver 按 `observerVisibility` 写入 `memory.result_observed`；观察者范围会输出 `observer_scope.v1`，覆盖 private / participants_only / all_in_location；这些 Phase 2 事件已携带 `phase2.trace.v1` trace envelope。
- `ResultObserver + BiasFilter` 已把工具完成、失败和中断事件分发为主观记忆，并同步一条短记忆到旧 memory list，保证现有 RAG-lite 可见；观察者分发已按 `private`、`participants_only`、`all_in_location` 三档解析 actor、input target、同地点 presence 和排除列表；`RelationshipEdgeStore` 已记录最小关系边和 `source_event_ids` / `trace_refs`；`HeuristicLibrary` 已能从成功工具、社交成功、工具失败或工具中断事件抽取规则启发式，记录 `effectiveConfidence`、`createdTick`、`updatedTick`，并进入后续仲裁；`GET /api/debug.phase2` 已输出 `recentTraceEvents.details`，可展开 decision、tool 和 memory observation 的轻量解释字段，其中 memory observation 已包含 `observerVisibility`、`observerCount` 和 `observerScope`。
- 2026-05-17 已修正 Day 1 生活行动目标分布；2026-05-21 `scripts/check_life_action_targets.py` 已改为校验 `motivation_plan.v1` 在 morning / afternoon / evening 的工具目标不超出当前客户端切片且不超过锚点容量。

### Director / Skill

- `backend/app/director/v0.py` 已包含规则版 Director v0 的摘要、张力检测、路由、Beat、校验和队列组件。
- `backend/app/skills/event_skill_schema.py` 已定义事件技能结构。
- `backend/app/skills/event_skill_registry.py` 已注册 `event.starlight_festival_shortage`。
- `EventChoiceOutcome` 已承载玩家画像证据模板、玩家风格信号 `styleSignal` 和事件反应记忆模板，`EventSkillSchema` 已承载 asset hints 与通用 fallback 台词模板，Runtime 继续负责格式化、事件写入和 fallback 执行。
- Runtime 会把 Director 关键步骤写入事件流，便于 Debug Console 读取。

### Content Codex / NPC 深度卡

- `backend/app/content/codex_schema.py` 定义 NPC 深度卡 dataclass 契约。
- `backend/app/content/codex_loader.py` 负责读取 `data/npc/*.json`、交叉校验关系阶段与 unlock 引用，并提供 runtime 字典转换。
- `backend/app/content/data/npc/` 已包含 6 份首发 NPC 卡，每份包含秘密、喜好/厌恶、5 段关系阶段、8 条以上独白种子、送礼四档反应和谣言钩子。
- `create_initial_world()` 会把深度卡挂载到对应 `agent.deepCard`。
- 对话 Prompt 已读取深度卡语气锚点；送礼会匹配深度卡 `giftReactions`；玩家对话和送礼结果会返回 `relationshipStage`。
- 夜间反思会读取 `monologueSeeds`，并把 compact `npc_monologue_seed` evidence 暴露给 Debug；规则 fallback 不依赖云端模型也能引用独白素材。
- `scripts/check_npc_codex.py` 已加入 `npm.cmd run content:check` 和 `npm.cmd run check`，并校验独白素材覆盖 morning / afternoon / evening、post_event、high_mood / low_mood，以及 gossip hook 的可消费性和传播目标覆盖。

### Provider / Debug

- `RuleBasedProvider` 用于离线开发、测试夹具和异常兜底。
- `CloudApiProvider` 支持 OpenAI-compatible API 形态。
- `config/models.example.json` 默认 `activeProvider=rule`，保证无密钥也可检查。
- `config/models.json` 是本机实际联调配置，已加入 gitignore；未配置本地密钥时运行链路会依赖 fallback。
- `npm.cmd run model:check` 会校验 profile 引用、结构和公开配置是否误写 `apiKey`。
- `/api/model-config/reload` 支持开发期热重载模型配置；Web 观察台已能展示 profile、路由、key 状态和触发对话 smoke。
- Debug 记录已包含 profile、provider、messages、rawText、parsed、executed、usage、latency 和 fallbackReason。
- 已提供 `/api/debug`、`/api/debug/director`、`/api/debug/skills`、`/api/debug/turns`、`/api/debug/influence`、`/api/debug/skill`、`/api/memory/summary`、`/api/memory/search` 查询入口。
- Debug 列表响应会压缩长 prompt / raw text，保留预览、长度和 message 数，便于 Web Debug Console 或 Godot 调试层读取。

### Godot 客户端

- `clients/godot/` 已有 Godot 4.x 项目、默认主场景 `scenes/world_main.tscn`、legacy 场景 `scenes/main.tscn`、`ApiClient`、`WorldSync`、`AssetRegistry`。
- legacy 主场景代码仍能读取世界状态、渲染背景、列出地点和 NPC、展示半身立绘、提交聊天动作；`npm.cmd run client:run:legacy` 用于回看该路径。
- 新默认 `world_main.tscn` 已接入三场景横向拼图、`WorldClockService`、`EventBusService`、`NpcController`、HUD 暂停/倍速，以及 `/api/world/tick` 返回事件驱动的 NPC 移动/行动状态；2026-05-17 已把默认画面从纯色块占位推进到现有地点背景、`map_idle` 小人、NPC 名称/状态、路径线和底部 tick 状态提示，`ColorRect` 仅作为缺图 fallback。
- `world_main.tscn` 已新增玩家本地控制闭环：`PlayerController` 显示玩家 `map_idle` 小人，支持 WASD / 方向键在大地图中移动，`Camera2D` 跟随玩家，靠近 NPC 后按 `E` 会通过 `/api/player/action` 提交 `talk`，并由 `WorldVnPanel` 弹出后端返回的对话、关系/记忆/事件计数。
- 2026-05-17 主人已确认玩家移动手感没有问题；同轮修正 NPC 首个 tick 全员同点迁徙、路径线过强和同锚点标签堆叠：NPC 初始站位对齐后端 presence，三名广场 NPC 使用表现层 crowd offset 分散显示，路径线改为低透明短暂调试线。
- 2026-05-17 新增 `WorldPulsePanel`，在默认 `world_main` 右上角展示后端 `/api/world/state` 的 active event、`npcSchedules` 生活计划，以及 `/api/world/tick` 的 NPC 移动 / 行动状态，作为阶段 1 日程可视化的最小玩家可读入口。
- 2026-05-17 新增远处事件提示：active event 会在对应地图锚点生成脉冲 beacon；当玩家不在事件所在场景时，顶部 `RemoteEventCompass` 会显示事件方向和地点，让玩家在远处也能感知酒馆 / 广场事件。
- 主场景已能渲染地图角色层，显示玩家和当前场景 NPC / event marker，并提供 talk / gift / event 交互 marker。
- 主场景已新增本地地图移动与靠近反馈：WASD 独立连续移动、点击当前场景空地设置落点、显示落点标记、玩家小人平滑移动、靠近最近 NPC / 事件后只高亮一个交互目标；玩家出生点与 NPC 比例站位槽分离并从底部边缘上移，交互半径已收紧并加入退出滞回；该坐标不写回后端。
- 主场景已接入地图上下文动作：靠近服务端锚点、交互体、居民或事件后生成候选动作，`E`/`Space` 执行，`Tab`/`Q` 切换；侧栏“场景行动”保留为调试兜底。
- 农场田块、公告板和事件点等入口可提交 `scene_action`，VN 面板会展示后端 `actionFeedback` 资源变化。
- 玩家可移动范围已从地点小范围扩大为舞台主体区域，避开左右 UI 与底部 VN 面板。
- 点击当前场景任意可见区域会先修正到可行走边界再设置落点，避免广场 / 酒馆视觉空地因 bounds 过窄产生无响应体感。
- 地图背景、顶层空白容器和标签已改为点击穿透；按钮与交互标记禁用键盘焦点，降低空地点击和移动键被 UI 吃掉的概率。
- 角色小人淡黄色矩形背景已移除，选中或靠近状态改用 sprite tint 与 marker 状态表达。
- 主场景已能列出 `activeEvents`，点击“查看事件”调用 `inspect`，渲染事件标题、摘要和 choices。
- 主场景已能点击事件选项调用 `attend_event`，并在 VN 面板中展示 NPC 台词、关系变化、记忆写入和夜间反思摘要。
- `AssetRegistry` 已接入星灯祭事件 CG，并支持 `happy` / `troubled` 表情缺图时回退 `neutral`。
- `scripts/check_godot_project.py` 会检查默认 `world_main.tscn`、legacy `main.tscn`、脚本、API 字符串、首批资产和 `.import` 元数据。
- `clients/godot/assets/sprites/` 已包含玩家和 6 个 NPC 的 `map_idle` PNG，以及 talk / gift / event 三类交互标记和对应 `.import`。
- 2026-05-16 主人已完成旧 P0 真实窗口人工验收，基本可用；2026-05-17 本轮默认 `world_main` 视觉可读性修复已通过 Godot headless 加载，仍需主人用真实窗口复验背景、小人、路径线和 tick 运动可读性。

### 资产管线

- `assets/source/` 是正式资产源目录。
- `assets/manifests/asset_manifest.json` 是当前资产登记入口。
- `scripts/check_asset_manifest.py` 会校验字段、源图、prompt 文件、PNG 尺寸和 Godot 引用。
- 当前 manifest 共有 55 条资产：21 条 `source_selected`、3 条 `style_anchor_candidate`、7 条 `pending_review`、24 条 `prompt_ready`。
- 当前已进入 Godot registry 的资产是 3 张地点背景、星灯祭事件 CG、玩家 + 6 个首发 NPC 的 `neutral` 半身立绘、玩家 + 6 个首发 NPC 的地图小人和 3 类交互标记。
- 地图小人和交互标记已进入 Godot 资产目录、`AssetRegistry` 与主场景地图角色层。
- 本轮新增表情差分、行动反馈图标和生活行动 UI 小组件的 `prompt_ready` backlog，并通过 `docs/asset_batches/prompt_ready_backlog_batches.json`、`prompt_ready_export.json`、`prompt_ready_export.md` 固化三批可执行清单；尚未生成或接入 Godot。

## 4. 当前主要缺口

### Phase 1 收口结果

1. **Phase 1 done**：旧 P0 窗口基础链路已通过；新默认 `world_main` 具备 tick 驱动 NPC 移动骨架、HUD 暂停/倍速、玩家移动、`E` 键 VN talk、右上角世界动态面板、远处事件提示和三场景横向拼图。2026-05-21 主人确认 Phase 1 可以收口，后续只做回归修复，不继续在 `LifeActionExecutor` 旧线上扩写新能力。

### Phase 2 启动前置（已完成的文档前置工作）

2. **核心圣经文档已落地**：`docs/agent_loop_architecture.md`（NPC agent loop）+ `docs/world_entity_model.md`（世界实体 schema）。
3. **方向文档已重写**：`project_vision.md` 重定位 + `production_roadmap.md` Phase 2 设计 + `gameplay_system_architecture.md` §2.4 软日程 → 动机系统。
4. **历史文档已归档**：9 份过时文档移到 `docs/archive/`。
5. **2026-05-20 研究 framing 增补已落地**：
   - 新增 `docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md` 三份决策源。
   - `project_vision.md` / `production_roadmap.md` / `agent_loop_architecture.md` / `docs/README.md` / `AGENTS.md` / `docs/agent_context.md` 已同步研究 framing 增补。
    - Phase 2 骨架清单新增 ResearchFraming / DomainAdapter / ProcessFidelityEval 三项，Phase 2 收口标准新增 Hard Delegation baseline 与关系记忆 ablation 硬验收。
    - `scripts/build_agent_context.py` 与 `.claude/rules/backend.md` 历史死链（指向 `vertical_slice_spec.md` / `initial_asset_generation_plan.md`）已修复，`npm.cmd run context:check` 通过。
6. **NPC 深度卡 Phase 2 schema 占位已落地**：6 张首发 NPC 卡已新增 `motivationProfile` / `capabilityPreferences` / `heuristicSeeds` 字段；当前为空占位，实际动机权重、工具偏好和启发式种子在 Phase 3 内容期填充。

### Phase 2 当前实施缺口（pending）

6. **三层工具分层 + ToolDefinition 注册表**：最小 schema 与 10 个首批工具已落地（life / farm / shop / cook / craft / social / strategic），ToolExecutor 已具备首版持续动作、移动、事务快照、失败回滚、规则副作用、完成事件 payload、ToolContractValidator 输入 schema / 世界前置条件校验、DecisionBudgetStore 路由事件和高优先级中断 trace；更完整 JSON Schema 子集、更多失败模式和更真实的 LLM 预算消费策略仍待扩展。
7. **MotivationEngine（替换 LifeActionExecutor）**：最小决策骨架已落地，需求计算已抽到 `NeedAccumulator`，可按 status / 空占位 motivationProfile 计算 primaryNeed、经 CapabilityRegistry 取候选工具并由 ArbitrationLayer 产出 selectedToolId 与 contributingSources；`/api/world/tick` 已切到 MotivationEngine -> ToolExecutor 主路径，旧 LifeActionExecutor 不并行运行。
8. **CapabilityRegistry**：`need_relevance / preconditions / npc_profile / event_scope / decision_budget` 五层动态过滤 / 路由已落地，`capability_resolution.v1` 会记录每层 input / allowed / rejected count、工具级过滤理由、allowedToolIds、rejectedTools 和 decisionBudgets，并进入 MotivationEngine snapshot 与 `motivation.decision_made.details.capabilityFilters`；后续可继续扩更多前置条件、预算通道和严格 fallback 策略。
9. **双轨主观记忆**：SubjectiveMemoryStore 最小 record/list/recall/debug_snapshot 骨架已落地，`ResultObserver + BiasFilter` 已接入运行时工具完成、失败和中断事件分发并写入统一 trace；`memory.result_observed` 已可追溯到 `tool.execution_completed` / `tool.execution_failed` / `tool.execution_interrupted`；运行时会按 NPC 召回 `tool_result` 主观记忆并传入 ArbitrationLayer，候选评分已输出 `subjectiveMemoryBonus` / `subjectiveMemoryRefCount`，`motivation.decision_made.details` 已展开 `subjectiveMemoryRecall` / `subjectiveMemoryRefs`；完整遗忘、归档、视线 / 听力 / 距离衰减和 LLM 增强仍待扩展。
10. **HeuristicLibrary**：最小 schema、规则提取和 Debug snapshot 已落地；成功工具会生成 `prefer_successful_tool:<tool_id>`，社交成功会生成 `prefer_social_when_affiliation_high`，工具失败会生成 `avoid_failed_tool:<tool_id>`，工具中断会生成 `avoid_interrupted_tool:<tool_id>`；启发式带 `effectiveConfidence`、tick 衰减字段和 active / dormant 状态，已进入 MotivationEngine snapshot 与 `motivation.decision_made.details.heuristicRecall`；设计师 seed 注入、LLM 提取和更复杂的置信度更新仍待扩展。
11. **ArbitrationLayer**：最小候选工具裁决与 contributing_sources Trace 已落地；关系边、主观记忆和启发式已可在同一需求候选内部加权，并把 `relationship_edge_refs` / `subjective_memory_refs` / `heuristic_refs` 写入 decision contributing_sources；候选评分已输出 `heuristicBonus` / `heuristicRefCount` / `heuristicConflictCount`，启发式冲突以 `highest_effective_delta_wins` 裁决；仍需完整竞争上下文裁决规则。
12. **WorldEntities**：WorldEntity dataclass 与 farm_plot / time 快照转换骨架已落地，完整 FarmPlot / Item / Inventory / Shop / Building / Time / Weather schema 仍待扩展。
13. **EvalFramework**：`scripts/run_agent_eval.py`、`backend/app/eval/` 与 5 个 L1 rule scenario 已落地，并纳入 `npm.cmd run check`；输出已包含 Full / Hard Delegation / No Relationship Edge 三组 rule baseline、`mean/std/n` 和 `ablation_comparison`。`npm.cmd run eval:process` 已新增 3 个 process-constrained GoalSpec、10 项 Process Fidelity 指标、Full / Hard Delegation / No Subjective Memory / No Relationship Edge / Shuffled Memory Owner / Evidence-Link Removal 六组 process baseline、Counterfactual Replay 和 `.run/eval-runs` 导出脚本；Counterfactual Replay 现在区分 `relationshipEffect`、`subjectiveMemoryEffect` 与 `heuristicEffect`；当前 Full baseline 的 `relationship_memory_causal_use_rate=1.0`，No Subjective Memory 的 `required_process_coverage=0.8` 且 `relationship_memory_causal_use_rate=1.0`，Hard / No Relationship Edge / Shuffled Memory Owner / Evidence-Link Removal 的关系记忆因果使用均为 `0.0`。这些结果当前属于规则级 / 后验 ablation 骨架，用于 CI 护栏和方向验证；Hard Delegation 仍是合成 baseline，No Subjective Memory 不是全程 runtime 级禁用，Counterfactual Replay 的因果判据仍需收紧。`npm.cmd run eval:stability` 已验证规则版 AgentRuntime 连续 24 游戏小时稳定推进：`ticksCompleted=24`、`completedToolCount=144`、`failedToolCount=0`、`interruptedToolCount=3`、`budget.decision_consumed=5`、`trace_schema_coverage=1.0`、`memory_observation_per_tool_result=1.0`、`tool_interruption_rate=0.020408`、`relationshipEdgeCount=8`、`heuristic_count=18`、`heuristic_decision_ref_rate=0.104167`、6 个首发 NPC 均参与。导出文件长期归档、更严格跨域 GoalSpec 仍待补齐。
14. **Godot 观察者模式**：Tab 切换、点击 NPC / `E` talk 同步选中、NPC 信息面板和 `/api/debug.phase2` 摘要读取已落地；后端已提供 `recentTraceEvents.details`；后续补 Godot 侧展开 UI、真实窗口体验验收和更细的 trace 可视化。
15. **NPC 深度卡实际数据填充**：4 核心 NPC 的 motivationProfile / capabilityPreferences / heuristicSeeds 实际内容，Phase 3 填；2 stub 继续默认权重或按需要升级。

### 持续维持

16. **真实 LLM 证据刷新**：2026-05-22 起真实 LLM smoke 已从常规 `check` / `smoke` 拆出；本轮 `npm.cmd run llm:smoke` 已通过并刷新 token、延迟、成本和 fallback 证据；修改 provider、prompt、模型配置或切换模型/key/profile 后，继续用 `npm.cmd run llm:smoke` 单独刷新真实证据。
17. **资产补齐**：表情差分、UI 组件和行动反馈图标已进入三批 `prompt_ready` backlog 和导出清单，仍待生成、筛选、登记源图和接入；地图小人晋级状态需主人确认。
18. **Debug Console 扩展**：后端已有 Debug / Memory 查询 API，Web 侧仍需展示 Director 队列、Skill 激活、fallback 和成本字段。Phase 2 后还要新增 Heuristic Library / Arbitration trace / 主观记忆对比视图。

## 5. 开发前关注点

- 后端 Runtime 是权威世界状态修改点。
- Godot 客户端当前负责读取状态、提交玩家动作、展示结果。
- LLM 输出进入可见结果前的路径包含解析、校验、fallback 和事件记录。
- 密钥配置路径为本地 overlay 或环境变量。
- 新增资产通常同步 manifest；新增 Godot 可用资产通常同步 registry 或检查脚本。
- 新增 API、存档字段、事件类型、资产目录、Debug 字段前，建议先写清数据契约。
- 未由代码、命令或人工窗口验证的能力在状态文档中保留为缺口或待验证项。

## 6. 当前可运行命令

```powershell
npm.cmd run check
npm.cmd run context:check
npm.cmd run content:check
npm.cmd run smoke
npm.cmd run asset:check
npm.cmd run client:env
npm.cmd run client:run:check
npm.cmd run start
npm.cmd run client:run
npm.cmd run client:run:legacy
git diff --check
```

本轮收口要求的完整验收命令为：

```powershell
npm.cmd run check
npm.cmd run context:check
npm.cmd run content:check
npm.cmd run smoke
npm.cmd run asset:check
npm.cmd run client:env
npm.cmd run client:run:check
git diff --check
```

早期白天整合交接快照已归档：

```powershell
Get-Content docs\archive\daytime_integration_handoff.md
```

## 7. 人工验收状态

2026-05-16，主人已运行真实 Godot 窗口并确认当前基础体验基本无问题。该结论覆盖：地点切换、背景切换、NPC 选择、`talk` 提交、星灯祭事件查看、choices 展示和事件结算展示。

2026-05-21，主人确认 Phase 1 可以收口，默认 `world_main.tscn` 进入完成基线。仍需后续人工验证的内容只保留 Phase 1 外延项：表情差分、UI 组件、真实 LLM profile 切换，以及 Phase 2 新增观察者模式 / Debug 视图。

## 8. 下一轮建议

### 立即（Phase 2 收紧）

1. 后端骨架线继续从当前 `motivation.decision_made -> tool.execution_completed / failed / interrupted -> memory.result_observed` trace 主路径推进到更完整 JSON Schema 子集、更真实的 LLM 预算消费策略、更细的空间可见性模型和更严格 Debug 展开，不再做旧 LifeActionExecutor shadow-run。
2. Eval 线继续扩展 `backend/app/eval/`，在当前 L1 + Process Fidelity + Counterfactual Replay + memory ablation + 24h stability 输出基础上补跨域 GoalSpec、更长期稳定性和更严格 trace dataset 归档。
3. Godot 观察者线已读取后端 phase2 debug 的 motivation / subjectiveMemory / relationshipEdges / heuristics；下一步补 recentTraceEvents 展开、空态文案和真实窗口手感验收。

### Phase 2 硬约束

4. `LifeActionExecutor` 旧线冻结，只做回归修复；Phase 2 直接切到 MotivationEngine，不并行运行。
5. 完整 Phase 2 总骨架以 `production_roadmap.md` §4.3 的 15 项为准；`agent_loop_architecture.md` §13.3 是 Agent Loop 内部 11 项清单。
6. Eval 是 Phase 2 硬验收线，不达标不进入 Phase 3。

### 持续维持

8. LLM / Debug 线在切换模型、key 或 profile 后用 `npm.cmd run llm:smoke` 刷新真实 smoke。
9. 资产线按 `docs/asset_batches/prompt_ready_export.md` 推进表情差分、生活 UI 组件和行动反馈图标，**注意 Phase 2 后资产规划要按 `open_questions.md` 末尾的"资产路线的范围调整"重新评估**。
10. Web Debug 追加 Director / Skill / fallback 视图，Phase 2 后新增 Heuristic Library / Arbitration trace / 主观记忆对比视图。
