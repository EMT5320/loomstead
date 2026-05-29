# Research Claim Review: 2026-05-29

## Scope

- Claims reviewed: `C2`, `C3`, `C4`, plus the cross-environment evidence path for Process Fidelity.
- Evidence level target: owner-approved `promoted with caveat` for `C2`, `C3`, and `C4`; keep final-empirical wording blocked on human review and broader scenario coverage.
- Commands checked in this closure pass:
  - `python scripts/run_agent_eval.py --suite process --export-dir .run/eval-runs --seeds 5`: pass, exported `.run/eval-runs/run_2026-05-29T13-57-50Z`.
  - `npm.cmd run eval:archive:promote -- run_2026-05-29T13-57-50Z`: pass, promoted to `.run/eval-promoted/run_2026-05-29T13-57-50Z`, status `needs_manual_review`.
  - `npm.cmd run paper:tables`: pass, generated tables from `.run/eval-promoted/` after switching the default paper-table input away from the local rolling export directory.

## Cloud Provider Evidence

Reviewed artifacts:

- `.run/process-llm-evidence/cloud-branna-forgiveness-2026-05-29.json`.
- `.run/process-llm-evidence/cloud-3goalspec-2026-05-29.json`.
- `.run/process-llm-evidence/cloud-4goalspec-summary-2026-05-29.json`.
- `.run/eval-promoted/run_2026-05-29T13-57-50Z/llm_evidence.json`.

Current provider-usage facts:

- `scenarioCount=4`: `pf.branna_forgiveness_requires_memory`, `pf.repair_talk_requires_memory_trace`, `pf.shared_chat_builds_traceable_trust`, `pf.affiliation_bias_remains_agent_initiated`.
- `seedCount=5`, `baselineCount=5`, `recordCount=100`.
- `cloudCallCount=100`, `fallbackCount=0`.
- Totals: `tokens=189949`, `promptTokens=167610`, `completionTokens=22339`, `latencyAvgMs=3086.12`, `cost=0.02972032 USD`.

Interpretation:

- The cloud-provider path is now artifact backed across all current Process Fidelity GoalSpecs.
- The promoted process run carries both rule-level process metrics and the cloud usage evidence through `llmEvidence`.
- The promotion remains `needs_manual_review` at the machine-record level because the export was created while the working tree was dirty and drift policy requires human explanation for the metric / baseline / scenario / artifact changes. The owner has reviewed the claim-level interpretation and approved `promoted with caveat` wording for `C2`/`C3`/`C4`.

Safe wording:

> Current Process Fidelity evidence is backed by a promoted rule-level process export plus 100 real cloud-provider arbitration records across four GoalSpecs, five seeds, and five baselines. The cloud evidence verifies provider execution and selected-tool traces; `C2`/`C3`/`C4` may be cited as promoted with caveat, while final empirical wording still requires human process review.

Unsafe wording:

- Do not present the cloud evidence as human believability validation.
- Do not claim statistical significance from the five-seed provider run.
- Do not treat the `needs_manual_review` promotion as a clean final-empirical artifact without the stated caveat.

## Cross-Environment Evidence Policy

Closure decision:

- `.run/eval-runs/` remains a machine-local rolling export directory.
- `.run/eval-promoted/` is the cross-environment source for cited eval runs.
- `.run/process-llm-evidence/latest*.json` is a mutable local cache for export/promotion and should stay ignored.
- Named cloud evidence files such as `cloud-*.json` and summary artifacts are the cross-environment provider evidence snapshots.
- `paper:tables` now defaults to `.run/eval-promoted/`, which keeps generated paper tables stable across home and office machines.

## Claim Reviews

Owner confirmation note: on 2026-05-29, the owner approved using `promoted with caveat` for `C2`, `C3`, and `C4` based on the cloud-backed Process Fidelity run. Final empirical status remains pending.

### C2

Claim: Motivational Delegation can satisfy process constraints while preserving agent-initiated action in current rule-level scenarios.

Verdict: owner-approved `promoted with caveat`.

Supporting evidence:

- `.run/eval-promoted/run_2026-05-29T13-57-50Z/summary.json`.
- `.run/eval-promoted/run_2026-05-29T13-57-50Z/llm_evidence.json`.
- `paper/generated/eval_summary_tables.md`.

Current result:

- Full baseline: `goal_success_rate=1`, `required_process_coverage=1`, `forced_action_rate=0`, `agent_initiated_action_ratio=1`, `causal_trace_coverage=1`, `process_believability_score=1`, `n=20`.
- Cloud provider usage confirms 100 real arbitration records across the full current Process Fidelity scenario set.

Remaining gaps:

- Human process ratings before final empirical wording.
- Larger and less fixture-like process suite.

### C3

Claim: Hard Delegation reaches final goals in the current process suite while producing shortcut and autonomy violations.

Verdict: owner-approved `promoted with caveat`.

Supporting evidence:

- `.run/eval-promoted/run_2026-05-29T13-57-50Z/ablation_comparison.json`.
- `.run/eval-promoted/run_2026-05-29T13-57-50Z/llm_evidence.json`.
- `paper/generated/ablation_table.csv`.

Current result:

- Hard Delegation delta vs Full: `goal_success_rate=0`, `required_process_coverage=-0.814286`, `process_believability_score=-0.962857`, `causal_trace_coverage=-1`, `relationship_memory_causal_use_rate=-1`, `shortcut_violation_rate=1`.

Remaining gaps:

- Stronger dynamic task-delegation baseline.
- Human review of shortcut semantics.

### C4

Claim: Relationship edges and evidence links are used as causal evidence in current ablation and replay scaffolds.

Verdict: owner-approved `promoted with caveat`.

Supporting evidence:

- `.run/eval-promoted/run_2026-05-29T13-57-50Z/summary.json`.
- `.run/eval-promoted/run_2026-05-29T13-57-50Z/llm_evidence.json`.
- Counterfactual replay and ablation artifacts in the promoted run.

Current result:

- Full baseline: `relationship_memory_causal_use_rate=1`, `causal_trace_coverage=1`, `counterfactual_tool_selection_change_rate=0.375`.
- Negative controls degrade process outcomes or trace validity: `no_relationship_edge`, `shuffled_memory_owner`, and `evidence_link_removal` all lose goal success or causal evidence coverage relative to Full.

Remaining gaps:

- Broader relationship-specific scenarios.
- Human trace review.
