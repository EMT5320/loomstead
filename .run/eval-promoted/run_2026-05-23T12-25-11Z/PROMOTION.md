# Eval Run Promotion

- status: `paper_grade_candidate`
- purpose: `paper` (论文证据)
- promotedAt: `2026-05-23T12:26:26+00:00`
- sourceRunDir: `.run/eval-runs/run_2026-05-23T12-25-11Z`
- suite: `process_fidelity`
- baseline: `full_motivational_delegation`
- manifestSha256: `7288109177e1330d6be96b1b34562ed00809c01723111da27995d97e28debce6`
- note: 2026-05-23 clean export after commit 95bd7e3; process_fidelity Full baseline anchors narrative-primary evidence; drift report severity none; no tracked dirty worktree during export; Godot/manual window evidence remains separate from this rule-level suite.

## Purpose note prompts

- 说明该 run 支撑的研究问题或表格编号。
- 记录 baseline / ablation 与主要指标解读。
- 说明 drift policy、git dirty 和人工窗口验收状态。

## Manual review items

- 暂无自动发现的人工复核项。

## Paper-grade checklist

- okTrue: True
- archiveCheckPassed: True
- gitCleanAtExport: True
- schemaRegistryV1: True
- driftExplained: True
- driftPolicyBlocking: False
- manualWindowVerified: False
- externalModelVerifiedIfNeeded: False

## Purpose checklist

- [ ] 确认 schema 与论文方法描述一致。
- [ ] 确认导出 artifact 可复现。
- [ ] 确认真实模型或人工窗口证据已单独记录。
