---
status: active
owner_lane: planning
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: production roadmap, phase axis, phase 1 closeout, phase 2 skeleton design
---

# Loomstead 生产化路线图

> 制定时间：2026-05-17，2026-05-19 重排
> 触发原因：项目当前体验被诊断为"UI 点击看板"——后端有厚实的 Director / Skill / NPC 深度卡 / 记忆 / gossip schema，但客户端只是"表单提交+状态展示"。本文档作为新的事实源，取代旧实施计划（已归档至 `docs/archive/implementation_plan.md`）作为路线执行依据。
> 2026-05-19 项目重定位后，本文档增补 Phase 2 详细技术方案，并将 Phase 2-6 重新排序，以"少而深 + 可解释 + 可评估"为差异化主轴。
> 适用边界：本文档定义阶段轴、阶段验收和 Phase 1 / Phase 2 详细技术方案；Phase 3-6 只给方向，等触发时再细化。

## 1. 方向决策（2026-05-19 重定位）

项目从"二次元田园 RPG"重定位为 **"可解释的多 Agent 叙事运行时"**。差异化主轴：**少而深 + 可解释 + 可评估**。

旧 A+C 复合（沙盒导演 + 社会模拟）作为外壳保留，但项目核心叙事改为"4 核心深度 NPC + 主观记忆 + 启发式学习 + Eval Framework"。详见 [`project_vision.md`](./project_vision.md) 和 [`agent_loop_architecture.md`](./agent_loop_architecture.md)。

### 1.1 30 秒 Demo 验收标尺

任何"已达成阶段 N"的论断，必须能在 30 秒视频内向不懂技术的观众证明该阶段的玩家体感。
具体指标见每阶段"玩家体感验收"段。

### 1.2 客户端推翻范围

- 推翻：`main.gd` / `main.tscn` 的 UI 主导布局（页签 + NPC 列表 + 事件列表 + VN 面板）、"按钮切换地点"概念、`end_phase` 回合制按钮。
- 保留：`api_client.gd` / `world_sync.gd` / `asset_registry.gd` 三个底层组件、全部资产、`.import` 元数据、Debug API / Web 观察台、后端 Director / Skill / 深度卡 / 记忆 / gossip schema。
- 推翻策略：**并行新建 `world_main.tscn`**，旧 `main.tscn` / `main.gd` 保留原路径并标记为 legacy，对应引用不迁移；通过 `project.godot` 切主场景即可一键回滚。

### 1.3 时间预算

2 周冲刺看到阶段 1（"活着的世界"）可演示原型。
后续阶段按里程碑式推进，不绑定固定周期。

## 2. 六阶段路线总览（2026-05-19 重排）

| 阶段 | 名称 | 核心问题 | 30 秒验收标尺 | 状态 |
| --- | --- | --- | --- | --- |
| **0** | 战略对齐 | 主轴选定、客户端推翻范围、阶段验收标准 | —— | done |
| **1** | 活着的世界 | 抛弃回合制 + 推翻 UI 主导客户端，NPC 真的在地图上做事 | 玩家不操作，30 秒内能看到至少 3 个 NPC 在地图上走动、做事 | done（2026-05-21 主人确认收口） |
| **2** | 骨架建立期 | 三层工具分层 + 动机系统 + 双轨记忆 + 启发式学习 + 仲裁 + Eval Framework 一次性铺到位 | 关闭某条核心能力（如 subjective_memory），eval 指标可测量退化 | active kickoff |
| **3** | 内容填充期 | 5 作物 + 25 物品 + 30 工具 + 4 核心 NPC 完整接入动机/启发式数据 | NPC 自己种田、开店、做饭、社交，不需要玩家干预；启发式经验首次可观测 | pending |
| **4** | 玩家成为变量 | 玩家行为在 NPC 之间传播，社会因果可见；observer 模式可点击追溯 | 玩家送花给 A，第二天 B 在酒馆说起这件事；玩家可点击 B 看到完整因果链 | pending |
| **5** | 涌现式叙事 | 多 Event Skill + 多日循环 + 启发式演化展示 | 第二天的小镇和第一天不一样；某 NPC 因失败积累形成新行为模式 | pending |
| **6** | 生产化打磨 | LLM 成本分层、存档、Web Debug Console 公开版、技术博客 + dataset 发布 | 稳定可发的 Demo 版本 + 可分享 portfolio | pending |

## 3. 阶段 1 详细技术设计（2 周冲刺执行依据）

### 3.1 架构变化

当前范式：
```text
玩家点按钮 ──► POST /api/player/action ──► Runtime ──► 返回 state
                                                          │
                                                          ▼
                                                main.gd 把字段塞 UI
```

阶段 1 目标范式：
```text
                          ┌─ 后端 tick：推进 NPC、生成事件
WorldClock(前端) ──tick──►│
   ▲                      └─► EventStore + tick events ──► EventBus(前端)
   │                                                           │
   └─ 玩家暂停/加速                                            ▼
                                                   NPC Controller × N (前端)
                                                   │ 状态机：Idle / Walking / Performing
                                                   │ 阶段 1 寻路：anchor graph + 直线插值
                                                   │ 动画：sprite tween + 头顶工具图标
                                                   ▼
                                                玩家看到 NPC "在生活"
```

核心切换：**"请求/响应"范式 → "事件驱动 + 客户端时间预测"范式**。
客户端职责升级为玩家可感知的表现世界；后端继续持有时间、位置、关系、记忆、事件和结算的权威事实。

### 3.2 关键技术决策（2026-05-17 锁定）

| 决策 | 选定 | 理由 |
| --- | --- | --- |
| 时间驱动模型 | **客户端驱动 tick；tick response events 为阶段 1 主通道，SSE 为可选增强** | 玩家暂停即冻结，调试容易；Godot 先通过 `/api/world/tick` 响应消费事件，避免阶段 1 被长连接稳定性牵制 |
| 客户端策略 | **并行新建 `world_main.tscn`，旧 `main.tscn` / `main.gd` 原路径保留** | 安全可随时回滚；旧场景留 legacy 备查，避免移动脚本导致引用断裂 |
| NPC 表现精度 | **sprite 插值 + 头顶动作图标 + idle bobbing** | "在生活"的最低视觉门槛，2 周可达 |
| NPC 决策来源 | **完全规则驱动，不上 LLM** | LLM 调用频率/成本不允许在阶段 1 上 NPC 自主；LLM 仅在玩家对话/事件选择时触发 |
| 寻路实现 | **anchor graph + 直线插值首选，Godot Navigation2D 后置增强** | 2 周目标优先证明 NPC 迁徙体感，减少 nav polygon 配置风险 |
| 地图布局 | **三场景横向拼图大画布 + 相机自由跟随玩家** | 取代"按钮切场景"，是体感最关键改造 |
| Day 1 日程目标 | **lifeActionSeeds 优先绑定可见 anchor id** | 避免泛化 `home/work_spot` 在首个 tick 被解析成同一目标，保证 6 名 NPC 呈现分散的生活动线 |

### 3.3 后端改造（最小集）

#### 3.3.1 新建 `backend/app/simulation/life_action_executor.py`

- 输入：world、`lifeActionPlan.selectedActions`、`deltaSeconds`
- 职责：
  - 对每个 NPC，根据当前 `activeLifeAction` 推进状态
  - NPC 不在目标 anchor → 生成 `npc.move_started` / `npc.move_progress` / `npc.arrived` 事件
  - 到达 anchor → 生成 `npc.action_started`，按 action 类型分配持续时间（首版用规则表，例如 `tend_farm=300s`、`chat_with=120s`、`tend_shop=600s`）
  - 持续期间生成低频 `npc.action_tick`
  - 到达持续时间 → 生成 `npc.action_completed`，按现有 Runtime 路径写入关系/记忆/物品
- 关键约束：**所有动作进度只用游戏时间，不用墙钟**。客户端不调 tick = 世界冻结。

#### 3.3.2 改造 `runtime.step()`

- 现有 `step(actor_id=...)` 保留，继续给 Debug Console 单步调试用。
- 新增 `runtime.tick(delta_seconds: float) -> dict`：
  - 调用顺序：`life_action_executor.tick() → director.tick(轻量) → event_store.append(events)`
  - 返回紧凑 state diff + 事件列表

#### 3.3.3 新增 `POST /api/world/tick`

请求：
```json
{ "deltaSeconds": 5.0, "speed": 1.0 }
```

响应：
```json
{
  "clock": { "day": 1, "hour": 8, "minute": 25, "phase": "morning" },
  "events": [
    { "type": "npc.move_started", "npcId": "tomas", "from": {...}, "to": {...} },
    { "type": "npc.action_started", "npcId": "kai", "actionId": "...", "duration": 300 }
  ],
  "agents": [ /* 简化 NPC 位置/状态变化 */ ]
}
```

### 3.4 前端改造（推翻 UI，保留底层）

#### 3.4.1 保留

- `scripts/api_client.gd`（升级支持 `tick()`；SSE 订阅使用独立节点或后续增强，不复用会取消请求的同一个 `HTTPRequest`）
- `scripts/asset_registry.gd`（不动）
- `scripts/world_sync.gd`（变薄，只缓存 clock、静态信息和后端 diff；动态表现位置由 NPC Controller 管）
- 所有资产、`.import` 元数据
- Web Debug 观察台

#### 3.4.2 推翻（逻辑冻结为 legacy，不在阶段 1 继续扩写）

- `main.gd` 的 UI 主导布局
- `main.tscn` 的页签结构（旧 scene 和脚本保留原路径，可一键回滚）
- "按钮切场景"概念

#### 3.4.3 新建

- `scripts/core/world_clock.gd`（autoload）—— 持有游戏时间，定时调用 `/api/world/tick`
- `scripts/core/event_bus.gd`（autoload）—— 先把 tick response events 分发为 Godot signal；SSE 后续作为独立长连接增强
- `scripts/world/npc_controller.gd`（每 NPC 一个实例）—— 状态机 + anchor graph / 直线插值 + 动画
- `scripts/world/player_controller.gd`—— WASD 移动 + E 键交互
- `scripts/world/town_map.gd`—— 主场景，三场景背景按地理布局横向拼图
- `scripts/ui/hud.gd`—— 简洁顶部 HUD（时钟、速率控制 1x/2x/暂停、当前位置）
- `scripts/ui/vn_panel.gd`—— VN 对话模块（弹出式）

### 3.5 "小镇全景图"的关键性

当前"按钮切场景"是体感"看板化"的最大根源——玩家永远看不到 NPC 之间的迁徙。
阶段 1 必须改为：**三张地点背景在一张大画布上拼接 + 相机自由跟随玩家**。

资产侧不需要重画，只是布局重排：

```text
[农场]--[广场]--[酒馆]   ← 三张背景横向拼接成一张大地图
   ↑      ↑      ↑
   NPC 可在三地之间真实迁徙，玩家在广场能远远看到铁匠从酒馆走出来
```

这是 2 周内能做到的"最小但震撼"的视觉切换。

### 3.6 2 周冲刺拆分（按天）

| 天 | 后端 | 前端 | 验收 |
| --- | --- | --- | --- |
| D1 | 设计 + 写 `LifeActionExecutor` 雏形（规则驱动，3 种动作类型） | 新建 `core/world_clock.gd` + `event_bus.gd` autoload | unit test：NPC A 从 anchor X 走到 Y，事件序列正确 |
| D2 | `/api/world/tick` 上线，整合到 step 旁路 | `api_client.gd` 增加 `tick()`，`event_bus.gd` 消费 tick response events | 客户端能调 tick，并把响应事件分发到前端 |
| D3 | NPC 行动持续时间表 + `npc.action_*` 事件全套 | 新建 `town_map.gd` 三场景横向拼图 | 浏览器能 hit `/api/world/tick`，state 推进正常 |
| D4 | 玩家行动复用现有路径，但事件改走 EventStore | 新建 `npc_controller.gd` 状态机（Idle/Walking/Performing） | NPC 在场景里能根据后端事件移动 |
| D5 | Director 整合（保留现有，不变形） | anchor graph 路线与直线插值打磨；记录 Navigation2D 后置清单 | 6 个 NPC 在大地图上各自走动 |
| D6 | 测试 + 1Hz 长跑稳定性 | 玩家相机自由跟随 + 速率控制 HUD | 静置 5 分钟无错误、无内存涨 |
| D7 | **里程碑 1：自主世界**——玩家不操作 NPC 自己活 | 同左 | 录屏：30 秒内能看到至少 3 个 NPC 在做事 |
| D8 | 玩家 talk 走新事件流 | VN 弹出模块（按 E 触发，脱离页签结构） | E 键弹 VN，对话能跑通 |
| D9 | NPC `action_completed` 写关系/记忆（复用现有 Runtime） | NPC sprite tween + 简单 idle 动画 | 玩家送礼后，事件出现在事件流，NPC 反应可见 |
| D10 | 星灯祭事件接入新事件流（"远处发生"） | 事件触发时地图上有视觉提示（图标飘过） | 玩家在农场能看到广场有事件正在发生 |
| D11 | 性能测试 + LLM 调用日志检查 | 旧 `main.tscn` / `main.gd` 保持原路径并标记 legacy，重检入口完整 | 帧率 ≥ 30，LLM 调用频率符合预期 |
| D12 | 文档：本文档阶段 1 收口 | 入口/HUD/相机收尾打磨 | `npm.cmd run check` 全绿 |
| D13 | 人工验收准备：录屏脚本、Demo 说明 | 视觉抛光（动作图标、对话气泡） | 主人窗口验收 |
| D14 | 缓冲日 + 文档归档 | 缓冲日 | 阶段 1 收口 |

### 3.7 阶段 1 玩家体感验收

录一段不超过 60 秒的视频，必须能展示：

1. 玩家进入游戏后 30 秒内**不做任何操作**，能看到至少 3 个 NPC 在地图上走动、做事；
2. 玩家能控制角色在大地图上自由移动，看到 NPC 从一个地点走到另一个地点；
3. 玩家靠近 NPC 按 E 键能弹出 VN 对话，对话流程跑通；
4. 暂停按钮按下后，所有 NPC 立即静止，再次按下恢复；
5. 顶部 HUD 显示游戏时间正在流逝。

任何一项不达成，阶段 1 视为未完成。

### 3.8 必须接受的硬妥协

- **NPC 决策完全规则驱动**，不上 LLM。LLM 调用频率和 latency 在阶段 1 不允许；LLM 上 NPC 自主行动放阶段 2。
- **没有寻路冲突解决**，NPC 互相穿模可接受（占位优先）。
- **没有作息真实表**，先用 `lifeActionSeeds` 的 phase 粗映射。
- **没有恋爱线/经济线**——阶段 4 的内容。
- **VN 面板视觉不重新设计**，先复用现有 layout（搬到弹出模块）。

### 3.9 风险与应对

| 风险 | 概率 | 应对 |
| --- | --- | --- |
| SSE 长连接和 tick 请求并发时出现连接管理复杂度 | 中 | 阶段 1 先用 tick response events；SSE 作为独立节点后置验证，后端当前已使用 `ThreadingHTTPServer` |
| Godot 4 Navigation2D 配置成本高 | 中 | 阶段 1 使用 anchor graph + 直线插值；Navigation2D 进入后置增强清单 |
| `main.gd` 2358 行继续扩写导致新旧逻辑耦合 | 高 | 旧 scene 和脚本原路径冻结；新建独立 `world_main.tscn`；通过 `project.godot` 切主场景 |
| LLM 玩家对话调用过慢导致 NPC 卡住 | 中 | NPC 行动不阻塞玩家请求；玩家请求独立线程处理 |
| Runtime 现有 `step()` 是 Agent 轮换调度，改为时间驱动可能破坏 Director | 中 | 不改 step；新建 `runtime.tick(delta_seconds)`；step 继续给 Debug Console 用 |
| 三场景横向拼图大地图导致首屏负担/视觉割裂 | 中 | 三背景间用过渡色块/草地拼接；优先保证 NPC 迁徙可见 |

## 4. Phase 2 详细技术设计（骨架建立期，重定位后核心阶段）

### 4.1 Phase 2 核心目标

**一次性铺好 5 条核心能力的完整骨架**，避免 AI 助手协作下的"无意识收窄"。Phase 2 不追内容广度，追接口完整性 + Eval 可测。

骨架 = 完整 schema + 接口 + 至少一个端到端可跑通的实例。

**2026-05-20 研究向增补**：Phase 2 保持原骨架计划不大改，但必须加入三项研究护栏：

1. **研究文档**：明确 narrative-primary / task-secondary、Motivational Delegation、Process Fidelity Eval、核心反论点和 baseline matrix（已落地 `docs/research_framing_motivational_delegation.md`）。
2. **跨域 adapter 接口**：抽象 GoalSpec / Intervention / Observation / EvalTrace，保证小镇是 primary domain，同时保留 task-secondary 可迁移路径（已落地 `docs/cross_domain_adapter.md`）。
3. **Hard Delegation baseline**：在 Eval 中加入"直接任务委派 / todo-list"对照，严肃回答为什么不用传统 task delegation（详见 `docs/process_fidelity_eval_spec.md` §3.3）。

### 4.2 直接切换原则

Phase 2 启动时 **直接退役** Phase 1 的 `LifeActionExecutor`，不并行运行。原因：

- AI 助手协作下并行运行会导致两套代码相互污染
- 新系统证据被旧系统稀释，无法量化对比
- 早做断舍离对项目有利

### 4.3 必须一次性到位的骨架（验收清单）

| 模块 | 形态 | 落地位置 |
| --- | --- | --- |
| ToolDefinition + ToolRegistry | 完整接口，注册 8-12 个工具实现 | `backend/app/tools/` |
| MotivationEngine | 完整决策周期 + 三层路由 + 决策预算 + Fallback | `backend/app/runtime/motivation_engine.py` |
| CapabilityRegistry | 4 层动态过滤齐全 | `backend/app/runtime/capability_registry.py` |
| NeedAccumulator + NeedProfile | 完整 4 类需求，每 NPC 实例 | `backend/app/runtime/need_accumulator.py` |
| ArbitrationLayer | 完整裁决 + Trace（contributing_sources 写入 EventStore） | `backend/app/runtime/arbitration.py` |
| ResultObserver + BiasFilter | 模板 + slot fill 版（LLM 增强放 Phase 3） | `backend/app/memory/observer.py` |
| SubjectiveMemoryStore | 完整 schema：衰减、归档、召回 | `backend/app/memory/subjective.py` |
| RelationshipEdgeStore | 双时间戳 + 至少 5 种边类型 | `backend/app/memory/relationship_edges.py` |
| HeuristicLibrary | 完整 schema + 规则提取 + LLM 提取（受预算约束） | `backend/app/memory/heuristic.py` |
| WorldEntities | FarmPlot / Item / Inventory / Shop / Building / Time / Weather schema | `backend/app/world/entities/` |
| EvalFramework | scripts/run_agent_eval.py + L1 scenario suite (5-8 个) | `scripts/run_agent_eval.py`, `backend/app/eval/` |
| ResearchFraming | Motivational Delegation + Process Fidelity Eval 研究文档 | `docs/research_framing_motivational_delegation.md` |
| DomainAdapter | GoalSpec / Observation / Intervention / EvalTrace 抽象接口 | `backend/app/domain/base.py`、`docs/cross_domain_adapter.md` |
| ProcessFidelityEval | 过程保真指标 + hard delegation baseline + ablation protocol + Counterfactual Replay + memory ablation | `backend/app/eval/process_fidelity.py`、`docs/process_fidelity_eval_spec.md` |
| 观察者模式 | Godot 内最小可用：切换 + NPC 信息面板 | `clients/godot/scripts/ui/observer_panel.gd` |

### 4.4 NPC 数量调整：4 核心 + 2 stub

- **4 核心 NPC**（kai / mira / bram / lena）：完整 motivationProfile / capabilityPreferences / heuristicSeeds 数据
- **2 stub NPC**（tomas / orren）：schema 占位，使用默认权重，行为简化

每个核心 NPC 必须能撑起一篇 blog 文章的深度。

### 4.5 Eval 是 Phase 2 硬验收线

Phase 2 收口标准：

- `npm.cmd run eval:rule` 通过
- L1 scenario suite 全部通过
- 至少 1 次 ablation 实验数据（关闭 subjective_memory 或 heuristic_library，对比关键指标）
- 规则版 NPC 决策周期可稳定运行 24 游戏小时不崩溃
- Debug Trace 可完整解释任意一次决策

**2026-05-20 研究向硬验收**：

- 至少 3 个 process-constrained GoalSpec。
- 至少 1 个 Hard Delegation baseline 可运行。
- 至少 1 个关系记忆 ablation 可运行：No Subjective Memory / No Relationship Edge / Shuffled Memory Owner / Evidence-Link Removal 四选一。
- Eval 输出 mean/std/n，不只输出 pass/fail。
- 至少 1 张 `ablation_comparison.json` 能比较 Full vs Hard Delegation vs No Memory。
- Counterfactual Replay 能证明至少一类关系记忆对 Arbitration winner 有因果影响。
- 任意关键目标状态变化必须能追溯到 `source_event_ids` 或 `trace_refs`。

不达标不进入 Phase 3。详见 [`agent_loop_architecture.md`](./agent_loop_architecture.md) §10、§13.6，以及 [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md) §8。

### 4.6 Phase 2 开发线推荐

| 开发线 | 写入范围 | 阻塞依赖 |
| --- | --- | --- |
| 后端骨架线 | `backend/app/tools/`、`backend/app/runtime/`、`backend/app/memory/`、`backend/app/world/entities/` | 无 |
| Eval 线 | `scripts/run_agent_eval.py`、`backend/app/eval/` | 后端骨架线先到位 |
| Godot 观察者线 | `clients/godot/scripts/ui/observer_panel.gd`、`clients/godot/scripts/observer_mode/` | 后端骨架线 API 先到位 |
| 内容 schema 线 | NPC 深度卡新增 motivationProfile / capabilityPreferences / heuristicSeeds 占位 | 无（schema-only） |
| 资产线 | 仅维持，不阻塞 Phase 2 | 独立 |
| 文档治理 | 持续更新 current_status / goal_board | 持续 |

## 5. Phase 3-6 概述（待激活时细化）

### Phase 3 · 内容填充期

- 5 作物 × 5 阶段实现
- 25 物品全部实现
- 30 工具全部实现
- 4 核心 NPC 完整 motivationProfile / capabilityPreferences / heuristicSeeds 数据
- L2/L3 scenario suite 完整
- 资产批次 B1-B5 落地
- Reflector + LLM 增强 BiasFilter
- 验收：NPC 自己种田、开店、做饭、社交，不需要玩家干预；启发式经验首次可观测

### Phase 4 · 玩家成为变量

- 把 `gossip.propagation_validated` 升级为"真的写入 NPC 记忆 + 关系扩散"
- 玩家行为目击纳入 ResultObserver
- 观察者模式因果链追溯 UI（点击 NPC 反应 → 展开 6 跳因果树）
- 信念模型（belief_about）首次接入决策
- 验收：玩家送花给 A，B 看到了，30 游戏分钟后 C 在酒馆议论；玩家可点击 C 看到完整因果链

### Phase 5 · 涌现式叙事

- 写第 2、3、4 个 Event Skill（情人冲突、店铺危机、流浪商人到访）
- Director Beat 队列引入优先级、衰减、冲突解决
- 多日循环 + 启发式演化展示
- "今日新闻"UI 元素让玩家感知导演在工作
- 公开 dataset 第一版（24 游戏日运行结果）
- 验收：第二天小镇和第一天不一样；某 NPC 因失败积累形成新行为模式

### Phase 6 · 生产化打磨

- LLM 成本分层：强模型用于 Director，便宜模型用于背景 NPC，规则用于 fallback
- 存档、断线恢复、windowed Demo 模式
- Web Debug Console 公开版（精简版可在浏览器运行）
- 技术博客主文 + 3-5 个短录屏 + dataset 发布
- 作品集页面

## 6. 与现有文档的关系

| 文档 | 关系处理 |
| --- | --- |
| `docs/project_vision.md` | 已重写：新定位"可解释多 Agent 叙事运行时"，5 条核心创新点 |
| `docs/agentic_game_design.md` | 不变，作为 Director / Skill / 多层 Agent 的设计源 |
| `docs/agent_loop_architecture.md` | **新事实源**：NPC agent loop 三层工具、动机系统、记忆架构、启发式学习、仲裁、Eval |
| `docs/world_entity_model.md` | **新事实源**：世界实体 schema + 工具空间 |
| `docs/gameplay_system_architecture.md` | 已重写第 2.4 节：软日程 → 动机系统 |
| `docs/npc_deep_card_spec.md` | Phase 2 启动时增补 motivationProfile / capabilityPreferences / heuristicSeeds 字段 |
| `docs/archive/vertical_slice_spec.md` | 已归档；切片范围被新阶段定义和 `world_entity_model.md` 覆盖 |
| `docs/archive/implementation_plan.md` | 已归档；本文档取代其执行依据角色 |
| `docs/archive/core_map.md` | 已归档；结论吸收到 `agent_loop_architecture.md` + `world_entity_model.md` + 本文档 Phase 2 设计 |
| `docs/current_status.md` | 持续更新：Phase 1 收口事实、Phase 2 启动准备 |
| `docs/goal_board.md` | 持续更新：Phase 1 收口 → Phase 2 骨架开发线 |
| `docs/agent_context.md` | 已更新指向新核心文档 |

## 6. 验收命令

每次推进 + 文档收口时运行：

```powershell
npm.cmd run context:check
npm.cmd run check
npm.cmd run smoke
npm.cmd run asset:check
npm.cmd run client:env
npm.cmd run client:run:check
git diff --check
```

阶段 1 内新增建议命令（具体实现后落地）：

```powershell
# 验证 tick API 路径稳定
curl.exe -X POST http://localhost:8787/api/world/tick -H "Content-Type: application/json" -d "{\"deltaSeconds\":5}"
# 验证 SSE 事件流
curl.exe -N http://localhost:8787/api/events
```

## 7. 立即接续步骤

### Phase 1 收口（已完成）

1. 2026-05-21 主人确认 Phase 1 可以收口。
2. `world_main.tscn`、tick 闭环、NPC 移动 / 行动、HUD、`E` talk、`WorldPulsePanel` 与远处事件提示进入完成基线。

### Phase 2 启动条件

1. Phase 1 已收口；`current_status.md` / `goal_board.md` 已同步。
2. `docs/agent_loop_architecture.md` 已落地（已完成）。
3. `docs/world_entity_model.md` 已落地（已完成）。
4. NPC 深度卡 schema 已增补 motivationProfile / capabilityPreferences / heuristicSeeds 三个字段（schema only，数据 Phase 3 填）。
5. `npm.cmd run context:check` 通过、`git diff --check` 通过。

### Phase 2 第一组开工动作

- **后端骨架线**：新建 `backend/app/tools/`、`backend/app/runtime/motivation_engine.py`、`backend/app/memory/subjective.py` 雏形 + 单元测试。
- **Eval 线**：新建 `scripts/run_agent_eval.py` 雏形 + L1 scenario 第一个用例。
- **Godot 观察者线**：先做"按 Tab 切换 + 点击 NPC 显示空白面板"最小骨架。
- **内容 schema 线**：占位字段已补；实际 4 核心 NPC 数据填充放 Phase 3。

### Phase 2 推进前必做

确认完整 Phase 2 总骨架仍以本文 §4.3 的 15 项为准；[`agent_loop_architecture.md`](./agent_loop_architecture.md) §13.3 仅是 Agent Loop 内部 11 项清单，避免开发线漂移。

## 8. 维护规则

- 本文档是 Phase 1 / Phase 2 内的"路线源"，**不复制源设计长文**。NPC agent loop 细节去 `agent_loop_architecture.md`，世界实体 schema 去 `world_entity_model.md`。
- Phase 推进过程中如有决策调整，先更新对应阶段的"必须一次性到位的骨架"清单，再开始实施。
- 任何已完成项必须有命令验证证据；任何未验证项必须显式标注 `manual unverified`。
- Phase 3-6 在被激活前不细化，避免规划幻觉。
