# Eval Run Promotion

- status: `needs_manual_review`
- purpose: `regression` (回归基线证据)
- promotedAt: `2026-05-28T03:09:29+00:00`
- sourceRunDir: `.run/eval-runs/robustness_2026-05-28T03-08-43Z`
- suite: `evidence_robustness`
- baseline: `full_motivational_delegation`
- manifestSha256: `e7ff1a561e1d2ee516c20dd0969e5c3878b4e9f636c7dea40efbddad4e4590db`
- note: Clean five-seed robustness strict gate export after commit c283f81; scenarioIds are now indexed for process, coding, and narrative robustness coverage. Drift review expected from manifest scenario id and gate summary changes.

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
