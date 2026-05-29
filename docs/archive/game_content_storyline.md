---
status: archive
owner_lane: content-codex
last_verified: 2026-05-21
startup_load: never
source_of_truth: false
scope: 已归档：内容剧本线早期工作台
---

# 游戏内容剧本线工作台（已归档）

> **归档说明**：本文已于 2026-05-28 移入归档层。内容剧本与 NPC 数据已固化到 `backend/app/content/`。仅供历史溯源。

> 更新时间：2026-05-21
> 用途：沉淀主人与 Windsurf 的内容扩充讨论、当前 Codex 收尾结果，以及后续把“游戏内容剧本线”拆成独立开发主线时的入口。

## 1. 主人原始需求

主人希望为 `Loomstead` 搭建一条可复用的内容生产工作流，借助模型写作能力批量生产游戏内容资产。内容范围包括：

- 后续事件扩充。
- 整体叙事节奏与剧本走向。
- 玩法趣味性设计。
- 可长期进入 Runtime、Director、NPC Prompt、记忆系统和表现层的结构化内容。

## 2. 本线核心判断

项目定调来自 `docs/agentic_game_design.md`：`Loomstead` 追求“涌现社会”的可玩观察与互动体验。内容扩充应优先生成可被系统组合、触发和解释的素材层。

当前内容资产的优先类型：

- 舞台：地点、节日窗口、事件场景、资产 hint。
- 土壤：小镇历史、谣言、角色长期目标、职业压力。
- 压力源：资源短缺、关系冲突、季节危机、健康/经济/家庭压力。
- 约束：触发条件、可见性、关系阶段门槛、冲突上限。
- 后果类型：关系变化、记忆写入、玩家画像信号、夜间反思。
- 文本锚点：fallback 台词池、口癖、独白种子、NPC 视角 brief。

这些内容能直接服务 Event Skill、NPC Agent、Director Beat、RAG-lite 记忆和 Godot 表现层。

## 3. Windsurf 讨论中的四层方案

```text
1. Content Codex（数据层）
   npc_codex/        NPC 深度卡
   skill_codex/      事件 Skill 数据
   story_arc_codex/  长期叙事节奏
   lore_codex/       小镇历史、节日、谣言
   item_codex/       物品偏好与典故

2. Authoring Workflows（写作工作流）
   /author-event-skill
   /author-npc-deep-card
   /author-gift-matrix
   /author-story-arc
   /author-gossip-web

3. Schema Validator + Loader
   标准库/dataclass 或后续 pydantic/jsonschema
   校验结构、交叉引用、资产 id、seed membership
   通过 loader 注入 Runtime

4. Runtime + Smoke
   SkillRouter 命中验证
   DirectorBeat 编排验证
   关系阶段、记忆、fallback、Debug 证据验证
```

## 4. 当前已落地范围

### 4.1 NPC 深度卡数据层

已新增：

- `backend/app/content/__init__.py`
- `backend/app/content/codex_schema.py`
- `backend/app/content/codex_loader.py`
- `backend/app/content/data/npc/kai.json`
- `backend/app/content/data/npc/bram.json`
- `backend/app/content/data/npc/mira.json`
- `backend/app/content/data/npc/tomas.json`
- `backend/app/content/data/npc/orren.json`
- `backend/app/content/data/npc/lena.json`

每份 NPC 深度卡包含：

- `identity`：年龄、性别、职业、archetype、voiceStyle、speechRegister。
- `personality`：核心性格、内在矛盾、口癖、压力触发、安抚来源。
- `goals`：长期目标、首日目标、恐惧。
- `secrets`：关系阶段解锁秘密。
- `likes` / `dislikes`：标签化喜好与厌恶。
- `relationshipStages`：5 段左右关系阶段。
- `monologueSeeds`：8 条以上独白种子。
- `giftReactions`：loved / liked / neutral / disliked 四档送礼反应。
- `gossipHooks`：谣言传播钩子。
- `lifeActionSeeds`：Day 1 生活行动素材（时段覆盖 + 关联 NPC）。
- `dailyRumorBeats`：Day 1 谣言节拍素材（hidden/town_known 双可见性）。
- `relationshipBeatSeeds`：Day 1 关系节拍素材（up/steady/down 反馈锚点）。
- `assetRefs`：manifest 中真实存在的 portrait / mapSprite 引用。

新增字段只承载“可触发素材”，不写固定剧情节点，也不直接改世界状态。

### 4.2 写作工作流

已新增：

- `.windsurf/workflows/author-npc-deep-card.md`

该工作流定义了 NPC 深度卡写作流程：读取数据契约、seed、内容定位、视觉设定和资产 manifest，输出 `backend/app/content/data/npc/<id>.json`，并要求通过 `python scripts/check_npc_codex.py`。

### 4.3 校验与运行时集成

已新增：

- `docs/npc_deep_card_spec.md`
- `scripts/check_npc_codex.py`
- `package.json` 脚本：`npm.cmd run content:check`

已接入：

- `scripts/check.py` 会执行 NPC Codex 校验。
- `create_initial_world()` 会把深度卡挂到 `agent.deepCard`。
- `context_builder.py` 会把 `voiceStyle`、`archetype`、`speechQuirks`、`innerContradiction` 放入对话 Prompt。
- 玩家送礼会根据 `giftReactions` 匹配反应档，并叠加关系变化修正。
- 玩家对话和送礼结果会返回 `relationshipStage`，方便 Godot 展示关系阶段变化。

### 4.4 Smoke 覆盖

`scripts/smoke_test.py` 已覆盖：

- Godot 游戏状态包含 `deepCard`。
- Kai 深度卡包含关系阶段和送礼 fallback 台词池。
- 对话 Prompt 包含深度卡语气锚点。
- `talk` 返回 `relationshipStage`。
- `give_gift` 返回 `giftReaction.tier` 与 `relationshipStage.label`。

## 5. 本轮验证证据

2026-05-16 默认本机配置验证：

```powershell
npm.cmd run check
npm.cmd run client:env
npm.cmd run client:run:check
```

结果：

- `npm.cmd run check` 通过。
- `[npc-codex-check] ok (6 cards)`。
- 真实 `llm-smoke` 已调用 `CloudApiProvider`：
  - `dialogue`：`deepseek-v4-flash`，2074 tokens，5311ms，估算成本 0.00023069 USD。
  - `event_reaction`：`deepseek-v4-flash`，6530 tokens，8507ms，估算成本 0.00086177 USD。
  - `night_reflection`：`deepseek-v4-flash`，15242 tokens，12698ms，估算成本 0.00209229 USD。
- `client:env` 通过，Godot 版本为 `4.6.2.stable.official.71f334935`。
- `client:run:check` 通过 dry-run。

说明：

- 真实窗口体验仍需主人手动运行 `npm.cmd run start` + `npm.cmd run client:run` 验收。
- `config/models.json` 是本机忽略配置，测试结果只记录概要，不把密钥写入仓库。

## 6. 后续主线拆分建议

### A. NPC 深度卡二阶段

目标：把已有 6 份深度卡从 Prompt 锚点进一步接入内容玩法。

候选任务：

1. `monologueSeeds -> 夜间反思/RAG`：把独白种子作为夜间反思 fallback 与记忆召回底料。
2. `relationshipStages -> Godot 展示`：在 VN/关系提示中展示阶段名、阶段变化和解锁提示。
3. `gossipHooks -> 谣言传播原型`：玩家行动写入旁观记忆，后续 NPC 对话按钩子扩散。

推荐先做第 1 项，范围最小，收益稳定。

### B. Event Skill 扩充

目标：把星灯祭经验复制为多事件内容生产线。

候选事件：

- 夏日水患。
- 深夜失窃。
- 远客借宿。
- 丰收夜会。
- 月猫走失。

首个目标应先建立 `/author-event-skill` 工作流与数据校验，再生成 3-5 个事件样本。

### C. 礼物与物品宇宙

目标：通过标签避免 NPC × Item 文案爆炸。

候选任务：

- `item_codex`：物品标签、来源、节日/情感/职业语义。
- `gift-matrix`：按标签匹配关系 delta 与 fallback 台词。
- Godot 侧送礼结果展示：反应档、关系变化、记忆证据。

### D. 谣言与秘密网络

目标：让玩家行为通过记忆和关系网络扩散。

候选任务：

- 旁观 NPC 记录玩家行为。
- `gossipHooks` 生成传播候选。
- 不同 NPC 根据关系与性格选择相信、质疑、转述或压下谣言。
- Debug 视图展示传播链。

### E. 30 天节奏与小镇历史

目标：提供长期节奏和世界底料。

候选任务：

- `story_arc_codex`：30 天压力源年历。
- `lore_codex`：奥蕾娅口述史、小镇节日、旧传闻。
- Director 低频读取节奏窗口，选择当日事件候选。

## 7. 当前开放讨论点

进入下一轮上下文治理前，建议主人只需要确认两件事：

1. 游戏内容剧本线的首个二阶段目标是否采用 `monologueSeeds -> 夜间反思/RAG`。
2. 新内容文档后续是否保持单独入口 `docs/game_content_storyline.md`，并在上下文治理时让 `docs/agent_context.md` 只保留摘要链接。

浮浮酱当前建议：先把 `monologueSeeds` 接入夜间反思/RAG，再启动 `/author-event-skill`，这样能同时提升文本质感和后续事件生产效率。
