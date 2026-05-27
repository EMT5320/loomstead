---
status: archive
owner_lane: context-governance
last_verified: 2026-05-27
startup_load: never
source_of_truth: false
scope: one-off exploration handoff for Eval, backend agent system, and paper directions
---

# 2026-05-27 下班前探索简记

## Scope

- 只读核对项目现状，没有改代码。
- 重点看三条后续主线：Eval、后端 Agent 系统、Paper / research writing。
- 已运行 `npm.cmd run context:resume`；开始前 git 工作区为 clean。

## Current Read

- Phase 1 已收口；当前不要重开旧玩法扩写。
- Phase 2 首轮骨架已落地，后端主路径是 `MotivationEngine -> ToolExecutor -> ResultObserver`。
- 当前最值得推进的是把 trace / eval / paper evidence 串成可复盘闭环。

## Recommended Order

1. Eval：先做 clean-git domain export，再跑 `paper:tables`，消掉当前 Table 5 dirty manifest 风险。
2. Eval：把 process / domain seeds 提到至少 5，补 mean / std / n 的稳定证据。
3. Paper：围绕现有 Table 5 写保守 prose，只声称 interface evidence，不外推 coding 性能。
4. Paper：从现有 narrative replay artifact 抽一条 concrete trace walkthrough，支撑 Figure 3。
5. Backend：后续做定向补强，优先 `ToolDefinition.served_needs`、CapabilityRegistry 语义过滤、arbitration score refs；暂不大规模扩工具和玩法。

## Risks

- 最新 cross-domain export `.run/eval-runs/domain_2026-05-27T08-21-49Z` 在 paper inventory 中记录 `dirty=True`。
- 当前 domain 证据是 deterministic `--seeds 2`，process paper 表仍偏小样本。
- 人工 reviewer / human believability 抽样还没形成证据。
- 真实 LLM 成功证据仍沿用旧记录，不应写成默认结论。

## Next Step

回家接续时建议直接执行：

```powershell
npm.cmd run context:resume
npm.cmd run eval:domain:export -- --seeds 2
npm.cmd run paper:tables
npm.cmd run eval:archive:check
```

若 clean export 正常，再考虑把 domain / process 扩到 `--seeds 5`。
