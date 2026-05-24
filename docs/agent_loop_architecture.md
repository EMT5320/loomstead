---
status: active
owner_lane: backend-director
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: NPC agent loop, motivation engine, capability registry, subjective memory, heuristic learning, arbitration, evaluation framework
---

# NPC Agent Loop 架构（核心圣经）

> 制定时间：2026-05-19
> 触发原因：项目从"二次元田园 RPG"重定位为"可解释的多 Agent 叙事运行时"。本文档与 [`agentic_game_design.md`](./agentic_game_design.md) 平级，专门定义 NPC Agent Loop 的内部机制、决策链路、记忆架构、启发式学习与 Eval Framework，作为 Phase 2 及之后所有 NPC 行为系统开发的事实源。
> 边界：本文不重复讲多层 Agent 系统的整体结构（见 `agentic_game_design.md`），也不讲世界实体 schema（见 `world_entity_model.md`）。本文聚焦"NPC 作为一个 agent，在每个决策周期里做了什么、依赖什么、如何被解释和评估"。

## 0. 项目重定位（前言）

`Loomstead` 不再以"涌现式田园生活模拟 RPG"作为项目核心叙事。新定位：

> **一个可解释的多 Agent 叙事运行时：通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，让少量深度 NPC 在可玩的 Godot 生活模拟切片中产生可追踪成长。**

差异化主轴是"少而深 + 可解释 + 可评估"，与 Smallville（中等规模 baseline）、AI Town（玩家弱涟漪）、AIvilization（10 万 agent 浅层）等"广而浅"路线区分。Godot 田园切片只是 demo scenario，不是项目主体。

本项目的五条核心能力（按重要性）：

1. **三层工具分层 + 动机系统**：替换软日程，让 NPC 行为来自内部需求而非时间表。
2. **双轨主观记忆**：客观事件流 + 每个 NPC 的主观视图，同事件不同记忆是可演示资产（Rashomon 玩法）。
3. **失败驱动的启发式学习**：NPC 从痛苦经验自动提取避坑规则，可观测、可量化的成长。
4. **竞争上下文仲裁**：NPC 同时面对动机/Director/Skill/记忆/启发式多源输入，结构化裁决，全过程可追溯。
5. **Eval Framework**：scripts/run_agent_eval.py 跑分层 scenario suite，量化指标证明上述能力比 baseline 强。

## 1. 整体决策环（一图概览）

```text
                      每 15-30 游戏分钟一次决策周期
                                 │
                                 ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  1. NeedAccumulator: 衰减/累积所有需求值（hunger/energy/...）  │
   ├──────────────────────────────────────────────────────────────┤
   │  2. PerceptionGather: 收集本周期内进入主观视图的事件          │
   ├──────────────────────────────────────────────────────────────┤
   │  3. CompetingContextBuilder: 合并以下输入并打分                │
   │       - 当前需求 (motivation)                                  │
   │       - Director Beat 临时偏置                                 │
   │       - Event Skill 局部约束                                   │
   │       - 启发式经验 (heuristic)                                 │
   │       - 长期目标 (goals)                                       │
   │       - 信念模型 (belief_about, 可选)                          │
   ├──────────────────────────────────────────────────────────────┤
   │  4. CapabilityRegistry: 动态生成可用工具集                    │
   │       (NPC × 当前位置 × 当前持有物 × 当前需求类别)             │
   ├──────────────────────────────────────────────────────────────┤
   │  5. ArbitrationLayer: 选定最迫切的需求 + 候选工具集           │
   ├──────────────────────────────────────────────────────────────┤
   │  6. ToolPicker: 三层路由                                      │
   │       - Physiological → 规则                                   │
   │       - Vocational → 规则 + 局部 LLM                            │
   │       - Social/Strategic → LLM (受预算约束)                    │
   ├──────────────────────────────────────────────────────────────┤
   │  7. ToolExecutor: 执行工具，写入 EventStore                   │
   ├──────────────────────────────────────────────────────────────┤
   │  8. ResultObserver: 把执行结果分发为在场观察者的主观记忆     │
   └──────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    继续推进到下一个决策周期
                    (执行中的工具受 Interrupt 机制管理)
```

每个组件都是可独立测试的纯函数或纯类，全过程产出 EventStore 条目，Debug Trace 可逆向追溯任意决策。

## 2. 三层工具分层（Tool Tier）

### 2.1 分层定义

| 层 | 决策来源 | 频率 | 例子 |
|---|---|---|---|
| **Physiological（生理）** | 规则 | 高频（每周期可触发） | move_to / rest / sleep / eat / drink |
| **Vocational（职业）** | 规则 + 局部 LLM | 中频（按软触发条件） | till_soil / plant_seed / water_crop / open_shop / cook_food / craft_item |
| **Social/Strategic（社交/谋略）** | LLM（受预算约束） | 低频 | chat_with / give_gift / spread_rumor / refuse_request / borrow_gold / confess |

NPC 默认在 Physiological + Vocational 层用规则跑，**只在以下分支点进入 Social 层调 LLM**：

- 关系阈值跨越（friend → close friend）
- 玩家在场或玩家行为目击
- Event Skill 激活
- Director Beat 注入临时目标
- 启发式经验首次触发

每条规则路径必须有 LLM 升级选项（"我可以决定，但当下情境值得一次精修对话"），但默认不走。

### 2.2 工具元数据 schema

每个工具实现必须声明：

```python
@dataclass
class ToolDefinition:
    tool_id: str                      # 唯一 id，例如 "till_soil"
    tier: Literal["physiological", "vocational", "social_strategic"]
    
    # 输入与前置条件
    input_schema: dict                # JSON Schema
    preconditions: list[Precondition] # 必须全部满足才能执行
    
    # 中断与持续
    duration_seconds: float           # 游戏时间持续
    interruptible: bool               # 是否可被打断
    interrupt_priority_threshold: float  # 高于此优先级的需求才能打断
    
    # 效果
    world_effects: list[WorldEffect]  # 状态变更
    event_emissions: list[str]        # 产出的事件类型
    observer_visibility: Literal["all_in_location", "participants_only", "private"]
    
    # 失败模式
    failure_modes: list[FailureMode]  # 可能的失败原因，每条带 emotional_charge
    
    # LLM 决策支持
    llm_eligible: bool                # 是否允许在 Social 层被 LLM 选择
    fallback_rule: Optional[Callable] # LLM 失败/超预算时的规则降级
```

`world_effects` 由 ToolExecutor 在事务中应用，失败时回滚。

### 2.3 工具命名空间约束

工具按命名空间组织，避免 LLM 上下文被全量工具淹没：

- `farm.*`：till_soil / plant_seed / water_crop / harvest_crop
- `shop.*`：open_shop / sell_item / buy_item / restock
- `cook.*`：cook_food / eat_food
- `social.*`：chat_with / give_gift / refuse_request / ask_for_help
- `strategic.*`：borrow_gold / spread_rumor / hide_secret / confess
- `life.*`：move_to / rest / sleep / inspect_object / carry_item
- `craft.*`：repair_building / craft_item / play_music / read_book

CapabilityRegistry 每次决策只把当前 NPC 在当前情境下**真正可用的子集**喂给 LLM，详见第 4 节。

## 3. 动机系统（Motivation Engine，替换软日程）

### 3.1 设计原则

软日程系统（lifeActionSeeds）整体退役。NPC 行为不再来自时间表，而是来自：

```text
内部需求（自动累积/衰减）
  +
长期目标（NPC 深度卡定义）
  +
导演层临时偏置（Director Beat）
  +
启发式经验（Heuristic Library）
  +
当下情境约束（地点、持有物、关系）
  ↓
最迫切需求 → 候选工具 → 决策
```

`lifeActionPlan` / `npcSchedules` API 字段保留，但语义从"今天的计划"改为"基于当前需求的下一步候选"，给 Godot 客户端做日程可视化用。

### 3.2 需求层（Need Layer）

每个 NPC 有 4 类需求，每类带 personality 权重：

```python
@dataclass
class NeedProfile:
    # 生理（自动累积，到阈值触发）
    hunger: NeedTrack          # 累积速度受 metabolism_rate 影响
    energy: NeedTrack          # 体力，工作消耗、休息恢复
    sleep_pressure: NeedTrack  # 一天结束累积，sleep 工具清零
    
    # 经济
    money_anxiety: NeedTrack   # 低于 money_floor 时累积
    
    # 社交
    affiliation: NeedTrack     # 缓慢累积，需要 chat/give_gift 满足
    recognition: NeedTrack     # 与 longTermGoal 关联，特定行为满足
    
    # 目标
    goal_progress: dict[str, float]  # 每个长期目标的进度

@dataclass
class NeedTrack:
    current: float             # 当前值 0-1
    decay_rate: float          # 每游戏小时累积/衰减速率
    weight: float              # NPC personality 权重
    threshold_trigger: float   # 自动触发对应工具的阈值
    threshold_critical: float  # 极端阈值，可打断其他工具
```

需求权重写在 NPC 深度卡 `motivationProfile` 字段（详见第 11 节）。

### 3.3 决策每周期流程

每 15-30 游戏分钟一次（具体粒度由 `MotivationEngine.decision_interval` 配置，首版 20 分钟）：

```python
def evaluate_npc(npc_id, world, delta_minutes):
    needs = NeedAccumulator.tick(npc_id, delta_minutes)  # 衰减/累积
    
    # 1. 找到最迫切需求
    director_bias = DirectorBeatRegistry.get_bias_for(npc_id)
    heuristic_modifiers = HeuristicLibrary.get_active_for(npc_id, world.context)
    
    candidate_needs = sorted(
        needs.items(),
        key=lambda n: (n.current * n.weight) 
                      + director_bias.get(n.id, 0)
                      + heuristic_modifiers.get(n.id, 0),
        reverse=True
    )
    
    # 2. 取 top-1 需求 + 必要时第二需求
    primary_need = candidate_needs[0]
    
    # 3. 通过 capability registry 取候选工具
    capability_subset = CapabilityRegistry.resolve(
        npc_id, primary_need.id, 
        world.location_of(npc_id),
        world.inventory_of(npc_id),
        world.relationships_of(npc_id)
    )
    
    if not capability_subset:
        return NoOpDecision(reason="no_capability_available")
    
    # 4. 三层路由
    tool_pick = ToolPicker.route(
        npc_id, primary_need, capability_subset,
        tier_policy=ToolDefinition.tier
    )
    
    # 5. 执行
    return ToolExecutor.execute(tool_pick)
```

`director_bias` 是 Director Beat 注入的临时需求权重偏置（"今晚 social 重要性 +30%"），过期自动消失。

### 3.4 长期目标（Goals）

每个 NPC 有 1-3 个长期目标，进入决策时作为软偏置：

```json
{
  "goalId": "kai_perform_at_starlight_festival",
  "title": "在星灯祭演出新曲",
  "progress": 0.3,
  "deadline": {"day": 5, "phase": "evening"},
  "unblocking_actions": ["practice_song", "borrow_instrument", "invite_audience"],
  "priority_boost_when_idle": 0.2,
  "priority_boost_when_blocked": 0.5
}
```

`unblocking_actions` 是该目标关联的工具 id 集合，候选工具集中包含这些工具时优先级增加 `priority_boost_when_idle`。

### 3.5 观察者模式与玩家干预

玩家观察者模式可以注入"临时动机调整"作为 directorBeat 的一种特殊形式（`beatType: "player_intervention"`），效果与 Director Beat 一致但 Debug Trace 标记 source。

## 4. Capability Registry（动态工具集）

### 4.1 为什么动态生成

如果每次 LLM 决策都把 30 个工具的完整 schema 塞进 prompt，token 浪费且决策质量下降。CapabilityRegistry 在每个决策周期动态生成"当前 NPC 在当前情境下真正可用的工具子集"，通常 3-8 个。

### 4.2 解析公式

```python
def resolve(npc_id, primary_need, location, inventory, relationships):
    candidates = []
    for tool in TOOL_REGISTRY.all():
        # Layer 1: 需求相关性
        if primary_need.id not in tool.served_needs:
            continue
        
        # Layer 2: 前置条件
        if not all(p.check(npc_id, location, inventory, relationships) 
                   for p in tool.preconditions):
            continue
        
        # Layer 3: 角色 capability profile（NPC 深度卡）
        npc_profile = NPCProfile.get(npc_id)
        if tool.tool_id in npc_profile.capability_blacklist:
            continue
        if tool.requires_skill and tool.required_skill not in npc_profile.skills:
            continue
        
        # Layer 4: 当前情境黑名单（事件 Skill 内）
        active_skill = EventSkillRegistry.active_for(npc_id)
        if active_skill and tool.tool_id in active_skill.disallowed_tools:
            continue
        
        candidates.append(tool)
    
    return candidates[:8]  # 上限保护
```

### 4.3 工具的 served_needs 标注

每个工具声明它能"满足"哪些需求：

```python
till_soil = ToolDefinition(
    tool_id="farm.till_soil",
    served_needs=["money_anxiety", "goal_progress.farming"],
    ...
)

chat_with = ToolDefinition(
    tool_id="social.chat_with",
    served_needs=["affiliation", "recognition", "goal_progress.relationship_building"],
    ...
)
```

NPC 深度卡的 `capabilityPreferences` 字段可以加权：凯娅的 `social.chat_with` 在 affiliation 需求下权重 +0.3，托玛的 `craft.craft_item` 在 recognition 需求下权重 +0.4。

### 4.4 玩家与 NPC 共享接口

玩家通过 UI 操作触发的工具与 NPC 通过 LLM 选择的工具走**同一套 ToolDefinition 注册表**。差别只在：

- 玩家由 UI 触发，跳过 CapabilityRegistry 路由（玩家看 UI 自行筛选）
- 玩家的 Tool 调用打 `actor_type=player` 标记
- 在场观察者把玩家行为写入主观记忆时，会有差异化的 prompt 反应

这点是亮点 4（因果链）的基础：玩家行为和 NPC 行为在 EventStore 中走完全相同的路径。

## 5. 决策循环：周期、预算、Fallback

### 5.1 决策周期

```python
DECISION_INTERVAL_GAME_MINUTES = 20  # 默认 20 游戏分钟

# 加速规则
- 关键事件触发时立即评估（不等周期）
- 当前工具完成时立即评估（不等周期）
- 玩家在场时缩短为 10 游戏分钟
- 离屏 NPC 拉长为 60 游戏分钟（轻量模拟）
```

### 5.2 LLM 调用预算

```python
@dataclass
class DecisionBudget:
    npc_id: str
    per_game_day: dict[str, int] = field(default_factory=lambda: {
        "social_strategic_layer": 8,    # NPC 自主社交决策
        "vocational_local_llm": 6,      # 职业层次的局部 LLM 增强
        "dialogue_with_player": 999,    # 玩家对话不计预算（玩家驱动）
        "reflection": 1,                # 夜间反思 1 次
        "heuristic_extraction": 2,      # 启发式提取 2 次
    })
    consumed: dict[str, int] = field(default_factory=dict)
    fallback_to_rule_when_exhausted: bool = True
```

预算耗尽时，默认 fallback 到该工具的 `fallback_rule`（在 ToolDefinition 里声明）。**预算事件本身写入 EventStore**，可在 Debug Trace 中看到"NPC X 今天 social_strategic 预算已用完，从 16:00 起降级为规则模式"。

### 5.3 Fallback 链

按优先级降级：

1. LLM 调用 → 如果失败/超时/输出非法
2. → 当前工具的 `fallback_rule`（规则函数）
3. → 默认 NoOp（NPC 原地等待下一周期）

每一级降级都产生 `decision.fallback_triggered` 事件，记录原因和降级路径。这是 Eval Framework 的 `fallback_rate` 指标基础。

### 5.4 离屏模拟（Off-screen Simulation）

玩家不在场的 NPC 可以走轻量模拟：

- 决策周期拉长为 60 游戏分钟
- Social 层强制 fallback 到规则
- 工具执行不产出动画事件，只产出状态变更事件

玩家进入对应场景时，"离屏期间发生的痕迹"已经存在于世界状态（公告变化、物资箱状态、NPC 情绪、对话引用）。这点是 `gameplay_system_architecture.md` "离屏痕迹"原则的物理实现。

## 6. Tool Executor 与中断机制

### 6.1 Tool 执行事务

```python
class ToolExecutor:
    def execute(self, decision: ToolDecision) -> ToolResult:
        tool = TOOL_REGISTRY.get(decision.tool_id)
        
        # 1. 启动事件
        EventStore.append({
            "type": f"npc.action_started",
            "npc_id": decision.actor_id,
            "tool_id": tool.tool_id,
            "duration": tool.duration_seconds,
            "context": decision.context_summary,
        })
        
        # 2. 注册到 ActiveActionRegistry，由 Tick 推进
        ActiveActionRegistry.register(decision)
        
        # 3. 返回 placeholder result，真正完成由 tick 触发
        return ToolResult(status="started", action_id=decision.action_id)
    
    def on_action_complete(self, action_id):
        decision = ActiveActionRegistry.pop(action_id)
        
        # 4. 应用 world effects（事务）
        with WorldStateTransaction() as tx:
            for effect in decision.tool.world_effects:
                effect.apply(tx, decision)
        
        # 5. 完成事件
        EventStore.append({
            "type": "npc.action_completed",
            "npc_id": decision.actor_id,
            "tool_id": decision.tool.tool_id,
            "outcome": decision.outcome,
        })
        
        # 6. 分发观察记忆
        ResultObserver.distribute(decision)
    
    def on_action_failure(self, action_id, failure_mode):
        decision = ActiveActionRegistry.pop(action_id)
        
        EventStore.append({
            "type": "npc.action_failed",
            "npc_id": decision.actor_id,
            "tool_id": decision.tool.tool_id,
            "failure_mode": failure_mode.code,
            "emotional_charge": failure_mode.emotional_charge,
            "reason_summary": failure_mode.summary,
        })
        
        # 失败也分发观察记忆（社会信号）
        ResultObserver.distribute(decision, status="failed")
```

### 6.2 中断机制

每个工具声明 `interruptible` 和 `interrupt_priority_threshold`：

```python
cook_food = ToolDefinition(
    tool_id="cook.cook_food",
    duration_seconds=300,
    interruptible=True,
    interrupt_priority_threshold=0.85,  # 只有需求紧迫度 ≥ 0.85 才能打断
    failure_modes=[
        FailureMode(
            code="hunger_collapse_during_cooking",
            emotional_charge="fear",
            summary="做饭做到一半饿到崩溃",
            triggers_heuristic=True,
        )
    ],
)

sleep = ToolDefinition(
    tool_id="life.sleep",
    duration_seconds=28800,  # 8 小时
    interruptible=True,
    interrupt_priority_threshold=0.95,  # 只有极端事件能打断
)
```

中断在 `MotivationEngine.evaluate_npc` 周期内触发：

```python
# 决策周期内，先检查当前是否有 ActiveAction 且需求超过中断阈值
current_action = ActiveActionRegistry.get_for(npc_id)
if current_action:
    most_urgent = max(needs.values(), key=lambda n: n.current * n.weight)
    if most_urgent.current * most_urgent.weight > current_action.tool.interrupt_priority_threshold:
        ToolExecutor.interrupt(current_action.action_id, reason=most_urgent.id)
        # 触发失败模式，写入 npc.action_aborted 事件
        # 进入下一周期决策
```

### 6.3 失败 / 中断的记忆写入

失败和中断**不只是日志**，必须写入观察者的主观记忆，且带情绪强度：

```python
@dataclass
class SubjectiveMemoryEntry:
    entry_id: str
    owner_npc: str               # 哪个 NPC 的视角
    event_id: str                # 关联的客观事件
    
    summary: str                 # 主观措辞
    importance: float            # 0-1
    emotional_charge: str        # joy / fear / anger / shame / surprise / neutral
    emotional_intensity: float   # 0-1
    tags: list[str]              # festival / debt / gift / ...
    
    decay_rate: float            # 衰减速率
    consolidation_count: int     # 被夜间反思引用过几次
    
    associated_with: list[str]   # 关联的工具、NPC、对象
    triggers_heuristic: bool     # 是否会触发启发式提取
```

`emotional_intensity > 0.7` 的失败/中断记忆**必须**进入 reflector 的 heuristic 候选池（详见第 8 节）。

### 6.4 工具冲突解决

NPC A 想 `harvest_crop(plot_5)`，但 NPC B 一秒前已经收完。

策略：**乐观执行 + 失败事件**。

- ToolExecutor 在 `on_action_complete` 时再校验状态
- 状态不再合法则触发 `FailureMode(code="resource_already_consumed")`
- 失败也是社会信号（"我去借东西被拒了"），通过 ResultObserver 写入相关 NPC 主观记忆
- 当前 NPC 立即重新进入决策周期

不做悲观锁、不做 reservation。简单、暴露涌现、不阻塞。

## 7. 双轨主观记忆架构

### 7.1 双轨设计

```text
┌────────────────────────────────────┐
│  Objective Event Log (EventStore)  │  ← 全局客观事实
│  - 所有 npc.action_*                 │
│  - 所有 player.action_*              │
│  - 所有 director.beat_*              │
│  - 所有 system.tick                  │
└────────────────────────────────────┘
                  │
                  │ ResultObserver 分发
                  ▼
┌────────────────────────────────────┐
│  Subjective Memory Views           │  ← 每个 NPC 一份
│  - npc_kai.subjective_view          │
│  - npc_mira.subjective_view         │
│  - npc_player.subjective_view       │
│  ...                                │
└────────────────────────────────────┘
                  │
                  │ Consolidator 滚动压缩
                  ▼
┌────────────────────────────────────┐
│  Semantic Facts (per NPC)          │  ← 抽取出的"事实"
│  - "凯娅欠布兰娜 30 金币"            │
│  - "玩家昨天在我家田里浇过水"         │
└────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────┐
│  Relationship Edges (graph)        │  ← 关系图，每条边带双时间戳
│  - kai → bram: { type: "owes",     │
│      confidence: 0.9,               │
│      valid_from: day1.morning,      │
│      valid_to: null,                │
│      ingested_at: day1.evening }    │
└────────────────────────────────────┘
```

四层各司其职，不接 Graphiti / Mem0 等外部库（理由见第 7.7 节）。

### 7.2 ResultObserver 分发流程

```python
class ResultObserver:
    def distribute(self, decision: ToolDecision, status="completed"):
        # 1. 找到本次行动的"在场观察者"
        observers = WorldState.observers_at(
            location=decision.location,
            visibility=decision.tool.observer_visibility
        )
        # 始终包括 actor 自己
        observers.add(decision.actor_id)
        
        # 2. 对每个观察者走 BiasFilter
        for observer_npc in observers:
            entry = BiasFilter.filter(
                observer=observer_npc,
                actor=decision.actor_id,
                tool=decision.tool,
                status=status,
                world_context=decision.context_summary,
            )
            
            if entry is None:
                continue  # BiasFilter 决定不写入（关注力不足）
            
            SubjectiveMemoryStore.append(observer_npc, entry)
            
            # 3. 副产物：可能产出语义事实和关系边变化
            for fact in entry.derived_facts:
                SemanticFactStore.append(observer_npc, fact)
            for edge_delta in entry.derived_edges:
                RelationshipEdgeStore.apply(observer_npc, edge_delta)
```

### 7.3 BiasFilter（主观性的物理实现）

同一事件 → 6 个 NPC 视角的不同记忆条目。差异来自：

```python
class BiasFilter:
    def filter(observer, actor, tool, status, world_context):
        # 1. 关注力门槛
        attention_score = self._compute_attention(observer, actor, tool)
        if attention_score < observer.attention_floor:
            return None  # 太无关，不记
        
        # 2. 关系偏置
        relationship = RelationshipQuery.get(observer, actor)
        # 朋友/敌人会放大不同情绪、用不同措辞
        
        # 3. 情绪偏置
        observer_mood = MoodQuery.get(observer)
        # 心情差时把中性事件记成负面
        
        # 4. 注意力偏置
        # 当前需求/目标相关的事件 importance 更高
        # 例：缺粮的 NPC 看到"凯娅去种麦"会写成高 importance 记忆
        
        # 5. 性格偏置（NPC 深度卡 personality）
        # 八卦型 NPC 更易记下他人冲突
        # 工作型 NPC 更易记下事务进度
        
        return SubjectiveMemoryEntry(
            owner_npc=observer.id,
            event_id=event.id,
            summary=self._compose_subjective_summary(...),
            importance=...,
            emotional_charge=...,
            emotional_intensity=...,
            ...
        )
```

`_compose_subjective_summary` 在规则层使用模板 + slot fill；在升级层（Phase 3+）可以走局部 LLM 让措辞更自然。**模板 + slot fill 已经足够支撑 Rashomon 演示**——因为差异主要来自 importance / emotional_charge / tag 选择，而非措辞本身。

### 7.4 关系图边

关系不再是单一 affection 数值，而是**多类型有向边**，每条带双时间戳：

```python
@dataclass
class RelationshipEdge:
    edge_id: str
    from_npc: str
    to_npc: str
    
    edge_type: str               # "trusts" / "owes" / "loves" / "envies" / "respects" / ...
    strength: float              # 0-1
    confidence: float            # 0-1, 该 NPC 对这条边的把握
    
    valid_from: GameTime         # 何时建立
    valid_to: Optional[GameTime] # 何时失效（null = 仍生效）
    
    ingested_at: GameTime        # 何时被记录（Graphiti bi-temporal 风格）
    source_event_ids: list[str]  # 证据
    
    last_reinforced_at: GameTime # 最后被强化的时间
```

聚合查询（"凯娅总体上信任布兰娜吗"）通过对所有相关边加权求和得到。**这是 Graphiti 风格的 bi-temporal**，但我们自己实现，不依赖 Neo4j。

### 7.5 Semantic Facts

从主观视图中抽取出的"事实"：

```python
@dataclass
class SemanticFact:
    fact_id: str
    owner_npc: str
    statement: str               # "凯娅欠布兰娜 30 金币"
    confidence: float
    
    valid_from: GameTime
    valid_to: Optional[GameTime]
    ingested_at: GameTime
    
    source_memory_ids: list[str] # 哪些主观记忆条目支撑这个事实
    contradicts: list[str]       # 与哪些 fact 矛盾
```

由 Reflector 在夜间反思时抽取，也可在工具执行后立即抽取（比如 `borrow_gold` 完成后立刻产出 `owes` 事实）。

### 7.6 召回（Retrieve）

NPC 决策时调用 `recall(npc_id, query, k)`：

```python
def recall(npc_id, query: RecallQuery, k=8):
    # 1. Triage 三因子打分（Smallville 公式起点）
    candidates = SubjectiveMemoryStore.all_for(npc_id)
    triage_scored = [
        (e, recency(e) * 0.3 + importance(e) * 0.4 + relevance(e, query) * 0.3)
        for e in candidates
    ]
    
    # 2. 关系跳转扩展
    if query.expand_via_relationships:
        related_npcs = RelationshipQuery.expand(npc_id, hops=2)
        triage_scored += [(e, _score(e, query) * 0.7)  # 折扣
                          for npc in related_npcs
                          for e in SubjectiveMemoryStore.all_for(npc) if e.shared_with(npc_id)]
    
    # 3. 时间约束
    if query.time_window:
        triage_scored = [(e, s) for e, s in triage_scored if e.in_window(query.time_window)]
    
    # 4. 语义召回（向量，可后置）
    if query.semantic_query:
        semantic_hits = VectorIndex.search(npc_id, query.semantic_query, top=k*2)
        # 与 triage 结果合并去重
    
    # 5. 排序取 top-k
    return sorted(triage_scored, key=lambda x: x[1], reverse=True)[:k]
```

向量索引在首版可以是**纯内存 cosine similarity over OpenAI embeddings**，等数据规模上来再换 FAISS / Qdrant。

### 7.7 为什么不接 Graphiti / Mem0 / Letta

调研结论（详见 archive 中讨论历史，本节作为决策记录）：

- **Graphiti**：双时间戳 + 实体边有效期 + episodic/semantic/community 三层是最匹配的范式，**但强依赖 Neo4j**，会让本地开发链路变重，6-12 NPC 规模杀鸡用牛刀。结论：**借鉴范式，自研抽象层**。
- **Mem0**：单 agent 长记忆 + 向量召回，缺多 NPC 主观性差异化，需要在它之上叠 BiasFilter 层。结论：**功能不够 + 还要加层，不如自研**。
- **Letta (MemGPT)**：分层 + agent 自编辑记忆，适合长会话连续，**不适合多 agent 主观差异**。结论：**形态不匹配**。
- **RAGFlow**：文档 RAG，擅长 PDF/表格解析，**与"事件流 → 主观印象"形态错位**。结论：**领域不匹配**。

自研路线保持小规模可控，schema 借鉴 Graphiti 的双时间戳和分层，未来如果规模扩大可以把 `RelationshipEdgeStore` 后端换成 Neo4j 或接 Graphiti，retrieve 层不用动。

### 7.8 遗忘曲线与归档

```python
class MemoryDecayPolicy:
    def daily_tick(self, npc_id):
        for entry in SubjectiveMemoryStore.all_for(npc_id):
            # 衰减
            entry.importance *= (1 - entry.decay_rate)
            
            # 情绪强度衰减更慢
            entry.emotional_intensity *= (1 - entry.decay_rate * 0.5)
            
            # 多次被夜间反思引用 → 巩固，衰减率降低
            if entry.consolidation_count >= 3:
                entry.decay_rate *= 0.7
            
            # 低于阈值归档（不删除，移出主索引）
            if entry.importance < 0.05 and entry.emotional_intensity < 0.1:
                ArchivedMemoryStore.move(entry)
```

归档不删除，保留给 Eval Framework 做长期对照。

## 8. 启发式学习（Heuristic Library）

### 8.1 设计目标

让 NPC 的决策机制本身被经验改写，而不只是"记忆累积导致对话不一样"。这是项目"自我进化"叙事的硬支撑。

### 8.2 Heuristic Schema

```python
@dataclass
class HeuristicMemory:
    heuristic_id: str
    owner_npc: str
    
    extracted_at: GameTime
    extracted_from: list[str]    # 触发提取的 SubjectiveMemoryEntry ids
    extraction_method: Literal["rule", "llm_reflector"]
    
    # 触发模式（什么情境激活这条经验）
    trigger_pattern: TriggerPattern
    
    # 调整方式
    adjustment: HeuristicAdjustment
    
    # 元信息
    confidence: float            # 0-1, 多次成功后上升，多次失败后下降
    duration_days: float         # 衰减时间
    activation_count: int        # 被激活过几次
    success_count: int           # 激活后行为成功的次数
    
    narrative: str               # NPC 自述"上次饿到差点晕，下次得早点准备"
    user_visible: bool           # Debug Console 是否展示

@dataclass
class TriggerPattern:
    needs: dict[str, str]        # {"hunger": ">0.7"}
    context: list[str]           # ["no cooked_food in inventory"]
    location_hint: Optional[str]
    relationship_state: Optional[dict]

@dataclass
class HeuristicAdjustment:
    type: Literal["preempt_threshold", "boost_capability", "blacklist_tool", 
                  "force_tool_pick", "modify_need_weight"]
    target: str                  # 需求 id / 工具 id
    delta: float
    reason_summary: str
```

### 8.3 提取流程

由 Reflector（夜间反思）执行：

```python
def extract_heuristics_for(npc_id):
    # 1. 找到今天高情绪强度的失败/中断记忆
    candidates = SubjectiveMemoryStore.query(
        npc_id=npc_id,
        emotional_intensity_gte=0.7,
        triggers_heuristic=True,
        time_window="today"
    )
    
    # 2. 对每条，尝试规则提取（patterns 表 + LLM 增强可选）
    for memory in candidates:
        # 规则提取：根据 failure_mode 模板
        rule_extracted = RuleHeuristicExtractor.try_extract(memory)
        if rule_extracted:
            HeuristicLibrary.add(npc_id, rule_extracted)
            continue
        
        # LLM 提取（受预算约束，每天 ≤ 2 次）
        if DecisionBudget.can_use("heuristic_extraction", npc_id):
            llm_extracted = LLMHeuristicExtractor.extract(memory)
            if llm_extracted:
                HeuristicLibrary.add(npc_id, llm_extracted)
                DecisionBudget.consume("heuristic_extraction", npc_id)
```

### 8.4 激活流程

每个决策周期内，HeuristicLibrary 检查所有 active heuristics 的 trigger pattern 是否命中：

```python
class HeuristicLibrary:
    def get_active_for(self, npc_id, world_context):
        active = []
        for h in self._all_for(npc_id):
            if h.confidence < 0.2:
                continue  # 太弱，不激活
            if h.trigger_pattern.match(world_context):
                active.append(h)
                h.activation_count += 1
        return active
```

激活的 heuristic 通过 `MotivationEngine` 注入需求权重偏置或工具优先级修改，**结果可以追溯到具体 heuristic_id**。

### 8.5 反馈与衰减

```python
def update_heuristic_after_action(heuristic_id, action_result):
    h = HeuristicLibrary.get(heuristic_id)
    if action_result.success:
        h.success_count += 1
        h.confidence = min(1.0, h.confidence + 0.05)
    else:
        h.confidence = max(0.0, h.confidence - 0.1)
    
    # 长期未激活 → 衰减
    if (current_game_time - h.last_activated_at).days > h.duration_days:
        h.confidence *= 0.8

    # 互相冲突的 heuristic 由 confidence 加权裁决
```

### 8.6 设计师注入的 heuristicSeeds

NPC 深度卡新增字段：

```json
{
  "heuristicSeeds": [
    {
      "heuristic_id": "kai_pre_performance_warmup",
      "trigger_pattern": {
        "context": ["upcoming_performance_within_2_hours"],
        "needs": {"recognition": ">0.4"}
      },
      "adjustment": {
        "type": "boost_capability",
        "target": "craft.play_music",
        "delta": 0.4
      },
      "confidence": 0.8,
      "narrative": "演出前要排练，这是我多年总结的习惯"
    }
  ]
}
```

设计师注入的 seed heuristic 让新角色不会一开始就反复犯蠢。但每个 seed 都是 confidence 0.8 起，仍会被失败经验下调，仍会被新提取的 heuristic 覆盖。

### 8.7 可视化与作品集卖点

Debug Console 应展示：

- 每个 NPC 当前激活的 heuristic 列表
- 每条 heuristic 的 narrative + extracted_from 跳转链接（可以点回原始失败记忆）
- 每次决策时哪些 heuristic 影响了选择
- heuristic 的 confidence 曲线随时间变化

这是项目"NPC 看得见地成长"的可演示证据。一段录屏：第一周凯娅周三周四周五连续饿到崩溃 → 第二周自动提前做饭，Debug 面板显示她正在执行 `heuristic_kai_001`。

## 9. 竞争上下文仲裁（Arbitration）

### 9.1 输入源

NPC 决策每周期同时面对：

| 输入源 | 提供者 | 形态 |
|---|---|---|
| 内部需求 | NeedAccumulator | dict[need_id → urgency] |
| Director Beat 偏置 | DirectorBeatRegistry | dict[need_id → delta] |
| Event Skill 局部约束 | EventSkillRegistry.active_for(npc) | allowlist + blocklist + brief |
| 长期目标 | NPC.goals | dict[goal_id → unblocking_actions] |
| 启发式经验 | HeuristicLibrary | list[active_heuristics] |
| 主观记忆召回 | SubjectiveMemoryStore.recall | top-k memories |
| 信念模型（可选） | BeliefAbout（Phase 4+） | dict[other_npc → BDI] |

每个输入源带 confidence 和 decay。

### 9.2 仲裁流程

```python
class ArbitrationLayer:
    def resolve(self, npc_id, inputs: ArbitrationInputs) -> Decision:
        # 1. 计算每个候选行动的"组合得分"
        candidate_actions = []
        
        for tool in inputs.capability_subset:
            score = (
                inputs.need_urgency.get(tool.served_needs, 0) * NEED_WEIGHT
                + inputs.director_bias.score_for(tool) * DIRECTOR_WEIGHT
                + inputs.event_skill_bias.score_for(tool) * SKILL_WEIGHT
                + inputs.goal_progress.score_for(tool) * GOAL_WEIGHT
                + inputs.heuristic_modifier.score_for(tool) * HEURISTIC_WEIGHT
                + inputs.memory_relevance.score_for(tool) * MEMORY_WEIGHT
            )
            
            # 2. 硬约束（disallowed_tools / preconditions failure）
            if not tool.preconditions_met(npc_id):
                continue
            if tool.tool_id in inputs.event_skill_bias.disallowed_tools:
                continue
            
            candidate_actions.append((tool, score))
        
        # 3. 输出 Decision，记录 contributing_sources 给 Debug
        winner = max(candidate_actions, key=lambda x: x[1])
        return Decision(
            tool=winner[0],
            score=winner[1],
            contributing_sources=self._explain(inputs, winner[0]),
        )
    
    def _explain(self, inputs, tool):
        # 给 Debug Console 展示每个输入源对最终选择贡献了多少分
        return {
            "need_urgency": inputs.need_urgency.score_for(tool),
            "director_bias": inputs.director_bias.score_for(tool),
            "event_skill_bias": inputs.event_skill_bias.score_for(tool),
            "goal_progress": inputs.goal_progress.score_for(tool),
            "heuristic_modifier": inputs.heuristic_modifier.score_for(tool),
            "memory_relevance": inputs.memory_relevance.score_for(tool),
        }
```

权重 `NEED_WEIGHT / DIRECTOR_WEIGHT / ...` 在 `config/arbitration_weights.json` 配置，可热更新。

### 9.3 LLM 决策时的 Arbitration

如果 ToolPicker 路由到 Social/Strategic 层走 LLM，LLM 接收的 prompt 不是规则得分，而是结构化输入摘要：

```text
You are Kai. Now is Day 1 evening.

CURRENT STATE:
- Location: tavern
- Top need: affiliation (urgency=0.78)
- Energy: 0.4 (somewhat tired)

DIRECTOR BRIEF: "Festival supply tension is escalating. Player is nearby."

ACTIVE EVENT SKILL: starlight_festival_shortage
- You are a participant
- Disallowed tools: spread_rumor (avoid escalating)
- Brief: "Try to keep festival mood, but the debt issue can no longer be avoided."

ACTIVE HEURISTICS:
1. heur_kai_002 (confidence=0.7): "When tense conversation looms, music helps soften."
   → suggests: play_music

LONG-TERM GOAL: kai_perform_at_starlight_festival (progress=0.3)

RECENT MEMORIES (from your subjective view):
1. [day1.afternoon, importance=0.7, fear] Bram refused to deliver crops; I felt cornered.
2. [day1.morning, importance=0.5, joy] Player gave me a flower at the plaza.

CANDIDATE TOOLS (filtered):
1. social.chat_with(target=bram, topic="festival_supply") — direct confrontation
2. social.chat_with(target=player, topic="ask_for_help") — leverage recent good memory
3. craft.play_music(at=tavern_stage) — heuristic-suggested
4. social.give_gift(target=bram, item=...) — soften via gesture

Please choose ONE tool and explain in 1-2 sentences how this serves your situation. Output JSON.
```

LLM 输出 → DirectorValidator 校验 → ToolExecutor 执行。Validator 拦截：越权工具、不存在的目标、不一致情绪。

### 9.4 Debug Trace（可追溯因果）

每次 Arbitration 写入：

```python
EventStore.append({
    "type": "decision.arbitration",
    "npc_id": npc_id,
    "decision_id": d_001,
    "selected_tool": "craft.play_music",
    "contributing_sources": {
        "need_urgency": 0.78,
        "director_bias": 0.30,
        "heuristic_modifier": 0.40,  # 来自 heur_kai_002
        "memory_relevance": 0.55,
    },
    "alternative_considered": [
        {"tool": "social.chat_with(bram)", "score": 0.62},
        {"tool": "social.chat_with(player)", "score": 0.59},
    ],
    "decision_layer": "social_strategic_llm",
    "llm_call_id": "llm_xxx",
    "fallback_triggered": false,
})
```

任何 NPC 行为都可逆向追溯到具体输入源、具体记忆、具体 heuristic。这是亮点 4（因果链）的存储基础。

## 10. Eval Framework

### 10.1 设计目标

Eval Framework 是项目第五条核心能力，理由：

- 直接证明"少而深 ≥ 多而浅"的差异化论点（关闭 subjective_memory 后某指标退化）
- 建立 baseline 心智，给 blog 提供量化图表
- 回归测试，AI 助手开发模式下作为护栏
- 输出 dataset，作为可复现 portfolio 资产

### 10.2 入口与执行模式

```bash
# 离线规则跑（CI 友好、零成本）
python scripts/run_agent_eval.py --provider rule --suite default

# 真实 LLM 跑（手动触发，记录成本）
python scripts/run_agent_eval.py --provider cloud --suite default

# 单个 scenario
python scripts/run_agent_eval.py --scenario L2_player_gift_propagation

# 对照实验（关闭某个能力）
python scripts/run_agent_eval.py --suite default --ablate subjective_memory
python scripts/run_agent_eval.py --suite default --ablate heuristic_library
python scripts/run_agent_eval.py --suite default --ablate director_layer
```

#### Hard Delegation baseline（2026-05-20 增补）

Director 将目标反推为显式 todo，并把 todo 直接委派给 NPC 执行。它代表传统 task delegation / parent-worker agent 模式，是 Phase 2 必须加入的强 baseline。Full 系统如果只比 direct state setter 强，不足以证明 Motivational Delegation 的价值；必须证明在 process fidelity、agent autonomy、side effect、relationship memory causal use 等指标上优于 Hard Delegation。

完整 baseline matrix（Direct State Setter / Static Todo Planner / Hard Delegation / Director w/o Subjective Memory / Full Motivational Delegation）与运行约定详见 [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md) §3、§5。

### 10.3 Scenario Suite 分层

| 层 | 数量 | 描述 | 例子 |
|---|---|---|---|
| L1 unit-like | 5-8 | 单 NPC 单工具 | NPC X 在 hunger=0.8 时是否选择 cook_food |
| L2 social | 5-8 | 2-3 NPC 互动 | A 送礼给 B → B 主观记忆是否正确写入 → C 看见后是否有观察记忆 |
| L3 emergent | 3-5 | 玩家扰动 + 全 NPC 24 游戏小时 | 玩家在 day1.morning 给 A 送花 → 24 小时内 B/C 是否在对话中引用 |

总计 13-21 个 scenario。

### 10.4 核心指标

```python
class EvalMetrics:
    # 用户指定的核心 8 个
    action_validity_rate: float         # 模型输出动作是否合法
    memory_reference_rate: float        # 后续对话是否引用相关记忆
    memory_grounding_precision: float   # 引用的记忆是否真实存在
    causal_trace_coverage: float        # 关键状态变化是否都有 evidence
    relationship_consistency: float     # 关系阶段变化是否符合阈值
    fallback_rate: float                # LLM 失败/非法输出后的 fallback 比例
    avg_latency_ms: float               # 平均延迟
    estimated_cost_usd: float           # 估算成本
    
    # 新定位下的差异化指标
    causal_trace_depth_avg: float       # 玩家行为引发的因果链平均跳数
    subjective_divergence: float        # 同一事件在不同 NPC 视角的措辞/情绪/重要性差异度
    heuristic_uptake_rate: float        # 提取的 heuristic 在后续决策中的引用频率

    # 2026-05-20 研究向增补：Process Fidelity 与 Motivational Delegation。
    # 完整公式与说明见 process_fidelity_eval_spec.md §4。
    process_fidelity_score: float            # 过程保真综合得分
    shortcut_violation_rate: float           # 硬改状态 / 跳过中间过程的比例
    forced_action_rate: float                # Director 显式指定 NPC 动作的比例
    agent_initiated_action_ratio: float      # ArbitrationLayer 自主选择的动作比例
    intervention_overreach_rate: float       # Director 越权干预（直改关系 / 对话结果）的比例
    relationship_memory_causal_use_rate: float  # 关系记忆在决策中是否真有因果作用
    memory_ablation_delta: float             # Full vs No-Memory 在关键指标上的差值
    side_effect_score: float                 # 预期外关系 / 记忆溢出的侧效应评分
```

`subjective_divergence` 计算方式：对同一 event_id，取所有观察者的 SubjectiveMemoryEntry，计算 (importance, emotional_charge, tag_set) 的 pairwise 距离平均值。

`process_fidelity_score` 、 `shortcut_violation_rate` 、 `relationship_memory_causal_use_rate` 等 8 个 Process Fidelity 指标仅在本文作为 EvalMetrics schema 声明，具体计算公式、ablation 协议、GoalSpec schema 与 Phase 2 补充验收条件详见 [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md)。

`causal_trace_depth_avg` 计算方式：对玩家每次 player.action_*，沿着观察记忆 → NPC 后续行动 → 第三方观察 这条链反向追溯，统计平均跳数。

### 10.5 输出形态

每次 eval 输出：

```text
.kiro/eval-runs/
├── run_2026-05-19T14-30-00/
│   ├── summary.json          # 所有指标
│   ├── per_scenario/
│   │   ├── L1_kai_hunger_to_cook.json
│   │   ├── L2_player_gift_propagation.json
│   │   └── ...
│   ├── ablation_comparison.json   # 与对照组对比
│   ├── event_store_dump.jsonl     # 完整 EventStore
│   └── subjective_views_dump.jsonl # 所有 NPC 主观视图
```

`event_store_dump.jsonl` + `subjective_views_dump.jsonl` 就是可公开的 dataset 资产。

### 10.6 与 npm.cmd run check 的集成

```text
npm.cmd run eval:rule        # 规则版 eval suite，加入 CI
npm.cmd run eval:cloud       # 真实 LLM eval，手动触发
npm.cmd run eval:ablate      # 对照实验
```

`npm.cmd run check` 默认包含 `eval:rule` 简化版（只跑 L1）。

### 10.7 Eval Schema 在 Phase 2 必须建立

Phase 2 启动时，Eval Framework 的 schema、metric 计算函数、L1 scenario suite **必须先到位**，不能等做完再补。否则差异化论点没有量化证明。完整 L2/L3 scenario 可以在 Phase 3 补。

## 11. NPC 深度卡 schema 扩展

NPC 深度卡新增三个字段（在 `npc_deep_card_spec.md` 中正式定义，本文给出形态）：

```json
{
  "motivationProfile": {
    "needs": {
      "hunger":       {"weight": 1.0, "decay_rate": 0.05, "threshold_trigger": 0.6, "threshold_critical": 0.9},
      "energy":       {"weight": 0.9, "decay_rate": 0.04, "threshold_trigger": 0.7, "threshold_critical": 0.95},
      "money_anxiety":{"weight": 0.8, "decay_rate": 0.02, "threshold_trigger": 0.5, "threshold_critical": 0.8},
      "affiliation":  {"weight": 1.2, "decay_rate": 0.03, "threshold_trigger": 0.5, "threshold_critical": 0.85},
      "recognition":  {"weight": 1.0, "decay_rate": 0.02, "threshold_trigger": 0.5, "threshold_critical": 0.8}
    },
    "personalityModifiers": {
      "extroversion": 0.8,
      "risk_appetite": 0.6,
      "conscientiousness": 0.5
    }
  },
  
  "capabilityPreferences": {
    "social.chat_with":   {"affiliation_boost": 0.3, "recognition_boost": 0.2},
    "craft.play_music":   {"recognition_boost": 0.4},
    "social.give_gift":   {"affiliation_boost": 0.2}
  },
  
  "heuristicSeeds": [
    {
      "heuristic_id": "kai_pre_performance_warmup",
      "trigger_pattern": {"context": ["upcoming_performance_within_2_hours"], "needs": {"recognition": ">0.4"}},
      "adjustment": {"type": "boost_capability", "target": "craft.play_music", "delta": 0.4},
      "confidence": 0.8,
      "narrative": "演出前要排练，这是我多年总结的习惯"
    }
  ]
}
```

Phase 2 启动时这三个字段必须 schema 到位，每张深度卡填占位空数据。Phase 3 内容期填实际数据。

## 12. 玩家与 NPC 共享接口 + 观察者模式

### 12.1 玩家工具调用走同一套 ToolDefinition

玩家 UI 触发的工具调用打 `actor_type=player` 标记，但走完全相同的 ToolExecutor 路径。这点保证：

- 玩家行为产生的 EventStore 条目和 NPC 行为完全一致
- ResultObserver 把玩家行为分发为在场 NPC 的主观记忆
- BiasFilter 看到 actor_type=player 时可以差异化 prompt（NPC 对玩家会有"陌生"权重）

### 12.2 观察者模式

观察者模式从原 Phase 5 提升为 Phase 2 必须支持的核心能力。具体形态：

- 玩家可在游戏内随时切换（默认 Tab 键）
- 观察者模式下玩家角色变为半透明幽灵或消失
- 玩家可以点击任何 NPC 查看：当前 motivation 状态、激活的 heuristic、最近记忆、关系图边、当前 Arbitration 解释
- 玩家可"干预"：投放物品、触发事件、修改 NPC 情绪、注入临时 Director Beat
- 干预编码为 `directorBeat(beatType="player_intervention")`，进入正常 Director Beat 流程

### 12.3 观察者模式 UI 与 Debug Console 关系

观察者模式的"NPC 信息面板"与 Web Debug Console 共用同一组数据（subjective view, motivation state, heuristic library, arbitration trace），但渲染层不同：

- 观察者模式：Godot 内置面板，叙事化展示
- Web Debug Console：研究院视角，结构化展示

后端只暴露一组 API，两个客户端都消费。

## 13. Phase 衔接

### 13.1 与 Phase 1 的关系

Phase 1（"活着的世界"）已使用 `LifeActionExecutor` + `/api/world/tick` 完成收口，这套机制 Phase 2 启动时**直接退役**：

- `LifeActionExecutor` 改名为 `MotivationEngine`（或新建 MotivationEngine，LifeActionExecutor 移除）
- `lifeActionPlan` API 字段保留，语义改为"基于当前需求的下一步候选"
- `npcSchedules` API 字段保留，给 Godot 客户端做日程可视化用
- 所有"软日程权重"相关代码移除

### 13.2 不并行运行

不做"旧规则 + 新动机"并行。原因：AI 助手协作下并行运行会导致两套代码相互污染，且新系统证据被旧系统稀释。早做断舍离对项目有利。

### 13.3 Phase 2 必须一次性到位的骨架

本节只列 Agent Loop 内部 11 项。完整 Phase 2 总骨架还包括 WorldEntities / ResearchFraming / DomainAdapter / ProcessFidelityEval，详见 `production_roadmap.md` §4.3。

| 模块 | 形态 | 备注 |
|---|---|---|
| ToolDefinition + ToolRegistry | 完整接口 | 至少注册 8-12 个工具实现 |
| MotivationEngine | 完整决策周期 | 三层路由 + 决策预算 + Fallback |
| CapabilityRegistry | 动态生成 | 5 层过滤 / 路由齐全 |
| NeedAccumulator | 完整 4 类需求 | 每 NPC NeedProfile 实例 |
| ArbitrationLayer | 完整裁决 + Trace | contributing_sources 完整 |
| ResultObserver + BiasFilter | 模板 + slot fill 版 | LLM 增强放 Phase 3 |
| SubjectiveMemoryStore | 完整 schema | record/list/recall/debug 已落地；tick 级 effectiveSalience 衰减、低显著性归档、active / archived debug 计数已接入；夜间反思 consolidation 写回继续收紧 |
| RelationshipEdgeStore | 双时间戳 | 至少 5 种边类型 |
| HeuristicLibrary | 完整 schema | 规则提取 + 衰减 + Debug 已落地；LLM 提取受预算约束继续收紧 |
| EvalFramework | scripts/run_agent_eval.py + L1 suite | 5-8 个 L1 scenario |
| Godot 观察者模式 | 最小可用 | 切换 + NPC 信息面板 |

### 13.4 Phase 3 内容期

骨架到位后 Phase 3 是纯加内容：

- 5 作物 × 5 阶段
- 25 物品
- 30 工具完整实现
- 4 核心 NPC 全接入 motivationProfile / capabilityPreferences / heuristicSeeds 实际数据；2 stub 继续默认权重或按需要升级
- L2/L3 scenario suite 完整
- 资产批次 B1-B5 落地

### 13.5 与 archive 文档的覆盖关系

本文档取代以下旧设计：

- `archive/architecture_blueprint.md` 中的 NPC 行为描述（早期单层 NPC 调度）
- `archive/vertical_slice_spec.md` 中的"软日程"描述
- `archive/core_map.md` 中的"动机系统"草稿（已升级为本文形态）
- `gameplay_system_architecture.md` 第 2.4 节已同步为 MotivationEngine 驱动的行为节奏，覆盖早期"软日程代替固定排班"描述

### 13.6 Eval 是 Phase 2 的硬验收线

Phase 2 收口标准：

- `npm.cmd run eval:rule` 通过
- L1 scenario suite 全部通过
- 至少 1 次 ablation 实验数据（关闭 subjective_memory 或 heuristic_library，对比关键指标）
- 规则版 NPC 决策周期可稳定运行 24 游戏小时不崩溃
- Debug Trace 可完整解释任意一次决策

不达标不进入 Phase 3。
