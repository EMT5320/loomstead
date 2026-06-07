# Figure 3 Trace Walkthrough (portfolio appendix)

## Scope and evidence boundary

- Intended figure: Figure 3 (`intervention -> event -> subjective memory -> relationship/heuristic -> later decision -> outcome`)
- Evidence boundary: promoted-with-caveat, metric / explainability level.
- ID binding: this walkthrough is bound to the current promoted process export `.run/eval-promoted/run_2026-05-29T13-57-50Z`. If that artifact is refreshed, rerun `npm.cmd run portfolio:snippets` and update this appendix together.
- Usage: appendix evidence for portfolio case cards. The first-screen path remains `docs/portfolio_case_cards.md` plus `docs/portfolio_evidence_snippets.md`.

## Source artifact

- Run: `.run/eval-promoted/run_2026-05-29T13-57-50Z`
- Manifest: `.run/eval-promoted/run_2026-05-29T13-57-50Z/manifest.json`
  - `ok=true`
  - `git.shortCommit=25c053d`
  - `git.dirty=true`
  - Dirty export caveat is documented in the promoted run `PROMOTION.md`; the owner approved promoted-with-caveat claim wording on 2026-05-29.
  - `seedCount=5`
- Trace A per-scenario file:
  - `.run/eval-promoted/run_2026-05-29T13-57-50Z/per_scenario/pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json`
- Trace B per-scenario file:
  - `.run/eval-promoted/run_2026-05-29T13-57-50Z/per_scenario/pf.repair_talk_requires_memory_trace_full_motivational_delegation_seed01.json`

## Candidate trace chain for Figure 3

Graphical draft source: `paper/diagrams/trace_evidence_chain_figure3.mmd`.

The figure source uses curated labels from the evidence below. It avoids relying on raw event-summary text so the rendered figure stays stable across artifact locale and encoding differences.

### Trace A: Branna forgiveness

1. **Intervention/setup anchor**
   - `scenarioId=pf.branna_forgiveness_requires_memory`
   - `setupKind=forgiveness_memory`
   - Seeded harm memory: `harmEventId=evt_512d3011ef624d95adffe43979a05208`, `recordId=evt_512d3011ef624d95adffe43979a05208:bram:harm`, `emotionalValence=-0.7976000000000001`

2. **Tool event (goal-relevant action)**
   - `eventType=tool.execution_completed`
   - `eventId=evt_5df32c5b59614a4a81caecd8b23aafd9`
   - `toolId=social.chat_with`
   - `targetNpcId=player`
   - Direct `sourceEventIds`: `evt_138fb9fe526c4918bffac68d93162296`
   - Motivation decision trace: `eventId=evt_dd21b7b4fdf5404690c5d90b89fbcfc3`, `traceId=trace_708567a85c4a4c2b97608bd561367641`, `selectedToolId=social.chat_with`

3. **Observed memory result (trace-link bridge)**
   - `eventType=memory.result_observed`
   - `eventId=evt_4e9c8173ebfd4faca73804478bbd4c1e`
   - `sourceEventId=evt_5df32c5b59614a4a81caecd8b23aafd9`
   - `observerVisibility=participants_only`
   - `memoryCount=2`
   - `relationshipEdgeCount=3`

4. **Subjective memory + relationship + heuristic evidence**
   - Subjective memory records include seeded harm memory `evt_512d3011ef624d95adffe43979a05208:bram:harm` and interaction memory `evt_5df32c5b59614a4a81caecd8b23aafd9:bram` (`emotionalValence=0.25`).
   - Relationship edges include `bram::player::trust` (`strength=0.52`) and `bram::player::affection` (`strength=0.53`).
   - Heuristic refs include `bram:designer:avoid_bram_force_chat_when_angry` and `bram:prefer_social_when_affiliation_high`.

5. **Later decision and counterfactual replay**
   - With full relationship/memory evidence: `social.chat_with` wins (`0.956874` vs `social.give_gift=0.902323`).
   - Relationship-edge-only removal: `social.chat_with` still wins (`0.893874` vs `social.give_gift=0.886573`), with `relationshipDecisionEffect=false`.
   - Top-level no-memory replay: `selectedWithoutRelationshipMemory=social.give_gift` (`0.845833` vs `social.chat_with=0.845`).
   - Single-record replay:
     - remove `evt_512d3011ef624d95adffe43979a05208:bram:harm` -> `social.chat_with`, `changed=false`
     - remove `evt_5df32c5b59614a4a81caecd8b23aafd9:bram` -> `social.give_gift`, `changed=true`
   - Replay stats: `cycleCount=24`, `comparisonCount=48`, `changedDecisionCount=24`, `changeRate=0.5`.
   - Reason labels: `reasonWithRelationshipMemory=memory_and_heuristic_weighted_fit`, `reasonWithoutRelationshipEdges=memory_and_heuristic_weighted_fit`, `reasonWithoutRelationshipMemory=highest_rule_tier_fit`.

6. **Outcome snapshot (for this seed)**
   - `goal_success_rate=1.0`
   - `required_process_coverage=1.0`
   - `causal_trace_coverage=1.0`
   - `relationship_memory_causal_use_rate=1.0`
   - `counterfactual_tool_selection_change_rate=0.5`
   - Legacy JSON field `process_believability_score=1.0` is retained for artifact compatibility; portfolio material treats it as a compatibility-only historical index and excludes it from human-believability claim language.
   - Process checks listed in the artifact are all `true`.

### Trace B: Tomas repair trace

1. **Setup anchor**
   - `scenarioId=pf.repair_talk_requires_memory_trace`
   - `setupKind=default`
   - Agent / target: `tomas -> mira`
   - Location: `plaza`, `plaza_fountain`

2. **Tool event (goal-relevant action)**
   - `eventType=tool.execution_completed`
   - `eventId=evt_882df3594cc64086b9f95b317c9b1184`
   - `toolId=social.give_gift`
   - `targetNpcId=mira`
   - Direct `sourceEventIds`: `evt_d10c2e764fb94ee98068f37acaca32a9`
   - Motivation decision trace: `eventId=evt_f44e7c27e1794e9e9f97d7265d91b5f7`, `traceId=trace_b005eb5e6a6a42b39849636dafbf147e`, `selectedToolId=social.give_gift`

3. **Observed memory result (trace-link bridge)**
   - `eventType=memory.result_observed`
   - `eventId=evt_66533174ecb8415e8781fb379e981508`
   - `sourceEventId=evt_882df3594cc64086b9f95b317c9b1184`
   - `observerVisibility=participants_only`
   - `memoryCount=2`
   - `relationshipEdgeCount=2`

4. **Subjective memory + relationship + heuristic evidence**
   - Subjective memory record: `evt_882df3594cc64086b9f95b317c9b1184:tomas`.
   - Relationship edges include `mira::tomas::trust` (`strength=0.52`) and `mira::tomas::affection` (`strength=0.54`).
   - Heuristic refs include `tomas:prefer_social_when_affiliation_high` and `tomas:prefer_successful_tool:social.give_gift`.

5. **Later decision and counterfactual replay**
   - With full relationship/memory evidence: `social.give_gift` wins (`0.986233` vs `social.chat_with=0.9626`).
   - Relationship-edge-only removal: `social.give_gift` still wins (`0.970333` vs `social.chat_with=0.899`), with `relationshipDecisionEffect=false`.
   - Single-record replay removes `evt_882df3594cc64086b9f95b317c9b1184:tomas`: cycle-level selected tool changes from `social.give_gift` to `social.chat_with` in 24/24 comparisons.
   - Replay stats: `cycleCount=24`, `comparisonCount=24`, `changedDecisionCount=24`, `changeRate=1.0`.

6. **Outcome snapshot (for this seed)**
   - `goal_success_rate=1.0`
   - `required_process_coverage=1.0`
   - `causal_trace_coverage=1.0`
   - `relationship_memory_causal_use_rate=1.0`
   - `counterfactual_tool_selection_change_rate=1.0`
   - Legacy JSON field `process_believability_score=1.0` is retained for artifact compatibility and excluded from current portfolio claim language.

### Aggregate guardrail annotation

1. **Process suite aggregate**
   - Source: `paper/generated/eval_summary_tables.md` and `.run/eval-promoted/run_2026-05-29T13-57-50Z/summary.json`.
   - Full Motivational Delegation process aggregate: `n=20` (`5 seeds x 4 scenarios`).
   - `counterfactual_tool_selection_change_rate=0.375`.
   - `no_relationship_edge` baseline `counterfactual_tool_selection_change_rate=0.25`.
   - `no_subjective_memory` baseline `counterfactual_tool_selection_change_rate=0.0`.
   - `causal_trace_coverage=1.0`.
   - `forced_action_rate=0`, `agent_initiated_action_ratio=1.0`.
   - This annotation is a promoted-with-caveat guardrail summary for metric / explainability discussion.

## Appendix figure notes

- Mermaid graph source is ready at `paper/diagrams/trace_evidence_chain_figure3.mmd` and is referenced by the LaTeX Figure 3 placeholder.
- Both trace lanes point at the same current promoted five-seed process export.
- Rendered labels should continue to use curated wording instead of raw summary text.
- External release can use this walkthrough as appendix material; the first-screen portfolio path should start from `docs/portfolio_case_cards.md`.
