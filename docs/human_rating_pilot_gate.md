---
status: active
owner_lane: research-quality
last_verified: 2026-06-01
startup_load: on-demand
source_of_truth: true
scope: Human Rating Pilot 的预注册 gate、盲评 packet 边界与分支判据
---

# Human Rating Pilot Gate

> 自管理层文档。用途：把 2026-06-01 讨论后的核心价值主张审核落成当前可执行 gate。它不升级 claim level；C2/C3/C4 仍保持 `promoted with caveat`，最终 empirical wording 继续等待 human ratings、扩样本和更强 baseline。

## 1. Gate 目标

Loomstead 当前核心风险是外部效度：自动 Process Fidelity 指标由作者定义，必须验证它们是否与非作者 reviewer 对“过程可信、角色自主、结果赚取”的判断方向一致。Pilot 只回答“是否值得继续投入正式 human-rating protocol”，不证明最终论文结论。

## 2. 三个拆分问题

| 层级 | 问题 | 失败后的含义 |
| --- | --- | --- |
| A. Process premise | 人类是否在乎 goal success 之外的过程可信度？ | Process Fidelity 作为主卖点变弱。 |
| B. Metric validity | 自动 Process Fidelity 排序是否预测人类评分方向？ | 自动指标降级为 debug / regression guardrail，或重做指标。 |
| C. System capability | 当前 Full Motivational Delegation 是否比 Hard / Direct 生成更可信过程？ | 当前系统能力不足，优先回到 agent / content / LLM 行为质量。 |

## 3. Pilot v0 范围

- 语言：中文；当前协助 reviewer 默认中文。
- Reviewer：3-5 名非作者；最好包含 1-2 名 AI / HCI / agent / 游戏叙事相关背景协助者。
- 条件隐藏：reviewer 不看 `baseline`、source path 或自动分数；内部映射单独保存。
- 样本来源：优先复用 `.run/eval-promoted/run_2026-05-29T13-57-50Z`，不重跑真实 LLM。
- 默认样本：3 个叙事场景 × `full_motivational_delegation` / `hard_delegation` × 1 seed，共 6 张 card + 3 组 pairwise。
- 默认命令：

```powershell
npm.cmd run eval:human-rating:packet -- --packet-id human_rating_pilot_2026-06-01_zh_v0
```

## 4. Reviewer rubric

单样本 1-5 分：

- `process_believability`：目标是否通过可理解中间过程达成。
- `earned_outcome`：结果是否像被上下文和角色行为逐步赚到。
- `character_autonomy`：角色是否像在根据自身动机、记忆、关系行动。
- `trace_clarity`：材料是否足以解释“为什么发生这件事”。

Pairwise：

- 同一场景下比较 A / B 哪个过程更可信。
- 比较 A / B 哪个结果更赚取。
- 填写 confidence 与自由文本。

## 5. 预注册判据

### Green signal

- Full 在 `process_believability` / `earned_outcome` 上平均高于 Hard 至少约 0.5-0.75 / 5。
- Full 至少在 2/3 场景中胜过 Hard。
- Full 绝对均分不低于 3.5 / 5。
- Pairwise preference 中 Full 胜 Hard / Direct 约 65%-70% 或更高。
- 自动 Process Fidelity 排序与人类评分排序在至少 2/3 场景一致。

### Red signal

- Full 与 Hard 基本无差异，或 Full 低于 Hard。
- Full 绝对均分低于 3.0 / 5。
- Reviewer 评论集中指出脚本化、跳跃、动机不清或被导演硬推。
- 自动 Process Fidelity 排序与人类评分长期不一致。

### Protocol failure

- Reviewer 普遍看不懂 packet。
- 评分分歧完全无结构，且自由文本显示材料或 rubric 有系统性问题。
- 协议失败时只允许修一次 packet 表达或 rubric，再重新收集；不能改样本解释结果。

## 6. 分支处理

- Green：扩样本、正式化 protocol、补 rater agreement、加入更强动态 baseline。
- Red：暂停强研究包装，回到 agent 行为、内容、LLM 决策质量或 scenario 设计。
- Protocol failure：修 packet 可读性或 rubric；展示层投入只服务材料可读性。

## 7. 当前执行边界

- Demo 视频 / GIF / 截图继续属于 `P_demo.exit`，但在 pilot v0 出结果前不做大规模 polish。
- 现有内部 `eval:reviewer:packet` 仍用于 artifact 审核；human rating pilot 使用 `scripts/build_human_rating_pilot_packet.py` 生成盲评包。
- 盲评结果未回填前，README / 博客只能继续使用 `promoted with caveat` 和 “human process ratings pending” 口径。
