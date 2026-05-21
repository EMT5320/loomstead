---
status: active
owner_lane: asset-pipeline
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: art style, asset generation order, acceptance rules, and visual consistency
---

﻿# 美术风格与资产生成指南：二次元轻幻想轻异世界田园风

> 本文用于指导 `Loomstead` 首版视觉资产生成、筛选、命名、导入和后续扩展。后续调用生图能力前，优先参考本文与 `assets/manifests/asset_manifest.json`。可直接复制的首版提示词见 [`asset_generation_prompts.md`](./asset_generation_prompts.md)；地图小人的细粒度返工规范见 [`map_sprite_style_guide.md`](./map_sprite_style_guide.md)。

## 核心定位

`Loomstead` 首版视觉路线确定为：**二次元轻幻想轻异世界田园生活模拟**。

目标观感：

- 像一部明亮、温柔、带少量魔法感的田园番剧。
- 角色有清晰二次元辨识度，适合半身立绘、表情差分和事件 CG。
- 小镇场景保留生活模拟的可亲近感，同时加入星灯、符文、轻魔法植物等轻异世界元素。
- UI 以 Visual Novel 对话框、角色名牌、选择按钮和记忆卡片为核心，服务聊天、送礼、事件选择和 Debug 讲解。

首版避免方向：

- 写实摄影感。
- 厚重油画感。
- 传统童话绘本水彩感。
- 暗黑废土、强恐怖、强战斗压迫感。
- 高复杂机械、赛博朋克、现代都市主视觉。
- 半身立绘过度 Q 版，导致角色关系张力减弱；地图小人另按 Q 版低像素规范执行。

## 视觉关键词

可复用关键词：

```text
bright anime farming life sim, light fantasy isekai village, cozy rural town, cel-shaded anime illustration, clean line art, warm sunlight, soft magical starlight, visual novel character portrait, expressive character design, wholesome slice-of-life anime, pastoral fantasy, harvest festival atmosphere
```

中文辅助描述：

```text
明亮二次元、轻幻想、轻异世界、田园生活模拟、星灯祭、温柔阳光、干净线稿、赛璐璐上色、角色半身立绘、番剧式群像、可爱但有生活质感
```

地图小人专用关键词：

```text
anime chibi low-pixel map sprite, 2.2-head-tall character, pixel-art inspired, crisp 1-2 px outline, limited warm palette, slight top-down front view, transparent background, readable at 64x64 and 32x32
```

建议负向约束：

```text
photorealistic, western storybook watercolor, heavy oil painting, dark grim fantasy, cyberpunk, horror, gritty realism, noisy background, low detail, distorted hands, extra fingers, text, watermark, logo, blurry face, inconsistent eyes, tall realistic body, cropped portrait, side-scroller sprite, noisy pixel dithering, muddy outline
```

## 世界观视觉基调

### 星灯谷

首版对内可称为“星灯谷”，对外继续使用 `Loomstead`。星灯谷是一座被温和星光祝福的小镇，农作物、节日和居民关系都与“星灯”意象有关。

核心意象：

- 星灯：祭典灯笼、窗边小灯、酒馆吊灯、广场灯绳。
- 晨露：玩家农场、清晨草叶、初始作物、柔和日光。
- 月猫：酒馆招牌、夜间社交、音乐与八卦。
- 轻魔法农作物：作物有轻微发光纹理，首版表现保持克制。
- 关系记忆：可以在 UI 里表现为星尘、便签、日记纸、记忆碎片。

### 魔法浓度

首版魔法浓度确定为 **低魔法生活感**：

- 角色服饰仍接近生活模拟与田园小镇。
- 道具、节日、植物和 UI 中可以出现少量符文、星光、漂浮微粒。
- 作物发光、星灯粒子和符文纹样保持克制，优先服务温柔氛围。
- 主要冲突来自居民关系、供给压力和主观记忆。
- 战斗、魔法职业和大型怪物留到后续扩展。

## 画面语言

### 角色立绘

首版角色以半身立绘为主：

- 干净线稿。
- 明亮赛璐璐上色。
- 眼睛有二次元高光。
- 服饰带职业识别点。
- 每个角色有固定主色和标志性小物。
- 同一角色所有表情差分保持发型、服饰、瞳色和配饰一致。

推荐尺寸：

| 类型 | 原始建议 | Godot 首版建议 | 背景 |
| --- | --- | --- | --- |
| 角色半身立绘 | 1024x1536 或 1536x2048 | 高度 700-900 px | 透明 PNG |
| 角色头像 | 1024x1024 | 256x256 或 512x512 | 透明 PNG |
| 地图小人概念 | 512x512 | 首版同步导入静态小人，后续切 Sprite Sheet | 透明 PNG |
| 表情差分 | 与半身立绘同尺寸 | 与半身立绘同尺寸 | 透明 PNG |

首版表情：

- `neutral`：常态。
- `happy`：好感、欢迎、轻松。
- `troubled`：冲突、疲惫、犹豫。

后续表情：

- `angry`
- `surprised`
- `shy`
- `sad`
- `festival`

### 场景背景

首版场景以 16:9 静态背景为主：

| 类型 | 原始建议 | Godot 首版建议 | 备注 |
| --- | --- | --- | --- |
| 地点背景 | 1920x1080 或 2560x1440 | 1920x1080 | 保留 UI 安全区 |
| 事件 CG | 1920x1080 或 2560x1440 | 1920x1080 | 用于剧情演出 |
| 风格 Key Art | 1920x1080 | 文档和展示用 | 先验证审美 |

场景要求：

- 背景信息清晰，便于后续叠加 NPC 半身立绘和对话框。
- 画面中心避免放过多文字招牌。
- 场景边缘保留 UI 空间。
- 色彩以日光、草地、木质、星灯暖光为主。

### UI

首版 UI 走二次元生活模拟 + Visual Novel 风：

- 半透明对话框。
- 角色名牌。
- 选择按钮。
- 礼物确认面板。
- 关系变化提示。
- 记忆 / 日记卡片。
- 星灯纹样边框。

UI 风格要求：

- 背景能透出一点场景色。
- 字体区域留足中文显示空间。
- 按钮状态至少预留 normal / hover / selected。
- 不在生成图里写死中文文本，文字由 Godot 或 Web Debug 渲染。

### 首版表现层结构

首版同步推进两层表现：

1. **可移动地图层**：Godot 中需要有玩家小人、NPC 小人、3 个地点和基础交互区域，保证游戏可以正常游玩。
2. **Visual Novel 对话层**：玩家靠近或点击 NPC 后，显示半身立绘、表情差分、对话框、选择按钮和关系变化提示。

地图小人首版统一定调为 **二次元 Q 版低像素地图小人**：静态 idle 正面 / 轻俯视正面，后续再扩展行走动画和多方向 Sprite Sheet。地图小人必须从已通过的角色参考图与半身立绘继承发型、主色、职业道具和标志物；生成结果先进入 `pending_review` 评审，确认尺寸、身份与可读性后再登记为可用来源。

## 首版资产包

### A. 风格锁定资产

首批建议先生成 3 张，用于确定整体审美：

```text
assets/source/style/style_key_art_loomstead.png
assets/source/style/style_character_lineup_day1.png
assets/source/ui/anime_dialogue_panel_style.png
```

用途：

- `style_key_art_loomstead.png`：展示星灯谷的整体气质，包含农场、广场、远处小镇和星灯元素。
- `style_character_lineup_day1.png`：6 个 NPC 的同框设计草图，用于统一比例、线稿、饱和度和服饰复杂度。
- `anime_dialogue_panel_style.png`：对话框、名牌、选项按钮和记忆卡片的 UI 风格参考。

### B. 角色资产

玩家角色确定为偏少女的“新搬来的农场主”。首版以可亲近、清爽、略带轻异世界冒险感的少女主角为默认形象。

```text
assets/source/characters/player_farmer_neutral.png
assets/source/characters/player_farmer_happy.png
assets/source/characters/player_farmer_troubled.png
```

6 个首发 NPC：

```text
assets/source/characters/npc_mira_neutral.png
assets/source/characters/npc_mira_happy.png
assets/source/characters/npc_mira_troubled.png
assets/source/characters/npc_tomas_neutral.png
assets/source/characters/npc_tomas_happy.png
assets/source/characters/npc_tomas_troubled.png
assets/source/characters/npc_orren_neutral.png
assets/source/characters/npc_orren_happy.png
assets/source/characters/npc_orren_troubled.png
assets/source/characters/npc_lena_neutral.png
assets/source/characters/npc_lena_happy.png
assets/source/characters/npc_lena_troubled.png
assets/source/characters/npc_kai_neutral.png
assets/source/characters/npc_kai_happy.png
assets/source/characters/npc_kai_troubled.png
assets/source/characters/npc_bram_neutral.png
assets/source/characters/npc_bram_happy.png
assets/source/characters/npc_bram_troubled.png
```

### C. 地图小人与交互资产

首版地图小人与半身立绘同步推进，先生成静态 idle 小人概念图，保证 Godot 可移动场景有可用表现。该批资产的目标风格是 **二次元 Q 版低像素地图小人**，详细规范以 [`map_sprite_style_guide.md`](./map_sprite_style_guide.md) 为准：

- **尺寸**：生图阶段使用方图构图，后处理目标为 `64x64` PNG；角色主体控制在约 `48x56` 安全框内，底部保留 4 px 落脚余量。远期 Sprite Sheet 使用 `64x64` 单元格，首版只做 `idle_front`。
- **头身比例**：约 `2.0-2.5` 头身，头部占全高 44%-50%，手脚简化成清晰块面。
- **视角**：轻俯视正面，镜头高约 20-30 度，脚底可见，适配俯视 / 斜俯视地图行走。
- **轮廓线**：1-2 px 深色外轮廓，内线少量保留；缩到 `64x64` 和 `32x32` 仍能辨认发型、服装和道具。
- **调色**：每个角色保留 3-5 个主色，优先继承半身立绘主色；阴影只做 1-2 级，避免复杂渐变和脏噪点。
- **身份继承**：必须继承 `source_selected` 角色参考图 / neutral 立绘的发型、主色、职业道具与标志物。当前地图小人重做只准备提示词，不把任何既有 `pending_review` 小人提升为 `source_selected`。

```text
assets/source/sprites/player_farmer_map_idle.png
assets/source/sprites/npc_mira_map_idle.png
assets/source/sprites/npc_tomas_map_idle.png
assets/source/sprites/npc_orren_map_idle.png
assets/source/sprites/npc_lena_map_idle.png
assets/source/sprites/npc_kai_map_idle.png
assets/source/sprites/npc_bram_map_idle.png
assets/source/sprites/interaction_marker_talk.png
assets/source/sprites/interaction_marker_gift.png
assets/source/sprites/interaction_marker_event.png
```

对应完整提示词先放在 `assets/manifests/prompts/*_map_idle.txt`。第一批试生成建议只跑 3 张：`player_farmer_map_idle`、`npc_mira_map_idle`、`npc_tomas_map_idle`，用于确认玩家、女性 NPC、男性 NPC 在同一低像素 Q 版体系中的比例与可读性；通过后再扩到 `npc_orren`、`npc_lena`、`npc_kai`、`npc_bram`。

### D. 地点背景

```text
assets/source/locations/farm_day_anime.png
assets/source/locations/plaza_day_anime.png
assets/source/locations/tavern_evening_anime.png
```

### E. 事件 CG

```text
assets/source/cg/starlight_festival_shortage_event.png
assets/source/cg/starlight_festival_gift_choice.png
```

首版最低只需要第一张。第二张作为增强项，用于玩家交出作物或调解时的关键画面。

### F. 道具图标

```text
assets/source/icons/item_fresh_turnip.png
assets/source/icons/item_farm_flower.png
assets/source/icons/item_starlight_lantern.png
assets/source/icons/item_star_soup_ingredient.png
assets/source/icons/item_tavern_receipt.png
```

### G. UI 资产

```text
assets/source/ui/dialogue_box_anime.png
assets/source/ui/nameplate_anime.png
assets/source/ui/choice_button_anime.png
assets/source/ui/gift_panel_anime.png
assets/source/ui/relationship_delta_badge.png
assets/source/ui/memory_card_anime.png
assets/source/ui/night_diary_panel_anime.png
```

### H. 下一批优先 backlog（仅 prompt 计划）

本轮优先补齐以下三类资源，先进入 manifest 的 `prompt_ready`，不提前声明已生成：

1. 玩家 + 6 NPC 的 `happy` / `troubled` 表情差分（共 14 张）。
2. `move`、`talk`、`gift`、`inspect`、`event` 行动反馈图标（共 5 张）。
3. 生活行动 UI 小组件：农务/社交/休息按钮、日程条、行动结果浮层（共 5 张）。

约束：

- 以上条目只登记 backlog，不标记 `source_selected`。
- prompt 引用统一落到 `docs/asset_generation_prompts.md` 的批次 8 锚点段落。
- 等源图真实生成并筛选通过后，再补 `processedPath` / `godotPath`。
- 批次编排、用途和 Godot 接入目标统一维护在 `docs/asset_batches/prompt_ready_backlog_batches.json`。
- 生产导出清单使用 `python scripts/export_prompt_ready_assets.py`，用于按批次发图与人工筛选。

## 角色设定表

### 首发性别比例与多元化原则

首版 6 个 NPC 调整为 **5 女 1 男**，只保留托玛·榆庭作为男性首发 NPC。这个比例优先服务二次元轻幻想风格下的角色生成稳定性、角色辨识度和女性角色人设多样化。

后续扩展 NPC 时默认沿用女性占多数的设计方向，建议保持约 5:1 或相近比例。若后续开发验证男性角色立绘、表情差分和地图小人能稳定保持高质量与一致性，再逐步增加男性角色比重。

角色关系与家庭结构按叙事需要设计。小镇可以自然存在同性配偶、双母家庭、单亲家庭、收养关系、非血缘家庭和其他多元关系结构，这些关系不作为风险或限制项处理。

### 玩家：新搬来的农场主

- 视觉定位：异乡搬来的年轻农场主，干净、亲和、有一点轻异世界冒险感。
- 年龄感：18-22 岁。
- 默认形象：偏少女，短外套、围裙、轻便靴、斜挎小包，气质清爽但有主见。
- 主色：奶油白、嫩叶绿、麦穗金。
- 标志物：小锄头、种子袋、星灯护符。
- 表情：好奇、温和、困惑。
- 恋爱铺垫定位：主角对居民保持真诚亲近感，首版通过对话选择、送礼反应和记忆写入体现好感变化。
- 生图提示摘要：`anime young female farmer protagonist, light fantasy rural outfit, cream and leaf green palette, seed pouch, small starlight charm, friendly curious expression, transparent background`

## 首发 NPC 显示名规则

首版保留 `mira`、`tomas`、`orren`、`lena`、`kai`、`bram` 作为内部 ID，降低代码和数据迁移成本。内部 ID 不再强绑定原始性别或旧显示名，游戏内显示名改为更偏二次元轻幻想的名字。文档中可在过渡期同时写“幻想显示名 / 内部 ID”。

| 内部 ID | 游戏内显示名 | 简称 | 英文别名 |
| --- | --- | --- | --- |
| `mira` | 米娅·星麦 | 米娅 | Mia Starwheat |
| `tomas` | 托玛·榆庭 | 托玛 | Toma Elmgarden |
| `orren` | 奥蕾娅·星历 | 奥蕾娅 | Aurea Asterchron |
| `lena` | 莉娜·白桦 | 莉娜 | Lena Birchveil |
| `kai` | 凯娅·月弦 | 凯娅 | Kaya Moonstring |
| `bram` | 布兰娜·麦垄 | 布兰娜 | Branna Wheatrow |

### 米娅·星麦 Mira

- 职业：杂货铺店主。
- 角色功能：生活物资、经济压力、照顾型关系入口。
- 视觉原型：温柔可靠的年轻店主姐姐。
- 年龄感：31 岁。
- 发型：栗棕色中长发，可有低马尾或侧编发。
- 瞳色：暖琥珀或橄榄绿。
- 服饰：浅色衬衣、暖橙围裙、种子袋、小账本。
- 主色：奶油白、暖橙、叶绿。
- 标志物：账本、种子包、星形发夹。
- 表情差分：
  - `neutral`：温柔营业笑。
  - `happy`：被玩家帮忙后放松微笑。
  - `troubled`：担心供货和家庭开销。
- 说话风格：温和务实，会先照顾对方感受，再谈现实问题。
- 恋爱铺垫：偏温柔照顾线，初期表现为对玩家农场生活的关心和信任累积。
- 生图提示摘要：`anime half-body portrait of Mia Starwheat, warm grocery shop owner, chestnut side braid, amber eyes, cream blouse, warm orange apron, seed packets and small ledger, cozy light fantasy farming village, transparent background`

### 托玛·榆庭 Tomas

- 职业：木匠。
- 角色功能：修缮、家庭线、沉默保护欲。
- 视觉原型：寡言可靠的木匠青年。
- 年龄感：34 岁。
- 发型：深棕短发，略凌乱。
- 瞳色：灰蓝或深棕。
- 服饰：深蓝工作衫、皮质工具带、卷起袖口、木屑痕迹。
- 主色：木褐、深蓝、黄铜。
- 标志物：木工锤、量尺、护腕。
- 表情差分：
  - `neutral`：安静专注。
  - `happy`：很淡的微笑。
  - `troubled`：想表达关心却卡住。
- 说话风格：短句多，行动导向，情绪藏在细节里。
- 恋爱铺垫：偏沉默守护线，初期通过帮玩家修理农场设施和笨拙关心体现。
- 生图提示摘要：`anime half-body portrait of Toma Elmgarden, quiet dependable carpenter, broad shoulders, messy dark brown hair, rolled sleeves, leather tool belt, wooden hammer, rural fantasy village, transparent background`

### 奥蕾娅·星历 Aurea

- 职业：退休教师。
- 角色功能：历史、传统、星灯祭解释者。
- 视觉原型：优雅固执、记忆力惊人的老年女教师。
- 年龄感：72 岁。
- 发型：银白长发盘起，或整齐短发配发簪。
- 瞳色：浅灰或淡蓝。
- 服饰：旧式长外套或马甲、长围巾、怀表、厚书。
- 主色：深绿、羊皮纸米色、古铜。
- 标志物：旧书、星图、怀表。
- 表情差分：
  - `neutral`：严肃审视。
  - `happy`：讲起传统时骄傲。
  - `troubled`：为年轻人不重视传统而生气。
- 说话风格：带历史引用，容易说教，也会突然流露关心。
- 恋爱铺垫：不作为首版恋爱候选，承担亲情、导师和小镇传统线。
- 生图提示摘要：`anime half-body portrait of Aurea Asterchron, elegant elderly female retired teacher, silver hair, old green vest or long coat, long scarf, pocket watch, ancient book with star map, light fantasy farming town, transparent background`

### 莉娜·白桦 Lena

- 职业：医生。
- 角色功能：健康、理性判断、疲惫公共责任。
- 视觉原型：冷静疲惫的年轻医生。
- 年龄感：27 岁。
- 发型：深青或黑蓝色中短发，可低束发。
- 瞳色：青绿或冷灰。
- 服饰：白色短外套、药草胸针、医用小包、简洁长裙或长裤。
- 主色：白、薄荷绿、深青。
- 标志物：药草包、听诊器风格的轻幻想道具、蓝色笔记本。
- 表情差分：
  - `neutral`：冷静观察。
  - `happy`：难得放松。
  - `troubled`：疲惫但强撑。
- 说话风格：理性、直接、会提醒休息和风险。
- 恋爱铺垫：偏理性克制线，初期表现为对玩家身体状况和生活节奏的特别关注。
- 生图提示摘要：`anime half-body portrait of Lena Birchveil, calm young doctor, dark teal hair, tired gentle eyes, white medical coat, mint green accents, herb satchel, light fantasy village clinic, transparent background`

### 凯娅·月弦 Kaya

- 职业：酒馆乐手。
- 角色功能：社交、节日氛围、冲突引爆点。
- 视觉原型：热情张扬、舞台感很强的年轻女性吟游乐手。
- 年龄感：22 岁。
- 发型：红棕或紫棕色微卷发。
- 瞳色：金色或紫色。
- 服饰：短披风、轻便演出服、腰带挂件、星灯吊坠。
- 主色：酒红、金色、夜紫。
- 标志物：鲁特琴或小提琴、乐谱、月猫酒馆徽章。
- 表情差分：
  - `neutral`：自信笑。
  - `happy`：夸张开朗。
  - `troubled`：欠账和活动压力下的慌张。
- 说话风格：情绪饱满，喜欢打比方，会把小事说得像舞台剧。
- 恋爱铺垫：偏热情直球线，初期会用玩笑和音乐邀请玩家参与祭典。
- 生图提示摘要：`anime half-body portrait of Kaya Moonstring, cheerful young female tavern musician, wavy auburn hair, golden eyes, burgundy cape, lute, star pendant, lively light fantasy festival mood, transparent background`

### 布兰娜·麦垄 Branna

- 职业：农场主。
- 角色功能：农场主题、供应线、欠账冲突。
- 视觉原型：强壮爽朗、说话直白的壮年女性农场主。
- 年龄感：36 岁。
- 发型：深棕短发或高马尾，带少量日晒挑染。
- 瞳色：土褐或橄榄绿。
- 服饰：粗布衬衫、背带裤、旧手套、草帽或肩披毛巾，整体更干练利落。
- 主色：麦穗黄、泥土棕、橄榄绿。
- 标志物：木箱、作物篮、旧账单。
- 表情差分：
  - `neutral`：严肃直视。
  - `happy`：认可玩家踏实。
  - `troubled`：被欠账和歉收激怒。
- 说话风格：直白、重劳动价值、讨厌空口承诺。
- 恋爱铺垫：首版先承担农场导师、供应冲突和劳动价值线，后续可扩展为成熟直率的并肩劳动线。
- 生图提示摘要：`anime half-body portrait of Branna Wheatrow, strong adult female farm owner, tanned skin, short dark brown hair or high ponytail, work gloves, straw hat, crop crate, earthy rural fantasy palette, transparent background`

## 地点设定

### 晨露农场

- 用途：玩家出生点、初始作物、送礼来源。
- 画面元素：小木屋、菜畦、晨露草地、旧栅栏、远处小镇、星灯护符挂在门口。
- 色彩：嫩绿、奶油白、浅蓝、麦穗金。
- 生图提示摘要：`bright anime light fantasy farm at morning, small cozy farmhouse, vegetable plots with dew, wooden fence, distant village, tiny starlight charm near the door, farming life sim background, 16:9, no text`

### 中央广场

- 用途：认识居民、公告、公共事件入口。
- 画面元素：喷泉、公告板、星灯灯绳、集市小摊、石板路、花坛。
- 色彩：晴空蓝、暖石色、节日金、草绿。
- 生图提示摘要：`anime pastoral fantasy town plaza, bright daytime, fountain, bulletin board, market stalls, strings of star lanterns, cozy village square, clean background for visual novel dialogue, 16:9, no text`

### 月猫酒馆

- 用途：社交、冲突、星灯祭事件。
- 画面元素：月猫招牌、木质吧台、小舞台、乐器、暖色吊灯、窗外紫色傍晚。
- 色彩：琥珀、酒红、木褐、夜紫。
- 生图提示摘要：`anime light fantasy tavern interior at evening, moon cat sign motif, wooden bar, small music stage, warm lantern lights, cozy social atmosphere, farming town festival night, 16:9, no text`

## 星灯祭供应短缺事件 CG

事件核心：星灯祭前夜，月猫酒馆需要节日食材。凯娅想把活动办起来，布兰娜因为旧欠账拒绝继续供货。玩家可以交出农场作物、调解、支持一方或旁观。

推荐构图：

1. **冲突构图**：酒馆门口，凯娅站在灯光下解释，布兰娜抱着作物箱皱眉，玩家站在两人之间，背景有围观居民。
2. **交付构图**：玩家递出新鲜芜菁或农场小花，凯娅·月弦露出希望，布兰娜·麦垄表情松动，米娅·星麦和莉娜·白桦在旁边观察。
3. **记忆构图**：夜晚星灯亮起，几个 NPC 看向同一盏星灯，画面表达同一事件进入不同人的记忆。

首版推荐先生成第 1 张。

生图提示摘要：

```text
anime event CG, light fantasy farming town, evening outside Moon Cat Tavern, starlight festival lanterns glowing, cheerful young female musician Kaya Moonstring looks anxious, strong adult female farm owner Branna Wheatrow holds a crate of crops, young female farmer protagonist stands between them with fresh turnips, villagers watching in background, warm amber and violet lighting, emotional slice-of-life anime scene, 16:9, no text, no watermark
```

## 资产清单字段

`assets/manifests/asset_manifest.json` 后续建议记录：

```text
id
path
type
ownerId
variantGroup
expression
style
promptSummary
fullPromptRef
promptBatchId
sourceTool
createdAt
sourceSize
processedPath
godotPath
godotTargetPath
godotTargetSlot
licenseNote
status
reviewNotes
```

字段说明：

- `variantGroup`：同一角色或同一 UI 组件的一组变体，例如 `npc_mira_portrait`。
- `expression`：表情或状态，例如 `neutral`、`happy`、`troubled`。
- `fullPromptRef`：完整提示词可单独放在 `assets/manifests/prompts/`，manifest 只保留引用。
- `promptBatchId`：`prompt_ready` 资产所属生产批次，用于导出、排产和验收追踪。
- `godotTargetPath`：`prompt_ready` 目标 Godot 路径，源图通过筛选后用于落库。
- `godotTargetSlot`：`prompt_ready` 对应的 Godot 注册槽位，标记后续接入目标。
- `reviewNotes`：记录筛选意见，方便下一轮重生成。

批次导出约束：

- `prompt_ready` 条目必须包含 `promptBatchId`、`fullPromptRef` 锚点、`usage`、`godotTargetPath`、`godotTargetSlot`。
- 每次更新 backlog 后运行 `python scripts/export_prompt_ready_assets.py`，同步导出：
  - `docs/asset_batches/prompt_ready_export.json`（机器可读）
  - `docs/asset_batches/prompt_ready_export.md`（人工筛选）

## 生图执行顺序

建议按以下顺序推进，避免一次生成太多后风格失控：

1. 生成 `style_key_art_loomstead.png`，确认整体颜色、线稿、魔法浓度。
2. 生成 `style_character_lineup_day1.png`，确认 6 个 NPC 的比例和服饰复杂度。
3. 生成 `anime_dialogue_panel_style.png`，确认 UI 能承载中文文本。
4. 生成偏少女玩家农场主 1 张 `neutral` 表情立绘。
5. 生成 6 个 NPC 的 `neutral` 立绘，并确认幻想显示名与视觉设定匹配。
6. 对通过的角色补 `happy` 和 `troubled` 差分。
7. 按 `map_sprite_style_guide.md` 先试生成 `player_farmer_map_idle`、`npc_mira_map_idle`、`npc_tomas_map_idle` 3 张低像素 Q 版地图小人，并保持 `pending_review`。
8. 试生成通过后再扩展 `npc_orren_map_idle`、`npc_lena_map_idle`、`npc_kai_map_idle`、`npc_bram_map_idle`。
9. 生成 3 张地点背景。
10. 生成星灯祭事件 CG。
11. 生成道具图标和 UI 切图。
12. 处理成 Godot 可导入尺寸并登记 manifest。

## 质量验收标准

一张资产进入首版前至少满足：

- 与二次元轻幻想轻异世界田园方向一致。
- 角色五官、手部、服饰结构无明显错误。
- 同一角色不同表情的发型、服饰、瞳色和配饰一致。
- 场景没有写死不可控文字。
- 背景能承载半身立绘和对话 UI。
- 文件名符合 lowercase snake_case。
- 资产用途、提示词摘要和生成日期可追踪。

地图小人额外验收：

- 明确呈现二次元 Q 版低像素地图小人气质，主体能压进 `64x64` 单元格。
- 头身比约 `2.0-2.5`，轻俯视正面，脚底和身体重心清楚。
- `64x64` 可辨认角色，`32x32` 仍能看出身份主色或职业道具。
- 轮廓线干净，透明背景或单色抠图背景可处理。
- 必须继承已选参考图 / neutral 立绘的发型、主色、标志物和职业身份。
- 失败图保留为 `pending_review` 或直接废弃，禁止因为已有文件存在就提升为 `source_selected`。

地图小人生成失败判定：

- 变成半身头像、写实全身立绘、侧卷轴角色、3D 模型感或高头身角色。
- 比例超过 3 头身，头部不够 Q 版，或道具大到遮挡身体。
- 轮廓糊、背景复杂、透明区域不干净，缩小后无法辨认。
- 玩家和米娅混淆，奥蕾娅被明显年轻化，托玛性别气质漂移，凯娅变现代偶像风，布兰娜失去成熟农场主感。
- 出现文字、水印、logo、额外人物、残肢、错手错脚、严重透视错误。

## 已确认细节

2026-05-15 已确认以下方向：

1. 玩家初版默认形象为偏少女的年轻农场主。
2. 首版同步推进可移动地图层和 Visual Novel 对话层，让 Demo 可以正常游玩和展示角色魅力。
3. NPC 游戏内显示名改为二次元轻幻想风，内部 ID 暂时保留，减少代码迁移成本。
4. 首版 NPC 性别比例调整为 5 女 1 男，只保留托玛·榆庭作为男性首发 NPC；多元家庭和配偶关系作为小镇正常生态处理。
5. 前期保持低魔法生活感，星灯、符文和作物发光只作为氛围点缀。
6. 首版开始恋爱铺垫，通过对话、送礼、记忆和关系变化表现好感倾向；完整恋爱、告白、结婚系统后续扩展。
