---
status: active
owner_lane: content-codex
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: NPC deep-card schema, writing rules, and validation contract
---

# NPC 深度卡数据契约

> 起草时间：2026-05-16
> 用途：定义 `Loomstead` 第二轮内容扩充的 NPC 深度卡（`npc_codex`）数据契约，作为后续批量内容写作工作流的统一蓝本。
> 设计依据：[`project_vision.md`](./project_vision.md)、[`agentic_game_design.md`](./agentic_game_design.md)、[`agent_loop_architecture.md`](./agent_loop_architecture.md)、[`current_status.md`](./current_status.md)。

## 1. 设计目标

- **保留 agentic 涌现**：深度卡只提供"压力源、口癖、秘密、反应倾向、阶段门槛"，不写死台词或剧情走向。
- **覆盖现有薄弱点**：补齐 `seed_data.AGENTS` 缺失的 likes/dislikes、口癖、秘密、独白库、关系阶段、礼物分级反应。
- **零外部依赖**：数据用 JSON，校验用标准库 + dataclass，对齐 `event_skill_schema.py` 风格。
- **批量可生成**：字段结构稳定到可由写作 workflow 一次性产出 6 份卡，校验通过后入库。
- **运行时小步集成**：不破坏现有 `seed_data.py` 字段访问，只在 `create_agent` 后做合并增强。

## 2. 非目标

- 不替代角色 seed 数据，深度卡只做扩展层。
- 不写死任何"NPC 在第 N 天必须说的话"。
- 不直接控制 Director / Skill 节奏，只为它们提供更丰富的角色证据。
- 首版不引入 PyYAML / Pydantic，保持仓库零外部依赖约束。

## 3. 文件布局

```text
backend/app/content/
├── __init__.py
├── codex_schema.py            # dataclass 定义 + 校验函数
├── codex_loader.py            # 读取 data/npc/*.json，合并到 runtime agent
└── data/
    └── npc/
        ├── kai.json
        ├── bram.json
        ├── mira.json
        ├── tomas.json
        ├── orren.json
        └── lena.json
```

文件名必须等于 NPC `id`，确保 loader 能反向定位写入目标。

## 4. 顶层结构

```jsonc
{
  "schemaVersion": 1,
  "id": "kai",
  "displayName": "凯娅·月弦",
  "shortName": "凯娅",
  "identity": { ... },
  "personality": { ... },
  "goals": { ... },
  "motivationProfile": { ... },
  "capabilityPreferences": { ... },
  "heuristicSeeds": [ ... ],
  "secrets": [ ... ],
  "likes": [ ... ],
  "dislikes": [ ... ],
  "relationshipStages": [ ... ],
  "monologueSeeds": [ ... ],
  "giftReactions": { ... },
  "gossipHooks": [ ... ],
  "lifeActionSeeds": [ ... ],
  "dailyRumorBeats": [ ... ],
  "relationshipBeatSeeds": [ ... ],
  "assetRefs": { ... }
}
```

`id` 必须存在于 `seed_data.AGENTS` 列表，否则 loader 报错。`schemaVersion` 当前固定为 `1`，后续不兼容字段升级时递增。

## 5. 字段说明

### 5.1 `identity`

```jsonc
{
  "age": 22,
  "gender": "female",
  "job": "酒馆乐手",
  "archetype": "热情直球乐手",
  "voiceStyle": "直率，爱用感叹号，偶尔用音乐和星灯比喻",
  "speechRegister": "casual"
}
```

- `archetype` 用于 prompt 顶层身份锚点。
- `voiceStyle` 是模型在线生成对话时的语气提示，必须 1-2 句中文，不带具体情节。
- `speechRegister` 取值：`casual / formal / poetic / clinical / blunt`。

### 5.2 `personality`

```jsonc
{
  "coreTraits": ["外向", "冲动", "浪漫"],
  "innerContradiction": "表面热闹但害怕被欠账冲突连累酒馆驻场资格",
  "speechQuirks": [
    "兴奋时哼一段调子",
    "紧张时反复擦指尖琴弦"
  ],
  "stressTriggers": ["节日冷场", "被指责不专业"],
  "comforts": ["有人愿意听她写的新曲", "看到星灯亮起"]
}
```

- `coreTraits` 应与 seed 中 `personality` 至少有一项重合，保持人设一致。
- `innerContradiction` 必须 1 句，描述内在张力，便于 LLM 生成有层次的反应。
- `speechQuirks` 至少 2 条，用于 prompt 行为锚定。

### 5.3 `goals`

```jsonc
{
  "longTerm": ["写出小镇之歌", "让月猫酒馆成为节日核心"],
  "today": ["撑过星灯祭前夜的演出"],
  "fears": ["节日冷场", "失去酒馆驻场资格"]
}
```

- `longTerm` 应与 seed 中 `longTermGoals` 一致或更具体。
- `today` 在首版只写第一天目标，后续支持按日期重写。

### 5.3.1 `motivationProfile` / `capabilityPreferences` / `heuristicSeeds`

Phase 2 启动时新增三项字段。当前 6 张卡已保留 `motivationProfile` / `capabilityPreferences` 占位，并填入首批 `heuristicSeeds` 作为 designer seed；Runtime 会在启动时把这些 seed 注入 `HeuristicLibrary`，经验提取出的启发式仍可在后续 tick 中覆盖或竞争。

```jsonc
"motivationProfile": {
  "needs": {},
  "personalityModifiers": {}
},
"capabilityPreferences": {},
"heuristicSeeds": [
  {
    "heuristic_id": "designer_prefer_social_chat_affiliation",
    "trigger_pattern": {"needId": "affiliation", "toolId": "social.chat_with"},
    "adjustment": {"toolId": "social.chat_with", "weightDelta": 0.07},
    "confidence": 0.56,
    "narrative": "节日前压力升高时，凯娅会先用聊天稳住现场气氛。"
  }
]
```

完整形态见 `agent_loop_architecture.md` §11：

- `motivationProfile.needs`：需求权重、衰减速率和阈值。
- `motivationProfile.personalityModifiers`：外向性、风险偏好、尽责性等人格修正。
- `capabilityPreferences`：按 tool id 记录 NPC 对工具的偏好加权。
- `heuristicSeeds`：设计师注入的可被经验覆盖的启发式种子；`adjustment` 必须包含 `toolId` 或 `needId`，且 `weightDelta` 保持在 `-0.2..0.2`。

Phase 2 继续允许 `motivationProfile` / `capabilityPreferences` 为空；`heuristicSeeds` 建议每位核心 NPC 至少 1 条，便于 Debug 和 Eval 观察 designer prior 与经验启发式的差异。

### 5.4 `secrets`

```jsonc
[
  {
    "id": "secret_kai_debt",
    "visibility": "hidden",
    "summary": "酒馆欠账其实有一部分是她私下赊账买乐谱",
    "unlockAfter": "stage_3",
    "tags": ["debt", "regret"]
  }
]
```

- `visibility` 取值：`hidden / town_known / npc_known(<id>)`。
- `unlockAfter` 引用 `relationshipStages[].stage`，玩家与该 NPC 关系达到该阶段才可被 LLM 自然提及。
- 每位 NPC 至少 2 条 secret，至少 1 条 `stage_3` 及以后解锁。

### 5.5 `likes` / `dislikes`

```jsonc
"likes": [
  { "tag": "festival", "weight": 3, "items": ["starlight_lantern"] },
  { "tag": "music", "weight": 2, "items": [] },
  { "tag": "flower", "weight": 1, "items": ["farm_flower"] }
],
"dislikes": [
  { "tag": "silence_punishment", "weight": 2, "items": [] }
]
```

- `tag` 是物品或行为的语义标签；运行时把礼物 / 行为标签求和后映射 `giftReactions.tier`。
- `weight` 1-3，越大表示越偏好或越反感。
- `items` 是可选的具体物品 id，命中时强制升一档反应。

### 5.6 `relationshipStages`

```jsonc
[
  { "stage": "stage_0", "label": "陌生", "threshold": { "affection": 0 }, "unlocks": [] },
  { "stage": "stage_1", "label": "镇上熟人", "threshold": { "affection": 25 }, "unlocks": ["topic_kai_music"] },
  { "stage": "stage_2", "label": "朋友", "threshold": { "affection": 50, "trust": 35 }, "unlocks": ["topic_kai_dream"] },
  { "stage": "stage_3", "label": "知音", "threshold": { "affection": 70, "trust": 55 }, "unlocks": ["secret_kai_debt", "monologue_kai_late_night"] },
  { "stage": "stage_4", "label": "心动", "threshold": { "affection": 85, "trust": 70, "conflictMax": 30 }, "unlocks": ["romance_seed_kai"] }
]
```

- 必须按阶段递增排列，`stage_0` 阈值必须为 0。
- 至少 4 个阶段，至多 6 个。
- `threshold` 字段：
  - `affection` / `trust`：要求关系数值 ≥ 该值。
  - `conflictMax`：要求关系冲突 ≤ 该值（可选）。
- `unlocks` 元素必须是合法 id（`topic_*` / `secret_*` / `monologue_*` / `romance_seed_*`），loader 会做交叉引用校验。
- 阶段计算函数 `compute_stage(relation)` 返回当前阶段 id；玩家动作返回新增 `relationshipStage` 字段。

### 5.7 `monologueSeeds`

```jsonc
[
  {
    "id": "kai_morning_warmup",
    "contextTags": ["morning", "tavern", "low_energy"],
    "text": "弦不在状态，今天的节日演出能撑住吗？"
  }
]
```

- 至少 8 条。
- `contextTags` 推荐覆盖 `morning / afternoon / evening`、`high_mood / low_mood`、`pre_event / post_event`、特定地点。
- `text` 第一人称中文，1-2 句，不引用具体玩家姓名。
- 用途：夜间反思 fallback、Prompt 锚点、Debug 展示。

### 5.8 `giftReactions`

```jsonc
{
  "loved": {
    "tagAny": ["festival", "music"],
    "itemAny": ["starlight_lantern"],
    "deltaModifier": { "affection": 3, "trust": 2 },
    "fallbackSpeechPool": [
      "哇——这个我超喜欢！要不要我用它写一段曲子？",
      "你也太懂我了，今晚的曲子要献给你！"
    ]
  },
  "liked": { "tagAny": ["flower", "sweet"], "deltaModifier": { "affection": 1 }, "fallbackSpeechPool": [...] },
  "neutral": { "fallbackSpeechPool": [...] },
  "disliked": { "tagAny": ["silence_punishment"], "deltaModifier": { "affection": -3, "trust": -1, "conflict": 2 }, "fallbackSpeechPool": [...] }
}
```

- 四档必须全部提供，`neutral` 用作兜底。
- `deltaModifier` 是在基础 `affection+4 / trust+2 / conflict-1` 之上的**叠加**修正（不是覆盖），保持现有送礼基础值不变。
- `fallbackSpeechPool` 至少 2 条，每条 1-2 句，仅在规则 fallback 时使用；LLM 在线时由模型生成，但 prompt 会带上当前命中的 tier 名称作为锚定。

### 5.9 `gossipHooks`

```jsonc
[
  {
    "id": "gossip_kai_bram_debt",
    "summary": "凯娅与布兰娜的欠账风波",
    "visibility": "town_known",
    "spreadAffinity": ["mira", "orren"]
  }
]
```

- `gossipHooks` 用于后续谣言传播玩法奠基，首版只入库不消费。
- `spreadAffinity` 标识对该话题最敏感的 NPC，便于后续 SkillRouter 优先路由。

### 5.10 `assetRefs`

```jsonc
{
  "portrait": "char_kai_neutral",
  "expressions": { "happy": "char_kai_happy", "troubled": "char_kai_troubled" },
  "mapSprite": "npc_kai_map_idle"
}
```

- 所有 id 必须存在于 `assets/manifests/asset_manifest.json`，loader 会做交叉校验。
- 缺失资产可用空字符串占位，但校验脚本会给出 warning。

### 5.11 `lifeActionSeeds`

```jsonc
[
  {
    "id": "life_kai_morning_routine",
    "timeWindow": "morning",
    "summary": "凯娅在开工前确认酒馆乐手相关准备，并观察镇上早晨氛围。",
    "intentTags": ["routine", "day1", "observation"],
    "locationHints": ["home", "work_spot"],
    "relatedNpcIds": ["bram"]
  }
]
```

- `lifeActionSeeds` 用于 Day 1 日常行动素材预留，给后续低层玩法做可消费输入。
- `timeWindow` 取值：`morning / afternoon / evening / night`。
- 每位 NPC 至少 3 条，并覆盖 `morning / afternoon / evening`。
- `locationHints` 可填写抽象标签（如 `home`、`work_spot`、`town_center`、`tavern`），也可填写具体 anchor id（如 `market_stall`、`plaza_gate`）；阶段 1 客户端优先使用具体 anchor id，避免多个 NPC 因泛化标签同时涌向同一点。
- 仅描述“行为倾向与动机”，不写固定剧情节点，不直接改世界状态。

### 5.12 `dailyRumorBeats`

```jsonc
[
  {
    "id": "rumor_kai_public_tension",
    "visibility": "town_known",
    "cue": "凯娅在公开场合与熟人围绕日常分工出现小摩擦，旁人容易接话扩散。",
    "spreadTargets": ["mira", "orren"],
    "tags": ["day1", "public", "tension"]
  }
]
```

- `dailyRumorBeats` 是 Day 1 谣言节拍素材，后续可直接喂给传播玩法。
- 每位 NPC 至少 2 条，并覆盖 `hidden` 与 `town_known` 两种可见性。
- `spreadTargets` 引用 `seed_data.AGENTS` 中存在的其他 NPC，数量建议 1-3。

### 5.13 `relationshipBeatSeeds`

```jsonc
[
  {
    "id": "relation_kai_assist_small_help",
    "stageHint": "stage_1",
    "trigger": "玩家在日常互动中主动帮忙并尊重对方节奏。",
    "direction": "up",
    "summary": "凯娅愿意给出更明确的偏好与轻量协作线索。",
    "tags": ["day1", "trust_building"]
  }
]
```

- `relationshipBeatSeeds` 用于关系反馈措辞与素材锚点，避免把关系变化写死成剧情节点。
- `direction` 取值：`up / steady / down`。
- 每位 NPC 至少覆盖 1 条 `up` 与 1 条 `steady/down`。
- `stageHint` 必须命中该 NPC 自己的 `relationshipStages[].stage`。

## 6. 运行时集成点

| 位置 | 改动 | 风险 |
| --- | --- | --- |
| `backend/app/world/world_state.py:create_agent` | 末尾合并 codex 字段到 agent dict（新增 `deepCard` 子对象，不污染顶层） | 低 |
| `backend/app/providers/context_builder.py:_agent_brief` | 增加 `voiceStyle / speechQuirks / unlockedMonologueIds` | 低 |
| `backend/app/providers/context_builder.py:build_player_dialogue_context` | 玩家对话 context 中增加 `relationshipStage` 与 `currentStageUnlocks` | 低 |
| `backend/app/runtime/agent_runtime.py:_handle_player_gift` | 在已有 `affection+4 / trust+2 / conflict-1` 之后叠加 `giftReactions[tier].deltaModifier`；fallback 文案从 `fallbackSpeechPool` 抽取 | 中 |
| `backend/app/runtime/agent_runtime.py:_relationship_evidence_payload` | 关系快照增加 `stage` / `stageLabel` 字段 | 低 |
| 玩家动作响应根节点 | 新增 `relationshipStage` 字段，结构 `{"targetId": "kai", "stage": "stage_2", "label": "朋友", "transition": "up"\|"same"\|"down"}` | 低 |

## 7. 校验规则（`scripts/check_npc_codex.py`）

- 文件名 `<id>.json` 与 `id` 一致。
- `id` 必须在 `seed_data.AGENTS` 内。
- `schemaVersion == 1`。
- 各字段满足类型与最小条数（详见 §5）。
- `relationshipStages` 升序、`stage_0` 阈值为 0、阈值递增。
- `secrets[].unlockAfter` 必须是当前 NPC 的合法 stage id。
- `giftReactions` 四档齐全。
- `assetRefs` 所有 id 命中 `asset_manifest.json`（缺失给 warning，不阻塞）。
- `monologueSeeds` 至少 8 条。
- `motivationProfile` / `capabilityPreferences` / `heuristicSeeds` 必须存在；`heuristicSeeds.adjustment.weightDelta` 必须保持在 `-0.2..0.2`。
- `lifeActionSeeds` 至少 3 条并覆盖 morning/afternoon/evening，`relatedNpcIds` 仅引用其他合法 NPC。
- `dailyRumorBeats` 至少 2 条且覆盖 hidden/town_known，`spreadTargets` 仅引用其他合法 NPC。
- `relationshipBeatSeeds` 至少 2 条且覆盖 up 与 steady/down，`stageHint` 命中本卡关系阶段。
- 校验通过后打印 `[npc-codex-check] ok`，挂入 `npm.cmd run content:check` 与 `scripts/check.py` 流水线。

## 8. 写作 Workflow（`.windsurf/workflows/author-npc-deep-card.md`）

输入契约：

- NPC `id`
- 现有 `seed_data` 字段
- `art_direction.md` 中该 NPC 的视觉与人设描述
- 该 NPC 在 `agent_loop_architecture.md` motivationProfile 矩阵中的差异化定位

输出契约：

- 单个 JSON 文件，路径 `backend/app/content/data/npc/<id>.json`
- 满足 §5 所有字段约束
- 与 seed 的 `personality / longTermGoals / job / age` 不冲突
- 不引用未入 manifest 的资产 id
- 不写死具体剧情节点或玩家姓名

写作约束硬性条目（写入 workflow 文档）：

1. 不写死结局与剧情，只写"压力源 / 秘密 / 口癖 / 反应倾向"。
2. `relationshipStages` 至少 4 阶段，最高阶段如包含 romance 必须有 `conflictMax` 限制。
3. `secrets` 至少 2 条，至少 1 条 `stage_3+` 解锁。
4. `monologueSeeds` 至少 8 条，覆盖三时段 + 高低情绪。
5. `giftReactions` 四档齐全，每档 fallback 至少 2 条，符合 `voiceStyle`。
6. `gossipHooks` 至少 1 条，引用现有冲突或秘密。
7. `lifeActionSeeds / dailyRumorBeats / relationshipBeatSeeds` 满足 Day 1 素材最小条数与引用合法性。
8. JSON 必须能通过 `python scripts/check_npc_codex.py`。

## 9. 验收

- `python scripts/check_npc_codex.py` 或 `npm.cmd run content:check` 通过。
- `npm.cmd run check` 通过（`scripts/check.py` 中追加 codex 校验）。
- `npm.cmd run smoke` 通过，包含至少一个验证礼物分级反应的用例。
- `docs/current_status.md` 更新本轮状态；涉及新对话入口或协作边界时同步 `docs/agent_context.md`。

## 10. 后续扩展

- Phase 2：把 `NPC Codex` 的 `secrets / monologueSeeds / gossipHooks` 接入 RAG 检索，作为长期记忆基底。
- Phase 3：复用本契约的写作 workflow 模式扩到 `EventSkill` / `ItemCodex` / `StoryArcCodex` / `LoreCodex`。
- Phase 4：Director Planner 输入加入"当前玩家与每位 NPC 的 stage"摘要，驱动事件 Skill 路由。
