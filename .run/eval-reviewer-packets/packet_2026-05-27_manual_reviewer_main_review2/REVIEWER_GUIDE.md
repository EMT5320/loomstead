# Reviewer Sampling Packet Guide

- packetId: `packet_2026-05-27_manual_reviewer_main_review2`
- packetVersion: `phase2.eval_reviewer_sampling_packet.v1`
- createdAt: `2026-05-27T14:01:34+00:00`

## Manual Gate

- status: `manual_review_required`
- 该包只负责抽样与路径整理；主观评分必须人工完成。

## Suggested Review Steps

1. 逐条打开 `reviewer_sampling_packet.json` 的 `perScenarioArtifact.repoPath`。
2. 结合 `companionArtifacts` 里的 trace / replay / evidence 文件复核过程证据。
3. 在 `reviewer_score_sheet.csv` 填写 1-5 分和结论备注。
4. 保留 fail 条目的具体证据路径，便于后续追溯。

## Stop Condition

- 该阶段到人工打分为止；脚本不自动生成最终结论。
