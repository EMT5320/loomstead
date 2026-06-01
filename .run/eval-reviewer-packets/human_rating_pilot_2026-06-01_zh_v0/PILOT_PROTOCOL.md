# Human Rating Pilot Protocol：human_rating_pilot_2026-06-01_zh_v0

## Scope

- 语言：中文。
- reviewer：3-5 名非作者协助者。
- 样本：3 个叙事场景 × 2 个隐藏条件 × 1 个 seed。
- source run：`.run/eval-promoted/run_2026-05-29T13-57-50Z`。
- 本包用于 pilot gate；正信号只解锁扩样本与正式 protocol，不能直接升级论文 claim。

## Green signal

- 隐藏 Full 条件在 process believability 或 earned outcome 上平均高于隐藏 Hard 条件 0.5-0.75 / 5。
- Full 至少在 2/3 场景中胜过 Hard。
- Full 绝对均分不低于 3.5 / 5。
- Pairwise preference 中 Full 胜 Hard / Direct 约 65%-70% 或更高。
- 自动 Process Fidelity 排序与人类评分排序在至少 2/3 场景一致。

## Red signal

- Full 与 Hard 基本无差异，或 Full 低于 Hard。
- Full 绝对均分低于 3.0 / 5。
- reviewer 评论集中指出脚本化、跳跃、动机不清或被导演硬推。
- 自动 Process Fidelity 排序与人类评分长期不一致。

## Protocol failure

- reviewer 普遍看不懂 packet。
- 评分分歧完全无结构，且自由文本显示材料或 rubric 有系统性问题。
- 协议失败时只允许修一次 packet 表达或 rubric，再重新收集；不能改样本解释结果。
