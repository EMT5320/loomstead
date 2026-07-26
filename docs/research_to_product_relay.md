---
status: active
owner_lane: research-quality
last_verified: 2026-07-26
startup_load: on-demand
source_of_truth: true
scope: Loomstead 的证伪结论如何成为 Tsukumo 的设计前提；两个仓库之间唯一的因果链事实源
---

# 研究 → 产品接力：一个被证伪的结论，和为它造的下一台仪器

> **一句话**：Loomstead 问「agent 的证据是否因果驱动它的行为」。答案是测不出来——而且原因可以精确定位到一行指标定义：
> 那个叫 `goal_success_rate` 的指标一半在测行为、一半在测自己的埋点。2026-06-02 按记录关闭盲评、撤回可信度措辞。
> 诊断是那些证据只对**指标**承重，不对**下一次动作**承重；要让它承重，它必须跨越一道 runtime 边界。
> [Tsukumo](https://github.com/EMT5320/tsukumo) 是造那道边界的仪器。
>
> *Loomstead asked whether an agent's evidence causally drives its behavior. It could not be measured, and the reason
> is one line of metric definition: `goal_success_rate` was half a behavior check and half an instrumentation check.
> The pre-registered pilot was closed on 2026-06-02 and the believability wording withdrawn. The diagnosis: the
> evidence was load-bearing for the metric, not for the next action. Tsukumo builds the boundary that makes it
> load-bearing.*

这条链此前只记录在 Tsukumo 的内部收敛稿和 `DESIGN.md` 的散落段落里，从 Loomstead 一侧完全看不见。
本文是两个仓库之间唯一的因果链事实源。

- 上游：本仓库（Loomstead），Agent 行为观测台
- 下游：[Tsukumo](https://github.com/EMT5320/tsukumo)，跨 runtime 状态与交接层

---

## 1. 可核验的时间线

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-05-13 | Loomstead 起始提交 | `git log --reverse` 首条 |
| 2026-05-29 | promoted process run 产出（4 scenarios × 5 seeds，n=20） | [`run_2026-05-29T13-57-50Z/`](../.run/eval-promoted/run_2026-05-29T13-57-50Z/) |
| 2026-06-02 | 预注册盲评 gate **因前提不成立而关闭**，可信度措辞撤回 | [`human_rating_pilot_gate.md`](human_rating_pilot_gate.md) |
| 2026-07-07 | Tsukumo 起始提交 | tsukumo `git log --reverse` 首条 |
| 2026-07-10 | Tsukumo 写下「研究—产品接力」，把 Loomstead 的负结果列为设计约束 | tsukumo `docs/tsukumo-vision-state-handoff-convergence-2026-07-10.md` §3 |

退让发生在下游项目开工前一个月。顺序不是事后编排的。

---

## 2. 第一阶段：Loomstead 问的问题

> 一个 agent 为什么采取了这个动作？哪些证据参与了决策？移除某类证据后，行为是否变化？

为回答它建了：结构化 trace、`sourceEventIds` / `traceRefs` 证据链、Process Fidelity 指标族、
反事实 replay、五条 ablation baseline、audit / failure-analysis packet、跨域 adapter。

这些仪器是后面那个否定结论**能够被确认**的前提。没有它们，你不会知道自己没测出来。

---

## 3. 转折：指标在测自己的埋点

原始数据见 [`ablation_comparison.json`](../.run/eval-promoted/run_2026-05-29T13-57-50Z/ablation_comparison.json)（n=20）：

| baseline | goal success | process believability | causal trace | 反事实换工具率 | shortcut violation |
|---|---|---|---|---|---|
| `full_motivational_delegation` | 1.0 | 1.0 | 1.0 | 0.375 (std 0.415) | 0.0 |
| `hard_delegation` | **1.0** | **0.037** | **0.0** | 0.0 | **1.0** |
| `no_subjective_memory` | 1.0 | 0.949 | 1.0 | 0.0 | 0.0 |
| `no_relationship_edge` | **0.0** | 0.563 | 0.0 | 0.25 | 0.0 |
| `shuffled_memory_owner` | **0.0** | 0.763 | 1.0 | 0.25 | 0.0 |
| `evidence_link_removal` | **0.0** | 0.363 | 0.0 | 0.25 | **1.0** |

三层结论，逐层收缩。

### 3.1 过程指标族确实能与目标成功率分离（仅指标构造层）

`hard_delegation` 一行 goal success 1.0、过程可信度 0.037、因果覆盖 0.0、捷径违规 1.0：
目标达成拉满而过程指标塌到地板，说明这组过程指标不是目标成功率的换算。

**这一行的 1.0 是声明的，不是测出来的。**
[`runner.py`](../backend/app/eval/runner.py) L1122 的 `_run_hard_delegation_process_scenario`
不跑 `AgentRuntime.tick`，直接传 `goal_success_override=True`（L1142）并返回硬编码的 `"ok": True`。

所以这一行**不能**被讲成「一个走捷径的 agent 照样拿到了目标」。它是指标构造层的分离性演示，
不是关于真实 agent 行为的实证结果。要做行为层对照，需要一个 runtime-backed 的 Hard baseline，
那项工作被明确延期。

### 3.2 三个消融的 goal success 归零，是指标耦合而非行为分化（关键发现）

`goal_success_rate` 的定义在 [`backend/app/eval/process_fidelity.py`](../backend/app/eval/process_fidelity.py) L79–L84：

```python
goal_success = (
    bool(goal_success_override)
    if goal_success_override is not None
    else process_checks.get("goal_relevant_tool_event", False)
    and process_checks.get("relationship_edge_trace", False)
)
goal_success_rate = 1.0 if goal_success else 0.0
```

`goal_success_override` 只被 §3.1 那个 stub 使用。真实 runtime 走的是后面那个合取。

两个合取项性质不同（[`backend/app/eval/runner.py`](../backend/app/eval/runner.py) L829–L831）：

- `goal_relevant_tool_event = bool(goal_tool_events)` — agent 是否真的执行了目标相关动作，**这是行为**
- `relationship_edge_trace = bool(goal_event_ids & relationship_source_ids)` — 目标事件 id 是否与关系边的
  source id 相交，**这是埋点是否完好**

所以这个名叫「目标成功率」的指标，一半在测行为、一半在测自己的证据链。
`evidence_link_removal` / `no_relationship_edge` / `shuffled_memory_owner` 打断的正是第二项。

对照 per-scenario 产物即可看到后果：`evidence_link_removal` 条件下 seed01–04 的 `goalToolEvents`
是同一个动作——agent `lena`、工具 `social.chat_with`、目标 `mira`、`tick 1`——而 `sourceLinks` 里出现
`"matched": false` / `source event 已不在当前 EventStore 窗口`。

**行为逐字段相同，指标从 1.0 掉到 0.0。**

这是评测基建的经典失效模式：成功指标与自身仪器耦合，降级仪器看起来就像降级行为。
表格里那三个刺眼的 0.0 不是「移除关系记忆导致 agent 失败」，把它那样讲会是一次过度主张。

### 3.3 因此可信度主张不可支撑，按记录撤回

见 [`human_rating_pilot_gate.md`](human_rating_pilot_gate.md)。盲评的前提是 reviewer 面前有两份**行为不同**
的运行；实际拿到的是行为相同、只有证据链断裂的两份运行。

处置：预注册 packet 不发 reviewer、不回收评分，仅作方法论记录保留；
`C2` / `C3` / `C4` 收缩为 `promoted with caveat`（metric / explainability 级）；
「Full 生成更可信行为」这句措辞**被撤回**。见 [`claim_evidence_matrix.md`](../paper/claim_evidence_matrix.md)。

余下可辩护的贡献：证据完整性度量、可解释性、debug guardrail。
反事实换工具率 0.375（std 0.415，n=20）是一个可索引可复查的敏感度信号，不是一个稳定效应。

---

## 4. 诊断：证据只对指标承重

上面那条链指向一个具体的结构原因，而不是「实验没做好」。

在 Loomstead 里，证据从来不需要活下来。它待在同一个 runtime、同一个进程、同一个会话里，
没有 token 预算压力，不必被压缩，不必被搬运，不必交给另一个 agent 继续用。

**没有任何机制迫使它跨越一道边界。** 于是它只对指标承重——打断它，指标动了；
它从来不对「下一次动作」承重，所以动作不动。

结论不是继续加指标，而是造出那道边界。

---

## 5. 第二阶段：Tsukumo 是造边界的仪器

[Tsukumo](https://github.com/EMT5320/tsukumo) 迫使状态经历它在这里从未经历的事：

1. 从真实执行轨迹派生（Chronicle：经历账）
2. 压进容量受限的 checkpoint（Canonical State + Handoff：状态账、交接账）
3. 投影到**另一个 runtime**，并留下 ProjectionReceipt（投影收据）
4. 每一步可审批、可撤销、可只读复检（`episode inspect`）

状态必须被压缩和搬运，才可能成为下一次动作的输入。这是「对动作承重」的必要条件。

Tsukumo `DESIGN.md` 里三处直接继承，不是事后附会：

| Tsukumo 位置 | 继承内容 |
|---|---|
| §8.6 | `traceRefs` 标注为「Loomstead 血统」；反事实重放作为现成实验 |
| §10.3 | Direct State Setter baseline 与 Process Fidelity 证明「完整性不足以推出行为与用户价值」，直接写成养成数值的设计约束 |
| §11.4 | 规定 **Loomstead-style 对照**：同任务、同 runtime、同模型，唯一变量是某条状态是否被投影 |

§11.4 要比较的量：tool choice、tool arguments、task success、clarification request、
policy violation、latency / token、result stability。

注意这份对照单里**没有**任何依赖埋点完好性的合取项。这是 §3.2 那个教训的直接产物。

---

## 6. 环还没闭上

**Tsukumo 目前只提供了仪器，没有提供测量结果。**

它尚未发表任何一个「移除某条状态改变了下游 runtime 的行为」的 case。§11.4 是规格，不是已完成实验。

这条边界必须守住。这个故事全部的价值在于「一个人如何诚实地撤回自己的主张」；
如果在讲述它的时候顺手声称环已经闭上，那就是重犯 Loomstead 记录在案撤回的那个过度主张。

现状口径：

- Loomstead：evidence / explainability 级贡献，`promoted with caveat`
- Tsukumo：跨 runtime 状态交接的**工程契约**已验证；行为改变**尚未**验证
- 合起来：一个被证伪的问题，和一台为重新回答它而造的仪器

---

## 7. 为什么这条链本身是成果

一次预注册、一次前提检验、一次定位到指标定义的根因、一次按记录的撤回、一台为诊断而造的新仪器。

评测与 harness 方向最需要的不是所有假设恰好成立的人，而是能发现自己的成功指标在测自己的埋点、
据此杀掉自己结论、并且知道下一步该造什么的人。

Loomstead 那些看起来「白做了」的工作没有一件是无用功：
正因为 trace、五条 ablation、promoted run 和 per-scenario 产物都在，
「行为层没有分化」才是一个**可以被定位到一行代码的结论**，而不是一次没人注意到的失败。

---

## 相关入口

- 本仓库对外第一跳：[`portfolio_case_cards.md`](portfolio_case_cards.md)，其中 Card B 即「移除证据后什么变了」
- 撤回记录：[`human_rating_pilot_gate.md`](human_rating_pilot_gate.md)
- 主张与证据对照：[`claim_evidence_matrix.md`](../paper/claim_evidence_matrix.md)
- 指标定义：[`process_fidelity.py`](../backend/app/eval/process_fidelity.py) · [`runner.py`](../backend/app/eval/runner.py)
- 下游仓库：[Tsukumo](https://github.com/EMT5320/tsukumo) · [claim 红线](https://github.com/EMT5320/tsukumo/blob/main/docs/PORTFOLIO_EVIDENCE.md)
