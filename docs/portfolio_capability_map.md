---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-06-03
startup_load: on-demand
source_of_truth: true
scope: Loomstead 求职展示 capability map（展示的工程能力 / 对应岗位 / 面试讲法 / 诚实边界 / 与 AlgoCoach 分工）
---

# Loomstead Portfolio Capability Map

> 自管理层文档，软上限 250 行。用途：把 Loomstead 现有资产串联成一份求职展示入口——它展示了哪些工程能力、对应什么岗位、面试怎么讲、诚实边界在哪。2026-06-02 战略收缩后，Loomstead 定位为「可解释多 agent 系统 + 可观测性 / eval 工程」的 portfolio piece，不再追 believability 论文化。

## 1. 一句话定位

- 中文：一个**可解释的多 agent 叙事运行时**——Director 通过 Motivational Delegation 间接驱动少量深度 NPC，每个结果都能通过结构化 trace 审计「为什么发生」，并配一套 Process Fidelity eval 飞轮。
- EN（简历/面试用）：*An explainable multi-agent narrative runtime where a Director steers deep NPCs through motivational delegation, every outcome is auditable via a structured trace, and a Process Fidelity eval harness scores not just goal completion but the path that produced it.*

## 2. 工程能力栈 → 证据 → 对应岗位

| 能力域 | 具体做了什么（真实代码 / artifact） | 对应岗位信号 |
| --- | --- | --- |
| **多 agent 编排** | `MotivationEngine -> ToolExecutor -> ResultObserver` tick 主路径；规则版 Director v0 + Event Skill（`event.starlight_festival_shortage`）；NPC arbitration 输出 `candidateScores` + `scoreComponentSourceRefs` / `scoreExplanationRefs`；`ToolDefinition.served_needs` + `CapabilityRegistry` 显式需求匹配。 | Agent infra / LLM application engineer |
| **可观测性工程** | `phase2.trace.v1` 覆盖 `motivation.decision_made`、工具完成/失败/中断、`memory.result_observed`、`budget.decision_consumed` / `budget.decision_fallback`，每条带 `sourceEventIds` + `traceRefs` 形成证据链；`GET /api/debug.phase2`；Godot Observer Dock + Web Debug（Heuristic Library / Arbitration Trace / Rashomon Memory）。 | Platform / observability / debugging tools |
| **Eval 工程** | `scripts/run_agent_eval.py` 覆盖 process / stability / determinism / domain / robustness suite；Process Fidelity 含 5 种 ablation baseline + counterfactual replay + budget trace check；跨域 adapter（town / coding，8 fixture + `dependency_evidence_chain.v2`）；`phase2.evidence_robustness.strict_gate.v1`；四层 provenance 飞轮（`eval:archive:promote` + drift policy + named cloud artifact）。 | ML / research engineer / eval infra |
| **全栈系统** | Python Agent Server（权威世界状态）+ Godot 4.x 客户端（表现层）+ Web Debug 控制台；LLM provider 抽象（`RuleBasedProvider` + OpenAI-compatible `CloudApiProvider` + fallback + cost 总览）；`schema_registry.v1` 集中 schema 治理。 | 全栈 / 系统 / backend engineer |

## 3. 面试 talking points

- **Motivational Delegation 的设计选择**：Director 不直接命令 NPC，而是塑造动机 / 机会 / 信息 / 事件压力 / 资源约束 / 可用工具，NPC 在合法工具间用自身状态仲裁。这是 agent 自主性与可控性之间的工程权衡。
- **可审计性如何落地**：不是事后日志，而是决策时就写结构化 trace——每个 tool 选择带 `sourceEventIds` 指回触发它的记忆 / 关系 / 预算事件，在 Observer Dock 里可逐步还原因果链。
- **eval 为什么不只看 goal success**：goal success 会掩盖「强推 / 走捷径」的路径，所以 Process Fidelity 同时度量路径质量（process coverage / agent-initiated ratio / shortcut violation / causal trace coverage），并用 ablation + counterfactual replay 验证指标对证据完整性敏感。
- **真实 LLM 证据**：4 GoalSpec × 5 seed × 5 baseline 跑通 100 次 cloud 调用、0 fallback、约 19 万 token / $0.03，并经 promote + drift policy 固化为命名 artifact。
- **最强信号——诚实降级（见 §4）**：主动发现自己的实验设计缺陷并显式降级 claim，是研究素养而非弱点。

## 4. 诚实边界（必须主动说，是加分项）

- 当前结果是 **metric / explainability 级**：指标对证据缺失 / 归属错乱 / 链接剥离敏感（可验证、已支持）。
- **不主张** human-validated believability：2026-06-02 复盘发现 baseline 之间不产生行为分化（`hard_delegation` 是 metric stub 不跑 runtime；memory / relationship ablation 输入进入决策路径，但在 promoted scenarios 中没有改变 `goalToolEvents`），所以「Full 生成更可信行为」的因果前提不成立，已显式降级并记录（`docs/human_rating_pilot_gate.md`、`paper/claim_evidence_matrix.md` C2/C3/C4）。
- 面试讲法：「我设计了 ablation 对照，但在投入人类盲评前核查发现 baseline 不产生可感知的行为分化，所以这个对照只能支撑 explainability 而非 believability 因果。我把 claim 降级、记录了根因，并把行为分化 baseline 列为 future work。」

## 5. 与 AlgoCoach 的分工（两个项目互补）

- **AlgoCoach-Flywheel**（求职 + 论文主力）：post-training 纵深——verifier-backed eval、7B QLoRA SFT/DPO、推理部署、provenance 数据飞轮。
- **Loomstead**（互补第二项目）：系统 / agent 编排 / 可观测性广度——多 agent runtime、trace schema、Godot 可视化、跨域 eval。
- 简历叙事：AlgoCoach 证明「能把模型训出来、评得准、部署上线」；Loomstead 证明「能设计可解释的 agent 系统并做可观测性 / eval 工程」。

## 6. 求职材料清单

- **已就绪**：`README.md`（Watch / Research 双入口）、`paper/blog_main.md`（技术博客主文）、Figure 1/2/3/4、trace 走查、Showcase Mode v1（Godot ShowcasePanel + `/api/showcase/starlight`）。
- **可选录制（manual gate）**：如果现有 Godot / Observer 界面已经足够清晰，可录 30-60 秒 explainability 素材；如果需要新 UI 开发才能讲清楚，则不继续投入展示层，只保留 README / blog / capability map 作为 portfolio 入口。脚本见 `docs/demo_capture_plan.md`，收口追踪见 `docs/showcase_manifest.md`。

## 7. 当前收尾与挽救节奏

- **兜底收尾优先**：当前先把 Loomstead 固化为工程展示项目，主要展示多 agent 编排、trace observability、eval infra 与 Godot 可视化；不为包装继续追加大 UI 或新玩法。
- **短挽救实验**：兜底收尾后可做一次 Auditable Agents spike，验证 `sourceEventIds` / `traceRefs` / counterfactual replay 能否形成高风险动作 provenance、policy bypass 检测与审计报告。
- **停止条件**：如果 spike 无法产出明确行为分化、policy bypass 差异或 reviewer 可读审计报告，则结束 Loomstead 研究投入，只保留本 capability map、README、blog 与现有 demo 资产。
