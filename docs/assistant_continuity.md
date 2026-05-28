---
status: active
owner_lane: context-governance
last_verified: 2026-05-26
startup_load: on-demand
source_of_truth: true
scope: cross-assistant resume, handoff, and evidence protocol
---

# 跨助手接续协议

本文定义家里 / 公司环境、多 AI 助手和子代理之间的统一接续流程。它是助手无关协议；Kilo command、Claude workflow、Codex prompt 都只做薄适配。

## 1. 接手流程

- 先运行 `npm.cmd run context:resume`，读取短接续摘要。
- 再读 `docs/agent_context.md`，确认项目定位、当前边界和最近下一步。
- 只有当任务涉及事实更新、验收状态或下一步判断时，才读 `docs/current_status.md`。
- 只有当任务进入具体开发线时，才读取对应源文档和代码。
- 不把 `docs/archive/`、旧 handoff 或 `.run/` artifact 当作当前事实源，除非任务明确要求溯源。

## 2. 开工前检查

- 查看当前分支和脏区，避免覆盖他人或其他助手的改动。
- 判断触达开发线：后端 / Eval / Godot / Web Debug / Content / Assets / LLM / 上下文治理。
- 根据开发线选择最小验证命令，不默认运行全量 eval 或真实 LLM。
- 如果发现状态文档与代码、命令或人工验收记录冲突，以代码和可复盘证据为准，并收缩文档表述。

## 3. 工作中约束

- 优先做最小正确改动，避免借接续治理扩 scope。
- 状态文档只写当前事实、验证状态、manual gate 和下一步，不复制源设计长文。
- 多助手并行时，`docs/current_status.md`、`docs/agent_context.md`、`AGENTS.md` 等治理入口由主会话串行修改。
- 本机私有 key、模型 overlay、本地绝对路径和未整理 `.run/` artifact 不进入提交态。
- 家里 / 公司交替开发时，已整理的 eval 证据子树可随 Git 同步：`.run/eval-runs/`、`.run/eval-promoted/`、`.run/eval-reviewer-packets/`、`.run/process-llm-evidence/`；发现本机缺少文档记录的 run 时，先视为 artifact 同步缺口，不默认重跑白天已完成的 eval。

## 4. 证据等级

- `code integrated`：代码或文档已修改并可定位到文件。
- `command checked`：命令已运行并记录结果。
- `artifact backed`：eval manifest、trace、JSONL、hash 或其他 artifact 可复盘。
- `manual verified`：主人或操作者已在真实窗口、浏览器或真实 provider 环境观察过。
- `manual unverified`：代码或离线检查完成，但仍缺真实窗口、真实 LLM、外部服务或人工体验确认。

## 5. 收工交接模板

```md
## Scope
<触达开发线和关键文件>

## Changes
- <本轮完成的事实>

## Verification
- command checked: <命令和结果>
- artifact backed: <manifest / trace / run，如不适用写 not-needed>
- manual verified: <实际人工观察>
- manual unverified: <仍需人工或真实服务确认>

## Risks
- <阻塞、跳过的命令、环境限制或回归风险>

## Next Step
<下一位助手可直接执行的最小任务>
```

## 6. 常用入口

- 接续摘要：`npm.cmd run context:resume`。
- 收工交接草稿：`npm.cmd run context:handoff`。
- 上下文治理：`npm.cmd run context:check; git diff --check`。
- 命令选择：参考 `docs/workflows.md` 中的 `test-eval-triage`。
- 分支交接：参考 `docs/workflows.md` 中的 `branch-review`。
- Kilo 快捷入口：`/loomstead-resume`、`/loomstead-handoff`。
