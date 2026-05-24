---
title: Loomstead workflow catalog
status: active
source_of_truth: true
owner_lane: context-governance
last_reviewed: 2026-05-25
last_verified: 2026-05-25
startup_load: on-demand
scope: Persistent Claude Code workflow catalog for research, eval, and verification discipline.
---

# Loomstead workflow catalog

本页记录可在家里和公司环境共享的项目 workflow。它们用于提高研究效率、审查质量和证据复盘，不替代研究判断，也不自动扩展项目 scope。

## 核心原则

- 默认只读分析；代码和状态文档修改由主会话串行完成。
- 输出必须区分 `code integrated`、`command checked`、`manual verified`、`manual unverified`。
- 研究结论必须指向可复盘证据：代码位置、命令输出、eval artifact、manifest、trace 或明确的人工验收记录。
- `docs/current_status.md` 只记录当前事实、验证状态和下一步；设计意图放在 vision / research / eval spec 文档。
- 常规 `check` / `smoke` 不访问真实 LLM；真实 provider、Godot 窗口和玩家手感验收需单独标记。
- 家里 / 公司切换时避免本机绝对路径、私有 key、临时 overlay 进入仓库。

## 持久化位置

可执行或半可执行 workflow 规格放在：

```text
.claude/workflows/
```

当前索引文档放在：

```text
docs/workflows.md
```

## P0：优先使用

### `research-claim-review`

位置：`.claude/workflows/research-claim-review.md`

用途：审查研究 claim 是否被指标、trace、artifact 和实现事实支撑。

适用场景：

- 更新研究 framing。
- 准备对外解释 Motivational Delegation / Process Fidelity Eval。
- 将 eval 结果写入 status 或 portfolio 前。
- 怀疑 claim 过强、证据不足或 baseline 不公平时。

### `process-eval-audit`

位置：`.claude/workflows/process-eval-audit.md`

用途：审查 Process Fidelity Eval 证据链，包括 baseline / ablation、manifest、schema、drift、promotion 和人工验收边界。

适用场景：

- 跑完 process eval / stability / domain eval 后。
- 准备 promote eval run。
- 修改 eval schema、metric、manifest、archive 或 baseline 后。
- 更新 `docs/current_status.md` 中 eval 事实前。

### `test-eval-triage`

位置：`.claude/workflows/test-eval-triage.md`

用途：根据触达 lane 选择最小必要验证命令，并把失败分诊为 quick / lane / eval / manual gate。

适用场景：

- 家里和公司环境切换后恢复上下文。
- 提交前选择验证命令。
- 命令失败后判断下一步查哪里。
- 区分离线验证与真实 LLM / Godot 人工验收。

## P1：明天或后续补齐

- `branch-review`：当前分支 / PR 前综合审查，包装 `review-branch`、`code-review` 或 `bughunt-lite`。
- `bug-sweep`：高风险 runtime / eval / schema / trace 变更后的 bug sweep。
- `schema-drift`：专门检查 schema registry、trace schema、debug API、eval manifest 是否同步。
- `consistency-sweep`：检查 backend → frontend Web Debug → Godot → docs 的字段和事实一致性。

## P2：后续自动化候选

- `next-step-planner`：只针对一个 lane 生成下一步计划，避免 scope 漂移。
- `research:brief`：npm script，输出当前 claim、最新 promoted eval、drift 状态和 manual unverified 列表。
- `research:evidence:check`：npm script，检查 promoted run 的 manifest、schema、rowCount、hash 和 LLM evidence 字段完整性。

## 建议执行节奏

今晚优先完成 P0 workflow 文档化。后续在公司环境 smoke 后，再把高频 workflow 转成可执行 JS workflow 或 npm script。

推荐顺序：

1. 使用 `research-claim-review` 收紧研究 claim。
2. 使用 `process-eval-audit` 审查证据链。
3. 使用 `test-eval-triage` 选择最小验证命令。
4. 根据验证结果串行修改代码或文档。
5. 运行 `npm.cmd run context:check` 和 `git diff --check`。
