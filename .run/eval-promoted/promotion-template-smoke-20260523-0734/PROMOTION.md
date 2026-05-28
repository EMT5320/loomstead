# Eval Run Promotion

- status: `needs_manual_review`
- purpose: `portfolio` (作品集证据)
- promotedAt: `2026-05-23T07:41:16+00:00`
- sourceRunDir: `.run/eval-runs/domain_2026-05-23T07-25-04Z`
- suite: `cross_domain_adapter`
- baseline: `full_motivational_delegation`
- manifestSha256: `452499d3fc1fff4eccdd64a93e44944f199bf8118c3d9998a342a231ae087a89`
- note: portfolio smoke

## Purpose note prompts

- 说明该 run 支撑的可展示能力。
- 记录一段非技术读者可理解的结果摘要。
- 列出截图、视频或 Godot 窗口验收引用。

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

## Purpose checklist

- [ ] 确认展示素材不包含本机密钥或私有路径。
- [ ] 确认失败或人工未验收项已在展示说明中标注。
