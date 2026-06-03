---
status: active
owner_lane: planning
last_verified: 2026-06-03
startup_load: on-demand
source_of_truth: true
scope: 阶段推进 checkpoint 板与 exit criteria
---

# Loomstead Phase Checkpoints

本文配套 `docs/context_governance.md` §4 使用，承载阶段推进的 yes/no 判据。每个 checkpoint 由主人解锁；AI 助手在达成 checkpoint 时必须按治理协议 §5 模板输出 review，等主人选定方向后才能进入下一项。

## 当前位置

- 已通过：`P1.exit`（Phase 1 活着的世界，2026-05-21 主人确认）
- 已完成方向确认：`P2.skeleton`（Phase 2 骨架建立，rule-level scaffold 与 cloud-backed Process Fidelity 证据已收口）
- 已通过：`P2.exit`（Phase 2 研究向硬验收，2026-05-29 主人确认 C2/C3/C4 `promoted with caveat`）
- 进行中：`P_demo.exit`（已收缩为二线兜底工程展示 / demo 冻结准备）
- 已排队：`P_audit_spike.entry`（P_demo 收尾后，做一次短周期 Auditable Agents 挽救实验）
- 未解锁：`P3.entry`、`P4.entry`

## P2.skeleton —— Phase 2 骨架完整性

> 状态：rule-level scaffold 与 B 线 cloud evidence 已收口；A 求职展示线已收缩为二线 portfolio 工程展示

### Exit criteria

- ✅ ToolDefinition / MotivationEngine / NeedAccumulator / CapabilityRegistry / ArbitrationLayer 接入并落地
- ✅ SubjectiveMemoryStore / RelationshipEdgeStore / HeuristicLibrary / ResultObserver 落地
- ✅ Phase 2 trace 覆盖 decision / tool / interruption / memory observation
- ✅ World entities schema (FarmPlot / Item / Inventory / Shop / Building / Time / Weather)
- ✅ Eval Framework rule process suite + 24h/72h stability + domain adapter + counterfactual replay + robustness strict gate
- ✅ ResearchFraming / DomainAdapter / ProcessFidelityEval 三项研究护栏文档落地
- ✅ 4 核心 NPC 接入 motivation profile / capability preferences / heuristic seeds
- ✅ Godot ObserverPanel 三 Tab + trace 导航代码
- ✅ 真实 LLM 跑通的 Process Fidelity / Hard Delegation evidence：cloud provider usage 已覆盖 4 个 GoalSpec × 5 seed × 5 baseline（100 calls，0 fallback），并 promote 到 `.run/eval-promoted/run_2026-05-29T13-57-50Z`；主人已确认 C2/C3/C4 使用 `promoted with caveat`，promotion note 已写入；机器记录仍保留 `needs_manual_review` 的 git.dirty / drift caveat
- ✅ Human Rating pilot 已关闭：2026-06-02 核查确认当前 baselines 不产生可评行为分化，现有证据仅支撑 metric / explainability 级 claim
- ⚠️ Godot 真实窗口最新 Trace 补修复验

### 主人下一阶段候选（A 已选定）

A. **求职展示线**（已收缩为二线 portfolio 工程展示）
   - 保留 README / blog / capability map 作为入口
   - 只在无需新 UI 开发时录制低成本 explainability demo
   - 不再追 human-believability、人评、cloud 重跑或展示层大改

B. **真实 LLM 证据线**（本轮已收口）
   - cloud 4 GoalSpec × 5 seed × 5 baseline 已跑通并 promote；C2/C3/C4 已由主人确认使用 `promoted with caveat`
   - 证据口径限定为 metric / explainability 级，不再支撑 human-believability claim
   - 支撑 portfolio 中的 agent observability / eval infra 展示

C. **Phase 4 玩家成为变量线**（历史候选，不再启动）
   - 原计划：接通 gossip 真扩散到 NPC 记忆、做 1 个跨日 emergence scenario

D. **内容深度线**（历史候选，不再启动）
   - 原计划：4 核心 NPC 完整接入、扩作物 / 物品 / 工具、补 L2/L3 scenario suite

E. **Eval Framework 加固延续**（不推荐）
   - 继续在 manifest / archive / promote / drift / strict gate 上加层
   - 触发额外 over-engineering 风险，治理协议 §3.2 已禁止此类无 trigger 加固

### 浮浮酱推荐

**A 已收缩为 portfolio 工程展示**：当前最有价值的是冻结并复用已有资产（runtime、trace、eval、Godot observer、cloud artifact）证明 agent 系统工程能力。若现有界面无需新开发即可讲清楚，可录低成本 explainability 素材；否则不继续包装展示层，主力转向 `AlgoCoach-Flywheel`。

## P_demo.exit —— 求职展示线收口

> 状态：收缩中。2026-06-03 主人确认顺序：先收尾为兜底工程展示项目，再启动一次短周期 Auditable Agents 挽救实验；`AlgoCoach-Flywheel` 仍是求职 + 论文主力。

### Exit criteria

- ⚠️ 可选 1 段 ≤ 60 秒低成本 explainability demo：只使用现有 Godot / Observer / trace 资产；若需要新 UI 开发才能讲清楚，则不执行
- ✅ 1 篇技术博客主文，已改为工程展示 / explainability / evidence-completeness 口径（`paper/blog_main.md`）
- ✅ README 顶部新增"快速看 demo / 快速看研究"两条 30 秒入口（已收敛为 Watch / Research 两条入口）
- ✅ Human Rating Pilot Gate 已关闭：`docs/human_rating_pilot_gate.md` 记录 2026-06-02 前提不成立结论，旧 packet 只作方法论记录
- ⚠️ 可选对外 GIF / 截图集：仅在现有界面足够清楚时人工捕获
- ✅ claim_evidence_matrix 全表的"Figure / Table target"列至少有 70% 已渲染（Figure 4 SVG 已补齐；`showcase:check` 回填 coverage=0.70）

## P2.exit —— Phase 2 研究向硬验收

> 状态：已通过（promoted-with-caveat 口径现限定为 metric / explainability 级；human-believability 已关闭为当前数据前提不成立）

### Exit criteria

- 至少 4 个 GoalSpec 跑通 5 seed × 5 baseline 真实 provider，promoted manifest `llmEvidence` 已写入
- claim_evidence_matrix C2 / C3 / C4 保留为 metric / explainability 级 promoted with caveat
- ablation_comparison 包含 Full vs Hard Delegation vs No Subjective Memory vs No Relationship Edge 四对比
- 真实 provider 跑通后 24h 内不重复 export 同 suite（避免治理 §3.2 违规）

## P_audit_spike.entry —— Auditable Agents 短挽救实验

> 状态：已排队，尚未启动。该实验只在 `P_demo.exit` 兜底收尾后执行，周期应控制在 3-5 天。

### Scope

- 推荐 framing：`Trace-grounded Auditable Agent Runtime` 或 `Agent Action Provenance & Counterfactual Audit Harness`。
- 复用现有 trace / eval / coding adapter 资产，但重新定义审计语义；避免把旧 Process Fidelity 指标直接改名后升级 claim。
- 至少新增 2 个高风险工具场景，例如 coding patch 前必须读取 policy / tests、ops 删除或移动文件前必须有 ticket / approval、data export 前必须经过 redaction policy。
- Baselines 至少包含 Full Runtime、No Policy Evidence、Evidence Link Removal、Shortcut Agent / Direct Executor。

### Exit criteria

- ⚠️ `action_provenance_coverage`：高风险动作必须携带可追踪 `sourceEventIds` / `traceRefs`。
- ⚠️ `policy_bypass_rate`：shortcut baseline 应明显高于 Full。
- ⚠️ `counterfactual_action_sensitivity`：至少 2 个场景移除关键 policy / context evidence 后 selected action 或 violation verdict 发生变化。
- ⚠️ `audit_report_completeness`：每个动作输出 selected tool、risk level、policy evidence、score components、source ids、counterfactual replay result、verdict。
- ⚠️ 产出一份 reviewer 可读审计报告；若报告无法定位“哪个证据影响了哪个动作”，实验判定失败。

### Claim boundary

- 可说：toy narrative / coding fixture 中的结构化 provenance 与反事实审计 harness。
- 避免：完全严密因果证明、企业级生产可用、跨域有效性已成立、AI Safety 核心贡献已完成。
- 如果上述 exit criteria 无法满足，则停止挽救路线，仅保留 portfolio 工程资产。

## P3.entry / P4.entry —— 后续阶段入口

未触发前不细化，避免规划幻觉。当 P2.exit 达成后再展开。

## 历史 checkpoint

- `P1.exit`：2026-05-21 主人确认 Phase 1 收口；`world_main.tscn` 进入完成基线
