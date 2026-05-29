# Eval Run Promotion

- status: `paper_grade_candidate`
- purpose: `paper` (论文证据)
- promotedAt: `2026-05-29T03:02:25+00:00`
- sourceRunDir: `.run/eval-runs/run_2026-05-28T07-43-32Z`
- suite: `process_fidelity`
- baseline: `full_motivational_delegation`
- manifestSha256: `f8b3fe4e4254999b304a95ec1a336c16502bc484a36ddc136514fd1c76d86f19`
- note: 支撑 claim matrix C2/C3/C4：rule-level Motivational Delegation process suite + Hard Delegation ablation；partial empirical，待真实 LLM 与人工评分补强。

## Purpose note prompts

- 说明该 run 支撑的研究问题或表格编号。
- 记录 baseline / ablation 与主要指标解读。
- 补充 llmEvidence：provider_usage_actual.v1 记录、token / latency / cost / fallback 与 final selectedToolId。
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

## LLM evidence

```json
{
  "schemaVersion": "process_llm_evidence.v1",
  "providerUsageSchemaVersion": "provider_usage_actual.v1",
  "source": "current_run",
  "providerMode": "rule",
  "seedCount": 5,
  "recordCount": 0,
  "cloudCallCount": 0,
  "fallbackCount": 0,
  "totals": {
    "calls": 0,
    "tokens": 0,
    "promptTokens": 0,
    "completionTokens": 0,
    "latencyTotalMs": 0,
    "latencyAvgMs": 0.0,
    "cost": 0.0,
    "currency": null
  },
  "records": []
}
```

## Purpose checklist

- [ ] 确认 schema 与论文方法描述一致。
- [ ] 确认导出 artifact 可复现。
- [ ] 确认真实模型或人工窗口证据已单独记录。
- [ ] 确认 llmEvidence 中的真实模型调用和 fallback_reason 已人工复核。
