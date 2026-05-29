# Eval Run Promotion

- status: `needs_manual_review`
- purpose: `regression` (回归基线证据)
- promotedAt: `2026-05-28T02:55:37+00:00`
- sourceRunDir: `.run/eval-runs/robustness_2026-05-28T02-55-13Z`
- suite: `evidence_robustness`
- baseline: `full_motivational_delegation`
- manifestSha256: `c83aa59b7e98667500d81d41a4c25d7da3db9fc12359c51317575894fdc0d4df`
- note: Clean five-seed robustness strict gate export after commit 3d66186; drift review expected from seed count and eval gate signature summary changes.

## Purpose note prompts

- 说明该 run 锁定的回归范围。
- 记录预期稳定的 metric / scenario 集合。
- 说明允许漂移的字段和后续触发条件。

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

- [ ] 确认未来回归脚本会引用同一 suite。
- [ ] 确认 drift policy 输出已保存。
