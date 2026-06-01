# Human Rating Pilot Reviewer README：human_rating_pilot_2026-06-01_zh_v0

## 使用方法

1. 逐条阅读 `reviewer_cards/HRP-*.md`。
2. 在 `blind_score_sheet.csv` 中填写 1-5 分与备注。
3. 再填写 `pairwise_preference_sheet.csv`，只比较 A/B 哪个过程更可信、结果更赚取。
4. 如果材料看不懂、缺上下文或无法评分，在 `protocol_issue_flag` 标记 `yes` 并写明原因。

## 评分锚点

- 1 = 明显硬推、跳跃或脚本化。
- 2 = 有少量过程，但关键因果缺失。
- 3 = 基本合理，但动机或证据偏薄。
- 4 = 过程自然，有可理解动机与上下文。
- 5 = 非常自然，像角色自己发展出的结果。

## 本包规模

- 单样本评分：6 条。
- Pairwise 比较：3 组。
- 条件标签已隐藏；请不要询问内部映射。
