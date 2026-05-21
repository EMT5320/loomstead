---
status: active
owner_lane: backend-director
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: multi-layer agent design, director system, event skills, memory, and model routing
---

# 多层 Agent 游戏系统设计

> 状态更新时间：2026-05-15
> 本文沉淀 `Loomstead` 后续开发的核心定调：项目把游戏世界设计为由多层 Agent、世界规则、事件 Skill 和可解释调试链路共同驱动的可游玩小镇社会，避免停留在传统固定剧情游戏加 LLM 对话的浅层形态。

## 核心结论

`Loomstead` 的长期方向是 **可被游玩的涌现社会**。

设计师负责提供土壤、舞台、规则和压力源；LLM Agent 负责在这些边界内做主观判断、表达、记忆和关系演化。游戏体验来自两部分的结合：

- 固定系统：世界规则、地点、物品、角色卡、关系数值、事件状态、工具行动、Debug 记录。
- 涌现系统：NPC 对事件的主观解释、关系变化后的后续态度、夜间反思、事件 Skill 激活后的现场规划。

这个方向保留早期“LLM 驱动 Agent 沙盒小镇”的初心，同时让它具备游戏客户端、视觉演出、首日事件和作品集展示所需要的可控结构。

## 当前设计冲突

### 传统内容与 Agent 自主性的冲突

传统游戏通常由设计师预先写好剧情、分支、任务条件和 NPC 行为逻辑。玩家每次游玩会看到大体稳定的内容。

`Loomstead` 的核心价值在于 NPC 具备人设、目标、关系和记忆后的自主演化。如果强制要求每个 LLM NPC 都走向设计师预设结局，会削弱项目最有辨识度的部分。

更合适的边界是：

- 固定剧情改为情境种子。
- 固定任务改为可激活事件 Skill。
- 固定 NPC 台词改为角色卡、记忆和局势约束下的现场表达。
- 固定结局改为可验证后果类型，例如关系变化、记忆写入、事件状态变化、资源变化。

### 涌现内容与美术覆盖的冲突

LLM 能产生大量不可预先枚举的细节。美术资产无法覆盖所有可能剧情。

因此美术层需要覆盖表现语法，不追逐每一种剧情可能：

- 固定地点背景承载大部分场景。
- 固定角色立绘和表情差分承载人物反应。
- 通用事件卡片、关系变化提示和记忆卡片承载涌现内容。
- 少量关键 CG 只覆盖高价值舞台，例如星灯祭供应短缺。
- Debug 时间线展示 Agent 推理链路，补足纯画面无法表达的系统深度。

### 导演层稳定性与延迟的冲突

如果把导演层做成每个 tick 都读取全量世界、控制所有 NPC、决定整个游戏方向的单个大模型调用，会出现几个风险：

- 上下文太大，成本和延迟高。
- 单点幻觉会影响整个世界。
- 模型输出难以稳定落入可执行结构。
- 玩家即时体验会被强模型思考时间阻塞。

因此导演层应定义为一个 **导演系统**，由摘要、检索、规则、队列、强模型和校验器共同组成。前沿长上下文模型只处理少数高价值规划，不承担高频 tick。

## 多层 Agent 架构

### 1. World / Simulation Layer

世界规则层是权威状态持有者，负责保证游戏状态合法。

职责：

- 时间、地点、NPC、玩家、物品、事件、关系、记忆状态。
- 行动工具执行，例如移动、聊天、送礼、参加事件、休息、工作。
- 事件日志和状态快照。
- 对模型输出做结构校验和权限校验。

设计原则：

- LLM 只能提出计划或工具调用意图。
- 世界状态只能由 Runtime 执行合法工具后修改。
- 所有关键变化进入 EventStore，支持 Debug 和回放。

### 2. Director System

导演系统是主代理层，负责节奏规划、事件激活、压力源分发和风险控制。

它不直接替 NPC 决定情绪、台词或最终态度。它负责提出阶段性世界目标，例如：

- 当前时段是否需要激活事件 Skill。
- 哪些关系张力值得推到玩家面前。
- 哪些 NPC 应收到局势 brief。
- 某个事件是否应继续发酵、收束或转入夜间反思。

导演系统由多个部件组成：

| 部件 | 职责 | 推荐实现 |
| --- | --- | --- |
| `WorldDigestBuilder` | 把原始世界压缩成稳定摘要 | 规则 + 模板 |
| `TensionDetector` | 扫描高张力关系、资源短缺、异常状态 | 规则优先，小模型可选 |
| `SkillRouter` | 根据触发条件筛选候选事件 Skill | 规则 + 标签匹配 |
| `DirectorPlanner` | 对高价值局势做阶段规划 | 长上下文强模型，低频调用 |
| `DirectorValidator` | 校验导演输出 schema、权限和世界版本 | 纯代码 |
| `DirectorQueueManager` | 管理异步 Director Beat 队列 | 纯代码 |
| `ModelRouter` | 根据任务价值选择 Pro / Flash / Rule | 配置驱动 |
| `DigestSummarizer` | 后台生成世界摘要和角色摘要 | Flash / 规则 / 批处理 |

### 3. Event Skill Layer

事件 Skill 是渐进式加载的情境模块。

平时导演层只加载轻量触发条件。当满足条件后，系统加载完整 Skill 内容，再将不同视角的 brief 分发给导演和相关 NPC。

事件 Skill 不等同于固定剧情。它应提供：

- 触发条件。
- 参与者。
- 局势背景。
- 角色视角 brief。
- 可用工具。
- 约束边界。
- 可结算后果类型。
- 推荐演出资产。
- Debug 展示字段。

事件 Skill 的生命周期：

```text
dormant
  -> candidate
  -> loaded
  -> active
  -> resolved
  -> reflected
  -> archived
```

### 4. NPC Agent Layer

NPC 是子代理层。每个 NPC 基于自己的角色卡、记忆、关系和导演 brief 自主行动。

NPC 每轮上下文应包含：

- 自己的角色卡摘要。
- 当前状态和地点。
- 近期记忆。
- 与附近角色的关系。
- 导演给出的当前局势 brief。
- 可用工具集合。
- 当前事件 Skill 的 NPC 视角信息。

NPC 不应看到全世界完整状态。它看到的是自己能合理知道的内容。

### 5. Player State Agent

玩家仍由真人控制。系统可以有一个 Player State Agent，用于总结玩家风格和历史选择，但不替玩家做操作。

职责：

- 总结玩家偏好，例如倾向调解、偏向某个 NPC、经常送礼。
- 给导演和 NPC 提供“玩家在小镇里的形象”。
- 帮助 NPC 对玩家形成长期印象。

边界：

- 不自动替玩家移动、选择或对话。
- 不把 Debug / 研究控制台视角泄漏到主游戏叙事。

### 6. Memory / RAG Layer

导演层和 NPC 层都需要记忆系统，但读取方式不同。

优先级从高到低：

1. 结构化权威状态：关系、地点、物品、事件状态、时间段。
2. 短期事件摘要：最近若干关键事件和玩家动作。
3. 角色长期记忆：每个 NPC 对人、地点、事件的长期印象。
4. 夜间反思：当天事件沉淀出的主观总结。
5. 向量检索 RAG：按实体、事件类型、标签和语义召回旧事件。

导演层主要读取 `WorldDigest`。原始日志全集保留给 Debug 和回放。

### 7. Presentation / Asset Layer

表现层把涌现内容转成可玩的画面：

- 地点背景。
- 角色半身立绘。
- 表情差分。
- 地图小人。
- 事件卡片。
- 关系变化提示。
- 记忆卡片。
- 夜间日记面板。
- Debug 时间线。

表现层不负责决定世界事实，也不追逐所有可能剧情资产。

### 8. Debug / Explainability Layer

Debug 是项目技术深度的展示窗口。

每个关键链路应能看到：

- Director Beat 输入摘要。
- 候选 Skill 和触发条件。
- 导演模型输出。
- Validator 结果。
- NPC brief。
- NPC 模型输出。
- 工具行动。
- 世界状态变化。
- 关系变化。
- 记忆写入。
- token、延迟、成本和 fallback。

## Director Beat

`Director Beat` 是导演层的基本输出单位。它是异步生成、可验证、可过期的阶段性世界指令。

它不直接修改世界，只进入队列，由 Runtime 在合适 tick 消费。

示例结构：

```json
{
  "directiveId": "dir_001",
  "worldVersion": 128,
  "validFromTick": 130,
  "expiresAtTick": 160,
  "priority": "high",
  "beatType": "activate_event_skill",
  "targetAgents": ["kai", "bram"],
  "goal": "让星灯祭供应冲突进入玩家可感知状态",
  "allowedSkills": ["starlight_festival_shortage"],
  "directorBrief": "酒馆食材不足，凯娅害怕节日冷场，布兰娜担心旧账和供货压力。",
  "npcBriefs": {
    "kai": "你想保住星灯祭气氛，但知道欠账问题已经无法回避。",
    "bram": "你不想再免费供货，但也不希望小镇把你当成破坏节日的人。"
  },
  "constraints": [
    "不强制 NPC 和解",
    "不直接生成最终结局",
    "只能通过合法玩家动作和 NPC 工具行动推进"
  ],
  "cancelIf": [
    "event_already_resolved",
    "player_left_tavern"
  ],
  "assetHints": ["tavern_evening_anime", "starlight_festival_shortage_event"]
}
```

必要字段：

- `worldVersion`：生成时参考的世界版本。
- `validFromTick` / `expiresAtTick`：生效窗口。
- `beatType`：节拍类型，例如激活事件、加压关系、收束事件、进入反思。
- `targetAgents`：受影响 NPC。
- `goal`：阶段目标。
- `constraints`：导演不能越界的规则。
- `cancelIf`：过期或失效条件。

消费规则：

- 如果 `worldVersion` 明显落后，降级为建议或丢弃。
- 如果 `expiresAtTick` 已过，丢弃。
- 如果 `cancelIf` 命中，丢弃。
- 如果 Validator 不通过，进入 Debug 错误事件并 fallback。

## 异步运行模型

### 快循环：世界与 NPC

高频循环负责玩家即时体验和 NPC 日常行为：

- 玩家移动。
- 玩家点击 NPC 对话。
- NPC 低风险日程行动。
- 地点级移动。
- 规则 Provider 或 Flash 模型对话。

这条路径不能等待长上下文强模型。

### 慢循环：导演规划

导演规划低频运行：

- 每个时间段开始。
- 关键玩家行为后。
- 事件 Skill 触发前。
- 事件结算后。
- 夜间总结前。

导演规划可以异步运行，结果进入 Director Beat 队列。玩家和 NPC 在等待期间继续使用当前 brief、规则 fallback 和已排队 beat。

### 后台循环：总结与记忆

后台任务负责：

- 压缩 EventStore。
- 更新 `WorldDigest`。
- 写入长期记忆。
- 为 RAG 建索引。
- 生成夜间反思。

这些任务可以延迟完成，完成后影响后续 tick，不阻塞当前玩家交互。

## 模型分工

模型选择应按任务价值分层。

| 任务 | 推荐模型层级 | 频率 |
| --- | --- | --- |
| 多角色冲突规划、每日主线节奏、复杂复盘 | 长上下文强模型 | 低频 |
| 事件 Skill 触发判断、摘要、短规划 | Flash / 小模型 / 规则 | 中频 |
| NPC 日常对话和即时反应 | Flash | 高频 |
| 高频移动、纯日程、合法性校验 | 规则 | 高频 |
| 记忆压缩和夜间日记草稿 | Flash / 批处理 | 后台 |
| 世界状态修改和权限校验 | 纯代码 | 每次 |

具体模型名以本机配置和实际价格/延迟测试为准。设计上不要把某个供应商或某个上下文窗口当成唯一前提。

## RAG 与长期记忆设计

### WorldDigest

导演层输入应优先使用结构化摘要：

```text
当前时间：Day 1 Evening
玩家位置：tavern
高张力关系：kai-bram conflict=44
活跃压力源：festival_supply_shortage
关键记忆：Branna 认为酒馆欠账；Kaya 害怕节日冷场
候选 skills：starlight_shortage, tavern_gossip, night_reflection
推荐动作：激活事件 / 继续观察 / 推迟
```

### 记忆类型

建议分层：

- `event_memory`：原始事件或压缩事件。
- `relationship_memory`：某 NPC 对另一个角色的长期印象。
- `self_reflection`：夜间日记、目标调整和情绪总结。
- `world_summary`：导演使用的小镇阶段摘要。
- `player_profile_memory`：玩家风格和历史选择总结。

### 检索策略

RAG 检索应同时支持：

- 实体过滤：NPC、玩家、地点、事件。
- 标签过滤：festival、debt、gift、romance、health。
- 时间过滤：当天、本周、长期。
- 关系过滤：高冲突、高亲密、最近变化。
- 语义向量：相似旧事件和旧对话。

导演层每次只拿少量证据，避免长上下文模型被无关信息稀释。

## Event Skill 渐进式加载

### 常驻 Skill Manifest

平时只加载轻量信息：

```json
{
  "skillId": "starlight_festival_shortage",
  "title": "星灯祭供应短缺",
  "trigger": {
    "phase": "evening",
    "locationId": "tavern",
    "requiredTension": [["kai", "bram", "conflict", 35]],
    "requiredItemsOrFlags": ["festival_preparation"]
  },
  "participants": ["kai", "bram", "mira", "lena", "orren", "tomas"],
  "tags": ["festival", "supply", "debt_conflict"],
  "assetHints": ["tavern_evening_anime", "starlight_festival_shortage_event"]
}
```

### 触发后加载完整 Skill

满足条件后再加载：

- 事件背景。
- 导演 brief。
- NPC 分视角 brief。
- 玩家可选行动。
- NPC 可用工具。
- 约束边界。
- 后果类型。
- 资产提示。
- Debug 展示字段。

### NPC 现场规划

事件 Skill 激活后，NPC 不读取完整剧本。NPC 只读取和自己相关的 brief，然后根据人设、关系、记忆和当前目标调用工具。

这能保留自主性，也能让事件有足够游戏结构。

## 设计边界

### 导演层可以做

- 激活事件 Skill。
- 给 NPC 分发局势 brief。
- 安排阶段目标。
- 提醒系统关注某个关系张力。
- 触发夜间反思。
- 选择是否延后某个事件。

### 导演层不能做

- 直接改世界状态。
- 直接强制 NPC 喜欢或讨厌玩家。
- 直接生成不可校验的结局。
- 绕过玩家选择。
- 调用 NPC 权限外的工具。

### NPC 可以做

- 选择自己的工具行动。
- 生成对话。
- 写入主观记忆。
- 根据关系和记忆调整态度。
- 对导演 brief 做符合人设的解释。

### NPC 不能做

- 修改其他 NPC 的内心状态。
- 读取自己不该知道的全局隐私。
- 越权改事件结算。
- 破坏世界规则。

## 稳定性策略

1. **结构化输出**：导演和 NPC 的关键输出都使用 schema。
2. **纯代码 Validator**：所有模型输出进入世界前先校验。
3. **世界版本控制**：异步 Director Beat 必须带 `worldVersion`。
4. **生效窗口**：过期 beat 自动丢弃。
5. **工具权限**：不同 Agent 只看到自己可调用的工具。
6. **Fallback**：强模型失败时使用规则、缓存 brief 或跳过本轮规划。
7. **Debug 可追踪**：失败、丢弃、fallback 都进入事件流。
8. **低频强规划**：强模型只处理复杂规划和复盘。
9. **高频快响应**：玩家即时交互优先用快模型、规则和已有 brief。

## 与当前实现的对齐

当前仓库已经具备后续演进所需的基础：

- Python Agent Runtime。
- World State。
- Event Store。
- Memory Store。
- RuleBasedProvider 和 CloudApiProvider。
- `GET /api/world/state`。
- `POST /api/player/action`。
- 首版 6 NPC / 3 地点游戏状态裁剪。
- 星灯祭供应短缺事件的查看、选择、关系变化、记忆写入和夜间反思种子。
- Godot 客户端首批背景和 `neutral` 立绘接入。

下一步不需要推倒现有结构。应在现有 Runtime 上增加 Director / Skill / Memory 的新模块：

```text
backend/app/director/
  digest.py
  tension.py
  skill_router.py
  planner.py
  validator.py
  queue.py

backend/app/skills/
  event_skill_schema.py
  starlight_festival_shortage.json

backend/app/memory/
  summaries.py
  retrieval.py
```

## 建议实施路线

### Phase 1：文档与数据契约

- 固化本文为后续 Agent 系统设计依据。
- 定义 `DirectorBeat` schema。
- 定义 `EventSkill` schema。
- 定义 `WorldDigest` schema。

### Phase 2：规则版 Director v0

- 用规则生成 WorldDigest。
- 用规则检测星灯祭供应短缺触发条件。
- 生成一个 `activate_event_skill` Director Beat。
- Beat 进入队列并由 Runtime 消费。

### Phase 3：事件 Skill 数据化

- 将当前硬编码星灯祭事件迁到数据文件。
- Runtime 根据 Skill 定义加载参与者、选择、brief 和结算类型。
- 继续保留规则结算，保证离线可跑。

### Phase 4：LLM Director Planner

- 在低频节点调用强模型。
- 输入为 WorldDigest + 候选 Skill + 少量检索证据。
- 输出 Director Beat。
- 使用 Validator 和 Queue Manager 控制落地。

### Phase 5：长期记忆与 RAG

- 增加每日世界摘要。
- 增加 NPC 关系记忆摘要。
- 增加按实体和标签检索旧事件。
- 再引入向量检索。

### Phase 6：Debug Console 可视化

- 展示 Director Beat 队列。
- 展示 Skill 触发条件。
- 展示模型延迟、成本和 fallback。
- 展示 NPC 接收到的 brief 和实际行动。

## 待讨论的大方向

以下问题会影响后续系统复杂度，建议在最小 Director v0 跑通后继续讨论：

1. **导演自治程度**：导演是否可以创造全新事件 Skill，还是只能激活已有 Skill。
2. **NPC 自主程度**：NPC 是否可以主动提出新目标或新冲突，进入导演候选队列。
3. **玩家状态代理边界**：Player State Agent 只总结玩家风格，是否允许给玩家生成任务建议。
4. **时间粒度**：小镇模拟按地点级、小时级还是更细 tick 推进。
5. **模型预算策略**：强模型每天最多调用几次，现场演示时是否锁定低成本模式。
6. **RAG 持久化路线**：首版用 JSON / SQLite 摘要，后续再接向量库。
7. **事件结算自由度**：事件结局是固定 outcome 类型，还是允许 Director 组合多个 outcome。
