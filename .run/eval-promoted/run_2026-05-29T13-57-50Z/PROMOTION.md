# Eval Run Promotion

- status: `needs_manual_review`
- purpose: `paper` (论文证据)
- promotedAt: `2026-05-29T13:57:54+00:00`
- sourceRunDir: `.run/eval-runs/run_2026-05-29T13-57-50Z`
- suite: `process_fidelity`
- baseline: `full_motivational_delegation`
- manifestSha256: `81c91fe3d8bc6384c965f2a8d7882a35384588ce5a3b2a68094d469241beb8ca`
- note: -

## Purpose note prompts

- 说明该 run 支撑的研究问题或表格编号。
- 记录 baseline / ablation 与主要指标解读。
- 补充 llmEvidence：provider_usage_actual.v1 记录、token / latency / cost / fallback 与 final selectedToolId。
- 说明 drift policy、git dirty 和人工窗口验收状态。

## Manual review items

- promotion note 为空；请按 论文证据 模板补充人工备注。
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

## LLM evidence

```json
{
  "schemaVersion": "process_llm_evidence.v1",
  "providerUsageSchemaVersion": "provider_usage_actual.v1",
  "source": "latest_cache",
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
  },
  "records": [
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "full_motivational_delegation",
      "seedIndex": 1,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1793,
      "latencyMs": 2714,
      "cost": 0.00026012,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "full_motivational_delegation",
      "seedIndex": 2,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1878,
      "latencyMs": 2999,
      "cost": 0.0002842,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "full_motivational_delegation",
      "seedIndex": 3,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1905,
      "latencyMs": 3863,
      "cost": 0.00029162,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "full_motivational_delegation",
      "seedIndex": 4,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1922,
      "latencyMs": 3779,
      "cost": 0.00029806,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "full_motivational_delegation",
      "seedIndex": 5,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1848,
      "latencyMs": 2924,
      "cost": 0.00027692,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "no_subjective_memory",
      "seedIndex": 1,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1641,
      "latencyMs": 3421,
      "cost": 0.00025228,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "no_subjective_memory",
      "seedIndex": 2,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1571,
      "latencyMs": 2895,
      "cost": 0.00023324,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "no_subjective_memory",
      "seedIndex": 3,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1810,
      "latencyMs": 4974,
      "cost": 0.00029974,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "no_subjective_memory",
      "seedIndex": 4,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1593,
      "latencyMs": 3051,
      "cost": 0.00023856,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "no_subjective_memory",
      "seedIndex": 5,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1702,
      "latencyMs": 4244,
      "cost": 0.00026866,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "no_relationship_edge",
      "seedIndex": 1,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1723,
      "latencyMs": 3550,
      "cost": 0.00025956,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    },
    {
      "scenarioId": "pf.branna_forgiveness_requires_memory",
      "baseline": "no_relationship_edge",
      "seedIndex": 2,
      "provider": "CloudApiProvider",
      "providerMode": "cloud",
      "model": "deepseek-v4-flash",
      "tokens": 1750,
      "latencyMs": 3381,
      "cost": 0.0002674,
      "fallbackReason": null,
      "finalSelectedToolId": "social.chat_with",
      "providerUsageVersion": "provider_usage_actual.v1"
    }
  ]
}
```

## Purpose checklist

- [ ] 确认 schema 与论文方法描述一致。
- [ ] 确认导出 artifact 可复现。
- [ ] 确认真实模型或人工窗口证据已单独记录。
- [ ] 确认 llmEvidence 中的真实模型调用和 fallback_reason 已人工复核。
