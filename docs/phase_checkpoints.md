---
status: active
owner_lane: planning
last_verified: 2026-05-29
startup_load: on-demand
source_of_truth: true
scope: 阶段推进 checkpoint 板与 exit criteria
---

# Loomstead Phase Checkpoints

本文配套 `docs/context_governance.md` §4 使用，承载阶段推进的 yes/no 判据。每个 checkpoint 由主人解锁；AI 助手在达成 checkpoint 时必须按治理协议 §5 模板输出 review，等主人选定方向后才能进入下一项。

## 当前位置

- 已通过：`P1.exit`（Phase 1 活着的世界，2026-05-21 主人确认）
- 进行中：`P2.skeleton`（Phase 2 骨架建立，已超额完成 rule-level scaffold，等待方向决策）
- 未解锁：`P2.exit`、`P3.entry`、`P4.entry`

## P2.skeleton —— Phase 2 骨架完整性

> 状态：rule-level scaffold 已完成；待主人决定下一阶段方向

### Exit criteria

- ✅ ToolDefinition / MotivationEngine / NeedAccumulator / CapabilityRegistry / ArbitrationLayer 接入并落地
- ✅ SubjectiveMemoryStore / RelationshipEdgeStore / HeuristicLibrary / ResultObserver 落地
- ✅ Phase 2 trace 覆盖 decision / tool / interruption / memory observation
- ✅ World entities schema (FarmPlot / Item / Inventory / Shop / Building / Time / Weather)
- ✅ Eval Framework rule process suite + 24h/72h stability + domain adapter + counterfactual replay + robustness strict gate
- ✅ ResearchFraming / DomainAdapter / ProcessFidelityEval 三项研究护栏文档落地
- ✅ 4 核心 NPC 接入 motivation profile / capability preferences / heuristic seeds
- ✅ Godot ObserverPanel 三 Tab + trace 导航代码
- ✅ 真实 LLM 跑通的 Process Fidelity / Hard Delegation evidence：cloud provider usage 已覆盖 4 个 GoalSpec × 5 seed × 5 baseline（100 calls，0 fallback），并 promote 到 `.run/eval-promoted/run_2026-05-29T13-57-50Z`；claim 升级和 promotion manual note 仍待主人确认
- ⚠️ 人工 reviewer 抽样填表（packet 已生成，待人工执行）
- ⚠️ Godot 真实窗口最新 Trace 补修复验

### 主人下一阶段候选（待选）

A. **求职展示线**（1-2 周）
   - 录 60 秒 NPC 自主生活 demo
   - 写技术博客主文（claim matrix + figure3 walkthrough 改写 70%）
   - README portfolio 化
   - 触发 `P_demo.exit`

B. **真实 LLM 证据线**（推荐，含主人协助）
   - cloud 4 GoalSpec × 5 seed × 5 baseline 已跑通并 promote；剩主人确认 C2/C3/C4 claim level 与 promotion manual note
   - 若主人确认，可把 C2/C3/C4 升到 final empirical 或 promoted with caveat；若暂不升级，则维持 partial empirical + cloud-backed caveat
   - 触发 `P2.exit` 的研究向硬验收

C. **Phase 4 玩家成为变量线**（4-6 天）
   - 接通 gossip 真扩散到 NPC 记忆
   - 1 个跨日 emergence scenario
   - 解锁愿景 §"30 秒可分享时刻"
   - 触发 `P4.entry`

D. **内容深度线**（Phase 3 启动）
   - 4 核心 NPC 完整接入 motivation / heuristic 数据
   - 5 作物 / 25 物品 / 30 工具落地
   - L2/L3 scenario suite 完整
   - 触发 `P3.entry`

E. **Eval Framework 加固延续**（不推荐）
   - 继续在 manifest / archive / promote / drift / strict gate 上加层
   - 触发额外 over-engineering 风险，治理协议 §3.2 已禁止此类无 trigger 加固

### 浮浮酱推荐

**确认 claim 口径后转 A**：B 线的 cloud evidence artifact 已收口到 promoted run；现在最有推进价值的是由主人确认 C2/C3/C4 是否升级，然后切到 A 把已有强支撑（trace、Process Fidelity 数据、Hard Delegation vs Full 对比、cloud provider usage）剪成 30-60 秒短 demo。

## P_demo.exit —— 求职展示线收口

> 状态：未解锁

### Exit criteria（候选，待主人正式选定 A 后定稿）

- 1 段 ≥ 60 秒 demo 录屏：NPC 自主生活 / Trace 因果链 / Rashomon 不同记忆任选其一
- 1 篇技术博客主文，覆盖：少而深 framing、Motivational Delegation、Process Fidelity 数据
- README 顶部新增"快速看 demo / 快速看研究"两条 30 秒入口
- 至少 1 段对外可分享的 GIF / 截图集
- claim_evidence_matrix 全表的"Figure / Table target"列至少有 70% 已渲染

## P2.exit —— Phase 2 研究向硬验收

> 状态：未解锁

### Exit criteria（候选，待主人正式选定 B 后定稿）

- 至少 4 个 GoalSpec 跑通 5 seed × 5 baseline 真实 provider，promoted manifest `llmEvidence` 已写入
- claim_evidence_matrix C2 / C3 / C4 升级为 final empirical 或 promoted with caveat
- ablation_comparison 包含 Full vs Hard Delegation vs No Subjective Memory vs No Relationship Edge 四对比
- 真实 provider 跑通后 24h 内不重复 export 同 suite（避免治理 §3.2 违规）

## P3.entry / P4.entry —— 后续阶段入口

未触发前不细化，避免规划幻觉。当 P2.exit 达成后再展开。

## 历史 checkpoint

- `P1.exit`：2026-05-21 主人确认 Phase 1 收口；`world_main.tscn` 进入完成基线
