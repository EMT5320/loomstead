---
status: active
owner_lane: backend-director
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: world entities (FarmPlot, Item, Inventory, Shop, Building, Time, Weather), tool action space, content scale targets
---

# 世界实体模型（Agent 工具空间）

> 制定时间：2026-05-19
> 用途：定义 `Loomstead` 的世界实体 schema，作为 NPC Agent 工具调用的"行动空间"。本文档与 [`agent_loop_architecture.md`](./agent_loop_architecture.md) 配套，前者讲 NPC 怎么决策，本文讲 NPC 决策的对象和效果作用在什么状态上。
> 边界：本文聚焦数据契约和状态规则，不讲 Godot 渲染层细节；不讲具体 NPC 内容（见 `npc_deep_card_spec.md` 和 `game_content_storyline.md`）；不讲资产 manifest（见 `art_direction.md` 和 `assets/manifests/`）。

## 0. 设计原则

### 0.1 工具即内容

每个世界实体 + 状态变化对都对应至少一个 NPC 工具。新增工具 = 新增 NPC 表达自我的方式。世界实体的丰富度直接决定 NPC 行为的丰富度。

### 0.2 内容稀薄但骨架完整

新定位下（"少而深"）内容规模目标：

| 类别 | Phase 2 骨架 | Phase 3 内容期 |
|---|---|---|
| 作物 | schema + 1 种实现 | 5 种实现完整 |
| 物品 | schema + 8-10 种 | 25 种完整 |
| 工具 | 接口 + 8-12 个实现 | 30 个完整 |
| 店铺 | schema + 1 个实现 | 2 个完整 |
| 建筑 | schema + 关键设施 | 完整建筑层 |
| 时间/天气 | 完整时间环境 schema | 雨天等扩展 |

骨架不能稀薄（少了某类工具就少了一种 NPC 表达），内容可以薄（每类只填首版必要数量）。

### 0.3 后端权威

所有世界实体状态由 Python 后端持有，Godot 只读取并提交合法工具调用。本文档定义的所有 schema 是后端权威 schema，对外暴露的 `/api/world/state` 字段是其投影（可能裁剪）。

### 0.4 NPC 与玩家共享接口

任何工具的 `actor_id` 字段既可以是 NPC id，也可以是 `"player"`。世界实体不区分调用者类型，只校验合法性。这是 `agent_loop_architecture.md` "玩家与 NPC 共享接口"原则的物理基础。

## 1. 农田系统

### 1.1 FarmPlot

```python
@dataclass
class FarmPlot:
    plot_id: str
    owner_id: str                # npc_id 或 "player" 或 "public"
    location_id: str             # 所在地点 id
    anchor_id: str               # 在地点内的 anchor
    
    state: Literal["empty", "tilled", "planted", "growing", "harvestable", "withered"]
    crop_id: Optional[str]       # planted 后绑定
    growth_progress: float       # 0-1
    water_level: float           # 0-1, 每日衰减
    quality: Literal["normal", "silver", "gold"]
    
    planted_at: Optional[GameTime]
    last_watered_at: Optional[GameTime]
    
    # 离屏状态推进
    last_ticked_at: GameTime
```

### 1.2 状态机

```text
empty
  ├── till_soil tool      → tilled
  └── (自然状态)

tilled
  ├── plant_seed tool     → planted
  └── (24h 未行动)        → empty (土壤板结回退)

planted
  ├── (生长进度推进)      → growing
  ├── water_level=0       → withered
  └── harvest_crop tool   (planted 阶段不允许)

growing
  ├── (生长进度满)        → harvestable
  ├── water_level=0       → withered
  └── water_crop tool     → growing (water_level 恢复)

harvestable
  ├── harvest_crop tool   → empty (产出作物)
  └── (3 天未收获)        → withered

withered
  ├── till_soil tool      → tilled (清理)
  └── (永久, 需手动清理)
```

### 1.3 生长规则

```python
class GrowthPolicy:
    def tick(self, plot: FarmPlot, delta_minutes: int):
        if plot.state in ("planted", "growing"):
            crop = CropRegistry.get(plot.crop_id)
            
            # 水量影响
            if plot.water_level <= 0:
                plot.state = "withered"
                EventStore.append({"type": "farm.crop_withered", "plot_id": plot.plot_id})
                return
            
            # 生长速率
            growth_rate = crop.growth_per_minute
            if plot.water_level >= 0.5:
                growth_rate *= 1.0
            else:
                growth_rate *= 0.6
            
            plot.growth_progress = min(1.0, plot.growth_progress + growth_rate * delta_minutes)
            
            # 水量衰减
            plot.water_level = max(0, plot.water_level - 0.001 * delta_minutes)
            
            # 状态过渡
            if plot.growth_progress >= 0.3 and plot.state == "planted":
                plot.state = "growing"
            if plot.growth_progress >= 1.0 and plot.state == "growing":
                plot.state = "harvestable"
                EventStore.append({"type": "farm.crop_harvestable", "plot_id": plot.plot_id})
```

天气影响在 §6 描述（雨天 water_level 自动恢复，不需要人工浇水）。

### 1.4 初版规模

| 农场 | 田块数量 | owner |
|---|---|---|
| 玩家农场 | 9 块（3×3） | "player" |
| 布兰娜农场 | 6 块 | "bram" |
| 公共菜园（广场旁） | 4 块 | "public" |

### 1.5 初版作物（5 种）

```python
CROP_REGISTRY = {
    "starwheat": Crop(
        id="starwheat",
        name="星麦",
        category="grain",
        growth_days=3,
        seed_item_id="seed_starwheat",
        produce_item_id="crop_starwheat",
        sell_price_base=12,
        tags=["grain", "festival_offering"],
    ),
    "moonberry": Crop(
        id="moonberry",
        name="月莓",
        category="fruit",
        growth_days=4,
        seed_item_id="seed_moonberry",
        produce_item_id="crop_moonberry",
        sell_price_base=20,
        tags=["fruit", "gift"],
    ),
    "dewgrass": Crop(
        id="dewgrass",
        name="晨露草",
        category="herb",
        growth_days=2,
        seed_item_id="seed_dewgrass",
        produce_item_id="crop_dewgrass",
        sell_price_base=18,
        tags=["herb", "medicine"],
    ),
    "goldbell_potato": Crop(
        id="goldbell_potato",
        name="金铃薯",
        category="vegetable",
        growth_days=3,
        seed_item_id="seed_goldbell_potato",
        produce_item_id="crop_goldbell_potato",
        sell_price_base=15,
        tags=["vegetable", "cooking"],
    ),
    "starlight_lily": Crop(
        id="starlight_lily",
        name="夜光花",
        category="ornamental",
        growth_days=5,
        seed_item_id="seed_starlight_lily",
        produce_item_id="crop_starlight_lily",
        sell_price_base=40,
        tags=["ornamental", "high_value_gift"],
    ),
}
```

Phase 2 只需实现 `starwheat`，其余 schema 占位。Phase 3 全部实现。

### 1.6 关联工具

| 工具 | 输入 | 状态变化 | tier |
|---|---|---|---|
| `farm.till_soil` | plot_id | empty → tilled | vocational |
| `farm.plant_seed` | plot_id, seed_item_id | tilled → planted, 消耗种子 | vocational |
| `farm.water_crop` | plot_id | water_level → 1.0 | vocational |
| `farm.harvest_crop` | plot_id | harvestable → empty, 产出作物 | vocational |
| `farm.clear_withered` | plot_id | withered → tilled | vocational |

## 2. 物品 / 背包系统

### 2.1 Item

```python
@dataclass
class Item:
    item_id: str
    name: str
    category: Literal["seed", "crop", "tool", "food", "gift", "material", "misc"]
    tags: list[str]              # 用于送礼匹配、NPC 偏好、料理配方
    
    stackable: bool
    max_stack: int
    sell_price_base: int         # 基础售价（市场浮动见 §3）
    
    description: str
    asset_icon_ref: Optional[str]
```

### 2.2 Inventory

```python
@dataclass
class Inventory:
    owner_id: str                # npc_id 或 "player"
    slots: list[InventorySlot]
    capacity: int                # 最大槽位数
    gold: int                    # 金币也归属于 inventory

@dataclass
class InventorySlot:
    item_id: str
    quantity: int
    quality: Literal["normal", "silver", "gold"] = "normal"
```

每个 NPC 和玩家都有一份 Inventory。NPC inventory 容量首版统一为 20。

### 2.3 初版物品清单（25 种）

```text
种子 (5):
  seed_starwheat / seed_moonberry / seed_dewgrass / seed_goldbell_potato / seed_starlight_lily

收获作物 (5):
  crop_starwheat / crop_moonberry / crop_dewgrass / crop_goldbell_potato / crop_starlight_lily

工具 (4):
  tool_hoe / tool_watering_can / tool_sickle / tool_axe

料理 (3):
  food_bread / food_jam / food_herbal_salve

礼物 (3):
  gift_flower_bouquet / gift_handcraft / gift_book

材料 (3):
  material_wood / material_stone / material_iron_ore

杂货 (2):
  misc_lantern_oil / misc_rope
```

Phase 2 实现：5 种子 + 5 作物 + 1 工具（hoe 或 watering_can）+ 1 料理 + 1 礼物 = 13 个。其余 schema 占位。Phase 3 全部实现。

### 2.4 Item Tag 体系

Tag 用于：

- 送礼匹配（NPC 深度卡 likes/dislikes 通过 tag 关联）
- 料理配方（配方按 tag 而非具体 item_id 写）
- NPC 偏好（凯娅喜欢 `music_related` tag 的物品）

首版 tag 命名空间：

```text
category.* — grain / fruit / herb / vegetable / ornamental
function.* — gift / cooking / medicine / festival_offering / high_value_gift
emotion.* — sweet / refreshing / calming
material.* — wood / stone / metal
```

### 2.5 关联工具

| 工具 | 输入 | 状态变化 | tier |
|---|---|---|---|
| `inventory.give_item` | target_id, item_id, quantity | 物品转移 | physiological |
| `cook.cook_food` | recipe_id, ingredients | 消耗材料, 产出食物 | vocational |
| `cook.eat_food` | item_id | 消耗食物, 恢复 hunger / energy | physiological |
| `social.give_gift` | target_id, item_id | 物品转移 + 关系变化 + 记忆 | social_strategic |

## 3. 店铺 / 经济系统

### 3.1 Shop

```python
@dataclass
class Shop:
    shop_id: str
    owner_id: str                # NPC id
    location_id: str
    anchor_id: str
    
    inventory: list[ShopSlot]    # 在售商品
    gold: int
    
    open_state: Literal["closed", "open"]
    open_hours: list[tuple[int, int]]  # [(8, 12), (14, 18)] 每天的开放时段
    
    restock_schedule: Literal["daily", "weekly"]
    last_restock_at: GameTime
    
    demand_tags: list[str]       # 当前需求标签，影响收购价

@dataclass
class ShopSlot:
    item_id: str
    quantity: int
    sell_price: int              # 卖给玩家/NPC 的价格
    buy_price: int               # 从玩家/NPC 收购的价格
```

### 3.2 Economy

```python
@dataclass
class Economy:
    market_prices: dict[str, MarketPrice]  # 全镇市场价格

@dataclass
class MarketPrice:
    item_id: str
    base_buy: int                # 商家收购基价
    base_sell: int               # 商家售出基价
    multiplier: float            # 当前供需修正 0.5-1.5
    last_updated_at: GameTime
```

价格 multiplier 由 `EconomyTickPolicy` 每天结算：玩家/NPC 大量出售某物品后 multiplier 下调；店铺需求 tag 命中的物品 multiplier 上调。

### 3.3 初版店铺

```text
mira_general_store:
  owner: mira
  location: plaza
  inventory: 卖种子、基础工具、日用品；收购作物
  open_hours: [(8, 12), (14, 18)]
  restock_schedule: daily
  demand_tags: ["category.grain", "category.vegetable"]

kai_tavern:
  owner: kai
  location: tavern
  inventory: 卖食物饮料；收购食材
  open_hours: [(17, 23)]
  restock_schedule: daily
  demand_tags: ["category.fruit", "function.cooking"]
```

Phase 2 实现 `mira_general_store`。`kai_tavern` schema 占位。Phase 3 全部实现。

### 3.4 关联工具

| 工具 | 输入 | 状态变化 | tier |
|---|---|---|---|
| `shop.open_shop` | shop_id | open_state → open | vocational |
| `shop.close_shop` | shop_id | open_state → closed | vocational |
| `shop.sell_item` | item_id, quantity, buyer_id | 物品转移, 金币变化 | vocational |
| `shop.buy_item` | item_id, quantity, shop_id | 物品转移, 金币变化 | vocational |
| `shop.restock` | shop_id | 补充库存 | vocational（每日自动 + 手动） |

## 4. 建筑 / 设施系统

### 4.1 Building

```python
@dataclass
class Building:
    building_id: str
    type: Literal["house", "shop", "farm", "public", "workshop"]
    owner_id: Optional[str]
    location_id: str
    
    condition: float             # 0-1, 影响功能和外观
    features: list[str]          # ["kitchen", "bed", "storage", "workbench", "stage"]
    upgrade_level: int           # 0-3
    
    # 室内 vs 室外（首版只做室外接近，室内不进入）
    enterable: bool = False
```

### 4.2 Interactable

可交互对象不属于建筑但属于建筑的"功能槽"：

```python
@dataclass
class Interactable:
    interactable_id: str
    type: Literal["crop_plot", "workbench", "bed", "stove", "well", "mailbox", 
                  "notice_board", "market_stall", "supply_crate", "tavern_stage", 
                  "bar_counter", "tavern_table", "festival_table", "fountain"]
    building_id: Optional[str]   # 属于哪座建筑（可空）
    location_id: str
    anchor_id: str
    
    state: dict                  # 类型相关的状态
    usable_by: list[str]         # 谁能用（NPC id 列表 or "all"）
    capacity: int                # 同时能容纳几个 actor
    current_users: list[str]     # 当前正在使用的 actor
```

### 4.3 初版建筑 / 设施

```text
玩家小屋（player_house）:
  features: [bed, storage_box, simple_kitchen]
  interactables: [bed_player, storage_box_player, stove_player]

布兰娜农舍（bram_farmhouse）:
  features: [tool_shed, big_kitchen]
  interactables: [tool_shed_bram, stove_bram]

米娅杂货铺（mira_shop_building）:
  features: [counter, shelves]
  interactables: [counter_mira_shop, shelves_mira_shop]

月猫酒馆（kai_tavern_building）:
  features: [bar, stage, tables]
  interactables: [bar_counter_tavern, tavern_stage, tavern_table_1, tavern_table_2, supply_crate_tavern]

广场公共设施（plaza_public）:
  features: [bulletin_board, well, benches]
  interactables: [notice_board_plaza, well_plaza, fountain_plaza, festival_table_plaza]

托玛工坊（tomas_workshop）:
  features: [workbench, wood_stack]
  interactables: [workbench_tomas, wood_stack_tomas]
```

Phase 2 落地玩家小屋 + 米娅杂货铺 + 月猫酒馆 + 广场公共设施的最少必要 interactables。其余 schema 占位。Phase 3 全部完整。

### 4.4 关联工具

| 工具 | 输入 | 状态变化 | tier |
|---|---|---|---|
| `craft.repair_building` | building_id, materials | condition 提升 | vocational |
| `craft.craft_item` | recipe_id, materials | 消耗材料, 产出成品 | vocational |
| `life.use_workbench` | interactable_id, intent | 设施 state 变化 | vocational |
| `life.sleep` | bed_id | 结束当天 | physiological |
| `life.rest` | location_id 或 interactable_id | 恢复 energy | physiological |
| `social.post_notice` | notice_board_id, content | 公告板更新 | social_strategic |

## 5. 时间 / 环境系统

### 5.1 WorldTime

```python
@dataclass
class WorldTime:
    day: int                     # 第几天，从 1 开始
    hour: int                    # 0-23
    minute: int                  # 0-59
    
    phase: Literal["dawn", "morning", "afternoon", "evening", "night"]
    season: Literal["spring", "summer", "autumn", "winter"]  # 首版只做 spring
    
    paused: bool = False
    speed_multiplier: float = 1.0  # 1x / 2x / 4x / 8x

PHASE_BOUNDARIES = [
    ("dawn", 5, 7),
    ("morning", 7, 12),
    ("afternoon", 12, 17),
    ("evening", 17, 21),
    ("night", 21, 5),  # 跨天
]
```

### 5.2 Weather

```python
@dataclass
class Weather:
    today: WeatherKind           # clear / cloudy / rain
    tomorrow: WeatherKind        # 预报，次日上午公布
    
    # 影响
    rain_water_replenish_per_hour: float = 0.1  # 雨天田块 water_level 自动恢复
    indoor_npc_preference_boost: float = 0.3    # 雨天 NPC 倾向室内
```

首版天气从 `[clear, clear, clear, cloudy, rain]` 随机选择，Phase 2 只实现 clear；Phase 3 加 cloudy/rain。

### 5.3 DayNightCycle

```python
@dataclass
class DayNightCycle:
    light_level: float           # 0-1, 由 phase + weather 计算
    ambient_color_hint: str      # 给 Godot 的 tint hint
    npc_awake_hours: dict[str, tuple[int, int]]  # 每个 NPC 的清醒时段
```

`npc_awake_hours` 不是固定排班——它是 NPC 默认 sleep_pressure 阈值映射的近似值，用于轻量离屏模拟和 Godot 显示。NPC 实际何时睡觉由 `MotivationEngine` 根据 sleep_pressure 决定。

### 5.4 Tick 推进

`POST /api/world/tick` 推进世界时间：

```python
def tick(delta_seconds: float, speed: float = 1.0):
    game_minutes_advance = delta_seconds * speed * GAME_TIME_RATIO
    world.time.advance(game_minutes_advance)
    
    # 顺序执行
    weather_policy.tick(world, game_minutes_advance)
    growth_policy.tick(world, game_minutes_advance)
    economy_policy.tick(world, game_minutes_advance)
    
    # 对每个需要决策的 NPC 跑一次
    for npc in world.npcs:
        if npc.needs_decision_now():
            motivation_engine.evaluate_npc(npc.id, world, game_minutes_advance)
    
    # 推进当前进行中的 Tool actions
    active_action_registry.tick(game_minutes_advance)
    
    return TickResult(events=..., agents_diff=..., clock=...)
```

## 6. 与 Tool / Motivation 的对接

每个工具的 `world_effects` 应用到本文档定义的实体上。Tool ↔ Entity 映射示例：

```python
class TillSoilEffect(WorldEffect):
    def apply(self, tx, decision):
        plot = tx.farm_plots[decision.input["plot_id"]]
        assert plot.state == "empty"
        plot.state = "tilled"

class PlantSeedEffect(WorldEffect):
    def apply(self, tx, decision):
        plot = tx.farm_plots[decision.input["plot_id"]]
        seed = decision.input["seed_item_id"]
        assert plot.state == "tilled"
        plot.state = "planted"
        plot.crop_id = SEED_TO_CROP_MAP[seed]
        plot.growth_progress = 0.0
        plot.water_level = 0.5
        plot.planted_at = tx.world.time.snapshot()
        tx.inventories[decision.actor_id].consume(seed, 1)
```

每个 effect 必须在事务内执行，失败回滚。

## 7. API 暴露

### 7.1 GET /api/world/state（增量字段）

```json
{
  "clock": { "day": 1, "hour": 8, "minute": 25, "phase": "morning", "paused": false, "speed_multiplier": 1.0 },
  "weather": { "today": "clear", "tomorrow": "clear" },
  
  "player": {
    "id": "player",
    "location_id": "farm",
    "anchor_id": "farm_house_door",
    "inventory": { "slots": [...], "gold": 100, "capacity": 30 },
    "needs": { ... },
    "active_action": null
  },
  
  "npcs": [
    {
      "id": "kai",
      "location_id": "tavern",
      "anchor_id": "tavern_stage",
      "inventory_summary": { "gold": 80, "slot_count": 5 },
      "needs_summary": { "top_need": "affiliation", "urgency": 0.6 },
      "active_action": { "tool_id": "craft.play_music", "started_at": ..., "duration": 300 },
      "motivation_visibility": "public"   // 观察者模式可见性
    }
  ],
  
  "farm_plots": [...],
  "shops": [...],
  "buildings": [...],
  "interactables": [...],
  
  "active_events": [...],
  "active_director_beats": [...],
  
  "current_objective": {...},
  "available_interactions": [...]
}
```

字段裁剪策略：

- 玩家正常游玩时只看到自己 inventory 完整数据，NPC 只看 summary
- 观察者模式打开时返回 NPC 的 needs / active_action / motivation_visibility 完整数据
- Web Debug Console 总是返回完整数据（带研究院视角）

### 7.2 POST /api/player/action

玩家行为统一通过这条 API 进入 ToolExecutor：

```json
{
  "type": "farm.till_soil",
  "actor_id": "player",
  "input": { "plot_id": "player_plot_3" }
}
```

返回 ToolResult。

### 7.3 POST /api/world/tick

由 Godot 客户端 WorldClock 服务定时调用，推进游戏时间。响应字段见 §5.4。

## 8. 与 Phase 1 当前实现的迁移

Phase 1 已经有：

- `LifeActionPlan` / `npcSchedules`：保留 API 字段，语义改为"基于动机的下一步候选"
- `playerAnchor` / `actionFeedback`：保留
- `farm_action` 玩家动作：拆解为 `farm.till_soil` / `farm.plant_seed` / `farm.water_crop` / `farm.harvest_crop`
- `scene_action` 玩家动作：拆解为对应 interactable 工具
- `talk` / `give_gift`：升级为 `social.chat_with` / `social.give_gift`
- `inspect` / `attend_event`：保留为独立工具命名空间

Phase 2 启动时的迁移工作：

1. 新建 `backend/app/world/entities/` 目录，放入本文档定义的所有 dataclass
2. 把 `seed_data.py` 中的 NPC inventory / location 数据迁入新 schema
3. 新建 `backend/app/tools/` 目录，按命名空间组织工具实现
4. `LifeActionExecutor` 改名 `MotivationEngine`，移除软日程逻辑（详见 `agent_loop_architecture.md` §13.1）
5. `/api/player/action` 路由按工具命名空间分发到 ToolExecutor
6. `/api/world/state` 字段按 §7.1 扩展

不并行运行旧代码（详见 `agent_loop_architecture.md` §13.2）。

## 9. 与 archive 文档的覆盖关系

本文档取代以下旧设计：

- `archive/architecture_blueprint.md` 中的 World State 字段说明（早期粗略 schema）
- `archive/vertical_slice_spec.md` 中的"Gameplay Systems Layer 农场系统"等章节
- `archive/core_map.md` §2 的"世界实体设计"草稿（已升级为本文形态）
- `gameplay_system_architecture.md` §3.3 的"农场系统 / 背包和物品系统 / 关系系统"等段（待该文档下次治理时改写为指向本文档）

## 10. Phase 2 验收标准

- 所有 §1-5 schema 已实现（dataclass + 序列化 + 反序列化）
- ToolDefinition 注册表中至少 8 个工具有完整 effects 实现
- `/api/world/state` 返回字段对齐 §7.1
- `/api/world/tick` 能推进 24 游戏小时不崩溃
- `eval:rule` L1 scenario suite 通过
- 玩家 + 4 核心 NPC 能跑通完整 Day 1 demo（种麦/送礼/聊天/吃饭/睡觉）

不达标不进入 Phase 3。

## 11. 后续扩展锚点

| 扩展方向 | 锚点字段 | 备注 |
|---|---|---|
| 多日循环 | WorldTime.day | 已在 schema 中 |
| 四季 | WorldTime.season | 已在 schema 中，首版只做 spring |
| 多种作物 | CROP_REGISTRY | 已支持注册表扩展 |
| 室内场景 | Building.enterable | 已留位置 |
| 委托任务 | NoticeBoard | 通过 post_notice 工具铺垫 |
| 节日 | Director Beat 注入 | 不需要独立 schema |
| 长期剧情 | Event Skill 多日生命周期 | 已在 `agentic_game_design.md` 定义 |
