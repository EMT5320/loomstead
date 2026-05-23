---
status: active
owner_lane: eval
last_verified: 2026-05-23
startup_load: on-demand
source_of_truth: true
scope: eval export manifest indexing, archive validation, and local retention policy
---

# Eval Dataset Archive 归档策略

本文定义 Phase 2 本地 Eval 导出的归档与复核方式，避免 `process`、`stability`、`domain` 证据只散落在 `.run/eval-runs/` 中。

## 1. 当前边界

- 本地导出根目录：`.run/eval-runs/`。
- 本地导出目录已被 `.gitignore` 忽略，不直接提交 run artifact。
- 每个有效 run 必须包含 `manifest.json`，manifest 版本为 `phase2.eval_manifest.v1`。
- `manifest.json` 是唯一索引入口；artifact 文件只通过 manifest 的相对路径读取。
- `scripts/index_eval_runs.py` 只索引和校验，不自动删除 run。

## 2. 常用命令

```powershell
npm.cmd run eval:process:export
npm.cmd run eval:stability:export
npm.cmd run eval:stability:long:export
npm.cmd run eval:domain:export
npm.cmd run eval:archive:check
npm.cmd run eval:archive:index
npm.cmd run eval:archive:drift
npm.cmd run eval:archive:promote -- <runDirName>
```

- `eval:archive:check`：校验所有 manifest 与 artifact 的 `bytes`、`sha256`、JSONL `rowCount`。
- `eval:archive:index`：在 `.run/eval-runs/index.json` 写入本地索引；该文件仍属于本地运行产物。
- `eval:archive:drift`：在 `.run/eval-runs/drift_report.json` 写入每个 suite 最新两次 run 的差异报告。
- `eval:archive:promote -- <runDirName>`：把指定 run 复制到 `.run/eval-promoted/<runDirName>/`，并写入 `promotion_record.json` 与 `PROMOTION.md`。

## 3. Manifest 校验规则

`scripts/index_eval_runs.py` 当前会检查：

1. manifest 必备字段：`manifestVersion`、`exportKind`、`createdAt`、`suite`、`baseline`、`ok`、`runDirName`、`git`、`schemaRegistry`、`metricIds`、`baselines`、`scenarioIds`、`artifacts`。
2. `manifestVersion == phase2.eval_manifest.v1`。
3. `runDirName` 与实际目录名一致。
4. artifact path 必须留在当前 run 目录内。
5. artifact 文件必须存在，且 `bytes` 与 `sha256` 匹配。
6. JSONL artifact 必须有 `rowCount`，且实际行数一致。

## 4. Retention 标记

索引文件会按 `suite` 给 run 标注保留建议：

- `keep_latest`：每个 suite 最新 3 个 run，默认保留。
- `historical_candidate`：更旧 run，可人工筛选后移动到长期归档。

当前策略只做标记，不做自动删除。删除、压缩或迁移 run 必须由人工明确确认。

## 5. Drift Report

`eval:archive:drift` 会按 suite 比较最新 run 和上一 run，报告：

- `metricIds`、`baselines`、`scenarioIds` 的新增、移除和稳定交集。
- `schemaRegistryVersion`、`exportKind`、`ok` 的变化。
- `artifactCountDelta`。
- 最新 run 与上一 run 的目录、创建时间和 Git 摘要。

该报告用于发现指标漂移、scenario 漏登、schema 迁移影响和导出内容变化；不会判定结果优劣。

## 6. Promotion 流程

Promotion 是“长期候选归档”动作，用于把某次已校验 run 从滚动本地导出区复制到候选目录。默认命令：

```powershell
npm.cmd run eval:archive:promote -- domain_2026-05-23T06-37-22Z
```

常用可选参数：

```powershell
python scripts/index_eval_runs.py --runs-dir .run/eval-runs --promote <runDirName> --promotion-id <targetName> --promotion-note "人工备注"
```

Promotion 规则：

1. promote 前会重新执行 archive 校验；存在 manifest / artifact 错误时拒绝 promote。
2. 目标目录默认是 `.run/eval-promoted/<runDirName>/`，已存在时拒绝覆盖。
3. promote 会完整复制源 run，并额外写入：
   - `promotion_record.json`：机器可读的晋级记录，版本 `phase2.eval_promotion.v1`。
   - `PROMOTION.md`：人工复核摘要。
4. 若 manifest 记录 `git.dirty=true`、manifest `ok=false`、缺少 drift 对比或 drift 有变化，`promotionStatus` 会标为 `needs_manual_review`。
5. 只有自动检查无人工复核项时，`promotionStatus` 才会标为 `paper_grade_candidate`。

Promotion 不代表证据已经可直接用于论文；它表示该 run 已从滚动导出区进入人工复核候选区。

## 7. Paper-grade 证据晋级条件

准备把某个 run 用作论文、报告或作品集证据前，至少满足：

- `ok=true`。
- `eval:archive:check` 通过。
- `eval:archive:drift` 无未解释的 metric / scenario / schema 漂移。
- 已执行 promotion，并确认 `promotion_record.json` 的 `promotionStatus` 与人工复核项。
- `git.dirty=false` 或记录清楚 dirty 原因。
- `schemaRegistry.registryVersion == schema_registry.v1`。
- 相关 suite 的 README / 状态文档已同步验证命令和结果。
- 若涉及真实模型或真实 Godot 窗口，单独记录人工验收时间与观察结论。

## 8. 后续收紧方向

- 增加 promotion 备注模板，区分论文、作品集和回归证据三种用途。
- 为 drift report 增加阈值策略，例如只在 metric / scenario 变化时让 CI 失败。
- 在真实研究样本稳定后，为 paper-grade runs 增加人工标签和备注文件。
