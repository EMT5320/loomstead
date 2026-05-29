# Eval Run Promotion

- status: `needs_manual_review`
- purpose: `paper` (论文证据)
- promotedAt: `2026-05-29T03:02:31+00:00`
- sourceRunDir: `.run/eval-runs/stability_2026-05-25T07-34-55Z`
- suite: `stability_24h`
- baseline: `rule_24h_stability`
- manifestSha256: `56243e2883d9cb5b4d67c424550217e0470edf57d1d6c458fc83bc71fb336ed5`
- note: 支撑 claim matrix C6：rule runtime 24h stability 窗口。

## Purpose note prompts

- 说明该 run 支撑的研究问题或表格编号。
- 记录 baseline / ablation 与主要指标解读。
- 补充 llmEvidence：provider_usage_actual.v1 记录、token / latency / cost / fallback 与 final selectedToolId。
- 说明 drift policy、git dirty 和人工窗口验收状态。

## Manual review items

- drift policy 要求人工复核；需要说明 metric / baseline / scenario / artifact 变化原因。

## Paper-grade checklist

- okTrue: True
- archiveCheckPassed: True
- gitCleanAtExport: True
- schemaRegistryV1: True
- driftExplained: False
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
