---
status: archive
owner_lane: research-quality
created: 2026-06-05
scope: 从 Motivational Delegation 到 Auditable Agents 的转型可行性分析，含历史问题还原、当前实现评估与后续路径建议
---

# 研究转型分析：Motivational Delegation → Auditable Agents

> 归档层文档，仅供溯源。2026-06-05 由幽浮喵完成分析，落盘供主人后续参考，不纳入当前上下文管理。

## 1. 历史根本问题还原

### 1.1 原始研究定位

Loomstead 原始研究 thesis：**Motivational Delegation + Process Fidelity Eval**

核心主张：*Director 不直接命令 NPC，而是通过动机偏置、事件 Skill、资源/机会调度、信息暴露和约束注入间接驱动 NPC 朝过程约束目标演化，并用 Process Fidelity 验证"过程是否可信"。*

设计了 5 个 baseline（Direct State Setter / Static Todo Planner / Hard Delegation / No Subjective Memory / Full），指标覆盖 goal_success_rate、shortcut_violation_rate、forced_action_rate 等。

### 1.2 三个致命问题

2026-06-02 数据核查发现：

**问题 1：Hard Delegation 是 metric stub，不是真实 runtime**

`backend/app/eval/runner.py:1122` — `_run_hard_delegation_process_scenario` 从不调用 `AgentRuntime.tick()`。它直接硬编码 `subjective_memory_refs=False`、`causal_trace=False`、`shortcut_events=1` 等，是预设的 metric-construct 对比，非真实行为差异。

**问题 2：Memory / Relationship ablation 不产生行为分化**

ablation 输入进入了决策路径，但 promoted scenarios 中 `goalToolEvents` 完全一致——Full 和 No Memory 的 NPC 选了相同的工具、做了相同的事。差异只存在于 metric 层的 sourceEventIds 完整性，行为层零分化。

**问题 3：Process Fidelity 指标只检测证据完整性，不等价于"过程可信"**

规则 provider 下 counterfactual_tool_selection_change_rate 在 coding domain 有 0.762，但 town domain 仅 0.333。这些变化是 deterministic rule 指令下的分数变化，从未验证真实 LLM agent 是否会因记忆消失而选不同行动。

### 1.3 收缩抉择（2026-06-02）

- Human Rating Pilot 关闭：baselines 不产生行为分化，人类盲评无法产生系统能力信号
- C2/C3/C4 降级为 metric/explainability level `promoted with caveat`
- Loomstead 降为二线 portfolio，AlgoCoach-Flywheel 成为主力

## 2. 转型方案：Auditable Agents

### 2.1 Framing 转变

- 旧：*"Motivational Delegation 产生更可信的行为"*
- 新：*"Trace-grounded provenance + counterfactual audit harness：每个高风险 agent 动作可追溯到授权证据，且移除证据后动作或判决发生变化"*

### 2.2 当前实现

| 组件 | 文件 | 状态 |
|---|---|---|
| 3 个高风险场景 | `backend/app/eval/audit.py` | coding patch / ops destructive / data export |
| 5 个 baseline | Full / No Policy Evidence / Evidence Link Removal / Shortcut Agent / Direct Executor | deterministic |
| 4 个审计指标 | provenance coverage / bypass rate / counterfactual sensitivity / report completeness | 15 份报告字段完整 |
| Go/No-Go gate | `audit.go_no_go.v1` | ✅ PASS |
| Reviewer packet | `scripts/build_audit_reviewer_packet.py` | README + summary + 3 case studies |

当前机器结果：
- Full provenance = 1.0, bypass = 0.0
- Shortcut/Direct bypass = 1.0（清晰 bypass 信号）
- 3 个场景 counterfactual sensitive（移除证据 → 动作或判决变化）
- 15 份 audit report 字段完整
- `manual_reviewer_readability` 人工 gate 待主人判断

### 2.3 与旧方案的对比

| 维度 | 旧（Motivational Delegation） | 新（Auditable Agents） |
|---|---|---|
| 核心问题 | "过程是否可信？" | "动作授权证据是否可追踪？" |
| 可验证性 | 需要人类判断 believability | 机器可自检 provenance coverage |
| baseline 分化 | 行为层零分化 | Full=bypass 0.0, Shortcut/Direct=bypass 1.0 |
| LLM 依赖 | 需要真实 LLM 跑出行为差异 | 当前 deterministic 就能证明概念 |
| 对标领域 | Smallville / Generative Agents | AI Safety / Agent Governance / Audit |

## 3. 可行性评估

### 3.1 能立住的理由

1. **解决的问题比旧方案更具体、更可量化**：从主观 believability 转向客观 provenance coverage
2. **与现有基础设施完美匹配**：trace schema（sourceEventIds / traceRefs）、Counterfactual Replay、Eval pipeline 天然擅长"证据链可追溯性"
3. **已有清晰 evidence differentiation**：5 个 baseline 在 provenance / bypass / counterfactual 上有明确数值分化
4. **有学术社区对接口**：Agent provenance / Policy compliance / Auditable AI 是活跃方向

### 3.2 站不住的风险

1. **当前 3 个场景是手工构造的 toy fixture**：required evidence 硬编码，bypass 预设计
2. **没有 real LLM 参与**：deterministic rule 下的 provenance 是 trivial 的
3. **贡献边界需极谨慎**：只能 claim "toy fixture 中的结构化 provenance"，不能 claim 企业级安全
4. **核心竞争问题**："结构化 trace + 反事实审计"的新颖性需要实证支撑

### 3.3 总体判断

**可以立住，但有条件。**

核心洞察：旧方案的根本问题是 framing 太大而数据太弱——优秀的 trace/eval 基础设施在试图证明它证明不了的东西（believability）。新方案 framing 小而精，而基础设施完美匹配。同一套基础设施，换了正确的 framing。

## 4. 三阶段实施建议

### Phase A：固化最小证据墙（1-2 天，低风险）

1. 主人审查 reviewer packet（`manual_reviewer_readability` gate）
2. 通过 → promote audit artifact
3. 不通过 → 改进 case study 叙事，重跑 packet
4. 写 `docs/research_framing_auditable_agents.md`（草案自管理层，审核后入圣经层）
5. `paper/claim_evidence_matrix.md` 新增 C17 claim

### Phase B：扩展 scenario + 接入 LLM（3-5 天，中等风险）

1. 扩展场景到 5-8 个（config change review、API key rotation compliance、model switch benchmark、deployment staged rollout 等）
2. Counterfactual replay 升级：单条 → 每条独立 + multi-evidence 移除
3. 接入真实 LLM agent：用 CloudApiProvider 跑 audit scenario，对比 rule vs LLM provenance 一致性

### Phase C：研究化收口（取决于 Phase B）

1. 写完整 research framing（RQ1-3、baseline matrix、metric families、claim boundary）
2. 文献对齐：agent provenance / AI audit / policy compliance
3. 目标 venue：AAMAS workshop / EMAS / EXTRAAMAS / arXiv 技术报告

### Go/No-Go 判断点

| Gate | 条件 | 继续条件 |
|---|---|---|
| G1 | reviewer packet 可读性通过 | 进入 Phase B |
| G2 | ≥5 scenario + LLM 接入 provenance 稳定 | 进入 Phase C |
| G3 | Phase C framing 完成 → 主人判断 vis 价值 | 决定是否继续投入 |

## 5. 当前实现合理性评估

### 做得好的

- 完全复用现有 eval 基础设施（manifest、export、promote），0 新造轮子
- baseline 差异逻辑集中在三个纯函数，容易审计
- reviewer packet 分层合理（README → summary → case studies → appendix）
- claim boundary 诚实（机器 gate 只检查字段完整）

### 需注意的

- `_available_evidence` 在 Evidence Link Removal baseline 下语义需在 case study 中清楚解释
- Counterfactual replay 只移除第一条 required evidence（硬编码 `required_evidence[0]`）
- scoreComponents 硬编码，非真实 scoring 函数

---

*分析人：幽浮喵 (2026-06-05)*
*本文件为归档层，不作当前上下文管理，仅供主人后续溯源参考。*
