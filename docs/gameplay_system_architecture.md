---
status: active
owner_lane: godot-client
last_verified: 2026-05-22
startup_load: on-demand
source_of_truth: true
scope: gameplay loop, map interactions, motivation-driven npc actions, godot/backend boundaries
---

# 游戏本体架构定调：可解释多 Agent 叙事运行时的可玩切片

> 状态更新时间：2026-05-22
> 本文用于约束 `Loomstead` 的游戏本体路线，定义 Godot 切片如何承载 [`agent_loop_architecture.md`](./agent_loop_architecture.md) 定义的 NPC agent loop。后续客户端、后端玩法系统、资产、Debug 与无人值守 goal 都应先对齐本文。
> 边界：本文聚焦"游戏切片如何呈现 agent 系统"。NPC 决策机制详见 `agent_loop_architecture.md`，世界实体 schema 详见 `world_entity_model.md`。

## 1. 核心结论

`Loomstead` 的游戏本体目标是 **由多层 Agent 系统驱动的二次元轻幻想田园生活模拟 RPG**。

首版内容量可以很小，系统结构需要提前按正式游戏骨架设计：

- 玩家在地图中移动、靠近角色或物体并触发交互。
- NPC 拥有角色目标、关系、记忆、当前意图和可解释行动来源。
- 导演层控制一天中的节奏、舞台焦点、事件压力和 NPC 聚散密度。
- NPC 的具体行动由角色卡、世界状态、局势 brief、记忆、关系和可用工具共同决定。
- 种田、背包、送礼、关系、事件、记忆和夜间反思形成闭环。
- Debug / 研究控制台服务解释和作品集展示，主游戏界面服务沉浸体验。

本轮特别确认：**首版不采用固定排班式 NPC 日程作为核心玩法**。NPC 的出现地点和行动节奏应由“NeedAccumulator / MotivationEngine / 世界约束 / 导演层节奏 / NPC 主观判断”共同生成。设计师提供生活规律、场景机会和事件压力，LLM NPC 在边界内保留尽可能多的自主性。

2026-05-18 进一步确认：项目方向不是“传统田园 RPG + LLM 对话”，而是 **LLM Agent 社会本身的可游玩化**。小镇自运转不能只依赖后端事件文本，必须落成玩家可见的生活机器：地图生活对象、行动表现模板、NPC 今日意图、行动碰撞、玩家介入入口和离屏结果痕迹共同构成体验；后端事件负责事实和权威状态，Godot 必须把事实演成画面里的生活片段。

## 2. 设计原则

### 2.1 地图优先

玩家的主要操作应发生在地图里：

- 移动到地点、区域、NPC、物体或事件入口。
- 靠近可交互对象后出现提示。
- 触发交互后进入 Visual Novel 对话层或事件演出层。
- UI 列表只作为辅助导航、状态查看或 Debug 入口。

### 2.2 玩法系统服务 Agent 社会

种田、背包、送礼、时间推进和事件选择都要进入 Agent 系统：

```text
玩家种出作物
  -> 作物进入背包
  -> 送礼或用于事件
  -> 改变关系、记忆和事件状态
  -> NPC 夜间反思
  -> 第二天对话、意图和事件倾向发生变化
```

如果某个玩法无法影响世界状态、NPC 记忆、关系或事件，它只能作为临时表现功能，不能成为长期核心系统。

### 2.3 导演层负责节奏，NPC 保留自主性

导演层的职责：

- 控制一天中的阶段节奏。
- 选择当前舞台焦点，例如农场新手引导、广场认识居民、酒馆事件压力。
- 激活 Event Skill。
- 给相关 NPC 下发局势 brief。
- 控制当前场景的 NPC 聚散密度，避免所有居民同时堆在一个画面。
- 生成可验证、可过期的 Director Beat。

NPC 的职责：

- 根据自身角色卡、目标、关系、记忆、状态和 brief 选择行动。
- 通过合法工具行动影响世界。
- 对同一事件形成主观解释。
- 在夜间反思中沉淀长期印象。

导演层可以安排“谁更可能进入玩家视野”和“什么冲突值得推到台前”，具体台词、态度、记忆解释和行动选择交给 NPC Agent。

### 2.4 动机系统驱动行为（替换软日程）

> 2026-05-19 项目重定位后，软日程系统整体退役。NPC 行为由 **MotivationEngine** 驱动，详见 [`agent_loop_architecture.md`](./agent_loop_architecture.md)。

每个 NPC 拥有 `motivationProfile`，包含 4 类需求（生理 / 经济 / 社交 / 目标），每类带 personality 权重与衰减速率。需求自动累积或衰减，到阈值后触发对应工具的候选选择。

```text
内部需求（NeedAccumulator 自动累积/衰减）
  +
长期目标（NPC 深度卡 goals）
  +
导演层临时偏置（Director Beat）
  +
启发式经验（HeuristicLibrary）
  +
当下情境约束（地点 / 持有物 / 关系）
  ↓
ArbitrationLayer 结构化裁决
  ↓
最迫切需求 + 候选工具集 → 三层路由（Physiological / Vocational / Social-Strategic）
```

`lifeActionPlan` / `npcSchedules` API 字段保留，但语义从"今天的计划"改为"基于当前需求的下一步候选"，给 Godot 客户端做日程可视化用。NPC 不再被锁进固定时间表。

导演层的角色不变：通过 Director Beat 注入临时需求权重偏置（"今晚 social 重要性 +30%"）和临时目标，过期自动消失。导演层不替 NPC 选工具，只调整动机权重。

### 2.5 反 UI 点击化硬约束

后续玩法实现需要遵守以下顺序：

1. 后端先定义合法 action、状态变更、回执和 Debug 证据。
2. Godot 在地图中提供靠近提示、上下文候选、快捷键和 VN 结果展示。
3. 侧栏按钮只能作为调试兜底、无障碍辅助或开发期验证入口。
4. 新增玩法如果只表现为列表按钮，需要同步补地图触发条件、空间锚点和后端权威契约。
5. 新增 NPC 日程只能作为可解释快照或候选，不得把角色锁死到固定排班。

这条约束用于保护系统地基，避免后续在资产、内容和事件规模扩大后产生大量迁移工程。

### 2.6 首版缩小内容，保留扩展骨架

近期可以重点打磨 3 个核心 NPC、3 个地点、1 种作物和 1 个事件，但数据结构要支持：

- 更多地点和室内外切换。
- 更多作物和物品。
- 更多 NPC、家庭和关系网络。
- 多日循环。
- 多个 Event Skill。
- 恋爱线、委托、节日和长期剧情。

### 2.7 自运转小镇必须先可见

“NPC 像独立 Agent 一样行动”不能只表现为后端生成事件或 Debug 日志。首版自运转小镇要优先落成以下玩家可见结构：

1. **生活对象**：地图上有田块、水井、仓箱、公告板、摊位、喷泉、节日桌、舞台、吧台、食材箱和餐桌等可被 NPC 与玩家共同使用的对象。
2. **行动片段**：NPC 的工具调用要演成短动作片段，例如走向对象、面向对象、显示头顶图标、冒出短气泡、持续一段时间并留下状态变化。
3. **日常需求**：NPC 行动来自可理解的生活驱动力，例如排练、送货、摆摊、催账、修理、采药、准备节日或寻找某人。
4. **行动碰撞**：当两个 NPC 争夺同一对象、目标冲突、关系紧张或在同一地点相遇时，可以触发可见冲突、合作、闲聊或事件苗头。
5. **玩家介入**：玩家靠近正在发生的行动时，可以交谈、帮忙、送物、旁观、插手或打断，结果写入关系、记忆和世界状态。
6. **离屏痕迹**：玩家不在场时可以轻量模拟；玩家之后来到现场时，应看到公告变化、物资箱状态、NPC 情绪、位置或对话引用等痕迹。

后端事件是事实账本和权威驱动，不等于游戏体验本身。Godot 需要把 `npc.action_started`、`npc.action_completed`、`event_skill`、记忆与关系变化翻译为地图对象状态、NPC 小人动作、图标、气泡、VN 插入和 HUD 提示。

## 3. 游戏本体分层架构

```text
Godot Presentation Layer
  地图、角色、交互提示、VN 对话、HUD、设置、Debug 展开层

Player Interaction Layer
  玩家移动、靠近交互、选择动作、背包选择、事件选择

Gameplay Systems Layer
  时间、行动预算、农场、背包、物品、送礼、关系、任务、事件

World / Simulation Authority
  权威状态、合法行动执行、事件流、地图位置、物品和关系一致性

Director Flow Layer
  世界摘要、张力扫描、舞台焦点、Event Skill 激活、NPC brief、节奏控制

NPC Agent Layer
  角色卡、目标、记忆、关系、主观判断、工具行动、夜间反思

Memory / RAG Layer
  短期事件、长期记忆、夜间摘要、关系证据、语义检索

Debug / Explainability Layer
  Prompt、模型输出、工具调用、记忆写入、关系变化、成本、fallback
```

### 3.1 Godot Presentation Layer

Godot 负责玩家直接感知的游戏形态：

- 地图场景和背景。
- 玩家角色移动。
- NPC 小人、可见状态和交互提示。
- Visual Novel 对话层。
- HUD：日期、时间段、地点、当前目标、背包摘要。
- 设置：UI 缩放、窗口模式、文本速度、Debug 开关。
- Debug 展开层：只在需要时显示 Agent 证据。

Godot 不持有权威世界事实；它展示后端状态并提交玩家动作。

### 3.2 Player Interaction Layer

玩家动作应逐步从 UI 按钮迁移到地图交互：

| 动作 | 地图表现 | 后端动作 |
| --- | --- | --- |
| 移动 | WASD / 点击目标点 / 地点出口 | `move` / `move_to_anchor` |
| 查看 | 靠近公告板、事件点、NPC marker | `inspect` |
| 聊天 | 靠近 NPC 后出现 talk 提示 | `talk` |
| 送礼 | 选择背包物品后点 NPC | `give_gift` |
| 种田 | 靠近田块后播种、浇水、收获 | `farm_action` |
| 参与事件 | 靠近事件 marker 或事件 NPC | `attend_event` |
| 结束时段 | 回家、睡觉或消耗行动预算 | `end_phase` |

UI 列表可以保留在 Debug 或辅助模式中，默认游玩路线应以地图行动为主。

### 3.3 Gameplay Systems Layer

首版最小玩法系统以 `world_entities.v1` typed schema 为统一数据契约，实体字段和工具空间详见 [`world_entity_model.md`](./world_entity_model.md)。

1. **时间段系统**
   - `morning` / `noon` / `afternoon` / `evening` / `night`。
   - 行动会消耗行动预算或推进时段。
   - 夜晚触发反思、记忆沉淀和次日摘要。

2. **农场系统**
   - 当前 typed schema 覆盖 FarmPlot，首版只需要少量田块。
   - 作物阶段：空地、已播种、已浇水、可收获。
   - 首版可只做 1 种作物，例如 `starlight_turnip` 或 `farm_flower`。

3. **背包和物品系统**
   - 当前 typed schema 覆盖 Item、Inventory 和 Shop。
   - 物品来源：初始赠送、农场收获、事件奖励。
   - 物品用途：送礼、事件消耗、任务条件。

4. **关系系统**
   - 关系变化来自聊天、送礼、事件选择和 NPC 主观反应。
   - 关系变化必须写入事件流、RelationshipEdge 和主观记忆证据。

5. **任务 / 当前目标系统**
   - 用轻量目标引导玩家，例如“去广场认识居民”“准备一份作物礼物”“傍晚去酒馆看看”。
   - 当前目标由后端生成，Godot 展示。

6. **事件系统**
   - Event Skill 提供情境、参与者、可用选择、后果类型和资产提示。
   - 玩家选择和作物 / 关系 / 记忆状态共同影响事件结果。

### 3.4 World / Simulation Authority

后端继续持有权威状态：

- 时间和时段。
- 玩家位置、朝向、背包、行动预算。
- 地点、区域、交互点。
- NPC 当前位置、可见性、当前意图和状态。
- 农场田块和作物。
- 物品、关系、记忆、事件状态。
- EventStore 和 Debug 记录。

所有状态改变都必须通过合法 action：

```text
move
move_to_anchor
inspect
talk
give_gift
farm_action
attend_event
end_phase
npc_action
director_beat
reflect
```

### 3.5 Director Flow Layer

导演层面向游戏节奏，而非固定脚本：

- 按时段读取 `WorldDigest`。
- 扫描关系张力、资源短缺、玩家行为和事件触发条件。
- 选择当前舞台焦点。
- 决定哪些 NPC 更适合进入玩家视野。
- 激活或推迟 Event Skill。
- 下发 NPC brief。
- 控制当前场景的可见 NPC 数量和冲突密度。

示例：

```json
{
  "beatType": "scene_focus",
  "phase": "afternoon",
  "sceneId": "plaza",
  "focus": "让玩家感到星灯祭供应紧张正在发酵",
  "spotlightNpcIds": ["kai", "bram", "mira"],
  "optionalNpcIds": ["lena", "orren"],
  "constraints": [
    "不要强制 NPC 达成和解",
    "避免所有居民同时聚集在同一地点",
    "优先让玩家通过地图靠近和对话发现问题"
  ]
}
```

### 3.6 NPC Agent Layer

NPC 行动由以下输入共同决定：

- 角色卡和说话风格。
- 长期目标。
- 当前状态：体力、情绪、压力、关系。
- 需求权重与 MotivationEngine 当前候选。
- 当前地点可用交互。
- 近期记忆和长期记忆。
- 与玩家和其他 NPC 的关系。
- 当前 Event Skill brief。
- Director Beat 中的舞台焦点。
- 可用工具列表。

NPC 输出应落到结构化行动：

```json
{
  "agentId": "kai",
  "intent": "维持酒馆节日气氛，同时试探玩家愿不愿意帮忙",
  "action": {
    "type": "talk",
    "targetId": "player",
    "topic": "starlight_shortage"
  },
  "confidence": 0.72,
  "memoryRefs": ["mem_kai_001", "event_starlight_shortage"],
  "directorBeatId": "dir_afternoon_001"
}
```

### 3.7 Memory / RAG Layer

记忆系统要同时服务游戏体验和 Debug：

- 游戏体验：NPC 第二次对话能体现之前发生的事。
- 关系演化：同一事件被不同 NPC 解释为不同印象。
- 事件推进：导演层能看到某个张力是否已经充分发酵。
- Debug：玩家能在研究控制台看到“为什么 NPC 这样回应”。

## 4. 场景与地图模型

首版地图可以先采用“静态背景 + 交互锚点 + 小人节点”的实现路线，后续再升级为更完整的 tile / navigation 地图。

### 4.1 Location

地点表示可进入的大场景：

```json
{
  "id": "plaza",
  "displayName": "中央广场",
  "backgroundRef": "plaza_day_anime",
  "defaultEntryAnchorId": "plaza_gate",
  "phaseAffinity": ["morning", "afternoon"],
  "tags": ["public", "festival", "market"]
}
```

### 4.2 Anchor

锚点表示地点内可站位、可交互或可触发事件的位置：

```json
{
  "id": "plaza_fountain",
  "locationId": "plaza",
  "kind": "social_spot",
  "screenPosition": {"x": 0.54, "y": 0.62},
  "capacity": 3,
  "tags": ["chat", "public", "festival_view"]
}
```

### 4.3 Interactable

可交互物体表示公告板、田块、酒馆舞台、事件 marker 等：

```json
{
  "id": "farm_plot_01",
  "locationId": "farm",
  "anchorId": "farm_field",
  "kind": "farm_plot",
  "actions": ["plant", "water", "harvest"],
  "state": {"cropId": null, "stage": "empty"}
}
```

### 4.4 Presence

NPC 是否出现在某地点由 Presence 结构表达：

```json
{
  "agentId": "mira",
  "locationId": "plaza",
  "anchorId": "market_stall",
  "visibility": "visible",
  "intent": "采购星灯祭需要的干货并观察供应问题",
  "source": "director_spotlight",
  "expiresAtPhase": "afternoon"
}
```

`source` 用于解释来源：

- `habit`：生活习惯权重。
- `director_spotlight`：导演层推到玩家视野。
- `event_skill`：事件参与者。
- `relationship_pull`：关系或记忆牵引。
- `offscreen_simulation`：后台模拟结果。

### 4.5 首版生活对象清单

首版不需要完整 tile map，但至少要让三处地点拥有可被 NPC 和玩家共同使用的生活对象：

| 地点 | 对象 | 用途 |
| --- | --- | --- |
| 农场 | `farm_plot_01` / `farm_plot_02` / `well` / `storage_box` | 播种、浇水、收获、存取作物、NPC 检查农务 |
| 广场 | `notice_board` / `market_stall` / `fountain` / `festival_table` | 公告、摆摊、闲聊、节日准备、公共事件苗头 |
| 酒馆 | `tavern_stage` / `bar_counter` / `supply_crate` / `tavern_table` | 排练、招待、食材冲突、吃饭、社交 |

这些对象是 NPC 行动落点，也是玩家介入小镇生活的入口。新增对象必须同时考虑：地图位置、可用动作、当前状态、可使用 NPC、玩家靠近交互和离屏结果痕迹。

### 4.6 行动表现模板

首版 NPC 工具行动统一映射到少量表现模板，避免每种行为都单独做演出：

| 模板 | 画面表现 | 典型用途 |
| --- | --- | --- |
| `move_to` | NPC 走向目标对象或锚点 | 去农场、去公告板、进酒馆 |
| `work_at` | 面向对象，头顶工具图标，短气泡，持续计时 | 修理、摆摊、检查田块、排练 |
| `talk_to` | 两名角色靠近并面对面，交替短气泡 | 闲聊、问候、传播消息 |
| `inspect_object` | 面向对象并显示观察图标 | 看公告、检查物资箱、查看田块 |
| `carry_item` | 从一个对象移动到另一个对象，显示小货物图标 | 送货、搬作物、补给酒馆 |
| `rest_at` | 坐下或停留，低频气泡 | 吃饭、休息、等人 |
| `prepare_event` | 事件对象轻微高亮，NPC 聚集并显示节日图标 | 星灯祭准备 |
| `conflict_talk` | 两名 NPC 面对面，感叹号或紧张气泡 | 欠账、供货、误解、站队 |

模板执行期间，Godot 负责 sprite tween、idle bobbing、图标、气泡和交互提示；后端负责行动合法性、状态变更、事件流和记忆 / 关系写入。

## 5. 第一天垂直切片重定向

近期目标调整为：**内容很少、结构完整的一天生活循环**。

### 5.1 内容规模

首版可以重点打磨：

- 3 个地点：农场、中央广场、月猫酒馆。
- 3 个重点 NPC：米娅、凯娅、布兰娜。
- 其他 3 个首发 NPC 保留数据、立绘、小人和轻量出现机会。
- 1 种作物。
- 1 个事件：星灯祭供应短缺。
- 1 个夜间反思流程。

### 5.2 推荐体验流

```text
早晨：农场醒来
  -> 学会移动和检查田块
  -> 获得或种下第一份作物

上午：去广场
  -> 在地图上遇到米娅或其他居民
  -> 通过靠近 NPC 进入 VN 对话
  -> 写入第一次见面记忆

下午：回农场或继续社交
  -> 收获 / 准备礼物
  -> 送礼影响关系
  -> 导演层开始推送星灯祭供应紧张

傍晚：月猫酒馆
  -> 事件 marker 出现
  -> 凯娅和布兰娜围绕供应问题形成张力
  -> 玩家选择捐作物、调解、站队或旁观

夜晚：回家休息
  -> NPC 生成主观反思
  -> 玩家看到日记 / 记忆卡片摘要
  -> 第二天对话或目标受白天选择影响
```

### 5.3 验收标准

第一天生活循环验收应关注：

- 玩家能在地图中移动并靠近对象。
- 至少 1 个农场对象能播种、浇水或收获。
- 背包能接收作物。
- 作物能送礼或用于星灯祭事件。
- NPC 出现位置有解释来源，且不会全员堆在同一屏幕。
- 至少 1 个 NPC 的第二次回应引用白天记忆。
- 夜间反思写入 EventStore 和 memory。
- Debug 控制台能解释事件、关系、记忆和模型调用。

## 6. Godot 客户端模块建议

建议把当前单个 `main.gd` 的职责逐步拆开：

| 模块 | 职责 |
| --- | --- |
| `GameRoot` | 装配全局节点、服务和层级。 |
| `MapSceneController` | 管理当前地点背景、锚点、NPC presence、interactable。 |
| `PlayerController` | 玩家移动、输入、朝向和靠近检测。 |
| `ActorController` | NPC 小人、姓名、marker、点击 / 靠近交互。 |
| `InteractionPrompt` | 展示 talk / gift / inspect / farm action 提示。 |
| `VNOverlay` | 半身立绘、姓名牌、文本、选项、事件结果。 |
| `HudController` | 时间、地点、当前目标、背包摘要、设置按钮。 |
| `DebugOverlay` | 默认隐藏，展示 Agent 证据和事件流。 |
| `UiTheme` | 二次元轻幻想 UI 样式、4K 自适应缩放、通用按钮和面板样式。 |

当前 UI 视觉重构可以继续推进，但下一轮客户端架构目标应转为：**把 UI demo 收束成地图游玩主循环**。

## 7. 后端数据契约建议

### 7.1 World State 增量字段

后续 `GET /api/world/state` 可逐步增加：

```json
{
  "clock": {
    "day": 1,
    "phase": "afternoon",
    "actionBudget": 2
  },
  "player": {
    "locationId": "farm",
    "anchorId": "farm_house_door",
    "inventory": []
  },
  "locations": [],
  "anchors": [],
  "interactables": [],
  "npcPresence": [],
  "currentObjective": {},
  "availableInteractions": []
}
```

### 7.2 Player Action 增量类型

```json
{
  "type": "farm_action",
  "actorId": "player",
  "locationId": "farm",
  "interactableId": "farm_plot_01",
  "action": "plant",
  "itemId": "starlight_turnip_seed"
}
```

建议新增动作类型：

- `move_to_anchor`
- `farm_action`
- `use_item`
- `end_phase`
- `inspect_interactable`

### 7.3 NPC Action 结构

NPC 后续行动也应走结构化工具：

```json
{
  "type": "npc_action",
  "agentId": "bram",
  "intent": "检查农场供货并避免酒馆继续赊账",
  "action": {
    "type": "move_to_anchor",
    "locationId": "farm",
    "anchorId": "farm_field"
  },
  "source": "agent_decision",
  "directorBeatId": "dir_supply_pressure_001"
}
```

## 8. 近期开发路线

### M0：本定调落地

- 新增本文。
- 文档索引、项目愿景和目标看板引用本文。
- 后续 goal 必须以本文为游戏本体边界。

### M1：地图主循环替代面板主循环

- 玩家可在当前地点移动。
- NPC presence 从后端状态生成。
- 靠近 NPC / 事件 / 田块时出现交互提示。
- VN 层作为交互结果展示。
- Debug 面板默认隐藏。

### M1.5：权威生活行动快照

- 后端输出 `npcSchedules` 与 `lifeActionPlan`。
- 快照由 NPC 深度卡 seeds、Presence、锚点和交互体生成。
- LLM 不能直接改写世界状态；Runtime 继续持有状态变更权。
- Godot 先做轻量可视化，再把候选动作接入地图上下文提示。

### M1.6：自运转小镇可见化

- 为农场、广场和酒馆补齐首版生活对象。
- 把 `npc.action_*` 映射到 `move_to`、`work_at`、`talk_to`、`carry_item`、`prepare_event`、`conflict_talk` 等表现模板。
- 为每个重点 NPC 配置 2-3 个 Day 1 今日意图，例如凯娅排练 / 找食材 / 拉人参加活动，布兰娜检查田块 / 送货 / 催账，米娅摆摊 / 贴公告 / 收购作物。
- 当 NPC 在同一对象或同一地点发生目标冲突时，生成可见闲聊、合作或冲突苗头。
- 玩家靠近正在发生的行动时，出现交谈、帮忙、送物、旁观或插手入口。
- 玩家不在场的行动要留下对象状态、NPC 情绪、公告、物资或后续台词痕迹。

### M2：最小农场和背包闭环

- 农场 3 个田块。
- 1 种种子 / 作物。
- 播种、浇水、收获。
- 背包展示和物品选择。
- 作物可送礼或用于事件。

### M3：导演层驱动的 NPC Presence

- 后端输出 `npcPresence`。
- NeedAccumulator、Director Beat、Event Skill、关系牵引共同影响 NPC 出现。
- Godot 按 `npcPresence` 渲染当前场景 NPC。
- Debug 显示每个 NPC 出现的 `source` 和 `intent`。

### M4：第一天完整闭环

- 时间段推进。
- 星灯祭事件使用作物 / 关系 / 记忆条件。
- 夜间反思。
- 第二次对话引用白天记忆。
- 可录屏演示。

## 9. 暂不阻塞的开放问题

这些问题无需阻塞下一轮开发，可在实现中逐步验证：

1. **地图形态**：首版继续使用静态背景 + 锚点，小地图或 tile map 后续专项推进。
2. **时间粒度**：首版使用时段 + 行动预算，真实实时钟和精细日程后续扩展。
3. **NPC 规模**：首版保留 6 个 NPC 数据，重点体验先围绕 3 个核心 NPC 打磨。
4. **农场深度**：首版只做 1 种作物和少量田块，经济系统后续扩展。
5. **动画规模**：首版小人可用 idle + 简单移动，逐帧行走动画后续资产专项。
6. **Debug 可见性**：主游戏默认隐藏 Debug，开发构建保留快捷入口。

## 10. 给后续 goal 的边界句

后续所有客户端和玩法系统 goal 可以复用这段约束：

```text
Loomstead 的游戏本体已经定调为涌现式田园生活模拟 RPG。后续实现要把玩家主要交互迁移到地图、移动、靠近提示和 VN 演出层；NPC 位置与行动由 NeedAccumulator、MotivationEngine、世界约束、Director Beat、Event Skill 和 NPC 自主判断共同生成；不要把 NPC 写死成固定排班，也不要继续把主体验扩写成背景图加 UI 按钮列表。后端保持权威状态，Godot 只展示状态并提交合法动作。
```
