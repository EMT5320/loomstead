---
status: active
owner_lane: vision
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: long-term product vision, differentiation, and success criteria
---

# 项目整体愿景：Loomstead

> 本文是项目后续推进的核心依据。后续设计、实现、取舍和阶段验收都优先对齐这里定义的方向。
> 2026-05-19 项目重定位：从"二次元田园 RPG"调整为"可解释的多 Agent 叙事运行时"。差异化主轴是"少而深 + 可解释 + 可评估"。
> 2026-05-20 研究 framing 增补：narrative-primary / task-secondary，研究主卖点改为 Motivational Delegation + Process Fidelity Eval（详见 `research_framing_motivational_delegation.md`）。

## 一句话定位

`Loomstead` 是一个 **narrative-primary 的可解释多 Agent 叙事运行时与研究环境**：通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，研究 Director 如何以 **Motivational Delegation** 的方式间接驱动少量深度 NPC 朝过程约束目标演化，并用 **Process Fidelity Eval** 验证"目标达成过程是否可信"。

2026-05-20 研究 framing 更新：小镇不再被描述为"通用架构的引言"，而是 primary validation domain。Process Fidelity 需要人类能直觉判断过程是否合理的场景；恋爱、和解、节日、信任修复和谣言传播这类叙事目标天然暴露"直接硬改状态"和"可信过程演化"的区别。跨域任务环境保留为 secondary validation，用于证明 GoalSpec / Intervention / Trace / Eval 抽象具备迁移可能，但不反客为主。

## 差异化定位

2026 年 LLM agent 小镇赛道已经成熟（Stanford Smallville / a16z AI Town / Altera Project Sid / AIvilization 10 万 agent）。本项目**不再追逐规模或游戏完整度**，而在以下维度建立差异化：

1. **少而深**：4 核心 NPC 拥有真正的内心生活（主观记忆、启发式经验、信念模型），不堆量到千 agent。
2. **可解释**：每个决策可逆向追溯到具体输入源、记忆条目、启发式经验；Debug Trace 是项目作品集核心资产。
3. **可评估**：Eval Framework 量化主观性发散度、因果链长度、启发式采纳率等指标，用 ablation 实验证明能力价值。
4. **可分享**：同事件不同视角的 Rashomon 玩法、NPC 从失败成长的 timeline、玩家行为引发的因果链，都是 30 秒级可分享 demo 内容。

## 项目目标

把项目升级为可被 LLM agent 圈识别的 **"少而深"路线代表作**：

1. **可玩切片**：Godot 田园生活切片作为 demo scenario，玩家能在地图中移动、对话、送礼、触发事件。
2. **技术深度**：多层 Agent + 三层工具分层 + 双轨主观记忆 + 启发式学习 + 竞争上下文仲裁，全部可解释。
3. **量化证据**：Eval Framework 输出指标 + ablation 数据 + 公开 dataset。
4. **作品集传播**：技术博客主文 + 短录屏（每个亮点一个）+ 交互式 Web Debug Console。
5. **能持续扩展**：首版结构能承载后续多日循环、节日、委托、长期剧情。

## 长期产品方向

首版目标是“第一天”可玩章节，长期目标是一座可以持续扩展的小镇：

- 多日生活循环。
- 更完整的农场经营。
- 更多居民、家庭、职业和关系网络。
- 节日、委托、突发危机和长期剧情线。
- 角色成长、关系阶段和小镇状态变化。
- 可回放的 Agent 决策与世界事件历史。
- 面向作品集和产品演示的稳定打包版本。

首版开发需要服务这个长期方向。可以裁剪内容规模，但关键工程结构要保留扩展路径。

## 核心体验

玩家进入小镇后，可以：

- 操控自己的角色在地图中移动。
- 与 NPC 对话，影响对方对玩家的印象。
- 送礼、参加活动、触发特殊事件。
- 通过持续对话、送礼和事件选择积累好感，为后续恋爱线做铺垫。
- 观察 NPC 根据日程、目标、情绪和记忆自主行动。
- 看到小镇中的事件被不同 NPC 以不同方式记住。
- 在 Debug / 研究控制台中查看 Agent 输入、模型输出、工具调用、记忆写入和世界状态变化。

## 核心创新点

### 0. 多层 Agent 游戏系统

`Loomstead` 的核心是可被游玩的涌现社会，由规则、压力源、记忆和 Agent 主观判断共同生成体验。

系统分为：

- **World / Simulation Layer**：持有权威世界状态，执行合法工具行动，保证时间、地点、物品、关系、事件和记忆一致。
- **Director System**：低频规划叙事节奏、激活事件 Skill、分发局势 brief，并通过可验证、可过期的 Director Beat 影响后续世界节奏。
- **Event Skill Layer**：以渐进式加载方式提供情境压力，平时只暴露触发条件，激活后加载参与者、brief、工具、约束、后果类型和资产提示。
- **NPC Agents**：在自身角色卡、记忆、关系和导演 brief 内自主选择工具行动。
- **Player State Agent**：只总结玩家风格与历史选择，帮助世界理解玩家形象，不替玩家操作。
- **Debug / Explainability Layer**：记录导演、Skill、NPC、工具、记忆和关系变化的完整链路。

设计师负责提供土壤、舞台、规则和压力源；LLM Agent 负责在边界内做主观判断、表达、记忆和关系演化。多层 Agent 架构见 [`agentic_game_design.md`](./agentic_game_design.md)，游戏本体架构见 [`gameplay_system_architecture.md`](./gameplay_system_architecture.md)。

### 0.1 涌现式田园生活模拟本体

首版游戏本体要从临时 UI demo 收束为地图主循环：

- 玩家在地图中移动、靠近 NPC 或物体并触发交互。
- 种田、背包、送礼、关系、事件和记忆形成可感知闭环。
- NPC 具备生活习惯、职业倾向和地点偏好，但具体出现位置和行动由软日程权重、世界约束、导演层节奏、Event Skill 和 NPC 自主判断共同生成。
- 导演层负责阶段节奏、舞台焦点、事件压力和 NPC 聚散密度，避免居民长期堆在同一画面。
- Godot 主界面优先服务沉浸式地图和 VN 演出，Debug / 研究信息默认收纳到调试层。

### 1. 三层工具分层 + 动机系统替换软日程

NPC 行为来自内部需求而非时间表：

- **Physiological 层**：饥饿、体力、睡眠 → 规则触发
- **Vocational 层**：种田、开店、做饭 → 规则 + 局部 LLM
- **Social/Strategic 层**：对话、送礼、谋略 → LLM（受预算约束，每 NPC 每日 ≤ 8 次）

Capability registry 动态生成（NPC × 地点 × 物品状态）每周期 3-8 个候选工具，避免 LLM 上下文被 30 个工具淹没。

详见 [`agent_loop_architecture.md`](./agent_loop_architecture.md)。

### 2. 双轨主观记忆（Rashomon 玩法）

```text
Objective Event Log         ← 客观事实
       ↓ ResultObserver + BiasFilter
Subjective Memory Views × N  ← 每个 NPC 一份，措辞/情绪/重要性差异化
       ↓ Reflector / Consolidator
Semantic Facts + Relationship Edges (双时间戳)
```

同一事件被 6 个 NPC 写成 6 个版本：温馨/嫉妒/八卦/无所谓/担忧/讽刺。Debug Console 可 side-by-side 展示。范式借鉴 Graphiti，自研抽象层不接 Neo4j。

### 3. 失败驱动的启发式学习（NPC 看得见地成长）

NPC 从痛苦经验自动提取避坑规则：

```
失败记忆（情绪强度 ≥ 0.7） → Reflector 提取
  → HeuristicMemory(trigger_pattern, adjustment, confidence, narrative)
  → 注入下次决策的需求权重 / 工具优先级
  → 行为改变可观测、可量化
```

第一周凯娅周三周四周五连续饿到崩溃 → 第二周自动提前做饭，Debug 面板展示她正在执行 `heuristic_kai_001`。这是项目"自我进化"叙事的硬支撑。

### 4. 竞争上下文仲裁（全过程可解释）

NPC 决策时同时面对：内部需求 + Director Beat 偏置 + Event Skill 局部约束 + 长期目标 + 启发式经验 + 主观记忆召回 + 信念模型（可选）。Arbitration Layer 结构化裁决，每次决策的 `contributing_sources` 写入 EventStore，玩家点击任意 NPC 行为可逆向追溯。

### 5. Motivational Delegation（动机委派）

用户目标不会被 Director 直接执行，也不会被拆成硬性 todo-list 分配给 NPC。Director 只能通过 `motivation_bias`、`event_skill_load`、`opportunity_schedule`、`resource_shift`、`information_exposure`、`constraint_injection` 等间接干预改变 Agent 的行动分布。NPC 是否接受、如何行动、是否失败，由自身动机、记忆、关系和 ArbitrationLayer 决定。

这是 Director / NPC 协作的根本范式：Director 不当 worker 调度器，而是"塑造世界条件让 Agent 自己想去做"。详见 [`research_framing_motivational_delegation.md`](./research_framing_motivational_delegation.md)。

### 6. Process Fidelity Eval（过程保真评估）

Eval 不只判断最终状态是否达成，还判断过程是否可信：是否绕过了中间过程、是否强制 Agent 行动、关键关系变化是否有记忆证据、Director 是否过度干预、Agent 行为是否与其长期记忆和关系一致。该体系用于回答"为什么不直接 task delegation"以及"关系记忆是否真的影响结果"两条核心反论点。

Process Fidelity 在原 Eval Framework（下文 §7）之上新增 `shortcut_violation_rate`、`required_process_coverage`、`forced_action_rate`、`relationship_memory_causal_use_rate` 等指标，并要求引入 Hard Delegation baseline 与关系记忆 ablation。详见 [`process_fidelity_eval_spec.md`](./process_fidelity_eval_spec.md)。

### 7. Eval Framework（量化差异化论点）

`scripts/run_agent_eval.py` 跑分层 scenario suite（L1 单 NPC × 5-8 / L2 社交 × 5-8 / L3 涌现 × 3-5），输出指标：

- `subjective_divergence`：同一事件不同视角的差异度（量化 Rashomon 效应）
- `causal_trace_depth_avg`：玩家行为引发的因果链平均跳数
- `heuristic_uptake_rate`：启发式经验采纳率
- 8 个工程指标（action_validity_rate / memory_grounding / fallback_rate / latency / cost / ...）

Ablation 实验（关闭 subjective_memory / heuristic_library / director_layer）证明每条核心能力的贡献。Eval 输出 + EventStore dump 作为可公开 dataset。

### 8. AI 辅助美术资产管线

游戏运行时使用本地静态资源，不依赖图片生成 API。Codex 生图能力用于开发期资产生产，覆盖 NPC 立绘、表情差分、地图小人、场景背景、UI 组件、事件 CG。美术风格仍为二次元轻幻想轻异世界田园风（保留为 demo scenario 视觉外壳）。

详见 [`art_direction.md`](./art_direction.md)。

## 产品边界

### 第一阶段聚焦内容

Phase 1（活着的世界）正在收口；Phase 2（骨架建立期）启动后聚焦：

- 1 个偏少女玩家农场主（参与者 + 观察者双模式）
- **4 核心 NPC + 2 stub NPC**（少而深，每个有完整 motivationProfile / capabilityPreferences / heuristicSeeds）
- 3 个地点：农场、广场、酒馆
- **完整骨架**：所有世界实体 schema + 三层工具分层 + 动机系统 + 双轨记忆 + 启发式学习 + 仲裁 + Eval Framework
- **稀薄内容**：5 作物 schema（实现 1 种）/ 25 物品 schema（实现 8-10）/ 30 工具 schema（实现 8-12）
- 1 个事件（星灯祭供应短缺继续作为 demo scenario）
- 玩家可移动、聊天、送礼、参与事件
- NPC 由动机系统驱动，不写死时间表
- 夜晚反思 + 启发式提取

### 暂缓内容

以下内容等 Phase 3 内容期再扩展：

- 5 作物全部实现 / 30 工具全部实现
- 多日循环 / 四季系统 / 复杂经济
- 完整恋爱告白结婚系统
- 多年人口演化
- 战斗系统
- 联机玩法
- 运行时生图 API

## 技术路线共识

### 客户端

主游戏客户端确定使用 Godot：

- 负责地图、玩家控制、NPC 表现、动画、UI 和交互。
- 优先使用 GDScript，降低 Web 导出和跨平台风险。
- 第一阶段以 Windows 桌面 Demo 为主要目标。

### 后端

保留并演进现有 Python Agent 后端：

- 世界状态
- 时间推进
- NPC 调度
- LLM Provider
- 行动解析与执行
- 记忆系统
- 关系系统
- 事件流
- Debug 数据
- 运行日志与调试导出

### Debug / 研究控制台

现有网页前端后续转为：

- Prompt 查看器
- 模型输出查看器
- 工具调用时间线
- 记忆写入检查器
- 关系图谱观察器
- 事件注入工具
- 运行数据与调试记录导出入口

### 视觉风格

首版采用二次元轻幻想轻异世界田园生活模拟方向：

- 画面目标接近明亮、温柔、带少量魔法感的田园番剧。
- `gpt-image-2` 优先用于生成角色半身立绘、表情差分、场景背景、事件 CG、UI 风格参考和作品集配图。
- 像素风暂时只作为 Godot 小人占位、后期手工像素化或专项动画方向，避免首版被精确像素网格、逐帧动画和多角度一致性拖慢。
- 视觉资产先同步覆盖可移动地图小人、静态背景、半身立绘和 3 个基础表情差分，后续再扩展行走动画、服装变体和事件演出。
- 星灯、轻魔法作物、月猫酒馆和记忆卡片是首版主要视觉符号。
- 首版 NPC 以女性角色为多数，优先保证二次元轻幻想角色资产的质量和一致性；后续男性角色比重根据实际生成与导入效果逐步评估。

### 多元关系

Loomstead 的小镇关系按叙事需要自然存在，不默认排斥同性配偶、双母家庭、单亲家庭、收养关系、非血缘家庭或其他多元亲密关系。角色关系的边界、亲密度和冲突通过角色卡、记忆和玩家选择表达。

### 玩家身份

玩家是新搬来的偏少女农场主，**支持参与者 + 观察者双模式**：

- **参与者模式（默认）**：玩家在地图中移动、聊天、送礼、参与事件，与 NPC 走相同的 ToolDefinition 调用路径。
- **观察者模式**：玩家变为半透明幽灵，可点击任意 NPC 查看 motivation / 激活 heuristic / 主观记忆 / 关系图边 / Arbitration trace；可投放物品、注入临时 Director Beat 等"扰动"。观察者模式从 Phase 5 提升为 Phase 2 必须支持的核心能力。
- Debug / 研究控制台保留研究院视角，与观察者模式共用底层 API，渲染层不同。
- 玩家主线叙事不主动暴露"NPC 是 Agent"，技术解释留给控制台和作品集讲解。

## 成功标准

### 体验成功

- 玩家能在 3 分钟内理解：这是一个由 AI agent 生活的小镇，且每个 agent 的反应都有可解释的来源。
- 玩家送花给 A，第二天 B 在酒馆议论这件事（因果链可见）。
- 第一周凯娅频繁踩坑，第二周看到她明显改变行为（启发式成长可见）。
- 同一事件能让玩家在 6 个 NPC 的视角看到 6 个不同版本（主观性可见）。
- Demo 截图与录屏具备技术博客与作品集传播价值。

### 技术成功

- 每次 NPC 决策都有可追踪链路：input sources（needs/director/skill/goals/heuristic/memory）、Arbitration 得分、LLM 输出、解析行动、世界变更、观察者主观记忆。
- 三层工具分层、双轨记忆、启发式学习、仲裁、Eval 五条核心能力全部 schema 完整、可独立测试。
- LLM 调用预算严控（每 NPC social_layer ≤ 8 次/日），全链路 Fallback 可用。
- Eval Framework 可输出量化指标 + ablation 数据，证明每条核心能力的贡献。

### 工程成功

- Phase 2 骨架一次性到位（详见 `agent_loop_architecture.md` §13.3），Phase 3 是纯加内容。
- 新增 NPC / 地点 / 事件 / 工具有明确扩展路径，O(1) 注册。
- 美术资产有统一命名、来源记录和导入流程。
- 公开 dataset（EventStore + 主观视图 dump）可被复现。

### 传播成功

- 一篇技术博客主文：讲清"少而深"是什么、为什么、怎么实现。
- 3-5 个短录屏：每条核心能力一个，每个 30-60 秒。
- 一个交互式 Web Debug Console：让任何人在浏览器里看到 NPC 决策链路。
- 一份运行 dataset：让别人能验证 Rashomon 效应、因果链长度、启发式采纳率。
- GitHub repo（已有）保持代码可读性 + README 简洁。

## 推进原则

1. **少而深，不广而浅**：4 核心 NPC 做深 ≫ 千 NPC 做浅。规模赛道已被 AIvilization 占据，深度赛道仍是空白。
2. **骨架完整，内容稀薄**：Phase 2 必须把所有核心能力的 schema 一次性铺到位（防止 AI 助手无意识收窄项目）；内容可以薄但不能缺类。
3. **每个行为都可解释**：Agent 行动必须能逆向追溯到具体输入源、记忆条目、启发式经验。Debug Trace 不是事后补丁，是设计要求。
4. **可评估优先于可玩**：Eval Framework 是 Phase 2 的硬验收线，不达标不进入 Phase 3。差异化论点没有量化证明就不成立。
5. **表现层与 Agent 层分离**：Godot 负责体验，Python 后端负责 agent 系统。后端权威，Godot 只读取 + 提交合法工具调用。
6. **NPC 与玩家共享接口**：玩家工具调用走同一套 ToolDefinition，玩家行为产生的观察记忆与 NPC 行为一视同仁。
7. **失败也是社会信号**：失败 / 中断 / fallback 都进入观察记忆和 EventStore，不只是日志。
8. **作品集传播优先于内容厚度**：每条核心能力都要有 30-60 秒可分享 demo；做不出可分享时刻的功能延后。
