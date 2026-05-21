---
status: active
owner_lane: context-governance
last_verified: 2026-05-21
startup_load: first-read
source_of_truth: true
scope: new-session entrypoint, boundaries, commands, and next steps
---

# Loomstead 新对话入口

> 更新时间：2026-05-20（研究 framing 增补：narrative-primary / Motivational Delegation / Process Fidelity Eval）
> 用途：下一轮新对话、无人值守开发、并行子代理任务的第一入口。

## 1. 当前入口

- 先读本文，再按任务线读取源文档。
- 长期方向以 `docs/project_vision.md` 为准（2026-05-19 重定位 + 2026-05-20 研究 framing 增补）。
- **研究 framing 源**：`docs/research_framing_motivational_delegation.md`（narrative-primary / Motivational Delegation / Process Fidelity Eval / baseline matrix）。
- **NPC agent loop 核心圣经**：`docs/agent_loop_architecture.md`（三层工具、动机系统、双轨记忆、启发式学习、仲裁、Eval）。
- **世界实体 schema**：`docs/world_entity_model.md`（FarmPlot / Item / Inventory / Shop / Building / Time / Weather + 工具空间）。
- **Process Fidelity Eval 规格**：`docs/process_fidelity_eval_spec.md`、**跨域 adapter 接口**：`docs/cross_domain_adapter.md`。
- 多层 Agent 系统设计：`docs/agentic_game_design.md`（Director / Skill / Memory / Model 分工）。
- 生产化阶段路线：`docs/production_roadmap.md`（Phase 1 收口中，Phase 2 骨架建立期待启动）。
- 当前事实以 `docs/current_status.md` 为准。
- 并行写入范围以 `docs/goal_board.md` 为准。
- 视觉和资产细节见 `docs/art_direction.md`、`docs/asset_generation_prompts.md`、`assets/manifests/asset_manifest.json`。
- 历史草案、已归档文档统一放在 `docs/archive/`，**不得作为当前事实源**。

## 2. 一句话定位（2026-05-19 重定位 + 2026-05-20 研究 framing 增补）

`Loomstead` 是一个 **narrative-primary 的可解释多 Agent 叙事运行时与研究环境**：通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，研究 Director 如何以 Motivational Delegation 间接驱动少量深度 NPC（4 核心 + 2 stub）朝过程约束目标演化，并用 Process Fidelity Eval 验证"过程是否可信"。差异化主轴：**少而深 + 可解释 + 可评估**。

## 3. 当前已验证事实

### 后端 Runtime / Director

- Python Agent Server 仍是权威世界状态入口。
- 已有 `GET /api/world/state`、`POST /api/player/action`、`/api/state`、`/api/model-config`、`POST /api/model-config/reload`、`/api/events`、`/api/developer`。
- 玩家动作已覆盖 `move`、`move_to_anchor`、`scene_action`、`farm_action`、`end_phase`、`talk`、`give_gift`、`inspect`、`attend_event`。
- `backend/app/director/v0.py` 已落地 `WorldDigest`、`TensionDetector`、`SkillRouter`、`DirectorBeat`、`DirectorValidator`、`DirectorQueueManager`。
- Runtime 会运行规则版 Director v0，并写入 `director.digest_created`、`director.beat_created`、`director.beat_validated`、`director.beat_consumed`、`director.beat_discarded`。
- 已有单个 Event Skill：`event.starlight_festival_shortage`，定义位于 `backend/app/skills/event_skill_registry.py`。
- 星灯祭事件当前支持查看、选择、关系变化、记忆写入、事件反应、夜间反思和结算记录。
- 星灯祭 Event Skill 已承载玩家画像证据模板、玩家风格信号 `styleSignal`、事件反应记忆模板、asset hints 与通用 fallback 台词模板，Runtime 继续负责执行、校验和格式化。
- 星灯祭结算会输出统一 `event_skill_outcome.v1`，API `eventResult`、`town.event_resolved.payload.outcomeRecord` 和 `completedEvents[].resolution.outcomeRecord` 共用该记录。
- 服务端已透出 `playerAnchor`，并为 `move_to_anchor` 与 `scene_action` 返回统一 `actionFeedback`。
- `/api/world/state` 已新增 `npcSchedules` 与 `lifeActionPlan` 只读快照，版本为 `life_action_plan.v1`，用于把 NPC 深度卡生活行动、谣言与关系节拍接入运行时可视化。
- `POST /api/world/tick` 已落地，走 `LifeActionExecutor` 推进规则生活行动，返回 `clock`、`events` 与 `agents` diff；tick 事件已覆盖 `npc.move_started`、`npc.move_progress`、`npc.arrived` 和 `npc.action_*`。

### Content Codex / NPC 深度卡

- 已新增 NPC 深度卡数据契约：`docs/npc_deep_card_spec.md`。
- 已新增写作工作流：`.windsurf/workflows/author-npc-deep-card.md`。
- 已新增内容数据层：`backend/app/content/`，当前包含 `kai`、`bram`、`mira`、`tomas`、`orren`、`lena` 6 份首发 NPC 深度卡。
- Runtime 初始化会把深度卡挂到 `agent.deepCard`；玩家对话 Prompt 会读取 `voiceStyle`、`archetype`、`speechQuirks`、`innerContradiction`。
- 送礼会根据深度卡 `giftReactions` 匹配反应档，玩家对话与送礼结果会返回 `relationshipStage`。
- `monologueSeeds` 已接入夜间反思上下文和 compact memory evidence；规则 fallback 可独立引用独白素材生成反思。
- `gossipHooks` 已完成首版可消费闭环：内容校验加严，玩家对话上下文会提供 `gossipEvidence`、选择理由、传播草案、`candidateDebugSummary`、`gossip_propagation` 输出契约和 validator；Runtime 会把校验结果写入 `gossip.propagation_validated`，但仍不改世界状态、关系或记忆。
- 6 张首发 NPC 卡已准备 `lifeActionSeeds`、`dailyRumorBeats`、`relationshipBeatSeeds`，每卡当前为 `3/2/3` 条 Day 1 素材。
- `npm.cmd run content:check` 与 `npm.cmd run check` 已覆盖 NPC 深度卡结构、seed membership、gossip hooks 可用性、资产引用 warning 和 smoke 集成。

### LLM / Debug

- 已有 `RuleBasedProvider` 和 OpenAI-compatible `CloudApiProvider`。
- 已有按 NPC / feature 选择 profile 的配置路径：`config/models.example.json` 为提交模板，`config/models.json` 和 `config/models.local.json` 为本机忽略配置；当前本机 `model:check` 显示 `activeProvider=cloud`、6 个 profiles、`localConfigLoaded=False`。
- Web 观察台已有 LLM 配置卡片，可查看 profile、路由、key 状态，支持热重载与一次对话 smoke。
- Debug 记录已包含 `providerMode`、`profileName`、`apiKeyConfigured`、`messages`、`rawText`、`parsed`、`executed`、`usage`、`latency`、`fallbackReason`。
- 2026-05-17 已用当前本机 `config/models.json` 跑通真实 `CloudApiProvider` smoke：dialogue / event_reaction / night_reflection 均调用 `deepseek-v4-flash`，`fallbackReason=None`；提交态不包含密钥，fresh env 或无 key 沙箱会按规则跳过真实 LLM 调用。

### Godot 客户端

- `clients/godot/` 是 Godot 4.x 项目骨架。
- `project.godot` 默认主场景已切到 `res://scenes/world_main.tscn`；`npm.cmd run client:run` 会直接打开 Phase 1 tick 可视化场景，旧 `res://scenes/main.tscn` 保留为 legacy 回看入口。
- 已有 `ApiClient`、`WorldSync`、`AssetRegistry`，并新增 `WorldClockService` / `EventBusService` autoload。
- 主场景已接入 3 张地点背景、星灯祭事件 CG，以及玩家 + 6 个首发 NPC 的 `neutral` 半身立绘。
- 已支持地点按钮、背景切换、NPC 选择、VN 风格底部对话面板、聊天动作提交。
- 已新增事件区：展示 `activeEvents`、调用 `inspect` 查看星灯祭事件、渲染 choices、调用 `attend_event` 并展示 NPC 台词、关系变化、记忆写入和夜间反思摘要。
- 已接入地图角色层：玩家和 6 个首发 NPC 的 `map_idle` 小人、talk / gift / event 交互 marker、NPC 点击入口均已进入主场景。
- 已新增本地地图移动与靠近反馈：WASD 独立连续移动、当前场景空地点击落点、落点标记、靠近最近 NPC / 事件后交互高亮；该坐标只用于客户端表现，不改变后端权威状态。
- 角色小人的淡黄色矩形背景已移除，靠近反馈改用 sprite tint 与 marker 状态表达。
- 地图角色层按当前 `selected_location_id` 过滤 NPC 和事件 marker，玩家可移动范围已扩大到当前舞台主体区域，避开左右 UI 和底部 VN 面板。
- 玩家出生点已和 NPC 固定站位槽分离，当前场景 NPC 使用比例槽位排布，交互半径已收紧，降低托玛等 NPC 与玩家重叠及高亮抖动概率。
- 地图层已补 UI 点击穿透、按钮禁用键盘焦点和 WASD 物理键兜底，降低空地点击被透明 UI 吃掉、移动键被按钮焦点干扰的概率。
- 当前场景点击落点改为先修正到可行走边界再接受，地图舞台 bounds 改为随窗口动态放宽，玩家出生点从底部边缘上移到舞台下中区，靠近目标增加滞回，NPC 小人保持可点，减少广场 / 酒馆的卡住体感。
- 地图上下文动作面板已接入：靠近锚点 / 交互体 / 居民 / 事件后生成候选动作，`E`/`Space` 执行，`Tab`/`Q` 切换；左侧“场景行动”降级为调试兜底，VN 面板继续展示后端 `actionFeedback`。
- `world_main.tscn` 已新增玩家本地控制闭环：`PlayerController` 显示玩家 `map_idle` 小人，WASD / 方向键移动，`Camera2D` 跟随，靠近 NPC 后按 `E` 会通过 `/api/player/action` 提交 `talk`，并由 `WorldVnPanel` 弹出后端返回对话。
- 2026-05-17 主人已确认玩家移动手感没有问题；同轮已修正 NPC 全员同点迁徙、路径线过强和同锚点标签堆叠，当前目标分布由 `scripts/check_life_action_targets.py` 覆盖 morning / afternoon / evening 防回归。
- 2026-05-17 新增右上角 `WorldPulsePanel`：启动读取 `/api/world/state` 的 active event 与 `npcSchedules`，tick 时用 `agents` diff 和 NPC 事件更新移动 / 行动状态，作为阶段 1 日程可视化最小入口。
- 2026-05-17 新增远处事件提示：active event 会在事件锚点生成地图 beacon；玩家不在事件场景时，顶部 `RemoteEventCompass` 显示方向、地点和事件名。
- `check_godot_project.py`、Godot headless import、`npm.cmd run client:env` 和 `npm.cmd run client:run:check` 已通过；2026-05-17 `world_main.tscn` 已加载现有地点背景、`map_idle` 小人、NPC 名称/状态、弱化路径线、右上角世界动态面板、远处事件提示和底部 tick 状态提示。2026-05-16 主人已完成上一版真实窗口人工验收；本轮 NPC 分散行动、`WorldPulsePanel`、远处事件提示、`E` talk 与 HUD 暂停/倍速仍需主人窗口复验。

### 资产与文档治理

- `assets/manifests/asset_manifest.json` 当前登记 55 条资产：21 条 `source_selected`、3 条 `style_anchor_candidate`、7 条 `pending_review`、24 条 `prompt_ready`。
- 已同步到 Godot 的资产包括 3 张地点背景、星灯祭事件 CG、玩家 + 6 个首发 NPC 的 `neutral` 立绘、7 张地图小人和 3 张交互标记。
- `AssetRegistry` 已支持 `happy` / `troubled` 表情键兜底，缺图时回退 `neutral`。
- 表情差分、行动反馈图标和生活行动 UI 小组件已有 3 批 `prompt_ready` backlog，导出清单位于 `docs/asset_batches/prompt_ready_export.md`，尚未生成或接入 Godot registry。
- `AGENTS.md`、`CLAUDE.md`、`docs/README.md`、`docs/agent_context.md`、`docs/goal_board.md`、`docs/current_status.md`、`docs/open_questions.md` 是当前治理入口。
- 2026-05-20 新增三份研究 framing 决策源文档已落地并通过 `npm.cmd run context:check`：`docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`；`scripts/build_agent_context.py` 与 `.claude/rules/backend.md` 的历史死链（指向 `vertical_slice_spec.md` / `initial_asset_generation_plan.md`）已修复。

## 4. 当前边界

- 后端持有权威世界状态；Godot 只做表现层、本地交互缓存和 API 调用。
- LLM 只生成文本、结构化建议或工具意图；世界状态变更必须经过 Runtime 规则和校验。
- 密钥只放 `config/models.local.json` 或环境变量，不写入仓库。
- 资产入库必须登记来源、提示词引用、用途、状态、授权备注和 Godot 引用。
- 未在当前轮次复验的云端 LLM、表情差分、资产晋级和新增玩法循环只能记录为待验证项。
- `frontend/` 继续作为迁移期 Debug 观察台；正式 Web Debug 后续再收敛到 `web-admin/`。
- 重定位后硬约束：所有 NPC 决策必须可解释（contributing_sources 写入 EventStore）；广度铺开不能稀释主观记忆/启发式学习/Eval 三条核心能力。
- Phase 2 启动后旧 `LifeActionExecutor` 退役，**不并行运行**（详见 `agent_loop_architecture.md` §13.2）。

## 5. 常用命令

```powershell
npm.cmd run context:check
npm.cmd run context:brief
npm.cmd run check
npm.cmd run content:check
npm.cmd run smoke
npm.cmd run asset:check
npm.cmd run client:run:check
npm.cmd run client:env
npm.cmd run start
npm.cmd run client:run
npm.cmd run client:run:legacy
git status --short
git branch --show-current
git log --oneline -8
git worktree list
git diff --check
```

说明：

- `npm.cmd run context:check` 校验 `AGENTS.md` / `CLAUDE.md`、核心文档元信息、任务线路由路径和明显状态冲突。
- `npm.cmd run context:brief` 生成下一轮新对话 brief。
- `npm.cmd run check` 覆盖 Python 编译、前端 JS、后端 smoke、资产 manifest、Godot 项目结构。
- `npm.cmd run content:check` 校验 6 份 NPC 深度卡、关系阶段、送礼反应、独白种子和资产引用。
- `npm.cmd run smoke` 重点验证后端 Runtime、Director v0、Event Skill、Debug 字段和 LLM smoke 跳过/执行/fallback 状态；强制真实云端通过时设置 `AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE=1`。
- `npm.cmd run asset:check` 校验资产路径、prompt 引用、PNG 尺寸和 Godot 引用。
- `check_godot_project.py`、Godot headless import、`npm.cmd run client:env` 和 `npm.cmd run client:run:check` 已通过；当前默认主场景为 `world_main.tscn`，legacy UI 可用 `client:run:legacy` 回看。
- `npm.cmd run client:run:check` 只检查 Godot 运行入口，不打开真实游戏窗口。
- `npm.cmd run client:run` 会打开真实 Godot 游戏窗口，当前默认进入 `world_main.tscn`。
- `npm.cmd run client:run:legacy` 会打开旧 `main.tscn`，用于回看 P0 UI 路径。

## 6. 下一轮最短开发入口

### 当前状态

- Phase 1（活着的世界）已落地，待主人窗口验收（NPC 分散行动、`WorldPulsePanel`、远处事件提示、`E` talk、HUD 暂停/倍速）。
- 项目已于 2026-05-19 重定位为"可解释多 Agent 叙事运行时"，差异化主轴改为"少而深 + 可解释 + 可评估"。
- 文档治理已完成第一轮：归档过时文档、新增 `agent_loop_architecture.md` + `world_entity_model.md`、重写 `project_vision.md` + `production_roadmap.md` Phase 2 设计 + `gameplay_system_architecture.md` §2.4。

### Phase 1 收口（当前最高优先级）

1. 启动后端：`npm.cmd run start`
2. 另开终端运行 `npm.cmd run client:run`，进入 `world_main.tscn`
3. 验收 30 秒标尺：玩家不操作时能看到至少 3 个 NPC 在地图上走动、做事；玩家可暂停/恢复世界时间；能靠近 NPC 按 `E` 弹出 VN 对话。
4. 验收完成后在 `current_status.md` 标记 Phase 1 done。

### Phase 2 启动前置

1. 阅读 `docs/agent_loop_architecture.md` §13.3 骨架清单（12 项）。
2. 阅读 `docs/world_entity_model.md` §10 Phase 2 验收标准。
3. NPC 深度卡 schema 增补 motivationProfile / capabilityPreferences / heuristicSeeds 占位字段（schema only）。
4. 启动条件 checklist（详见 `production_roadmap.md` §7.2）全部满足后才能开 Phase 2 worker。

### 离线基线检查

每轮新对话启动建议运行：

```powershell
npm.cmd run context:check
npm.cmd run check
npm.cmd run smoke
npm.cmd run asset:check
npm.cmd run client:env
npm.cmd run client:run:check
```
