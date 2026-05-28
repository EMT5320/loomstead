# Figure 3 Trace Walkthrough Draft (research-preview)

## Scope and evidence level

- Intended figure: Figure 3 (`intervention -> event -> subjective memory -> relationship/heuristic -> later decision -> outcome`)
- Claim level target: L2 local guardrail evidence (per `paper/claim_policy.md`)
- This draft uses one clean exported artifact for the primary Branna trace, one older local trace artifact for a second illustrative lane, and aggregate metrics from the latest generated paper tables. Wording stays at interface/research-preview level.

## Source artifact

- Run: `.run/eval-runs/run_2026-05-27T13-37-33Z`
- Manifest: `.run/eval-runs/run_2026-05-27T13-37-33Z/manifest.json`
  - `ok=true`
  - `git.shortCommit=71e9f07`
  - `git.dirty=false`
  - `seedCount=5`
- Per-scenario file:
  - `.run/eval-runs/run_2026-05-27T13-37-33Z/per_scenario/pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json`
- Second trace source:
  - `.run/eval-runs/run_2026-05-25T07-34-53Z/per_scenario/pf.repair_talk_requires_memory_trace_full_motivational_delegation.json`
  - `ok=true`, `git.shortCommit=a4581b2`, `git.dirty=false`, `seedCount=1`

## Candidate trace chain for Figure 3

Graphical draft source: `paper/diagrams/trace_evidence_chain_figure3.mmd`.

The figure source uses curated labels from the evidence below. It intentionally avoids raw artifact event summaries because the source artifact contains mojibake-like strings.

### Trace A: Branna forgiveness

1. **Intervention/setup anchor**
   - `scenarioId=pf.branna_forgiveness_requires_memory`
   - `setupKind=forgiveness_memory`
   - Seeded harm memory:
     - `harmEventId=evt_485d0da457cd4ad1b4a992914c672653`
     - `recordId=evt_485d0da457cd4ad1b4a992914c672653:bram:harm`

2. **Tool event (goal-relevant action)**
   - `eventType=tool.execution_completed`
   - `eventId=evt_aa11706eb4b4408b9f92df85fd7546a4`
   - `toolId=social.chat_with`
   - `targetNpcId=player`
   - Trace refs include:
     - subjective memory refs (`count=1`)
     - heuristic refs (`count=1`)
     - motivation decision trace (`eventId=evt_f3aae51dfcdc4ba5a4f09580ea98f4fe`)

3. **Observed memory result (trace-link bridge)**
   - `eventType=memory.result_observed`
   - `eventId=evt_6223740588d04bb5a242b7063554154e`
   - `sourceEventId=evt_aa11706eb4b4408b9f92df85fd7546a4`
   - `observerVisibility=participants_only`
   - `memoryCount=2`
   - `relationshipEdgeCount=3`

4. **Subjective memory + relationship + heuristic evidence**
   - Subjective memory records include:
     - `evt_485d0da457cd4ad1b4a992914c672653:bram:harm` (negative valence)
     - `evt_aa11706eb4b4408b9f92df85fd7546a4:bram` (current interaction)
   - Relationship edges include:
     - `bram::player::trust` (`strength=0.52`)
     - `bram::player::affection` (`strength=0.53`)
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
   - `eventId=evt_b4d123eedf23465a9035ca036c6a4628`
   - `toolId=social.give_gift`
   - `targetNpcId=mira`
   - Motivation decision trace selected `social.give_gift` (`eventId=evt_e63f41812e5c4feab539ea941ecca886`).

3. **Observed memory result (trace-link bridge)**
   - `eventType=memory.result_observed`
   - `eventId=evt_e9f54b17ff5c44989a15b9eaf52e83d5`
   - `sourceEventId=evt_b4d123eedf23465a9035ca036c6a4628`
   - `observerVisibility=participants_only`
   - `memoryCount=2`
   - `relationshipEdgeCount=2`

4. **Subjective memory + relationship + heuristic evidence**
   - Subjective memory record: `evt_b4d123eedf23465a9035ca036c6a4628:tomas`.
   - Relationship edges include:
     - `mira::tomas::trust` (`strength=0.52`)
     - `mira::tomas::affection` (`strength=0.54`)
   - Heuristic refs include `tomas:prefer_social_when_affiliation_high` and `tomas:prefer_successful_tool:social.give_gift`.

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
   - Source: `paper/generated/eval_summary_tables.md` and `.run/eval-runs/run_2026-05-27T13-37-33Z/summary.json`.
   - Full Motivational Delegation process aggregate: `n=20` (`5 seeds x 4 scenarios`).
   - `counterfactual_tool_selection_change_rate=0.375`.
   - `causal_trace_coverage=1.0`.
   - `forced_action_rate=0`, `agent_initiated_action_ratio=1.0`.
   - This annotation is a local guardrail summary, not a publication-level causal claim.

## Figure drafting notes (manual follow-up required)

- Mermaid graph source is ready at `paper/diagrams/trace_evidence_chain_figure3.mmd` and is referenced by the LaTeX Figure 3 placeholder.
- Aggregate guardrail annotation and a second trace lane have been added to the Mermaid source.
- The event summaries in the artifact include mojibake-like strings; final rendered labels should continue to use curated wording instead of raw summary text.
- Publication-ready Figure 3 still needs wording review and may later swap Trace B for a matching latest clean five-seed artifact if that local run is restored.
