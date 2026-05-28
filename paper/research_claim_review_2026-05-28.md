# Research Claim Review: 2026-05-28

## Scope

- Claims reviewed: `C2`, `C3`, `C4`, `C7`, `C15`, and new robustness regression guardrail claim `C16`.
- Evidence level target: keep paper wording at `research-preview`, `local guardrail`, or `promoted regression guardrail with caveat`.
- Commands checked this session:
  - `npm.cmd run research:evidence:check`: pass, latest promoted robustness manifest `.run/eval-promoted/robustness_2026-05-28T03-08-43Z/manifest.json`.
  - `npm.cmd run eval:archive:drift`: pass, no blocking drift; 2 comparisons require manual review under the zero-tolerance drift policy.

## Robustness Drift Review

Reviewed run: `.run/eval-promoted/robustness_2026-05-28T03-08-43Z`.

Current machine status: `needs_manual_review`.

Verdict: usable as a promoted regression guardrail candidate with an explicit drift caveat; not paper-grade empirical evidence by itself.

Reasoning:

- The latest robustness export is clean: `git.dirty=false`, `ok=true`, `seedCount.process=5`, `seedCount.domain=5`.
- `phase2.evidence_robustness.strict_gate.v1` passed with `failedCheckCount=0`.
- Domain signatures remain present for `loomstead.coding.v0` and `loomstead.town.v0`, both with `overallInvarianceRate=1.0`.
- The drift that keeps the promotion in `needs_manual_review` is scenario indexing drift: the latest manifest adds `scenarioIds` for 4 process scenarios, 8 coding scenarios, and 3 narrative scenarios after the manifest scanner was fixed.
- No metric id, baseline, schema registry version, export kind, eval gate summary, or artifact count regressed in the robustness comparison.

Safe wording:

> The latest promoted robustness run is a regression guardrail candidate: it passed strict evidence robustness checks across process, coding, and narrative scenario groups with five deterministic seeds. Its promotion remains marked `needs_manual_review` because the drift policy requires a human explanation for newly indexed scenario ids, which reflect manifest coverage repair rather than a metric or baseline change.

Unsafe wording:

- Do not call this `paper-grade` evidence yet.
- Do not use it to claim human believability, real LLM robustness, or real coding-task performance.
- Do not treat strict source perturbation stability as proof that the underlying scenario semantics are complete.

## Claim Reviews

### C2

Claim: Motivational Delegation can satisfy process constraints while preserving agent-initiated action in current rule-level scenarios.

Verdict: keep, with local-rule-level wording.

Evidence level: artifact backed, not final empirical.

Supporting evidence:

- `.run/eval-runs/run_2026-05-27T13-37-33Z/summary.json`.
- `paper/generated/eval_summary_tables.md`: Full Motivational Delegation aggregate shows `goal_success_rate=1`, `required_process_coverage=1`, `forced_action_rate=0`, `agent_initiated_action_ratio=1`, `process_believability_score=1`, `n=20`.

Counterclaim: the scenarios are deterministic rule fixtures and may overfit the current Process Fidelity predicates.

Gaps:

- 10-seed report target pending.
- LLM-backed process run pending.
- Human process believability ratings pending.

Recommended wording:

> In the current rule-level process suite, Motivational Delegation satisfies the tracked process predicates while preserving agent-initiated action; this is local guardrail evidence rather than a final empirical result.

### C3

Claim: Hard Delegation reaches final goals in the current process suite while producing shortcut and autonomy violations.

Verdict: keep, with baseline caveat.

Evidence level: artifact backed, not final empirical.

Supporting evidence:

- `.run/eval-runs/run_2026-05-27T13-37-33Z/ablation_comparison.json`.
- `paper/generated/eval_summary_tables.md`: Hard Delegation aggregate shows `goal_success_rate=1`, `shortcut_violation_rate=1`, `forced_action_rate=1`, `agent_initiated_action_ratio=0`, `causal_trace_coverage=0`, `process_believability_score=0.037143`, `n=20`.

Counterclaim: the Hard Delegation baseline is intentionally synthetic and may be weaker than a dynamic task planner with recovery.

Gaps:

- Stronger dynamic hard-delegation or static-todo baseline pending.
- Human review of whether each shortcut violation is semantically fair pending.

Recommended wording:

> The current synthetic Hard Delegation baseline is useful as a shortcut/autonomy guardrail: it can reach final goals while violating process and autonomy predicates, but stronger task-delegation baselines remain future work.

### C4

Claim: Relationship edges and evidence links are used as causal evidence in current ablation and replay scaffolds.

Verdict: keep, but do not generalize beyond current scaffolds.

Evidence level: artifact backed, narrow claim.

Supporting evidence:

- `.run/eval-runs/run_2026-05-27T13-37-33Z/summary.json`.
- Process suite aggregate: Full baseline `relationship_memory_causal_use_rate=1`, `counterfactual_tool_selection_change_rate=0.375`, `causal_trace_coverage=1`.
- Negative controls show process degradation or trace failure: `no_relationship_edge` has `goal_success_rate=0` and `causal_trace_coverage=0`; `evidence_link_removal` has `shortcut_violation_rate=1` and `causal_trace_coverage=0`.

Counterclaim: current replay is still fixture-level and does not prove broad memory causality across open-ended narrative behavior.

Gaps:

- More relationship-specific scenarios pending.
- Human trace review pending.
- LLM-backed replay pending.

Recommended wording:

> Current ablation and replay scaffolds show that relationship and evidence-link inputs affect tracked fixture routes and trace validity; broader memory-causality claims remain open.

### C7

Claim: The DomainAdapter abstraction can export comparable summary schema across town and coding fixtures.

Verdict: keep as interface evidence.

Evidence level: artifact backed, task-secondary.

Supporting evidence:

- `.run/eval-runs/domain_2026-05-27T13-29-21Z/summary.json`.
- `paper/generated/eval_summary_tables.md`: cross-domain aggregate `55/55`, coding `40/40`, town `15/15`, aggregate `counterfactual_tool_selection_change_rate=0.645238`.
- `docs/cross_domain_adapter.md` records 3 narrative scenarios and 8 coding fixture scenarios.

Counterclaim: fixture-level coding evidence does not prove real software-engineering performance.

Gaps:

- Human reviewer spot checks pending.
- Realistic external coding tasks pending.
- Non-rule provider evidence pending.

Recommended wording:

> The DomainAdapter currently provides interface-level portability evidence by exporting comparable trace and metric schemas across town and coding fixtures; it does not yet support claims about real coding-task performance.

### C15

Claim: The coding adapter provides fixture-level portability evidence through 8 repo fixtures, derived dependency graphs, dependency evidence chains, cross-file regression, reviewer arbitration, and counterfactual replay artifacts.

Verdict: keep as fixture-level portability evidence.

Evidence level: artifact backed, task-secondary.

Supporting evidence:

- `.run/eval-runs/domain_2026-05-27T13-29-21Z/manifest.json`.
- `docs/cross_domain_adapter.md` scenario inventory lists 8 coding dry-run fixtures.
- `paper/generated/eval_summary_tables.md` records `loomstead.coding.v0` `n=40` with comparable metric output.

Counterclaim: the coding adapter may be validating export plumbing more than meaningful software-engineering behavior.

Gaps:

- Manual reviewer sampling pending.
- More realistic coding tasks pending.
- External repository variance pending.

Recommended wording:

> The coding adapter currently demonstrates fixture-level portability of the GoalSpec / Trace / Eval interface, including patch-test-review evidence artifacts; real task-performance claims remain out of scope.

### C16

Claim: The promoted robustness run provides a regression guardrail for evidence-link stability across process, coding, and narrative scenario groups.

Verdict: keep with explicit `needs_manual_review` drift caveat.

Evidence level: promoted evidence with caveat.

Supporting evidence:

- `.run/eval-promoted/robustness_2026-05-28T03-08-43Z/manifest.json`.
- `npm.cmd run research:evidence:check`: pass, strict gate pass, `scenarioCount=15`.
- `.run/eval-runs/drift_report.json`: robustness drift severity `review`, `blocksPromotion=false`, reason `scenarioIds` added.

Counterclaim: source perturbation robustness does not prove the scenario set is complete or externally valid.

Gaps:

- Machine promotion status still `needs_manual_review`.
- Human reviewer sampling pending.
- True provider and human-believability evidence pending.

Recommended wording:

> The latest promoted robustness run is a regression guardrail candidate for evidence-link stability across process, coding, and narrative fixtures; the only recorded promotion caveat is a reviewed scenario-indexing drift, not a failing metric or baseline regression.
