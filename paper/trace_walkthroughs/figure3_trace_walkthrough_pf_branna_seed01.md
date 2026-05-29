# Figure 3 Trace Walkthrough (research-preview)

## Scope and evidence level

- Intended figure: Figure 3 (`intervention -> event -> subjective memory -> relationship/heuristic -> later decision -> outcome`)
- Claim level target: L2 local guardrail evidence (per `paper/claim_policy.md`)
- This walkthrough uses the current promoted process export for both trace lanes and aggregate metrics from the generated paper tables. Wording stays at interface/research-preview level.

## Source artifact

- Run: `.run/eval-promoted/run_2026-05-29T13-57-50Z`
- Manifest: `.run/eval-promoted/run_2026-05-29T13-57-50Z/manifest.json`
  - `ok=true`
  - `git.shortCommit=25c053d`
  - `git.dirty=true`
  - Dirty export caveat is documented in the promoted run `PROMOTION.md`; the owner approved promoted-with-caveat claim wording on 2026-05-29.
  - `seedCount=5`
- Per-scenario file:
  - `.run/eval-promoted/run_2026-05-29T13-57-50Z/per_scenario/pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json`
- Second trace source:
  - `.run/eval-promoted/run_2026-05-29T13-57-50Z/per_scenario/pf.repair_talk_requires_memory_trace_full_motivational_delegation_seed01.json`
  - Same manifest: `ok=true`, `git.shortCommit=25c053d`, `git.dirty=true`, `seedCount=5`, with the same promoted-with-caveat note in `PROMOTION.md`.

## Candidate trace chain for Figure 3

Graphical draft source: `paper/diagrams/trace_evidence_chain_figure3.mmd`.

The figure source uses curated labels from the evidence below. It avoids relying on raw event-summary text so the rendered figure stays stable across artifact locale and encoding differences.

### Trace A: Branna forgiveness

1. **Intervention/setup anchor**
   - `scenarioId=pf.branna_forgiveness_requires_memory`
   - `setupKind=forgiveness_memory`
   - Seeded harm memory: `harmEventId=evt_23610b252185405b98964b4dd06abf8f`, `recordId=evt_23610b252185405b98964b4dd06abf8f:bram:harm`

2. **Tool event (goal-relevant action)**
   - `eventType=tool.execution_completed`
   - `eventId=evt_1d1e79ac8322464fb5bdf2ea9f16f779`
   - `toolId=social.chat_with`
   - `targetNpcId=player`
   - Trace refs include subjective memory refs (`count=1`), heuristic refs (`count=1`), and motivation decision trace (`eventId=evt_41f9c18817c84abea138bde5e6cc2b99`).

3. **Observed memory result (trace-link bridge)**
   - `eventType=memory.result_observed`
   - `eventId=evt_dc118721774042e481de495af597288f`
   - `sourceEventId=evt_1d1e79ac8322464fb5bdf2ea9f16f779`
   - `observerVisibility=participants_only`
   - `memoryCount=2`
   - `relationshipEdgeCount=3`

4. **Subjective memory + relationship + heuristic evidence**
   - Subjective memory records include `evt_23610b252185405b98964b4dd06abf8f:bram:harm` (negative valence) and `evt_1d1e79ac8322464fb5bdf2ea9f16f779:bram` (current interaction).
   - Relationship edges include `bram::player::trust` (`strength=0.52`) and `bram::player::affection` (`strength=0.53`).
   - Heuristic refs include designer seed and preference heuristics.

5. **Later decision and counterfactual replay**
   - With relationship memory: `social.chat_with`
   - Without relationship memory: `social.give_gift`
   - `toolSelectionChanged=true`
   - `counterfactualToolSelectionChangeRate=0.5`
   - Replay stats:
     - `cycleCount=24`
     - `comparisonCount=48`
     - `changedDecisionCount=24`

6. **Outcome snapshot (for this seed)**
   - `goal_success_rate=1.0`
   - `required_process_coverage=1.0`
   - `causal_trace_coverage=1.0`
   - `relationship_memory_causal_use_rate=1.0`
   - `process_believability_score=1.0`
   - Process checks listed in the artifact are all `true`.

### Trace B: Tomas repair trace

1. **Setup anchor**
   - `scenarioId=pf.repair_talk_requires_memory_trace`
   - `setupKind=default`
   - Agent / target: `tomas -> mira`
   - Location: `plaza`, `plaza_fountain`

2. **Tool event (goal-relevant action)**
   - `eventType=tool.execution_completed`
   - `eventId=evt_64b6f17377694f12a1ee184d2deaa46a`
   - `toolId=social.give_gift`
   - `targetNpcId=mira`
   - Motivation decision trace selected `social.give_gift` (`eventId=evt_4391fca1d95a44bea6948de1e3537ca0`).

3. **Observed memory result (trace-link bridge)**
   - `eventType=memory.result_observed`
   - `eventId=evt_79220d486b674ff6988532ee8e6ac407`
   - `sourceEventId=evt_64b6f17377694f12a1ee184d2deaa46a`
   - `observerVisibility=participants_only`
   - `memoryCount=2`
   - `relationshipEdgeCount=2`

4. **Subjective memory + relationship + heuristic evidence**
   - Subjective memory record: `evt_64b6f17377694f12a1ee184d2deaa46a:tomas`.
   - Relationship edges include `mira::tomas::trust` (`strength=0.52`) and `mira::tomas::affection` (`strength=0.54`).
   - Heuristic refs include `designer_seed:tomas:designer_prefer_open_shop_money_anxiety` and `tomas:prefer_successful_tool:social.give_gift`.

5. **Later decision and counterfactual replay**
   - With memory: `social.give_gift`
   - Without memory: `social.chat_with`
   - `toolSelectionChanged=true`
   - `counterfactualToolSelectionChangeRate=1.0`
   - Replay stats:
     - `cycleCount=24`
     - `comparisonCount=24`
     - `changedDecisionCount=24`

6. **Outcome snapshot (for this trace)**
   - `goal_success_rate=1.0`
   - `required_process_coverage=1.0`
   - `causal_trace_coverage=1.0`
   - `relationship_memory_causal_use_rate=1.0`
   - `process_believability_score=1.0`

### Aggregate guardrail annotation

1. **Process suite aggregate**
   - Source: `paper/generated/eval_summary_tables.md` and `.run/eval-promoted/run_2026-05-29T13-57-50Z/summary.json`.
   - Full Motivational Delegation process aggregate: `n=20` (`5 seeds x 4 scenarios`).
   - `counterfactual_tool_selection_change_rate=0.375`.
   - `causal_trace_coverage=1.0`.
   - `forced_action_rate=0`, `agent_initiated_action_ratio=1.0`.
   - This annotation is a promoted-with-caveat guardrail summary, with final empirical wording still pending human process review.

## Figure drafting notes (manual follow-up required)

- Mermaid graph source is ready at `paper/diagrams/trace_evidence_chain_figure3.mmd` and is referenced by the LaTeX Figure 3 placeholder.
- Both trace lanes now point at the same current promoted five-seed process export.
- Rendered labels should continue to use curated wording instead of raw summary text.
- Publication-ready Figure 3 may still need visual hierarchy/layout polish before external release.
