---
status: reference
owner_lane: research-quality
last_verified: 2026-06-01
startup_load: never
source_of_truth: false
scope: Discussion note for the human-rating pilot decision gate; not a context entry or formal protocol.
---

# Human Rating Pilot Decision Note

> 留档用途：记录 2026-06-01 关于 Loomstead 核心价值主张、展示层投入和 human ratings 的质量审核讨论。
> 本文不是 `agent_context` / `current_status` / checkpoint 入口，不升级 claim level，也不替代正式实验协议。

## 1. 核心风险

本轮讨论认为，Loomstead 当前最危险的审稿质疑不是单纯的“为什么不直接派任务”，而是循环论证：

```text
这些 Process Fidelity 指标由作者定义，天然偏向 Motivational Delegation。
如果 goal_success 已经达成，过程“不可信”到底造成了什么损失？
作者是否只是设计了一场自己稳赢的比较？
```

因此，自动指标不能单独承担最终研究 claim。它们需要外部效度：至少证明这些指标与非作者 reviewer 对“过程可信、角色自主、结果是否赚到”的判断方向一致。

## 2. 展示层循环

继续打磨 demo 视频、GIF、Godot 展示和博客存在一个循环风险：

- 核心 claim 尚未被 human ratings 验证，展示层难以讲清研究故事。
- 展示层效果不佳，又反过来让人怀疑后端 agent、LLM 和 eval 主线是否足够支撑 claim。
- 如果继续大量投入展示层，可能变成给未验证的研究故事做包装。

当前判断：后端 trace / eval artifact 可能已经足够支持一个小型盲评 pilot；Godot 展示层暂时不应默认成为下一轮重投入主线。更合理的顺序是先验证核心 claim 信号，再决定展示层具体包装什么。

## 3. 需要拆开的三个问题

Human rating pilot 不应粗暴回答“项目行不行”，而应拆分为三层：

| 层级 | 问题 | 若失败意味着什么 |
| --- | --- | --- |
| A. Process premise | 人类是否真的在乎 goal success 之外的过程可信度？ | Process Fidelity 作为核心研究卖点变弱。 |
| B. Metric validity | 自动 Process Fidelity 指标是否预测人类评分？ | 自动指标需要重做，或降级为 debug / regression guardrail。 |
| C. System capability | 当前 Full Motivational Delegation 是否比 Hard / Direct 生成更可信过程？ | 当前实现不足以支撑强 empirical claim，需要回到 agent / content / LLM 行为质量开发。 |

这样可以避免 pilot 结果出来后被任意解释。例如 C 失败不等于 A 失败；它可能只是当前系统实现还不够强。

## 4. Reviewer 来源判断

只有作者本人评分不能破解循环论证。Reviewer 不一定全是研究员，但必须满足基本独立性：

- 非作者。
- 不知道 trajectory 属于 Full / Hard / Direct / ablation 哪个条件。
- 按评分前固定的 rubric 打分。
- 样本顺序随机化。
- 自由文本说明保留，用来判断评分是否有真实依据。

最小 pilot 可考虑 3-5 名外部 reviewer，其中最好包含 1-2 名 AI / HCI / agent / 游戏叙事相关背景的人。正式 empirical claim 若要增强，再扩到 mixed panel：少量 expert reviewer 加更多目标用户或众包 rater。

## 5. Pilot Gate 建议

跑 pilot 前需要预先写死“信号好 / 差 / 协议失败”的判据，避免结果出来后因确认偏误而重解释。

建议的正信号仅解锁下一轮投入，不直接升级论文 claim：

- Full 在 `process believability` / `earned outcome` 上平均高于 Hard 至少约 0.5-0.75 / 5。
- Full 至少在 2/3 场景中胜过 Hard 或 Direct。
- Full 绝对均分不低于 3.5 / 5，避免只是“比差 baseline 稍好”。
- Pairwise preference 中 Full 胜 Hard / Direct 约 65%-70% 或更高。
- 自动 Process Fidelity 与人类评分排序方向在至少 2/3 场景一致。

建议的负信号应触发收缩或转向：

- Full 与 Hard 基本无差异，或 Full 低于 Hard。
- Full 绝对均分低于 3.0 / 5。
- Reviewer 评论集中指出“脚本化、跳跃、看不懂角色为什么这么做、像被导演硬推”。
- 自动 Process Fidelity 排序与人类评分长期不一致。

协议失败需要单独处理：

- 如果 reviewer 普遍看不懂 packet、评分分歧完全无结构，说明材料或 rubric 失败。
- 这种情况下只允许修一次协议或 packet 表达，不应改样本解释结果。

## 6. 分支不对称原则

Pilot 的正负信号不能对称处理：

- 正信号：只能说明“值得继续投入”，下一步是扩样本、正式化 protocol、补 rater agreement 和更强 baseline。
- 负信号：足以说明当前强 claim 不应继续包装，需要降级或回炉。

原因是小样本 pilot 的正结果不能证明最终结论，但负结果已经足够提示当前路线不值得继续用展示层硬撑。

## 7. 降级路径的真实代价

若 pilot 信号差，已有工程不废弃，但 claim surface 需要收缩：

| 失败点 | 降级后果 |
| --- | --- |
| A 失败 | 项目不再主打 Process Fidelity 研究，转为可解释 agent runtime / narrative sandbox。 |
| B 失败 | Process Fidelity 自动指标不能声称是 human believability 代理，只能作为 debug trace / regression guardrail。 |
| C 失败 | 当前系统生成过程不够强，优先回到 agent 行为、内容、LLM 决策质量和 scenario 设计。 |
| 多项失败 | 论文路线降级为 demo / systems prototype / portfolio project。 |

对应地，C2 / C3 / C4 这类 promoted-with-caveat claim 不能因为已有自动 eval 或展示材料而升级为强论文 claim。

## 8. 下一轮优化方向

建议分叉对话的具体实现和质量审核围绕以下目标展开：

1. 暂停继续重投入 demo polish，除非它直接服务 pilot packet 可读性。
2. 先产出一页 pilot decision gate：场景、条件、样本、rubric、reviewer、Green / Red / Protocol failure 判据。
3. 优先复用当前 eval artifact，生成最小盲评 packet，避免手工挑选“最好看”的样本。
4. Reviewer 条件映射单独保存，评分材料中隐藏 baseline 标签。
5. Pilot 结果按预注册分支处理：扩研究、回炉系统、或降级为可解释 runtime / portfolio 展示。

这份 note 的用途是作为后续评审锚点：检查新方案是否真的解决循环论证、展示层循环、确认偏误和降级代价，而不是继续堆展示或指标。
