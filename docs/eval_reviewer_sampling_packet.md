---
status: active
owner_lane: eval
last_verified: 2026-05-27
startup_load: on-demand
source_of_truth: true
scope: manual reviewer sampling packet generation for process/domain eval artifacts
---

# Eval 人工 Reviewer 抽样包（Manual Gate）

本文定义 Phase 2 `process_fidelity` + `cross_domain_adapter` 的人工 reviewer 抽样包生成方式。目标是把审核输入整理成可执行包，到人工评分处停止。

## 1. 边界

- 只读取 `.run/eval-runs/*/manifest.json` 与其中登记的 artifacts。
- 不运行真实 LLM，不重跑 eval，不改写已有 run。
- 输出写入 `.run/eval-reviewer-packets/<packet_id>/`，属于本地产物。
- 脚本只做抽样与模板生成；最终结论必须人工填写。

## 2. 命令

```powershell
python scripts/build_eval_reviewer_packet.py `
  --process-run run_2026-05-27T13-37-33Z `
  --domain-run domain_2026-05-27T13-29-21Z `
  --process-samples 3 `
  --domain-samples 3 `
  --packet-id packet_2026-05-27_manual_reviewer_seeded
```

可选参数：

- `--seed`：抽样随机种子，默认 `20260527`。
- `--process-run/--domain-run` 留空时自动选择对应 suite 最新 `ok=true` 且 `git.dirty=false` 的 run；若确需使用 dirty run，显式添加 `--allow-dirty-runs`。
- `--out-dir` 可覆盖输出根目录。

## 3. 输出内容

- `reviewer_sampling_packet.json`：机器可读清单，含 source runs、抽样策略、samples、manual gate。
- `reviewer_score_sheet.csv`：人工打分模板（1-5 分 + fail/pass + notes）。
- `REVIEWER_GUIDE.md`：执行步骤与停止条件。

## 4. Manual Gate（停止点）

生成抽样包后停在以下人工步骤：

1. Reviewer 打开 `reviewer_sampling_packet.json` 的 `perScenarioArtifact.repoPath`。
2. 结合 `companionArtifacts` 复核 trace / replay / evidence。
3. 填写 `reviewer_score_sheet.csv`。
4. 在 PR 或研究记录中回填人工结论。

脚本阶段不自动生成最终评分、通过结论或论文 claim。
