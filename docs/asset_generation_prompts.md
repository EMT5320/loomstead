---
status: active
owner_lane: asset-pipeline
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: asset prompt pack and manifest registration examples
---

# 首版生图提示词包

> 本文是 `art_direction.md` 的执行补充，提供下一步调用生图能力时可直接复制的提示词。所有提示词都围绕二次元轻幻想轻异世界田园生活模拟方向，生成后按 `art_direction.md` 与 `assets/manifests/asset_manifest.json` 登记资产清单。

## 通用风格锚点

建议每次生成时都追加以下风格锚点：

```text
bright anime farming life sim, light fantasy isekai village, cozy rural town, cel-shaded anime illustration, clean line art, warm sunlight, soft magical starlight, expressive character design, wholesome slice-of-life anime, pastoral fantasy, harvest festival atmosphere, high quality, detailed but readable, no text, no watermark
```

角色立绘追加：

```text
visual novel half-body character portrait, transparent background, consistent character design, clean silhouette, expressive anime eyes, simple readable costume details
```

场景背景追加：

```text
16:9 background, clean composition for visual novel dialogue overlay, no readable text, no logo, clear foreground and midground, warm cozy lighting
```

地图小人追加：

```text
anime chibi low-pixel map sprite, pixel-art inspired, 2.0 to 2.5 heads tall, slight top-down front view, 64x64 sprite target, 48x56 safe character area, crisp 1-2 px dark outline, limited warm palette, readable at 64x64 and 32x32, transparent background, single character only
```

负向提示词：

```text
photorealistic, western storybook watercolor, heavy oil painting, dark grim fantasy, cyberpunk, horror, gritty realism, noisy background, low detail, distorted hands, extra fingers, malformed anatomy, text, watermark, logo, blurry face, inconsistent eyes
```

## 生成批次 0：风格锁定

### `assets/source/style/style_key_art_loomstead.png`

```text
Key art for Loomstead, a bright anime light fantasy isekai farming life sim. A cozy rural homestead valley town called Starlight Valley, small farmhouse with vegetable plots in the foreground, sunny plaza and Moon Cat Tavern in the distance, strings of star lanterns, tiny magical sparkles around crops, warm morning sunlight, soft pastoral fantasy atmosphere, clean cel-shaded anime illustration, wholesome slice-of-life anime mood, 16:9, high quality, no text, no watermark.
```

### `assets/source/style/style_character_lineup_day1.png`

```text
Character lineup sheet for six villagers in a bright anime light fantasy farming town, five women and one man. Include Mia Starwheat the warm grocery shop owner, Toma Elmgarden the quiet male carpenter, Aurea Asterchron the elegant elderly female retired teacher, Lena Birchveil the calm tired young female doctor, Kaya Moonstring the cheerful young female tavern musician, and Branna Wheatrow the strong adult female farm owner. Full body or three-quarter view, consistent anime style, clean line art, cel-shaded colors, each character has clear silhouette and profession props, simple neutral background, no text, no watermark.
```

### `assets/source/ui/anime_dialogue_panel_style.png`

```text
Visual novel UI style sheet for a bright anime farming life sim. Include a semi-transparent dialogue box, character nameplate, choice buttons, small relationship change badge, memory card panel and night diary panel. Light fantasy starlight motif, warm cream and amber palette with soft green accents, clean readable shapes, enough blank space for Chinese text rendered later, no actual text, no logo, no watermark.
```

## 生成批次 1：玩家角色

### `assets/source/characters/player_farmer_neutral.png`

```text
Anime half-body portrait of a young female farmer protagonist who just moved to a light fantasy rural town, age 18 to 22, friendly curious expression, refreshing and determined aura, short practical jacket, simple apron, light boots, crossbody seed pouch, small starlight charm, cream white, leaf green and wheat gold palette, visual novel character portrait, transparent background, clean line art, cel-shaded, no text, no watermark.
```

表情差分追加：

- `happy`：`same character and outfit, warm happy smile, relaxed shoulders`
- `troubled`：`same character and outfit, slightly confused and worried expression`

## 生成批次 2：NPC 半身立绘

### `assets/source/characters/npc_mira_neutral.png`

```text
Anime half-body portrait of Mia Starwheat, a warm grocery shop owner in a light fantasy farming village, 31 years old, chestnut medium-length hair with side braid, amber or olive green eyes, cream blouse, warm orange apron, seed packets, small ledger, star-shaped hairpin, gentle practical big-sister aura, visual novel character portrait, transparent background, clean line art, cel-shaded, no text, no watermark.
```

表情差分追加：

- `happy`：`same character and outfit, relieved warm smile, kind eyes`
- `troubled`：`same character and outfit, worried about supplies and family expenses`

### `assets/source/characters/npc_tomas_neutral.png`

```text
Anime half-body portrait of Toma Elmgarden, a quiet dependable carpenter in a light fantasy farming town, 34 years old, broad shoulders, messy dark brown short hair, gray-blue or dark brown eyes, dark blue work shirt, rolled sleeves, leather tool belt, wooden hammer, measuring ruler, tiny wood shavings on clothes, calm focused expression, visual novel character portrait, transparent background, clean line art, cel-shaded, no text, no watermark.
```

表情差分追加：

- `happy`：`same character and outfit, subtle gentle smile`
- `troubled`：`same character and outfit, awkward caring expression, struggling to speak`

### `assets/source/characters/npc_orren_neutral.png`

```text
Anime half-body portrait of Aurea Asterchron, an elegant elderly female retired teacher and town historian in a light fantasy farming town, 72 years old, silver hair pinned up or neatly cut, pale gray or blue eyes, old green vest or long coat, parchment-colored shirt, long scarf, pocket watch, ancient book with star map, strict but lovable expression, visual novel character portrait, transparent background, clean line art, cel-shaded, no text, no watermark.
```

表情差分追加：

- `happy`：`same character and outfit, proud smile while talking about tradition`
- `troubled`：`same character and outfit, stern worried expression`

### `assets/source/characters/npc_lena_neutral.png`

```text
Anime half-body portrait of Lena Birchveil, a calm young doctor in a light fantasy village clinic, 27 years old, dark teal or blue-black medium-short hair, tired gentle eyes, white short medical coat, mint green accents, herb brooch, medical satchel, simple skirt or trousers, rational and caring expression, visual novel character portrait, transparent background, clean line art, cel-shaded, no text, no watermark.
```

表情差分追加：

- `happy`：`same character and outfit, rare relaxed smile`
- `troubled`：`same character and outfit, exhausted but determined expression`

### `assets/source/characters/npc_kai_neutral.png`

```text
Anime half-body portrait of Kaya Moonstring, a cheerful young female tavern musician in a light fantasy farming town, 22 years old, wavy auburn or reddish purple hair, golden or purple eyes, burgundy short cape, lively performance outfit, belt accessories, star pendant, lute or violin, confident playful smile, visual novel character portrait, transparent background, clean line art, cel-shaded, no text, no watermark.
```

表情差分追加：

- `happy`：`same character and outfit, energetic bright grin, theatrical pose`
- `troubled`：`same character and outfit, anxious smile under festival pressure`

### `assets/source/characters/npc_bram_neutral.png`

```text
Anime half-body portrait of Branna Wheatrow, a strong adult female farm owner in a light fantasy rural town, 36 years old, tanned skin, short dark brown hair or practical high ponytail with sunlit streaks, earthy shirt, suspenders or work overalls, old work gloves, straw hat or towel over shoulder, crop crate, serious direct gaze, wheat yellow, soil brown and olive green palette, visual novel character portrait, transparent background, clean line art, cel-shaded, no text, no watermark.
```

表情差分追加：

- `happy`：`same character and outfit, approving smile toward a hardworking farmer`
- `troubled`：`same character and outfit, angry and stressed about debt and poor harvest`

## 生成批次 3：地图小人与交互标记

地图小人用于 Godot 可移动场景。首版只做静态 `idle_front` 概念图，统一定调为 **二次元 Q 版低像素地图小人**。详细尺寸、头身比例、视角、轮廓线、调色、身份继承和失败判定见 [`map_sprite_style_guide.md`](./map_sprite_style_guide.md)。

统一追加：

```text
anime chibi low-pixel map sprite, pixel-art inspired, light fantasy farming life sim, 2.0 to 2.5 heads tall, slight top-down front view, centered full body, 64x64 sprite target, 48x56 safe character area, crisp 1-2 px dark outline, limited warm palette, readable at 64x64 and 32x32, transparent background, single character only, no text, no watermark
```

完整提示词文件：

- `assets/manifests/prompts/player_farmer_map_idle.txt` -> `assets/source/sprites/player_farmer_map_idle.png`
- `assets/manifests/prompts/npc_mira_map_idle.txt` -> `assets/source/sprites/npc_mira_map_idle.png`
- `assets/manifests/prompts/npc_tomas_map_idle.txt` -> `assets/source/sprites/npc_tomas_map_idle.png`
- `assets/manifests/prompts/npc_orren_map_idle.txt` -> `assets/source/sprites/npc_orren_map_idle.png`
- `assets/manifests/prompts/npc_lena_map_idle.txt` -> `assets/source/sprites/npc_lena_map_idle.png`
- `assets/manifests/prompts/npc_kai_map_idle.txt` -> `assets/source/sprites/npc_kai_map_idle.png`
- `assets/manifests/prompts/npc_bram_map_idle.txt` -> `assets/source/sprites/npc_bram_map_idle.png`

第一批试生成范围：

1. `player_farmer_map_idle`：确认玩家绿色新手农场主小人读感。
2. `npc_mira_map_idle`：确认女性 NPC、橙色围裙和杂货铺身份读感。
3. `npc_tomas_map_idle`：确认男性 NPC、深蓝木匠和工具腰带读感。

这 3 张通过后，再生成 `npc_orren_map_idle`、`npc_lena_map_idle`、`npc_kai_map_idle`、`npc_bram_map_idle`。新生成的小人先保持 `pending_review`，完成 64px / 32px 可读性和身份继承评审后再考虑登记为可用来源。

交互标记统一追加：

```text
small UI interaction marker icon for anime farming life sim, transparent background, readable silhouette, soft starlight glow, no text, no watermark
```

- `interaction_marker_talk.png`：`speech bubble with tiny star`
- `interaction_marker_gift.png`：`small wrapped gift with leaf and star motif`
- `interaction_marker_event.png`：`glowing star lantern exclamation marker`

## 生成批次 4：地点背景

### `assets/source/locations/farm_day_anime.png`

```text
Bright anime light fantasy farm at morning, small cozy farmhouse, vegetable plots with dew, wooden fence, seed bags near the door, tiny starlight charm hanging by the entrance, distant village and hills, soft warm sunlight, peaceful farming life sim background, clean composition for visual novel dialogue overlay, 16:9, no readable text, no watermark.
```

### `assets/source/locations/plaza_day_anime.png`

```text
Anime pastoral fantasy town plaza in bright daytime, stone fountain, bulletin board without readable text, market stalls, strings of star lanterns, flower beds, cozy village square, clean roads and open space, warm community atmosphere, farming life sim background, clean composition for visual novel dialogue overlay, 16:9, no readable text, no watermark.
```

### `assets/source/locations/tavern_evening_anime.png`

```text
Anime light fantasy tavern interior at evening, Moon Cat Tavern motif, wooden bar, small music stage with instruments, warm amber lantern lights, window showing violet dusk, cozy social atmosphere, farming town festival night, clean composition for visual novel dialogue overlay, 16:9, no readable text, no watermark.
```

## 生成批次 5：星灯祭事件 CG

### `assets/source/cg/starlight_festival_shortage_event.png`

```text
Anime event CG for a light fantasy farming town, evening outside Moon Cat Tavern, starlight festival lanterns glowing, cheerful young female musician Kaya Moonstring looks anxious, strong adult female farm owner Branna Wheatrow holds a crate of crops, young female farmer protagonist stands between them with fresh turnips, Mia Starwheat the grocery shop owner, Lena Birchveil the doctor and Aurea Asterchron the elderly female teacher watching in background, warm amber and violet lighting, emotional slice-of-life anime scene, 16:9, no text, no watermark.
```

### `assets/source/cg/starlight_festival_gift_choice.png`

```text
Anime event CG for a cozy farming life sim, close-up scene of a young female farmer protagonist offering fresh turnips and a small farm flower under glowing starlight festival lanterns, Kaya Moonstring smiles with relief, Branna Wheatrow's stern expression softens, warm tavern lights in background, gentle emotional anime scene, light fantasy rural town, 16:9, no text, no watermark.
```

## 生成批次 6：道具图标

图标统一追加：

```text
anime game item icon, light fantasy farming life sim, clean silhouette, transparent background, soft cel-shaded, readable at small size, no text, no watermark
```

逐项提示词：

- `item_fresh_turnip.png`：`fresh white turnip with green leaves, tiny dew drops, soft magical sparkle`
- `item_farm_flower.png`：`small warm-colored farm flower bouquet tied with twine, gentle rural gift`
- `item_starlight_lantern.png`：`small star-shaped festival lantern, warm amber glow, light fantasy craft`
- `item_star_soup_ingredient.png`：`basket of festival soup ingredients, turnip, herbs, tiny star-shaped spice`
- `item_tavern_receipt.png`：`old tavern receipt paper with blank unreadable marks, tied with red string`

## 生成批次 7：UI 组件

UI 统一追加：

```text
visual novel UI asset for anime light fantasy farming life sim, transparent background, warm cream and amber palette, starlight motif, clean readable shapes, no actual text, no watermark
```

逐项提示词：

- `dialogue_box_anime.png`：`wide semi-transparent dialogue box, soft cream panel, amber border, tiny star lantern corner ornaments`
- `nameplate_anime.png`：`small character nameplate, warm amber frame, leaf and star motif`
- `choice_button_anime.png`：`rounded choice button, normal and selected style shown side by side, soft green and amber accents`
- `gift_panel_anime.png`：`compact gift confirmation panel, item slot, soft parchment texture, starlight corner`
- `relationship_delta_badge.png`：`small relationship change badge, heart and trust star motifs, readable icon shape`
- `memory_card_anime.png`：`small memory card panel, diary paper, star dust, blank area for text`
- `night_diary_panel_anime.png`：`night diary panel, dark blue translucent frame, tiny lantern and moon cat motif, blank area for text`

## 生成批次 8：表情差分 + 行动反馈图标 + 生活行动 UI 小组件（backlog）

> 本批次仅写入可校验的 prompt 计划，尚未生成源图。对应 manifest 条目统一使用 `status=prompt_ready`。
> 批次拆分与导出字段：`batch-8a-expression-delta`、`batch-8b-action-feedback-icons`、`batch-8c-life-ui-widgets`。
> 每个 `prompt_ready` 条目都需要补齐 `promptBatchId`、`godotTargetPath`、`godotTargetSlot`。
> 批次分组定义：`docs/asset_batches/prompt_ready_backlog_batches.json`。
> 导出生产清单命令：`python scripts/export_prompt_ready_assets.py`（输出到 `docs/asset_batches/prompt_ready_export.json` 与 `docs/asset_batches/prompt_ready_export.md`）。

### 表情差分（`happy` / `troubled`）
<a id="batch-8-expression-delta"></a>

- `promptBatchId`：`batch-8a-expression-delta`
- `godotTargetPath`：`res://assets/characters/<asset_id>.png`
- `godotTargetSlot`：`asset_registry.portraits.<ownerId>.<expression>`

统一追加：
```text
same character, same outfit, same hairstyle, same accessories, preserve neutral identity, expression-only delta, transparent background
```

- `player_farmer_happy`：主角放松微笑，肩线放松，眼神更温暖。
- `player_farmer_troubled`：主角轻度困惑和担忧，眉心收紧，嘴角收敛。
- `npc_mira_happy`：米娅如释重负的营业微笑，亲和感增强。
- `npc_mira_troubled`：米娅担忧供货和家庭开销，眼神更谨慎。
- `npc_tomas_happy`：托玛克制的淡笑，姿态略微放松。
- `npc_tomas_troubled`：托玛想表达关心却犹豫，眉眼更紧。
- `npc_orren_happy`：奥蕾娅讲述传统时的自豪笑意。
- `npc_orren_troubled`：奥蕾娅对传统断层的严肃担忧。
- `npc_lena_happy`：莉娜罕见放松微笑，疲态下降。
- `npc_lena_troubled`：莉娜疲惫但坚持，眼神更锐利。
- `npc_kai_happy`：凯娅舞台感增强，笑意外放。
- `npc_kai_troubled`：凯娅在节日压力下强撑笑容。
- `npc_bram_happy`：布兰娜认可玩家后出现的干脆笑意。
- `npc_bram_troubled`：布兰娜因欠账与收成压力而明显焦躁。

### 行动反馈图标（action feedback）
<a id="batch-8-action-feedback-icons"></a>

- `promptBatchId`：`batch-8b-action-feedback-icons`
- `godotTargetPath`：`res://assets/icons/<asset_id>.png`
- `godotTargetSlot`：`asset_registry.action_feedback.<usage>`

统一追加：
```text
anime UI feedback icon, transparent background, centered symbol, readable at 32x32 and 64x64, one accent color + one outline color, no text, no watermark
```

- `action_feedback_move`：小靴印 + 轨迹弧线，表示移动已确认。
- `action_feedback_talk`：对话气泡 + 星点，表示对话触发。
- `action_feedback_gift`：礼物盒 + 叶片，表示送礼成功或可送礼。
- `action_feedback_inspect`：放大镜 + 星纹，表示观察/调查反馈。
- `action_feedback_event`：星灯 + 感叹记号，表示事件交互反馈。

### 生活行动 UI 小组件（life action widgets）
<a id="batch-8-life-ui-widgets"></a>

- `promptBatchId`：`batch-8c-life-ui-widgets`
- `godotTargetPath`：`res://assets/ui/<asset_id>.png`
- `godotTargetSlot`：`asset_registry.life_ui.<asset_id>`

统一追加：
```text
anime life-sim UI widget, rounded panel, warm cream + amber + soft green palette, subtle starlight motif, transparent background, blank text-safe area, no watermark
```

- `ui_life_action_button_farm`：生活行动按钮（农务）。
- `ui_life_action_button_chat`：生活行动按钮（社交）。
- `ui_life_action_button_rest`：生活行动按钮（休息）。
- `ui_life_action_schedule_strip`：日程条组件（早/午/晚三个段位容器）。
- `ui_life_action_result_toast`：行动结果浮层组件（图标位 + 简短文本位）。

## 生成后登记模板

每张图筛选通过后，建议按以下结构补入 `assets/manifests/asset_manifest.json`：

```json
{
  "id": "npc_mira_neutral",
  "path": "assets/source/characters/npc_mira_neutral.png",
  "type": "character_portrait",
  "ownerId": "mira",
  "usage": "dialogue_portrait",
  "variantGroup": "npc_mira_portrait",
  "expression": "neutral",
  "style": "anime_light_fantasy_isekai_farming",
  "promptSummary": "Mia Starwheat, warm grocery shop owner, chestnut side braid, orange apron, seed packets, ledger",
  "fullPromptRef": "assets/manifests/prompts/npc_mira_neutral.txt",
  "sourceTool": "codex_image_generation",
  "createdAt": "2026-05-15",
  "sourceSize": "1024x1536",
  "processedPath": null,
  "godotPath": null,
  "licenseNote": "development generated asset",
  "status": "source_selected",
  "reviewNotes": "角色识别清晰，待补 happy/troubled 差分"
}
```
