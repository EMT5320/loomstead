---
status: active
owner_lane: decisions
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: confirmed decisions, unresolved questions, and validation points
---

# 决策记录与剩余问题

本文记录主人已经拍板的边界，以及后续仍需要在实现中验证的问题。当前信息已经足够启动 Phase 2 骨架建立期。

> 2026-05-21 更新：同步研究输出范围，从早期非研究定位改为研究原型 / benchmark / demo / dataset 优先。

## 2026-05-19 项目重定位决策（最高优先级）

### 项目重定位

- 项目从"二次元田园 RPG"重定位为 **"可解释的多 Agent 叙事运行时"**。
- 对外口径："一个可解释的多 Agent 叙事运行时：通过 Director / Event Skill、主观记忆、关系演化和 Debug Trace，让少量深度 NPC 在可玩的 Godot 生活模拟切片中产生可追踪成长。"
- 项目名继续保留 `Agent Valley`，不重命名。
- 差异化主轴：**少而深 + 可解释 + 可评估**。
- 与 Smallville / AI Town / AIvilization / Project Sid 的"广而浅"路线区分。

### 五条核心能力

1. 三层工具分层 + 动机系统（替换软日程）
2. 双轨主观记忆（Rashomon 玩法）
3. 失败驱动的启发式学习（NPC 看得见地成长）
4. 竞争上下文仲裁（全过程可解释）
5. Eval Framework（量化差异化论点）

详见 `docs/project_vision.md` 和 `docs/agent_loop_architecture.md`。

### NPC 数量调整

- 旧规模：6 NPC（5 女 1 男）。
- 新规模：**4 核心 NPC + 2 stub NPC**（核心 NPC 完整接入 motivationProfile / capabilityPreferences / heuristicSeeds，stub 使用默认权重）。
- 4 核心建议：kai / mira / bram / lena；2 stub：tomas / orren。最终名单可在 Phase 2 启动前再调整。

### 决策周期与 LLM 预算

- 决策周期：每个 NPC 每 15-30 游戏分钟评估一次需求（首版 20 分钟）。
- LLM 预算：social_strategic_layer ≤ 8 次/NPC/日；vocational_local_llm ≤ 6 次/NPC/日；reflection 1 次/日；heuristic_extraction ≤ 2 次/日；dialogue 与玩家不计预算。
- 预算耗尽时自动 fallback 到工具的 fallback_rule。

### Capability Registry

- **动态生成**（NPC × 当前位置 × 当前持有物 × 当前需求类型）。
- 每决策周期暴露 3-8 个候选工具，避免 LLM 上下文被全量工具淹没。
- NPC 深度卡 `capabilityPreferences` 字段提供权重加权。

### 直接切换不并行

- Phase 2 启动时 `LifeActionExecutor` 直接退役，**不与 MotivationEngine 并行运行**。
- 原因：AI 助手协作下并行运行会导致两套代码相互污染，新系统证据被旧系统稀释。早做断舍离对项目有利。
- `lifeActionPlan` / `npcSchedules` API 字段保留，语义改为"基于当前需求的下一步候选"。

### 广度骨架优先（不收窄）

- Phase 2 必须一次性铺好 12 项骨架（详见 `agent_loop_architecture.md` §13.3）。
- 内容可以稀薄（Phase 2 只实现 8-12 工具 + 1 作物），但骨架不能稀薄。
- 防止 AI 助手协作下的"无意识收窄项目"。

### 记忆架构（自研抽象层）

- **不接 Graphiti / Mem0 / Letta / RAGFlow**，自研抽象层借鉴 Graphiti 范式（双时间戳 + episodic/semantic/community 三层）。
- 四层架构：Objective Event Log + Subjective Memory Views + Semantic Facts + Relationship Edges。
- BiasFilter 决定主观记忆差异化（关系/情绪/注意力/性格偏置）。
- 首版用模板 + slot fill 实现 BiasFilter，Phase 3+ 升级为局部 LLM。
- 后期如需扩展规模，可把 store 后端换成 Neo4j 或接 Graphiti，retrieve 层不动。
- 详见 `docs/agent_loop_architecture.md` §7.7 决策记录。

### 启发式学习（Heuristic Library）

- **作为 Phase 2 骨架核心**：schema + 规则提取 + LLM 提取（受预算约束）+ 激活机制 + 衰减 + 设计师 heuristicSeeds 注入 + Debug 可视化都必须 Phase 2 到位。
- 提取触发条件：失败/痛苦记忆 emotional_intensity ≥ 0.7。
- 是项目"自我进化"叙事的硬支撑，可视化是作品集传播点。
- 详见 `docs/agent_loop_architecture.md` §8。

### 工具中断 + 失败记忆

- 工具声明 `interruptible` 和 `interrupt_priority_threshold`。
- 中断和失败必须写入观察者主观记忆，带情绪强度。
- 高情绪强度的失败/中断记忆**必须**进入 reflector 的 heuristic 候选池。
- 失败也是社会信号（"我去借东西被拒了"），通过 ResultObserver 写入相关 NPC 主观记忆。

### Eval Framework（第五条核心能力）

- `scripts/run_agent_eval.py` 跑分层 scenario suite（L1 单 NPC × 5-8 / L2 社交 × 5-8 / L3 涌现 × 3-5）。
- 11 个核心指标（详见 `docs/agent_loop_architecture.md` §10.4）。
- 双模式：`--provider rule` 走规则跑（CI 友好、零成本）；`--provider cloud` 真实 LLM 跑（手动触发）。
- Ablation 实验（关闭 subjective_memory / heuristic_library / director_layer）作为差异化论点的量化证明。
- **Eval 是 Phase 2 硬验收线，不达标不进入 Phase 3**。
- 输出 EventStore + 主观视图 dump 作为公开 dataset。

### 观察者模式（Phase 2 核心能力）

- 玩家 + 观察者双模式，从 Phase 5 提升为 Phase 2 必须支持的核心能力。
- 玩家在游戏内随时切换（默认 Tab 键）。
- 观察者模式下玩家可点击任意 NPC 查看 motivation / 激活 heuristic / 主观记忆 / 关系图边 / Arbitration trace。
- 观察者模式可"干预"：投放物品、注入临时 Director Beat 等，编码为 `directorBeat(beatType="player_intervention")`。

### NPC 与玩家共享接口

- 玩家工具调用走同一套 ToolDefinition 注册表。
- 玩家行为打 `actor_type=player` 标记，BiasFilter 看到时可差异化 prompt。
- 玩家行为产生的 EventStore 条目和 NPC 行为完全一致，ResultObserver 一视同仁分发主观记忆。

### Eval 的具体指标

- 核心 8 个：action_validity_rate / memory_reference_rate / memory_grounding_precision / causal_trace_coverage / relationship_consistency / fallback_rate / avg_latency_ms / estimated_cost_usd。
- 新定位差异化指标：causal_trace_depth_avg（玩家行为引发因果链平均跳数） / subjective_divergence（同事件视角差异度） / heuristic_uptake_rate（启发式采纳率）。
- 详见 `docs/agent_loop_architecture.md` §10.4。

## 已确认决策（旧）

### 1. 主客户端

- Godot 正式作为主游戏客户端。
- 第一阶段以 Windows 桌面 Demo 为主。
- Web 展示放到后续，当前网页前端转向 Debug / 研究控制台。

### 2. 游戏视觉风格

- 首版采用二次元轻幻想轻异世界田园生活模拟方向。
- 判断依据：主人更偏好二次元审美，该方向更适合角色立绘、表情差分、事件 CG、关系群像和番剧式小镇剧情展示。
- `gpt-image-2` 优先用于生成角色半身立绘、表情差分、场景背景、事件 CG、UI 风格参考和作品集配图。
- 像素风暂不作为首版主路线，只保留为 Godot 小人占位、后期手工像素化或专项动画方向。
- 首版重点资产包括：1 组风格锁定图、偏少女玩家农场主立绘、玩家与 6 个 NPC 地图小人、6 个 NPC 半身立绘与 3 个基础表情、农场/广场/酒馆背景、星灯祭事件 CG、Visual Novel 风格 UI 组件。
- 详细美术风格、角色设定和资产生成顺序见 [`art_direction.md`](./art_direction.md)。
- 玩家初版默认形象为偏少女的年轻农场主。
- 首版同步推进可移动地图层和 Visual Novel 对话层。
- NPC 游戏内显示名采用二次元轻幻想风，内部 ID 暂时保留。
- 前期保持低魔法生活感。
- 首版开始恋爱铺垫，通过对话、送礼、记忆和关系变化表现好感倾向。

### 3. 首版 NPC 数量与复杂度

- 首版裁剪为 6 个高质量 NPC。
- 首版 NPC 性别比例调整为 5 女 1 男，只保留托玛·榆庭作为男性首发 NPC。
- 后续扩展默认沿用女性占多数的比例，若男性角色资产一致性和质量稳定，再适当增加男性角色比重。
- 小镇允许同性配偶、双母家庭、单亲、收养和其他多元家庭关系，这些关系按叙事需要正常存在。
- 原有 10 个 NPC 设定保留为后续扩展池。
- 6 个首发 NPC 必须具备完整人设、日程、关系、喜好、记忆和至少一个可触发关系张力。

### 4. 玩家身份

- 玩家是新搬来的偏少女农场主，作为普通居民进入小镇。
- Debug / 研究控制台保留研究院视角，用于观察、干预和解释 Agent 行为。
- 玩家主游戏剧情不主动暴露 NPC 是 Agent。

### 5. LLM Provider 策略

- 直接开始接入 LLM 做测试，减少规则系统调试时间。
- DeepSeek V4 Flash 作为首版优先测试模型，利用低成本优势覆盖对话、事件反应和夜间反思。
- RuleBasedProvider 保留为离线兜底、测试夹具和异常 fallback。
- 首版需要尽早记录 token、延迟、失败率和每次 Demo 的大致调用成本。

### 6. 研究输出范围

- 本项目当前定位为研究原型、benchmark environment、demo / dataset / evaluation work，第一目标不是直接承诺 full paper。
- 后续文档不再使用“论文支撑”作为泛化阶段目标；研究 claims 必须由 Process Fidelity Eval、baseline 和 ablation 数据支撑。
- 可导出数据服务于调试、回放、作品集讲解、benchmark 复现、技术报告和后续产品化分析。

### 7. 仓库演进

- 当前仓库原地演进。
- 对外项目名使用 `Agent Valley`。
- 保留现有 Python Agent Runtime。
- 新增 `clients/godot/`。
- 旧 `frontend/` 后续迁移为 `web-admin/`，作为 Debug / 研究控制台。

### 8. 开发约束

- 项目按较完整的游戏目标推进。
- 首版垂直切片是正式游戏骨架的第一章，工程结构需要支持长期扩展。
- 重要节点需要检查 NPC、地点、事件、玩家动作、资产、存档和 Debug 链路的扩展性。
- 新增功能优先明确数据契约、事件记录和 Debug 展示方式。

### 9. 多层 Agent 系统定调

- 项目核心定调为可被游玩的涌现社会，固定内容负责规则、舞台、角色底层和压力源，LLM Agent 负责主观判断、表达、记忆和关系演化。
- 导演层定义为 Director System，采用摘要、路由、规划、校验和队列组合，避免单个每 tick 全知控制器。
- Director System 由 WorldDigest、TensionDetector、SkillRouter、DirectorPlanner、Validator、QueueManager 和 ModelRouter 等部件组成。
- 导演层通过异步 Director Beat 影响后续节奏，每个 Beat 需要世界版本、生效窗口、取消条件、目标、约束和目标 Agent。
- 事件按 Skill 渐进式加载：常驻阶段只加载触发条件，满足条件后再加载完整事件 brief、工具、约束、后果类型和资产提示。
- NPC Agent 在角色卡、记忆、关系和导演 brief 内自主行动，导演层不直接强制 NPC 的情绪、最终态度或结局。
- 玩家仍由真人控制；Player State Agent 只总结玩家风格和历史选择，不替玩家操作。

## 仍需实现中验证的问题

### Godot Spike 验证

- 2026-05-16 主人已完成上一版真实 Godot 窗口人工验收，基础通信、地点切换、NPC 选择、对话和事件展示基本可用。
- 本轮代码已补 WASD 独立移动、地图层直接点击当前场景空地落点、落点标记、当前场景角色/事件过滤、动态舞台移动范围、UI 点击穿透、单个最近目标高亮、玩家 / NPC 分离站位槽、玩家出生点上移、收紧交互半径、点击边界修正和靠近滞回；这些体验仍需主人窗口复验。
- 下一轮验证重点：服务端锚点契约、靠近交互、行动反馈和日程可视化是否能把体验推进到可玩的生活模拟。
- Godot 与后端状态同步在新增坐标、交互半径、行动冷却和日程状态后是否仍顺手。

### LLM 接入验证

- DeepSeek V4 Flash 的 OpenAI-compatible 调用参数、模型名和上下文长度以当前本机 profile 和真实 smoke 记录为准。
- 首版 Prompt 是否能稳定输出可解析行动。
- 对话质量、延迟和成本是否适合现场演示。
- 失败时是否能自动 fallback 到规则或缓存回复。
- 前序已有一次真实 smoke 记录；切换模型、key、profile 或 Prompt 后需要刷新延迟、成本、失败率和 fallback 证据。

### Director / Agent 系统验证

- Director Beat 是否能在异步返回后通过 `worldVersion`、`validFromTick`、`expiresAtTick` 和 `cancelIf` 稳定落地。
- 强模型低频规划、快模型 NPC 响应、规则校验之间的延迟是否适合真实游玩。
- WorldDigest、事件摘要、关系记忆和 RAG 检索能否让导演层避免读取全量日志。
- Validator 是否能拦住越权工具调用、过期 Beat 和不符合世界状态的规划。
- Event Skill 数据结构是否能复用到后续节日、委托、危机和恋爱铺垫事件。
- `gossipEvidence` 目前进入对话上下文并提供传播草案、debug summary 和 validator，Runtime 会写入 `gossip.propagation_validated` 校验事件；后续是否写入 NPC 记忆或关系网络扩散。

### 视觉资产验证

- 二次元轻幻想轻异世界风是否能在角色、场景、UI 和事件 CG 之间保持统一。
- 角色半身立绘、头像和表情差分是否能稳定保持同一角色设定。
- 地图小人小尺寸角色资产是否足够支撑首版移动、靠近和交互。
- 首张星灯祭供应短缺事件 CG 纳入首版基础交付，第二张交付选择 CG 作为增强项。
- UI 风格是否优先采用 Visual Novel 对话框、名牌、选择按钮和记忆卡片组合。

### 已确认角色与视觉细节

- 玩家角色默认形象：偏少女年轻农场主。
- NPC 命名体系：游戏内显示名改为二次元轻幻想风，内部 ID 保持 `mira`、`tomas`、`orren`、`lena`、`kai`、`bram`，内部 ID 不再强绑定旧显示名或旧性别。
- 魔法浓度：前期低魔法生活感，星灯、符文和作物发光只做氛围点缀。
- 首版主画面：可移动地图层与 Visual Novel 对话层同步推进。
- 恋爱要素：首版开始铺垫好感和暧昧倾向，完整恋爱、告白、结婚系统后续扩展。

### 6 个 NPC 最终名单

建议从现有 10 个 NPC 中首发：

- 米娅·星麦（`mira`）：杂货铺店主，照顾型，家庭与经济压力入口。
- 托玛·榆庭（`tomas`）：木匠，沉默可靠，家庭线与小镇修缮入口。
- 奥蕾娅·星历（`orren`）：退休教师，小镇历史和健康风险入口。
- 莉娜·白桦（`lena`）：医生，公共健康与理性冲突入口。
- 凯娅·月弦（`kai`）：酒馆乐手，社交、浪漫和债务冲突入口。
- 布兰娜·麦垄（`bram`）：农场主，农场主题和欠账冲突入口。

暂缓到扩展池：

- 妮娜：婴儿，当前交互性弱，适合后续家庭成长系统。
- 萨娜：镇长，适合后续扩大治理事件。
- 里奥：学生，适合后续青少年支线。
- 艾薇：外来研究员，容易和玩家/研究院视角重叠，适合 Debug 叙事或后续剧情。

## 下一轮讨论入口

当前信息已经足够进入正式开发。后续讨论可以围绕实现中出现的具体分歧展开：

1. 复验 Godot 空地点击落点、单目标高亮、当前场景过滤和移动稳定性后，确认地图表现方案和同步频率。
2. 规则版 Director v0 跑通后确认 Director Beat schema、过期策略和队列消费方式。
3. 星灯祭事件继续迁移为 Event Skill 数据后确认事件系统是否足以扩展到后续节日、委托和危机事件。
4. LLM 首轮实测后确认模型名、成本、延迟和 fallback 策略。
5. 第一批风格锁定资产生成后确认二次元轻幻想轻异世界是否作为长期主风格。
6. 偏少女玩家主角确认后，生成正式玩家半身立绘、表情差分和地图小人。
## 2026-05-15 收口后仍需实现中验证

- Godot 真实窗口里，背景切换、NPC 选择、聊天提交、错误提示和同步频率是否适合首版演示。
- Godot 事件 UI 如何展示 `inspect`、`attend_event`、事件选择结果和关系/记忆变化。
- 星灯祭 Event Skill 的选项、后果、`styleSignal`、记忆模板、fallback 台词和 asset hints 已继续迁入数据层；剩余结算模板是否能继续减少 Runtime 硬编码。
- 单个 Event Skill 的结构是否足以复用到后续节日、委托、危机和恋爱铺垫事件。
- `gossip.propagation_validated` 后续是否写入 NPC 记忆或关系网络扩散。
- 切换模型、key、profile 或 Prompt 后，dialogue、event_reaction、night_reflection 三条 LLM profile 的延迟、成本、失败率和 fallback 表现。
- 表情差分、地图小人、UI 组件入库后，角色一致性和 Godot registry 维护方式是否稳定。

## 2026-05-16 Godot 窗口验收后仍需实现中验证

- 主人已确认真实窗口基础体验基本可用；后续重点转向玩法深度、内容节奏和长期扩展性。
- 当前 Godot 已有 WASD 独立移动、地图层空地点击落点、落点标记、当前场景过滤、动态舞台移动范围、UI 点击穿透、单目标靠近高亮、玩家 / NPC 分离站位槽、玩家出生点上移、收紧交互半径、点击边界修正和靠近滞回；需要主人复验三场景手感，并继续验证服务端锚点契约、行动反馈和日程可视化的最小结构。
- VN 结果面板同时展示 NPC 台词、关系变化、即时记忆和夜间反思时，是否需要拆成分页、卡片或可滚动详情。
- 星灯祭事件 CG 与角色立绘共用当前 `portrait_rect` 是否适合演示，后续是否需要独立 CG 层。
- `happy` / `troubled` 表情差分补齐后，Godot 表情选择策略应由后端返回字段驱动，还是由客户端根据事件结果做轻量映射。
- 地图层继续深入时，当前 `move` / `inspect` / `attend_event` API 是否先补 `anchorId` / `interactableId` 锚点校验，还是一步到位补坐标、交互半径或场景状态字段。


## 2026-05-19 Phase 2 实施期待验证（工程细节，不阻塞决策）

这些问题不影响 Phase 2 启动，可在实施期再决定，先记录避免遗忘：

### 工具失败 / 冲突处理

- 默认采用乐观执行 + 失败事件，不做悲观锁。
- 失败事件如何分发为观察者主观记忆的具体 BiasFilter 模板（首版 5-8 个模板覆盖大部分情况）。
- 工具冲突频率上限：如果某 NPC 一周期内 ≥ 3 次工具失败，是否触发"挫败"情绪状态。

### 玩家观察记忆的细化

- 玩家行为对不在场 NPC 的"间接知晓"传播路径：通过其他 NPC 转述 vs 直接事实写入。
- 玩家观察者模式干预（投放物品、修改情绪）写入哪些 NPC 的主观记忆，以及如何标记"超自然事件"。

### 工具时间与动画对齐

- 客户端动画时长是否需要严格匹配后端 `actionDuration`，或允许客户端做轻微缓动加速。
- `npc.action_tick` 事件是否算作其他 NPC 的"观察记忆"（建议：低重要性默认不写入，只有 ≥ 0.5 importance 才写）。

### 一致性约束的工程前置

- B1 角色姿态批次开工前，每个 NPC 必须先准备 reference image stack（neutral 立绘 + 至少 2 张多角度参考）。
- `npc_*_reference.txt` prompt 模板扩展为多姿态版本（不仅描述外观，要包括姿态结构）。
- 一致性验收标准（脸型 / 发色 hex / 服装色块 / 瞳色 / 特征标记）必须先写下来。
- 不做这一步，资产返工率预计 30-50%。

### 信念模型（belief_about）

- Phase 2 schema 占位（NPC 主观视图新增 `belief_about` 条目类型）。
- Phase 4 实际接入决策上下文（"我以为 X 想做 Y" → LLM 决策时纳入）。
- Phase 5 加 counterfactual 反思（"我以为 vs 实际"差距驱动 belief update）。

### NPC 决策周期粒度

- 默认 20 游戏分钟，离屏拉长到 60 分钟，玩家在场缩短到 10 分钟。
- 是否需要"事件触发立即评估"的优先队列（避免事件在周期间隙发生时延迟响应）。
- 离屏 NPC 是否需要批量 tick 优化（一次推进多个 NPC 多个周期）。

### Heuristic 衰减与冲突

- 多条互相矛盾的 heuristic 由 confidence 加权裁决，但具体公式（线性 vs softmax）待实现期决定。
- heuristic 长期未激活的衰减曲线（建议指数衰减，半衰期 = duration_days）。
- 设计师注入的 seed heuristic 是否允许被失败经验完全覆盖（建议：可以，confidence 可降到 0）。

### 与现有 gossipHooks / monologueSeeds 的迁移

- gossipHooks 和 monologueSeeds 在 Phase 2 是否继续保留，还是合并到 SubjectiveMemoryStore 的某种特殊条目类型。
- 已有的 `gossip.propagation_validated` 校验事件如何与新主观记忆路径并存或合并（建议：Phase 2 保留校验事件，Phase 4 改写为真正传播）。

### 资产路线的范围调整

- 旧 230-250 张资产计划在新定位下偏多。
- 实际 Phase 2-3 需要：4 核心 NPC × 多姿态（保守 5 姿态）× 2 方向 = 40 张 + 2 stub × 2 姿态 = 4 张 + 表情差分 + 物件状态 ≈ 100-120 张。
- 砍掉的部分：日夜雨变体（用 shader）、未实现作物的生长阶段、第二批节日 CG 等。
