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
npm.cmd run eval:domain:export
npm.cmd run eval:archive:check
npm.cmd run eval:archive:index
```

- `eval:archive:check`：校验所有 manifest 与 artifact 的 `bytes`、`sha256`、JSONL `rowCount`。
- `eval:archive:index`：在 `.run/eval-runs/index.json` 写入本地索引；该文件仍属于本地运行产物。

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

## 5. Paper-grade 证据晋级条件

准备把某个 run 用作论文、报告或作品集证据前，至少满足：

- `ok=true`。
- `eval:archive:check` 通过。
- `git.dirty=false` 或记录清楚 dirty 原因。
- `schemaRegistry.registryVersion == schema_registry.v1`。
- 相关 suite 的 README / 状态文档已同步验证命令和结果。
- 若涉及真实模型或真实 Godot 窗口，单独记录人工验收时间与观察结论。

## 6. 后续收紧方向

- 增加可选 `--promote <runDir>`，把候选 run 复制到人工指定的长期归档目录。
- 增加跨 run 对比报告，显示 metrics 漂移、scenario 增减和 schema 版本变化。
- 在真实研究样本稳定后，为 paper-grade runs 增加人工标签和备注文件。
