---
description: 为指定 NPC 撰写一份符合 npc_deep_card_spec 的深度卡 JSON
---

# /author-npc-deep-card

为 `Agent Valley` 中某位 NPC 撰写一份符合 [`docs/npc_deep_card_spec.md`](../../docs/npc_deep_card_spec.md) 的深度卡 JSON 文件。本工作流不直接生成剧情，只生成 **压力源 / 口癖 / 秘密 / 反应倾向 / 关系阶段 / 独白种子** 等可被 LLM 在线调用的角色基底。

## 启动条件

- 用户提供 NPC `id`，例如 `mira`、`tomas`、`orren`、`lena`、`bram`、`kai`。
- 该 NPC `id` 已经存在于 `backend/app/world/seed_data.py` 的 `AGENTS` 列表。
- 仓库 `npm.cmd run check` 当前为绿。

## 必读上下文

依次读取并对齐：

1. [`docs/npc_deep_card_spec.md`](../../docs/npc_deep_card_spec.md) — 字段契约。
2. [`backend/app/world/seed_data.py`](../../backend/app/world/seed_data.py) — 取该 NPC 的 seed 字段（personality / longTermGoals / job / age / 关系）。
3. [`docs/game_content_storyline.md`](../../docs/game_content_storyline.md) 与 [`docs/project_vision.md`](../../docs/project_vision.md) — 取该 NPC 的内容定位、关系张力、研究展示价值与少而深边界。
4. [`docs/art_direction.md`](../../docs/art_direction.md) — 取该 NPC 的视觉与人设描述。
5. [`backend/app/content/data/npc/kai.json`](../../backend/app/content/data/npc/kai.json) — 参考样板，把握粒度与语气。
6. [`assets/manifests/asset_manifest.json`](../../assets/manifests/asset_manifest.json) — 找到该 NPC 的 `portrait` 与 `mapSprite` 真实 id（关键字 `npc_<id>_neutral` 与 `npc_<id>_map_idle`）。

## 输出契约

- 单文件路径：`backend/app/content/data/npc/<id>.json`。
- JSON 必须通过 `python scripts/check_npc_codex.py`。
- `id` 与文件名一致；`schemaVersion` 固定为 `1`。
- 不引用 `asset_manifest.json` 中不存在的资产 id；表情差分若未生成则 `expressions: {}`。
- 不引用具体玩家姓名；不预设固定剧情节点。

## 写作硬约束

1. **`personality.speechQuirks`**：≥ 2 条。结合 `seed.personality` 与 `voiceStyle`，不要写常见模板。
2. **`personality.innerContradiction`**：1 句，揭示外在表现与内在恐惧之间的张力。
3. **`secrets`**：≥ 2 条；至少 1 条 `unlockAfter` 为 `stage_3` 或更后阶段；`tags` 体现领域。
4. **`relationshipStages`**：4–6 阶段，按 `affection` 严格升序。
   - `stage_0` 阈值必须为 `affection:0, trust:0`。
   - 若包含 `romance_seed_*` 解锁，所属阶段必须设 `conflictMax`，建议 ≤ 35。
   - `unlocks` 中 `secret_*` 与 `monologue_*` 必须存在于本卡的 `secrets` / `monologueSeeds`。
5. **`monologueSeeds`**：≥ 8 条。`contextTags` 推荐覆盖：
   - 时段：`morning` / `afternoon` / `evening`。
   - 情绪：`high_mood` / `low_mood`。
   - 节点：`pre_event` / `post_event`。
   - 至少 1 条与玩家相关，使用 `social` 标签。
6. **`giftReactions`**：四档 `loved` / `liked` / `neutral` / `disliked` 必须齐全。
   - 每档 `fallbackSpeechPool` ≥ 2 条，符合 `voiceStyle`。
   - `loved` 应包含至少 1 个 `tagAny` 与该 NPC 长期目标 / 职业相关的 tag。
   - `disliked` 至少 1 条标签呼应该 NPC 的 `stressTriggers`。
   - `deltaModifier` 是叠加值，建议范围：loved `affection:+2~+3, trust:+1~+2`；liked `affection:+1`；disliked `affection:-2~-3, conflict:+1~+3`；neutral 通常 `{}`。
7. **`gossipHooks`**：≥ 1 条；至少 1 条引用现有冲突或秘密。
8. **`assetRefs`**：必须使用 `asset_manifest.json` 实际 id；缺失资产留空字符串或空对象，不要伪造。

## 风格指引

- 语言风格统一为 **简体中文 + 二次元轻幻想轻异世界**，与 `art_direction.md` 一致。
- 不使用 emoji；颜文字仅在测试用 fallback 中限量使用。
- 不暴露"研究院 / 实验"叙事。
- 不暴露 `Player` / `LLM` 等元词汇。

## 执行步骤

1. 读取必读上下文（§必读上下文 1–6）。
2. 整理出该 NPC 的：
   - `seed` 字段（id / age / job / personality / longTermGoals）。
   - 内容定位中的核心张力、关系阶段入口和研究展示价值。
   - `asset_manifest` 中真实可用的 portrait / mapSprite id。
3. 按 [`docs/npc_deep_card_spec.md`](../../docs/npc_deep_card_spec.md) §5 字段顺序起草 JSON。
4. 使用 `write_to_file` 写入 `backend/app/content/data/npc/<id>.json`。
// turbo
5. 运行 `python scripts/check_npc_codex.py`，确认输出包含 `[npc-codex-check] ok (N cards)` 且无新 warning。
// turbo
6. 运行 `npm.cmd run check`，确认整条流水线绿。
7. 在 `docs/current_status.md` 末尾增量记录新生成的卡 id 与跑通时间。

## 失败处理

- 若 `check_npc_codex.py` 报错：阅读错误信息中的字段路径，修正 JSON。
- 若资产 warning：核对 `asset_manifest.json` 实际 id；不要绕过校验。
- 若 `npm.cmd run check` 在 smoke 阶段失败：先回看 `_handle_player_gift` / `_handle_player_talk` 与 deep card 字段，确认本卡未引入未知字段或非法值。

## 验收

- `python scripts/check_npc_codex.py` 输出 `[npc-codex-check] ok (N cards)`。
- `npm.cmd run check` 绿。
- 新卡 `id` 与文件名一致。
- 新卡资产引用全部命中 manifest（或显式留空）。
- `relationshipStages` 与 `unlocks` 引用通过交叉校验。

## 后续扩展

- 当 6 个首发 NPC 全部入库后，新增写作 workflow `/author-event-skill` 用同一模式产出 Event Skill JSON。
- 把 `monologueSeeds` 接入 RAG 长期记忆索引，作为夜间反思与寒暄锚。
- 把 `gossipHooks` 接入谣言传播玩法（后续阶段）。
