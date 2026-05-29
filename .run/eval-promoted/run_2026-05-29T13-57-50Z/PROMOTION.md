# Eval Run Promotion

- status: `needs_manual_review`
- purpose: `paper` (论文证据)
- promotedAt: `2026-05-29T13:57:54+00:00`
- sourceRunDir: `.run/eval-runs/run_2026-05-29T13-57-50Z`
- suite: `process_fidelity`
- baseline: `full_motivational_delegation`
- manifestSha256: `81c91fe3d8bc6384c965f2a8d7882a35384588ce5a3b2a68094d469241beb8ca`
- note: Owner reviewed on 2026-05-29: C2/C3/C4 may be cited as promoted with caveat. The export dirty state came from the same closure pass that fixed cross-environment evidence policy and promoted the cloud-backed process run. The drift caveat reflects expected metric/baseline/scenario/artifact expansion for the 4-GoalSpec, 5-seed, 5-baseline Process Fidelity evidence bundle. Human believability/process review and broader scenario coverage remain required before final empirical wording.

## Owner review resolution

- ownerReviewedAt: `2026-05-29`
- claimLevelDecision: `C2/C3/C4 promoted with caveat`
- final empirical wording: pending human believability/process review and broader scenario coverage

## Manual review items

- manifest git.dirty=true；需要说明导出时工作区改动原因，或重新从干净 commit 导出。
- drift policy 要求人工复核；需要说明 metric / baseline / scenario / artifact 变化原因。

## Paper-grade checklist

- okTrue: True
- archiveCheckPassed: True
- gitCleanAtExport: False
- schemaRegistryV1: True
- driftExplained: False
- driftPolicyBlocking: False
- manualWindowVerified: False
- externalModelVerifiedIfNeeded: True

## LLM evidence summary

```json
{
  "schemaVersion": "process_llm_evidence.v1",
  "providerUsageSchemaVersion": "provider_usage_actual.v1",
  "providerMode": "cloud",
  "seedCount": 5,
  "recordCount": 100,
  "cloudCallCount": 100,
  "fallbackCount": 0,
  "totals": {
    "calls": 100,
    "tokens": 189949,
    "promptTokens": 167610,
    "completionTokens": 22339,
    "latencyTotalMs": 308612,
    "latencyAvgMs": 3086.12,
    "cost": 0.02972032,
    "currency": "USD"
  }
}
```

## Remaining caveat for external use

This run can support `promoted with caveat` wording for `C2`/`C3`/`C4`. It should not be presented as final empirical evidence until human process ratings, Godot window review, and broader scenario coverage are recorded.
