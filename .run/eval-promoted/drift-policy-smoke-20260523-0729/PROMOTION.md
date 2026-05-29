# Eval Run Promotion

- status: `needs_manual_review`
- promotedAt: `2026-05-23T07:37:39+00:00`
- sourceRunDir: `.run/eval-runs/domain_2026-05-23T07-25-04Z`
- suite: `cross_domain_adapter`
- baseline: `full_motivational_delegation`
- manifestSha256: `452499d3fc1fff4eccdd64a93e44944f199bf8118c3d9998a342a231ae087a89`
- note: drift policy smoke

## Manual review items

- manifest git.dirty=true；需要说明导出时工作区改动原因，或重新从干净 commit 导出。

## Paper-grade checklist

- okTrue: True
- archiveCheckPassed: True
- gitCleanAtExport: False
- schemaRegistryV1: True
- driftExplained: True
- driftPolicyBlocking: False
- manualWindowVerified: False
- externalModelVerifiedIfNeeded: False
