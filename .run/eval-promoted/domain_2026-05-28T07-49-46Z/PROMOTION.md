# Eval Run Promotion

- status: `paper_grade_candidate`
- purpose: `paper` (论文证据)
- promotedAt: `2026-05-29T03:02:37+00:00`
- sourceRunDir: `.run/eval-runs/domain_2026-05-28T07-49-46Z`
- suite: `cross_domain_adapter`
- baseline: `full_motivational_delegation`
- manifestSha256: `75e8c4be26851bbe35992e39b140a745e7d6eef3592391697ea20cd55dbe8a32`
- note: 支撑 claim matrix C7：DomainAdapter town/coding 跨域 summary schema 可比性。

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
  "schemaVersion": null,
  "providerUsageSchemaVersion": null,
  "source": null,
  "providerMode": null,
  "seedCount": null,
  "recordCount": 0,
  "cloudCallCount": 0,
  "fallbackCount": 0,
  "totals": {},
  "records": []
}
```

## Purpose checklist

- [ ] 确认 schema 与论文方法描述一致。
- [ ] 确认导出 artifact 可复现。
- [ ] 确认真实模型或人工窗口证据已单独记录。
- [ ] 确认 llmEvidence 中的真实模型调用和 fallback_reason 已人工复核。
