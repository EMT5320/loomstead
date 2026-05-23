from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.runtime.schema_registry import require_schema_version

EntityKind = Literal["farm_plot", "item", "inventory", "shop", "building", "time", "weather"]
ItemCategory = Literal["seed", "crop", "tool", "food", "gift", "material", "misc"]
InventoryQuality = Literal["normal", "silver", "gold"]
ShopState = Literal["closed", "open"]
BuildingType = Literal["house", "shop", "farm", "public", "workshop", "tavern", "clinic"]
WeatherKind = Literal["clear", "cloudy", "rain"]


@dataclass(frozen=True)
class WorldEntity:
    """Debug / Eval 使用的统一世界实体投影。"""

    entity_id: str
    kind: EntityKind
    label: str
    state: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    location_id: str | None = None
    owner_id: str | None = None
    refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entityId": self.entity_id,
            "kind": self.kind,
            "label": self.label,
            "locationId": self.location_id,
            "ownerId": self.owner_id,
            "state": dict(self.state),
            "tags": list(self.tags),
            "refs": list(self.refs),
        }


@dataclass(frozen=True)
class FarmPlot:
    """农田实体骨架，承接 farm.* 工具和成长策略。"""

    plot_id: str
    location_id: str
    anchor_id: str
    stage: str
    seed_item_id: str | None = None
    crop_id: str | None = None
    output_item_id: str | None = None

    @classmethod
    def from_state(cls, plot_id: str, plot: dict[str, Any]) -> FarmPlot:
        output_item = plot.get("outputItem") if isinstance(plot.get("outputItem"), dict) else {}
        return cls(
            plot_id=plot_id,
            location_id=str(plot.get("locationId") or ""),
            anchor_id=str(plot.get("anchorId") or ""),
            stage=str(plot.get("stage") or "unknown"),
            seed_item_id=str(plot.get("seedItemId") or "") or None,
            crop_id=str(plot.get("cropId") or "") or None,
            output_item_id=str(output_item.get("id") or "") or None,
        )

    def to_entity(self) -> WorldEntity:
        return WorldEntity(
            entity_id=self.plot_id,
            kind="farm_plot",
            label=self.plot_id,
            location_id=self.location_id,
            state={
                "plotId": self.plot_id,
                "stage": self.stage,
                "anchorId": self.anchor_id,
                "seedItemId": self.seed_item_id,
                "cropId": self.crop_id,
                "outputItemId": self.output_item_id,
            },
            tags=("farm", "plot", f"stage.{self.stage}"),
            refs=tuple(ref for ref in (self.seed_item_id, self.output_item_id) if ref),
        )


@dataclass(frozen=True)
class Item:
    """物品实体骨架，统一背包、商店和农作产出引用。"""

    item_id: str
    name: str
    category: ItemCategory
    tags: tuple[str, ...] = ()
    quantity_hint: int | None = None

    @classmethod
    def from_inventory_item(cls, item: dict[str, Any]) -> Item:
        tags = tuple(str(tag) for tag in item.get("tags", []) if str(tag))
        return cls(
            item_id=str(item.get("id") or ""),
            name=str(item.get("name") or item.get("id") or ""),
            category=_item_category(tags),
            tags=tags,
            quantity_hint=_safe_int(item.get("quantity")),
        )

    def to_entity(self) -> WorldEntity:
        return WorldEntity(
            entity_id=f"item.{self.item_id}",
            kind="item",
            label=self.name,
            state={
                "itemId": self.item_id,
                "name": self.name,
                "category": self.category,
                "quantityHint": self.quantity_hint,
            },
            tags=("item", f"category.{self.category}", *self.tags),
        )


@dataclass(frozen=True)
class InventorySlot:
    item_id: str
    quantity: int
    quality: InventoryQuality = "normal"

    def to_dict(self) -> dict[str, Any]:
        return {"itemId": self.item_id, "quantity": self.quantity, "quality": self.quality}


@dataclass(frozen=True)
class Inventory:
    """玩家和 NPC 共用的背包实体骨架。"""

    owner_id: str
    slots: tuple[InventorySlot, ...] = ()
    capacity: int = 20
    gold: int = 0

    @classmethod
    def from_owner(cls, owner_id: str, raw_items: list[dict[str, Any]], *, capacity: int = 20, gold: int = 0) -> Inventory:
        slots = tuple(
            InventorySlot(
                item_id=str(item.get("id") or ""),
                quantity=max(0, _safe_int(item.get("quantity")) or 0),
                quality=str(item.get("quality") or "normal") if str(item.get("quality") or "normal") in {"normal", "silver", "gold"} else "normal",
            )
            for item in raw_items
            if isinstance(item, dict) and str(item.get("id") or "")
        )
        return cls(owner_id=owner_id, slots=slots, capacity=capacity, gold=gold)

    def to_entity(self) -> WorldEntity:
        return WorldEntity(
            entity_id=f"inventory.{self.owner_id}",
            kind="inventory",
            label=f"{self.owner_id} inventory",
            owner_id=self.owner_id,
            state={
                "ownerId": self.owner_id,
                "capacity": self.capacity,
                "gold": self.gold,
                "slotCount": len(self.slots),
                "slots": [slot.to_dict() for slot in self.slots],
            },
            tags=("inventory",),
            refs=tuple(slot.item_id for slot in self.slots),
        )


@dataclass(frozen=True)
class ShopSlot:
    item_id: str
    quantity: int
    sell_price: int
    buy_price: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "itemId": self.item_id,
            "quantity": self.quantity,
            "sellPrice": self.sell_price,
            "buyPrice": self.buy_price,
        }


@dataclass(frozen=True)
class Shop:
    """商店实体骨架；Phase 2 先用杂货铺和临时摊位投影。"""

    shop_id: str
    owner_id: str
    location_id: str
    anchor_id: str
    inventory: tuple[ShopSlot, ...]
    gold: int = 120
    open_state: ShopState = "closed"

    def to_entity(self) -> WorldEntity:
        return WorldEntity(
            entity_id=f"shop.{self.shop_id}",
            kind="shop",
            label=self.shop_id,
            location_id=self.location_id,
            owner_id=self.owner_id,
            state={
                "shopId": self.shop_id,
                "anchorId": self.anchor_id,
                "gold": self.gold,
                "openState": self.open_state,
                "inventory": [slot.to_dict() for slot in self.inventory],
            },
            tags=("shop", "commerce"),
            refs=tuple(slot.item_id for slot in self.inventory),
        )


@dataclass(frozen=True)
class Building:
    """建筑 / 设施实体骨架，保留后续 condition 和 enterable 扩展位。"""

    building_id: str
    building_type: BuildingType
    location_id: str
    owner_id: str | None = None
    anchor_ids: tuple[str, ...] = ()
    condition: float = 1.0
    enterable: bool = True

    def to_entity(self) -> WorldEntity:
        return WorldEntity(
            entity_id=f"building.{self.building_id}",
            kind="building",
            label=self.building_id,
            location_id=self.location_id,
            owner_id=self.owner_id,
            state={
                "buildingId": self.building_id,
                "type": self.building_type,
                "condition": self.condition,
                "enterable": self.enterable,
                "anchorIds": list(self.anchor_ids),
            },
            tags=("building", f"type.{self.building_type}"),
            refs=self.anchor_ids,
        )


@dataclass(frozen=True)
class WorldTime:
    """时间实体骨架，给 Eval / Debug 一个独立时间投影。"""

    day: int
    hour: int
    minute: int
    tick: int
    phase: str
    action_budget: int

    @classmethod
    def from_clock(cls, clock: dict[str, Any]) -> WorldTime:
        return cls(
            day=_safe_int(clock.get("day")) or 1,
            hour=_safe_int(clock.get("hour")) or 8,
            minute=_safe_int(clock.get("minute")) or 0,
            tick=_safe_int(clock.get("tick")) or 0,
            phase=str(clock.get("phase") or "morning"),
            action_budget=_safe_int(clock.get("actionBudget")) or 0,
        )

    def to_entity(self) -> WorldEntity:
        return WorldEntity(
            entity_id="world.clock",
            kind="time",
            label="World Clock",
            state={
                "day": self.day,
                "hour": self.hour,
                "minute": self.minute,
                "tick": self.tick,
                "phase": self.phase,
                "actionBudget": self.action_budget,
            },
            tags=("time", f"phase.{self.phase}"),
        )


@dataclass(frozen=True)
class Weather:
    """天气实体骨架；当前只作为规则和美术提示的稳定占位。"""

    today: WeatherKind = "clear"
    tomorrow: WeatherKind = "clear"
    rain_water_replenish_per_hour: float = 0.0
    ambient_color_hint: str = "warm_clear"

    @classmethod
    def from_world(cls, world: dict[str, Any]) -> Weather:
        raw = world.get("weather") if isinstance(world.get("weather"), dict) else {}
        today = _weather_kind(raw.get("today") or raw.get("condition") or "clear")
        tomorrow = _weather_kind(raw.get("tomorrow") or "clear")
        return cls(
            today=today,
            tomorrow=tomorrow,
            rain_water_replenish_per_hour=float(raw.get("rainWaterReplenishPerHour") or 0.0),
            ambient_color_hint=str(raw.get("ambientColorHint") or ("rain_soft" if today == "rain" else "warm_clear")),
        )

    def to_entity(self) -> WorldEntity:
        return WorldEntity(
            entity_id="world.weather",
            kind="weather",
            label="Weather",
            state={
                "today": self.today,
                "tomorrow": self.tomorrow,
                "rainWaterReplenishPerHour": self.rain_water_replenish_per_hour,
                "ambientColorHint": self.ambient_color_hint,
            },
            tags=("weather", f"weather.{self.today}"),
        )


def world_entities_from_state(world: dict[str, Any]) -> list[WorldEntity]:
    entities: list[WorldEntity] = []
    entities.extend(_farm_plot_entities(world))
    entities.extend(_inventory_entities(world))
    entities.extend(_item_entities(world))
    entities.extend(_shop_entities(world))
    entities.extend(_building_entities(world))
    clock = world.get("clock", {}) if isinstance(world.get("clock"), dict) else {}
    entities.append(WorldTime.from_clock(clock).to_entity())
    entities.append(Weather.from_world(world).to_entity())
    return entities


def world_entity_snapshot(world: dict[str, Any], limit: int = 80) -> dict[str, Any]:
    """输出 Phase 2 WorldEntities 调试快照，保留 typed schema 骨架证据。"""
    entities = world_entities_from_state(world)
    by_kind: dict[str, int] = {}
    for entity in entities:
        by_kind[entity.kind] = by_kind.get(entity.kind, 0) + 1
    return {
        "version": require_schema_version("world_entities"),
        "count": len(entities),
        "byKind": by_kind,
        "items": [entity.to_dict() for entity in entities[:limit]],
    }


def _farm_plot_entities(world: dict[str, Any]) -> list[WorldEntity]:
    entities: list[WorldEntity] = []
    for plot_id, plot in world.get("farmPlots", {}).items():
        if isinstance(plot, dict):
            entities.append(FarmPlot.from_state(str(plot_id), plot).to_entity())
    return entities


def _inventory_entities(world: dict[str, Any]) -> list[WorldEntity]:
    entities: list[WorldEntity] = []
    player = world.get("player") if isinstance(world.get("player"), dict) else {}
    player_inventory = player.get("inventory", []) if isinstance(player.get("inventory"), list) else []
    entities.append(Inventory.from_owner("player", player_inventory, capacity=30, gold=_safe_int(player.get("gold")) or 100).to_entity())
    for agent_id, agent in world.get("agents", {}).items():
        if isinstance(agent, dict) and isinstance(agent.get("inventory"), list):
            entities.append(Inventory.from_owner(str(agent_id), agent["inventory"], capacity=20, gold=_safe_int(agent.get("gold")) or 0).to_entity())
    return entities


def _item_entities(world: dict[str, Any]) -> list[WorldEntity]:
    by_item_id: dict[str, Item] = {}
    player = world.get("player") if isinstance(world.get("player"), dict) else {}
    for item in player.get("inventory", []) if isinstance(player.get("inventory"), list) else []:
        if isinstance(item, dict) and str(item.get("id") or ""):
            by_item_id[str(item.get("id"))] = Item.from_inventory_item(item)
    for plot in world.get("farmPlots", {}).values():
        if not isinstance(plot, dict):
            continue
        seed_item_id = str(plot.get("seedItemId") or "")
        if seed_item_id and seed_item_id not in by_item_id:
            by_item_id[seed_item_id] = Item(item_id=seed_item_id, name=seed_item_id, category="seed", tags=("seed", "farm"))
        output_item = plot.get("outputItem") if isinstance(plot.get("outputItem"), dict) else {}
        output_item_id = str(output_item.get("id") or "")
        if output_item_id and output_item_id not in by_item_id:
            by_item_id[output_item_id] = Item(
                item_id=output_item_id,
                name=str(output_item.get("name") or output_item_id),
                category=_item_category(tuple(str(tag) for tag in output_item.get("tags", []) if str(tag))),
                tags=tuple(str(tag) for tag in output_item.get("tags", []) if str(tag)),
            )
    for slot in _default_shop_slots():
        if slot.item_id not in by_item_id:
            by_item_id[slot.item_id] = Item(item_id=slot.item_id, name=slot.item_id, category="misc", tags=("shop",))
    return [item.to_entity() for item in sorted(by_item_id.values(), key=lambda item: item.item_id)]


def _shop_entities(world: dict[str, Any]) -> list[WorldEntity]:
    phase = str(world.get("clock", {}).get("phase") or "morning") if isinstance(world.get("clock"), dict) else "morning"
    open_state: ShopState = "open" if phase in {"morning", "afternoon"} else "closed"
    return [
        Shop(
            shop_id="mira_general_store",
            owner_id="mira",
            location_id="shop",
            anchor_id="shop_counter",
            inventory=tuple(_default_shop_slots()),
            open_state=open_state,
        ).to_entity(),
        Shop(
            shop_id="plaza_market_stall",
            owner_id="mira",
            location_id="plaza",
            anchor_id="market_stall",
            inventory=tuple(_default_shop_slots()[:2]),
            gold=80,
            open_state=open_state,
        ).to_entity(),
    ]


def _building_entities(world: dict[str, Any]) -> list[WorldEntity]:
    entities: list[WorldEntity] = []
    for location_id, location in world.get("locations", {}).items():
        if not isinstance(location, dict):
            continue
        anchors = tuple(
            str(anchor.get("id"))
            for anchor in world.get("anchors", {}).values()
            if isinstance(anchor, dict) and anchor.get("locationId") == location_id and str(anchor.get("id") or "")
        )
        entities.append(
            Building(
                building_id=str(location_id),
                building_type=_building_type(location),
                location_id=str(location_id),
                owner_id=_building_owner(str(location_id)),
                anchor_ids=anchors,
                enterable=bool(anchors),
            ).to_entity()
        )
    return entities


def _default_shop_slots() -> list[ShopSlot]:
    return [
        ShopSlot(item_id="starlight_turnip_seed", quantity=8, sell_price=5, buy_price=2),
        ShopSlot(item_id="fresh_turnip", quantity=4, sell_price=12, buy_price=6),
        ShopSlot(item_id="farm_flower", quantity=3, sell_price=8, buy_price=3),
    ]


def _item_category(tags: tuple[str, ...]) -> ItemCategory:
    tag_set = set(tags)
    if "seed" in tag_set:
        return "seed"
    if "crop" in tag_set:
        return "crop"
    if "food" in tag_set:
        return "food"
    if "gift" in tag_set or "flower" in tag_set:
        return "gift"
    if "material" in tag_set:
        return "material"
    if "tool" in tag_set:
        return "tool"
    return "misc"


def _building_type(location: dict[str, Any]) -> BuildingType:
    location_id = str(location.get("id") or "")
    location_type = str(location.get("type") or "")
    if location_id == "farm":
        return "farm"
    if location_id == "shop":
        return "shop"
    if location_id == "tavern":
        return "tavern"
    if location_id == "clinic":
        return "clinic"
    if location_type == "residential":
        return "house"
    return "public"


def _building_owner(location_id: str) -> str | None:
    return {
        "farm": "player",
        "shop": "mira",
        "tavern": "kai",
        "clinic": "lena",
    }.get(location_id)


def _weather_kind(value: Any) -> WeatherKind:
    text = str(value or "clear")
    return text if text in {"clear", "cloudy", "rain"} else "clear"


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
