---
status: active
owner_lane: planning
last_verified: 2026-05-20
startup_load: after-agent-context
source_of_truth: true
scope: lane board, write boundaries, and handoff format
---

# Agent Valley 目标看板

> 更新时间：2026-05-19（项目重定位 + 文档治理）
> 用途：为无人值守开发、并行子代理和下一轮收口提供状态、写入范围和验收命令。
> 2026-05-19 项目重定位为"可解释多 Agent 叙事运行时"，差异化主轴改为"少而深 + 可解释 + 可评估"。Phase 2-6 已重排，详见 `docs/production_roadmap.md`。

## 1. 状态标记

- `done`：本轮已核对，当前目标完成。
- `partial`：最小闭环已落地，仍有明确后续缺口。
- `blocked`：需要人工配置、真实窗口、API key 或上游资产后继续。
- `watch`：当前只读跟踪，暂不作为主线扩写。

## 2. 本轮验收证据

- `npm.cmd run check`：通过，包含 `[model-config] ok`、`[python-smoke] ok`、真实 `[llm-smoke]`、`[asset-manifest-check] ok`、`[npc-codex-check] ok (6 cards)`、`[godot-check] ok`；本机配置走 `CloudApiProvider`，三条链路 `fallbackReason=None`。
- `npm.cmd run content:check`：通过，6 份 NPC 深度卡结构、关系阶段、unlock 引用与资产引用 warning 检查通过。
- 本轮真实 `llm-smoke` 实测概要：dialogue 3744 tokens / 10446ms / 0.00041262 USD；event_reaction 6302 tokens / 4876ms / 0.00079765 USD；night_reflection 18514 tokens / 6418ms / 0.0024811 USD。
- `npm.cmd run client:env`：通过，Godot 4.6.2 headless 项目打开检查通过。
- `npm.cmd run client:run:check`：通过 DryRun，当前默认运行入口指向 `world_main.tscn`。
- Godot headless `world_main.tscn` 加载：通过，已加载 3 张地点背景和 6 张 NPC `map_idle` 小人贴图，日志未出现脚本解析错误或资源加载错误。
- `world_main` 玩家闭环：代码已接入玩家 `map_idle`、WASD / 方向键移动、`Camera2D` 跟随、靠近 NPC 后 `E` 键提交后端 `talk`、`WorldVnPanel` 对话弹层；已通过 headless 加载，真实窗口仍待主人复验。
- `world_main` NPC 轨迹修复：已确认 lifeAction 目标从全员同指 `farm_house_door` 修正为可见 anchor 分布；新增 `scripts/check_life_action_targets.py` 覆盖 morning / afternoon / evening 防回归；Godot 路径线改为低透明短暂调试线，同锚点 NPC 使用 crowd offset 分散站位；主人仍需真实窗口复验 NPC 观感。
- `world_main` 世界动态面板：新增 `WorldPulsePanel`，启动时读取 `/api/world/state` 的 `activeEvents` 与 `npcSchedules`，tick 时读取 `clock/events/agents` 更新 NPC 当前移动或行动状态；Godot headless 加载通过，真实窗口仍待主人复验。
- `world_main` 远处事件提示：active event 会在事件锚点生成地图 beacon；玩家不在事件场景时，顶部 `RemoteEventCompass` 显示方向、地点和事件名；Godot headless 加载通过，真实窗口仍待主人复验。
- `npm.cmd run client:run:legacy:check`：通过 DryRun，旧 P0 UI 可通过 `res://scenes/main.tscn` 回看。
- Godot headless import / quit：通过，脚本可加载；退出时仅出现 Godot ObjectDB leak warning。
- 真实 Godot 窗口：2026-05-16 主人已人工验收上一版基础体验；2026-05-17 主人确认点击移动已正常，但仍反馈三场景中必有一处卡住，中央广场为主、酒馆偶发；本轮补点击边界修正、动态 bounds、玩家出生点上移、靠近滞回和地点短窗收紧后仍需主人复验。
- 本轮并行开发收口：`py_compile`、`content:check`、`smoke`、强制真实 LLM smoke、`check`、`asset:check`、`context:check`、`check_godot_project.py`、prompt_ready 导出、仓库外导出、Godot headless import、Godot headless quit、`client:env`、`client:run:check`、`git diff --check` 已通过。
- 本轮真实 LLM smoke 使用 `deepseek-v4-flash`，dialogue / event_reaction / night_reflection 三条链路 `fallbackReason=None`。
- `npm.cmd run asset:check`：通过。
- `npm.cmd run context:check`：通过，校验共享代理入口、核心文档元信息和任务线路由路径。
- `git diff --check`：通过。
- 白天后端 agent 线已合并到 `main`：`a61a16c merge: integrate day backend agent line`。
- 白天美术资产线已合并到 `main`：`6e77406 merge: integrate day art asset line`。
- Godot 新 sprite `.import` 元数据已提交：`1de91f6 chore: import Godot map sprite metadata`。
- 2026-05-20 研究 framing 增补已落地并通过 `npm.cmd run context:check`：新增 `docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md`、`docs/cross_domain_adapter.md`；`project_vision.md` / `production_roadmap.md` / `agent_loop_architecture.md` / `docs/README.md` / `AGENTS.md` / `docs/agent_context.md` / `docs/current_status.md` 已同步；`scripts/build_agent_context.py` 与 `.claude/rules/backend.md` 死链已修复。

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

### 部分完成

- Content Codex 首批数据已可用；`monologueSeeds` 已接入夜间反思/RAG，`gossipHooks` 已进入对话证据选择、传播草案、validator 和运行时校验事件，`lifeActionSeeds` / `dailyRumorBeats` / `relationshipBeatSeeds` 已进入 `npcSchedules` / `lifeActionPlan` 快照，后续需要驱动实际 NPC 行动、记忆 / 关系扩散。
- Godot 事件交互、地图角色层、本地移动与靠近反馈已通过代码检查、headless 检查和 dry-run；上一版真实窗口已由主人验收；新默认 `world_main` 已通过视觉可读性修复、玩家移动 / `E` talk 接入、NPC 目标分布修复与 headless 加载，玩家移动手感已由主人确认，NPC 分散行动仍待主人复验。
- Godot 已从纯背景图和简单 UI 点击推进到可移动舞台层，并已接入地图上下文候选、快捷键执行、服务端锚点、生活场景行动和行动反馈；后续缺口转为日程可视化与更自然的生活节奏。
- Event Skill 仍只有星灯祭单技能，部分结算逻辑仍有 Runtime 硬编码。
- LLM profile 可配置，Web 观察台已追加配置查看、热重载和对话 smoke 入口；当前本机 `config/models.json` 已跑通真实云端 smoke，切换模型、key 或 profile 后需要刷新。
- 资产批次完成到首批背景、事件 CG、neutral 立绘、地图小人候选和交互标记；24 条 `prompt_ready` 已拆成 3 个导出批次，表情差分、行动反馈图标和生活 UI 小组件尚未生成入库。

### 阻塞项

- 刷新真实 LLM 验证需要本地 `config/models.local.json`、`config/models.json` 或环境变量 API key。
- 表情差分、UI 组件、道具图标和行动反馈图标需要继续生成和人工筛选。
- 地图小人的资产晋级状态需要主人给出筛选结论。

## 4. 开发线看板

| 开发线 | 当前状态 | 下一步 | 主要写入范围 | 禁止/谨慎范围 | 验收命令 |
| --- | --- | --- | --- | --- | --- |
| Phase 1 sprint · 活着的世界 | partial | D1-D2 基础闭环已落地：`LifeActionExecutor`、`/api/world/tick`、`world_clock.gd`、`event_bus.gd`、`npc_controller.gd`、`town_map.gd`、`world_main.tscn` 与默认 `client:run` 入口；下一步把 `world_main` 从骨架推进到可验收玩法入口，优先补相机/玩家控制、VN 交互、动作标签/idle bobbing 与 30 秒录屏验收 | `docs/production_roadmap.md`、`backend/app/simulation/`、必要 `backend/app/runtime/agent_runtime.py` / `backend/app/main.py`、`clients/godot/scenes/`、`clients/godot/scripts/core/`、`clients/godot/scripts/world/`、`clients/godot/scripts/ui/`、必要检查脚本 | 旧 `main.tscn` / `main.gd` 保留为 legacy；不把世界权威事实放进 GDScript；阶段 1 不让 LLM 驱动 NPC 高频自主行动；不把 SSE 作为 D1-D7 硬依赖 | `npm.cmd run context:check`、`npm.cmd run smoke`、`npm.cmd run client:env`、`npm.cmd run client:run:check`、`npm.cmd run client:run:legacy:check`、`git diff --check`，人工录屏验收 |
| Godot 玩法客户端 | partial | WASD、地图层空地点击、落点标记、单目标高亮、当前场景过滤、动态移动范围、UI 点击穿透、焦点收紧、玩家 / NPC 分离站位槽、玩家出生点上移、收紧交互半径、点击边界修正、靠近滞回、地图上下文候选、`E`/`Space` 执行、`Tab`/`Q` 切换、服务端锚点、`scene_action`、`actionFeedback`、NPC 目标分布修复、路径线弱化、同锚点 crowd offset、`WorldPulsePanel` 和远处事件提示已落地；下一步主人复验 NPC 分散行动、世界动态面板、事件 beacon、地图候选动作、农场行动与行动反馈，再推进 NPC 行动图标 | `clients/godot/`、必要时 `clients/godot/assets/`、`scripts/check_godot_project.py`、`scripts/check_life_action_targets.py` | 不在客户端保存权威世界状态；不把后端结算规则复制进 GDScript | `npm.cmd run client:env`、`npm.cmd run client:run:check`、`npm.cmd run check`，人工 `client:run` |
| Content Codex / NPC 深度卡 | partial | `monologueSeeds` 已接入夜间反思/RAG，`gossipHooks` 已进入对话 `gossipEvidence`、`propagationDraft`、validator 与运行时校验事件，`lifeActionSeeds` / `dailyRumorBeats` / `relationshipBeatSeeds` 已进入 `npcSchedules` / `lifeActionPlan` 快照；下一步用快照驱动 NPC 实际工具行动，并把谣言证据写入记忆 / 关系传播 | `backend/app/content/`、`backend/app/simulation/`、`scripts/check_npc_codex.py`、`backend/app/providers/context_builder.py`、必要 runtime glue、相关 docs | 不写固定剧情节点；不让内容卡直接改世界状态；不伪造资产 id | `npm.cmd run content:check`、`npm.cmd run smoke`、`npm.cmd run check` |
| 后端 Director / Event Skill | partial | 画像证据、`styleSignal`、事件反应记忆、asset hints、通用 fallback 台词、`event_skill_outcome.v1` outcomeRecord、`npcSchedules` 与 `lifeActionPlan` 只读快照已进入 Skill / Runtime 协作链路；下一步继续迁移结算模板，补 Skill 复用测试 | `backend/app/director/`、`backend/app/skills/`、`backend/app/runtime/agent_runtime.py`、`backend/app/simulation/`、相关测试 | 不让 LLM 直接改世界状态；不破坏旧 `/api/state` 与 Debug 观察台 | `npm.cmd run smoke`、`npm.cmd run check` |
| 资产管线 | partial | 24 条 `prompt_ready` backlog 已登记并导出到 `docs/asset_batches/prompt_ready_export.md`，下一步生成并筛选表情差分、生活 UI 组件和行动反馈图标；地图小人晋级等待主人筛选 | `assets/source/`、`assets/processed/`、`assets/manifests/`、`docs/asset_batches/`、`clients/godot/assets/` | 不覆盖原图；不提交来源不清的资产；不把未人工确认的小人标成 `source_selected` | `npm.cmd run asset:check`、`python scripts/export_prompt_ready_assets.py`、`npm.cmd run check` |
| LLM / Debug | partial | 当前真实 smoke 已跑通；切换模型、key 或 profile 后用 `AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE=1` 刷新 dialogue / event_reaction / night_reflection 证据 | `backend/app/providers/`、`backend/app/providers/context_builder.py`、Debug 记录结构、迁移期 `frontend/`、相关 docs | 不提交密钥；不隐藏 token、延迟、错误；不把跳过或 fallback 的 live smoke 写成通过 | `npm.cmd run model:check`、`npm.cmd run smoke`、真实 LLM 手动记录 |
| Web Debug Console | watch | 等事件 UI 和 Skill 链路更稳定后展示 Director 队列、Skill、fallback、成本 | 迁移期 `frontend/`，后续 `web-admin/` | 不阻塞 Godot 主体验；不泄漏玩家叙事视角 | `npm.cmd run check` |
| 文档与治理 | done | 每轮结束只更新入口、状态、下一步和仍需验证问题 | `AGENTS.md`、`CLAUDE.md`、`docs/README.md`、`docs/agent_context.md`、`docs/goal_board.md`、`docs/current_status.md`、`docs/open_questions.md`、`scripts/build_agent_context.py` | 不复制源设计长文；不把未验证能力写成完成 | `npm.cmd run context:check`、`npm.cmd run check`、`git diff --check` |

## 5. 人工验收状态

2026-05-16 主人已完成上一版真实 Godot 窗口人工验收，基础体验基本无阻断问题。已覆盖地点切换、背景切换、NPC 选择、`talk` 提交、星灯祭事件查看、choices 与事件结算展示。

后续人工验收重点转为新默认 `world_main` 与下一批扩展：NPC 分散行动是否自然、弱化路径线与底部 tick 状态提示是否可读、右上角 `WorldPulsePanel` 是否能让玩家读懂 NPC 日程、`RemoteEventCompass` 和事件 beacon 是否能表达远处事件、HUD 暂停/倍速、三场景横向拼图、`E` 键 talk、VN 弹层、表情差分和真实 LLM profile 切换。玩家移动手感已由主人在 2026-05-17 确认没有问题。

## 6. 并行任务拆分建议

- Godot worker：只改 `clients/godot/` 和必要检查脚本，目标是推进地图上下文交互、行动反馈和 `lifeActionPlan` 日程可视化。
- 后端 worker：只改 Director / Skill / Runtime / Simulation 相关最小范围，目标是让 `lifeActionPlan` 驱动 NPC 工具行动，并减少星灯祭硬编码。
- Content worker：只改 Content Codex、Prompt 上下文和必要 Runtime glue，目标是把 `gossip.propagation_validated` 扩展为谣言记忆 / 关系传播最小闭环。
- 资产 worker：只改资产目录、manifest、`docs/asset_batches/` 和必要 Godot asset mirror，目标是按批生成表情差分、生活 UI 组件和行动反馈图标。
- Reviewer：只读核对契约、过标表述、验收输出和工作区状态。

不要让多个 worker 同时修改 `docs/current_status.md`、`docs/agent_context.md`、`docs/goal_board.md`。

## 7. 每轮交接格式

```markdown
## 本轮开发线

- 线别：
- 写入范围：
- 已完成：
- 部分完成：
- 阻塞项：
- 验收命令：
- 风险：
- 下一步：
```

## 8. 下一轮推荐排程

### Phase 1 收口（最高优先级）

1. **主人窗口验收**：`npm.cmd run start` + `npm.cmd run client:run`，按 30 秒标尺验收 NPC 分散行动、HUD 暂停/倍速、`E` talk、`WorldPulsePanel`、远处事件提示。
2. 验收完成后在 `current_status.md` §1 标记 Phase 1 done，本看板新增"Phase 2 骨架"开发线占位。

### Phase 2 启动前置

3. NPC 深度卡 schema 增补 motivationProfile / capabilityPreferences / heuristicSeeds 占位字段（schema only）。
4. `npm.cmd run context:check`、`npm.cmd run check`、`git diff --check` 确认文档治理无残留错误。
5. 阅读 `docs/agent_loop_architecture.md` §13.3 + `docs/world_entity_model.md` §10。

### Phase 2 启动后并行开发线（详见 `production_roadmap.md` §4.6）

6. **后端骨架线**：`backend/app/tools/` + `backend/app/runtime/motivation_engine.py` + `backend/app/memory/subjective.py`。
7. **Eval 线**：`scripts/run_agent_eval.py` + L1 scenario suite。
8. **Godot 观察者线**：Tab 切换 + NPC 信息面板最小骨架。
9. **内容 schema 线**：NPC 深度卡三个字段实际数据填充（Phase 3 内容期）。

### 持续维持

10. LLM / Debug 在切换模型、key 或 profile 后刷新真实 smoke。
11. 资产线按新定位重新评估范围（详见 `open_questions.md` 末尾"资产路线的范围调整"）。
12. Web Debug 追加 Director / Skill / fallback 视图，Phase 2 后新增 Heuristic / Arbitration / 主观记忆对比视图。

早期白天整合交接快照已归档至 `docs/archive/daytime_integration_handoff.md`，仅供历史溯源。
